"""Full offline static audit of Once Human's BluePrintScrollViewPart.pyc.

This module deliberately does *not* narrow to suspected Blueprint handlers.  It
walks every code object in the extracted BluePrintScrollViewPart.pyc module and
preserves the module's complete static Python metadata, constants, raw bytecode,
and bounded diagnostic disassembly.  Game bytecode is never imported or executed
and the live game process is never opened.
"""
from __future__ import annotations

import dis
import hashlib
import json
import marshal
import types
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from weapon_progression import _padded_disassembly, _serialise_instructions

SCHEMA_VERSION = 1
TARGET_BASENAME = "blueprintscrollviewpart.pyc"
ActivityCallback = Callable[[str], None]


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


def _find_modules(base: Path, current: Path, *, activity: ActivityCallback) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    seen: set[str] = set()
    for layer, root in _roots(base, current):
        activity(f"Blueprint Module Audit: searching extracted {layer} PYC root for {TARGET_BASENAME}")
        for path in root.rglob("*.pyc"):
            if path.name.casefold() != TARGET_BASENAME:
                continue
            resolved = path.resolve()
            key = str(resolved).casefold()
            if key in seen:
                continue
            seen.add(key)
            matches.append({
                "layer": layer,
                "source_root": str(root),
                "path": resolved,
                "relative_path": resolved.relative_to(root).as_posix(),
            })
    matches.sort(key=lambda row: (0 if row["layer"] == "current" else 1, row["relative_path"].casefold()))
    return matches


def _load_code(path: Path) -> tuple[types.CodeType | None, bytes, str | None]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, b"", f"{type(exc).__name__}: {exc}"
    if len(raw) < 17:
        return None, raw, "PYC file is too small"
    try:
        code = marshal.loads(raw[16:])
    except Exception as exc:
        return None, raw, f"{type(exc).__name__}: {exc}"
    if not isinstance(code, types.CodeType):
        return None, raw, "marshal payload was not a CodeType"
    return code, raw, None


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


def _constant(value: Any) -> dict[str, Any]:
    if isinstance(value, types.CodeType):
        return {
            "type": "code",
            "name": value.co_name,
            "firstlineno": value.co_firstlineno,
        }
    if value is None or isinstance(value, (bool, int, float, str)):
        return {"type": type(value).__name__, "value": value}
    if isinstance(value, bytes):
        return {
            "type": "bytes",
            "length": len(value),
            "sha256": hashlib.sha256(value).hexdigest(),
            "hex": value.hex(),
        }
    if isinstance(value, tuple):
        return {"type": "tuple", "length": len(value), "items": [_constant(item) for item in value]}
    if isinstance(value, frozenset):
        items = [_constant(item) for item in value]
        return {"type": "frozenset", "length": len(items), "items": items}
    return {"type": type(value).__name__, "repr": repr(value)}


def _instructions(code: types.CodeType) -> dict[str, Any]:
    warning = (
        "Diagnostic only: Once Human may remap opcode numbers. Raw co_code bytes, operands, names, and constants are preserved; "
        "stock Python opnames are not treated as authoritative semantics."
    )
    try:
        values = list(dis.get_instructions(code, show_caches=True))
        error = None
    except Exception as exc:
        values, padded_error = _padded_disassembly(code)
        error = f"{type(exc).__name__}: {exc}"
        if padded_error:
            error += f"; padded disassembly: {padded_error}"
    # One module is the explicit research target, so keep the full diagnostic stream.
    serialised = _serialise_instructions(values or [], 1_000_000)
    return {"warning": warning, "error": error, "instructions": serialised}


def _code_row(index: int, qualname: str, code: types.CodeType) -> dict[str, Any]:
    constants = [_constant(value) for value in code.co_consts]
    strings = [value for value in code.co_consts if isinstance(value, str)]
    return {
        "index": index,
        "qualname": qualname,
        "co_name": code.co_name,
        "co_filename": code.co_filename,
        "co_firstlineno": code.co_firstlineno,
        "co_argcount": code.co_argcount,
        "co_posonlyargcount": getattr(code, "co_posonlyargcount", 0),
        "co_kwonlyargcount": code.co_kwonlyargcount,
        "co_nlocals": code.co_nlocals,
        "co_stacksize": code.co_stacksize,
        "co_flags": code.co_flags,
        "co_names": list(map(str, code.co_names)),
        "co_varnames": list(map(str, code.co_varnames)),
        "co_cellvars": list(map(str, code.co_cellvars)),
        "co_freevars": list(map(str, code.co_freevars)),
        "string_constants": strings,
        "constants": constants,
        "co_code_length": len(code.co_code),
        "co_code_sha256": hashlib.sha256(code.co_code).hexdigest(),
        "co_code_hex": code.co_code.hex(),
        "diagnostic_disassembly": _instructions(code),
    }


