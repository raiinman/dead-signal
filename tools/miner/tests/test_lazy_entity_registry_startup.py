from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_entity_selector import RegistrySelectorModel


class _AdapterRegistry:
    @staticmethod
    def entity_types():
        return ("weapon", "armor")


class _Graph:
    def __init__(self):
        self.registry = _AdapterRegistry()
        self.rebuilds = 0
        self.searches = 0

    def rebuild_entity_registry(self):
        self.rebuilds += 1
        return {"adapter_types": ["weapon", "armor"], "total": 2}

    def search_entities(self, query, *, entity_type=None, unresolved_only=False, limit=250):
        self.searches += 1
        return [{
            "entity_type": entity_type or "weapon",
            "canonical_id": "ds-w-1",
            "display_name": "Test Weapon",
            "graph_target": {"entity_type": entity_type or "weapon", "canonical_id": "ds-w-1"},
        }]

    def registered_entity(self, entity_type, canonical_id):
        return {
            "graph_target": {"entity_type": entity_type, "canonical_id": str(canonical_id)},
        }

    @staticmethod
    def recent_entities():
        return []


class LazyEntityRegistryStartupTests(unittest.TestCase):
    def test_model_construction_does_not_rebuild_registry(self):
        graph = _Graph()
        model = RegistrySelectorModel(graph)
        self.assertEqual(graph.rebuilds, 0)
        self.assertEqual(model.entity_types(), ("weapon", "armor"))

    def test_known_canonical_id_routes_without_registry_rebuild(self):
        graph = _Graph()
        model = RegistrySelectorModel(graph)
        target = model.target_for_choice("Last Valor [ds-w-1]", entity_type="weapon")
        self.assertEqual(target, {"entity_type": "weapon", "canonical_id": "ds-w-1"})
        self.assertEqual(graph.rebuilds, 0)
        self.assertEqual(model.recent(), [])
        self.assertEqual(graph.rebuilds, 0)

    def test_first_browse_builds_registry_once(self):
        graph = _Graph()
        model = RegistrySelectorModel(graph)
        rows = model.search("test", entity_type="weapon")
        self.assertEqual(len(rows), 1)
        self.assertEqual(graph.rebuilds, 1)
        self.assertEqual(graph.searches, 1)
        model.search("again", entity_type="weapon")
        self.assertEqual(graph.rebuilds, 1)
        self.assertEqual(graph.searches, 2)


if __name__ == "__main__":
    unittest.main()
