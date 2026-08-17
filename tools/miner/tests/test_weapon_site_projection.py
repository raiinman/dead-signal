from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_weapon_site_projection import build_weapon_site_projection  # noqa: E402


class WeaponSiteProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.published = self.root / "published"
        self.weapons_path = self.published / "data" / "weapons.json"
        self.weapons_path.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_promotes_tier_one_gun_fields_and_publishes_lean_payload(self):
        weapons = {
            "weapons": [
                {
                    "blueprint_id": 13231101,
                    "item_id": 10231101,
                    "prototype_id": 204,
                    "name": "AA12",
                    "category": "Shotgun",
                    "quality_code": 2,
                    "quality": "Rare",
                    "short_description": "Installed description",
                    "ranged_stats": {"bullet_pattern_id": "PatShared", "projectile_count": 5, "rpm": 180, "magazine": 8},
                    "blueprint_star_progression": {"stars": [1, 2, 3, 4, 5, 6], "perk_slot_calibration_max": 2},
                    "tiers": [
                        {"tier": 1, "item_id": 10231101, "gun_no": 10230011, "damage": 38, "recipe": {"forge_no": 1}},
                        {"tier": 2, "item_id": 10231102, "gun_no": 10230012, "damage": 59},
                    ],
                },
                {
                    "blueprint_id": 13231201,
                    "item_id": 10231201,
                    "prototype_id": 204,
                    "name": "AA12 Variant",
                    "category": "Shotgun",
                    "quality_code": 3,
                    "quality": "Epic",
                    "ranged_stats": {"bullet_pattern_id": "PatShared", "projectile_count": 5},
                    "tiers": [{"tier": 1, "item_id": 10231201, "gun_no": 10230021, "damage": 40}],
                },
            ]
        }
        self.weapons_path.write_text(json.dumps(weapons), encoding="utf-8")
        fields = [
            {"group": "ads_time", "field": "ads_time", "json_pointer": "/ads_time", "value": 0.2325},
            {"group": "bullet_speed", "field": "bullet_speed", "json_pointer": "/bullet_speed", "value": 200.0},
            {"group": "firing_mode", "field": "default_shoot_mode", "json_pointer": "/default_shoot_mode", "value": 3},
            {"group": "firing_mode", "field": "burst_bullet_num", "json_pointer": "/burst_bullet_num", "value": 0},
            {"group": "reload", "field": "reload_loop_affix_value", "json_pointer": "/reload_loop_affix_value", "value": 33},
            {"group": "reload", "field": "reload_loop_time", "json_pointer": "/reload_loop_time", "value": 2.4},
            {"group": "magazine", "field": "weapon_magazine_size_affix_value", "json_pointer": "/weapon_magazine_size_affix_value", "value": 8},
            {"group": "mobility", "field": "weapon_mobility", "json_pointer": "/weapon_mobility", "value": 50},
            {"group": "range", "field": "weapon_range_affix_value", "json_pointer": "/weapon_range_affix_value", "value": 7},
            {"group": "range", "field": "weapon_range_value", "json_pointer": "/weapon_range_value", "value": 40},
            {"group": "fire_rate", "field": "weapon_rpm_affix_value", "json_pointer": "/weapon_rpm_affix_value", "value": 180},
            {"group": "fire_rate", "field": "weapon_rpm", "json_pointer": "/weapon_rpm", "value": 97.75},
        ]
        corpus = {
            "weapons": [
                {
                    "blueprint_id": 13231101,
                    "exact_corpus_evidence": [{
                        "layer": "current",
                        "table": "game_common/data/gun_base_params_data.json",
                        "record_id": "10230011",
                        "matched_identity_values": ["10230011"],
                        "evidence_scope": "variant-local",
                        "precedence": 2,
                        "fields": fields,
                    }],
                },
                {
                    "blueprint_id": 13231201,
                    "exact_corpus_evidence": [{
                        "layer": "current",
                        "table": "game_common/data/bullet_pattern_data.json",
                        "record_id": "PatShared",
                        "matched_identity_values": ["PatShared"],
                        "evidence_scope": "family-shared",
                        "precedence": 1,
                        "fields": [{"group": "projectiles", "field": "bullet_num", "value": 5}],
                    }],
                },
            ]
        }
        readiness = {
            "weapons": [
                {"blueprint_id": 13231101, "questions": {"rarity": {"state": "unresolved"}}, "enhancements": {}},
                {"blueprint_id": 13231201, "questions": {}, "enhancements": {}},
            ]
        }
        report = build_weapon_site_projection(self.weapons_path, self.published, corpus, readiness)
        self.assertEqual(report["record_counts"]["weapons"], 2)
        self.assertEqual(report["record_counts"]["gun_base_promoted"], 1)
        self.assertEqual(report["record_counts"]["rarity_promoted"], 2)
        aa12 = report["weapons"][0]
        self.assertEqual(aa12["handling"]["semantic"]["ads_time"], 0.2325)
        self.assertEqual(aa12["handling"]["semantic"]["bullet_speed"], 200.0)
        self.assertEqual(aa12["handling"]["semantic"]["reload_score"], 33)
        self.assertEqual(aa12["handling"]["semantic"]["fire_rate_display_rpm"], 180)
        self.assertEqual(aa12["firing_mode"]["raw_code"], 3)
        self.assertEqual(aa12["firing_mode"]["label_state"], "unresolved-code-map")
        self.assertEqual(aa12["rarity"]["label"], "Rare")
        self.assertEqual(aa12["family"]["family_id"], "prototype:204")
        self.assertEqual(len(aa12["family"]["members"]), 2)
        self.assertEqual(aa12["ballistic_family"]["bullet_pattern_id"], "PatShared")
        variant = report["weapons"][1]
        self.assertEqual(variant["handling"]["state"], "unresolved")

        forensic = self.published / "site" / "weapons-v2.json"
        lean = self.published / "site" / "weapons.json"
        evidence = self.published / "site" / "weapon-evidence.json"
        self.assertTrue(forensic.is_file())
        self.assertTrue(lean.is_file())
        self.assertTrue(evidence.is_file())
        lean_payload = json.loads(lean.read_text(encoding="utf-8"))
        self.assertEqual(lean_payload["weapons"][0]["rarity"]["label"], "Rare")
        self.assertEqual(lean_payload["weapons"][0]["stats"]["ads_time"], 0.2325)
        self.assertNotIn("research", lean_payload["weapons"][0]["firing_mode"])
        self.assertEqual(report["browser_publish"]["record_counts"]["rarity"], 2)


if __name__ == "__main__":
    unittest.main()
