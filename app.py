import os,json,sqlite3,threading,time,csv,io,hashlib,math,base64,hmac
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
VERSION='1.0.0'
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
MUSCLE_MAP=[
 ('Chest',['bench press','chest press','chest fly','chest flye','pec deck','push up','push-up','cable crossover'],{'Triceps':.35,'Shoulders':.25}),
 ('Back',['row','pulldown','pull down','pull-up','pull up','chin-up','chin up','lat pull'],{'Biceps':.35}),
 ('Shoulders',['shoulder press','overhead press','military press'],{'Triceps':.35}),('Shoulders',['lateral raise','front raise','rear delt','face pull','upright row'],{}),
 ('Hamstrings',['leg curl'],{}),
 ('Biceps',['bicep','curl','hammer curl','preacher'],{}),
 ('Triceps',['close-grip dumbbell press','close grip dumbbell press'],{'Chest':.5,'Shoulders':.2}),
 ('Triceps',['skullcrusher','skull crusher'],{}),
 ('Back',['pullover'],{'Chest':.3}),
 ('Back',['shrug'],{}),
 ('Triceps',['tricep','pushdown','push down','overhead extension','dip'],{}),
 ('Quads',['squat','leg press','hack squat','lunge','split squat'],{'Glutes':.4,'Hamstrings':.2}),('Quads',['leg extension'],{}),
 ('Hamstrings',['hamstring','romanian deadlift','rdl','stiff leg'],{'Glutes':.35}),('Glutes',['hip thrust','glute','kickback','bridge'],{}),
 ('Back',['deadlift'],{'Hamstrings':.5,'Glutes':.5}),('Calves',['calf','calves'],{}),('Core',['crunch','plank','ab wheel','sit up','sit-up','leg raise','russian twist'],{})
]
def muscle_targets(name):
 n=name.lower()
 for primary,words,secondary in MUSCLE_MAP:
  if any(word in n for word in words): return [(primary,1.0)]+list(secondary.items())
 return [('Other',1.0)]
