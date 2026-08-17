from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
import zipfile


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_neox_export import export_all_neox_tables  # noqa: E402
from neox_data_explorer import NeoXDataExplorer  # noqa: E402


class NeoXAllTablesExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.root / "base"
        self.current = self.root / "current"
        self.base.mkdir()
        self.current.mkdir()
        (self.root / "last-run.json").write_text(json.dumps({
            "active_snapshots": {"base": str(self.base), "current": str(self.current)},
        }), encoding="utf-8")

        base_table = self.base / "game_common/data/gun_blueprint_attr_data.json"
        current_table = self.current / "game_common/data/item_data.json"
        base_table.parent.mkdir(parents=True)
        current_table.parent.mkdir(parents=True)
        base_table.write_text(json.dumps({"data": {"(1, 1)": {"fixed_skill_code": "WS2001"}}}), encoding="utf-8")
        current_table.write_text(json.dumps({"data": {"2": {"name": "Example"}}}), encoding="utf-8")

        catalogs = self.root / "catalogs"
        catalogs.mkdir()
        connection = sqlite3.connect(catalogs / "structured-tables.sqlite")
        connection.execute("""
            CREATE TABLE tables (
                relative_path TEXT PRIMARY KEY,
                base_json_path TEXT,
                current_json_path TEXT,
                base_records INTEGER,
                current_records INTEGER,
                base_bytes INTEGER,
                current_bytes INTEGER,
                layer_status TEXT NOT NULL
            )
        """)
        connection.execute("CREATE TABLE domain_tables (domain TEXT, relative_path TEXT)")
        connection.executemany("INSERT INTO tables VALUES (?,?,?,?,?,?,?,?)", [
            (
                "game_common/data/gun_blueprint_attr_data.json", str(base_table), None,
                1, 0, base_table.stat().st_size, 0, "base-only",
            ),
            (
                "game_common/data/item_data.json", None, str(current_table),
                0, 1, 0, current_table.stat().st_size, "current-patch-only",
            ),
        ])
        connection.commit()
        connection.close()

    def tearDown(self):
        self.temp.cleanup()

    def test_export_contains_every_catalogued_table_layer_and_manifest(self):
        explorer = NeoXDataExplorer(self.root)
        destination = self.root / "research" / "all-neox.zip"
        result = export_all_neox_tables(explorer, destination)
        self.assertEqual(2, result["catalog_tables"])
        self.assertEqual(2, result["exported_table_files"])
        self.assertEqual(0, result["missing_expected_files"])
        self.assertTrue(destination.is_file())

        with zipfile.ZipFile(destination, "r") as archive:
            names = set(archive.namelist())
            self.assertIn("manifest.json", names)
            self.assertIn("base/game_common/data/gun_blueprint_attr_data.json", names)
            self.assertIn("current/game_common/data/item_data.json", names)
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            self.assertEqual("dead-signal-neox-all-tables-export", manifest["schema"])
            self.assertEqual(2, manifest["record_counts"]["catalog_tables"])
            self.assertEqual(2, manifest["record_counts"]["exported_table_files"])
            self.assertIn("never modified", result["policy"])
            self.assertIn("No game module", manifest["policy"]["execution"])

    def test_data_intelligence_exposes_one_click_all_table_export(self):
        source = (SRC / "dead_signal_intelligence_window.py").read_text(encoding="utf-8")
        self.assertIn('"EXPORT ALL NEOX TABLES"', source)
        self.assertIn("export_all_neox_tables(self.explorer)", source)
        self.assertIn("Complete NeoX research bundle created", source)


if __name__ == "__main__":
    unittest.main()
