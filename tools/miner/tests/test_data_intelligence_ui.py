from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_compiler_tab import _format_elapsed  # noqa: E402
from dead_signal_intelligence_window import configure_data_intelligence_styles  # noqa: E402
from dead_signal_miner import PIPELINE_STAGES  # noqa: E402


class FakeStyle:
    def __init__(self):
        self.configured = []
        self.mapped = []

    def configure(self, name, **kwargs):
        self.configured.append((name, kwargs))

    def map(self, name, **kwargs):
        self.mapped.append((name, kwargs))


class DataIntelligenceUiTests(unittest.TestCase):
    def test_notebook_style_uses_ttk_widget_class_suffix(self):
        style = FakeStyle()
        configure_data_intelligence_styles(style)
        configured = {name for name, _kwargs in style.configured}
        mapped = {name for name, _kwargs in style.mapped}

        self.assertIn("DSI.TNotebook", configured)
        self.assertIn("DSI.TNotebook.Tab", configured)
        self.assertIn("DSI.TNotebook.Tab", mapped)
        self.assertNotIn("DSI.Notebook", configured)
        self.assertNotIn("DSI.Notebook.Tab", configured)

    def test_window_constructs_notebook_with_valid_custom_style_name(self):
        source = (SRC / "dead_signal_intelligence_window.py").read_text(encoding="utf-8")
        self.assertIn('ttk.Notebook(self.window, style="DSI.TNotebook")', source)
        self.assertNotIn('style="DSI.Notebook"', source)

    def test_compiler_tab_exposes_live_activity_telemetry(self):
        source = (SRC / "dead_signal_compiler_tab.py").read_text(encoding="utf-8")
        self.assertIn('text="LIVE ACTIVITY"', source)
        self.assertIn('self.detail_var', source)
        self.assertIn('self.elapsed_var', source)
        self.assertIn('self.heartbeat_var', source)
        self.assertIn('activity=lambda value:', source)
        self.assertEqual("00:00", _format_elapsed(0))
        self.assertEqual("01:05", _format_elapsed(65))
        self.assertEqual("1:01:01", _format_elapsed(3661))

    def test_window_exposes_existing_runtime_coverage_tab(self):
        source = (SRC / "dead_signal_intelligence_window.py").read_text(encoding="utf-8")
        self.assertIn('self._build_coverage(notebook)', source)
        self.assertIn('"Launch Coverage"', source)
        self.assertIn('dead-signal-coverage-dashboard.json', source)

    def test_miner_shell_combines_work_into_three_workspaces(self):
        source = (SRC / "dead_signal_miner.py").read_text(encoding="utf-8")
        self.assertIn('self._build_run_workspace()', source)
        self.assertIn('self._build_explore_workspace()', source)
        self.assertIn('self._build_publish_workspace()', source)
        self.assertIn('RUN COMPLETE PIPELINE', source)
        self.assertIn('compile_intelligence(', source)
        self.assertIn('self_test()', source)
        self.assertEqual(
            ("MINE", "INDEX", "RESOLVE", "COMPILE", "VERIFY"),
            tuple(stage[0] for stage in PIPELINE_STAGES),
        )


if __name__ == "__main__":
    unittest.main()
