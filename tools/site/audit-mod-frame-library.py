#!/usr/bin/env python3
"""Audit direct Mod 2.0 frame-library and sub-entry-family relationships.

This tool proves only relationships visible in installed-game evidence:
- normalized Mods expose ``frame_code`` from the current Mod property data;
- ``new_mod_frame_lib_data`` is keyed by frame code;
- each used frame record preserves four ordered ``sub_entry_item_no`` values;
- every used sub-entry ID is an exact ``mod_entry_data`` entry family;
- regular entry levels 1-5 preserve one stable attribute-code or buff identity.

It deliberately does NOT claim that sub-entry list position maps to frame_lv_1..4.
That positional consumer relationship needs separate runtime evidence. It also
makes no claim about numeric magnitude semantics beyond the entry identities.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

FRAME_TABLE = "game_common/data/new_mod_frame_lib_data.json"
ENTRY_TABLE = "game_common/data/mod_entry_data.json"
REGULAR_ENTRY_LEVELS = {1, 2, 3, 4, 5}
ENTRY_RECORD = re.compile(r"^\((\d+),\s*(\d+)\)$")


def load_mods(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("mods") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ValueError("Expected normalized mods.json with a mods array")
    return [row for row in rows if isinstance(row, dict)]


def frame_library(db: Path) -> dict[int, list[int]]:
    connection = sqlite3.connect(db)
    try:
        rows = connection.execute(
            """
            SELECT record_id, json_pointer, value
            FROM occurrences
            WHERE table_name = ? AND field = 'sub_entry_item_no'
            ORDER BY CAST(record_id AS INTEGER), json_pointer
            """,
            (FRAME_TABLE,),
        ).fetchall()
    finally:
        connection.close()

    grouped: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for record_id, pointer, value in rows:
        try:
            index = int(str(pointer).rsplit("/", 1)[-1])
            grouped[int(record_id)].append((index, int(value)))
        except (TypeError, ValueError):
            continue
    return {record_id: [value for _, value in sorted(values)] for record_id, values in grouped.items()}


def mod_entry_library(db: Path) -> dict[int, dict[int, dict[str, set]]]:
    connection = sqlite3.connect(db)
    try:
        rows = connection.execute(
            """
            SELECT record_id, field, value
            FROM occurrences
            WHERE table_name = ? AND field IN ('attr_no_list', 'buff_id')
            """,
            (ENTRY_TABLE,),
        ).fetchall()
    finally:
        connection.close()

    entries: dict[int, dict[int, dict[str, set]]] = defaultdict(
        lambda: defaultdict(lambda: {"attribute_codes": set(), "buff_ids": set()})
    )
    for record_id, field, value in rows:
        match = ENTRY_RECORD.match(str(record_id))
        if not match:
            continue
        entry_id, level = (int(part) for part in match.groups())
        if field == "attr_no_list":
            text = str(value or "").strip()
            if text:
                entries[entry_id][level]["attribute_codes"].add(text)
        elif field == "buff_id":
            try:
                buff_id = int(value)
            except (TypeError, ValueError):
                continue
            if buff_id:
                entries[entry_id][level]["buff_ids"].add(buff_id)
    return entries


def _entry_signature(level: dict[str, set]) -> tuple[tuple[str, ...], tuple[int, ...]]:
    return (
        tuple(sorted(level.get("attribute_codes") or set())),
        tuple(sorted(level.get("buff_ids") or set())),
    )


def audit(mods_path: Path, tracer_path: Path) -> dict:
    mods = load_mods(mods_path)
    library = frame_library(tracer_path)
    entries = mod_entry_library(tracer_path)
    frame_counts = Counter(int(row.get("frame_code") or 0) for row in mods)
    used = sorted(frame_counts)
    missing = [code for code in used if code not in library]
    malformed = {code: library.get(code, []) for code in used if code in library and len(library[code]) != 4}

    used_sub_entries = sorted({entry_id for code in used for entry_id in library.get(code, [])})
    missing_entry_families = [entry_id for entry_id in used_sub_entries if entry_id not in entries]
    incomplete_regular_levels: dict[str, list[int]] = {}
    ambiguous_regular_identity: dict[str, list[int]] = {}
    changing_regular_identity: dict[str, list[dict]] = {}
    resolved_entry_families: dict[str, dict] = {}

    for entry_id in used_sub_entries:
        levels = entries.get(entry_id, {})
        available = set(levels)
        if not REGULAR_ENTRY_LEVELS.issubset(available):
            incomplete_regular_levels[str(entry_id)] = sorted(available)
            continue

        signatures = []
        ambiguous_levels = []
        for level in sorted(REGULAR_ENTRY_LEVELS):
            signature = _entry_signature(levels[level])
            signatures.append(signature)
            has_attributes = bool(signature[0])
            has_buffs = bool(signature[1])
            if has_attributes == has_buffs:
                ambiguous_levels.append(level)
        if ambiguous_levels:
            ambiguous_regular_identity[str(entry_id)] = ambiguous_levels
            continue

        if len(set(signatures)) != 1:
            changing_regular_identity[str(entry_id)] = [
                {
                    "level": level,
                    "attribute_codes": list(_entry_signature(levels[level])[0]),
                    "buff_ids": list(_entry_signature(levels[level])[1]),
                }
                for level in sorted(REGULAR_ENTRY_LEVELS)
            ]
            continue

        attributes, buffs = signatures[0]
        resolved_entry_families[str(entry_id)] = {
            "source_kind": "attribute" if attributes else "buff",
            "attribute_codes": list(attributes),
            "buff_ids": list(buffs),
            "regular_levels": sorted(REGULAR_ENTRY_LEVELS),
            "available_levels": sorted(available),
        }

    problems = bool(
        missing
        or malformed
        or missing_entry_families
        or incomplete_regular_levels
        or ambiguous_regular_identity
        or changing_regular_identity
    )
    return {
        "schema": "dead-signal-mod-frame-library-audit",
        "schema_version": 2,
        "source_tables": [FRAME_TABLE, ENTRY_TABLE],
        "normalized_mod_records": len(mods),
        "used_frame_codes": len(used),
        "frame_library_records": len(library),
        "used_sub_entry_families": len(used_sub_entries),
        "resolved_used_sub_entry_families": len(resolved_entry_families),
        "missing_used_frame_codes": missing,
        "used_frames_without_exactly_four_sub_entries": malformed,
        "missing_mod_entry_families": missing_entry_families,
        "sub_entry_families_missing_regular_levels_1_5": incomplete_regular_levels,
        "sub_entry_families_with_ambiguous_regular_identity": ambiguous_regular_identity,
        "sub_entry_families_with_changing_regular_identity": changing_regular_identity,
        "used_frame_code_counts": {str(code): frame_counts[code] for code in used},
        "used_frame_sub_entries": {str(code): library.get(code, []) for code in used},
        "resolved_sub_entry_families": resolved_entry_families,
        "proven_relationship": (
            "normalized Mod frame_code selects a new_mod_frame_lib_data record with four ordered sub_entry_item_no IDs; "
            "every used ID resolves exactly to a mod_entry_data family whose regular Levels 1-5 preserve one stable attribute-code or buff identity"
        ),
        "unproven_relationship": (
            "no current evidence proves sub_entry_item_no list index 0..3 corresponds to frame_lv_1..4 respectively, "
            "and this audit does not infer numeric magnitude semantics from entry identity alone"
        ),
        "status": "pass" if not problems else "review",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Mod 2.0 frame-library and sub-entry-family evidence")
    parser.add_argument("mods", type=Path, help="normalized data/mods.json")
    parser.add_argument("tracer", type=Path, help="indexes/reference-tracer.sqlite")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.mods, args.tracer)
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
