from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "extractor" / "weapon_typed_seed_trace.py"
SPEC = importlib.util.spec_from_file_location("weapon_typed_seed_trace", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class WeaponTypedSeedTraceTests(unittest.TestCase):
    def test_prototype_seed_requires_prototype_field_or_table(self):
        self.assertTrue(MODULE._field_matches_kind("prototype_id", "prototype_id"))
        self.assertFalse(MODULE._field_matches_kind("buff_id", "prototype_id"))
        self.assertFalse(MODULE._field_matches_kind("effect_index", "prototype_id"))
        self.assertTrue(MODULE._record_id_matches_kind("game_common/data/weapon_prototype_data.json", "prototype_id"))
        self.assertFalse(MODULE._record_id_matches_kind("game_common/data/logic_tree/behavior_test.json", "prototype_id"))

    def test_identity_kinds_do_not_cross_match_numeric_fields(self):
        self.assertTrue(MODULE._field_matches_kind("gun_no", "gun_no"))
        self.assertFalse(MODULE._field_matches_kind("buff_id", "gun_no"))
        self.assertTrue(MODULE._field_matches_kind("gun_item_no", "item_id"))
        self.assertFalse(MODULE._field_matches_kind("prototype_no", "item_id"))
        self.assertTrue(MODULE._field_matches_kind("blueprint_id", "blueprint_id"))
        self.assertFalse(MODULE._field_matches_kind("status_id", "blueprint_id"))


if __name__ == "__main__":
    unittest.main()
