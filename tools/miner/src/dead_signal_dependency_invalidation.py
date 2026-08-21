"""Phase 11 dependency invalidation for generalized Evidence Graph claims.

This module compares persisted claim snapshots against current dependency
fingerprints and produces a bounded review/site-delta report. Historical proof is
retained as history only; any changed, removed, or conflicting dependency makes
the prior claim non-current until recomputed.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

SCHEMA = "dead-signal-claim-dependency-state"
SCHEMA_VERSION = 1
HISTORY_LIMIT = 20


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _claim_key(entity_type: str, canonical_id: str, claim_type: str) -> str:
    return f"{entity_type}:{canonical_id}:{claim_type}"


def _normalized_dependencies(claim: dict[str, Any]) -> list[str]:
    return sorted({str(value).strip() for value in claim.get("dependencies", []) if str(value or "").strip()})


def _claim_fingerprint(claim: dict[str, Any], dependency_fingerprints: dict[str, str]) -> str:
    dependencies = _normalized_dependencies(claim)
    return _hash({
        "claim_type": claim.get("claim_type"),
        "result": claim.get("result"),
        "requirements": claim.get("requirements", []),
        "evidence": claim.get("evidence", []),
        "missing": claim.get("missing", []),
        "conflicts": claim.get("conflicts", []),
        "dependencies": {name: dependency_fingerprints.get(name) for name in dependencies},
    })


def current_dependency_fingerprints(output: Path | str, dependencies: Iterable[str]) -> dict[str, str]:
    """Hash exact dependency files from the current Miner output/snapshot.

    Dependencies that do not resolve to files remain explicitly missing. This
    function never substitutes Base evidence for a missing Current dependency.
    """
    root = Path(output).expanduser().resolve()
    result: dict[str, str] = {}
    candidates: list[Path] = []
    last_run = root / "last-run.json"
    if last_run.is_file():
        try:
            state = json.loads(last_run.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            state = {}
        for key in ("current", "published"):
            value = state.get(key)
            if value:
                path = Path(value)
                if not path.is_absolute():
                    path = root / path
                candidates.append(path.resolve())
    candidates.extend((root / "current", root / "published", root))

    for dependency in sorted(set(str(value) for value in dependencies if str(value or "").strip())):
        found: Path | None = None
        for base in candidates:
            path = base / dependency
            if path.is_file():
                found = path
                break
        if found is None:
            result[dependency] = "MISSING"
            continue
        digest = hashlib.sha256()
        with found.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        result[dependency] = digest.hexdigest()
    return result


@dataclass(frozen=True)
class ClaimSnapshot:
    key: str
    entity_type: str
    canonical_id: str
    claim_type: str
    result: str
    dependencies: tuple[str, ...]
    dependency_fingerprints: dict[str, str]
    claim_fingerprint: str
    affected_pages: tuple[str, ...]


def snapshot_claim(
    graph: dict[str, Any],
    claim: dict[str, Any],
    dependency_fingerprints: dict[str, str],
    *,
    affected_pages: Iterable[str] = (),
) -> ClaimSnapshot:
    entity = graph.get("entity") or {}
    entity_type = str(entity.get("entity_type") or "")
    canonical_id = str(entity.get("canonical_id") or "")
    claim_type = str(claim.get("claim_type") or "")
    dependencies = tuple(_normalized_dependencies(claim))
    scoped = {name: dependency_fingerprints.get(name, "MISSING") for name in dependencies}
    return ClaimSnapshot(
        key=_claim_key(entity_type, canonical_id, claim_type),
        entity_type=entity_type,
        canonical_id=canonical_id,
        claim_type=claim_type,
        result=str(claim.get("result") or "UNRESOLVED"),
        dependencies=dependencies,
        dependency_fingerprints=scoped,
        claim_fingerprint=_claim_fingerprint(claim, scoped),
        affected_pages=tuple(sorted({str(value) for value in affected_pages if str(value or "").strip()})),
    )


class DependencyInvalidationStore:
    """Persistent, deterministic claim snapshot and invalidation store."""

    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        self.path = self.output / "catalogs" / "dead-signal-claim-dependencies.json"
        self.report_path = self.output / "reports" / "claim-invalidation.json"

    def load(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"schema": SCHEMA, "schema_version": SCHEMA_VERSION, "claims": {}, "history": []}
        if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
            raise ValueError("Invalid claim dependency store")
        return payload

    def evaluate(
        self,
        graphs: Iterable[dict[str, Any]],
        *,
        page_resolver: Callable[[str, str, str], Iterable[str]] | None = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        previous = self.load()
        old_claims = previous.get("claims") or {}
        if not isinstance(old_claims, dict):
            raise ValueError("Claim dependency store claims must be an object")

        graph_list = [graph for graph in graphs if isinstance(graph, dict)]
        dependency_names = {
            str(dep)
            for graph in graph_list
            for claim in graph.get("claims", [])
            if isinstance(claim, dict)
            for dep in claim.get("dependencies", [])
            if str(dep or "").strip()
        }
        fingerprints = current_dependency_fingerprints(self.output, dependency_names)
        current: dict[str, dict[str, Any]] = {}
        invalidated: list[dict[str, Any]] = []
        unchanged: list[str] = []
        recomputed: list[str] = []

        for graph in graph_list:
            entity = graph.get("entity") or {}
            entity_type = str(entity.get("entity_type") or "")
            canonical_id = str(entity.get("canonical_id") or "")
            for claim in graph.get("claims", []):
                if not isinstance(claim, dict):
                    continue
                claim_type = str(claim.get("claim_type") or "")
                pages = tuple(page_resolver(entity_type, canonical_id, claim_type)) if page_resolver else ()
                snap = snapshot_claim(graph, claim, fingerprints, affected_pages=pages)
                row = {
                    "entity_type": snap.entity_type,
                    "canonical_id": snap.canonical_id,
                    "claim_type": snap.claim_type,
                    "result": snap.result,
                    "dependencies": list(snap.dependencies),
                    "dependency_fingerprints": snap.dependency_fingerprints,
                    "claim_fingerprint": snap.claim_fingerprint,
                    "affected_pages": list(snap.affected_pages),
                    "current": True,
                }
                current[snap.key] = row
                old = old_claims.get(snap.key)
                if not isinstance(old, dict):
                    recomputed.append(snap.key)
                    continue
                changed_dependencies = sorted(
                    name for name in set(old.get("dependency_fingerprints", {})) | set(row["dependency_fingerprints"])
                    if (old.get("dependency_fingerprints") or {}).get(name) != row["dependency_fingerprints"].get(name)
                )
                if changed_dependencies:
                    invalidated.append({
                        "claim_key": snap.key,
                        "reason": "dependency-changed-or-removed",
                        "changed_dependencies": changed_dependencies,
                        "previous_result": old.get("result"),
                        "current_result": row.get("result"),
                        "affected_pages": row["affected_pages"],
                    })
                    recomputed.append(snap.key)
                elif old.get("claim_fingerprint") != row["claim_fingerprint"]:
                    invalidated.append({
                        "claim_key": snap.key,
                        "reason": "claim-evidence-changed",
                        "changed_dependencies": [],
                        "previous_result": old.get("result"),
                        "current_result": row.get("result"),
                        "affected_pages": row["affected_pages"],
                    })
                    recomputed.append(snap.key)
                else:
                    unchanged.append(snap.key)

        removed_keys = sorted(set(old_claims) - set(current))
        for key in removed_keys:
            old = old_claims[key]
            invalidated.append({
                "claim_key": key,
                "reason": "claim-or-entity-removed",
                "changed_dependencies": list((old.get("dependency_fingerprints") or {}).keys()),
                "previous_result": old.get("result"),
                "current_result": "UNRESOLVED",
                "affected_pages": list(old.get("affected_pages") or []),
            })

        history = list(previous.get("history") or [])
        if old_claims:
            history.append({"captured_at": _now(), "claims": old_claims})
        history = history[-HISTORY_LIMIT:]

        store = {
            "schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "claims": current,
            "history": history,
        }
        affected_pages = sorted({page for row in invalidated for page in row.get("affected_pages", [])})
        report = {
            "schema": "dead-signal-claim-invalidation-report",
            "schema_version": 1,
            "generated_at": _now(),
            "claim_counts": {
                "current": len(current),
                "unchanged": len(unchanged),
                "recomputed": len(set(recomputed)),
                "invalidated": len(invalidated),
                "removed": len(removed_keys),
            },
            "invalidated_claims": sorted(invalidated, key=lambda row: row["claim_key"]),
            "review_queue": sorted({row["claim_key"] for row in invalidated}),
            "affected_website_pages": affected_pages,
            "policy": "Historical PROVEN results are retained only in history. Changed or removed dependencies require current recomputation and review; stale proof never remains current.",
        }
        if persist:
            _atomic(self.path, store)
            _atomic(self.report_path, report)
        return report
