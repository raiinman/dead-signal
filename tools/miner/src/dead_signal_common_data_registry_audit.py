"""Offline static audit of Once Human's Env.common_data table registry architecture.

The audit scans the already-extracted PYC snapshot for exact registry signatures
(`common_data` and `*_TABLE`) and then walks every code object in matching modules.
It never imports or executes game bytecode and never touches the live game process.

The discovery pass is deliberately memory-bounded: it never retains PYC payloads.
Matching modules are reopened and inspected one at a time during the analysis pass.
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
TABLE_RE_TEXT = re.compile(r"^[A-Z][A-Z0-9_]*_TABLE$")
TABLE_RE_BYTES = re.compile(rb"[A-Z][A-Z0-9_]{2,}_TABLE")
MAX_RETAINED_NAMES = 256
MAX_RETAINED_STRINGS = 128
MAX_RETAINED_STRING_LENGTH = 512
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


def _load_code(raw: bytes) -> tuple[types.CodeType | None, str | None]:
    if len(raw) < 17:
        return None, "PYC file is too small"
    try:
        value = marshal.loads(raw[16:])
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(value, types.CodeType):
        return None, "marshal payload was not a CodeType"
    return value, None


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


def _string_constants(code: types.CodeType) -> list[str]:
    result: list[str] = []
    for value in code.co_consts:
        values: tuple[Any, ...] | frozenset[Any]
        if isinstance(value, str):
            candidates = (value,)
        elif isinstance(value, tuple):
            candidates = value
        elif isinstance(value, frozenset):
            candidates = value
        else:
            continue
        for item in candidates:
            if isinstance(item, str):
                result.append(item[:MAX_RETAINED_STRING_LENGTH])
                if len(result) >= MAX_RETAINED_STRINGS:
                    return result
    return result


def _table_symbols(names: list[str], strings: list[str]) -> list[str]:
    return sorted({value for value in names + strings if TABLE_RE_TEXT.fullmatch(value)})


def _code_row(index: int, qualname: str, code: types.CodeType) -> dict[str, Any]:
    all_names = list(map(str, code.co_names))
    strings = _string_constants(code)
    tables = _table_symbols(all_names, strings)
    common_data = "common_data" in all_names or "common_data" in strings
    env = "Env" in all_names or "Env" in strings
    bytecode = code.co_code
    return {
        "index": index,
        "qualname": qualname,
        "co_name": code.co_name,
        "co_filename": code.co_filename,
        "co_firstlineno": code.co_firstlineno,
        "co_names": all_names[:MAX_RETAINED_NAMES],
        "co_names_total": len(all_names),
        "co_varnames": list(map(str, code.co_varnames))[:MAX_RETAINED_NAMES],
        "string_constants": strings,
        "table_symbols": tables,
        "references_common_data": common_data,
        "references_env": env,
        "common_data_and_table_cooccur": bool(common_data and tables),
        "co_code_length": len(bytecode),
        "co_code_sha256": hashlib.sha256(bytecode).hexdigest(),
        "co_code_prefix_hex": bytecode[:MAX_BYTECODE_PREFIX].hex(),
        "co_code_prefix_bytes": min(len(bytecode), MAX_BYTECODE_PREFIX),
    }


def _scan_candidates(base: Path, current: Path, *, activity: ActivityCallback) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Discover matching PYC paths without retaining any file payloads."""
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    scanned = 0
    common_hits = 0
    table_hits = 0
    for layer, root in _roots(base, current):
        activity(f"Common Data Registry Audit: scanning extracted {layer} PYC tree")
        for path in root.rglob("*.pyc"):
            scanned += 1
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            has_common = b"common_data" in raw
            raw_tables = sorted({match.decode("ascii", errors="ignore") for match in TABLE_RE_BYTES.findall(raw)})
            if not has_common and not raw_tables:
                continue
            common_hits += int(has_common)
            table_hits += int(bool(raw_tables))
            resolved = path.resolve()
            key = str(resolved).casefold()
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                "layer": layer,
                "source_root": str(root),
                "path": str(resolved),
                "relative_path": resolved.relative_to(root).as_posix(),
                "file_size": len(raw),
                "file_sha256": hashlib.sha256(raw).hexdigest(),
                "raw_common_data_hit": has_common,
                "raw_table_symbols": raw_tables,
            })
            # `raw` falls out of scope each iteration; no candidate payload is retained.
    candidates.sort(key=lambda row: (0 if row["layer"] == "current" else 1, row["relative_path"].casefold()))
    return candidates, {
        "pyc_files_scanned": scanned,
        "raw_common_data_module_hits": common_hits,
        "raw_table_symbol_module_hits": table_hits,
    }


