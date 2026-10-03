import unittest,json
from datetime import datetime,timedelta
import app
class DashboardTools(unittest.TestCase):
 def setUp(self):
  with app.db() as c:c.execute('DELETE FROM workouts')
  app.settings({'workouts':4,'sets':60,'range':90})
 def workout(self,ident,date,reps=10):
  w={'id':ident,'title':'Push','start_time':date+'T08:00:00+03:00','end_time':date+'T09:00:00+03:00','exercises':[{'title':'Bench Press','sets':[{'type':'normal','weight_kg':20,'reps':reps},{'type':'warmup','weight_kg':20,'reps':30}]}]}
  with app.db() as c:c.execute('INSERT INTO workouts VALUES (?,?,?)',(ident,'api',json.dumps(w)))
  return w
 def test_custom_range_boundaries(self):
  self.workout('a','2026-09-01');self.workout('b','2026-09-02');self.workout('c','2026-09-03')
  s=app.stats(90,'2026-09-02','2026-09-02');self.assertEqual(s['summary']['workouts'],1);self.assertEqual(s['summary']['volume'],200);self.assertEqual(s['date_range']['end'],'2026-09-02')
  with self.assertRaises(ValueError):app.stats(90,'2026-09-03','2026-09-01')
 def test_settings_persist_and_validate(self):
  app.settings({'workouts':5,'sets':70,'range':180});self.assertEqual(app.settings()['sets'],70)
  for bad in [{'sets':0},{'workouts':31},{'range':3},{'sets':True},{'unknown':2}]:
   with self.assertRaises(ValueError):app.settings(bad)
  self.assertEqual(app.settings()['sets'],70)
 def test_same_weight_excludes_warmups(self):
  a=self.workout('a','2026-09-01',10);b=self.workout('b','2026-09-02',12);p=app.same_weight_progress([b,a]);self.assertEqual(p[0]['change'],2);self.assertEqual(p[0]['latest_reps'],12)
 def test_quality_duplicate_and_empty(self):
  a=self.workout('a','2026-09-01');b={**a,'id':'b'};empty={**a,'id':'c','title':'Empty','exercises':[]};q=app.quality_checks([a,b,empty]);self.assertEqual(q['duplicates'],1);self.assertEqual(q['flagged'],1);self.assertEqual(q['issues'][0]['id'],'c')

 def test_invalid_workout_excluded_from_analytics(self):
  good=self.workout('good','2026-09-01')
  bad={**good,'id':'bad','start_time':'2026-09-02T08:00:00+03:00','end_time':'2026-09-02T14:00:00+03:00'}
  with app.db() as db: db.execute('INSERT INTO workouts VALUES (?,?,?)',('bad','api',json.dumps(bad)))
  s=app.stats(3650)
  self.assertEqual(s['summary']['workouts'],1)
  self.assertEqual(s['analytics_excluded'],1)

 def test_load_ratio_requires_enough_sessions(self):
  self.workout('only','2026-10-01')
  s=app.stats(3650)
  self.assertFalse(s['load']['available'])
  self.assertIsNone(s['load']['ratio'])

 def test_exercise_names_are_normalized(self):
  a=self.workout('a','2026-09-01'); b=self.workout('b','2026-09-02')
  b['exercises'][0]['title']='Bench-Press'
  with app.db() as db: db.execute('UPDATE workouts SET payload=? WHERE id=?',(json.dumps(b),'b'))
  s=app.stats(3650)
  self.assertEqual(len(s['exercises']),1)