def stats(days=90,start_date=None,end_date=None):
 with db() as c: raw=[json.loads(r[0]) for r in c.execute('SELECT payload FROM workouts')]
 # API wins over CSV when title and timestamps match.
 raw.sort(key=lambda w: str(w['id']).startswith('csv-')); seen=set(); workouts=[]
 for w in raw:
  k=(w['title'],stamp(w['start_time']).isoformat(),stamp(w['end_time']).isoformat())
  if k not in seen: seen.add(k); workouts.append(w)
 now=datetime.now(TZ); today=now.date(); monday=today-timedelta(days=today.weekday()); cutoff=today-timedelta(days=days-1); report_end=today
 if start_date or end_date:
  if not start_date or not end_date: raise ValueError('Both dates are required')
  cutoff=datetime.strptime(start_date,'%Y-%m-%d').date(); report_end=datetime.strptime(end_date,'%Y-%m-%d').date()
  if cutoff>report_end or (report_end-cutoff).days>36500: raise ValueError('Invalid date range')
 weekly={}; daily={}; daily_detail={}; exercises={}; muscle_stats={}; muscle_weeks={}; recent=[]; weekdays=[0]*7; hours=[0]*24; months={}; titles={}; prs=[]; total_sets=total_reps=volume=duration=occurrences=0; longest=0
 selected=[w for w in workouts if cutoff<=stamp(w['start_time']).date()<=report_end]
 for w in sorted(selected,key=lambda w:w['start_time']):
  start=stamp(w['start_time']); day=start.date(); week=(day-timedelta(days=day.weekday())).isoformat()
  b=weekly.setdefault(week,{'workouts':0,'sets':0,'volume':0,'minutes':0}); b['workouts']+=1; daily[day.isoformat()]=daily.get(day.isoformat(),0)+1; dd=daily_detail.setdefault(day.isoformat(),{'workouts':0,'sets':0,'volume':0,'minutes':0,'titles':[]}); dd['workouts']+=1; dd['titles'].append(w['title']); weekdays[day.weekday()]+=1; hours[start.hour]+=1
  seconds=max(0,(stamp(w['end_time'])-start).total_seconds()); duration+=seconds; dd['minutes']+=round(seconds/60); month=day.strftime('%Y-%m'); mb=months.setdefault(month,{'workouts':0,'volume':0,'sets':0,'minutes':0}); mb['workouts']+=1; mb['minutes']+=round(seconds/60); titles[w['title']]=titles.get(w['title'],0)+1; b['minutes']+=round(seconds/60); longest=max(longest,seconds); occurrences+=len(w['exercises']); wvol=0
  for e in w['exercises']:
   name=e['title']; targets=muscle_targets(name); primary=targets[0][0]; target_rows=[]
   for muscle,factor in targets:
    ms=muscle_stats.setdefault(muscle,{'muscle':muscle,'sets':0,'reps':0,'volume':0,'sessions':set(),'last_trained':None,'exercises':set(),'exercise_names':set()}); ms['sessions'].add(w['id']); ms['last_trained']=day.isoformat(); ms['exercises'].add(name); ms['exercise_names'].add(name); mw=muscle_weeks.setdefault(week,{}).setdefault(muscle,{'sets':0,'volume':0}); target_rows.append((ms,mw,factor))
   item=exercises.setdefault(name,{'name':name,'sessions':0,'sets':0,'reps':0,'volume':0,'best_weight':0,'e1rm':0,'rep_prs':{},'history':[]}); item['sessions']+=1; best=0; best_e1rm=0; ev=0; session_reps=0; session_sets=0
   for s in e['sets']:
    if s.get('type')=='warmup': continue
    weight=s.get('weight_kg') or 0; reps=s.get('reps') or 0; v=weight*reps
    total_sets+=1; total_reps+=reps; volume+=v; wvol+=v; dd['sets']+=1; dd['volume']+=v; b['sets']+=1; b['volume']+=v; mb['sets']+=1; mb['volume']+=v
    item['sets']+=1; item['reps']+=reps; item['volume']+=v
    for ms,mw,factor in target_rows: ms['sets']+=factor; ms['reps']+=reps*factor; ms['volume']+=v*factor; mw['sets']+=factor; mw['volume']+=v*factor
    best=max(best,weight); ev+=v; session_reps+=reps; session_sets+=1
    if weight>0 and 1<=reps<=12: best_e1rm=max(best_e1rm,weight*(1+reps/30))
    if weight>0 and reps>0:
     bucket=str(int(reps)); old=item['rep_prs'].get(bucket,0)
     if weight>old: item['rep_prs'][bucket]=weight
   old_weight=item['best_weight']; old_e1rm=item['e1rm']; item['best_weight']=max(old_weight,best); item['e1rm']=max(old_e1rm,best_e1rm); item['history'].append({'date':day.isoformat(),'weight':best,'e1rm':round(best_e1rm,1),'volume':ev,'reps':session_reps,'sets':session_sets});
   if best>old_weight and old_weight>0: prs.append({'date':day.isoformat(),'exercise':name,'kind':'Weight PR','value':round(best,1),'unit':'kg'})
   if best_e1rm>old_e1rm and old_e1rm>0: prs.append({'date':day.isoformat(),'exercise':name,'kind':'e1RM PR','value':round(best_e1rm,1),'unit':'kg'})
  recent.append({'id':w['id'],'title':w['title'],'date':start.isoformat(),'exercises':len(w['exercises']),'volume':wvol,'minutes':round(max(0,(stamp(w['end_time'])-start).total_seconds())/60)})
 first=cutoff-timedelta(days=cutoff.weekday()); cursor=first
 while cursor<=report_end:
  weekly.setdefault(cursor.isoformat(),{'workouts':0,'sets':0,'volume':0,'minutes':0}); cursor+=timedelta(days=7)
 active_days=sorted(stamp(w['start_time']).date() for w in selected); streak=best_streak=0; prev=None
 for d in sorted(set(active_days)):
  streak=streak+1 if prev and d==prev+timedelta(days=1) else 1; best_streak=max(best_streak,streak); prev=d
 current_streak=0; d=today
 active_set=set(active_days)
 while d in active_set: current_streak+=1; d-=timedelta(days=1)
 range_days=max(1,(report_end-cutoff).days+1); avg_week=round(len(selected)/max(1,range_days/7),1); avg_sets=round(total_sets/len(selected),1) if selected else 0; avg_volume=round(volume/len(selected)) if selected else 0
 top_day=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'][weekdays.index(max(weekdays))] if selected else '-'; top_hour=hours.index(max(hours)) if selected else 0
 records=sorted([{'name':e['name'],'best_weight':round(e['best_weight'],1),'e1rm':round(e['e1rm'],1),'volume':round(e['volume'])} for e in exercises.values() if e['best_weight']>0],key=lambda x:x['e1rm'],reverse=True)[:10]
 monthly=[{'month':k,**v} for k,v in sorted(months.items())]; top_exercises=sorted([{'name':e['name'],'sessions':e['sessions'],'sets':e['sets'],'volume':round(e['volume'])} for e in exercises.values()],key=lambda x:x['sessions'],reverse=True)[:10]
 workout_types=sorted([{'name':k,'count':v} for k,v in titles.items()],key=lambda x:x['count'],reverse=True)[:8]
 prev_start=cutoff-timedelta(days=range_days); previous=[w for w in workouts if prev_start<=stamp(w['start_time']).date()<cutoff]
 def period_totals(rows):
  v=sets=reps=0
  for ww in rows:
   for ee in ww['exercises']:
    for ss in ee['sets']:
     if ss.get('type')=='warmup': continue
     wt=ss.get('weight_kg') or 0; rp=ss.get('reps') or 0; sets+=1; reps+=rp; v+=wt*rp
  return {'workouts':len(rows),'sets':sets,'reps':round(reps),'volume':round(v)}
 comparison={'current':period_totals(selected),'previous':period_totals(previous)}
 for k in ('workouts','sets','reps','volume'):
  p=comparison['previous'][k]; comparison[k+'_change']=round((comparison['current'][k]-p)/p*100,1) if p else None
 recent28=[w for w in workouts if today-timedelta(days=27)<=stamp(w['start_time']).date()<=today]; recent7=[w for w in workouts if today-timedelta(days=6)<=stamp(w['start_time']).date()<=today]
 load28=period_totals(recent28)['volume']; load7=period_totals(recent7)['volume']; load={'volume_7d':load7,'volume_28d':load28,'ratio':round(load7/(load28/4),2) if load28 else 0}
 insights=[]
 if comparison['volume_change'] is not None: insights.append({'icon':'📈' if comparison['volume_change']>=0 else '📉','title':'Training volume','text':f"{abs(comparison['volume_change'])}% {'higher' if comparison['volume_change']>=0 else 'lower'} than the previous period."})
 if comparison['workouts_change'] is not None: insights.append({'icon':'🔥','title':'Consistency','text':f"{comparison['current']['workouts']} workouts vs {comparison['previous']['workouts']} in the previous period."})
 if records: insights.append({'icon':'🏆','title':'Top estimated strength','text':f"{records[0]['name']} leads at an estimated 1RM of {records[0]['e1rm']} kg."})
 if selected: insights.append({'icon':'⏱','title':'Session length','text':f"Average workout is {round(duration/60/len(selected))} minutes; longest is {round(longest/60)} minutes."})
 if load['ratio']: insights.append({'icon':'🌊','title':'Recent load','text':f"Your last 7 days are {load['ratio']}× the weekly average of the last 28 days."})
 muscles=[]
 for ms in muscle_stats.values():
  last=datetime.fromisoformat(ms['last_trained']).date() if ms['last_trained'] else None; muscles.append({'muscle':ms['muscle'],'sets':round(ms['sets'],1),'reps':round(ms['reps']),'volume':round(ms['volume']),'sessions':len(ms['sessions']),'last_trained':ms['last_trained'],'days_since':(today-last).days if last else None,'exercises':len(ms['exercises']),'exercise_names':sorted(ms['exercise_names'])})
 muscles.sort(key=lambda x:x['sets'],reverse=True)
 muscle_weekly=[{'date':wk,'muscles':{m:{'sets':round(v['sets'],1),'volume':round(v['volume'])} for m,v in vals.items()}} for wk,vals in sorted(muscle_weeks.items())]
 # Calendar always spans the full stored history, independent of the analytics range.
 calendar_detail={}
 for ww in sorted(workouts,key=lambda x:x['start_time']):
  st=stamp(ww['start_time']); dk=st.date().isoformat(); secs=max(0,(stamp(ww['end_time'])-st).total_seconds()); cd=calendar_detail.setdefault(dk,{'workouts':0,'sets':0,'volume':0,'minutes':0,'titles':[],'sessions':[]}); cd['sessions'].append({'id':ww['id'],'title':ww['title']}); cd['workouts']+=1; cd['minutes']+=round(secs/60); cd['titles'].append(ww['title'])
  for ee in ww['exercises']:
   for ss in ee['sets']:
    if ss.get('type')=='warmup': continue
    wt=ss.get('weight_kg') or 0; rp=ss.get('reps') or 0; cd['sets']+=1; cd['volume']+=wt*rp
 # Lifetime journey and useful lifetime records.
 lifetime=period_totals(workouts); lifetime_seconds=sum(max(0,(stamp(w['end_time'])-stamp(w['start_time'])).total_seconds()) for w in workouts)
 lifetime['hours']=round(lifetime_seconds/3600,1); lifetime['first_date']=min((stamp(w['start_time']).date().isoformat() for w in workouts),default=None)
 all_days=sorted(set(stamp(w['start_time']).date() for w in workouts)); life_best=life_streak=0; life_prev=None
 for ld in all_days:
  life_streak=life_streak+1 if life_prev and ld==life_prev+timedelta(days=1) else 1; life_best=max(life_best,life_streak); life_prev=ld
 lifetime['best_streak']=life_best
 # Progress cards compare the first and latest meaningful best weight in the selected range.
 progression=[]
 for e in exercises.values():
  hist=[h for h in e['history'] if h['weight']>0]
  if len(hist)>=2:
   first_w=hist[0]['weight']; last_w=hist[-1]['weight']; change=round((last_w-first_w)/first_w*100,1) if first_w else 0
   progression.append({'name':e['name'],'first':round(first_w,1),'latest':round(last_w,1),'change':change,'history':[{'date':h['date'],'weight':round(h['weight'],1)} for h in hist[-12:]]})
 progression=sorted(progression,key=lambda x:(len(next(e['history'] for e in exercises.values() if e['name']==x['name'])),abs(x['change'])),reverse=True)[:6]
 achievements=[]
 for goal,label in [(1,'First workout'),(10,'10 workouts'),(25,'25 workouts'),(50,'50 workouts'),(100,'100 workouts'),(250,'250 workouts')]: achievements.append({'label':label,'unlocked':len(workouts)>=goal,'progress':min(100,round(len(workouts)/goal*100))})
 for goal,label in [(10000,'10K kg lifted'),(50000,'50K kg lifted'),(100000,'100K kg lifted'),(500000,'500K kg lifted')]: achievements.append({'label':label,'unlocked':lifetime['volume']>=goal,'progress':min(100,round(lifetime['volume']/goal*100))})
 return {'date_range':{'start':cutoff.isoformat(),'end':report_end.isoformat()},'quality':quality_checks(raw),'same_weight':same_weight_progress(selected),'version':VERSION,'status':STATUS.copy(),'week_totals':period_totals([w for w in workouts if monday<=stamp(w['start_time']).date()<=today]),'days':days,'summary':{'workouts':len(selected),'all_time':len(workouts),'this_week':sum(monday<=stamp(w['start_time']).date()<=today for w in workouts),'this_month':sum(stamp(w['start_time']).date().replace(day=1)==today.replace(day=1) for w in workouts),'exercises':len(exercises),'exercise_entries':occurrences,'sets':total_sets,'reps':total_reps,'volume':round(volume),'hours':round(duration/3600,1),'average_minutes':round(duration/60/len(selected)) if selected else 0,'avg_week':avg_week,'avg_sets':avg_sets,'avg_volume':avg_volume,'longest_minutes':round(longest/60),'active_days':len(set(active_days)),'current_streak':current_streak,'best_streak':best_streak,'favorite_day':top_day,'favorite_hour':top_hour},'weekly':[{'date':k,**v} for k,v in sorted(weekly.items())],'daily':daily,'daily_detail':daily_detail,'calendar_detail':calendar_detail,'lifetime':lifetime,'progression':progression,'insights':insights,'muscles':muscles,'muscle_weekly':muscle_weekly,'exercises':sorted(exercises.values(),key=lambda e:e['sessions'],reverse=True),'recent':recent[::-1][:30],'records':records,'weekdays':weekdays,'hours':hours,'monthly':monthly,'top_exercises':top_exercises,'workout_types':workout_types,'achievements':achievements,'comparison':comparison,'load':load,'prs':sorted(prs,key=lambda x:x['date'],reverse=True)[:30]}
