import json,tempfile,unittest
from pathlib import Path
from dead_signal_reference_graph import ReferenceGraph,seed_weapon_graph
class ReferenceGraphTests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.db=Path(self.t.name)/'g.sqlite';self.g=ReferenceGraph(self.db);self.g.initialize()
 def tearDown(self):self.t.cleanup()
 def test_candidate_and_proven_are_distinct_and_queryable(self):
  common=dict(source_table='a',source_record_id='1',source_field='skill_list',source_value=['WS1'],source_layer='base',target_table='b',target_record_id='WS1',relationship_kind='skill',scope='variant-local',role='owner',provenance={},parent_field_path='/skill_list/0')
  self.g.add_edge(proof_state='structural-candidate',**common);self.assertEqual([],self.g.query(min_proof='typed-relationship-proven'));self.g.add_edge(proof_state='typed-relationship-proven',**common);self.assertEqual(1,len(self.g.query(min_proof='typed-relationship-proven')));self.assertEqual('/skill_list/0',self.g.query()[0]['parent_field_path'])
 def test_weapon_seeds_are_typed_and_no_bare_scalar_edges(self):
  count=seed_weapon_graph(self.g,[{'blueprint_id':10,'item_id':20,'prototype_id':30,'ranged_stats':{'bullet_pattern_id':'Pat1','projectile_count':5},'tiers':[{'tier':1,'item_id':20,'gun_no':40}]}]);self.assertEqual(4,count);self.assertTrue(all(r['proof_state']!='structural-candidate' for r in self.g.query()));self.assertEqual([],self.g.query(target_record_id='5'))
 def test_rejected_edge_never_satisfies_proven_query(self):
  self.g.add_edge(source_table='a',source_record_id='1',source_field='value',source_value=7,source_layer='base',target_table='x',target_record_id='7',relationship_kind='scalar-collision',proof_state='rejected',scope='global',role='reference',provenance={});self.assertEqual([],self.g.query(min_proof='typed-relationship-proven'))
if __name__=='__main__':unittest.main()
