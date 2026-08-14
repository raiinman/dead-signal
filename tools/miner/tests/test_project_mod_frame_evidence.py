from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "extractor" / "project_mod_frame_evidence.py"
SPEC = importlib.util.spec_from_file_location("project_mod_frame_evidence", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ProjectModFrameEvidenceTests(unittest.TestCase):
    def test_exact_item_identity_projects_proven_evidence(self):
        evidence = {
            "frame_code": 27,
            "sub_entry_ids": [1101, 1102, 7401, 7405],
            "sub_entry_families": [],
            "status": MODULE.PROVEN_STATUS,
            "order_semantics": "source-order-preserved; frame_lv_1..4 positional mapping unproven",
        }
        normalized = {
            "mods": [{"item_id": 9001, "frame_sub_entry_evidence": evidence}],
        }
        web = {
            "schema": "dead-signal-mods",
            "record_counts": {"families": 1, "source_variants": 1},
            "families": [{"variants": [{"item_id": 9001, "name": "Test Mod"}]}],
        }
        projected = MODULE.project(normalized, web)
        variant = projected["families"][0]["variants"][0]
        self.assertEqual(evidence, variant["frame_sub_entry_evidence"])
        self.assertEqual(1, projected["record_counts"]["frame_evidence_complete_variants"])
        self.assertEqual(0, projected["record_counts"]["frame_evidence_unresolved_variants"])
        self.assertEqual(1, projected["record_counts"]["used_frame_codes"])
        self.assertEqual(4, projected["record_counts"]["used_sub_entry_families"])
        self.assertEqual(
            "proven-entry-identities-positional-level-mapping-unresolved",
            projected["mod_frame_evidence_status"],
        )

    def test_missing_exact_item_match_fails_closed_per_variant(self):
        normalized = {"mods": []}
        web = {
            "schema": "dead-signal-mods",
            "record_counts": {"families": 1, "source_variants": 1},
            "families": [{"variants": [{"item_id": 9001}]}],
        }
        projected = MODULE.project(normalized, web)
        self.assertEqual(0, projected["record_counts"]["frame_evidence_complete_variants"])
        self.assertEqual(1, projected["record_counts"]["frame_evidence_unresolved_variants"])
        self.assertEqual([9001], projected["mod_frame_evidence_missing_normalized_item_ids"])
        self.assertEqual(
            "normalized-frame-evidence-missing",
            projected["families"][0]["variants"][0]["frame_sub_entry_evidence"]["status"],
        )


if __name__ == "__main__":
    unittest.main()
