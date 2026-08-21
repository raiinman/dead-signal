"""Phase 11 dependency invalidation for generalized Evidence Graph claims.

Claims are persisted with exact dependency fingerprints. A changed/removed source
invalidates only claims that named that dependency. Historical proof is retained
for audit, but never treated as current proof after invalidation.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

SCHEMA = "dead-signal-claim-dependency-state"
SCHEMA_VERSION = 1
HISTORY_LIMIT = 20


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _claim_key(entity_type: str, canonical_id: str, claim_type: str) -> str:
    return f"{entity_type}:{canonical_id}:{claim_type}"


def _dependencies(claim: dict[str, Any]) -> list[str]:
    return sorted({str(value).strip() for value in claim.get("dependencies", []) if str(value or "").strip()})


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _roots(output: Path) -> tuple[Path | None, Path | None, Path | None]:
    state: dict[str, Any] = {}
    try:
        state = json.loads((output / "last-run.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass

    def resolve(key: str, fallback: str) -> Path | None:
        raw = state.get(key)
        path = Path(raw) if raw else output / fallback
        if not path.is_absolute():
            path = output / path
        path = path.resolve()
        try:
            path.relative_to(output)
        except ValueError:
            return None
        return path

    return resolve("current", "current"), resolve("base", "base"), resolve("published", "published")


def _dependency_files(output: Path, dependency: str) -> list[Path]:
    """Resolve a dependency using effective Current-over-Base patch semantics."""
    current, base, published = _roots(output)
    dep = dependency.replace("\\", "/").lstrip("/")

    def matches(root: Path | None, rel: str) -> list[Path]:
        if root is None:
            return []
        pattern = root / rel
        if "*" in pattern.name:
            return sorted(path for path in pattern.parent.glob(pattern.name) if path.is_file())
        return [pattern] if pattern.is_file() else []

    if dep.startswith("published/"):
        return matches(published, dep[len("published/"):])

    # Current is a patch layer: absence here is not deletion; fall back to Base.
    for root in (current, base):
        found = matches(root, dep)
        if found:
            return found

    # Normalized evidence/report dependencies may live under published/output.
    for root in (published, output):
        found = matches(root, dep)
        if found:
            return found
    return []


def current_dependency_fingerprints(output: Path | str, dependencies: Iterable[str]) -> dict[str, str]:
    root = Path(output).expanduser().resolve()
    result: dict[str, str] = {}
    for dependency in sorted({str(value).strip() for value in dependencies if str(value or "").strip()}):
        files = _dependency_files(root, dependency)
        result[dependency] = "MISSING" if not files else _hash([(path.as_posix(), _file_sha(path)) for path in files])
    return result


def _claim_fingerprint(claim: dict[str, Any], dependency_fingerprints: dict[str, str]) -> str:
    return _hash({
        "claim_type": claim.get("claim_type"),
        "result": claim.get("result"),
        "requirements": claim.get("requirements", []),
        "evidence": claim.get("evidence", []),
        "missing": claim.get("missing", []),
        "conflicts": claim.get("conflicts", []),
        "dependencies": {name: dependency_fingerprints.get(name, "MISSING") for name in _dependencies(claim)},
    })


def default_page_resolver(entity_type: str, canonical_id: str, _claim_type: str) -> tuple[str, ...]:
    """Return stable affected-page keys, not assumed production URLs."""
    return (f"{entity_type}:{canonical_id}",)


class DependencyInvalidationStore:
    """Persistent dependency state, dirty-claim planner, and review diagnostics."""

    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        self.path = self.output / "catalogs" / "dead-signal-claim-dependencies.json"
        self.report_path = self.output / "reports" / "claim-invalidation.json"

    def load(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"schema": SCHEMA, "schema_version": SCHEMA_VERSION, "claims": {}, "history": []}
        if not isinstance(payload, dict) or payload.get("schema") != SCHEMA or payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Invalid claim dependency store")
        return payload

    def invalidation_plan(self) -> dict[str, Any]:
        """Identify dirty persisted claims before recomputation."""
        claims = self.load().get("claims") or {}
        dependency_names = {dep for row in claims.values() if isinstance(row, dict) for dep in (row.get("dependencies") or [])}
        current = current_dependency_fingerprints(self.output, dependency_names)
        dirty: list[dict[str, Any]] = []
        unchanged: list[str] = []
        for key, row in sorted(claims.items()):
            old = row.get("dependency_fingerprints") or {}
            changed = sorted(dep for dep in set(old) | set(row.get("dependencies") or []) if old.get(dep) != current.get(dep, "MISSING"))
            if changed:
                dirty.append({
                    "claim_key": key,
                    "entity_type": row.get("entity_type"),
                    "canonical_id": row.get("canonical_id"),
                    "claim_type": row.get("claim_type"),
                    "previous_result": row.get("result"),
                    "changed_dependencies": changed,
                    "affected_pages": list(row.get("affected_pages") or []),
                })
            else:
                unchanged.append(key)
        return {
            "schema": "dead-signal-claim-invalidation-plan",
            "schema_version": 1,
            "generated_at": _now(),
            "dirty_claims": dirty,
            "dirty_claim_keys": [row["claim_key"] for row in dirty],
            "dirty_entities": sorted({f"{row['entity_type']}:{row['canonical_id']}" for row in dirty}),
            "unchanged_claim_keys": unchanged,
            "affected_website_pages": sorted({page for row in dirty for page in row["affected_pages"]}),
        }

    def evaluate(
        self,
        graphs: Iterable[dict[str, Any]],
        *,
        page_resolver: Callable[[str, str, str], Iterable[str]] = default_page_resolver,
        full_snapshot: bool = True,
        removed_claim_keys: Iterable[str] = (),
        persist: bool = True,
    ) -> dict[str, Any]:
        """Persist recomputed claims and invalidate stale/removed proof.

        ``full_snapshot=False`` is claim-scoped: only claims supplied in ``graphs``
        are replaced. Unchanged siblings remain untouched. If a dirty claim no
        longer resolves, its exact key must be supplied in ``removed_claim_keys``.
        """
        previous = self.load()
        old_claims = previous.get("claims") or {}
        if not isinstance(old_claims, dict):
            raise ValueError("Claim dependency store claims must be an object")
        graph_list = [graph for graph in graphs if isinstance(graph, dict)]
        dependency_names = {dep for graph in graph_list for claim in graph.get("claims", []) if isinstance(claim, dict) for dep in _dependencies(claim)}
        fingerprints = current_dependency_fingerprints(self.output, dependency_names)
        current = {} if full_snapshot else dict(old_claims)
        invalidated: list[dict[str, Any]] = []
        recomputed: set[str] = set()

        for graph in graph_list:
            entity = graph.get("entity") or {}
            entity_type = str(entity.get("entity_type") or "")
            canonical_id = str(entity.get("canonical_id") or "")
            for claim in graph.get("claims", []):
                if not isinstance(claim, dict):
                    continue
                claim_type = str(claim.get("claim_type") or "")
                key = _claim_key(entity_type, canonical_id, claim_type)
                deps = _dependencies(claim)
                dep_fingerprints = {name: fingerprints.get(name, "MISSING") for name in deps}
                pages = sorted({str(value) for value in page_resolver(entity_type, canonical_id, claim_type) if str(value or "").strip()})
                row = {
                    "entity_type": entity_type,
                    "canonical_id": canonical_id,
                    "claim_type": claim_type,
                    "result": str(claim.get("result") or "UNRESOLVED"),
                    "dependencies": deps,
                    "dependency_fingerprints": dep_fingerprints,
                    "claim_fingerprint": _claim_fingerprint(claim, dep_fingerprints),
                    "affected_pages": pages,
                    "current": True,
                }
                current[key] = row
                recomputed.add(key)
                old = old_claims.get(key)
                if not isinstance(old, dict):
                    continue
                changed_dependencies = sorted(dep for dep in set(old.get("dependency_fingerprints", {})) | set(dep_fingerprints) if (old.get("dependency_fingerprints") or {}).get(dep) != dep_fingerprints.get(dep))
                if changed_dependencies or old.get("claim_fingerprint") != row["claim_fingerprint"]:
                    invalidated.append({
                        "claim_key": key,
                        "reason": "dependency-changed-or-removed" if changed_dependencies else "claim-evidence-changed",
                        "changed_dependencies": changed_dependencies,
                        "previous_result": old.get("result"),
                        "current_result": row["result"],
                        "affected_pages": pages,
                    })

        if full_snapshot:
            removed = set(old_claims) - set(current)
        else:
            removed = {str(key) for key in removed_claim_keys if str(key) in old_claims and str(key) not in recomputed}
        removed_keys = sorted(removed)
        for key in removed_keys:
            old = old_claims[key]
            current.pop(key, None)
            invalidated.append({
                "claim_key": key,
                "reason": "claim-or-owner-removed",
                "changed_dependencies": list((old.get("dependency_fingerprints") or {}).keys()),
                "previous_result": old.get("result"),
                "current_result": "UNRESOLVED",
                "affected_pages": list(old.get("affected_pages") or []),
            })

        history = list(previous.get("history") or [])
        if old_claims:
            history.append({"captured_at": _now(), "claims": old_claims})
        history = history[-HISTORY_LIMIT:]
        store = {"schema": SCHEMA, "schema_version": SCHEMA_VERSION, "generated_at": _now(), "claims": current, "history": history}
        affected_pages = sorted({page for row in invalidated for page in row.get("affected_pages", [])})
        report = {
            "schema": "dead-signal-claim-invalidation-report",
            "schema_version": 1,
            "generated_at": _now(),
            "claim_counts": {
                "current": len(current),
                "recomputed": len(recomputed),
                "invalidated": len(invalidated),
                "removed": len(removed_keys),
                "untouched": max(0, len(current) - len(recomputed)),
            },
            "invalidated_claims": sorted(invalidated, key=lambda row: row["claim_key"]),
            "review_queue": sorted({row["claim_key"] for row in invalidated}),
            "affected_website_pages": affected_pages,
            "policy": "Historical PROVEN results are audit history only. Changed or removed dependencies require current recomputation; removed claims cannot remain current PROVEN.",
        }
        if persist:
            _atomic(self.path, store)
            _atomic(self.report_path, report)
        return report
