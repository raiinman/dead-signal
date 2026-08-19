"""Phase-0 compatibility checks for the weapon Evidence Graph.

The baseline protects graph semantics while the expansion introduces generalized
entities and domain adapters. Performance values are observations, not gates.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from dead_signal_evidence_graph import DeadSignalEvidenceGraph


BASELINE_SCHEMA = "dead-signal-evidence-graph-phase-0-baseline"
BASELINE_VERSION = 1
REQUIRED_GRAPH_KEYS = ("schema", "schema_version", "brand", "subject", "record_counts", "nodes", "edges", "policy")
REQUIRED_COUNTS = ("nodes", "edges", "exact_occurrences")
REQUIRED_POLICY_KEYS = ("edges", "discovery", "publication")


def validate_weapon_graph_compatibility(payload: dict[str, Any]) -> list[str]:
    """Return compatibility violations without mutating or promoting evidence."""
    errors: list[str] = []
    for key in REQUIRED_GRAPH_KEYS:
        if key not in payload:
            errors.append(f"missing top-level key: {key}")
    if payload.get("schema") != "dead-signal-evidence-graph":
        errors.append("weapon graph schema changed")
    if payload.get("brand") != "Dead Signal":
        errors.append("brand changed")
    subject = payload.get("subject") or {}
    if subject.get("type") != "weapon":
        errors.append("subject.type must remain weapon during Phase 0")
    counts = payload.get("record_counts") or {}
    for key in REQUIRED_COUNTS:
        if not isinstance(counts.get(key), int) or counts.get(key) < 0:
            errors.append(f"invalid record count: {key}")
    nodes = payload.get("nodes") or []
    edges = payload.get("edges") or []
    if not any(row.get("kind") == "weapon" for row in nodes if isinstance(row, dict)):
        errors.append("missing weapon root node")
    if any(not row.get("authoritative") for row in edges if isinstance(row, dict)):
        errors.append("non-authoritative edge entered exact weapon graph")
    policy = payload.get("policy") or {}
    for key in REQUIRED_POLICY_KEYS:
        if not str(policy.get(key) or "").strip():
            errors.append(f"missing policy statement: {key}")
    return errors


def canonical_graph_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def measure_weapon_baseline(output: Path | str, fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    """Measure representative traces from one completed local snapshot."""
    root = Path(output).expanduser().resolve()
    graph = DeadSignalEvidenceGraph(root)
    measurements = []
    for fixture in fixtures:
        started = time.perf_counter()
        payload = graph.weapon_graph(fixture["canonical_id"])
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        errors = validate_weapon_graph_compatibility(payload)
        if errors:
            raise ValueError(f"{fixture['canonical_id']} failed compatibility: {errors}")
        measurements.append({
            **fixture,
            "observed_name": (payload.get("subject") or {}).get("name"),
            "elapsed_ms_observed": elapsed_ms,
            "record_counts": payload.get("record_counts"),
            "canonical_graph_sha256": canonical_graph_hash(payload),
        })
    web = root / "published" / "web"
    tracer = root / "published" / "indexes" / "reference-tracer.sqlite"
    return {
        "schema": BASELINE_SCHEMA,
        "schema_version": BASELINE_VERSION,
        "source": "completed-local-miner-snapshot",
        "fixtures": measurements,
        "artifact_bytes": {
            "weapons_json": (web / "weapons.json").stat().st_size,
            "relationship_graph_json": (web / "relationship-graph.json").stat().st_size,
            "reference_tracer_sqlite": tracer.stat().st_size,
        },
        "compatibility": {
            "required_graph_keys": list(REQUIRED_GRAPH_KEYS),
            "required_record_counts": list(REQUIRED_COUNTS),
            "required_policy_keys": list(REQUIRED_POLICY_KEYS),
            "authoritative_edges_only": True,
            "performance_values_are_release_information_not_test_thresholds": True,
        },
    }
