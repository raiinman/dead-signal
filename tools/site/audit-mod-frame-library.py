#!/usr/bin/env python3
"""Audit the direct Mod 2.0 frame-code -> frame-library relationship.

This tool proves only relationships visible in installed-game evidence:
- normalized Mods expose ``frame_code`` from new_mod_property_data.frame;
- new_mod_frame_lib_data is keyed by frame code;
- each used frame record preserves its ordered ``sub_entry_item_no`` values.

It deliberately does NOT claim that sub-entry list position maps to frame_lv_1..4.
That positional consumer relationship needs separate evidence.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

FRAME_TABLE = "game_common/data/new_mod_frame_lib_data.json"


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


def audit(mods_path: Path, tracer_path: Path) -> dict:
    mods = load_mods(mods_path)
    library = frame_library(tracer_path)
    frame_counts = Counter(int(row.get("frame_code") or 0) for row in mods)
    used = sorted(frame_counts)
    missing = [code for code in used if code not in library]
    malformed = {code: library.get(code, []) for code in used if code in library and len(library[code]) != 4}
    return {
        "schema": "dead-signal-mod-frame-library-audit",
        "schema_version": 1,
        "source_table": FRAME_TABLE,
        "normalized_mod_records": len(mods),
        "used_frame_codes": len(used),
        "frame_library_records": len(library),
        "missing_used_frame_codes": missing,
        "used_frames_without_exactly_four_sub_entries": malformed,
        "used_frame_code_counts": {str(code): frame_counts[code] for code in used},
        "used_frame_sub_entries": {str(code): library.get(code, []) for code in used},
        "proven_relationship": "normalized Mod frame_code selects a new_mod_frame_lib_data record whose ordered sub_entry_item_no list is preserved",
        "unproven_relationship": "no current evidence proves sub_entry_item_no list index 0..3 corresponds to frame_lv_1..4 respectively",
        "status": "pass" if not missing and not malformed else "review",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Mod 2.0 frame-library evidence")
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
