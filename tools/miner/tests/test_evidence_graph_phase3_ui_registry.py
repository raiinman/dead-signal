from __future__ import annotations

import sys
import unittest
from pathlib import Path


MINER = Path(__file__).resolve().parents[1]
SRC = MINER / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_entity_selector import (  # noqa: E402
    RegistrySelectorModel,
    entity_choice_label,
    identity_from_choice,
)


class FakeGeneralizedGraph:
    def __init__(self):
        self.rows = [
            {
                "entity_type": "weapon",
                "canonical_id": "ds-w-1",
                "display_name": "Alpha Rifle",
                "identity_state": "PROVEN",
                "graph_target": {"entity_type": "weapon", "canonical_id": "ds-w-1"},
            },
            {
                "entity_type": "weapon",
                "canonical_id": "ds-w-2",
                "display_name": "Beta Rifle",
                "identity_state": "UNRESOLVED",
                "graph_target": {"entity_type": "weapon", "canonical_id": "ds-w-2"},
            },
        ]
        self.selected = []

    def rebuild_entity_registry(self):
        return {"adapter_types": ["weapon"], "total": len(self.rows)}

    def search_entities(self, query, *, entity_type=None, unresolved_only=False, limit=100):
        needle = str(query or "").casefold()
        rows = []
        for row in self.rows:
            if entity_type and row["entity_type"] != entity_type:
                continue
            if unresolved_only and row["identity_state"] not in {"PARTIAL", "UNRESOLVED", "CONFLICT"}:
                continue
            if needle and needle not in row["display_name"].casefold() and needle not in row["canonical_id"].casefold():
                continue
            rows.append(dict(row))
        return rows[:limit]

    def registered_entity(self, entity_type, canonical_id):
        row = next(
            item for item in self.rows
            if item["entity_type"] == entity_type and item["canonical_id"] == canonical_id
        )
        key = (entity_type, canonical_id)
        if key in self.selected:
            self.selected.remove(key)
        self.selected.insert(0, key)
        return dict(row)

    def recent_entities(self):
        result = []
        for entity_type, canonical_id in self.selected:
            result.append(self.registered_entity(entity_type, canonical_id))
        return result


class EvidenceGraphPhaseThreeUIRegistryTests(unittest.TestCase):
    def test_choice_label_and_identity_round_trip(self):
        entity = {
            "display_name": "SOCR - The Last Valor",
            "canonical_id": "ds-w-last-valor",
        }
        label = entity_choice_label(entity)
        self.assertEqual("SOCR - The Last Valor  [ds-w-last-valor]", label)
        self.assertEqual("ds-w-last-valor", identity_from_choice(label))

    def test_model_exposes_registered_entity_types(self):
        model = RegistrySelectorModel(FakeGeneralizedGraph())
        self.assertEqual(("weapon",), model.entity_types())

    def test_name_search_routes_to_exact_graph_target(self):
        model = RegistrySelectorModel(FakeGeneralizedGraph())
        rows = model.search("alpha", entity_type="weapon")
        self.assertEqual(1, len(rows))
        label = entity_choice_label(rows[0])
        target = model.target_for_choice(label, entity_type="weapon")
        self.assertEqual({"entity_type": "weapon", "canonical_id": "ds-w-1"}, target)

    def test_exact_id_search_routes_to_same_target(self):
        model = RegistrySelectorModel(FakeGeneralizedGraph())
        rows = model.search("ds-w-2", entity_type="weapon")
        target = model.target_for_choice(entity_choice_label(rows[0]), entity_type="weapon")
        self.assertEqual("ds-w-2", target["canonical_id"])

    def test_unresolved_only_filter_is_preserved(self):
        model = RegistrySelectorModel(FakeGeneralizedGraph())
        rows = model.search("", entity_type="weapon", unresolved_only=True)
        self.assertEqual(["ds-w-2"], [row["canonical_id"] for row in rows])

    def test_manual_choice_falls_back_to_bracket_identity(self):
        model = RegistrySelectorModel(FakeGeneralizedGraph())
        model.search("", entity_type="weapon")
        target = model.target_for_choice("Custom label  [ds-w-1]", entity_type="weapon")
        self.assertEqual("ds-w-1", target["canonical_id"])


if __name__ == "__main__":
    unittest.main()
