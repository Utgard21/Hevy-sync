import unittest,json
from datetime import datetime,timedelta
import app
class ProgressFeatures(unittest.TestCase):
 def setUp(self):
  with app.db() as c:c.execute('DELETE FROM workouts')
 def test_week_totals_and_details(self):
  now=datetime.now(app.TZ);start=now.replace(hour=8,minute=0,second=0,microsecond=0)
  if start>now: start-=timedelta(days=1)
  w={'id':'details-test','title':'Push','start_time':start.isoformat(),'end_time':(start+timedelta(hours=1)).isoformat(),'exercises':[{'title':'Bench Press','sets':[{'type':'normal','weight_kg':20,'reps':10},{'type':'normal','weight_kg':20,'reps':12},{'type':'warmup','weight_kg':10,'reps':5}]}]}
  with app.db() as c:c.execute('INSERT INTO workouts VALUES (?,?,?)',(w['id'],'api',json.dumps(w)))
  s=app.stats(30);self.assertEqual(s['week_totals'],{'workouts':1,'sets':2,'reps':22,'volume':440});self.assertEqual(s['recent'][0]['id'],w['id']);self.assertEqual(s['calendar_detail'][start.date().isoformat()]['sessions'][0]['id'],w['id']);h=s['exercises'][0]['history'][0];self.assertEqual(h['reps'],22);self.assertEqual(h['sets'],2);self.assertEqual(h['volume'],440)

 def test_weekly_streak_survives_rest_day(self):
  now=datetime.now(app.TZ)
  monday=now.date()-timedelta(days=now.weekday())
  app.settings({'workouts':2,'sets':60,'range':90})
  for offset in (7,6,0):
   day=monday-timedelta(days=offset)
   ident='streak-'+day.isoformat()
   self.workout_for_streak(ident,day)
  s=app.stats(90)
  self.assertGreaterEqual(s['summary']['current_streak'],1)

 def workout_for_streak(self,ident,day):
  start=datetime.combine(day,datetime.min.time(),tzinfo=app.TZ).replace(hour=8)
  w={'id':ident,'title':'Training','start_time':start.isoformat(),'end_time':(start+timedelta(hours=1)).isoformat(),'exercises':[{'title':'Bench Press','sets':[{'type':'normal','weight_kg':20,'reps':10}]}]}
  with app.db() as db: db.execute('INSERT INTO workouts VALUES (?,?,?)',(ident,'api',json.dumps(w)))

 def test_weekly_streak_counts_consecutive_completed_weeks(self):
  app.settings({'workouts':2,'sets':60,'range':90})
  today=datetime.now(app.TZ).date(); monday=today-timedelta(days=today.weekday())
  for weeks_back in (1,2):
   base=monday-timedelta(days=7*weeks_back)
   self.workout_for_streak(f'w{weeks_back}a',base)
   self.workout_for_streak(f'w{weeks_back}b',base+timedelta(days=1))
  s=app.stats(90)
  self.assertEqual(s['summary']['current_streak'],2)
  self.assertEqual(s['summary']['best_streak'],2)
  self.assertEqual(s['lifetime']['best_streak'],2)

 def test_weekly_streak_breaks_after_missed_week(self):
  app.settings({'workouts':2,'sets':60,'range':90})
  today=datetime.now(app.TZ).date(); monday=today-timedelta(days=today.weekday())
  base=monday-timedelta(days=14)
  self.workout_for_streak('old-a',base); self.workout_for_streak('old-b',base+timedelta(days=1))
  s=app.stats(90)
  self.assertEqual(s['summary']['current_streak'],0)
  self.assertEqual(s['summary']['best_streak'],1)
