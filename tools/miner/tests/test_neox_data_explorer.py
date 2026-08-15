from __future__ import annotations

import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "neox_data_explorer.py"
SPEC = importlib.util.spec_from_file_location("neox_data_explorer", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class NeoXDataExplorerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.root / "snapshots" / "full" / "base" / "abc" / "tables"
        self.current = self.root / "snapshots" / "full" / "current" / "def" / "tables"
        self.base.mkdir(parents=True)
        self.current.mkdir(parents=True)
        relative = Path("game_common/data/example_weapon_ui_data.json")
        (self.base / relative).parent.mkdir(parents=True, exist_ok=True)
        (self.current / relative).parent.mkdir(parents=True, exist_ok=True)
        (self.base / relative).write_text(json.dumps({"data": {"100": {"item_id": 200, "description": "OLD"}}}), encoding="utf-8")
        (self.current / relative).write_text(json.dumps({"data": {
            "100": {"item_id": 200, "description": "Current weapon flavor", "nested": {"tooltip_id": "DESC_200"}},
            "101": {"item_id": 201, "description": "Other text"},
        }}), encoding="utf-8")
        (self.root / "last-run.json").write_text(json.dumps({
            "active_snapshots": {"base": str(self.base), "current": str(self.current)},
            "published": str(self.root / "published"),
        }), encoding="utf-8")
        catalogs = self.root / "catalogs"
        catalogs.mkdir()
        db = sqlite3.connect(catalogs / "structured-tables.sqlite")
        db.executescript("""
            CREATE TABLE tables (
                relative_path TEXT PRIMARY KEY,
                base_json_path TEXT,
                current_json_path TEXT,
                base_records INTEGER,
                current_records INTEGER,
                base_bytes INTEGER,
                current_bytes INTEGER,
                layer_status TEXT NOT NULL
            );
            CREATE TABLE domain_tables (
                domain TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                PRIMARY KEY (domain, relative_path)
            );
        """)
        rel = relative.as_posix()
        db.execute("INSERT INTO tables VALUES (?,?,?,?,?,?,?,?)", (
            rel, str(self.base / relative), str(self.current / relative), 1, 2, 60, 180, "base-and-current-patch"
        ))
        db.execute("INSERT INTO domain_tables VALUES (?,?)", ("weapons", rel))
        db.commit()
        db.close()
        self.relative = rel
        self.explorer = MODULE.NeoXDataExplorer(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_lists_cataloged_tables_and_domains(self):
        result = self.explorer.list_tables("weapon", domain="weapons")
        self.assertEqual(1, result["result_count"])
        self.assertEqual(self.relative, result["tables"][0]["relative_path"])
        summary = self.explorer.table_summary(self.relative)
        self.assertEqual(["weapons"], summary["domains"])
        self.assertEqual(2, summary["current_records"])

    def test_browses_exact_record_and_flattens_fields(self):
        record = self.explorer.record(self.relative, "100", layer="current")
        fields = {row["json_pointer"]: row["value"] for row in record["fields"]}
        self.assertEqual(200, fields["/item_id"])
        self.assertEqual("Current weapon flavor", fields["/description"])
        self.assertEqual("DESC_200", fields["/nested/tooltip_id"])
        self.assertEqual("Exact record identity from one extracted NeoX table; no inference or fuzzy joins.", record["policy"])

    def test_record_search_is_discovery_only(self):
        results = self.explorer.search_record_fields(self.relative, layer="current", query="tooltip")
        self.assertEqual(1, results["result_count"])
        self.assertEqual("tooltip_id", results["results"][0]["field"])
        self.assertIn("never establishes", results["identity_policy"])

    def test_path_escape_is_rejected(self):
        with self.assertRaises(ValueError):
            self.explorer.list_records("../../outside.json", layer="current")


if __name__ == "__main__":
    unittest.main()