def _table_inventory(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    for module in modules:
        rel = str(module.get("relative_path") or "")
        layer = str(module.get("layer") or "")
        for symbol in module.get("raw_table_symbols") or []:
            row = inventory.setdefault(symbol, {"symbol": symbol, "raw_modules": [], "code_references": []})
            row["raw_modules"].append({"layer": layer, "relative_path": rel})
        for code in module.get("code_objects") or []:
            for symbol in code.get("table_symbols") or []:
                row = inventory.setdefault(symbol, {"symbol": symbol, "raw_modules": [], "code_references": []})
                row["code_references"].append({
                    "layer": layer,
                    "relative_path": rel,
                    "code_object": code.get("index"),
                    "qualname": code.get("qualname"),
                    "co_name": code.get("co_name"),
                    "references_common_data": bool(code.get("references_common_data")),
                    "references_env": bool(code.get("references_env")),
                })
    result = []
    for symbol, row in sorted(inventory.items()):
        row["raw_modules"] = sorted(row["raw_modules"], key=lambda item: (item["relative_path"], item["layer"]))
        row["code_references"] = sorted(row["code_references"], key=lambda item: (item["relative_path"], item["qualname"] or ""))
        row["common_data_reference_count"] = sum(bool(item["references_common_data"]) for item in row["code_references"])
        result.append(row)
    return result


def run_common_data_registry_audit(
    base: Path,
    current: Path,
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    candidates, scan_counts = _scan_candidates(base, current, activity=activity)
    activity(f"Common Data Registry Audit: found {len(candidates)} registry-signature module candidate(s)")

    modules: list[dict[str, Any]] = []
    for number, candidate in enumerate(candidates, start=1):
        path = Path(str(candidate["path"]))
        activity(
            f"Common Data Registry Audit: inspecting {number}/{len(candidates)} "
            f"{candidate['relative_path']}"
        )
        try:
            raw = path.read_bytes()
        except OSError as exc:
            module = {key: value for key, value in candidate.items() if key != "path"}
            module.update({"marshal_compatible": False, "error": f"{type(exc).__name__}: {exc}", "code_objects": []})
            modules.append(module)
            continue

        code, error = _load_code(raw)
        # Drop the raw module bytes before moving on to the next candidate. The CodeType
        # tree contains its own compact metadata and is the only object needed below.
        del raw
        module = {key: value for key, value in candidate.items() if key != "path"}
        module["marshal_compatible"] = code is not None
        module["error"] = error
        module["code_objects"] = []
        if code is not None:
            all_count = 0
            relevant: list[dict[str, Any]] = []
            for index, (qualname, obj) in enumerate(_walk(code)):
                all_count += 1
                row = _code_row(index, qualname, obj)
                if row["references_common_data"] or row["references_env"] or row["table_symbols"]:
                    relevant.append(row)
            module["code_objects"] = relevant
            module["record_counts"] = {
                "all_code_objects": all_count,
                "registry_relevant_code_objects": len(relevant),
                "common_data_code_objects": sum(bool(row["references_common_data"]) for row in relevant),
                "table_symbol_code_objects": sum(bool(row["table_symbols"]) for row in relevant),
                "common_data_and_table_code_objects": sum(bool(row["common_data_and_table_cooccur"]) for row in relevant),
            }
        modules.append(module)
        del code

    inventory = _table_inventory(modules)
    common_data_accesses = []
    for module in modules:
        for row in module.get("code_objects") or []:
            if not row.get("references_common_data"):
                continue
            common_data_accesses.append({
                "layer": module.get("layer"),
                "relative_path": module.get("relative_path"),
                "code_object": row.get("index"),
                "qualname": row.get("qualname"),
                "co_name": row.get("co_name"),
                "table_symbols": row.get("table_symbols") or [],
                "references_env": bool(row.get("references_env")),
                "co_names": row.get("co_names") or [],
                "string_constants": row.get("string_constants") or [],
            })

    report = {
        "schema": "dead-signal-common-data-registry-static-audit",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Once Human Env.common_data table registry",
        "mode": "offline-static-pyc-registry-audit-memory-bounded",
        "record_counts": {
            **scan_counts,
            "candidate_modules": len(modules),
            "marshal_compatible_modules": sum(bool(row.get("marshal_compatible")) for row in modules),
            "registry_relevant_code_objects": sum(len(row.get("code_objects") or []) for row in modules),
            "common_data_accesses": len(common_data_accesses),
            "unique_table_symbols": len(inventory),
            "tables_with_common_data_reference": sum(bool(row.get("common_data_reference_count")) for row in inventory),
        },
        "table_inventory": inventory,
        "common_data_accesses": common_data_accesses,
        "modules": modules,
        "policy": {
            "discovery": "The complete extracted PYC tree is scanned for exact raw signatures common_data and uppercase *_TABLE tokens. Discovery retains only paths and compact signature metadata.",
            "analysis": "Candidate PYC files are reopened and statically inspected one at a time; raw payloads are released before advancing.",
            "bytecode_retention": "Broad audit retains bytecode SHA-256, length, and a bounded 256-byte prefix only. Full PYC remains available at the recorded extracted path for later targeted audits.",
            "execution": "No game module is imported or executed. marshal is used only to inspect CodeType metadata.",
            "identity": "Only exact symbols/strings are reported. No fuzzy table-name inference is used.",
            "live_game": "No process handle, debugger, hook, injection, memory access, network interception, client modification, or anti-cheat interaction.",
        },
        "interpretation": {
            "goal": "Reconstruct the client's internal common-data architecture by locating table constants and the code objects that access Env.common_data.",
            "next_step": "Inspect high-connectivity common_data accessors and table-definition modules to identify the registry initializer and authoritative table-name-to-bindict mapping.",
        },
    }
    _write_json(reports_dir / "common-data-registry-static-audit.json", report)
    return report
