#!/usr/bin/env python3
"""Audit weapon fixed-skill references against the Miner's reference tracer.

This tool only proves exact record identity. If a Blueprint references WS1301 but
passive_skill_data has no record_id WS1301, the result is a dangling reference.
It never aliases that code to a similar-looking record such as WS13101.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

PASSIVE_SKILL_TABLE = "game_common/data/passive_skill_data.json"


def load_weapons(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("weapons"), list):
        raise ValueError("Expected normalized weapons.json with a weapons array")
    return payload


def fixed_skill_codes(weapon: dict[str, Any]) -> set[str]:
    result = set()
    progression = weapon.get("blueprint_attribute_progression") or {}
    for row in progression.get("levels") or []:
        if not isinstance(row, dict):
            continue
        code = str(row.get("fixed_skill_code") or "").strip()
        if code:
            result.add(code)
    return result


def passive_skill_ids(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT DISTINCT record_id FROM occurrences WHERE table_name = ?",
        (PASSIVE_SKILL_TABLE,),
    )
    return {str(row[0]) for row in rows}


def audit(weapons_payload: dict[str, Any], connection: sqlite3.Connection) -> dict[str, Any]:
    known = passive_skill_ids(connection)
    referenced = set()
    dangling = []
    for weapon in weapons_payload.get("weapons") or []:
        if not isinstance(weapon, dict):
            continue
        codes = fixed_skill_codes(weapon)
        referenced.update(codes)
        missing = sorted(code for code in codes if code not in known)
        if missing:
            dangling.append({
                "blueprint_id": weapon.get("blueprint_id"),
                "name": weapon.get("name"),
                "rarity": weapon.get("quality"),
                "fixed_skill_codes": missing,
                "classification": "dangling-exact-passive-skill-reference",
                "reason": "The exact referenced skill code has no record_id in passive_skill_data; no alias is inferred.",
            })
    dangling_codes = sorted({code for row in dangling for code in row["fixed_skill_codes"]})
    return {
        "schema": "dead-signal-weapon-skill-reference-audit",
        "schema_version": 1,
        "policy": "Exact record identity only; similar-looking skill IDs are never treated as aliases without direct mined evidence.",
        "counts": {
            "referenced_fixed_skill_codes": len(referenced),
            "passive_skill_record_ids": len(known),
            "dangling_fixed_skill_codes": len(dangling_codes),
            "weapons_with_dangling_fixed_skill_references": len(dangling),
        },
        "dangling_fixed_skill_codes": dangling_codes,
        "queue": dangling,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit weapon fixed-skill references against reference-tracer.sqlite")
    parser.add_argument("weapons", type=Path, help="Normalized data/weapons.json")
    parser.add_argument("reference_tracer", type=Path, help="indexes/reference-tracer.sqlite")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    with sqlite3.connect(args.reference_tracer.expanduser().resolve()) as connection:
        report = audit(load_weapons(args.weapons.expanduser().resolve()), connection)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
