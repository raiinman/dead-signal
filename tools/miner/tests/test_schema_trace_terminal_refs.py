from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_schema_trace_batch import summarize_trace  # noqa: E402
from dead_signal_weapon_schema_trace import (  # noqa: E402
    TERMINAL_REFERENCE_KINDS,
    _field_kind,
    _owner_ref_matches,
)


class SchemaTraceTerminalReferenceTests(unittest.TestCase):
    def test_crosshair_handle_is_declared_terminal(self):
        self.assertIn("crosshair_id", TERMINAL_REFERENCE_KINDS)

    def test_stardust_gun_skill_record_is_a_typed_skill_owner(self):
        row = {
            "table": "game_common/data/stardust_gun_skill_data.json",
            "field": "record_id",
            "record_id": "wp_dust_1000",
        }
        self.assertTrue(_owner_ref_matches("skill_id", row))

    def test_star_skill_field_stays_typed_as_skill(self):
        self.assertEqual("skill_id", _field_kind("star_skill_no"))

    def test_terminal_reference_does_not_make_batch_row_unresolved(self):
        result = {
            "subject": {
                "canonical_id": "ds-w-test",
                "name": "Test Weapon",
                "category": "Test",
            },
            "identities": [
                {"kind": "gun_no", "value": "100", "state": "VERIFIED"},
                {
                    "kind": "crosshair_id",
                    "value": "Xhair100",
                    "state": "TERMINAL-EXACT-REFERENCE",
                    "exact_reference_count": 1,
                    "terminal_note": "terminal",
                },
            ],
            "records": [],
            "record_counts": {},
        }
        summary = summarize_trace(result)
        self.assertEqual("clean", summary["status"])
        self.assertEqual(0, summary["unresolved_stop_count"])
        self.assertEqual(1, summary["terminal_reference_count"])
        self.assertEqual("Xhair100", summary["terminal_references"][0]["value"])


if __name__ == "__main__":
    unittest.main()
