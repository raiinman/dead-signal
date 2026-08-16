"""Targeted static audit of Once Human DataMgr data-type/package/proxy maps.

This audit is intentionally narrow: it only opens DataMgr.pyc from the completed
snapshot, unmarshals its CodeType tree, and records map-related constants/code
objects needed to reconstruct DataType -> package/proxy relationships. It never
imports or executes game bytecode and never touches the live game process.
"""
from __future__ import annotations

import hashlib
import json
import marshal
import types
from collections import Counter
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 3
ActivityCallback = Callable[[str], None]
TARGET_RELATIVE_SUFFIX = "game_common/helper/DataMgr.pyc"
MAP_NAMES = {
    "DATA_TYPE_MAP",
    "DATA_TYPE_PROXY_MAP",
    "DATA_NAME_MAP",
    "PACKAGE_TYPE_MAP",
    "WORLD_AREA_MASK_DATA_TYPE_MAP",
    "_PACKAGE_KEY_MAP",
}
TARGET_FUNCTION_TOKENS = (
    "package_converter",
    "_load_package_path_and_name",
    "get_data_full_name",
    "get_data_proxy_name",
    "_load_data_proxy",
    "load_data_patch",
    "load_data",
)
MAX_DEEP_FILE_BYTES = 64 * 1024 * 1024
MAX_SCALAR_STRING = 1024
MAX_SEQUENCE_ITEMS = 512
MAP_WINDOW_BYTES = 384


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


def _find_targets(base: Path, current: Path) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for layer, root in _roots(base, current):
        direct = root / Path(TARGET_RELATIVE_SUFFIX)
        if direct.is_file():
            targets.append({"layer": layer, "root": root, "path": direct.resolve(), "relative_path": TARGET_RELATIVE_SUFFIX})
            continue
        for path in root.rglob("DataMgr.pyc"):
            rel = path.resolve().relative_to(root).as_posix()
            if rel.endswith(TARGET_RELATIVE_SUFFIX):
                targets.append({"layer": layer, "root": root, "path": path.resolve(), "relative_path": rel})
    targets.sort(key=lambda row: (0 if row["layer"] == "current" else 1, row["relative_path"].casefold()))
    return targets


def _load_code(path: Path) -> tuple[types.CodeType | None, str | None, int, str | None]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}", 0, None
    if size > MAX_DEEP_FILE_BYTES:
        return None, f"skipped: file exceeds {MAX_DEEP_FILE_BYTES} byte guard", size, None
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


def _serializable_const(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return {"type": type(value).__name__, "truncated": True}
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:MAX_SCALAR_STRING]
    if isinstance(value, bytes):
        return {"type": "bytes", "length": len(value), "prefix_hex": value[:128].hex()}
    if isinstance(value, (tuple, list, frozenset, set)):
        items = list(value)[:MAX_SEQUENCE_ITEMS]
        return {
            "type": type(value).__name__,
            "length": len(value),
            "items": [_serializable_const(item, depth + 1) for item in items],
        }
    if isinstance(value, types.CodeType):
        return {"type": "code", "co_name": value.co_name, "co_firstlineno": value.co_firstlineno}
    return {"type": type(value).__name__, "repr": repr(value)[:MAX_SCALAR_STRING]}


def _code_row(index: int, qualname: str, code: types.CodeType) -> dict[str, Any]:
    names = list(map(str, code.co_names))
    string_constants = [value[:MAX_SCALAR_STRING] for value in code.co_consts if isinstance(value, str)]
    return {
        "index": index,
        "qualname": qualname,
        "co_name": code.co_name,
        "co_filename": code.co_filename,
        "co_firstlineno": code.co_firstlineno,
        "co_names": names,
        "co_varnames": list(map(str, code.co_varnames)),
        "string_constants": string_constants,
        "constants": [_serializable_const(value) for value in code.co_consts],
        "map_names_present": sorted(MAP_NAMES.intersection(names) | MAP_NAMES.intersection(string_constants)),
        "co_code_length": len(code.co_code),
        "co_code_sha256": hashlib.sha256(code.co_code).hexdigest(),
        "co_code_hex": code.co_code.hex(),
    }


