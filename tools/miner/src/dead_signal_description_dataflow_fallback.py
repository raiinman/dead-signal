"""Bounded fallback for recovering description code capsules from an existing PYC report.

The persisted weapon-progression PYC report can be hundreds of megabytes. This
module never loads it wholesale. It searches for exact target ``co_name`` tokens,
then decodes only the nearby ``code_capsule`` JSON object written by the static
PYC analyzer. No game bytecode is executed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

TARGET_FUNCTIONS = (
    "get_weapon_item_data",
    "get_item_desc_text",
    "get_weapon_prototype_data",
    "get_weapon_prototype_data_val_by_key",
)
REPORT_NAME = "weapon-progression-pyc-consumers.json"
CHUNK = 1024 * 1024
OVERLAP = 4096
MAX_CAPSULE_BYTES = 8 * 1024 * 1024
ActivityCallback = Callable[[str], None]


def _find_offsets(path: Path, needle: bytes, limit: int = 12) -> list[int]:
    offsets: list[int] = []
    carry = b""
    absolute = 0
    with path.open("rb") as source:
        while len(offsets) < limit:
            block = source.read(CHUNK)
            if not block:
                break
            data = carry + block
            data_start = absolute - len(carry)
            start = 0
            while len(offsets) < limit:
                found = data.find(needle, start)
                if found < 0:
                    break
                offsets.append(data_start + found)
                start = found + len(needle)
            absolute += len(block)
            carry = data[-OVERLAP:]
    return sorted(set(offsets))


def _decode_capsule_near(path: Path, token_offset: int, function: str) -> dict[str, Any] | None:
    back = 128 * 1024
    start = max(0, token_offset - back)
    with path.open("rb") as source:
        source.seek(start)
        prefix = source.read(token_offset - start + 4096)
    relative = token_offset - start
    key = b'"code_capsule"'
    key_pos = prefix.rfind(key, 0, relative + 1)
    if key_pos < 0:
        return None
    brace = prefix.find(b"{", key_pos + len(key))
    if brace < 0:
        return None
    absolute_brace = start + brace

    with path.open("rb") as source:
        source.seek(absolute_brace)
        raw = source.read(MAX_CAPSULE_BYTES)
    text = raw.decode("utf-8", errors="replace")
    try:
        capsule, _end = json.JSONDecoder().raw_decode(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(capsule, dict) or str(capsule.get("co_name") or "") != function:
        return None
    return capsule


def _raw_wordcode_from_hex(hex_text: str, limit: int = 16384) -> list[dict[str, Any]]:
    try:
        raw = bytes.fromhex(hex_text)
    except ValueError:
        return []
    rows = []
    for offset in range(0, min(len(raw), limit), 2):
        rows.append({
            "offset": offset,
            "opcode": raw[offset],
            "oparg_byte": raw[offset + 1] if offset + 1 < len(raw) else None,
        })
    return rows


def recover_persisted_description_capsules(
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    report_path = reports_dir / REPORT_NAME
    result = {
        "source": str(report_path),
        "report_present": report_path.is_file(),
        "mode": "bounded-persisted-code-capsule-recovery",
        "functions": [],
        "missing_functions": [],
        "policy": (
            "Exact co_name search plus bounded code_capsule JSON recovery only; the giant report is never loaded wholesale "
            "and game bytecode is never executed."
        ),
    }
    if not report_path.is_file():
        result["missing_functions"] = list(TARGET_FUNCTIONS)
        return result

    activity(f"Description Data Flow fallback: scanning {REPORT_NAME} for exact target code capsules")
    for function in TARGET_FUNCTIONS:
        needles = [
            f'"co_name": "{function}"'.encode("utf-8"),
            f'"co_name":"{function}"'.encode("utf-8"),
        ]
        offsets: list[int] = []
        for needle in needles:
            offsets.extend(_find_offsets(report_path, needle))
        capsule = None
        matched_offset = None
        for offset in sorted(set(offsets)):
            capsule = _decode_capsule_near(report_path, offset, function)
            if capsule is not None:
                matched_offset = offset
                break
        if capsule is None:
            result["missing_functions"].append(function)
            continue
        names = list(map(str, capsule.get("co_names") or []))
        consts = [value for value in capsule.get("co_consts") or [] if isinstance(value, str)]
        result["functions"].append({
            "function": function,
            "qualname": capsule.get("co_qualname"),
            "filename": capsule.get("co_filename"),
            "report_byte_offset": matched_offset,
            "co_names": names,
            "string_constants": consts,
            "relationship_signals": {
                "contains_prototype_desc": "prototype_desc" in names or "prototype_desc" in consts,
                "calls_get_item_desc_text": "get_item_desc_text" in names,
                "calls_get_weapon_prototype_data": "get_weapon_prototype_data" in names,
                "calls_get_weapon_prototype_data_val_by_key": "get_weapon_prototype_data_val_by_key" in names,
            },
            "code_capsule": capsule,
            "raw_wordcode": _raw_wordcode_from_hex(str(capsule.get("co_code_hex") or "")),
            "diagnostic_disassembly": {
                "warning": "Unavailable from persisted capsule alone; raw wordcode and code-object metadata remain preserved.",
                "instructions": [],
                "target_windows": [],
            },
            "source_mode": "persisted-code-capsule",
        })
        activity(f"Description Data Flow fallback: recovered {function}")

    result["record_counts"] = {
        "functions_recovered": len(result["functions"]),
        "functions_missing": len(result["missing_functions"]),
    }
    return result