def _build_indexes(rows: list[dict[str, Any]]) -> dict[str, Any]:
    names: dict[str, list[int]] = defaultdict(list)
    strings: dict[str, list[int]] = defaultdict(list)
    functions: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        idx = int(row["index"])
        functions[str(row.get("co_name") or "")].append(idx)
        for name in row.get("co_names") or []:
            names[str(name)].append(idx)
        for value in row.get("string_constants") or []:
            strings[str(value)].append(idx)
    return {
        "function_name_to_code_objects": dict(sorted(functions.items())),
        "co_name_symbol_to_code_objects": dict(sorted(names.items())),
        "string_constant_to_code_objects": dict(sorted(strings.items())),
    }


def _build_reference_edges(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_function: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        by_function[str(row.get("co_name") or "")].append(int(row["index"]))
    edges: list[dict[str, Any]] = []
    seen: set[tuple[int, int, str]] = set()
    for row in rows:
        source = int(row["index"])
        for symbol in row.get("co_names") or []:
            for target in by_function.get(str(symbol), []):
                if source == target:
                    continue
                key = (source, target, str(symbol))
                if key in seen:
                    continue
                seen.add(key)
                edges.append({"source": source, "target": target, "symbol": str(symbol), "basis": "co_names-exact"})
    return edges


def run_blueprint_module_audit(
    base: Path,
    current: Path,
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    """Audit every code object in every extracted BluePrintScrollViewPart.pyc candidate."""
    activity = activity or (lambda _message: None)
    candidates = _find_modules(base, current, activity=activity)
    activity(f"Blueprint Module Audit: found {len(candidates)} module candidate(s)")

    modules: list[dict[str, Any]] = []
    for candidate in candidates:
        path = candidate["path"]
        activity(f"Blueprint Module Audit: statically reading {candidate['relative_path']} ({candidate['layer']})")
        code, raw, error = _load_code(path)
        module: dict[str, Any] = {
            "layer": candidate["layer"],
            "relative_path": candidate["relative_path"],
            "file_size": len(raw),
            "file_sha256": hashlib.sha256(raw).hexdigest() if raw else None,
            "marshal_compatible": code is not None,
            "error": error,
            "code_objects": [],
            "indexes": {},
            "reference_edges": [],
        }
        if code is not None:
            rows = [_code_row(index, qualname, obj) for index, (qualname, obj) in enumerate(_walk(code))]
            module["code_objects"] = rows
            module["indexes"] = _build_indexes(rows)
            module["reference_edges"] = _build_reference_edges(rows)
            module["record_counts"] = {
                "code_objects": len(rows),
                "reference_edges": len(module["reference_edges"]),
                "unique_function_names": len(module["indexes"]["function_name_to_code_objects"]),
                "unique_co_names": len(module["indexes"]["co_name_symbol_to_code_objects"]),
                "unique_string_constants": len(module["indexes"]["string_constant_to_code_objects"]),
            }
            activity(
                f"Blueprint Module Audit: {candidate['layer']} module yielded {len(rows)} code objects, "
                f"{module['record_counts']['unique_co_names']} unique names, "
                f"{module['record_counts']['unique_string_constants']} unique strings"
            )
        modules.append(module)

    report = {
        "schema": "dead-signal-blueprint-scroll-view-full-static-audit",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "BluePrintScrollViewPart.pyc",
        "mode": "offline-full-module-static-pyc-audit",
        "target_basename": TARGET_BASENAME,
        "record_counts": {
            "candidate_modules": len(modules),
            "marshal_compatible_modules": sum(bool(row.get("marshal_compatible")) for row in modules),
            "code_objects": sum(len(row.get("code_objects") or []) for row in modules),
            "reference_edges": sum(len(row.get("reference_edges") or []) for row in modules),
        },
        "modules": modules,
        "policy": {
            "scope": "No function or symbol filtering. Every nested code object in BluePrintScrollViewPart.pyc is retained.",
            "execution": "The PYC marshal payload is deserialized for static CodeType inspection only. No game bytecode is executed.",
            "semantics": "co_names, constants, raw co_code, and exact metadata are authoritative observations; stock dis opnames are diagnostic only.",
            "live_game": "No game process handle, debugger, hook, injection, memory read, client modification, or anti-cheat interaction.",
        },
    }
    _write_json(reports_dir / "blueprint-scroll-view-full-static-audit.json", report)
    return report
