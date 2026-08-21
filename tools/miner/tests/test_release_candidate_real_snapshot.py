from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_release_candidate import validate_real_snapshot


def valid_graph() -> dict:
    return {
        "schema": "dead-signal-generalized-evidence-graph",
        "schema_version": 1,
        "brand": "Dead Signal",
        "entity": {
            "schema_version": 1,
            "entity_type": "test",
            "canonical_id": "test-1",
            "name": "Test",
            "classification": "synthetic",
            "identity_state": "PROVEN",
            "source_records": [{"table": "game_common/data/item_data.json", "record": "1"}],
        },
        "claims": [{
            "schema_version": 1,
            "claim_type": "test.identity",
            "subject": {"canonical_id": "test-1"},
            "result": "PROVEN",
            "requirements": ["exact owner"],
            "evidence": [{"table": "game_common/data/item_data.json", "record": "1"}],
            "missing": [],
            "conflicts": [],
            "dependencies": ["game_common/data/item_data.json"],
        }],
        "edges": [],
        "assessment": {
            "schema_version": 1,
            "result": "PROVEN",
            "claim_counts": {"PROVEN": 1, "PARTIAL": 0, "UNRESOLVED": 0, "NOT APPLICABLE": 0, "CONFLICT": 0},
            "missing": [],
            "conflicts": [],
        },
        "compatibility": {"publication_authority": False},
    }


class FakeRegistry:
    def entity_types(self):
        return ("test",)

    def get(self, _domain):
        return object()


class FakeEngine:
    def __init__(self, _output):
        self.registry = FakeRegistry()

    def rebuild_entity_registry(self):
        return {"total": 1, "by_entity_type": {"test": 1}}

    def search_entities(self, _query, *, entity_type=None, limit=100):
        return [{"entity_type": entity_type or "test", "canonical_id": "test-1"}][:limit]

    def entity_graph(self, _domain, _identity, **_kwargs):
        return valid_graph()


class ReleaseCandidateRealSnapshotTests(unittest.TestCase):
    def test_green_snapshot_writes_ready_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "last-run.json").write_text(json.dumps({"base": "base", "current": "current", "published": "published"}), encoding="utf-8")
            with patch("dead_signal_release_candidate.DeadSignalGeneralizedGraph", FakeEngine), \
                 patch("dead_signal_release_candidate.audit_adapter_contracts", return_value={"ok": True, "domains": []}), \
                 patch("dead_signal_release_candidate.benchmark_real_snapshot", return_value={"sample_count": 1, "warm_hits": 1, "samples": []}):
                report = validate_real_snapshot(output, sample_per_domain=1, performance_sample=1)
            self.assertTrue(report["ready_for_packaging"])
            self.assertEqual(report["blockers"], [])
            saved = json.loads((output / "reports" / "release-candidate-validation.json").read_text(encoding="utf-8"))
            self.assertTrue(saved["ready_for_packaging"])

    def test_missing_snapshot_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            with patch("dead_signal_release_candidate.DeadSignalGeneralizedGraph", FakeEngine), \
                 patch("dead_signal_release_candidate.audit_adapter_contracts", return_value={"ok": True, "domains": []}), \
                 patch("dead_signal_release_candidate.benchmark_real_snapshot", return_value={"sample_count": 1, "warm_hits": 1, "samples": []}):
                report = validate_real_snapshot(output, sample_per_domain=1, performance_sample=1)
            self.assertFalse(report["ready_for_packaging"])
            self.assertIn("last-run-missing-or-invalid", report["blockers"])

    def test_incomplete_warm_cache_coverage_blocks_packaging(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "last-run.json").write_text("{}", encoding="utf-8")
            with patch("dead_signal_release_candidate.DeadSignalGeneralizedGraph", FakeEngine), \
                 patch("dead_signal_release_candidate.audit_adapter_contracts", return_value={"ok": True, "domains": []}), \
                 patch("dead_signal_release_candidate.benchmark_real_snapshot", return_value={"sample_count": 2, "warm_hits": 1, "samples": []}):
                report = validate_real_snapshot(output, sample_per_domain=1, performance_sample=2)
            self.assertFalse(report["ready_for_packaging"])
            self.assertIn("warm-cache-hit-coverage-incomplete", report["blockers"])


if __name__ == "__main__":
    unittest.main()
