from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

MINER = Path(__file__).resolve().parents[1]
SRC = MINER / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class EvidenceGraphPhaseThirteenInterfaceTests(unittest.TestCase):
    def test_new_interface_modules_parse(self):
        for name in ("dead_signal_generalized_workspace.py", "dead_signal_phase13_shell.py"):
            source = (SRC / name).read_text(encoding="utf-8")
            ast.parse(source, filename=name)

    def test_generalized_renderer_routes_any_registered_entity(self):
        source = (SRC / "dead_signal_generalized_workspace.py").read_text(encoding="utf-8")
        self.assertIn('self.engine.entity_graph(target["entity_type"],target["canonical_id"])', source)
        self.assertNotIn('target.get("entity_type") != "weapon"', source)
        self.assertIn("CLAIM ASSESSMENT / PROVENANCE", source)
        self.assertIn("navigation_targets", source)
        self.assertIn("RECOMPUTE", source)
        self.assertIn("OPEN REVIEW QUEUE", source)

    def test_shell_exposes_phase13_navigation_contract(self):
        source = (SRC / "dead_signal_phase13_shell.py").read_text(encoding="utf-8")
        for label in (
            "INTELLIGENCE", "Overview", "Evidence Graph", "Review Queue",
            "OPERATIONS", "Run Pipeline", "Resolvers", "Publication", "Reports",
        ):
            self.assertIn(label, source)

    def test_review_queue_opens_exact_entity_in_graph(self):
        source = (SRC / "dead_signal_phase13_shell.py").read_text(encoding="utf-8")
        self.assertIn('app.generalized_evidence.set_target(entity_type, canonical_id)', source)
        self.assertIn('app._show_workspace("Evidence Graph")', source)

    def test_bootstrap_packages_phase13_modules(self):
        source = (SRC / "miner_entry.py").read_text(encoding="utf-8")
        self.assertIn('"dead_signal_generalized_workspace"', source)
        self.assertIn('"dead_signal_phase13_shell"', source)
        self.assertIn("install_phase13_shell", source)
        self.assertIn("_build_ui_with_phase13_shell", source)

    def test_phase13_is_presentation_only(self):
        source = (SRC / "dead_signal_generalized_workspace.py").read_text(encoding="utf-8")
        self.assertNotIn("publication_authority = True", source)
        self.assertNotIn('"PROVEN" if', source)
        self.assertIn("self.engine.assess_claim", source)
        self.assertIn("evidence_review_queue", source)


if __name__ == "__main__":
    unittest.main()
