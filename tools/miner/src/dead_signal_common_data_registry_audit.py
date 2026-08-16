"""Offline static audit of Once Human's Env.common_data registry architecture.

The full extracted PYC tree is scanned read-only for exact raw signatures.  Only
modules that actually contain ``common_data`` are unmarshaled for deep CodeType
inspection.  Game bytecode is never imported or executed.
"""
from __future__ import annotations

import hashlib
import json
import marshal
import re
import types
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 3
ActivityCallback = Callable[[str], None]
TABLE_RE = re.compile(rb"[A-Z][A-Z0-9_]{2,}_TABLE")
CHUNK_SIZE = 1024 * 1024
SCAN_TAIL = 128
MAX_PATH_SAMPLES = 12
MAX_DEEP_PYC_BYTES = 64 * 1024 * 1024
MAX_NAMES = 256
MAX_STRINGS = 128
MAX_STRING_LENGTH = 512
MAX_BYTECODE_PREFIX = 256


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


def _scan_file(path: Path) -> tuple[int, str, bool, set[str]]:
    """Stream one PYC and return size/hash/signatures without retaining payload."""
    digest = hashlib.sha256()
    total = 0
    has_common = False
    tables: set[str] = set()
    tail = b""
    with path.open("rb") as handle:
        while True:
            block = handle.read(CHUNK_SIZE)
            if not block:
                break
            total += len(block)
            digest.update(block)
            data = tail + block
            if b"common_data" in data:
                has_common = True
            for match in TABLE_RE.findall(data):
                tables.add(match.decode("ascii", errors="ignore"))
            tail = data[-SCAN_TAIL:]
    return total, digest.hexdigest(), has_common, tables


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
        candidates: Any
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


def _code_row(index: int, qualname: str, code: types.CodeType) -> dict[str, Any] | None:
    names = list(map(str, code.co_names))
    strings = _strings(code)
    tables = sorted({value for value in names + strings if value.endswith("_TABLE") and value.upper() == value})
    common = "common_data" in names or "common_data" in strings
    env = "Env" in names or "Env" in strings
    if not (common or env or tables):
        return None
    bytecode = code.co_code
    return {
        "index": index,
        "qualname": qualname,
        "co_name": code.co_name,
        "co_filename": code.co_filename,
        "co_firstlineno": code.co_firstlineno,
        "co_names": names[:MAX_NAMES],
        "co_names_total": len(names),
        "string_constants": strings,
        "table_symbols": tables,
        "references_common_data": common,
        "references_env": env,
        "common_data_and_table_cooccur": bool(common and tables),
        "co_code_length": len(bytecode),
        "co_code_sha256": hashlib.sha256(bytecode).hexdigest(),
        "co_code_prefix_hex": bytecode[:MAX_BYTECODE_PREFIX].hex(),
    }


def _load_code(path: Path) -> tuple[types.CodeType | None, str | None]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"
    try:
        value = marshal.loads(raw[16:]) if len(raw) >= 17 else None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    finally:
        del raw
    if not isinstance(value, types.CodeType):
        return None, "marshal payload was not a CodeType"
    return value, None


