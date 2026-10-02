import unittest,json
from datetime import datetime,timedelta
import app
class ProgressFeatures(unittest.TestCase):
 def setUp(self):
  with app.db() as c:c.execute('DELETE FROM workouts')
 def test_week_totals_and_details(self):
  now=datetime.now(app.TZ);start=now.replace(hour=8,minute=0,second=0,microsecond=0)
  w={'id':'details-test','title':'Push','start_time':start.isoformat(),'end_time':(start+timedelta(hours=1)).isoformat(),'exercises':[{'title':'Bench Press','sets':[{'type':'normal','weight_kg':20,'reps':10},{'type':'normal','weight_kg':20,'reps':12},{'type':'warmup','weight_kg':10,'reps':5}]}]}
  with app.db() as c:c.execute('INSERT INTO workouts VALUES (?,?,?)',(w['id'],'api',json.dumps(w)))
  s=app.stats(30);self.assertEqual(s['week_totals'],{'workouts':1,'sets':2,'reps':22,'volume':440});self.assertEqual(s['recent'][0]['id'],w['id']);self.assertEqual(s['calendar_detail'][start.date().isoformat()]['sessions'][0]['id'],w['id']);h=s['exercises'][0]['history'][0];self.assertEqual(h['reps'],22);self.assertEqual(h['sets'],2);self.assertEqual(h['volume'],440)
