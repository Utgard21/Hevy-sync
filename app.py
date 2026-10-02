import os,json,sqlite3,threading,time,csv,io,hashlib,math,base64,hmac
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
DATA=Path(os.getenv('DATA_DIR','./data')); DATA.mkdir(parents=True,exist_ok=True)
TZ=ZoneInfo(os.getenv('TZ','Europe/Sofia'))
KEY=os.getenv('HEVY_API_KEY','')
AUTH_USER=os.getenv('DASHBOARD_USERNAME','').strip(); AUTH_PASS=os.getenv('DASHBOARD_PASSWORD','')
INTERVAL=max(300,int(os.getenv('SYNC_INTERVAL','3600')))
LOCK=threading.Lock(); STATUS={'syncing':False,'last_sync':None,'error':None,'api_configured':bool(KEY)}
def db():
 c=sqlite3.connect(DATA/'hevy.sqlite'); c.execute('CREATE TABLE IF NOT EXISTS workouts (id TEXT PRIMARY KEY,source TEXT NOT NULL,payload TEXT NOT NULL)'); return c
def stamp(s):
 d=datetime.fromisoformat(s.replace('Z','+00:00')); return d.replace(tzinfo=TZ) if d.tzinfo is None else d.astimezone(TZ)
def validate(w):
 if not isinstance(w,dict) or not w.get('id'): raise ValueError('Workout is missing an ID')
 stamp(w['start_time']); stamp(w['end_time'])
 if not isinstance(w.get('exercises'),list): raise ValueError('Invalid exercises')
 for e in w['exercises']:
  if not isinstance(e.get('sets'),list): raise ValueError('Invalid sets')
  for s in e['sets']:
   for k in ['weight_kg','reps']:
    if s.get(k) is not None and (not isinstance(s[k],(int,float)) or not math.isfinite(s[k]) or s[k]<0): raise ValueError('Invalid set values')
 return w
def fetch(path,field,size):
 result=[]; page=1
 while True:
  req=Request(f'https://api.hevyapp.com/v1/{path}?page={page}&pageSize={size}',headers={'api-key':KEY,'Accept':'application/json'})
  for attempt in range(4):
   try:
    with urlopen(req,timeout=30) as r: payload=json.load(r)
    break
   except HTTPError as e:
    if e.code not in (429,500,502,503,504) or attempt==3: raise
    time.sleep(min(30,2**attempt*2))
  result.extend(payload[field])
  if page>=payload['page_count']: return result
  page+=1
  if page>10000: raise ValueError('Unexpected API pagination')
def sync():
 if not KEY or not LOCK.acquire(False): return
 STATUS.update(syncing=True,error=None)
 try:
  workouts=fetch('workouts','workouts',10)
  for w in workouts: validate(w)
  # Replace the API snapshot only after every page succeeds. CSV history is retained.
  with db() as c:
   c.execute("DELETE FROM workouts WHERE source='api'")
   c.executemany('INSERT OR REPLACE INTO workouts VALUES (?,?,?)',[(w['id'],'api',json.dumps(w)) for w in workouts])
  STATUS['last_sync']=datetime.now(timezone.utc).isoformat()
 except HTTPError as e: STATUS['error']=f'Hevy returned HTTP {e.code}. Check your API key and Pro access.'
 except Exception: STATUS['error']='Sync failed. Check connectivity and try again; cached workouts are preserved.'
 finally: STATUS['syncing']=False; LOCK.release()
def worker():
 while True: sync(); time.sleep(INTERVAL)
def csv_date(s):
 for fmt in ('%d %b %Y, %H:%M','%d %b %Y, %H:%M:%S','%Y-%m-%d %H:%M:%S'):
  try: return datetime.strptime(s,fmt).replace(tzinfo=TZ).isoformat()
  except ValueError: pass
 return stamp(s).isoformat()
def parse_csv(text):
 reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
 required={'title','start_time','end_time','exercise_title','weight_kg','reps'}
 if not required.issubset(reader.fieldnames or []): raise ValueError('Expected a Hevy workout CSV with columns: '+', '.join(sorted(required)))
 groups={}
 for r in reader:
  start=csv_date(r['start_time']); end=csv_date(r['end_time']); key=(r['title'],start,end)
  if key not in groups: groups[key]={'id':'csv-'+hashlib.sha256('|'.join(key).encode()).hexdigest(),'title':r['title'],'start_time':start,'end_time':end,'exercises':[]}
  w=groups[key]; title=r['exercise_title']; e=next((e for e in w['exercises'] if e['title']==title),None)
  if e is None: e={'title':title,'exercise_template_id':title,'sets':[]}; w['exercises'].append(e)
  e['sets'].append({'type':r.get('set_type','normal'),'weight_kg':float(r['weight_kg']) if r['weight_kg'] else None,'reps':float(r['reps']) if r['reps'] else None})
 return [validate(w) for w in groups.values()]