def run_common_data_registry_audit(
    base: Path,
    current: Path,
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    progress_path = reports_dir / "common-data-registry-progress.json"

    scan_counts = {"pyc_files_scanned": 0, "raw_common_data_module_hits": 0, "raw_table_symbol_module_hits": 0}
    table_counts: Counter[str] = Counter()
    table_samples: dict[str, list[dict[str, str]]] = defaultdict(list)
    deep_candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    for layer, root in _roots(base, current):
        activity(f"Common Data Registry Audit: whole-tree census of extracted {layer} PYC files")
        for path in root.rglob("*.pyc"):
            resolved = path.resolve()
            key = str(resolved).casefold()
            if key in seen:
                continue
            seen.add(key)
            scan_counts["pyc_files_scanned"] += 1
            try:
                size, sha256, has_common, tables = _scan_file(resolved)
            except OSError:
                continue
            rel = resolved.relative_to(root).as_posix()
            if tables:
                scan_counts["raw_table_symbol_module_hits"] += 1
                for symbol in tables:
                    table_counts[symbol] += 1
                    if len(table_samples[symbol]) < MAX_PATH_SAMPLES:
                        table_samples[symbol].append({"layer": layer, "relative_path": rel})
            if has_common:
                scan_counts["raw_common_data_module_hits"] += 1
                deep_candidates.append({
                    "layer": layer,
                    "path": str(resolved),
                    "relative_path": rel,
                    "file_size": size,
                    "file_sha256": sha256,
                    "raw_table_symbols": sorted(tables),
                })

    deep_candidates.sort(key=lambda row: (0 if row["layer"] == "current" else 1, row["relative_path"].casefold()))
    activity(
        f"Common Data Registry Audit: census found {len(table_counts)} table symbols and "
        f"{len(deep_candidates)} common_data module(s) for deep inspection"
    )

    modules: list[dict[str, Any]] = []
    common_data_accesses: list[dict[str, Any]] = []
    for number, candidate in enumerate(deep_candidates, start=1):
        _write_json(progress_path, {
            "schema": "dead-signal-common-data-registry-progress",
            "status": "inspecting",
            "candidate_number": number,
            "candidate_total": len(deep_candidates),
            "layer": candidate["layer"],
            "relative_path": candidate["relative_path"],
            "file_size": candidate["file_size"],
        })
        activity(
            f"Common Data Registry Audit: inspecting {number}/{len(deep_candidates)} "
            f"{candidate['relative_path']}"
        )
        module = {key: value for key, value in candidate.items() if key != "path"}
        module["code_objects"] = []
        if int(candidate["file_size"]) > MAX_DEEP_PYC_BYTES:
            module.update({"marshal_compatible": False, "error": "deep-inspection-size-guard"})
            modules.append(module)
            continue
        code, error = _load_code(Path(str(candidate["path"])))
        module["marshal_compatible"] = code is not None
        module["error"] = error
        if code is not None:
            all_count = 0
            relevant: list[dict[str, Any]] = []
            for index, (qualname, obj) in enumerate(_walk(code)):
                all_count += 1
                row = _code_row(index, qualname, obj)
                if row is not None:
                    relevant.append(row)
                    if row["references_common_data"]:
                        common_data_accesses.append({
                            "layer": candidate["layer"],
                            "relative_path": candidate["relative_path"],
                            "code_object": index,
                            "qualname": qualname,
                            "co_name": row["co_name"],
                            "table_symbols": row["table_symbols"],
                            "references_env": row["references_env"],
                            "co_names": row["co_names"],
                            "string_constants": row["string_constants"],
                        })
            module["code_objects"] = relevant
            module["record_counts"] = {
                "all_code_objects": all_count,
                "registry_relevant_code_objects": len(relevant),
                "common_data_code_objects": sum(bool(row["references_common_data"]) for row in relevant),
                "common_data_and_table_code_objects": sum(bool(row["common_data_and_table_cooccur"]) for row in relevant),
            }
        modules.append(module)
        del code

    table_inventory = [
        {
            "symbol": symbol,
            "raw_module_count": table_counts[symbol],
            "raw_module_samples": table_samples[symbol],
            "deep_common_data_references": [
                {
                    "layer": access["layer"],
                    "relative_path": access["relative_path"],
                    "qualname": access["qualname"],
                }
                for access in common_data_accesses if symbol in access["table_symbols"]
            ],
        }
        for symbol in sorted(table_counts)
    ]

    report = {
        "schema": "dead-signal-common-data-registry-static-audit",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Once Human Env.common_data table registry",
        "mode": "offline-whole-tree-census-plus-common-data-deep-inspection",
        "record_counts": {
            **scan_counts,
            "unique_table_symbols": len(table_inventory),
            "deep_common_data_candidates": len(deep_candidates),
            "deep_modules": len(modules),
            "marshal_compatible_deep_modules": sum(bool(row.get("marshal_compatible")) for row in modules),
            "common_data_accesses": len(common_data_accesses),
        },
        "table_inventory": table_inventory,
        "common_data_accesses": common_data_accesses,
        "deep_modules": modules,
        "policy": {
            "whole_tree": "Every extracted PYC is streamed for exact raw *_TABLE and common_data signatures; payloads are not retained.",
            "deep_scope": "Only modules with the exact common_data signature are unmarshaled, because they are the modules relevant to the registry/accessor question.",
            "size_guard": f"Individual deep candidates over {MAX_DEEP_PYC_BYTES} bytes are recorded but not unmarshaled in the broad pass.",
            "execution": "No game module or game bytecode is imported or executed; marshal is used only for CodeType metadata inspection.",
            "live_game": "No process handle, debugger, hook, injection, memory access, network interception, client modification, or anti-cheat interaction.",
        },
    }
    _write_json(reports_dir / "common-data-registry-static-audit.json", report)
    _write_json(progress_path, {
        "schema": "dead-signal-common-data-registry-progress",
        "status": "complete",
        "deep_modules": len(modules),
        "common_data_accesses": len(common_data_accesses),
    })
    return report
