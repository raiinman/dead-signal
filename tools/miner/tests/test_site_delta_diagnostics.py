import tempfile,unittest
from pathlib import Path
from unittest import mock
from dead_signal_self_diagnostics import apply_publication_blocks,build_self_diagnostics
from dead_signal_site_delta import build_site_delta
class SiteDeltaDiagnosticsTests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
 def tearDown(self):self.t.cleanup()
 def test_site_delta_names_semantics_without_full_records(self):
  before={'weapons':[{'blueprint_id':1,'name':'A','stats':{'ads_time':1}},{'blueprint_id':2,'name':'B'}]};after={'weapons':[{'blueprint_id':1,'name':'A','stats':{'ads_time':2}},{'blueprint_id':3,'name':'C'}]};r=build_site_delta(before,after,self.root/'site-delta.json');self.assertEqual({'added':1,'removed_or_unpublished':1,'changed':1},r['record_counts']);self.assertEqual(['promoted_stats'],r['changed'][0]['semantic_fields']);self.assertNotIn('weapons',r)
 def test_diagnostic_blocker_suppresses_only_affected_field(self):
  duplicate=tuple(list(__import__('dead_signal_self_diagnostics').DEFINITIONS)+[__import__('dead_signal_self_diagnostics').DEFINITIONS[0]])
  projection={'weapons':[{'handling':{'semantic':{'ads_time':1,'bullet_speed':2}},'ranged_stats':{'projectile_count':5}}]}
  with mock.patch('dead_signal_self_diagnostics.DEFINITIONS',duplicate):report=build_self_diagnostics(self.root,projection,self.root)
  self.assertIn('ads_time',report['publication_blocked_fields']);apply_publication_blocks(projection,report['publication_blocked_fields']);self.assertNotIn('ads_time',projection['weapons'][0]['handling']['semantic']);self.assertEqual(2,projection['weapons'][0]['handling']['semantic']['bullet_speed'])
if __name__=='__main__':unittest.main()
