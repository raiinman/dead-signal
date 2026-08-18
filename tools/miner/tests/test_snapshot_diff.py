import json,tempfile,unittest
from pathlib import Path
from dead_signal_consumer_index import run_consumer_index
from dead_signal_snapshot_diff import build_snapshot_diff,structured_diff
from dead_signal_table_registry import run_table_registry
class SnapshotDiffTests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);self.b=self.root/'b';self.c=self.root/'c';self.b.mkdir();self.c.mkdir();self.r=self.root/'reports'
 def tearDown(self):self.t.cleanup()
 def write(self,root,name,value):p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value),encoding='utf-8')
 def test_record_and_field_diff(self):
  self.write(self.b,'x.json',{'data':{'1':{'a':1,'gone':2},'2':{'a':2}}});self.write(self.c,'x.json',{'data':{'1':{'a':3,'new':4},'3':{'a':3}}});d=structured_diff(self.b/'x.json',self.c/'x.json');self.assertEqual({'base':2,'current':2,'added':1,'removed':1,'changed':1},d['record_counts']);self.assertEqual({'a','gone','new'},{x['field'] for x in d['changed_records'][0]['fields']})
 def test_registry_backed_diff_and_patch_absence_policy(self):
  self.write(self.b,'client_data/bullet_pattern_data.json',{'data':{'Pat':{'bullet_num':1}}});self.write(self.c,'client_data/bullet_pattern_data.json',{'data':{'Pat':{'bullet_num':5}}});self.write(self.b,'base_only.json',{'data':{'1':{}}});run_table_registry(self.b,self.c,self.root,self.r);run_consumer_index(self.b,self.c,self.root,self.r);report=build_snapshot_diff(self.b,self.c,self.root,self.r);self.assertEqual(1,report['table_counts']['changed']);self.assertEqual(1,report['table_counts']['removed_or_patch_absent']);self.assertIn('projectile_count',report['affected_semantic_definitions']);self.assertIn('never asserted',report['policy'])
if __name__=='__main__':unittest.main()
