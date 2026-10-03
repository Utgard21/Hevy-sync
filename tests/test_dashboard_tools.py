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

 def test_long_workout_is_flagged_but_sets_are_preserved(self):
  good=self.workout('good','2026-09-01')
  long={**good,'id':'long','start_time':'2026-09-02T08:00:00+03:00','end_time':'2026-09-02T14:00:00+03:00'}
  with app.db() as db: db.execute('INSERT INTO workouts VALUES (?,?,?)',('long','api',json.dumps(long)))
  s=app.stats(3650)
  self.assertEqual(s['summary']['workouts'],2); self.assertEqual(s['summary']['volume'],400)
  self.assertEqual(s['analytics_excluded'],0); self.assertEqual(s['quality']['flagged'],1)

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

 def test_data_confidence_does_not_invent_volume(self):
  w=self.workout('coverage','2026-10-01')
  w['exercises'][0]['sets']=[{'type':'normal','weight_kg':20,'reps':10},{'type':'normal','weight_kg':None,'reps':15},{'type':'normal','duration_seconds':60,'weight_kg':None,'reps':None}]
  with app.db() as db: db.execute('UPDATE workouts SET payload=? WHERE id=?',(json.dumps(w),'coverage'))
  s=app.stats(3650); d=s['data_confidence']
  self.assertEqual(s['summary']['volume'],200)
  self.assertEqual(d['working_sets'],3)
  self.assertEqual(d['weighted_sets'],1)
  self.assertEqual(d['reps_only_sets'],1)
  self.assertEqual(d['duration_sets'],1)
  self.assertAlmostEqual(d['volume_coverage_pct'],33.3)

 def test_reps_only_exercise_uses_rep_metrics_without_fake_weight(self):
  w=self.workout('pushups','2026-10-01'); w['exercises']=[{'title':'Push Ups','sets':[{'type':'normal','weight_kg':None,'reps':20},{'type':'normal','weight_kg':None,'reps':25}]}]
  with app.db() as db: db.execute('UPDATE workouts SET payload=? WHERE id=?',(json.dumps(w),'pushups'))
  e=app.stats(3650)['exercises'][0]
  self.assertEqual(e['measurement_type'],'reps'); self.assertEqual(e['best_reps'],25); self.assertEqual(e['best_weight'],0); self.assertEqual(e['volume'],0)

 def test_treadmill_uses_recorded_distance_and_time(self):
  w=self.workout('treadmill','2026-10-01'); w['exercises']=[{'title':'Treadmill','sets':[{'type':'normal','distance_meters':3000,'duration_seconds':1800,'weight_kg':None,'reps':None}]}]
  with app.db() as db: db.execute('UPDATE workouts SET payload=? WHERE id=?',(json.dumps(w),'treadmill'))
  e=app.stats(3650)['exercises'][0]
  self.assertEqual(e['measurement_type'],'mixed'); self.assertEqual(e['total_distance_meters'],3000); self.assertEqual(e['total_duration_seconds'],1800); self.assertEqual(e['pace_seconds_per_km'],600); self.assertEqual(e['volume'],0)

 def test_routine_volume_uses_only_recorded_weighted_sets(self):
  w=self.workout('routine','2026-10-01'); w['title']='Push Day'; w['exercises'][0]['sets']=[{'type':'normal','weight_kg':50,'reps':10},{'type':'normal','weight_kg':None,'reps':20}]
  with app.db() as db: db.execute('UPDATE workouts SET payload=? WHERE id=?',(json.dumps(w),'routine'))
  r=next(x for x in app.stats(3650)['workout_types'] if x['name']=='Push Day')
  self.assertEqual(r['volume'],500); self.assertEqual(r['weighted_sets'],1)

 def test_hevy_template_muscles_override_name_fallback(self):
  w=self.workout('meta','2026-10-01'); w['exercises'][0]['title']='Unknown Move'; w['exercises'][0]['exercise_template_id']='tpl-1'
  with app.db() as db:
   db.execute('UPDATE workouts SET payload=? WHERE id=?',(json.dumps(w),'meta'))
   db.execute('INSERT OR REPLACE INTO exercise_templates VALUES (?,?)',('tpl-1',json.dumps({'id':'tpl-1','primary_muscle_group':'chest','secondary_muscle_groups':['shoulders']})))
  s=app.stats(3650); e=s['exercises'][0]
  self.assertEqual(e['muscle_source'],'hevy')
  self.assertTrue(any(m['muscle']=='Chest' for m in s['muscles']))
  self.assertFalse(any(m['muscle']=='Other' for m in s['muscles']))

 def test_pace_requires_paired_distance_and_duration(self):
  w=self.workout('paired','2026-10-01'); w['exercises']=[{'title':'Treadmill','sets':[{'type':'normal','distance_meters':3000},{'type':'normal','duration_seconds':1800}]}]
  with app.db() as db: db.execute('UPDATE workouts SET payload=? WHERE id=?',(json.dumps(w),'paired'))
  e=app.stats(3650)['exercises'][0]
  self.assertEqual(e['measurement_type'],'mixed'); self.assertIsNone(e['pace_seconds_per_km'])

 def test_mixed_weighted_and_reps_only_is_not_forced_to_weighted(self):
  w=self.workout('mixed','2026-10-01'); w['exercises']=[{'title':'Push Ups','sets':[{'type':'normal','weight_kg':10,'reps':10},{'type':'normal','reps':20}]}]
  with app.db() as db: db.execute('UPDATE workouts SET payload=? WHERE id=?',(json.dumps(w),'mixed'))
  e=app.stats(3650)['exercises'][0]
  self.assertEqual(e['measurement_type'],'mixed'); self.assertTrue(e['measurement_mixed']); self.assertEqual(e['volume'],100)

 def test_invalid_cardio_measurements_are_rejected(self):
  w=self.workout('badcardio','2026-10-01'); w['exercises'][0]['sets']=[{'type':'normal','duration_seconds':-1,'distance_meters':1000}]
  with self.assertRaises(ValueError): app.validate(w)

 def test_pure_cardio_does_not_create_muscle_stimulus(self):
  w=self.workout('cardio-muscle','2026-10-01'); w['exercises']=[{'title':'Mystery Cardio','exercise_template_id':'cardio-tpl','sets':[{'type':'normal','distance_meters':3000,'duration_seconds':1800}]}]
  with app.db() as db:
   db.execute('UPDATE workouts SET payload=? WHERE id=?',(json.dumps(w),'cardio-muscle'))
   db.execute('INSERT OR REPLACE INTO exercise_templates VALUES (?,?)',('cardio-tpl',json.dumps({'id':'cardio-tpl','primary_muscle_group':'quads'})))
  s=app.stats(3650)
  self.assertFalse(any(m['sets']>0 for m in s['muscles']))

 def test_cardio_summary_exposes_recorded_measurements(self):
  w=self.workout('cardio-summary','2026-10-01'); w['exercises']=[{'title':'Treadmill','sets':[{'type':'normal','distance_meters':3000,'duration_seconds':1800}]}]
  with app.db() as db: db.execute('UPDATE workouts SET payload=? WHERE id=?',(json.dumps(w),'cardio-summary'))
  s=app.stats(3650); row=next(x for x in s['cardio'] if x['name']=='Treadmill')
  self.assertEqual(row['distance_meters'],3000); self.assertEqual(row['duration_seconds'],1800); self.assertEqual(row['pace_seconds_per_km'],600)

 def test_hevy_secondary_muscles_are_not_fractional_guesses(self):
  w=self.workout('secondary','2026-10-01'); w['exercises'][0]['exercise_template_id']='tpl-secondary'
  with app.db() as db:
   db.execute('UPDATE workouts SET payload=? WHERE id=?',(json.dumps(w),'secondary'))
   db.execute('INSERT OR REPLACE INTO exercise_templates VALUES (?,?)',('tpl-secondary',json.dumps({'id':'tpl-secondary','primary_muscle_group':'chest','secondary_muscle_groups':['shoulders']})))
  muscles={m['muscle']:m for m in app.stats(3650)['muscles']}
  self.assertEqual(muscles['Chest']['sets'],1); self.assertEqual(muscles['Shoulders']['sets'],1)

 def test_timed_resistance_counts_muscle_without_inventing_reps(self):
  w=self.workout('plank','2026-10-01'); w['exercises']=[{'title':'Plank','sets':[{'type':'normal','duration_seconds':60}]}]
  with app.db() as db: db.execute('UPDATE workouts SET payload=? WHERE id=?',(json.dumps(w),'plank'))
  s=app.stats(3650); core=next(m for m in s['muscles'] if m['muscle']=='Core')
  self.assertEqual(core['sets'],1); self.assertEqual(core['reps'],0); self.assertEqual(core['volume'],0)

 def test_distance_and_duration_are_both_recorded_in_confidence(self):
  w=self.workout('cardio-both','2026-10-01'); w['exercises']=[{'title':'Treadmill','sets':[{'type':'normal','distance_meters':1000,'duration_seconds':600}]}]
  with app.db() as db: db.execute('UPDATE workouts SET payload=? WHERE id=?',(json.dumps(w),'cardio-both'))
  d=app.stats(3650)['data_confidence']; self.assertEqual(d['distance_sets'],1); self.assertEqual(d['duration_sets'],1)

 def test_same_weight_normalizes_hyphenated_exercise_names(self):
  a=self.workout('norm-a','2026-09-01',10); b=self.workout('norm-b','2026-09-02',12); b['exercises'][0]['title']='Bench-Press'
  with app.db() as db: db.execute('UPDATE workouts SET payload=? WHERE id=?',(json.dumps(b),'norm-b'))
  p=app.same_weight_progress([a,b]); self.assertEqual(len(p),1); self.assertEqual(p[0]['change'],2)