def stats(days=90):
 with db() as c: raw=[json.loads(r[0]) for r in c.execute('SELECT payload FROM workouts')]
 # API wins over CSV when title and timestamps match.
 raw.sort(key=lambda w: str(w['id']).startswith('csv-')); seen=set(); workouts=[]
 for w in raw:
  k=(w['title'],stamp(w['start_time']).isoformat(),stamp(w['end_time']).isoformat())
  if k not in seen: seen.add(k); workouts.append(w)
 now=datetime.now(TZ); today=now.date(); monday=today-timedelta(days=today.weekday()); cutoff=(today.replace(year=today.year-1)+timedelta(days=1)) if days==365 else today-timedelta(days=days-1)
 weekly={}; daily={}; exercises={}; recent=[]; weekdays=[0]*7; hours=[0]*24; months={}; titles={}; total_sets=total_reps=volume=duration=occurrences=0; longest=0
 selected=[w for w in workouts if cutoff<=stamp(w['start_time']).date()<=today]
 for w in sorted(selected,key=lambda w:w['start_time']):
  start=stamp(w['start_time']); day=start.date(); week=(day-timedelta(days=day.weekday())).isoformat()
  b=weekly.setdefault(week,{'workouts':0,'sets':0,'volume':0,'minutes':0}); b['workouts']+=1; daily[day.isoformat()]=daily.get(day.isoformat(),0)+1; weekdays[day.weekday()]+=1; hours[start.hour]+=1
  seconds=max(0,(stamp(w['end_time'])-start).total_seconds()); duration+=seconds; month=day.strftime('%Y-%m'); mb=months.setdefault(month,{'workouts':0,'volume':0,'sets':0,'minutes':0}); mb['workouts']+=1; mb['minutes']+=round(seconds/60); titles[w['title']]=titles.get(w['title'],0)+1; b['minutes']+=round(seconds/60); longest=max(longest,seconds); occurrences+=len(w['exercises']); wvol=0
  for e in w['exercises']:
   name=e['title']; item=exercises.setdefault(name,{'name':name,'sessions':0,'sets':0,'reps':0,'volume':0,'best_weight':0,'e1rm':0,'history':[]}); item['sessions']+=1; best=0; ev=0
   for s in e['sets']:
    if s.get('type')=='warmup': continue
    weight=s.get('weight_kg') or 0; reps=s.get('reps') or 0; v=weight*reps
    total_sets+=1; total_reps+=reps; volume+=v; wvol+=v; b['sets']+=1; b['volume']+=v; mb['sets']+=1; mb['volume']+=v
    item['sets']+=1; item['reps']+=reps; item['volume']+=v; best=max(best,weight); ev+=v
    if weight>0 and 1<=reps<=12: item['e1rm']=max(item['e1rm'],weight*(1+reps/30))
   item['best_weight']=max(item['best_weight'],best); item['history'].append({'date':day.isoformat(),'weight':best,'volume':ev})
  recent.append({'title':w['title'],'date':start.isoformat(),'exercises':len(w['exercises']),'volume':wvol,'minutes':round(max(0,(stamp(w['end_time'])-start).total_seconds())/60)})
 first=cutoff-timedelta(days=cutoff.weekday()); cursor=first
 while cursor<=today:
  weekly.setdefault(cursor.isoformat(),{'workouts':0,'sets':0,'volume':0,'minutes':0}); cursor+=timedelta(days=7)
 active_days=sorted(stamp(w['start_time']).date() for w in selected); streak=best_streak=0; prev=None
 for d in sorted(set(active_days)):
  streak=streak+1 if prev and d==prev+timedelta(days=1) else 1; best_streak=max(best_streak,streak); prev=d
 current_streak=0; d=today
 active_set=set(active_days)
 while d in active_set: current_streak+=1; d-=timedelta(days=1)
 range_days=max(1,(today-cutoff).days+1); avg_week=round(len(selected)/max(1,range_days/7),1); avg_sets=round(total_sets/len(selected),1) if selected else 0; avg_volume=round(volume/len(selected)) if selected else 0
 top_day=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'][weekdays.index(max(weekdays))] if selected else '-'; top_hour=hours.index(max(hours)) if selected else 0
 records=sorted([{'name':e['name'],'best_weight':round(e['best_weight'],1),'e1rm':round(e['e1rm'],1),'volume':round(e['volume'])} for e in exercises.values() if e['best_weight']>0],key=lambda x:x['e1rm'],reverse=True)[:10]
 monthly=[{'month':k,**v} for k,v in sorted(months.items())]; top_exercises=sorted([{'name':e['name'],'sessions':e['sessions'],'sets':e['sets'],'volume':round(e['volume'])} for e in exercises.values()],key=lambda x:x['sessions'],reverse=True)[:10]
 workout_types=sorted([{'name':k,'count':v} for k,v in titles.items()],key=lambda x:x['count'],reverse=True)[:8]
 achievements=[]
 for goal,label in [(1,'First workout'),(10,'10 workouts'),(25,'25 workouts'),(50,'50 workouts'),(100,'100 workouts'),(250,'250 workouts')]: achievements.append({'label':label,'unlocked':len(workouts)>=goal,'progress':min(100,round(len(workouts)/goal*100))})
 for goal,label in [(10000,'10K kg lifted'),(50000,'50K kg lifted'),(100000,'100K kg lifted'),(500000,'500K kg lifted')]: achievements.append({'label':label,'unlocked':volume>=goal,'progress':min(100,round(volume/goal*100))})
 return {'status':STATUS.copy(),'days':days,'summary':{'workouts':len(selected),'all_time':len(workouts),'this_week':sum(monday<=stamp(w['start_time']).date()<=today for w in workouts),'this_month':sum(stamp(w['start_time']).date().replace(day=1)==today.replace(day=1) for w in workouts),'exercises':len(exercises),'exercise_entries':occurrences,'sets':total_sets,'reps':total_reps,'volume':round(volume),'hours':round(duration/3600,1),'average_minutes':round(duration/60/len(selected)) if selected else 0,'avg_week':avg_week,'avg_sets':avg_sets,'avg_volume':avg_volume,'longest_minutes':round(longest/60),'active_days':len(set(active_days)),'current_streak':current_streak,'best_streak':best_streak,'favorite_day':top_day,'favorite_hour':top_hour},'weekly':[{'date':k,**v} for k,v in sorted(weekly.items())],'daily':daily,'exercises':sorted(exercises.values(),key=lambda e:e['sessions'],reverse=True),'recent':recent[::-1][:30],'records':records,'weekdays':weekdays,'hours':hours,'monthly':monthly,'top_exercises':top_exercises,'workout_types':workout_types,'achievements':achievements}
