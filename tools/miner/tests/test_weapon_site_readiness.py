from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_weapon_site_readiness import run_weapon_site_readiness  # noqa: E402


class WeaponSiteReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.root / "base"
        self.current = self.root / "current"
        self.reports = self.root / "reports"
        for path in (self.base, self.current, self.reports):
            path.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_uses_game_data_only_and_keeps_candidate_semantics_gated(self):
        weapons_path = self.root / "weapons.json"
        weapons_path.write_text(json.dumps({"weapons": [{
            "blueprint_id": 13231101,
            "item_id": 10231101,
            "prototype_id": 204,
            "name": "AA12",
            "category": "Shotgun",
            "ranged_stats": {
                "rpm": 180,
                "magazine": 8,
                "range_meters": 40,
                "reload_seconds": 2.4,
                "mobility": 50,
                "full_damage_distance": 7.0,
                "minimum_damage_distance": 12.95,
                "minimum_damage_multiplier": 0.1,
                "ammo_item_id": 30150001,
                "projectile_count": 5,
                "accuracy": 45,
                "stability": 45,
            },
            "tiers": [{"tier": 1, "item_id": 10231101, "gun_no": 10230011, "damage": 38, "recipe": {"forge_no": 1}}],
            "blueprint_star_progression": {"stars": [{"blueprint_stars": 1}]},
            "ammo_configuration": {"accessory_slot": 8, "selectable_ammo_item_ids": [30150052]},
            "image_reference": "aa12.png",
            "effect_resolution": {"status": "no-fixed-skill-reference", "fixed_skill_code": ""},
        }]}), encoding="utf-8")

        table = self.current / "game_common" / "data" / "gun_display_data.json"
        table.parent.mkdir(parents=True, exist_ok=True)
        table.write_text(json.dumps({"10230011": {
            "gun_no": 10230011,
            "rarity": 1,
            "reload_score": 33,
        }}), encoding="utf-8")

        corpus = {"weapons": [{
            "blueprint_id": 13231101,
            "exact_corpus_evidence": [{
                "table": "game_common/data/gun_data.json",
                "record_id": "10230011",
                "matched_identity_values": ["10230011"],
                "fields": [
                    {"group": "ads_time", "field": "ads_time", "json_pointer": "/ads_time", "value": 0.23},
                    {"group": "bullet_speed", "field": "bullet_speed", "json_pointer": "/bullet_speed", "value": 200},
                ],
            }],
        }]}

        report = run_weapon_site_readiness(self.base, self.current, weapons_path, self.reports, corpus)
        self.assertEqual(report["record_counts"]["weapons"], 1)
        row = report["weapons"][0]
        self.assertEqual(row["questions"]["damage"]["value"], 38)
        self.assertEqual(row["questions"]["rarity"]["state"], "exact-game-record-located-needs-semantic-proof")
        self.assertEqual(row["questions"]["reload_score"]["state"], "exact-game-record-located-needs-semantic-proof")
        self.assertEqual(row["questions"]["ads_time"]["state"], "exact-game-record-located-needs-semantic-proof")
        self.assertIn("external_sites", report["authority_policy"])
        self.assertTrue((self.reports / "weapon-site-readiness.json").is_file())

    def test_melee_questions_are_not_counted_as_missing_firearm_fields(self):
        weapons_path = self.root / "weapons.json"
        weapons_path.write_text(json.dumps({"weapons": [{
            "blueprint_id": 1,
            "item_id": 2,
            "prototype_id": 3,
            "name": "Blade",
            "category": "Melee",
            "melee_stats": {"attack_range": 2.0},
            "tiers": [{"tier": 1, "damage": 50}],
        }]}), encoding="utf-8")
        report = run_weapon_site_readiness(self.base, self.current, weapons_path, self.reports, {"weapons": []})
        questions = report["weapons"][0]["questions"]
        self.assertEqual(questions["ads_time"]["state"], "not-applicable")
        self.assertEqual(questions["magazine"]["state"], "not-applicable")


if __name__ == "__main__":
    unittest.main()
