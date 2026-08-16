"""Static instruction-window tracing for exact fixed_skill_code consumers.

This module never imports or executes Once Human bytecode. It only unmarshals code
objects from retained PYC files and disassembles the already-identified direct
consumers so research can see what names/constants/operations immediately surround
the fixed_skill_code read.
"""
from __future__ import annotations

import dis
import marshal
import types
from collections import Counter
from pathlib import Path
from typing import Any, Callable

ActivityCallback = Callable[[str], None]
TARGET_SYMBOL = "fixed_skill_code"
WINDOW_RADIUS = 18
MAX_WINDOW_INSTRUCTIONS = 160
INTEREST_TOKENS = (
    "skill",
    "buff",
    "data",
    "config",
    "star",
    "fixed",
    "package",
    "affix",
    "blueprint",
    "passive",
    "stardust",
)


def _load_marshaled_root(raw: bytes) -> tuple[types.CodeType | None, str | None]:
    if len(raw) < 17:
        return None, "PYC file is too small"
    try:
        root = marshal.loads(raw[16:])
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(root, types.CodeType):
        return None, "marshal payload was not CodeType"
    return root, None


def _walk_code(code: types.CodeType, qualname: str = "<module>"):
    yield qualname, code
    occurrence: Counter[str] = Counter()
    for value in code.co_consts:
        if not isinstance(value, types.CodeType):
            continue
        occurrence[value.co_name] += 1
        suffix = f"#{occurrence[value.co_name]}" if occurrence[value.co_name] > 1 else ""
        child = value.co_name + suffix
        child_name = child if qualname == "<module>" else f"{qualname}.{child}"
        yield from _walk_code(value, child_name)


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, tuple) and len(value) <= 12 and all(
        item is None or isinstance(item, (str, int, float, bool)) for item in value
    ):
        return list(value)
    return None


def _interesting(values: set[str]) -> list[str]:
    return sorted(
        value for value in values
        if value == TARGET_SYMBOL or any(token in value.casefold() for token in INTEREST_TOKENS)
    )[:128]


def _instruction_windows(code: types.CodeType) -> tuple[list[dict[str, Any]], int, str | None]:
    try:
        instructions = list(dis.get_instructions(code, show_caches=False))
    except Exception as exc:
        return [], 0, f"{type(exc).__name__}: {exc}"

    anchors = [index for index, ins in enumerate(instructions) if ins.argval == TARGET_SYMBOL]
    if not anchors:
        return [], 0, None

    selected: set[int] = set()
    for anchor in anchors:
        start = max(0, anchor - WINDOW_RADIUS)
        end = min(len(instructions), anchor + WINDOW_RADIUS + 1)
        selected.update(range(start, end))
    ordered = sorted(selected)[:MAX_WINDOW_INSTRUCTIONS]

    rows: list[dict[str, Any]] = []
    previous = None
    for index in ordered:
        if previous is not None and index != previous + 1:
            rows.append({"gap": True})
        ins = instructions[index]
        row = {
            "index": index,
            "offset": ins.offset,
            "opname": ins.opname,
            "argrepr": ins.argrepr,
            "starts_line": ins.starts_line,
            "is_fixed_skill_anchor": ins.argval == TARGET_SYMBOL,
        }
        safe = _safe_value(ins.argval)
        if safe is not None:
            row["argval"] = safe
        rows.append(row)
        previous = index
    return rows, len(anchors), None


def trace_fixed_skill_flows(
    roots: list[tuple[str, Path]],
    consumer_trace: dict[str, Any],
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    """Disassemble only direct fixed_skill_code consumer functions.

    Candidate files come from the exact-symbol consumer scan; this function does
    not perform a second broad corpus crawl.
    """
    activity = activity or (lambda _message: None)
    root_by_layer = {layer: root for layer, root in roots}
    candidates = consumer_trace.get("direct_consumer_candidates") or []
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    anchor_count = 0

    activity(f"Missing Skill Forensics: tracing {len(candidates)} direct fixed-skill consumer files")
    for candidate in candidates:
        layer = str(candidate.get("layer") or "")
        relative = str(candidate.get("relative_path") or "")
        root = root_by_layer.get(layer)
        if root is None or not relative:
            errors.append({"layer": layer, "relative_path": relative, "error": "source root unavailable"})
            continue
        path = root / Path(relative)
        try:
            raw = path.read_bytes()
        except OSError as exc:
            errors.append({"layer": layer, "relative_path": relative, "error": f"{type(exc).__name__}: {exc}"})
            continue
        code_root, error = _load_marshaled_root(raw)
        if code_root is None:
            errors.append({"layer": layer, "relative_path": relative, "error": error or "marshal decode failed"})
            continue

        for qualname, code in _walk_code(code_root):
            strings = {value for value in code.co_consts if isinstance(value, str)}
            names = set(map(str, code.co_names))
            varnames = set(map(str, code.co_varnames))
            if TARGET_SYMBOL not in (strings | names | varnames):
                continue
            windows, anchors, dis_error = _instruction_windows(code)
            if dis_error:
                errors.append({
                    "layer": layer,
                    "relative_path": relative,
                    "error": f"{qualname}: {dis_error}",
                })
                continue
            anchor_count += anchors
            rows.append({
                "layer": layer,
                "relative_path": relative,
                "qualname": qualname,
                "co_name": code.co_name,
                "co_filename": code.co_filename,
                "co_firstlineno": code.co_firstlineno,
                "fixed_skill_anchor_count": anchors,
                "referenced_names": _interesting(names),
                "local_names": _interesting(varnames),
                "string_constants": _interesting(strings),
                "instruction_window": windows,
            })

    parent_status = str(consumer_trace.get("status") or "unknown")
    if not roots:
        status = "raw-source-roots-unavailable"
    elif parent_status != "complete":
        status = "partial-parent-consumer-scan"
    elif errors:
        status = "complete-with-read-errors"
    else:
        status = "complete"

    return {
        "status": status,
        "record_counts": {
            "candidate_files": len(candidates),
            "consumer_functions": len(rows),
            "fixed_skill_instruction_anchors": anchor_count,
            "errors": len(errors),
        },
        "functions": rows,
        "errors": errors,
        "policy": {
            "scope": "Only exact direct consumer files already identified by consumer_trace are disassembled.",
            "execution": "PYC code objects are unmarshaled and disassembled only; game bytecode is never executed.",
            "interpretation": (
                "Instruction windows are static evidence of nearby operations and symbols, not proof of runtime values "
                "or player-facing mechanic semantics."
            ),
        },
    }
