"""Phase 16 performance probes and release-gate diagnostics.

This module never publishes a release. It measures local trace behavior and audits
already-built assets/manifests so publication remains an explicit final action.
"""
from __future__ import annotations

import hashlib
import json
import time
import tracemalloc
from pathlib import Path
from typing import Any

from dead_signal_generalized_graph import DeadSignalGeneralizedGraph

SCHEMA_VERSION = 1
DEFAULT_TRACE_SAMPLE_LIMIT = 20


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def benchmark_real_snapshot(output: Path | str, *, sample_limit: int = DEFAULT_TRACE_SAMPLE_LIMIT) -> dict[str, Any]:
    """Measure cold/warm trace latency and Python allocation peak on a local snapshot."""
    root = Path(output).expanduser().resolve()
    engine = DeadSignalGeneralizedGraph(root)
    engine.rebuild_entity_registry()
    rows = engine.search_entities("", limit=max(1, min(int(sample_limit), 100)))
    samples: list[dict[str, Any]] = []
    for row in rows:
        entity_type = row.get("entity_type")
        canonical_id = row.get("canonical_id")
        if not entity_type or not canonical_id:
            continue
        tracemalloc.start()
        cold_start = time.perf_counter()
        engine.entity_graph(entity_type, canonical_id, use_cache=False)
        cold_seconds = time.perf_counter() - cold_start
        _current, cold_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        warm_start = time.perf_counter()
        engine.entity_graph(entity_type, canonical_id, use_cache=True)
        # First cache-enabled call seeds the dependency-aware cache.
        seed_seconds = time.perf_counter() - warm_start
        hit_start = time.perf_counter()
        engine.entity_graph(entity_type, canonical_id, use_cache=True)
        hit_seconds = time.perf_counter() - hit_start
        meta = dict(engine.last_trace_meta)
        samples.append({
            "entity_type": entity_type,
            "canonical_id": canonical_id,
            "cold_seconds": cold_seconds,
            "cache_seed_seconds": seed_seconds,
            "warm_hit_seconds": hit_seconds,
            "warm_cache_status": meta.get("cache_status"),
            "cold_peak_bytes": cold_peak,
        })
    def avg(key: str) -> float:
        values = [float(row[key]) for row in samples]
        return sum(values) / len(values) if values else 0.0
    report = {
        "schema": "dead-signal-phase16-performance",
        "schema_version": SCHEMA_VERSION,
        "sample_count": len(samples),
        "averages": {
            "cold_seconds": avg("cold_seconds"),
            "cache_seed_seconds": avg("cache_seed_seconds"),
            "warm_hit_seconds": avg("warm_hit_seconds"),
            "cold_peak_bytes": avg("cold_peak_bytes"),
        },
        "warm_hits": sum(row.get("warm_cache_status") == "HIT" for row in samples),
        "samples": samples,
    }
    target = root / "reports" / "phase16-performance.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def audit_release_asset(zip_path: Path | str, manifest_path: Path | str) -> dict[str, Any]:
    """Fail closed unless a verified public ZIP matches the updater manifest."""
    archive = Path(zip_path).expanduser().resolve()
    manifest = Path(manifest_path).expanduser().resolve()
    blockers: list[str] = []
    if archive.name.casefold() == "miner.zip" or "tools/miner.zip" in archive.as_posix().casefold():
        blockers.append("tools/miner.zip-is-not-a-release-asset")
    if not archive.is_file():
        blockers.append("public-zip-missing")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        payload = {}
        blockers.append("manifest-missing-or-invalid")
    actual_hash = _sha256(archive) if archive.is_file() else ""
    actual_size = archive.stat().st_size if archive.is_file() else 0
    expected_hash = str(payload.get("sha256") or "").lower()
    expected_size = int(payload.get("size") or 0)
    if archive.is_file() and expected_hash != actual_hash.lower():
        blockers.append("public-zip-sha256-mismatch")
    if archive.is_file() and expected_size != actual_size:
        blockers.append("public-zip-size-mismatch")
    if archive.is_file() and manifest.is_file() and manifest.stat().st_mtime < archive.stat().st_mtime:
        # Manifest must be written/published after the verified asset.
        blockers.append("manifest-predates-public-zip")
    return {
        "schema": "dead-signal-phase16-release-audit",
        "schema_version": SCHEMA_VERSION,
        "ready": not blockers,
        "blockers": sorted(set(blockers)),
        "archive": str(archive),
        "manifest": str(manifest),
        "actual_sha256": actual_hash,
        "actual_size": actual_size,
        "manifest_sha256": expected_hash,
        "manifest_size": expected_size,
    }
