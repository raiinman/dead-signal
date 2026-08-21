"""Phase 16 bounded runtime and dependency-aware cache for generalized traces.

Cache entries are accepted only while every exact claim dependency retains the
same effective Current-over-Base fingerprint. The cache never changes evidence
state and is safe to delete at any time.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event, RLock
from typing import Any, Callable

from dead_signal_dependency_invalidation import current_dependency_fingerprints
from dead_signal_evidence_contracts import validate_generalized_graph

SCHEMA = "dead-signal-adapter-result-cache"
SCHEMA_VERSION = 1
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_CACHE_ENTRIES = 512
ATOMIC_REPLACE_ATTEMPTS = 6
ATOMIC_REPLACE_DELAY_SECONDS = 0.025
ProgressCallback = Callable[[int, str], None]

# Phase 13 can have Overview, Evidence Graph, and Review Queue workers active in
# the same process. Serialize the cache read-modify-write transaction so one
# worker cannot overwrite another worker's just-added entry. This is deliberately
# process-local: the Miner owns one output snapshot per running application.
_CACHE_WRITE_LOCK = RLock()


def _stable(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _key(entity_type: object, identity: object, kwargs: dict[str, Any]) -> str:
    raw = _stable({"entity_type": str(entity_type), "identity": identity, "kwargs": kwargs})
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dependencies(graph: dict[str, Any]) -> list[str]:
    return sorted({
        str(dep).strip()
        for claim in graph.get("claims", []) if isinstance(claim, dict)
        for dep in claim.get("dependencies", [])
        if str(dep or "").strip()
    })


def _atomic(path: Path, payload: dict[str, Any]) -> None:
    """Atomically replace one JSON file without sharing a Windows temp name.

    A fixed ``.tmp`` filename is unsafe when multiple UI workers persist cache
    entries at once: one writer can move/delete the temporary file while another
    still expects it. Use a unique sibling temp file, close it before replacement
    (required by Windows), and tolerate short-lived antivirus/indexer locks.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)

        last_error: PermissionError | None = None
        for attempt in range(ATOMIC_REPLACE_ATTEMPTS):
            try:
                os.replace(temporary, path)
                temporary = None
                return
            except PermissionError as error:
                last_error = error
                if attempt + 1 >= ATOMIC_REPLACE_ATTEMPTS:
                    raise
                time.sleep(ATOMIC_REPLACE_DELAY_SECONDS * (attempt + 1))
        if last_error is not None:
            raise last_error
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


@dataclass(frozen=True)
class TraceResult:
    graph: dict[str, Any]
    cache_status: str
    elapsed_seconds: float


class AdapterResultCache:
    """Small persistent cache keyed by trace input plus exact dependency state."""

    def __init__(self, output: Path | str, *, max_entries: int = DEFAULT_MAX_CACHE_ENTRIES):
        self.output = Path(output).expanduser().resolve()
        self.path = self.output / "catalogs" / "dead-signal-adapter-cache.json"
        self.max_entries = max(1, int(max_entries))

    def load(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"schema": SCHEMA, "schema_version": SCHEMA_VERSION, "entries": {}}
        if not isinstance(payload, dict) or payload.get("schema") != SCHEMA or payload.get("schema_version") != SCHEMA_VERSION:
            return {"schema": SCHEMA, "schema_version": SCHEMA_VERSION, "entries": {}}
        if not isinstance(payload.get("entries"), dict):
            payload["entries"] = {}
        return payload

    def get(self, entity_type: object, identity: object, kwargs: dict[str, Any]) -> dict[str, Any] | None:
        payload = self.load()
        row = (payload.get("entries") or {}).get(_key(entity_type, identity, kwargs))
        if not isinstance(row, dict):
            return None
        graph = row.get("graph")
        if not isinstance(graph, dict) or validate_generalized_graph(graph):
            return None
        dependencies = [str(value) for value in row.get("dependencies") or []]
        expected = row.get("dependency_fingerprints") or {}
        if current_dependency_fingerprints(self.output, dependencies) != expected:
            return None
        return graph

    def put(self, entity_type: object, identity: object, kwargs: dict[str, Any], graph: dict[str, Any]) -> None:
        errors = validate_generalized_graph(graph)
        if errors:
            raise ValueError(f"Refusing to cache invalid generalized graph: {errors}")
        dependencies = _dependencies(graph)
        dependency_fingerprints = current_dependency_fingerprints(self.output, dependencies)
        key = _key(entity_type, identity, kwargs)
        row = {
            "entity_type": str(entity_type),
            "identity": identity,
            "kwargs": kwargs,
            "dependencies": dependencies,
            "dependency_fingerprints": dependency_fingerprints,
            "graph": graph,
            "last_used_epoch": time.time(),
        }

        # Lock the complete read-modify-write transaction. Locking only the final
        # replace would avoid the Windows exception but still allow lost updates.
        with _CACHE_WRITE_LOCK:
            payload = self.load()
            entries = payload.setdefault("entries", {})
            entries[key] = row
            if len(entries) > self.max_entries:
                ordered = sorted(entries.items(), key=lambda item: float((item[1] or {}).get("last_used_epoch", 0.0)))
                for old_key, _ in ordered[: len(entries) - self.max_entries]:
                    entries.pop(old_key, None)
            _atomic(self.path, payload)

    def clear(self) -> None:
        with _CACHE_WRITE_LOCK:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass


class TraceRuntime:
    """Bounded orchestration around one adapter call.

    Cancellation is cooperative at the facade boundary. A cancelled/superseded UI
    request discards the late worker result even if a legacy adapter cannot abort
    midway through one synchronous read.
    """

    def __init__(self, output: Path | str):
        self.cache = AdapterResultCache(output)

    def run(
        self,
        adapter_call: Callable[[], dict[str, Any]],
        *,
        entity_type: object,
        identity: object,
        kwargs: dict[str, Any],
        use_cache: bool = True,
        cancel_event: Event | None = None,
        progress: ProgressCallback | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> TraceResult:
        started = time.perf_counter()
        notify = progress or (lambda _percent, _message: None)
        cancelled = cancel_event or Event()
        if cancelled.is_set():
            raise InterruptedError("Evidence trace cancelled")
        notify(5, "Checking dependency-aware trace cache")
        if use_cache:
            cached = self.cache.get(entity_type, identity, kwargs)
            if cached is not None:
                notify(100, "Warm trace cache hit")
                return TraceResult(cached, "HIT", time.perf_counter() - started)
        if cancelled.is_set():
            raise InterruptedError("Evidence trace cancelled")
        notify(20, "Resolving typed evidence")
        graph = adapter_call()
        elapsed = time.perf_counter() - started
        if elapsed > float(timeout_seconds):
            raise TimeoutError(f"Evidence trace exceeded {timeout_seconds:.1f}s bound ({elapsed:.3f}s)")
        if cancelled.is_set():
            raise InterruptedError("Evidence trace cancelled")
        errors = validate_generalized_graph(graph)
        if errors:
            raise ValueError(f"Adapter returned invalid generalized graph: {errors}")
        notify(85, "Validating dependency fingerprints")
        if use_cache:
            self.cache.put(entity_type, identity, kwargs, graph)
        notify(100, "Trace complete")
        return TraceResult(graph, "MISS", elapsed)
