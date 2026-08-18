from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WeaponsV1SchemaLockTests(unittest.TestCase):
    def test_locked_schema_declares_identity_build_and_compatibility_boundaries(self):
        schema = json.loads((ROOT / "docs" / "weapons-v1.schema.json").read_text(encoding="utf-8"))
        self.assertEqual("Dead Signal Weapons v1", schema["title"])
        self.assertEqual(2, schema["properties"]["schema_version"]["const"])
        required = set(schema["properties"]["weapons"]["items"]["required"])
        self.assertTrue(
            {"identity", "crafting", "attachment_compatibility", "calibration_compatibility", "ammo_configuration", "cradle_applicability"}.issubset(required)
        )
        self.assertEqual(
            ["compatible", "incompatible", "unresolved", "not-applicable"],
            schema["properties"]["schema_contract"]["properties"]["compatibility_states"]["const"],
        )


if __name__ == "__main__":
    unittest.main()
