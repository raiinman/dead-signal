from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_schema_trace_batch import summarize_trace  # noqa: E402


class SchemaTraceBatchTests(unittest.TestCase):
    def test_clean_trace_summary_compacts_owner_records_and_branches(self):
        payload = {
            "subject": {
                "canonical_id": "ds-w-1",
                "name": "Example",
                "category": "Shotgun",
                "blueprint_id": 10,
                "item_id": 20,
                "prototype_id": 30,
            },
            "identities": [
                {"kind": "blueprint_id", "value": "10", "state": "VERIFIED", "depth": 0},
                {"kind": "item_id", "value": "20", "state": "VERIFIED", "depth": 1},
            ],
            "records": [
                {
                    "layer": "current",
                    "table": "game_common/data/gun_blueprint_data.json",
                    "record_id": "10",
                    "matched_identity": {"kind": "blueprint_id", "value": "10"},
                    "outbound_typed_identities": [
                        {"kind": "item_id", "value": "20", "field": "gun_item_no"},
                        {"kind": "item_id", "value": "20", "field": "gun_item_no"},
                    ],
                }
            ],
            "record_counts": {"skipped_broad_exact_references": 7},
        }
        result = summarize_trace(payload)
        self.assertEqual("clean", result["status"])
        self.assertEqual(1, result["typed_branch_count"])
        self.assertEqual(0, result["unresolved_stop_count"])
        self.assertEqual(1, result["record_count"])
        self.assertEqual(7, result["skipped_broad_exact_references"])

    def test_unresolved_identity_is_preserved_as_stop_point(self):
        payload = {
            "subject": {"canonical_id": "ds-w-2", "name": "Blocked"},
            "identities": [
                {
                    "kind": "skill_id",
                    "value": "9001",
                    "state": "EXACT-REFS-NO-TYPED-OWNER",
                    "depth": 3,
                    "exact_reference_count": 4,
                    "owner_tables": ["game_common/data/skill_data.json"],
                    "discovered_from": "current|table|record/path",
                }
            ],
            "records": [],
            "record_counts": {},
        }
        result = summarize_trace(payload)
        self.assertEqual("stopped-with-unresolved-identities", result["status"])
        self.assertEqual(1, result["unresolved_stop_count"])
        stop = result["unresolved_stops"][0]
        self.assertEqual("skill_id", stop["kind"])
        self.assertEqual("9001", stop["value"])
        self.assertEqual(4, stop["exact_reference_count"])


if __name__ == "__main__":
    unittest.main()
