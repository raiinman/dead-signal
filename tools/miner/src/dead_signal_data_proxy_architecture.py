"""Offline static audit of Once Human's common/client/server data proxy architecture.

This module inventories the central Env.pyc and DataMgr.pyc modules completely, then
walks proxy-hit modules one at a time to recover exact code-object relationships
between common_data, client_data, server_data and table/data symbols. It never
imports or executes game bytecode and never touches the live game process.
"""
from __future__ import annotations

import hashlib
import json
import marshal
import re
import types
from collections import Counter
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 1
ActivityCallback = Callable[[str], None]
PROXIES = ("common_data", "client_data", "server_data")
TABLE_RE = re.compile(r"^[A-Z][A-Z0-9_]*_TABLE$")
DATA_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*_data$")
TARGET_BASENAMES = {"Env.pyc", "DataMgr.pyc"}
MAX_DEEP_FILE_BYTES = 64 * 1024 * 1024
MAX_NAMES = 384
MAX_STRINGS = 256
MAX_STRING_LENGTH = 512
MAX_CODE_PREFIX = 256


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _source_root(snapshot: Path) -> Path | None:
    payload = _read_json(snapshot / "snapshot.json", {}) or {}
    raw = payload.get("source_root") if isinstance(payload, dict) else None
    if not raw:
        return None
    root = Path(str(raw)).expanduser()
    root = (snapshot / root).resolve() if not root.is_absolute() else root.resolve()
    return root if root.is_dir() else None


def _roots(base: Path, current: Path) -> list[tuple[str, Path]]:
    result: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for layer, snapshot in (("current", current), ("base", base)):
        root = _source_root(snapshot)
        if root is None:
            continue
        key = str(root).casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append((layer, root))
    return result


def _load_code(path: Path) -> tuple[types.CodeType | None, str | None, int]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}", 0
    if size > MAX_DEEP_FILE_BYTES:
        return None, f"skipped: file exceeds {MAX_DEEP_FILE_BYTES} byte deep-audit guard", size
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}", size
    if len(raw) < 17:
        return None, "PYC file is too small", size
    try:
        value = marshal.loads(raw[16:])
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}", size
    if not isinstance(value, types.CodeType):
        return None, "marshal payload was not a CodeType", size
    return value, None, size


def _walk(code: types.CodeType, qualname: str = "<module>"):
    yield qualname, code
    occurrence: Counter[str] = Counter()
    for value in code.co_consts:
        if not isinstance(value, types.CodeType):
            continue
        occurrence[value.co_name] += 1
        suffix = f"#{occurrence[value.co_name]}" if occurrence[value.co_name] > 1 else ""
        child = value.co_name + suffix
        child_qualname = child if qualname == "<module>" else f"{qualname}.{child}"
        yield from _walk(value, child_qualname)


def _strings(code: types.CodeType) -> list[str]:
    result: list[str] = []
    for value in code.co_consts:
        if isinstance(value, str):
            candidates = (value,)
        elif isinstance(value, (tuple, frozenset)):
            candidates = value
        else:
            continue
        for item in candidates:
            if isinstance(item, str):
                result.append(item[:MAX_STRING_LENGTH])
                if len(result) >= MAX_STRINGS:
                    return result
    return result


def _symbols(names: list[str], strings: list[str]) -> tuple[list[str], list[str]]:
    values = set(names) | set(strings)
    tables = sorted(value for value in values if TABLE_RE.fullmatch(value))
    data_names = sorted(
        value for value in values
        if value not in PROXIES and DATA_NAME_RE.fullmatch(value)
    )
    return tables, data_names


def _proxy_hits(names: list[str], strings: list[str]) -> list[str]:
    values = set(names) | set(strings)
    return [proxy for proxy in PROXIES if proxy in values]