def settings(update=None):
 defaults={'workouts':4,'sets':60,'range':90}
 with db() as c:
  c.execute('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY,payload TEXT NOT NULL)')
  row=c.execute('SELECT payload FROM settings WHERE id=1').fetchone(); value={**defaults,**(json.loads(row[0]) if row else {})}
  if update is not None:
   if not isinstance(update,dict) or set(update)-set(defaults): raise ValueError('Unknown settings')
   for key,v in update.items():
    if type(v) is not int or (key=='workouts' and not 1<=v<=30) or (key=='sets' and not 1<=v<=1000) or (key=='range' and v not in (30,90,180,365,3650)): raise ValueError('Invalid setting')
   value.update(update); c.execute('INSERT OR REPLACE INTO settings VALUES (1,?)',(json.dumps(value),))
 return value

def quality_checks(rows):
 issues=[]; seen=set(); duplicates=0
 for w in rows:
  key=(w['title'],stamp(w['start_time']).isoformat(),stamp(w['end_time']).isoformat())
  if key in seen: duplicates+=1
  seen.add(key); minutes=(stamp(w['end_time'])-stamp(w['start_time'])).total_seconds()/60
  reasons=[]
  if minutes<=0 or minutes>240: reasons.append('Duration is zero, negative, or over 4 hours')
  if not w.get('exercises') or not any(e.get('sets') for e in w.get('exercises',[])): reasons.append('No logged sets')
  if stamp(w['start_time'])>datetime.now(TZ): reasons.append('Workout date is in the future')
  if reasons: issues.append({'id':w['id'],'title':w['title'],'date':stamp(w['start_time']).date().isoformat(),'reasons':reasons})
 return {'duplicates':duplicates,'flagged':len(issues),'issues':issues[:50],'checked':len(rows)}

