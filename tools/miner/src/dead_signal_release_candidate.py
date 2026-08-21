"""Final real-snapshot release-candidate validation for Dead Signal Miner.

This module never publishes assets or edits the updater manifest. It validates the
actual local Miner snapshot and writes one deterministic packaging gate report.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dead_signal_evidence_contracts import validate_generalized_graph
from dead_signal_false_proof_benchmark import audit_adapter_contracts
from dead_signal_generalized_graph import DeadSignalGeneralizedGraph
from dead_signal_performance_release import benchmark_real_snapshot

SCHEMA = "dead-signal-release-candidate-validation"
SCHEMA_VERSION = 1


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def validate_real_snapshot(output: Path | str, *, sample_per_domain: int = 3, performance_sample: int = 20) -> dict[str, Any]:
    root = Path(output).expanduser().resolve()
    blockers: list[str] = []
    state = _load(root / "last-run.json")
    if not state:
        blockers.append("last-run-missing-or-invalid")

    engine = DeadSignalGeneralizedGraph(root)
    try:
        registry = engine.rebuild_entity_registry()
    except Exception as exc:
        registry = {"total": 0, "by_entity_type": {}}
        blockers.append(f"registry-rebuild-failed:{type(exc).__name__}:{exc}")

    contract_audit = audit_adapter_contracts(engine.registry.adapters())
    if not contract_audit.get("ok"):
        blockers.append("adapter-contract-audit-failed")

    domains = tuple(engine.registry.entity_types())
    smoke_rows: list[dict[str, Any]] = []
    for domain in domains:
        rows = engine.search_entities("", entity_type=domain, limit=max(1, min(int(sample_per_domain), 10)))
        if not rows:
            blockers.append(f"domain-has-no-registered-entities:{domain}")
            continue
        for row in rows:
            canonical_id = row.get("canonical_id")
            try:
                graph = engine.entity_graph(domain, canonical_id, use_cache=False)
                errors = validate_generalized_graph(graph)
                smoke_rows.append({"entity_type": domain, "canonical_id": canonical_id, "ok": not errors, "errors": errors})
                if errors:
                    blockers.append(f"invalid-generalized-graph:{domain}:{canonical_id}")
            except Exception as exc:
                smoke_rows.append({"entity_type": domain, "canonical_id": canonical_id, "ok": False, "errors": [f"{type(exc).__name__}: {exc}"]})
                blockers.append(f"trace-failed:{domain}:{canonical_id}")

    try:
        performance = benchmark_real_snapshot(root, sample_limit=max(1, min(int(performance_sample), 100)))
    except Exception as exc:
        performance = {"sample_count": 0, "warm_hits": 0, "error": f"{type(exc).__name__}: {exc}"}
        blockers.append("performance-benchmark-failed")
    sample_count = int(performance.get("sample_count") or 0)
    warm_hits = int(performance.get("warm_hits") or 0)
    if sample_count <= 0:
        blockers.append("performance-sample-empty")
    elif warm_hits != sample_count:
        blockers.append("warm-cache-hit-coverage-incomplete")

    report = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "ready_for_packaging": not blockers,
        "blockers": sorted(set(blockers)),
        "snapshot": {
            "last_run_present": bool(state),
            "registry_total": int(registry.get("total") or 0),
            "by_entity_type": registry.get("by_entity_type") or {},
        },
        "adapter_contract_audit": contract_audit,
        "smoke": {
            "sample_per_domain": max(1, min(int(sample_per_domain), 10)),
            "checked": len(smoke_rows),
            "passed": sum(bool(row.get("ok")) for row in smoke_rows),
            "rows": smoke_rows,
        },
        "performance": performance,
        "release_policy": {
            "source_suite_external_gate_required": True,
            "windows_build_external_gate_required": True,
            "packaged_self_test_external_gate_required": True,
            "phase15_false_proven_target": 0,
            "manifest_may_be_published": False,
            "next_gate": "build-and-verify-public-release-zip" if not blockers else "resolve-real-snapshot-blockers",
        },
    }
    target = root / "reports" / "release-candidate-validation.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Validate a real Dead Signal Miner snapshot before packaging.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--sample-per-domain", type=int, default=3)
    parser.add_argument("--performance-sample", type=int, default=20)
    args = parser.parse_args(argv)
    report = validate_real_snapshot(args.output, sample_per_domain=args.sample_per_domain, performance_sample=args.performance_sample)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready_for_packaging"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
