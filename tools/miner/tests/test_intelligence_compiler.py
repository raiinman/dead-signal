from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import dead_signal_intelligence_compiler as compiler  # noqa: E402


class IntelligenceCompilerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.root / "snapshots" / "base"
        self.current = self.root / "snapshots" / "current"
        self.base.mkdir(parents=True)
        self.current.mkdir(parents=True)
        published = self.root / "published"
        (published / "data").mkdir(parents=True)
        (published / "reports").mkdir(parents=True)
        (published / "indexes").mkdir(parents=True)
        (self.root / "catalogs").mkdir(parents=True)
        (published / "data" / "weapons.json").write_text(
            json.dumps({"weapons": [{"blueprint_id": 100, "name": "Test Weapon"}]}), encoding="utf-8"
        )
        (self.root / "last-run.json").write_text(json.dumps({
            "active_snapshots": {"base": str(self.base), "current": str(self.current)},
            "published": str(published),
        }), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_resolve_snapshot_uses_completed_run_metadata(self):
        resolved = compiler.resolve_snapshot(self.root)
        self.assertEqual(self.base.resolve(), resolved["base"])
        self.assertEqual(self.current.resolve(), resolved["current"])
        self.assertEqual(self.root / "published" / "data" / "weapons.json", resolved["weapons"])

    def test_resolve_snapshot_rejects_incomplete_folder(self):
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(ValueError):
                compiler.resolve_snapshot(Path(empty))

    @mock.patch.object(compiler, "build_gate_report")
    @mock.patch.object(compiler, "DeadSignalAnalytics")
    @mock.patch.object(compiler, "DeadSignalDiscovery")
    @mock.patch.object(compiler, "run_research_suite")
    def test_compile_runs_extensions_and_builds_uploadable_bundle(
        self, research_mock, discovery_class, analytics_class, gate_mock
    ):
        reports = self.root / "published" / "reports"

        def research_side_effect(base, current, weapons, reports_dir):
            payload = {
                "record_counts": {
                    "weapons": 120,
                    "profiled_tables": 42,
                    "source_finder_states": {"CANDIDATE": 3, "UNRESOLVED": 117},
                }
            }
            (reports_dir / "dead-signal-research-suite.json").write_text(json.dumps(payload), encoding="utf-8")
            (reports_dir / "dead-signal-table-profiles.json").write_text(json.dumps({"tables": []}), encoding="utf-8")
            (reports_dir / "dead-signal-source-finder.json").write_text(json.dumps({"weapons": []}), encoding="utf-8")
            return payload

        research_mock.side_effect = research_side_effect
        discovery = discovery_class.return_value
        discovery.run_all.return_value = {
            "schema_clusters": {"record_counts": {"tables": 42}},
            "description_hotspots": {"record_counts": {"hotspots": 5}},
        }
        (reports / "dead-signal-discovery.json").write_text("{}", encoding="utf-8")

        analytics = analytics_class.return_value
        analytics.build.return_value = {"rows": {"source_finder": 3, "table_profiles": 42}}
        analytics.description_leads.return_value = {"row_count": 3, "rows": []}
        analytics.suspicious_description_fields.return_value = {"row_count": 8, "rows": []}
        gate_mock.return_value = {"record_counts": {"publishable_candidates": 0}}

        progress = []
        result = compiler.compile_intelligence(
            self.root,
            progress=lambda value, label: progress.append((value, label)),
        )

        self.assertEqual(42, result["record_counts"]["profiled_tables"])
        self.assertEqual(5, result["record_counts"]["description_hotspots"])
        self.assertEqual(3, result["record_counts"]["description_leads"])
        self.assertEqual(0, result["record_counts"]["publishable_candidates"])
        self.assertEqual(100, progress[-1][0])
        archive = Path(result["bundle"])
        self.assertTrue(archive.is_file())
        with zipfile.ZipFile(archive) as bundle:
            names = set(bundle.namelist())
        self.assertIn("dead-signal-intelligence-compiled.json", names)
        self.assertIn("published/reports/dead-signal-description-leads.json", names)
        self.assertIn("published/data/weapons.json", names)
        self.assertTrue((reports / "dead-signal-intelligence-compiled.json").is_file())


if __name__ == "__main__":
    unittest.main()
