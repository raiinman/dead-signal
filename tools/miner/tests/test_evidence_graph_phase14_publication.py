from __future__ import annotations

import sys
import unittest
from pathlib import Path

MINER = Path(__file__).resolve().parents[1]
SRC = MINER / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_publication_contracts import (  # noqa: E402
    BLOCKED_STATES,
    CONTRACT_BY_FIELD,
    contract_manifest,
    project_field,
    publication_decision,
)
from dead_signal_publication_integration import audit_graph  # noqa: E402


def claim(claim_type="attachment.slot_type", result="PROVEN", requirements=None, **extra):
    row = {
        "claim_type": claim_type,
        "result": result,
        "requirements": requirements if requirements is not None else ["player attachment subtype maps to a supported slot"],
        "evidence": [{"table": "game_common/data/item_data.json", "record_id": "1"}],
        "missing": [],
        "conflicts": [],
        "dependencies": ["game_common/data/item_data.json"],
    }
    row.update(extra)
    return row


class Phase14PublicationContractTests(unittest.TestCase):
    def test_manifest_has_unique_registered_fields(self):
        manifest = contract_manifest()
        self.assertEqual(manifest["field_count"], len(CONTRACT_BY_FIELD))
        self.assertTrue(manifest["policy"]["proof_is_not_publication"])
        self.assertFalse(manifest["policy"]["partial_unresolved_conflict_publish_silently"])

    def test_proven_claim_with_contract_requirement_is_publishable(self):
        decision = publication_decision("attachment.slot_type", claim())
        self.assertTrue(decision["publishable"])
        self.assertEqual("PUBLISHABLE", decision["decision"])
        self.assertEqual(["game_common/data/item_data.json"], decision["provenance"]["dependencies"])

    def test_proven_alone_is_not_enough_when_contract_evidence_is_undeclared(self):
        decision = publication_decision("attachment.slot_type", claim(requirements=["some other requirement"]))
        self.assertFalse(decision["publishable"])
        self.assertTrue(any(value.startswith("contract-requirement-not-declared:") for value in decision["blockers"]))

    def test_partial_unresolved_and_conflict_never_publish_silently(self):
        for state in sorted(BLOCKED_STATES):
            with self.subTest(state=state):
                decision = publication_decision("attachment.slot_type", claim(result=state))
                self.assertFalse(decision["publishable"])
                self.assertEqual("BLOCKED", decision["decision"])

    def test_conflict_payload_blocks_even_if_result_says_proven(self):
        decision = publication_decision("attachment.slot_type", claim(conflicts=[{"owner": "A", "other": "B"}]))
        self.assertFalse(decision["publishable"])
        self.assertIn("conflicting-evidence", decision["blockers"])

    def test_wrong_claim_type_fails_closed(self):
        decision = publication_decision("attachment.slot_type", claim(claim_type="attachment.artwork"))
        self.assertFalse(decision["publishable"])
        self.assertIn("wrong-claim-type", decision["blockers"])

    def test_unregistered_field_fails_closed(self):
        decision = publication_decision("attachment.magic_dps", claim())
        self.assertFalse(decision["publishable"])
        self.assertEqual(["unregistered-publication-field"], decision["blockers"])

    def test_missing_claim_is_omitted_not_fabricated(self):
        decision = publication_decision("attachment.slot_type", None)
        self.assertFalse(decision["publishable"])
        self.assertEqual("OMIT", decision["decision"])

    def test_not_applicable_is_explicit_not_missing(self):
        relation = claim(
            claim_type="attachment.weapon_relationship",
            result="NOT APPLICABLE",
            requirements=["shared four-state policy", "weapon-side reverse state agrees"],
        )
        decision = publication_decision("attachment.weapon_relationship", relation)
        self.assertTrue(decision["publishable"])
        self.assertEqual("NOT APPLICABLE", decision["decision"])

    def test_blocked_projection_never_carries_public_value(self):
        projected = project_field("attachment.slot_type", claim(result="PARTIAL"), "Muzzle")
        self.assertIsNone(projected["value"])
        self.assertFalse(projected["publication"]["publishable"])

    def test_audit_graph_names_claim_and_provenance(self):
        graph = {
            "entity": {"entity_type": "attachment", "canonical_id": "ds-att-1", "identity_state": "PROVEN"},
            "claims": [claim()],
            "edges": [],
        }
        audit = audit_graph(graph)
        slot = next(row for row in audit["fields"] if row["field"] == "attachment.slot_type")
        self.assertEqual("attachment.slot_type", slot["publication"]["claim_type"])
        self.assertEqual(["game_common/data/item_data.json"], slot["publication"]["provenance"]["dependencies"])


if __name__ == "__main__":
    unittest.main()