class Handler(BaseHTTPRequestHandler):
 def authenticated(self):
  if not AUTH_USER and not AUTH_PASS: return True
  if not AUTH_USER or not AUTH_PASS: return False
  header=self.headers.get('Authorization','')
  if not header.startswith('Basic '): return False
  try: user,password=base64.b64decode(header[6:],validate=True).decode('utf-8').split(':',1)
  except (ValueError,UnicodeError): return False
  return hmac.compare_digest(user,AUTH_USER) and hmac.compare_digest(password,AUTH_PASS)
 def auth_required(self):
  body=b'Authentication required'; self.send_response(401); self.send_header('WWW-Authenticate','Basic realm="Hevy Progress", charset="UTF-8"'); self.send_header('Content-Type','text/plain; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(body)
 def reply(self,code,body,kind='application/json'):
  data=body if isinstance(body,bytes) else json.dumps(body).encode(); self.send_response(code); self.send_header('Content-Type',kind); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(data)
 def do_GET(self):
  from urllib.parse import urlparse,parse_qs
  u=urlparse(self.path)
  if u.path!='/health' and not self.authenticated(): return self.auth_required()
  if u.path=='/health': return self.reply(200,{'ok':True})
  if u.path=='/api/stats':
   try: days=int(parse_qs(u.query).get('days',['90'])[0]); assert days in (30,90,180,365,3650); return self.reply(200,stats(days))
   except (ValueError,AssertionError): return self.reply(400,{'error':'Invalid date range'})
  if u.path=='/api/export':
   with db() as c: data=[json.loads(r[0]) for r in c.execute('SELECT payload FROM workouts')]
   return self.reply(200,data)
  files={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
  if u.path not in files: return self.reply(404,{'error':'Not found'})
  name=files[u.path]; return self.reply(200,(Path(__file__).parent/'static'/name).read_bytes(),{'html':'text/html; charset=utf-8','js':'application/javascript','css':'text/css'}[name.split('.')[-1]])
 def do_POST(self):
  if not self.authenticated(): return self.auth_required()
  # Require a custom header so third-party pages cannot submit imports/syncs.
  if self.headers.get('X-Hevy-Dashboard')!='1': return self.reply(403,{'error':'Missing request header'})
  if self.path=='/api/sync':
   if not KEY: return self.reply(400,{'error':'Set HEVY_API_KEY in your container settings, or import CSV.'})
   threading.Thread(target=sync,daemon=True).start(); return self.reply(202,{'ok':True})
  if self.path=='/api/import':
   try:
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=10*1024*1024: return self.reply(413,{'error':'CSV must be between 1 byte and 10 MB'})
    rows=parse_csv(self.rfile.read(length).decode('utf-8-sig'))
    with db() as c: c.executemany('INSERT OR REPLACE INTO workouts VALUES (?,?,?)',[(w['id'],'csv',json.dumps(w)) for w in rows])
    return self.reply(200,{'imported':len(rows)})
   except (ValueError,KeyError,UnicodeError): return self.reply(400,{'error':'Invalid Hevy CSV. Check column names, dates, and numeric values.'})
  return self.reply(404,{'error':'Not found'})
if __name__=='__main__':
 db().close(); threading.Thread(target=worker,daemon=True).start(); ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
