from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


MINER = Path(__file__).resolve().parents[1]
SRC = MINER / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_evidence_contracts import (  # noqa: E402
    GENERAL_SCHEMA,
    dependency_fingerprint,
    normalize_evidence_state,
    project_legacy_weapon_graph,
    validate_claim,
    validate_edge,
    validate_generalized_graph,
)
from dead_signal_graph_baseline import validate_weapon_graph_compatibility  # noqa: E402


class EvidenceGraphPhaseOneContractTests(unittest.TestCase):
    def setUp(self):
        self.legacy = {
            "schema": "dead-signal-evidence-graph",
            "schema_version": 5,
            "brand": "Dead Signal",
            "subject": {"type": "weapon", "identity": "ds-w-test", "name": "Test Weapon"},
            "record_counts": {"nodes": 3, "edges": 2, "exact_occurrences": 1},
            "nodes": [
                {
                    "id": "weapon:ds-w-test",
                    "kind": "weapon",
                    "label": "Test Weapon",
                    "state": "VERIFIED",
                    "canonical_id": "ds-w-test",
                    "blueprint_id": 1001,
                    "item_id": 2001,
                    "category": "AR",
                },
                {"id": "item_id:2001", "kind": "item_id", "label": "2001", "state": "VERIFIED"},
                {
                    "id": "record:client_data|game_common/data/item_data.json|2001",
                    "kind": "record",
                    "label": "item_data / 2001",
                    "layer": "client_data",
                    "table": "game_common/data/item_data.json",
                    "record_id": "2001",
                    "state": "VERIFIED",
                },
            ],
            "edges": [
                {
                    "from": "weapon:ds-w-test",
                    "to": "item_id:2001",
                    "kind": "exact-identity",
                    "field": "item_id",
                    "state": "VERIFIED",
                    "authoritative": True,
                },
                {
                    "from": "item_id:2001",
                    "to": "record:client_data|game_common/data/item_data.json|2001",
                    "kind": "exact-occurrence",
                    "field": "id",
                    "json_pointer": "/id",
                    "state": "VERIFIED",
                    "authoritative": True,
                },
            ],
            "policy": {
                "edges": "exact only",
                "discovery": "never creates edges",
                "publication": "not automatic",
            },
        }

    def test_state_normalization_is_centralized_and_fail_closed(self):
        self.assertEqual("PROVEN", normalize_evidence_state("VERIFIED"))
        self.assertEqual("NOT APPLICABLE", normalize_evidence_state("not_applicable"))
        with self.assertRaises(ValueError):
            normalize_evidence_state("looks-good")

    def test_edge_without_full_provenance_is_rejected(self):
        edge = {
            "schema_version": 1,
            "source": "weapon:a",
            "destination": "item:1",
            "relationship_type": "exact-identity",
            "source_table": "",
            "source_record": "a",
            "selector": "item_id",
            "layer": "published-snapshot",
            "authority": "legacy-authoritative-weapon-identity",
            "state": "PROVEN",
            "dependency_fingerprint": dependency_fingerprint("a"),
        }
        self.assertIn("edge provenance must be non-empty: source_table", validate_edge(edge))

    def test_proven_claim_without_evidence_is_rejected(self):
        claim = {
            "schema_version": 1,
            "claim_type": "weapon.exact_identity",
            "subject": {"entity_type": "weapon", "canonical_id": "a"},
            "result": "PROVEN",
            "requirements": [],
            "evidence": [],
            "missing": [],
            "conflicts": [],
            "dependencies": [],
        }
        self.assertIn("PROVEN claim requires evidence", validate_claim(claim))

    def test_projection_preserves_legacy_payload_without_mutation(self):
        before = copy.deepcopy(self.legacy)
        projected = project_legacy_weapon_graph(self.legacy)
        self.assertEqual(before, self.legacy)
        self.assertEqual(before, projected["compatibility"]["legacy_payload"])
        self.assertEqual([], validate_weapon_graph_compatibility(projected["compatibility"]["legacy_payload"]))

    def test_projected_weapon_satisfies_generalized_contract(self):
        projected = project_legacy_weapon_graph(self.legacy)
        self.assertEqual(GENERAL_SCHEMA, projected["schema"])
        self.assertEqual("weapon", projected["entity"]["entity_type"])
        self.assertEqual("ds-w-test", projected["entity"]["canonical_id"])
        self.assertEqual([], validate_generalized_graph(projected))
        self.assertEqual(2, len(projected["edges"]))
        self.assertEqual(2, len(projected["claims"]))
        self.assertEqual("PROVEN", projected["assessment"]["result"])

    def test_reference_occurrence_keeps_exact_record_provenance(self):
        projected = project_legacy_weapon_graph(self.legacy)
        occurrence = next(edge for edge in projected["edges"] if edge["relationship_type"] == "exact-occurrence")
        self.assertEqual("game_common/data/item_data.json", occurrence["source_table"])
        self.assertEqual("2001", occurrence["source_record"])
        self.assertEqual("/id", occurrence["selector"])
        self.assertEqual("client_data", occurrence["layer"])
        self.assertEqual("reference-tracer-exact-occurrence", occurrence["authority"])

    def test_non_authoritative_legacy_edge_fails_projection(self):
        self.legacy["edges"][0]["authoritative"] = False
        with self.assertRaisesRegex(ValueError, "not authoritative"):
            project_legacy_weapon_graph(self.legacy)

    def test_missing_occurrence_provenance_fails_projection(self):
        record = self.legacy["nodes"][2]
        record["table"] = ""
        with self.assertRaisesRegex(ValueError, "cannot satisfy generalized provenance"):
            project_legacy_weapon_graph(self.legacy)


if __name__ == "__main__":
    unittest.main()
