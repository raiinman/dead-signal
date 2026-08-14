from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "extractor" / "mod_frame_enrichment.py"
SPEC = importlib.util.spec_from_file_location("mod_frame_enrichment", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ModFrameEnrichmentTests(unittest.TestCase):
    @staticmethod
    def entries(changing: bool = False) -> dict:
        result = {}
        identities = {
            1101: ("E0100", 0),
            1102: ("E0200", 0),
            7401: (None, 589720000),
            7405: (None, 589725000),
        }
        for entry_id, (attribute, buff_id) in identities.items():
            for level in range(1, 7):
                code = attribute
                if changing and entry_id == 1101 and level == 5:
                    code = "E0300"
                result[f"({entry_id}, {level})"] = {
                    "attr_no_list": [code] if code else [],
                    "buff_id": buff_id,
                }
        return result

    def test_enrich_preserves_source_order_and_resolves_stable_identity(self):
        payload = {"mods": [{"item_id": 9001, "mod_code": 77, "frame_code": 27}], "record_counts": {"mods": 1}}
        frames = {"27": {"sub_entry_item_no": [1101, 1102, 7401, 7405]}}
        enriched = MODULE.enrich(payload, frames, self.entries())
        evidence = enriched["mods"][0]["frame_sub_entry_evidence"]
        self.assertEqual("proven-frame-and-sub-entry-family-identities", evidence["status"])
        self.assertEqual([1101, 1102, 7401, 7405], evidence["sub_entry_ids"])
        self.assertEqual("attribute", evidence["sub_entry_families"][0]["source_kind"])
        self.assertEqual(["E0100"], evidence["sub_entry_families"][0]["attribute_codes"])
        self.assertEqual("buff", evidence["sub_entry_families"][2]["source_kind"])
        self.assertEqual([589720000], evidence["sub_entry_families"][2]["buff_ids"])
        self.assertIn("positional mapping unproven", evidence["order_semantics"])
        self.assertEqual(1, enriched["record_counts"]["frame_evidence_complete"])
        self.assertEqual(0, enriched["record_counts"]["frame_evidence_unresolved"])

    def test_identity_change_keeps_mod_unresolved(self):
        payload = {"mods": [{"item_id": 9001, "frame_code": 27}], "record_counts": {}}
        frames = {"27": {"sub_entry_item_no": [1101, 1102, 7401, 7405]}}
        enriched = MODULE.enrich(payload, frames, self.entries(changing=True))
        evidence = enriched["mods"][0]["frame_sub_entry_evidence"]
        self.assertEqual("sub-entry-family-identity-unresolved", evidence["status"])
        self.assertEqual(
            "identity-changes-across-regular-levels",
            evidence["sub_entry_families"][0]["identity_status"],
        )
        self.assertEqual(1, enriched["record_counts"]["frame_evidence_unresolved"])
        self.assertEqual([9001], enriched["mod_frame_evidence_unresolved_ids"])

    def test_frame_requires_exactly_four_source_entries(self):
        evidence = MODULE.frame_evidence(27, {"27": {"sub_entry_item_no": [1101, 1102]}}, MODULE._entry_rows(self.entries()))
        self.assertEqual("frame-missing-exact-four-sub-entry-ids", evidence["status"])


if __name__ == "__main__":
    unittest.main()
