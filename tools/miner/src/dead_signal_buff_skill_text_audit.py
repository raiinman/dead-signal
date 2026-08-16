"""Offline static audit of buff/skill player-facing description resolution.

Targets the two exact helper modules proven by the fixed-skill audit:
- dcs_extend/common/BuffDataHelper.pyc
- dcs_extend/common/SkillMarkRuleHelper.pyc

No game module is imported or executed. marshal is used only to inspect CodeType metadata.
"""
from __future__ import annotations

import hashlib
import json
import marshal
import types
from collections import Counter
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 1
ActivityCallback = Callable[[str], None]
TARGET_SUFFIXES = (
    "dcs_extend/common/BuffDataHelper.pyc",
    "dcs_extend/common/SkillMarkRuleHelper.pyc",
)
TARGET_FUNCTIONS = {
    "get_buff_level_desc",
    "get_buff_star_desc",
    "get_format_desc",
    "get_buff_level_data",
    "get_buff_star_data",
    "get_buff_level_name",
    "get_rule_data",
    "get_desc_match_data",
    "get_desc_match_string",
    "get_grey_desc_match_string",
    "process_pure_desc_by_rate",
}
DATA_SYMBOLS = {
    "BUFF_LEVEL_DATA", "BUFF_STAR_DATA", "BUFF_LEVEL_MAP", "BUFF_STAR_MAP",
    "MARK_RULE_TABLE", "skill_mark_rule_data", "char_property_data",
}
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_CODE_PREFIX = 4096
MAX_STRINGS = 256
MAX_STRING_LEN = 1024


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
    found: list[dict[str, Any]] = []
    for layer, root in _roots(base, current):
        for suffix in TARGET_SUFFIXES:
            direct = root / Path(suffix)
            if direct.is_file():
                found.append({"layer": layer, "path": direct.resolve(), "relative_path": suffix})
                continue
            basename = Path(suffix).name
            for path in root.rglob(basename):
                rel = path.resolve().relative_to(root).as_posix()
                if rel.endswith(suffix):
                    found.append({"layer": layer, "path": path.resolve(), "relative_path": rel})
                    break
    found.sort(key=lambda row: (0 if row["layer"] == "current" else 1, row["relative_path"].casefold()))
    return found


def _load_code(path: Path) -> tuple[types.CodeType | None, str | None, int, str | None]:
    try:
        size = path.stat().st_size
        raw = path.read_bytes()
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}", 0, None
    if size > MAX_FILE_BYTES:
        return None, f"skipped: file exceeds {MAX_FILE_BYTES} byte guard", size, None
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
            result.append(value[:MAX_STRING_LEN])
        elif isinstance(value, (tuple, frozenset)):
            for item in value:
                if isinstance(item, str):
                    result.append(item[:MAX_STRING_LEN])
        if len(result) >= MAX_STRINGS:
            break
    return result[:MAX_STRINGS]


def _select(qualname: str, code: types.CodeType) -> bool:
    values = set(map(str, code.co_names)) | set(_strings(code))
    return qualname == "<module>" or code.co_name in TARGET_FUNCTIONS or bool(DATA_SYMBOLS.intersection(values))


def _row(index: int, qualname: str, code: types.CodeType) -> dict[str, Any]:
    names = list(map(str, code.co_names))
    strings = _strings(code)
    values = set(names) | set(strings)
    raw = code.co_code
    return {
        "index": index,
        "qualname": qualname,
        "co_name": code.co_name,
        "co_filename": code.co_filename,
        "co_firstlineno": code.co_firstlineno,
        "co_argcount": code.co_argcount,
        "co_varnames": list(map(str, code.co_varnames)),
        "co_names": names,
        "string_constants": strings,
        "data_symbols": sorted(DATA_SYMBOLS.intersection(values)),
        "co_code_length": len(raw),
        "co_code_sha256": hashlib.sha256(raw).hexdigest(),
        "co_code_prefix_hex": raw[:MAX_CODE_PREFIX].hex(),
    }


def run_buff_skill_text_audit(base: Path, current: Path, reports_dir: Path, *, activity: ActivityCallback | None = None) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    progress_path = reports_dir / "buff-skill-text-progress.json"
    _write_json(progress_path, {"stage": "starting", "schema_version": SCHEMA_VERSION})
    targets = _find_targets(base, current)
    modules: list[dict[str, Any]] = []
    function_counts: Counter[str] = Counter()
    symbol_counts: Counter[str] = Counter()

    for number, target in enumerate(targets, start=1):
        _write_json(progress_path, {"stage": "inspect-helper", "index": number, "total": len(targets), "relative_path": target["relative_path"]})
        activity(f"Buff/Skill Text Audit: {number}/{len(targets)} {target['relative_path']}")
        code, error, size, digest = _load_code(Path(target["path"]))
        rows: list[dict[str, Any]] = []
        all_count = 0
        if code is not None:
            for index, (qualname, obj) in enumerate(_walk(code)):
                all_count += 1
                if not _select(qualname, obj):
                    continue
                row = _row(index, qualname, obj)
                rows.append(row)
                function_counts[row["co_name"]] += 1
                symbol_counts.update(row["data_symbols"])
        modules.append({
            "layer": target["layer"], "relative_path": target["relative_path"],
            "file_size": size, "file_sha256": digest, "marshal_compatible": code is not None,
            "error": error, "all_code_objects": all_count, "selected_code_objects": len(rows), "code_objects": rows,
        })

    report = {
        "schema": "dead-signal-buff-skill-text-static-audit",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Once Human buff-backed fixed-skill description resolution",
        "mode": "offline-static-targeted-buff-skill-pyc-audit",
        "record_counts": {
            "target_modules": len(modules),
            "marshal_compatible_modules": sum(bool(row["marshal_compatible"]) for row in modules),
            "selected_code_objects": sum(row["selected_code_objects"] for row in modules),
            "functions": dict(sorted(function_counts.items())),
            "data_symbols": dict(sorted(symbol_counts.items())),
        },
        "target_functions": sorted(TARGET_FUNCTIONS),
        "target_data_symbols": sorted(DATA_SYMBOLS),
        "modules": modules,
        "policy": {
            "scope": "Only BuffDataHelper.pyc and SkillMarkRuleHelper.pyc are deeply inspected.",
            "evidence": "co_names, string constants, exact data-symbol references, and bounded raw code prefixes are static evidence.",
            "execution": "No game module is imported or executed; marshal is used only to deserialize CodeType metadata.",
            "live_game": "No process handle, debugger, hook, injection, memory access, network interception, client modification, or anti-cheat interaction.",
        },
        "next_step": "Resolve PASSIVE_TABLE buff_id through BUFF_LEVEL_DATA / BUFF_STAR_DATA to the exact description payload and compare SkillMarkRuleHelper formatting with ACTIVE_CONFIG_TABLE discription.",
    }
    _write_json(reports_dir / "buff-skill-text-static-audit.json", report)
    _write_json(progress_path, {"stage": "complete", "target_modules": len(modules)})
    return report
