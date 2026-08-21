from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import dead_signal_entity_selector as selector


class PackagedStartupContractTests(unittest.TestCase):
    def test_selector_constructor_does_not_refresh_registry(self):
        source = inspect.getsource(selector.EntityRegistrySelector.__init__)
        self.assertNotIn("self.refresh()", source)

    def test_initial_selection_is_deferred(self):
        source = inspect.getsource(selector.EntityRegistrySelector.set_initial)
        self.assertNotIn("self.model.search", source)
        self.assertIn("REGISTRY DEFERRED", source)


if __name__ == "__main__":
    unittest.main()
