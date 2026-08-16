"""Offline-only Weapon Description bytecode data-flow tracer.

This module never imports, executes, attaches to, or modifies the Once Human
client. It reads only already-extracted PYC files referenced by a completed Dead
Signal Miner snapshot, unmarshals code objects, and preserves static metadata and
raw wordcode around the Weapon item-detail description path.

The goal is intentionally narrow: recover the client-side producer chain around
``ItemDataTools.get_weapon_item_data`` / ``get_item_desc_text`` and the output
key ``prototype_desc`` after the exact prototype-table hypothesis was ruled out.
"""
from __future__ import annotations

import dis
import json
import marshal
import re
import sys
import types
from collections import Counter, deque
from pathlib import Path
from typing import Any, Callable

from weapon_progression import (
    _code_capsule,
    _padded_disassembly,
    _raw_wordcode,
    _serialise_instructions,
    _walk_code_objects,
)

SCHEMA_VERSION = 1
ActivityCallback = Callable[[str], None]

TARGET_PYC_BASENAMES = {
    "itemdatatools.pyc",
    "blueprinthelper.pyc",
}
TARGET_FUNCTIONS = {
    "get_weapon_item_data",
    "get_item_desc_text",
    "get_weapon_prototype_data",
    "get_weapon_prototype_data_val_by_key",
}
TARGET_SYMBOLS = {
    "prototype_desc",
    "get_item_desc_text",
    "get_weapon_item_data",
    "weapon_prototype_data",
    "get_weapon_prototype_data",
    "get_weapon_prototype_data_val_by_key",
}
RELEVANT_NAME = re.compile(
    r"(?:desc|text|item|weapon|prototype|blueprint|translate|local|lang|display|detail|tooltip|copy|data)",
    re.IGNORECASE,
)


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


def _snapshot_source_root(snapshot: Path) -> Path | None:
    payload = _read_json(snapshot, {}) or {}
    raw = payload.get("source_root") if isinstance(payload, dict) else None
    if not raw:
        return None
    root = Path(str(raw)).expanduser()
    return root.resolve() if root.exists() else None


def _candidate_roots(base: Path, current: Path) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for layer, snapshot in (("current", current / "snapshot.json"), ("base", base / "snapshot.json")):
        root = _snapshot_source_root(snapshot)
        if root is None:
            continue
        key = str(root).casefold()
        if key in seen:
            continue
        seen.add(key)
        roots.append((layer, root))
    return roots


def _find_target_pycs(base: Path, current: Path, *, activity: ActivityCallback) -> list[dict[str, Any]]:
    roots = _candidate_roots(base, current)
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for layer, root in roots:
        activity(f"Description Data Flow: scanning extracted PYC root ({layer}) for two target modules")
        for path in root.rglob("*.pyc"):
            if path.name.casefold() not in TARGET_PYC_BASENAMES:
                continue
            key = str(path.resolve()).casefold()
            if key in seen:
                continue
            seen.add(key)
            found.append({
                "layer": layer,
                "source_root": str(root),
                "path": path,
                "relative_path": path.relative_to(root).as_posix(),
            })
    found.sort(key=lambda row: (row["relative_path"].casefold(), row["layer"]))
    return found


def _safe_strings(values) -> list[str]:
    return [str(value) for value in values if isinstance(value, str)]


def _diagnostic_disassembly(code_obj: types.CodeType) -> dict[str, Any]:
    """Return static instruction diagnostics without treating stock opnames as proof.

    Once Human remaps opcode numbers. Metadata operands remain useful, but the
    operation labels produced by the local Python runtime may be wrong. Raw
    wordcode and code-object metadata therefore remain authoritative evidence.
    """
    warning = (
        "Diagnostic only: Once Human remaps opcode numbers. Operand metadata and raw opcode/argument bytes are retained, "
        "but stock Python operation names are not treated as authoritative semantics."
    )
    try:
        instructions = list(dis.get_instructions(code_obj, show_caches=True))
        error = None
    except Exception as exc:
        instructions, padded_error = _padded_disassembly(code_obj)
        error = f"{type(exc).__name__}: {exc}"
        if padded_error:
            error += f"; padded disassembly: {padded_error}"
    serialised = _serialise_instructions(instructions or [], 5000)
    windows = []
    for index, row in enumerate(serialised):
        argval = str(row.get("argval") or "")
        if argval not in TARGET_SYMBOLS:
            continue
        windows.append({
            "target": argval,
            "instruction_index": index,
            "instructions": serialised[max(0, index - 48): min(len(serialised), index + 49)],
        })
    return {
        "warning": warning,
        "error": error,
        "instructions": serialised,
        "target_windows": windows,
    }


