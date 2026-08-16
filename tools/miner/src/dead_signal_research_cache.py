"""Incremental cache helpers for Dead Signal Data Intelligence research reports.

The cache never changes evidence semantics. It only reuses a previously written
research report when the completed Miner snapshot inputs are unchanged and the
analyzer revision matches. Reports remain local/research-only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

CACHE_FIELD = "_dead_signal_cache"
CACHE_SCHEMA_VERSION = 1


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def fingerprint(paths: Iterable[Path], *, revision: str) -> str:
    digest = hashlib.sha256()
    digest.update(f"dead-signal-cache-v{CACHE_SCHEMA_VERSION}|{revision}\n".encode("utf-8"))
    for path in sorted({Path(p).expanduser().resolve() for p in paths}, key=lambda p: str(p).casefold()):
        digest.update(str(path).encode("utf-8", errors="replace"))
        digest.update(b"\0")
        try:
            stat = path.stat()
        except OSError:
            digest.update(b"missing\n")
            continue
        digest.update(f"{stat.st_size}|{stat.st_mtime_ns}\n".encode("ascii"))
    return digest.hexdigest()


def dependency_paths(output: Path, base: Path, current: Path, weapons_path: Path) -> list[Path]:
    candidates = [
        output / "last-run.json",
        output / "catalogs" / "structured-tables.sqlite",
        output / "published" / "indexes" / "reference-tracer.sqlite",
        weapons_path,
        base / "snapshot.json",
        current / "snapshot.json",
    ]
    return [path for path in candidates if path.exists()]


def load_cached_report(
    path: Path,
    *,
    signature: str,
    revision: str,
    dependencies: Iterable[Path],
    allow_legacy_adoption: bool = False,
) -> dict[str, Any] | None:
    payload = _read_json(path, None)
    if not isinstance(payload, dict):
        return None
    marker = payload.get(CACHE_FIELD)
    if isinstance(marker, dict):
        if marker.get("signature") == signature and marker.get("revision") == revision:
            return payload
        return None
    if not allow_legacy_adoption:
        return None
    try:
        report_mtime = path.stat().st_mtime_ns
        newest_input = max((Path(dep).stat().st_mtime_ns for dep in dependencies if Path(dep).exists()), default=0)
    except OSError:
        return None
    if report_mtime < newest_input:
        return None
    payload[CACHE_FIELD] = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "signature": signature,
        "revision": revision,
        "adopted_legacy_report": True,
    }
    return payload


def stamp_report(payload: dict[str, Any], *, signature: str, revision: str) -> dict[str, Any]:
    payload[CACHE_FIELD] = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "signature": signature,
        "revision": revision,
        "adopted_legacy_report": False,
    }
    return payload
