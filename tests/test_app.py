import os,tempfile,unittest,json
from unittest.mock import patch
os.environ['DATA_DIR']=tempfile.mkdtemp()
import app
CSV='title,start_time,end_time,exercise_title,set_type,weight_kg,reps\nPush,"02 Oct 2026, 10:00","02 Oct 2026, 11:00",Bench Press,normal,20,10\nPush,"02 Oct 2026, 10:00","02 Oct 2026, 11:00",Bench Press,warmup,10,5\n'
class Tests(unittest.TestCase):
 def setUp(self):
  with app.db() as c:c.execute('DELETE FROM workouts')
 def save(self,w,source='csv'):
  with app.db() as c:c.execute('INSERT OR REPLACE INTO workouts VALUES (?,?,?)',(w['id'],source,json.dumps(w)))
 def test_csv_and_totals(self):
  w=app.parse_csv(CSV)[0];self.save(w);self.save(w)
  s=app.stats(3650);self.assertEqual(s['summary']['workouts'],1);self.assertEqual(s['summary']['sets'],1);self.assertEqual(s['summary']['volume'],200);self.assertEqual(s['summary']['reps'],10)
 def test_duplicate_sources(self):
  w=app.parse_csv(CSV)[0];self.save(w);w['id']='api-id';self.save(w,'api');self.assertEqual(app.stats(3650)['summary']['workouts'],1)
 def test_failed_sync_preserves_cache(self):
  w=app.parse_csv(CSV)[0];self.save(w,'api')
  with patch.object(app,'KEY','key'),patch.object(app,'fetch',side_effect=ValueError()):app.sync()
  self.assertEqual(app.stats(3650)['summary']['all_time'],1);self.assertFalse(app.STATUS['syncing']);self.assertIsNotNone(app.STATUS['error'])
 def test_sync_removes_deleted_api_keeps_csv(self):
  w=app.parse_csv(CSV)[0];self.save(w);w['id']='api';self.save(w,'api')
  with patch.object(app,'KEY','key'),patch.object(app,'fetch',return_value=[]):app.sync()
  with app.db() as c:self.assertEqual(c.execute('SELECT source FROM workouts').fetchall(),[('csv',)])
 def test_bad_csv(self):
  with self.assertRaises(ValueError):app.parse_csv('bad,columns\n1,2')
 def test_timezone(self):
  self.assertEqual(app.stamp('2026-10-01T22:30:00Z').date().isoformat(),'2026-10-02')
if __name__=='__main__':unittest.main()
