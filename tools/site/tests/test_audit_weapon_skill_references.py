import importlib.util
import sqlite3
import tempfile
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "audit-weapon-skill-references.py"
SPEC = importlib.util.spec_from_file_location("audit_weapon_skill_references", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class WeaponSkillReferenceAuditTests(unittest.TestCase):
    @staticmethod
    def payload():
        return {
            "weapons": [
                {
                    "blueprint_id": 1,
                    "name": "Resolved Rifle",
                    "quality": "Legendary",
                    "blueprint_attribute_progression": {"levels": [{"fixed_skill_code": "WS100"}]},
                },
                {
                    "blueprint_id": 2,
                    "name": "Dangling Rifle",
                    "quality": "Epic",
                    "blueprint_attribute_progression": {"levels": [{"fixed_skill_code": "WS1301"}]},
                },
            ]
        }

    @staticmethod
    def connection():
        connection = sqlite3.connect(":memory:")
        connection.execute(
            "CREATE TABLE occurrences (value TEXT, layer TEXT, table_name TEXT, record_id TEXT, field TEXT, json_pointer TEXT)"
        )
        connection.execute(
            "INSERT INTO occurrences VALUES (?, ?, ?, ?, ?, ?)",
            ("1", "base", MODULE.PASSIVE_SKILL_TABLE, "WS100", "buff_id", "/data/WS100/buff_id"),
        )
        # Similar-looking IDs must not satisfy an exact reference.
        connection.execute(
            "INSERT INTO occurrences VALUES (?, ?, ?, ?, ?, ?)",
            ("2", "base", MODULE.PASSIVE_SKILL_TABLE, "WS13101", "buff_id", "/data/WS13101/buff_id"),
        )
        return connection

    def test_exact_record_identity_only(self):
        connection = self.connection()
        try:
            report = MODULE.audit(self.payload(), connection)
        finally:
            connection.close()
        self.assertEqual(["WS1301"], report["dangling_fixed_skill_codes"])
        self.assertEqual(1, report["counts"]["weapons_with_dangling_fixed_skill_references"])
        self.assertEqual("Dangling Rifle", report["queue"][0]["name"])
        self.assertEqual("dangling-exact-passive-skill-reference", report["queue"][0]["classification"])


if __name__ == "__main__":
    unittest.main()
