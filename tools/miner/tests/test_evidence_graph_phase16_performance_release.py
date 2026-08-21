from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_graph_runtime import AdapterResultCache, TraceRuntime
from dead_signal_performance_release import audit_release_asset


def graph(dep: str = "game_common/data/item_data.json") -> dict:
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
            "source_records": [{"table": dep, "record": "1"}],
        },
        "claims": [{
            "schema_version": 1,
            "claim_type": "test.identity",
            "subject": {"canonical_id": "test-1"},
            "result": "PROVEN",
            "requirements": ["exact owner"],
            "evidence": [{"table": dep, "record": "1"}],
            "missing": [],
            "conflicts": [],
            "dependencies": [dep],
        }],
        "edges": [],
        "assessment": {
            "schema_version": 1,
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
        "compatibility": {
            "legacy_weapon_graph_unchanged": True,
            "publication_authority": False,
        },
    }


def snapshot(tmp_path: Path) -> Path:
    output = tmp_path / "out"
    base = output / "base" / "game_common" / "data"
    base.mkdir(parents=True)
    (base / "item_data.json").write_text('{"1":{"name":"A"}}', encoding="utf-8")
    (output / "last-run.json").write_text(
        json.dumps({
            "base": str(output / "base"),
            "current": str(output / "current"),
            "published": str(output / "published"),
        }),
        encoding="utf-8",
    )
    return output


class Phase16PerformanceReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._temporary.name)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def test_dependency_aware_cache_hits_only_while_owner_is_unchanged(self):
        output = snapshot(self.tmp_path)
        cache = AdapterResultCache(output)
        payload = graph()
        cache.put("test", "test-1", {}, payload)
        self.assertEqual(cache.get("test", "test-1", {}), payload)

        owner = output / "base" / "game_common" / "data" / "item_data.json"
        owner.write_text('{"1":{"name":"B"}}', encoding="utf-8")
        self.assertIsNone(cache.get("test", "test-1", {}))

    def test_concurrent_cache_writes_are_serialized_without_lost_entries(self):
        output = snapshot(self.tmp_path)
        cache = AdapterResultCache(output, max_entries=64)
        payload = graph()
        identities = [f"entity-{index}" for index in range(24)]

        def write(identity: str) -> None:
            cache.put("test", identity, {}, payload)

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(write, identities))

        persisted = cache.load()
        self.assertEqual(len(persisted.get("entries") or {}), len(identities))
        leftovers = list(cache.path.parent.glob(f".{cache.path.name}.*.tmp"))
        self.assertEqual(leftovers, [])

    def test_trace_runtime_reports_miss_then_hit_and_can_cancel(self):
        output = snapshot(self.tmp_path)
        runtime = TraceRuntime(output)
        calls = {"count": 0}

        def resolve():
            calls["count"] += 1
            return graph()

        first = runtime.run(resolve, entity_type="test", identity="test-1", kwargs={})
        second = runtime.run(resolve, entity_type="test", identity="test-1", kwargs={})
        self.assertEqual(first.cache_status, "MISS")
        self.assertEqual(second.cache_status, "HIT")
        self.assertEqual(calls["count"], 1)

        cancelled = Event()
        cancelled.set()
        with self.assertRaises(InterruptedError):
            runtime.run(
                resolve,
                entity_type="test",
                identity="test-2",
                kwargs={},
                cancel_event=cancelled,
            )

    def test_trace_timeout_fails_closed(self):
        output = snapshot(self.tmp_path)
        runtime = TraceRuntime(output)

        def slow():
            time.sleep(0.02)
            return graph()

        with self.assertRaises(TimeoutError):
            runtime.run(
                slow,
                entity_type="test",
                identity="slow",
                kwargs={},
                use_cache=False,
                timeout_seconds=0.001,
            )

    def test_release_audit_requires_hash_size_and_manifest_after_asset(self):
        archive = self.tmp_path / "Dead-Signal-Miner-v9-Windows.zip"
        archive.write_bytes(b"verified asset")
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        manifest = self.tmp_path / "latest.json"
        manifest.write_text(
            json.dumps({"sha256": digest, "size": archive.stat().st_size}),
            encoding="utf-8",
        )

        now = time.time()
        os.utime(archive, (now - 2, now - 2))
        os.utime(manifest, (now, now))
        self.assertTrue(audit_release_asset(archive, manifest)["ready"])

        manifest.write_text(
            json.dumps({"sha256": "0" * 64, "size": 1}),
            encoding="utf-8",
        )
        failed = audit_release_asset(archive, manifest)
        self.assertFalse(failed["ready"])
        self.assertIn("public-zip-sha256-mismatch", failed["blockers"])
        self.assertIn("public-zip-size-mismatch", failed["blockers"])

    def test_release_audit_protects_tools_miner_zip(self):
        protected = self.tmp_path / "tools" / "miner.zip"
        protected.parent.mkdir(parents=True)
        protected.write_bytes(b"do-not-release")
        manifest = self.tmp_path / "latest.json"
        manifest.write_text(
            json.dumps({
                "sha256": hashlib.sha256(protected.read_bytes()).hexdigest(),
                "size": protected.stat().st_size,
            }),
            encoding="utf-8",
        )
        failed = audit_release_asset(protected, manifest)
        self.assertFalse(failed["ready"])
        self.assertIn("tools/miner.zip-is-not-a-release-asset", failed["blockers"])


if __name__ == "__main__":
    unittest.main()