def _code_row(qualname: str, code_obj: types.CodeType, *, pyc: dict[str, Any]) -> dict[str, Any]:
    names = list(map(str, code_obj.co_names))
    varnames = list(map(str, code_obj.co_varnames))
    constants = _safe_strings(code_obj.co_consts)
    hits = sorted(TARGET_SYMBOLS & (set(names) | set(constants) | {code_obj.co_name}))
    relevant_names = sorted({name for name in names if RELEVANT_NAME.search(name)})
    relevant_constants = sorted({value for value in constants if RELEVANT_NAME.search(value)})
    direct_calls = sorted(TARGET_FUNCTIONS & set(names))
    diagnostics = _diagnostic_disassembly(code_obj)
    relationship = {
        "contains_prototype_desc": "prototype_desc" in constants or "prototype_desc" in names,
        "calls_get_item_desc_text": "get_item_desc_text" in names,
        "calls_get_weapon_prototype_data": "get_weapon_prototype_data" in names,
        "calls_get_weapon_prototype_data_val_by_key": "get_weapon_prototype_data_val_by_key" in names,
    }
    relationship["prototype_desc_and_desc_helper_cooccur"] = bool(
        relationship["contains_prototype_desc"] and relationship["calls_get_item_desc_text"]
    )
    return {
        "pyc": pyc["relative_path"],
        "layer": pyc["layer"],
        "qualname": qualname,
        "function": code_obj.co_name,
        "firstlineno": code_obj.co_firstlineno,
        "target_hits": hits,
        "direct_target_function_dependencies": direct_calls,
        "relevant_co_names": relevant_names,
        "relevant_string_constants": relevant_constants,
        "relationship_signals": relationship,
        "co_name_positions": {name: index for index, name in enumerate(names) if name in TARGET_SYMBOLS or RELEVANT_NAME.search(name)},
        "string_constant_positions": {
            value: index for index, value in enumerate(code_obj.co_consts)
            if isinstance(value, str) and (value in TARGET_SYMBOLS or RELEVANT_NAME.search(value))
        },
        "code_capsule": _code_capsule(code_obj),
        "raw_wordcode": _raw_wordcode(code_obj, limit=16384),
        "diagnostic_disassembly": diagnostics,
    }


def _load_pyc_code(path: Path) -> tuple[types.CodeType | None, str | None]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if len(raw) < 17:
        return None, "PYC file is too small"
    try:
        code = marshal.loads(raw[16:])
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(code, types.CodeType):
        return None, "marshal payload was not a CodeType"
    return code, None


