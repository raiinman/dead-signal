from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

MINER = Path(__file__).resolve().parents[1]
SRC = MINER / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_crafting_adapters import MaterialAdapter, RecipeAdapter
from dead_signal_domain_adapters import AdapterContract, EvidenceDomainAdapter
from dead_signal_evidence_contracts import (
    ASSESSMENT_SCHEMA_VERSION,
    ENTITY_SCHEMA_VERSION,
    GENERAL_SCHEMA,
    GENERAL_SCHEMA_VERSION,
)


class GraphOnlyAdapter(EvidenceDomainAdapter):
    contract = AdapterContract(
        entity_type="graph_only",
        identity_seeds=("graph_only_id",),
        canonical_owner_tables=("game_common/data/graph_only_data.json",),
        allowed_outbound_fields=(),
        typed_destination_tables=(),
        collision_prone_fields=(),
        blocked_generic_fields=("id", "no", "code"),
        terminal_presentation_fields=("name",),
        supported_claims=("graph_only.identity",),
        applicability_rules=("exact owner required",),
    )

    def graph(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        value = str(identity)
        return {
            "schema": GENERAL_SCHEMA,
            "schema_version": GENERAL_SCHEMA_VERSION,
            "entity": {
                "schema_version": ENTITY_SCHEMA_VERSION,
                "entity_type": "graph_only",
                "canonical_id": value,
                "name": f"Graph Only {value}",
                "classification": "test",
                "identity_state": "PROVEN",
                "source_records": [],
            },
            "claims": [
                {
                    "schema_version": 1,
                    "claim_type": "graph_only.identity",
                    "subject": {"entity_type": "graph_only", "canonical_id": value},
                    "result": "PROVEN",
                    "requirements": ["exact owner"],
                    "evidence": [{"id": value}],
                    "missing": [],
                    "conflicts": [],
                    "dependencies": ["game_common/data/graph_only_data.json"],
                }
            ],
            "edges": [],
            "assessment": {
                "schema_version": ASSESSMENT_SCHEMA_VERSION,
                "result": "PROVEN",
                "claim_counts": {
                    "PROVEN": 1,
                    "PARTIAL": 0,
                    "UNRESOLVED": 0,
                    "NOT APPLICABLE": 0,
                    "CONFLICT": 0,
                },
                "missing": [],
                "conflicts": [],
            },
            "domain": {"entity_type": "graph_only", "adapter": type(self).__name__},
        }


class Phase9AdapterContractHotfixTests(unittest.TestCase):
    def test_recipe_and_material_adapters_are_concrete(self):
        self.assertEqual(frozenset(), RecipeAdapter.__abstractmethods__)
        self.assertEqual(frozenset(), MaterialAdapter.__abstractmethods__)

    def test_graph_only_adapter_gets_fail_closed_default_views(self):
        adapter = GraphOnlyAdapter()
        self.assertEqual("7", adapter.identify(7)["canonical_id"])
        self.assertEqual("graph_only.identity", adapter.claims(7)[0]["claim_type"])
        self.assertEqual("PROVEN", adapter.resolve_claim(7, "graph_only.identity")["result"])
        self.assertEqual(["game_common/data/graph_only_data.json"], adapter.dependencies(7))
        presentation = adapter.presentation(7)
        self.assertEqual("PROVEN", presentation["assessment"])
        self.assertFalse(presentation["publication_authority"])

    def test_unsupported_default_claim_still_fails_closed(self):
        with self.assertRaises(KeyError):
            GraphOnlyAdapter().resolve_claim(7, "graph_only.missing")


if __name__ == "__main__":
    unittest.main()
