import unittest
from dead_signal_family_registry import inherit
from dead_signal_promotion_engine import promote
from dead_signal_semantic_registry import get_semantic
class SemanticPromotionTests(unittest.TestCase):
 def test_proof_requirements_are_structured(self):
  blocked=promote('firing_mode',raw_value=3,evidence={'exact-owner-record'},scope='variant-local');self.assertEqual('unresolved',blocked['state']);self.assertIn('static-enum',blocked['reasons_not_promoted'][0]);ok=promote('firing_mode',raw_value=3,evidence={'exact-owner-record','static-enum'},scope='variant-local');self.assertEqual(3,ok['value'])
 def test_similarly_named_field_does_not_promote(self):
  result=promote('reload_score',raw_value=None,evidence={'exact-owner-record'},scope='variant-local');self.assertEqual('unresolved',result['state']);self.assertIsNone(result['value'])
 def test_variant_local_overrides_family_and_leakage_is_rejected(self):
  self.assertEqual(8,inherit('bullet-pattern','projectile_count',local=8,shared=5)['value']);self.assertFalse(inherit('bullet-pattern','ads_time',shared=.2)['accepted']);self.assertFalse(inherit('shared-prototype','special_skill',shared='x')['accepted'])
 def test_registry_keeps_raw_display_and_owner_metadata(self):
  definition=get_semantic('fire_rate_display_rpm');self.assertEqual('tier_one_gun',definition.owner_type);self.assertEqual('display',definition.raw_display)
if __name__=='__main__':unittest.main()
