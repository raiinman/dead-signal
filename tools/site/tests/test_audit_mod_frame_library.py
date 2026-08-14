from __future__ import annotations

import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "audit-mod-frame-library.py"
SPEC = importlib.util.spec_from_file_location("audit_mod_frame_library", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ModFrameLibraryAuditTests(unittest.TestCase):
    def _fixture(self, *, changing_identity: bool = False):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        mods = root / "mods.json"
        tracer = root / "reference-tracer.sqlite"
        mods.write_text(json.dumps({"mods": [{"frame_code": 27}]}), encoding="utf-8")

        connection = sqlite3.connect(tracer)
        connection.execute(
            "CREATE TABLE occurrences (value TEXT NOT NULL, layer TEXT NOT NULL, table_name TEXT NOT NULL, record_id TEXT NOT NULL, field TEXT NOT NULL, json_pointer TEXT NOT NULL)"
        )
        for index, entry_id in enumerate((1101, 1102, 7401, 7405)):
            connection.execute(
                "INSERT INTO occurrences VALUES (?, 'base', ?, '27', 'sub_entry_item_no', ?)",
                (str(entry_id), MODULE.FRAME_TABLE, f"/data/27/sub_entry_item_no/{index}"),
            )
            for level in range(1, 7):
                if entry_id in (1101, 1102):
                    code = "E0100" if entry_id == 1101 else "E0200"
                    if changing_identity and entry_id == 1101 and level == 5:
                        code = "E0300"
                    connection.execute(
                        "INSERT INTO occurrences VALUES (?, 'base', ?, ?, 'attr_no_list', ?)",
                        (code, MODULE.ENTRY_TABLE, f"({entry_id}, {level})", f"/data/({entry_id}, {level})/attr_no_list/0"),
                    )
                    connection.execute(
                        "INSERT INTO occurrences VALUES ('0', 'base', ?, ?, 'buff_id', ?)",
                        (MODULE.ENTRY_TABLE, f"({entry_id}, {level})", f"/data/({entry_id}, {level})/buff_id"),
                    )
                else:
                    buff_id = 589720000 if entry_id == 7401 else 589725000
                    connection.execute(
                        "INSERT INTO occurrences VALUES (?, 'base', ?, ?, 'buff_id', ?)",
                        (str(buff_id), MODULE.ENTRY_TABLE, f"({entry_id}, {level})", f"/data/({entry_id}, {level})/buff_id"),
                    )
        connection.commit()
        connection.close()
        return temp, mods, tracer

    def test_exact_frame_and_entry_family_join_passes(self):
        temp, mods, tracer = self._fixture()
        self.addCleanup(temp.cleanup)
        report = MODULE.audit(mods, tracer)
        self.assertEqual("pass", report["status"])
        self.assertEqual(1, report["used_frame_codes"])
        self.assertEqual(4, report["used_sub_entry_families"])
        self.assertEqual(4, report["resolved_used_sub_entry_families"])
        self.assertEqual("attribute", report["resolved_sub_entry_families"]["1101"]["source_kind"])
        self.assertEqual("buff", report["resolved_sub_entry_families"]["7401"]["source_kind"])
        self.assertEqual([1, 2, 3, 4, 5, 6], report["resolved_sub_entry_families"]["1101"]["available_levels"])

    def test_regular_level_identity_change_blocks_pass(self):
        temp, mods, tracer = self._fixture(changing_identity=True)
        self.addCleanup(temp.cleanup)
        report = MODULE.audit(mods, tracer)
        self.assertEqual("review", report["status"])
        self.assertIn("1101", report["sub_entry_families_with_changing_regular_identity"])


if __name__ == "__main__":
    unittest.main()
