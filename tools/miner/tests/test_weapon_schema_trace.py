from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_weapon_schema_trace import DeadSignalWeaponSchemaTrace  # noqa: E402


class WeaponSchemaTraceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.root / "snapshots" / "base"
        self.current = self.root / "snapshots" / "current"
        self.base.mkdir(parents=True)
        self.current.mkdir(parents=True)
        published = self.root / "published"
        (published / "web").mkdir(parents=True)
        (published / "indexes").mkdir(parents=True)
        (self.root / "catalogs").mkdir()
        sqlite3.connect(self.root / "catalogs" / "structured-tables.sqlite").close()

        weapon = {
            "canonical_id": "ds-w-13231101",
            "blueprint_id": 13231101,
            "item_id": 10231101,
            "prototype_id": 204,
            "name": "AA12",
            "category": "Shotgun",
            "acquisition": {"fragment_id": 14231101},
            "baseline": {"ranged": {"bullet_pattern_id": "Pat10230011"}},
            "progression": {"gear_tiers": [{"item_id": 10231101, "gun_no": 10230011}]},
        }
        (published / "web" / "weapons.json").write_text(
            json.dumps({"weapons": [weapon]}), encoding="utf-8"
        )
        (self.root / "last-run.json").write_text(json.dumps({
            "active_snapshots": {"base": str(self.base), "current": str(self.current)},
            "published": str(published),
        }), encoding="utf-8")

        tables = {
            "game_common/data/gun_blueprint_data.json": {
                "13231101": {"gun_item_no": 10231101, "prototype_no": 204, "fragment_no": 14231101}
            },
            "game_common/data/equip_data.json": {
                "10231101": {"blueprint_no": 13231101, "gun_no": 10230011, "equip_origin_id": 10231101}
            },
            "game_common/data/gun_base_params_data.json": {
                "10230011": {
                    "bullet_base_no": 10230011,
                    "bullet_no": 30150001,
                    "bullet_pattern_no": "Pat10230011",
                    "bullet_scatter_no": "Spr10230011",
                    "bullet_aim_no": "Xhair10230011",
                    "accessory_seq_no": 10230011,
                }
            },
            "game_common/data/bullet_base_params_data.json": {
                "10230011": {"gun_no": 10230011, "bullet_pattern_no": "Pat10230011"}
            },
            "client_data/bullet_pattern_data.json": {
                "Pat10230011": {"pattern_no": "Pat10230011", "pellet_count": 5}
            },
            "game_common/data/weapon_prototype_data.json": {
                "204": {"prototype_name": "AA12", "prototype_desc": "AA12_DESC"}
            },
            "game_common/data/item_data.json": {
                "30150001": {"item_id": 30150001},
                "14231101": {"item_id": 14231101},
            },
            # Deliberate collision: prototype 204 must never traverse here.
            "game_common/data/buff/buff_data.json": {
                "9001": {"tag_id": 204, "buff_no": 777}
            },
        }
        for relative, rows in tables.items():
            path = self.base / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"data": rows}), encoding="utf-8")

        tracer = sqlite3.connect(published / "indexes" / "reference-tracer.sqlite")
        tracer.execute(
            "CREATE TABLE occurrences(value TEXT, layer TEXT, table_name TEXT, record_id TEXT, field TEXT, json_pointer TEXT)"
        )
        rows = [
            ("13231101", "base", "game_common/data/gun_blueprint_data.json", "13231101", "record_id", "/record_id"),
            ("13231101", "base", "game_common/data/equip_data.json", "10231101", "blueprint_no", "/blueprint_no"),
            ("10231101", "base", "game_common/data/equip_data.json", "10231101", "record_id", "/record_id"),
            ("10231101", "base", "game_common/data/gun_blueprint_data.json", "13231101", "gun_item_no", "/gun_item_no"),
            ("10230011", "base", "game_common/data/gun_base_params_data.json", "10230011", "record_id", "/record_id"),
            ("10230011", "base", "game_common/data/equip_data.json", "10231101", "gun_no", "/gun_no"),
            ("10230011", "base", "game_common/data/bullet_base_params_data.json", "10230011", "record_id", "/record_id"),
            ("204", "base", "game_common/data/weapon_prototype_data.json", "204", "record_id", "/record_id"),
            ("204", "base", "game_common/data/buff/buff_data.json", "9001", "tag_id", "/tag_id"),
            ("14231101", "base", "game_common/data/item_data.json", "14231101", "record_id", "/record_id"),
            ("30150001", "base", "game_common/data/item_data.json", "30150001", "record_id", "/record_id"),
            ("Pat10230011", "base", "client_data/bullet_pattern_data.json", "Pat10230011", "record_id", "/record_id"),
        ]
        tracer.executemany("INSERT INTO occurrences VALUES (?,?,?,?,?,?)", rows)
        tracer.commit()
        tracer.close()

    def tearDown(self):
        self.temp.cleanup()

    def test_aa12_trace_walks_canonical_weapon_schema(self):
        result = DeadSignalWeaponSchemaTrace(self.root).trace("ds-w-13231101")
        records = {(row["table"], row["record_id"]) for row in result["records"]}
        self.assertIn(("game_common/data/gun_blueprint_data.json", "13231101"), records)
        self.assertIn(("game_common/data/equip_data.json", "10231101"), records)
        self.assertIn(("game_common/data/gun_base_params_data.json", "10230011"), records)
        self.assertIn(("game_common/data/weapon_prototype_data.json", "204"), records)
        self.assertIn(("game_common/data/item_data.json", "30150001"), records)
        self.assertIn(("client_data/bullet_pattern_data.json", "Pat10230011"), records)

        outbound = {
            (entry["kind"], entry["value"])
            for record in result["records"]
            for entry in record["outbound_typed_identities"]
        }
        self.assertIn(("gun_no", "10230011"), outbound)
        self.assertIn(("ammo_item_id", "30150001"), outbound)
        self.assertIn(("bullet_pattern_id", "Pat10230011"), outbound)

    def test_prototype_numeric_collision_is_not_followed(self):
        result = DeadSignalWeaponSchemaTrace(self.root).trace("13231101")
        tables = {row["table"] for row in result["records"]}
        self.assertIn("game_common/data/weapon_prototype_data.json", tables)
        self.assertNotIn("game_common/data/buff/buff_data.json", tables)
        prototype = next(
            row for row in result["identities"]
            if row["kind"] == "prototype_id" and row["value"] == "204"
        )
        self.assertEqual(2, prototype["exact_reference_count"])
        self.assertEqual(1, prototype["followed_owner_record_count"])

    def test_only_exact_owner_edges_are_authoritative(self):
        result = DeadSignalWeaponSchemaTrace(self.root).trace("AA12")
        identity_edges = [row for row in result["edges"] if row["from_type"] == "identity"]
        field_edges = [row for row in result["edges"] if row["from_type"] == "record"]
        self.assertTrue(identity_edges)
        self.assertTrue(all(row["authoritative"] for row in identity_edges))
        self.assertTrue(field_edges)
        self.assertTrue(all(not row["authoritative"] for row in field_edges))
        self.assertIn("never promotes", result["policy"]["publication"])


if __name__ == "__main__":
    unittest.main()
