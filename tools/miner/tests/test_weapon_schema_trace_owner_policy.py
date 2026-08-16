from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_weapon_schema_trace import (  # noqa: E402
    _field_kind,
    _owner_ref_matches,
    _reference_candidates,
)


class WeaponSchemaTraceOwnerPolicyTests(unittest.TestCase):
    def test_blueprint_template_metadata_is_not_a_blueprint_identity(self):
        self.assertIsNone(_field_kind("blueprint_template_no"))
        self.assertEqual("blueprint_id", _field_kind("blueprint_no"))

    def test_relevant_table_wrong_field_does_not_establish_owner(self):
        row = {
            "table": "game_common/data/gun_blueprint_data.json",
            "record_id": "13111101",
            "field": "blueprint_template_no",
        }
        self.assertFalse(_owner_ref_matches("blueprint_id", row))

    def test_relevant_table_typed_field_establishes_owner(self):
        row = {
            "table": "game_common/data/gun_blueprint_attr_data.json",
            "record_id": "(13231101, 1)",
            "field": "blueprint_no",
        }
        self.assertTrue(_owner_ref_matches("blueprint_id", row))

    def test_gun_identity_does_not_follow_equal_scalar_in_gun_base_neighbor(self):
        wrong = {
            "table": "game_common/data/gun_base_params_data.json",
            "record_id": "10420121",
            "field": "accessory_seq_no",
        }
        owner = {
            "table": "game_common/data/gun_base_params_data.json",
            "record_id": "10420011",
            "field": "record_id",
        }
        self.assertFalse(_owner_ref_matches("gun_no", wrong))
        self.assertTrue(_owner_ref_matches("gun_no", owner))

    def test_reference_candidates_preserve_table_field_evidence(self):
        rows = [
            {"table": "client_data/foo.json", "field": "aim_no"},
            {"table": "client_data/foo.json", "field": "aim_no"},
            {"table": "client_data/bar.json", "field": "record_id"},
        ]
        candidates = _reference_candidates(rows)
        self.assertEqual(
            {"table": "client_data/foo.json", "field": "aim_no", "count": 2},
            candidates[0],
        )


if __name__ == "__main__":
    unittest.main()
