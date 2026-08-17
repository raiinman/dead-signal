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

    def _weapons_path(self) -> Path:
        path = self.root / "weapons.json"
        path.write_text(json.dumps({
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
        return path

    def test_full_audit_uses_exact_identity_and_finds_new_player_fields(self):
        weapons_path = self._weapons_path()
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
        self.assertTrue(all(row.get("evidence_scope") == "variant-local" for row in records))
        self.assertFalse(any(row["record_id"] == "similar-only" for row in records))
        self.assertGreater(report["pyc_consumer_scan"]["group_candidate_counts"]["ads_time"], 0)
        self.assertTrue((self.reports / "weapon-corpus-audit.json").is_file())

    def test_container_map_does_not_leak_sibling_fields_across_records(self):
        weapons_path = self._weapons_path()
        table = self.current / "game_common" / "data" / "container_map.json"
        table.parent.mkdir(parents=True, exist_ok=True)
        table.write_text(json.dumps({
            "data": {
                "7": {"prototype_no": 9999, "ads_time": 9.99},
                "other": {"gun_no": 8880, "bullet_speed": 1},
                "real": {"gun_no": 888, "fire_mode": "full_auto"},
            }
        }), encoding="utf-8")

        report = run_weapon_corpus_audit(self.base, self.current, weapons_path, self.reports)
        weapon = report["weapons"][0]
        records = weapon["exact_corpus_evidence"]
        self.assertTrue(any(row["record_id"] == "real" for row in records))
        self.assertFalse(any(row["record_id"] == "7" for row in records))
        self.assertFalse(any(row["record_id"] == "other" for row in records))
        self.assertEqual(weapon["coverage"]["ads_time"], "missing")
        self.assertEqual(weapon["coverage"]["bullet_speed"], "missing")
        self.assertEqual(weapon["coverage"]["firing_mode"], "candidate-evidence-found")

    def test_shared_bullet_pattern_is_family_evidence_not_variant_ownership(self):
        weapons_path = self.root / "weapons.json"
        weapons_path.write_text(json.dumps({
            "weapons": [
                {
                    "blueprint_id": 100001,
                    "item_id": 200001,
                    "prototype_id": 204,
                    "name": "AA12",
                    "category": "Shotgun",
                    "ranged_stats": {"bullet_pattern_id": "PatShared"},
                    "tiers": [{"tier": 1, "item_id": 200011, "gun_no": 300011, "damage": 30}],
                },
                {
                    "blueprint_id": 100002,
                    "item_id": 200002,
                    "prototype_id": 204,
                    "name": "ACS12 Variant",
                    "category": "Shotgun",
                    "ranged_stats": {"bullet_pattern_id": "PatShared"},
                    "tiers": [{"tier": 1, "item_id": 200012, "gun_no": 300012, "damage": 31}],
                },
            ]
        }), encoding="utf-8")
        pattern = self.current / "game_common" / "data" / "bullet_pattern_data.json"
        pattern.parent.mkdir(parents=True, exist_ok=True)
        pattern.write_text(json.dumps({
            "PatShared": {
                "bullet_pattern_no": "PatShared",
                "bullet_num": 5,
                "scatter_num": 7,
                "bullet_speed": 200,
                "ads_time": 9.99,
                "default_shoot_mode": 99,
            }
        }), encoding="utf-8")
        gun = self.current / "game_common" / "data" / "gun_base_params_data.json"
        gun.write_text(json.dumps({
            "300011": {"gun_no": 300011, "ads_time": 0.23, "default_shoot_mode": 3}
        }), encoding="utf-8")

        report = run_weapon_corpus_audit(self.base, self.current, weapons_path, self.reports)
        first, second = report["weapons"]
        for weapon in (first, second):
            inherited = [row for row in weapon["exact_corpus_evidence"] if row.get("evidence_scope") == "family-shared"]
            self.assertTrue(inherited)
            inherited_groups = {field["group"] for row in inherited for field in row["fields"]}
            self.assertIn("projectiles", inherited_groups)
            self.assertIn("bullet_speed", inherited_groups)
            self.assertNotIn("ads_time", inherited_groups)
            self.assertNotIn("firing_mode", inherited_groups)
            self.assertEqual(weapon["family_inheritance"]["precedence"], ["variant-local", "family-shared"])

        first_local = [row for row in first["exact_corpus_evidence"] if row.get("evidence_scope") == "variant-local"]
        second_local = [row for row in second["exact_corpus_evidence"] if row.get("evidence_scope") == "variant-local"]
        self.assertTrue(any(any(field["group"] == "ads_time" for field in row["fields"]) for row in first_local))
        self.assertFalse(any(any(field["group"] == "ads_time" for field in row["fields"]) for row in second_local))
        self.assertEqual(first["coverage"]["ads_time"], "candidate-evidence-found")
        self.assertEqual(second["coverage"]["ads_time"], "missing")

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
