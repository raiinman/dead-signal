from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
EXTRACTOR = SRC / "extractor"
NEOXTRACTOR = SRC / "neoxtractor"
for root in (SRC, EXTRACTOR, NEOXTRACTOR):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

import miner_entry  # noqa: E402


class _Button:
    def __init__(self):
        self.calls = []

    def configure(self, **kwargs):
        self.calls.append(kwargs)


class MinerUiLifecycleTests(unittest.TestCase):
    def test_terminal_idle_transition_clears_worker_handle(self):
        app = miner_entry._miner_ui.DeadSignalMinerApp.__new__(miner_entry._miner_ui.DeadSignalMinerApp)
        app.worker = object()
        app.start_button = _Button()
        app.cancel_button = _Button()
        app.update_button = _Button()

        app._set_idle_buttons()

        self.assertIsNone(app.worker)
        self.assertEqual("normal", app.start_button.calls[-1]["state"])
        self.assertEqual("disabled", app.cancel_button.calls[-1]["state"])
        self.assertEqual("normal", app.update_button.calls[-1]["state"])


if __name__ == "__main__":
    unittest.main()
