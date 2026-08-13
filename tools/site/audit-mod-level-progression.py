#!/usr/bin/env python3
"""Inspect Mod-level progression evidence without inferring relationships.

The Miner emits normalized ``data/progression.json`` rows from
``new_mod_level_data.json``. This audit compares the ``mod_level`` rows with
compact Mod codes and main-entry codes only as overlap evidence. Matching
numbers are research leads, never proof that fields are related.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


def text(value: Any) -> str:
    return str(value or "").strip()


def numeric_tokens(value: Any) -> set[str]:
    if isinstance(value, bool) or value is None:
        return set()
    if isinstance(value, dict):
        result: set[str] = set()
        for child in value.values():
            result.update(numeric_tokens(child))
        return result
    if isinstance(value, list):
        result: set[str] = set()
        for child in value:
            result.update(numeric_tokens(child))
        return result
    return set(re.findall(r"-?\d+", text(value)))


def resolve_sources(root: Path) -> tuple[Path, Path]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Expected Miner published directory: {root}")
    mods = next((p for p in (root / "web" / "mods.json", root / "mods.json") if p.is_file()), None)
    progression = next((p for p in (root / "data" / "progression.json", root / "progression.json") if p.is_file()), None)
    if mods is None:
        raise FileNotFoundError(f"Could not find compact mods.json under {root}")
    if progression is None:
        raise FileNotFoundError(f"Could not find normalized progression.json under {root}")
    return mods, progression


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def compact_code_sets(payload: dict[str, Any]) -> tuple[set[str], set[str]]:
    if payload.get("schema") != "dead-signal-mods":
        raise ValueError("Expected compact dead-signal-mods contract")
    mod_codes: set[str] = set()
    main_entry_codes: set[str] = set()
    for family in payload.get("families") or []:
        if not isinstance(family, dict):
            continue
        for variant in family.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            if variant.get("mod_code") not in (None, ""):
                mod_codes.add(str(variant.get("mod_code")))
            if variant.get("main_entry_code") not in (None, ""):
                main_entry_codes.add(str(variant.get("main_entry_code")))
    return mod_codes, main_entry_codes


def audit(mods_payload: dict[str, Any], progression_payload: dict[str, Any]) -> dict[str, Any]:
    mod_codes, main_entry_codes = compact_code_sets(mods_payload)
    progression = [row for row in progression_payload.get("progression") or [] if isinstance(row, dict)]
    rows = [row for row in progression if text(row.get("track")) == "mod_level"]

    levels: Counter[int] = Counter()
    invalid_levels = []
    overlaps = []
    top_keys: Counter[str] = Counter()
    definition_keys: Counter[str] = Counter()
    rows_with_mod_overlap = 0
    rows_with_entry_overlap = 0

    for row in rows:
        top_keys.update(row.keys())
        definition = row.get("game_definition")
        if isinstance(definition, dict):
            definition_keys.update(definition.keys())

        level = row.get("level")
        if isinstance(level, int) and not isinstance(level, bool):
            levels[level] += 1
        else:
            invalid_levels.append({"id": row.get("id"), "level_key": row.get("level_key"), "level": level})

        tokens = numeric_tokens(row.get("level_key")) | numeric_tokens(definition)
        mod_hits = sorted(tokens & mod_codes, key=lambda value: int(value))
        entry_hits = sorted(tokens & main_entry_codes, key=lambda value: int(value))
        if mod_hits:
            rows_with_mod_overlap += 1
        if entry_hits:
            rows_with_entry_overlap += 1
        if mod_hits or entry_hits:
            overlaps.append({
                "id": row.get("id"),
                "level_key": row.get("level_key"),
                "level": level,
                "mod_code_token_hits": mod_hits,
                "main_entry_code_token_hits": entry_hits,
                "game_definition": definition,
            })

    duplicate_level_keys = sorted({
        text(row.get("level_key"))
        for row in rows
        if text(row.get("level_key"))
        and sum(text(other.get("level_key")) == text(row.get("level_key")) for other in rows) > 1
    })

    return {
        "schema": "dead-signal-mod-level-progression-audit",
        "schema_version": 1,
        "policy": "Numeric overlap is correlation evidence only; no field relationship is inferred.",
        "counts": {
            "mod_level_rows": len(rows),
            "distinct_levels": len(levels),
            "minimum_level": min(levels) if levels else None,
            "maximum_level": max(levels) if levels else None,
            "rows_with_mod_code_token_overlap": rows_with_mod_overlap,
            "rows_with_main_entry_code_token_overlap": rows_with_entry_overlap,
            "overlap_rows": len(overlaps),
        },
        "level_distribution": {str(level): count for level, count in sorted(levels.items())},
        "shape": {
            "top_level_key_frequency": dict(sorted(top_keys.items())),
            "game_definition_key_frequency": dict(sorted(definition_keys.items())),
        },
        "queues": {
            "invalid_levels": invalid_levels,
            "duplicate_level_keys": duplicate_level_keys,
            "numeric_overlap_research_leads": overlaps,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Mod 2.0 level progression correlation evidence")
    parser.add_argument("published", type=Path, help="Fresh Miner published/ directory")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON report path")
    args = parser.parse_args()
    mods_path, progression_path = resolve_sources(args.published)
    report = audit(load_json(mods_path), load_json(progression_path))
    encoded = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