def _select_rows(all_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep target functions, target-symbol consumers, and their bounded local dependencies."""
    by_function: dict[str, list[int]] = {}
    for index, row in enumerate(all_rows):
        by_function.setdefault(str(row.get("function") or ""), []).append(index)

    selected: set[int] = set()
    queue: deque[tuple[int, int]] = deque()
    for index, row in enumerate(all_rows):
        if row.get("function") in TARGET_FUNCTIONS or row.get("target_hits"):
            selected.add(index)
            queue.append((index, 0))

    while queue:
        index, depth = queue.popleft()
        if depth >= 2:
            continue
        row = all_rows[index]
        names = set((row.get("code_capsule") or {}).get("co_names") or [])
        for name in names:
            for dependent_index in by_function.get(str(name), []):
                if dependent_index in selected:
                    continue
                selected.add(dependent_index)
                queue.append((dependent_index, depth + 1))

    return [all_rows[index] for index in sorted(selected)]


def run_description_dataflow_trace(
    base: Path,
    current: Path,
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    pycs = _find_target_pycs(base, current, activity=activity)
    activity(f"Description Data Flow: found {len(pycs)} exact target PYC files")

    all_rows: list[dict[str, Any]] = []
    pyc_status = []
    for pyc in pycs:
        path = pyc["path"]
        activity(f"Description Data Flow: statically reading {pyc['relative_path']}")
        code, error = _load_pyc_code(path)
        status = {
            "layer": pyc["layer"],
            "relative_path": pyc["relative_path"],
            "marshal_compatible": code is not None,
            "error": error,
        }
        pyc_status.append(status)
        if code is None:
            continue
        for qualname, code_obj in _walk_code_objects(code):
            all_rows.append(_code_row(qualname, code_obj, pyc=pyc))

    selected = _select_rows(all_rows)
    function_counts = Counter(str(row.get("function") or "") for row in selected)
    target_presence = {
        target: sum(
            1 for row in selected
            if target == row.get("function") or target in (row.get("target_hits") or [])
        )
        for target in sorted(TARGET_SYMBOLS | TARGET_FUNCTIONS)
    }
    cooccurrence = [
        {
            "pyc": row["pyc"],
            "qualname": row["qualname"],
            "function": row["function"],
            "signals": row["relationship_signals"],
        }
        for row in selected
        if (row.get("relationship_signals") or {}).get("prototype_desc_and_desc_helper_cooccur")
    ]

    source_roots = [
        {"layer": layer, "path": str(root)}
        for layer, root in _candidate_roots(base, current)
    ]
    report = {
        "schema": "dead-signal-weapon-description-static-dataflow",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Weapon Description",
        "mode": "offline-static-pyc-only",
        "record_counts": {
            "source_roots": len(source_roots),
            "target_pyc_files": len(pycs),
            "marshal_compatible_pycs": sum(bool(row["marshal_compatible"]) for row in pyc_status),
            "all_code_objects": len(all_rows),
            "selected_code_objects": len(selected),
            "prototype_desc_get_item_desc_text_cooccurrences": len(cooccurrence),
            "functions": dict(sorted(function_counts.items())),
        },
        "source_roots": source_roots,
        "pyc_status": pyc_status,
        "target_presence": target_presence,
        "cooccurrence_signals": cooccurrence,
        "code_objects": selected,
        "interpretation": {
            "goal": (
                "Recover the static producer neighborhood around prototype_desc and get_item_desc_text after proving that "
                "prototype_desc is not an exact field in weapon_prototype_data."
            ),
            "next_step": (
                "Use the captured code capsules/raw wordcode to reconstruct the exact producer assignment and helper arguments. "
                "No live process tracing is required."
            ),
        },
        "safety": {
            "game_process": "Never opened, attached to, debugged, injected, hooked, or read from process memory.",
            "anti_cheat": "No anti-cheat interaction or bypass behavior is performed.",
            "bytecode_execution": "Game bytecode is never executed; marshal is used only to deserialize static CodeType metadata.",
            "filesystem": "Reads only already-extracted PYC files referenced by the completed Miner snapshot; no game files are modified.",
            "network": "No network access is performed by this analyzer.",
        },
        "evidence_policy": {
            "raw_wordcode": "Authoritative static bytes/operands are preserved.",
            "stock_disassembly": "Diagnostic only because the Once Human client remaps opcode numbers.",
            "publication": "This report is research-only and cannot publish Weapon descriptions.",
        },
    }
    report_path = reports_dir / "weapon-description-static-dataflow.json"
    _write_json(report_path, report)
    activity(
        "Description Data Flow complete: "
        f"{len(selected)} selected code objects; {len(cooccurrence)} prototype_desc/get_item_desc_text co-occurrences"
    )
    return report
