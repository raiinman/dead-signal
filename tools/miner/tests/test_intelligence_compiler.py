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
            json.dumps({"weapons": [{"blueprint_id": 100, "prototype_id": 300, "name": "Test Weapon"}]}), encoding="utf-8"
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
        self.assertEqual((self.root / "published" / "data" / "weapons.json").resolve(), resolved["weapons"].resolve())

    def test_resolve_snapshot_rejects_incomplete_folder(self):
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(ValueError):
                compiler.resolve_snapshot(Path(empty))

    @mock.patch.object(compiler, "build_gate_report")
    @mock.patch.object(compiler, "DeadSignalAnalytics")
    @mock.patch.object(compiler, "DeadSignalDiscovery")
    @mock.patch.object(compiler, "run_research_suite")
    @mock.patch.object(compiler, "run_weapon_description_consumer_trace")
    def test_compile_runs_extensions_builds_bundle_and_reports_activity(
        self, consumer_mock, research_mock, discovery_class, analytics_class, gate_mock
    ):
        reports = self.root / "published" / "reports"

        def consumer_side_effect(base, current, weapons, reports_dir, *, activity=None):
            if activity:
                activity("UI Consumer Trace: resolved 120/120 weapons")
            payload = {"record_counts": {
                "weapons": 120,
                "prototype_desc_fields_found": 90,
                "consistent_resolutions": 88,
                "consumer_backed_candidates": 84,
            }}
            (reports_dir / "weapon-description-ui-consumer-trace.json").write_text(json.dumps(payload), encoding="utf-8")
            return payload

        consumer_mock.side_effect = consumer_side_effect

        def research_side_effect(base, current, weapons, reports_dir, *, activity=None):
            if activity:
                activity("Multi-hop Resolver 1/120: Test Weapon")
                activity("Table Profiler 1/2: gun_alpha.json")
                activity("Table Profiler 2/2: weapon_beta.json")
            payload = {
                "record_counts": {
                    "weapons": 120,
                    "profiled_tables": 42,
                    "source_finder_states": {"CANDIDATE": 3, "UNRESOLVED": 117},
                    "multihop_candidates": 7,
                    "multihop_expanded_records": 321,
                }
            }
            (reports_dir / "dead-signal-research-suite.json").write_text(json.dumps(payload), encoding="utf-8")
            (reports_dir / "weapon-description-multihop.json").write_text(json.dumps({"weapons": []}), encoding="utf-8")
            (reports_dir / "weapon-description-combined-investigation.json").write_text(json.dumps({"weapons": []}), encoding="utf-8")
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
        activity = []
        result = compiler.compile_intelligence(
            self.root,
            progress=lambda value, label: progress.append((value, label)),
            activity=activity.append,
        )

        self.assertEqual(84, result["record_counts"]["ui_consumer_candidates"])
        self.assertEqual(90, result["record_counts"]["prototype_desc_fields_found"])
        self.assertEqual(88, result["record_counts"]["prototype_desc_resolved"])
        self.assertEqual(42, result["record_counts"]["profiled_tables"])
        self.assertEqual(7, result["record_counts"]["multihop_candidates"])
        self.assertEqual(321, result["record_counts"]["multihop_expanded_records"])
        self.assertEqual(5, result["record_counts"]["description_hotspots"])
        self.assertEqual(3, result["record_counts"]["description_leads"])
        self.assertEqual(0, result["record_counts"]["publishable_candidates"])
        self.assertEqual(100, progress[-1][0])
        self.assertTrue(any("Starting Weapon UI Consumer Trace" in line for line in activity))
        self.assertTrue(any("UI Consumer Trace: resolved 120/120" in line for line in activity))
        self.assertTrue(any("Starting Research Suite" in line for line in activity))
        self.assertTrue(any("Multi-hop Resolver 1/120" in line for line in activity))
        self.assertTrue(any("Starting Analytics Warehouse" in line for line in activity))
        self.assertTrue(any("Bundle" in line for line in activity))
        archive = Path(result["bundle"])
        self.assertTrue(archive.is_file())
        with zipfile.ZipFile(archive) as bundle:
            names = set(bundle.namelist())
        self.assertIn("dead-signal-intelligence-compiled.json", names)
        self.assertIn("published/reports/weapon-description-ui-consumer-trace.json", names)
        self.assertIn("published/reports/weapon-description-multihop.json", names)
        self.assertIn("published/reports/dead-signal-description-leads.json", names)
        self.assertIn("published/data/weapons.json", names)
        self.assertTrue((reports / "dead-signal-intelligence-compiled.json").is_file())

    @mock.patch.object(compiler, "DeadSignalAnalytics")
    @mock.patch.object(compiler, "DeadSignalDiscovery")
    @mock.patch.object(compiler, "run_research_suite")
    @mock.patch.object(compiler, "run_weapon_description_consumer_trace")
    def test_fast_ui_trace_does_not_run_full_research_stack(
        self, consumer_mock, research_mock, discovery_class, analytics_class
    ):
        reports = self.root / "published" / "reports"

        def consumer_side_effect(base, current, weapons, reports_dir, *, activity=None):
            payload = {"record_counts": {
                "weapons": 120,
                "prototype_desc_fields_found": 87,
                "consistent_resolutions": 85,
                "consumer_backed_candidates": 81,
            }}
            (reports_dir / "weapon-description-ui-consumer-trace.json").write_text(json.dumps(payload), encoding="utf-8")
            if activity:
                activity("UI Consumer Trace complete: 81 candidates")
            return payload

        consumer_mock.side_effect = consumer_side_effect
        activity = []
        result = compiler.compile_weapon_description_ui_trace(self.root, activity=activity.append)

        self.assertEqual(81, result["record_counts"]["consumer_backed_candidates"])
        self.assertEqual(100, result["record_counts"]["weapons"] - 20)
        research_mock.assert_not_called()
        discovery_class.assert_not_called()
        analytics_class.assert_not_called()
        archive = Path(result["bundle"])
        self.assertTrue(archive.is_file())
        self.assertTrue(archive.name.startswith("Dead-Signal-Weapon-UI-Trace-"))
        with zipfile.ZipFile(archive) as bundle:
            names = set(bundle.namelist())
        self.assertIn("dead-signal-weapon-ui-trace-summary.json", names)
        self.assertIn("published/reports/weapon-description-ui-consumer-trace.json", names)
        self.assertIn("published/data/weapons.json", names)
        self.assertTrue(any("UI Consumer Trace complete" in line for line in activity))


if __name__ == "__main__":
    unittest.main()