def _is_target_row(qualname: str, row: dict[str, Any]) -> bool:
    name = str(row.get("co_name") or "")
    names = set(row.get("co_names") or [])
    strings = set(row.get("string_constants") or [])
    if qualname in {"<module>", "DataType", "_DataProxy", "_DataProxyBase"}:
        return True
    if MAP_NAMES.intersection(names | strings):
        return True
    lowered = name.casefold()
    return any(token in lowered for token in TARGET_FUNCTION_TOKENS)


def _candidate_datatype_members(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in rows:
        if row.get("qualname") != "DataType":
            continue
        names = [name for name in row.get("co_names") or [] if name not in {"__name__", "__module__", "__qualname__"}]
        return [{"name": name, "ordinal_candidate": index} for index, name in enumerate(names)]
    return []


def _line_ranges(code: types.CodeType) -> list[dict[str, Any]]:
    result = []
    try:
        for start, end, line in code.co_lines():
            result.append({"start_offset": start, "end_offset": end, "line": line})
    except Exception:
        pass
    return result


def _line_for_offset(ranges: list[dict[str, Any]], offset: int) -> int | None:
    for row in ranges:
        if row["start_offset"] <= offset < row["end_offset"]:
            line = row.get("line")
            return int(line) if isinstance(line, int) else None
    return None


def _numeric_wordcode(code: types.CodeType, ranges: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    raw = code.co_code
    names = list(map(str, code.co_names))
    consts = list(code.co_consts)
    ranges = ranges if ranges is not None else _line_ranges(code)
    rows = []
    for offset in range(0, len(raw) - 1, 2):
        opcode_byte = raw[offset]
        arg_byte = raw[offset + 1]
        row: dict[str, Any] = {
            "offset": offset,
            "source_line": _line_for_offset(ranges, offset),
            "opcode_byte": opcode_byte,
            "opcode_hex": f"0x{opcode_byte:02x}",
            "arg_byte": arg_byte,
        }
        if arg_byte < len(names):
            row["co_names_candidate"] = names[arg_byte]
        if arg_byte < len(consts):
            row["co_consts_candidate"] = _serializable_const(consts[arg_byte])
        rows.append(row)
    return rows


def _group_wordcode_by_line(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int | None, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.get("source_line"), []).append(row)
    result = []
    for line, items in grouped.items():
        meaningful_names = []
        meaningful_consts = []
        seen_names: set[str] = set()
        seen_consts: set[str] = set()
        for item in items:
            name = item.get("co_names_candidate")
            if isinstance(name, str) and name not in seen_names:
                seen_names.add(name)
                meaningful_names.append(name)
            const = item.get("co_consts_candidate")
            if isinstance(const, (str, int, float, bool)) or const is None:
                key = json.dumps(const, ensure_ascii=False, sort_keys=True)
                if key not in seen_consts:
                    seen_consts.add(key)
                    meaningful_consts.append(const)
        result.append({
            "source_line": line,
            "start_offset": min(item["offset"] for item in items),
            "end_offset": max(item["offset"] for item in items) + 2,
            "word_count": len(items),
            "name_candidates": meaningful_names,
            "scalar_const_candidates": meaningful_consts,
            "numeric_wordcode": items,
        })
    result.sort(key=lambda row: (row["source_line"] is None, row["source_line"] if row["source_line"] is not None else 10**9, row["start_offset"]))
    return result


def _map_assignment_windows(code: types.CodeType) -> list[dict[str, Any]]:
    """Locate numeric instruction words whose argument indexes a known map name.

    We deliberately do not assign semantic opcode names. The output is structural
    evidence only: raw opcode/argument bytes, nearby words, co_names/co_consts
    candidates, and original source-line grouping from the preserved line table.
    """
    names = list(map(str, code.co_names))
    raw = code.co_code
    ranges = _line_ranges(code)
    wordcode = _numeric_wordcode(code, ranges)
    results: list[dict[str, Any]] = []
    for offset in range(0, len(raw) - 1, 2):
        arg = raw[offset + 1]
        if arg >= len(names) or names[arg] not in MAP_NAMES:
            continue
        start = max(0, offset - MAP_WINDOW_BYTES)
        end = min(len(raw), offset + MAP_WINDOW_BYTES + 2)
        nearby = [row for row in wordcode if start <= row["offset"] < end]
        line_hits = [row for row in ranges if row["start_offset"] <= offset < row["end_offset"]]
        results.append({
            "map_name": names[arg],
            "offset": offset,
            "opcode_byte": raw[offset],
            "opcode_hex": f"0x{raw[offset]:02x}",
            "arg_byte": arg,
            "window_start": start,
            "window_end": end,
            "raw_window_hex": raw[start:end].hex(),
            "line_ranges_at_offset": line_hits,
            "numeric_wordcode_window": nearby,
            "source_line_groups": _group_wordcode_by_line(nearby),
        })
    return results


def run_datamgr_map_audit(
    base: Path,
    current: Path,
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    targets = _find_targets(base, current)
    activity(f"DataMgr Map Audit: found {len(targets)} target module(s)")
    modules: list[dict[str, Any]] = []

    for number, target in enumerate(targets, start=1):
        activity(f"DataMgr Map Audit: inspecting {number}/{len(targets)} {target['relative_path']}")
        code, error, size, digest = _load_code(Path(target["path"]))
        selected: list[dict[str, Any]] = []
        all_count = 0
        assignment_windows: list[dict[str, Any]] = []
        module_line_ranges: list[dict[str, Any]] = []
        if code is not None:
            assignment_windows = _map_assignment_windows(code)
            module_line_ranges = _line_ranges(code)
            for index, (qualname, obj) in enumerate(_walk(code)):
                all_count += 1
                row = _code_row(index, qualname, obj)
                if _is_target_row(qualname, row):
                    selected.append(row)
        modules.append({
            "layer": target["layer"],
            "relative_path": target["relative_path"],
            "file_size": size,
            "file_sha256": digest,
            "marshal_compatible": code is not None,
            "error": error,
            "all_code_objects": all_count,
            "selected_code_objects": len(selected),
            "code_objects": selected,
            "datatype_member_candidates": _candidate_datatype_members(selected),
            "module_line_ranges": module_line_ranges,
            "map_assignment_windows": assignment_windows,
        })

    current_module = next((row for row in modules if row["layer"] == "current"), modules[0] if modules else None)
    report = {
        "schema": "dead-signal-datamgr-map-static-audit",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Once Human DataMgr DataType/package/proxy maps",
        "mode": "offline-static-targeted-datamgr-pyc-audit",
        "record_counts": {
            "target_modules": len(modules),
            "marshal_compatible_modules": sum(bool(row["marshal_compatible"]) for row in modules),
            "selected_code_objects": sum(row["selected_code_objects"] for row in modules),
            "datatype_member_candidates": len((current_module or {}).get("datatype_member_candidates") or []),
            "map_assignment_windows": sum(len(row.get("map_assignment_windows") or []) for row in modules),
        },
        "map_names": sorted(MAP_NAMES),
        "current_datatype_member_candidates": (current_module or {}).get("datatype_member_candidates") or [],
        "current_map_assignment_windows": (current_module or {}).get("map_assignment_windows") or [],
        "modules": modules,
        "policy": {
            "scope": "Only game_common/helper/DataMgr.pyc is deeply inspected from completed offline snapshots.",
            "opcode_semantics": "Numeric opcode/argument bytes are retained without assigning stock Python opcode names. co_names/co_consts values are emitted only as index candidates for structural analysis.",
            "datatype_ordinals": "ordinal_candidate is an observed class-member ordering candidate, not yet a verified enum numeric value unless independently corroborated.",
            "map_windows": "Map assignment windows are structural evidence around numeric instruction words whose argument indexes a known map name; source_line_groups come only from CodeType.co_lines() and do not assert opcode semantics.",
            "execution": "No game module is imported or executed; marshal is used only to deserialize CodeType metadata.",
            "live_game": "No process handle, debugger, hook, injection, memory access, network interception, client modification, or anti-cheat interaction.",
        },
        "next_step": "Use source-line-grouped numeric map evidence to reconstruct individual DATA_TYPE_MAP and DATA_TYPE_PROXY_MAP entries, then corroborate against accessor/converter functions before publication.",
    }
    _write_json(reports_dir / "datamgr-map-static-audit.json", report)
    return report