def _row(index: int, qualname: str, code: types.CodeType, *, full: bool) -> dict[str, Any]:
    names = list(map(str, code.co_names))
    strings = _strings(code)
    proxies = _proxy_hits(names, strings)
    tables, data_names = _symbols(names, strings)
    bytecode = code.co_code
    result = {
        "index": index,
        "qualname": qualname,
        "co_name": code.co_name,
        "co_filename": code.co_filename,
        "co_firstlineno": code.co_firstlineno,
        "proxy_references": proxies,
        "table_symbols": tables,
        "data_symbols": data_names,
        "co_names": names[:MAX_NAMES],
        "string_constants": strings,
        "co_code_length": len(bytecode),
        "co_code_sha256": hashlib.sha256(bytecode).hexdigest(),
        "co_code_prefix_hex": bytecode[:MAX_CODE_PREFIX].hex(),
    }
    if full:
        result.update({
            "co_argcount": code.co_argcount,
            "co_posonlyargcount": getattr(code, "co_posonlyargcount", 0),
            "co_kwonlyargcount": code.co_kwonlyargcount,
            "co_flags": code.co_flags,
            "co_varnames": list(map(str, code.co_varnames))[:MAX_NAMES],
            "co_cellvars": list(map(str, code.co_cellvars))[:MAX_NAMES],
            "co_freevars": list(map(str, code.co_freevars))[:MAX_NAMES],
            "nested_code_names": [value.co_name for value in code.co_consts if isinstance(value, types.CodeType)],
        })
    return result


def _stream_has_proxy(path: Path) -> tuple[list[str], int]:
    hits = {proxy: False for proxy in PROXIES}
    total = 0
    overlap = b""
    try:
        with path.open("rb") as handle:
            while True:
                block = handle.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                data = overlap + block
                for proxy in PROXIES:
                    if not hits[proxy] and proxy.encode("ascii") in data:
                        hits[proxy] = True
                overlap = data[-32:]
    except OSError:
        return [], total
    return [proxy for proxy in PROXIES if hits[proxy]], total


