from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "extractor" / "weapon_reference_filter.py"
SPEC = importlib.util.spec_from_file_location("weapon_reference_filter", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class WeaponReferenceFilterTests(unittest.TestCase):
    def test_explicit_mechanic_identifiers_are_kept(self):
        for field in (
            "passive_skill_code",
            "buff_id",
            "keyword_status_id",
            "logic_tree_ref",
            "behavior_ref",
            "ability_id",
            "effect_id",
            "trigger_ref",
        ):
            with self.subTest(field=field):
                self.assertTrue(MODULE.is_mechanic_reference_field(field))

    def test_numeric_parameter_fields_are_not_mechanic_references(self):
        for field in (
            "effect_index",
            "ads_fly_sfx_trigger_dis",
            "trigger_checker",
            "trigger_op",
            "buff_duration_seconds",
            "effect_scale",
        ):
            with self.subTest(field=field):
                self.assertFalse(MODULE.is_mechanic_reference_field(field))


if __name__ == "__main__":
    unittest.main()
