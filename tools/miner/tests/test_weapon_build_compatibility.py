from __future__ import annotations

import sys
import unittest
from pathlib import Path


EXTRACTOR = Path(__file__).resolve().parents[1] / "src" / "extractor"
sys.path.insert(0, str(EXTRACTOR))

from weapon_build_compatibility import _attachment_relation
from combat_resolver import ammo_accessory_code


class WeaponBuildCompatibilityTests(unittest.TestCase):
    def test_explicit_category_produces_compatible_and_incompatible(self):
        attachment = {
            "compatibility_evidence": {
                "all_weapons": False,
                "compatible_weapon_categories": ["Assault Rifle"],
                "named_weapon_text_present": False,
            }
        }
        self.assertEqual("compatible", _attachment_relation({"category": "Assault Rifle", "item_id": 1}, attachment))
        self.assertEqual("incompatible", _attachment_relation({"category": "Pistol", "item_id": 2}, attachment))

    def test_named_text_without_typed_owner_stays_unresolved(self):
        attachment = {
            "compatibility_evidence": {
                "all_weapons": False,
                "compatible_weapon_categories": [],
                "named_weapon_text_present": True,
            }
        }
        self.assertEqual("unresolved", _attachment_relation({"category": "Pistol", "item_id": 2}, attachment))

    def test_typed_item_owner_can_resolve_named_model_relationship(self):
        attachment = {
            "compatible_weapon_item_ids": [20],
            "compatibility_evidence": {
                "all_weapons": False,
                "compatible_weapon_categories": [],
                "named_weapon_text_present": True,
            },
        }
        self.assertEqual("compatible", _attachment_relation({"category": "Pistol", "item_id": 20}, attachment))
        self.assertEqual("incompatible", _attachment_relation({"category": "Pistol", "item_id": 21}, attachment))

    def test_melee_is_not_applicable(self):
        attachment = {"compatibility_evidence": {"all_weapons": True}}
        self.assertEqual("not-applicable", _attachment_relation({"category": "Melee"}, attachment))

    def test_ammo_accessory_prefers_exact_legacy_owner_then_item_map_fallback(self):
        params = {"810_ar_ammo_lv1": {}, "810_nail_ammo_lv0": {}}
        mapping = {"30150394": {"accessory_no": "810_nail_ammo_lv0"}}
        self.assertEqual(
            "810_ar_ammo_lv1",
            ammo_accessory_code("ar_ammo_pack", 1, 30150053, params, mapping),
        )
        self.assertEqual(
            "810_nail_ammo_lv0",
            ammo_accessory_code("nail_ammo_pack", 1, 30150394, params, mapping),
        )


if __name__ == "__main__":
    unittest.main()
