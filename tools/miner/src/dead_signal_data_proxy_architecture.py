"""Offline static audit of Once Human's common/client/server data proxy architecture.

The complete extracted PYC tree is scanned as a bounded raw-byte census. Only the
central Env.pyc and DataMgr.pyc modules are unmarshaled and walked deeply. This
keeps the architecture audit safe on real snapshots while still exposing the
three data proxies and their central loader/registry machinery.

No game module is imported or executed and the live game process is never touched.
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

SCHEMA_VERSION = 2
ActivityCallback = Callable[[str], None]
PROXIES = ("common_data", "client_data", "server_data")
TARGET_BASENAMES = {"Env.pyc", "DataMgr.pyc"}
TABLE_TOKEN_RE = re.compile(rb"(?<![A-Z0-9_])[A-Z][A-Z0-9_]{2,63}_TABLE(?![A-Z0-9_])")
DATA_TOKEN_RE = re.compile(rb"(?<![a-z0-9_])[a-z][a-z0-9_]{2,63}_data(?![a-z0-9_])")
MAX_DEEP_FILE_BYTES = 64 * 1024 * 1024
MAX_NAMES = 384
MAX_STRINGS = 256
MAX_STRING_LENGTH = 512
MAX_CODE_PREFIX = 256
MAX_RAW_SYMBOLS_PER_MODULE = 256
STREAM_BLOCK_BYTES = 1024 * 1024
STREAM_OVERLAP_BYTES = 96


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


def _load_code(path: Path) -> tuple[types.CodeType | None, str | None, int, str | None]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}", 0, None
    if size > MAX_DEEP_FILE_BYTES:
        return None, f"skipped: file exceeds {MAX_DEEP_FILE_BYTES} byte deep-audit guard", size, None
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}", size, None
    digest = hashlib.sha256(raw).hexdigest()
    if len(raw) < 17:
        return None, "PYC file is too small", size, digest
    try:
        value = marshal.loads(raw[16:])
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}", size, digest
    if not isinstance(value, types.CodeType):
        return None, "marshal payload was not a CodeType", size, digest
    return value, None, size, digest


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


def _proxy_hits(names: list[str], strings: list[str]) -> list[str]:
    values = set(names) | set(strings)
    return [proxy for proxy in PROXIES if proxy in values]


def _symbols(names: list[str], strings: list[str]) -> tuple[list[str], list[str]]:
    values = set(names) | set(strings)
    tables = sorted(
        value for value in values
        if 6 <= len(value) <= 70 and value.endswith("_TABLE") and value.replace("_", "").isalnum() and value.upper() == value
    )
    data_names = sorted(
        value for value in values
        if value not in PROXIES and 6 <= len(value) <= 70 and value.endswith("_data") and value.replace("_", "").isalnum() and value.lower() == value
    )
    return tables, data_names


def _code_row(index: int, qualname: str, code: types.CodeType) -> dict[str, Any]:
    names = list(map(str, code.co_names))
    strings = _strings(code)
    proxies = _proxy_hits(names, strings)
    tables, data_names = _symbols(names, strings)
    bytecode = code.co_code
    return {
        "index": index,
        "qualname": qualname,
        "co_name": code.co_name,
        "co_filename": code.co_filename,
        "co_firstlineno": code.co_firstlineno,
        "co_argcount": code.co_argcount,
        "co_posonlyargcount": getattr(code, "co_posonlyargcount", 0),
        "co_kwonlyargcount": code.co_kwonlyargcount,
        "co_flags": code.co_flags,
        "co_varnames": list(map(str, code.co_varnames))[:MAX_NAMES],
        "co_cellvars": list(map(str, code.co_cellvars))[:MAX_NAMES],
        "co_freevars": list(map(str, code.co_freevars))[:MAX_NAMES],
        "nested_code_names": [value.co_name for value in code.co_consts if isinstance(value, types.CodeType)],
        "proxy_references": proxies,
        "table_symbols": tables,
        "data_symbols": data_names,
        "co_names": names[:MAX_NAMES],
        "string_constants": strings,
        "co_code_length": len(bytecode),
        "co_code_sha256": hashlib.sha256(bytecode).hexdigest(),
        "co_code_prefix_hex": bytecode[:MAX_CODE_PREFIX].hex(),
    }


def _stream_census(path: Path) -> tuple[list[str], list[str], list[str], int]:
    proxy_hits = {proxy: False for proxy in PROXIES}
    tables: set[str] = set()
    data_names: set[str] = set()
    total = 0
    overlap = b""
    try:
        with path.open("rb") as handle:
            while True:
                block = handle.read(STREAM_BLOCK_BYTES)
                if not block:
                    break
                total += len(block)
                data = overlap + block
                for proxy in PROXIES:
                    if not proxy_hits[proxy] and proxy.encode("ascii") in data:
                        proxy_hits[proxy] = True
                if len(tables) < MAX_RAW_SYMBOLS_PER_MODULE:
                    tables.update(
                        match.decode("ascii", errors="ignore")
                        for match in TABLE_TOKEN_RE.findall(data)
                    )
                if len(data_names) < MAX_RAW_SYMBOLS_PER_MODULE:
                    data_names.update(
                        match.decode("ascii", errors="ignore")
                        for match in DATA_TOKEN_RE.findall(data)
                        if match.decode("ascii", errors="ignore") not in PROXIES
                    )
                overlap = data[-STREAM_OVERLAP_BYTES:]
    except OSError:
        return [], [], [], total
    return (
        [proxy for proxy in PROXIES if proxy_hits[proxy]],
        sorted(tables)[:MAX_RAW_SYMBOLS_PER_MODULE],
        sorted(data_names)[:MAX_RAW_SYMBOLS_PER_MODULE],
        total,
    )


def run_data_proxy_architecture_audit(
    base: Path,
    current: Path,
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    progress_path = reports_dir / "data-proxy-architecture-progress.json"
    _write_json(progress_path, {"stage": "starting", "schema_version": SCHEMA_VERSION})

    census_modules: list[dict[str, Any]] = []
    target_modules: list[dict[str, Any]] = []
    raw_proxy_module_counts = Counter()
    scanned = 0
    seen: set[str] = set()

    for layer, root in _roots(base, current):
        activity(f"Data Proxy Architecture: raw census of extracted {layer} PYC tree")
        _write_json(progress_path, {"stage": "raw-census", "layer": layer, "pyc_files_scanned": scanned})
        for path in root.rglob("*.pyc"):
            scanned += 1
            resolved = path.resolve()
            key = str(resolved).casefold()
            if key in seen:
                continue
            seen.add(key)
            proxies, tables, data_names, byte_count = _stream_census(resolved)
            is_target = resolved.name in TARGET_BASENAMES
            if not proxies and not is_target:
                continue
            rel = resolved.relative_to(root).as_posix()
            row = {
                "layer": layer,
                "source_root": str(root),
                "path": str(resolved),
                "relative_path": rel,
                "file_size": byte_count,
                "raw_proxy_hits": proxies,
                "raw_table_symbols": tables,
                "raw_data_symbols": data_names,
            }
            if proxies:
                census_modules.append(row)
                raw_proxy_module_counts.update(proxies)
            if is_target:
                target_modules.append(row)

    census_modules.sort(key=lambda row: (0 if row["layer"] == "current" else 1, row["relative_path"].casefold()))
    target_modules.sort(key=lambda row: (0 if row["layer"] == "current" else 1, row["relative_path"].casefold()))
    activity(f"Data Proxy Architecture: census found {len(census_modules)} proxy-hit module(s); deeply auditing {len(target_modules)} Env/DataMgr target(s)")
    _write_json(progress_path, {
        "stage": "deep-central-modules",
        "pyc_files_scanned": scanned,
        "proxy_hit_modules": len(census_modules),
        "target_modules": len(target_modules),
    })

    central_modules: list[dict[str, Any]] = []
    exact_edges: dict[str, dict[str, Any]] = {}
    proxy_code_counts = Counter()

    for number, candidate in enumerate(target_modules, start=1):
        _write_json(progress_path, {
            "stage": "deep-central-module",
            "index": number,
            "total": len(target_modules),
            "layer": candidate["layer"],
            "relative_path": candidate["relative_path"],
        })
        activity(f"Data Proxy Architecture: central module {number}/{len(target_modules)} {candidate['relative_path']}")
        path = Path(candidate["path"])
        code, error, size, digest = _load_code(path)
        rows: list[dict[str, Any]] = []
        if code is not None:
            for index, (qualname, obj) in enumerate(_walk(code)):
                row = _code_row(index, qualname, obj)
                rows.append(row)
                for proxy in row["proxy_references"]:
                    proxy_code_counts[proxy] += 1
                symbols = [("table", value) for value in row["table_symbols"]] + [("data", value) for value in row["data_symbols"]]
                for kind, symbol in symbols:
                    if not row["proxy_references"]:
                        continue
                    edge = exact_edges.setdefault(symbol, {
                        "symbol": symbol,
                        "symbol_kind": kind,
                        "proxy_counts": {proxy: 0 for proxy in PROXIES},
                        "references": [],
                    })
                    for proxy in row["proxy_references"]:
                        edge["proxy_counts"][proxy] += 1
                        edge["references"].append({
                            "proxy": proxy,
                            "layer": candidate["layer"],
                            "relative_path": candidate["relative_path"],
                            "code_object": index,
                            "qualname": qualname,
                            "co_name": obj.co_name,
                        })
        central_modules.append({
            "layer": candidate["layer"],
            "relative_path": candidate["relative_path"],
            "file_size": size,
            "file_sha256": digest,
            "raw_proxy_hits": candidate["raw_proxy_hits"],
            "marshal_compatible": code is not None,
            "error": error,
            "all_code_objects": len(rows),
            "proxy_code_objects": {proxy: sum(proxy in row["proxy_references"] for row in rows) for proxy in PROXIES},
            "code_objects": rows,
        })

    raw_symbol_proxy: dict[tuple[str, str], Counter[str]] = {}
    raw_symbol_modules: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for module in census_modules:
        for kind, symbols in (("table", module["raw_table_symbols"]), ("data", module["raw_data_symbols"])):
            for symbol in symbols:
                key = (kind, symbol)
                counts = raw_symbol_proxy.setdefault(key, Counter())
                counts.update(module["raw_proxy_hits"])
                raw_symbol_modules.setdefault(key, []).append({
                    "layer": module["layer"],
                    "relative_path": module["relative_path"],
                    "proxy_hits": module["raw_proxy_hits"],
                })

    raw_ownership = []
    for (kind, symbol), counts in sorted(raw_symbol_proxy.items(), key=lambda item: (item[0][0], item[0][1])):
        nonzero = [proxy for proxy in PROXIES if counts[proxy]]
        raw_ownership.append({
            "symbol": symbol,
            "symbol_kind": kind,
            "proxy_module_counts": {proxy: counts[proxy] for proxy in PROXIES},
            "proxy_classification": f"raw-module-{nonzero[0]}-cooccurrence" if len(nonzero) == 1 else "raw-module-multi-proxy-cooccurrence",
            "module_samples": raw_symbol_modules[(kind, symbol)][:20],
        })

    exact_ownership = []
    for symbol, row in sorted(exact_edges.items()):
        nonzero = [proxy for proxy in PROXIES if row["proxy_counts"][proxy]]
        row["proxy_classification"] = f"exact-code-object-{nonzero[0]}-cooccurrence" if len(nonzero) == 1 else "exact-code-object-multi-proxy-cooccurrence"
        exact_ownership.append(row)

    report = {
        "schema": "dead-signal-data-proxy-architecture-static-audit",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Once Human Env/DataMgr common_data client_data server_data architecture",
        "mode": "offline-static-raw-census-plus-central-pyc-audit",
        "record_counts": {
            "pyc_files_scanned": scanned,
            "proxy_hit_modules": len(census_modules),
            "target_env_datamgr_modules": len(central_modules),
            "raw_proxy_module_counts": dict(raw_proxy_module_counts),
            "central_proxy_code_object_counts": dict(proxy_code_counts),
            "raw_symbol_classifications": len(raw_ownership),
            "exact_central_symbol_classifications": len(exact_ownership),
        },
        "raw_module_symbol_proxy_cooccurrence": raw_ownership,
        "exact_central_symbol_proxy_cooccurrence": exact_ownership,
        "module_proxy_census": [
            {key: value for key, value in row.items() if key not in {"path", "source_root"}}
            for row in census_modules
        ],
        "central_modules_full_static_audit": central_modules,
        "proxy_definitions": {
            "common_data": "Exact/raw static references to common_data proxy symbols in shipped client files.",
            "client_data": "Exact/raw static references to client_data proxy symbols in shipped client files.",
            "server_data": "Static server_data symbols shipped in the client; this does not imply access to live remote server state.",
        },
        "policy": {
            "scope": "Every extracted PYC is scanned as bounded raw bytes. Only Env.pyc and DataMgr.pyc are unmarshaled and recursively walked.",
            "raw_ownership_semantics": "Raw module co-occurrence is a discovery lead, not proof that a symbol and proxy are used in the same function.",
            "exact_ownership_semantics": "Exact central ownership edges require proxy and symbol co-occurrence in the same Env/DataMgr code object.",
            "execution": "No game module is imported or executed. marshal is used only for Env.pyc/DataMgr.pyc CodeType metadata.",
            "live_game": "No process handle, debugger, hook, injection, memory access, network interception, client modification, or anti-cheat interaction.",
        },
    }
    _write_json(reports_dir / "data-proxy-architecture-static-audit.json", report)
    _write_json(progress_path, {
        "stage": "complete",
        "pyc_files_scanned": scanned,
        "proxy_hit_modules": len(census_modules),
        "target_modules": len(central_modules),
    })
    return report