def run_data_proxy_architecture_audit(
    base: Path,
    current: Path,
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    proxy_modules: list[dict[str, Any]] = []
    target_modules: list[dict[str, Any]] = []
    seen: set[str] = set()
    scanned = 0
    raw_proxy_module_counts = Counter()

    for layer, root in _roots(base, current):
        activity(f"Data Proxy Architecture: scanning extracted {layer} PYC tree")
        for path in root.rglob("*.pyc"):
            scanned += 1
            resolved = path.resolve()
            key = str(resolved).casefold()
            if key in seen:
                continue
            seen.add(key)
            hits, byte_count = _stream_has_proxy(resolved)
            if not hits and resolved.name not in TARGET_BASENAMES:
                continue
            rel = resolved.relative_to(root).as_posix()
            row = {
                "layer": layer,
                "source_root": str(root),
                "path": str(resolved),
                "relative_path": rel,
                "file_size": byte_count,
                "raw_proxy_hits": hits,
            }
            if hits:
                proxy_modules.append(row)
                raw_proxy_module_counts.update(hits)
            if resolved.name in TARGET_BASENAMES:
                target_modules.append(row)

    proxy_modules.sort(key=lambda row: (0 if row["layer"] == "current" else 1, row["relative_path"].casefold()))
    target_keys = {str(row["path"]).casefold() for row in target_modules}
    activity(f"Data Proxy Architecture: {len(proxy_modules)} proxy-hit module(s), {len(target_modules)} Env/DataMgr target(s)")

    module_summaries: list[dict[str, Any]] = []
    ownership: dict[str, dict[str, Any]] = {}
    proxy_code_counts = Counter()
    full_targets: list[dict[str, Any]] = []

    for number, candidate in enumerate(proxy_modules, start=1):
        path = Path(candidate["path"])
        activity(f"Data Proxy Architecture: inspecting {number}/{len(proxy_modules)} {candidate['relative_path']}")
        code, error, size = _load_code(path)
        is_target = str(path).casefold() in target_keys
        summary = {
            "layer": candidate["layer"],
            "relative_path": candidate["relative_path"],
            "file_size": size,
            "raw_proxy_hits": candidate["raw_proxy_hits"],
            "marshal_compatible": code is not None,
            "error": error,
            "proxy_code_objects": {proxy: 0 for proxy in PROXIES},
            "ownership_edge_count": 0,
        }
        target_rows: list[dict[str, Any]] = []
        all_code_objects = 0
        if code is not None:
            for index, (qualname, obj) in enumerate(_walk(code)):
                all_code_objects += 1
                row = _row(index, qualname, obj, full=is_target)
                for proxy in row["proxy_references"]:
                    summary["proxy_code_objects"][proxy] += 1
                    proxy_code_counts[proxy] += 1
                symbols = [("table", value) for value in row["table_symbols"]]
                symbols += [("data", value) for value in row["data_symbols"]]
                if row["proxy_references"] and symbols:
                    for kind, symbol in symbols:
                        item = ownership.setdefault(symbol, {
                            "symbol": symbol,
                            "symbol_kind": kind,
                            "proxy_counts": {proxy: 0 for proxy in PROXIES},
                            "references": [],
                        })
                        for proxy in row["proxy_references"]:
                            item["proxy_counts"][proxy] += 1
                            item["references"].append({
                                "proxy": proxy,
                                "layer": candidate["layer"],
                                "relative_path": candidate["relative_path"],
                                "code_object": index,
                                "qualname": qualname,
                                "co_name": obj.co_name,
                            })
                            summary["ownership_edge_count"] += 1
                if is_target:
                    target_rows.append(row)
        summary["all_code_objects"] = all_code_objects
        module_summaries.append(summary)
        if is_target:
            full_targets.append({**summary, "code_objects": target_rows})

    already = {row["relative_path"] for row in full_targets}
    for candidate in target_modules:
        if candidate["relative_path"] in already:
            continue
        path = Path(candidate["path"])
        code, error, size = _load_code(path)
        rows = []
        if code is not None:
            rows = [_row(index, qualname, obj, full=True) for index, (qualname, obj) in enumerate(_walk(code))]
        full_targets.append({
            "layer": candidate["layer"],
            "relative_path": candidate["relative_path"],
            "file_size": size,
            "raw_proxy_hits": candidate["raw_proxy_hits"],
            "marshal_compatible": code is not None,
            "error": error,
            "all_code_objects": len(rows),
            "proxy_code_objects": {
                proxy: sum(proxy in row["proxy_references"] for row in rows) for proxy in PROXIES
            },
            "ownership_edge_count": 0,
            "code_objects": rows,
        })

    ownership_rows = []
    for symbol, row in sorted(ownership.items()):
        nonzero = [proxy for proxy in PROXIES if row["proxy_counts"][proxy]]
        if len(nonzero) == 1:
            classification = f"exact-{nonzero[0]}-cooccurrence"
        elif len(nonzero) > 1:
            classification = "multi-proxy-cooccurrence"
        else:
            classification = "unclassified"
        row["proxy_classification"] = classification
        row["references"] = sorted(
            row["references"], key=lambda item: (item["proxy"], item["relative_path"], item["qualname"])
        )
        ownership_rows.append(row)

    report = {
        "schema": "dead-signal-data-proxy-architecture-static-audit",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Once Human Env/DataMgr common_data client_data server_data architecture",
        "mode": "offline-static-pyc-data-proxy-audit",
        "record_counts": {
            "pyc_files_scanned": scanned,
            "proxy_hit_modules": len(proxy_modules),
            "target_env_datamgr_modules": len(full_targets),
            "raw_proxy_module_counts": dict(raw_proxy_module_counts),
            "proxy_code_object_counts": dict(proxy_code_counts),
            "classified_symbols": len(ownership_rows),
            "single_proxy_symbols": sum(row["proxy_classification"].startswith("exact-") for row in ownership_rows),
            "multi_proxy_symbols": sum(row["proxy_classification"] == "multi-proxy-cooccurrence" for row in ownership_rows),
        },
        "proxy_definitions": {
            "common_data": "Exact static references to Env/common_data-style proxy symbols in shipped client bytecode metadata.",
            "client_data": "Exact static references to client_data proxy symbols in shipped client bytecode metadata.",
            "server_data": "Exact static references to server_data proxy symbols present in the shipped client. Presence does not imply access to live remote server databases or runtime server state.",
        },
        "symbol_proxy_ownership": ownership_rows,
        "module_proxy_summary": module_summaries,
        "central_modules_full_static_audit": sorted(full_targets, key=lambda row: row["relative_path"].casefold()),
        "policy": {
            "scope": "The complete extracted PYC tree is scanned for common_data, client_data, and server_data signatures. Env.pyc and DataMgr.pyc are inventoried fully; proxy-hit modules are unmarshaled one at a time for compact exact ownership edges.",
            "ownership_semantics": "A proxy classification means the symbol co-occurs with that exact proxy in one or more code objects. It is evidence of static consumption/ownership relationship, not proof of exclusive storage semantics.",
            "server_data_semantics": "server_data evidence is limited to static data/code shipped in the client snapshot. It does not expose or claim live server-only state.",
            "execution": "No game module is imported or executed. marshal is used only for CodeType metadata inspection.",
            "live_game": "No process handle, debugger, hook, injection, memory access, network interception, client modification, or anti-cheat interaction.",
        },
    }
    _write_json(reports_dir / "data-proxy-architecture-static-audit.json", report)
    return report
