"""Bounded static audit of Once Human DataMgr data-type/package/proxy maps.

Only game_common/helper/DataMgr.pyc from completed offline snapshots is opened.
The game module is never imported or executed. The audit preserves compact,
line-local structural evidence around the DataMgr map assignments without
materializing or serializing the complete module bytecode multiple times.
"""
from __future__ import annotations

import hashlib
import json
import marshal
import types
from collections import Counter
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 4
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
MAX_NAME_ITEMS = 384
MAX_STRING_ITEMS = 192
MAX_STRING_LENGTH = 512
MAX_CODE_PREFIX_BYTES = 256
MAX_LINE_SLICE_BYTES = 1536
MAX_LINE_WORDS = 768


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _source_root(snapshot: Path) -> Path | None:
    payload = _read_json(snapshot / "snapshot.json", {}) or {}
    raw = payload.get("source_root") if isinstance(payload, dict) else None
    if not raw:
        return None
    root = Path(str(raw)).expanduser()
    if not root.is_absolute():
        root = (snapshot / root).resolve()
    else:
        root = root.resolve()
    return root if root.is_dir() else None


def _targets(base: Path, current: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for layer, snapshot in (("current", current), ("base", base)):
        root = _source_root(snapshot)
        if root is None:
            continue
        root_key = str(root).casefold()
        if root_key in seen:
            continue
        seen.add(root_key)
        direct = root / Path(TARGET_RELATIVE_SUFFIX)
        if direct.is_file():
            rows.append({"layer": layer, "path": direct.resolve(), "relative_path": TARGET_RELATIVE_SUFFIX})
            continue
        for path in root.rglob("DataMgr.pyc"):
            resolved = path.resolve()
            relative = resolved.relative_to(root).as_posix()
            if relative.endswith(TARGET_RELATIVE_SUFFIX):
                rows.append({"layer": layer, "path": resolved, "relative_path": relative})
                break
    rows.sort(key=lambda row: (0 if row["layer"] == "current" else 1, row["relative_path"].casefold()))
    return rows


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
    counts: Counter[str] = Counter()
    for value in code.co_consts:
        if not isinstance(value, types.CodeType):
            continue
        counts[value.co_name] += 1
        suffix = f"#{counts[value.co_name]}" if counts[value.co_name] > 1 else ""
        child = value.co_name + suffix
        child_qualname = child if qualname == "<module>" else f"{qualname}.{child}"
        yield from _walk(value, child_qualname)


def _scalar_const(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:MAX_STRING_LENGTH]
    if isinstance(value, bytes):
        return {"type": "bytes", "length": len(value), "prefix_hex": value[:64].hex()}
    if isinstance(value, types.CodeType):
        return {"type": "code", "co_name": value.co_name, "co_firstlineno": value.co_firstlineno}
    if isinstance(value, tuple) and len(value) <= 32:
        compact = []
        for item in value:
            if item is None or isinstance(item, (bool, int, float, str)):
                compact.append(_scalar_const(item))
            else:
                return {"type": "tuple", "length": len(value)}
        return {"type": "tuple", "length": len(value), "items": compact}
    return {"type": type(value).__name__}


def _strings(code: types.CodeType) -> list[str]:
    result: list[str] = []
    for value in code.co_consts:
        if isinstance(value, str):
            result.append(value[:MAX_STRING_LENGTH])
            if len(result) >= MAX_STRING_ITEMS:
                break
    return result


def _is_relevant(qualname: str, code: types.CodeType) -> bool:
    if qualname in {"<module>", "DataType", "_DataProxy", "_DataProxyBase", "_DataMgrBase"}:
        return True
    name = code.co_name.casefold()
    if any(token in name for token in TARGET_FUNCTION_TOKENS):
        return True
    names = set(map(str, code.co_names))
    strings = set(_strings(code))
    return bool(MAP_NAMES.intersection(names | strings))


def _code_summary(index: int, qualname: str, code: types.CodeType) -> dict[str, Any]:
    names = list(map(str, code.co_names))[:MAX_NAME_ITEMS]
    strings = _strings(code)
    return {
        "index": index,
        "qualname": qualname,
        "co_name": code.co_name,
        "co_filename": code.co_filename,
        "co_firstlineno": code.co_firstlineno,
        "co_names": names,
        "co_varnames": list(map(str, code.co_varnames))[:MAX_NAME_ITEMS],
        "string_constants": strings,
        "map_names_present": sorted(MAP_NAMES.intersection(names) | MAP_NAMES.intersection(strings)),
        "nested_code_names": [value.co_name for value in code.co_consts if isinstance(value, types.CodeType)][:MAX_NAME_ITEMS],
        "co_code_length": len(code.co_code),
        "co_code_sha256": hashlib.sha256(code.co_code).hexdigest(),
        "co_code_prefix_hex": code.co_code[:MAX_CODE_PREFIX_BYTES].hex(),
    }


def _datatype_members(code: types.CodeType) -> list[dict[str, Any]]:
    for qualname, obj in _walk(code):
        if qualname != "DataType":
            continue
        names = [
            name for name in map(str, obj.co_names)
            if name not in {"__name__", "__module__", "__qualname__"}
        ]
        return [{"name": name, "ordinal_candidate": index} for index, name in enumerate(names)]
    return []


def _line_ranges(code: types.CodeType) -> list[tuple[int, int, int | None]]:
    try:
        return list(code.co_lines())
    except Exception:
        return []


def _source_line_for_offset(ranges: list[tuple[int, int, int | None]], offset: int) -> int | None:
    for start, end, line in ranges:
        if start <= offset < end:
            return int(line) if isinstance(line, int) else None
    return None


def _line_bounds(ranges: list[tuple[int, int, int | None]], source_line: int | None, fallback: int) -> tuple[int, int]:
    if source_line is None:
        return fallback, fallback + 2
    hits = [(start, end) for start, end, line in ranges if line == source_line]
    if not hits:
        return fallback, fallback + 2
    start = min(item[0] for item in hits)
    end = max(item[1] for item in hits)
    if end - start > MAX_LINE_SLICE_BYTES:
        half = MAX_LINE_SLICE_BYTES // 2
        start = max(start, fallback - half)
        end = min(end, start + MAX_LINE_SLICE_BYTES)
    return start, end


def _word_rows(code: types.CodeType, start: int, end: int, source_line: int | None) -> list[dict[str, Any]]:
    raw = code.co_code
    names = list(map(str, code.co_names))
    consts = list(code.co_consts)
    result: list[dict[str, Any]] = []
    aligned_start = start if start % 2 == 0 else start + 1
    for offset in range(aligned_start, min(end, len(raw) - 1), 2):
        if len(result) >= MAX_LINE_WORDS:
            break
        opcode_byte = raw[offset]
        arg_byte = raw[offset + 1]
        row: dict[str, Any] = {
            "offset": offset,
            "source_line": source_line,
            "opcode_byte": opcode_byte,
            "arg_byte": arg_byte,
        }
        if arg_byte < len(names):
            row["co_names_candidate"] = names[arg_byte]
        if arg_byte < len(consts):
            candidate = _scalar_const(consts[arg_byte])
            if candidate is not None or isinstance(consts[arg_byte], (bool, int, float, str)):
                row["co_consts_candidate"] = candidate
        result.append(row)
    return result


def _map_line_evidence(code: types.CodeType) -> list[dict[str, Any]]:
    """Return one compact, deduplicated source-line slice per map-name hit.

    No opcode mnemonic is inferred. An instruction is only considered a map-name
    hit when its raw argument byte directly indexes the map name in co_names.
    This is structural evidence, not execution or semantic decompilation.
    """
    raw = code.co_code
    names = list(map(str, code.co_names))
    ranges = _line_ranges(code)
    evidence: list[dict[str, Any]] = []
    seen: set[tuple[str, int | None]] = set()

    for offset in range(0, len(raw) - 1, 2):
        arg = raw[offset + 1]
        if arg >= len(names):
            continue
        map_name = names[arg]
        if map_name not in MAP_NAMES:
            continue
        source_line = _source_line_for_offset(ranges, offset)
        key = (map_name, source_line)
        if key in seen:
            continue
        seen.add(key)
        start, end = _line_bounds(ranges, source_line, offset)
        words = _word_rows(code, start, end, source_line)
        name_candidates: list[str] = []
        scalar_candidates: list[Any] = []
        seen_names: set[str] = set()
        seen_scalars: set[str] = set()
        for word in words:
            name = word.get("co_names_candidate")
            if isinstance(name, str) and name not in seen_names:
                seen_names.add(name)
                name_candidates.append(name)
            if "co_consts_candidate" in word:
                value = word["co_consts_candidate"]
                if isinstance(value, (str, int, float, bool)) or value is None:
                    marker = json.dumps(value, ensure_ascii=False, sort_keys=True)
                    if marker not in seen_scalars:
                        seen_scalars.add(marker)
                        scalar_candidates.append(value)
        evidence.append({
            "map_name": map_name,
            "assignment_offset": offset,
            "source_line": source_line,
            "line_start_offset": start,
            "line_end_offset": end,
            "line_byte_length": max(0, end - start),
            "raw_line_hex": raw[start:end].hex(),
            "name_candidates": name_candidates,
            "scalar_const_candidates": scalar_candidates,
            "numeric_words": words,
        })

    evidence.sort(key=lambda row: (row["source_line"] is None, row["source_line"] or 10**9, row["assignment_offset"]))
    return evidence


def run_datamgr_map_audit(
    base: Path,
    current: Path,
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    progress_path = reports_dir / "datamgr-map-progress.json"
    targets = _targets(base, current)
    _write_json(progress_path, {"stage": "starting", "schema_version": SCHEMA_VERSION, "targets": len(targets)})
    activity(f"DataMgr Map Audit: found {len(targets)} target module(s)")

    modules: list[dict[str, Any]] = []
    for number, target in enumerate(targets, start=1):
        _write_json(progress_path, {
            "stage": "target",
            "index": number,
            "total": len(targets),
            "layer": target["layer"],
            "relative_path": target["relative_path"],
        })
        activity(f"DataMgr Map Audit: inspecting {number}/{len(targets)} {target['relative_path']}")
        code, error, size, digest = _load_code(Path(target["path"]))
        summaries: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        members: list[dict[str, Any]] = []
        all_code_objects = 0

        if code is not None:
            evidence = _map_line_evidence(code)
            members = _datatype_members(code)
            for index, (qualname, obj) in enumerate(_walk(code)):
                all_code_objects += 1
                if _is_relevant(qualname, obj):
                    summaries.append(_code_summary(index, qualname, obj))

        modules.append({
            "layer": target["layer"],
            "relative_path": target["relative_path"],
            "file_size": size,
            "file_sha256": digest,
            "marshal_compatible": code is not None,
            "error": error,
            "all_code_objects": all_code_objects,
            "selected_code_objects": len(summaries),
            "code_objects": summaries,
            "datatype_member_candidates": members,
            "map_line_evidence": evidence,
        })
        code = None

    current_module = next((row for row in modules if row["layer"] == "current"), modules[0] if modules else {})
    report = {
        "schema": "dead-signal-datamgr-map-static-audit",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Once Human DataMgr DataType/package/proxy maps",
        "mode": "offline-static-targeted-datamgr-line-evidence-bounded",
        "record_counts": {
            "target_modules": len(modules),
            "marshal_compatible_modules": sum(bool(row["marshal_compatible"]) for row in modules),
            "selected_code_objects": sum(int(row["selected_code_objects"]) for row in modules),
            "datatype_member_candidates": len(current_module.get("datatype_member_candidates") or []),
            "map_line_evidence_records": sum(len(row.get("map_line_evidence") or []) for row in modules),
        },
        "map_names": sorted(MAP_NAMES),
        "current_datatype_member_candidates": current_module.get("datatype_member_candidates") or [],
        "current_map_line_evidence": current_module.get("map_line_evidence") or [],
        "modules": modules,
        "policy": {
            "scope": "Only game_common/helper/DataMgr.pyc is deeply inspected from completed offline snapshots.",
            "memory": "Complete module bytecode and complete line tables are not serialized. Evidence is deduplicated to bounded source-line slices around map-name hits.",
            "opcode_semantics": "Numeric opcode/argument bytes are retained without assigning stock Python opcode names.",
            "datatype_ordinals": "ordinal_candidate is observed DataType class-member ordering, not a verified enum numeric value unless independently corroborated.",
            "map_line_evidence": "A map-line record proves only that the map name is indexed by a raw instruction argument on that preserved source line; candidate name/constant indices are structural leads until corroborated.",
            "execution": "No game module is imported or executed; marshal is used only to deserialize CodeType metadata.",
            "live_game": "No process handle, debugger, hook, injection, memory access, network interception, client modification, or anti-cheat interaction.",
        },
        "next_step": "Use bounded source-line records to reconstruct map entries and corroborate candidate pairs against DataMgr accessor/converter functions before publication.",
    }
    _write_json(reports_dir / "datamgr-map-static-audit.json", report)
    _write_json(progress_path, {
        "stage": "complete",
        "schema_version": SCHEMA_VERSION,
        "targets": len(modules),
        "map_line_evidence_records": report["record_counts"]["map_line_evidence_records"],
    })
    return report
