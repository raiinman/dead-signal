from __future__ import annotations

import importlib.util
import json
import marshal
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_weapon_corpus_audit import run_weapon_corpus_audit  # noqa: E402


class WeaponCorpusAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.root / "base"
        self.current = self.root / "current"
        self.reports = self.root / "reports"
        self.source = self.root / "source"
        for path in (self.base, self.current, self.reports, self.source):
            path.mkdir(parents=True, exist_ok=True)
        for snapshot in (self.base, self.current):
            (snapshot / "snapshot.json").write_text(json.dumps({"source_root": str(self.source)}), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def _write_pyc(self, relative: str, source: str) -> None:
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        code = compile(source, relative, "exec")
        path.write_bytes(importlib.util.MAGIC_NUMBER + (b"\x00" * 12) + marshal.dumps(code))

    def test_full_audit_uses_exact_identity_and_finds_new_player_fields(self):
        weapons_path = self.root / "weapons.json"
        weapons_path.write_text(json.dumps({
            "weapons": [{
                "blueprint_id": 123,
                "item_id": 456,
                "prototype_id": 7,
                "name": "Test Rifle",
                "category": "Assault Rifle",
                "durability": 100,
                "weight": 1.5,
                "short_description": "Test description",
                "acquisition_hint": "Test acquisition",
                "ranged_stats": {
                    "rpm": 600,
                    "magazine": 40,
                    "range_meters": 55,
                    "reload_seconds": 2.4,
                    "mobility": 50,
                    "full_damage_distance": 24,
                    "minimum_damage_distance": 67,
                    "minimum_damage_multiplier": 0.3,
                    "ammo_item_id": 999,
                    "accuracy": 45,
                    "stability": 45,
                },
                "tiers": [{"tier": 1, "item_id": 457, "gun_no": 888, "damage": 31, "recipe": {"forge_no": 1}}],
                "image_reference": "test.png",
            }]
        }), encoding="utf-8")
        table = self.current / "game_common" / "data" / "gun_extra_stats.json"
        table.parent.mkdir(parents=True, exist_ok=True)
        table.write_text(json.dumps({
            "good": {"gun_no": 888, "ads_time": 0.22, "bullet_speed": 480, "fire_mode": "full_auto"},
            "similar-only": {"gun_no": 8880, "ads_time": 9.99, "bullet_speed": 1},
        }), encoding="utf-8")
        self._write_pyc(
            "game_common/guncore/GunDisplayHelper.pyc",
            "def get_stats(gun):\n"
            "    ads_time = gun.get('ads_time')\n"
            "    bullet_speed = gun.get('bullet_speed')\n"
            "    return ads_time, bullet_speed\n",
        )

        report = run_weapon_corpus_audit(self.base, self.current, weapons_path, self.reports)
        self.assertEqual(report["record_counts"]["weapons"], 1)
        weapon = report["weapons"][0]
        self.assertEqual(weapon["coverage"]["magazine"], "published")
        self.assertEqual(weapon["coverage"]["ads_time"], "candidate-evidence-found")
        self.assertEqual(weapon["coverage"]["bullet_speed"], "candidate-evidence-found")
        records = weapon["exact_corpus_evidence"]
        self.assertTrue(any(row["record_id"] == "good" for row in records))
        self.assertFalse(any(row["record_id"] == "similar-only" for row in records))
        self.assertGreater(report["pyc_consumer_scan"]["group_candidate_counts"]["ads_time"], 0)
        self.assertTrue((self.reports / "weapon-corpus-audit.json").is_file())

    def test_melee_marks_firearm_only_fields_not_applicable(self):
        weapons_path = self.root / "weapons.json"
        weapons_path.write_text(json.dumps({
            "weapons": [{
                "blueprint_id": 321,
                "item_id": 654,
                "prototype_id": 8,
                "name": "Test Blade",
                "category": "Melee",
                "melee_stats": {"attack_range": 2.0},
                "tiers": [{"tier": 1, "damage": 50}],
            }]
        }), encoding="utf-8")
        report = run_weapon_corpus_audit(self.base, self.current, weapons_path, self.reports)
        coverage = report["weapons"][0]["coverage"]
        self.assertEqual(coverage["magazine"], "not-applicable")
        self.assertEqual(coverage["ads_time"], "not-applicable")
        self.assertNotIn("magazine", {row["group"] for row in report["weapons"][0]["gaps"]})


if __name__ == "__main__":
    unittest.main()
