from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


MINER = Path(__file__).resolve().parents[1]
SRC = MINER / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_graph_baseline import (  # noqa: E402
    canonical_graph_hash,
    validate_weapon_graph_compatibility,
)


class EvidenceGraphPhaseZeroBaselineTests(unittest.TestCase):
    def setUp(self):
        self.graph = {
            "schema": "dead-signal-evidence-graph",
            "schema_version": 5,
            "brand": "Dead Signal",
            "subject": {"type": "weapon", "identity": "ds-w-test", "name": "Test Weapon"},
            "record_counts": {"nodes": 2, "edges": 1, "exact_occurrences": 0},
            "nodes": [
                {"id": "weapon:ds-w-test", "kind": "weapon", "label": "Test Weapon", "state": "VERIFIED"},
                {"id": "item_id:1", "kind": "item_id", "label": "1", "state": "UNRESOLVED"},
            ],
            "edges": [{"from": "weapon:ds-w-test", "to": "item_id:1", "authoritative": True}],
            "policy": {"edges": "exact only", "discovery": "never creates edges", "publication": "not automatic"},
        }

    def test_current_weapon_graph_contract_is_accepted(self):
        self.assertEqual([], validate_weapon_graph_compatibility(self.graph))

    def test_non_authoritative_edge_fails_closed(self):
        self.graph["edges"][0]["authoritative"] = False
        self.assertIn("non-authoritative edge entered exact weapon graph", validate_weapon_graph_compatibility(self.graph))

    def test_missing_provenance_policy_is_rejected(self):
        self.graph["policy"].pop("publication")
        self.assertIn("missing policy statement: publication", validate_weapon_graph_compatibility(self.graph))

    def test_canonical_hash_is_stable_across_mapping_order(self):
        reversed_graph = dict(reversed(list(self.graph.items())))
        self.assertEqual(canonical_graph_hash(self.graph), canonical_graph_hash(reversed_graph))

    def test_committed_baseline_covers_all_phase_zero_cohorts(self):
        path = MINER / "baselines" / "weapon-evidence-graph-phase-0.json"
        baseline = json.loads(path.read_text(encoding="utf-8"))
        cohorts = {row["cohort"] for row in baseline["fixtures"]}
        self.assertEqual({
            "standard-ranged",
            "melee",
            "nonstandard-blueprint",
            "special-equipped",
            "no-fixed-skill-reference",
        }, cohorts)
        self.assertTrue(baseline["compatibility"]["authoritative_edges_only"])
        self.assertTrue(baseline["compatibility"]["performance_values_are_release_information_not_test_thresholds"])


if __name__ == "__main__":
    unittest.main()
