import importlib.util,json,marshal,tempfile,types,unittest
from pathlib import Path
from dead_signal_consumer_index import ConsumerIndex,inspect_pyc,run_consumer_index
class ConsumerIndexTests(unittest.TestCase):
 def setUp(self): self.t=tempfile.TemporaryDirectory(); self.root=Path(self.t.name); self.base=self.root/'b'; self.current=self.root/'c'; self.base.mkdir(); self.current.mkdir(); self.reports=self.root/'reports'
 def tearDown(self): self.t.cleanup()
 def pyc(self,root,name,source):
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(importlib.util.MAGIC_NUMBER+b'\0'*12+marshal.dumps(compile(source,name,'exec')));return p
 def test_code_scope_cooccurrence_and_child_relationships(self):
  self.pyc(self.base,'x.pyc','def outer():\n def inner():\n  return cradle_override_entry + gun_type\n return inner\n')
  result=run_consumer_index(self.base,self.current,self.root,self.reports); idx=ConsumerIndex(result['database']); rows=idx.find_scopes(['cradle_override_entry','gun_type']); self.assertEqual(1,len(rows)); self.assertIn('inner',rows[0]['qualname'])
 def test_cache_reuse_and_change_invalidation(self):
  p=self.pyc(self.base,'x.pyc','VALUE="prototype_desc"'); a=run_consumer_index(self.base,self.current,self.root,self.reports); b=run_consumer_index(self.base,self.current,self.root,self.reports); self.assertEqual(1,a['cache_statistics']['pycs_reindexed']); self.assertEqual(1,b['cache_statistics']['pycs_reused']); p.write_bytes(b'bad prototype_desc pyc'); c=run_consumer_index(self.base,self.current,self.root,self.reports); self.assertEqual(1,c['cache_statistics']['pycs_reindexed']); self.assertEqual(1,c['cache_statistics']['fallback_files'])
 def test_invalid_pyc_falls_back_to_raw_tokens(self):
  info=inspect_pyc(b'bad default_shoot_mode ShootMode'); self.assertFalse(info['marshal_compatible']); self.assertIn('ShootMode',info['raw_tokens'])
if __name__=='__main__':unittest.main()