def same_weight_progress(rows):
 grouped={}
 for w in sorted(rows,key=lambda w:stamp(w['start_time'])):
  for e in w['exercises']:
   by_weight={}
   for ss in e['sets']:
    weight=ss.get('weight_kg') or 0; reps=ss.get('reps') or 0
    if ss.get('type')!='warmup' and weight>0 and reps>0: by_weight[weight]=max(by_weight.get(weight,0),reps)
   for weight,reps in by_weight.items():grouped.setdefault((e['title'],weight),{})[w['id']]={'date':stamp(w['start_time']).date().isoformat(),'reps':reps}
 result=[]
 for (name,weight),sessions in grouped.items():
  hist=list(sessions.values())
  if len(hist)>=2:
   first,last=hist[0],hist[-1];result.append({'name':name,'weight':weight,'first_reps':first['reps'],'latest_reps':last['reps'],'change':last['reps']-first['reps'],'first_date':first['date'],'latest_date':last['date'],'sessions':len(hist)})
 return sorted(result,key=lambda x:(x['latest_date'],x['change']),reverse=True)[:30]

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
   try: days=int(parse_qs(u.query).get('days',['90'])[0]); assert days in (30,90,180,365,3650); q=parse_qs(u.query); return self.reply(200,stats(days,q.get('start',[None])[0],q.get('end',[None])[0]))
   except (ValueError,AssertionError): return self.reply(400,{'error':'Invalid date range'})
  if u.path=='/api/settings': return self.reply(200,settings())
  if u.path=='/api/workout':
   wid=parse_qs(u.query).get('id',[''])[0]
   with db() as c: row=c.execute('SELECT payload FROM workouts WHERE id=?',(wid,)).fetchone()
   return self.reply(200,json.loads(row[0])) if row else self.reply(404,{'error':'Workout not found'})
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
  if self.path=='/api/settings':
   try:
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=4096: return self.reply(400,{'error':'Invalid settings size'})
    return self.reply(200,settings(json.loads(self.rfile.read(length))))
   except (ValueError,UnicodeError): return self.reply(400,{'error':'Invalid settings'})
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
