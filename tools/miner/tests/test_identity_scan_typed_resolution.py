from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_evidence_graph import _typed_occurrence_rows  # noqa: E402


class IdentityScanTypedResolutionTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute(
            "CREATE TABLE occurrences(value TEXT, layer TEXT, table_name TEXT, record_id TEXT, field TEXT, json_pointer TEXT)"
        )
        self.connection.executemany(
            "INSERT INTO occurrences VALUES (?,?,?,?,?,?)",
            [
                (
                    "204",
                    "base",
                    "game_common/data/weapon_prototype_data.json",
                    "204",
                    "record_id",
                    "/record_id",
                ),
                (
                    "204",
                    "base",
                    "game_common/data/buff/buff_data.json",
                    "9001",
                    "tag_id",
                    "/tag_id",
                ),
                (
                    "204",
                    "current",
                    "client_data/gun_sticker_data.json",
                    "77",
                    "sticker_index",
                    "/sticker_index",
                ),
            ],
        )
        self.connection.commit()

    def tearDown(self):
        self.connection.close()

    def test_prototype_identity_only_walks_weapon_prototype_table(self):
        rows, tables = _typed_occurrence_rows(self.connection, "prototype_id", "204", 100)
        self.assertEqual(("game_common/data/weapon_prototype_data.json",), tables)
        self.assertEqual(1, len(rows))
        self.assertEqual("game_common/data/weapon_prototype_data.json", rows[0][1])
        self.assertEqual("204", rows[0][2])

    def test_prototype_no_uses_same_typed_destination(self):
        rows, tables = _typed_occurrence_rows(self.connection, "prototype_no", "204", 100)
        self.assertEqual(("game_common/data/weapon_prototype_data.json",), tables)
        self.assertEqual(1, len(rows))

    def test_untyped_identity_preserves_broad_exact_occurrences(self):
        rows, tables = _typed_occurrence_rows(self.connection, "item_id", "204", 100)
        self.assertEqual((), tables)
        self.assertEqual(3, len(rows))


if __name__ == "__main__":
    unittest.main()
