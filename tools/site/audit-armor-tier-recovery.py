#!/usr/bin/env python3
"""Prove which recipe-backed Armor Tier gaps are safe to recover.

This audit is intentionally stricter than name/blueprint matching. A missing Tier is
recoverable only when the crafting recipe output, blueprint-art map, equip blueprint,
set/key identity, and origin-stat record all agree. Variant conflicts stay blocked.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

EXPECTED_TIERS = {1, 2, 3, 4, 5}


def load_armor(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "dead-signal-armor":
        raise ValueError("Expected dead-signal-armor compact contract")
    return payload


def tier_number(row: dict[str, Any]) -> int | None:
    value = row.get("data_level") if row.get("data_level") is not None else row.get("tier")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def field_values(connection: sqlite3.Connection, table_name: str, record_id: str, field: str) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT value FROM occurrences WHERE table_name=? AND record_id=? AND field=?",
            (table_name, record_id, field),
        )
    }


def record_exists(connection: sqlite3.Connection, table_name: str, record_id: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM occurrences WHERE table_name=? AND record_id=? AND field='record_id' LIMIT 1",
        (table_name, record_id),
    ).fetchone()
    return row is not None


def iter_pieces(payload: dict[str, Any]):
    for armor_set in payload.get("armor_sets") or []:
        if not isinstance(armor_set, dict):
            continue
        for piece in armor_set.get("pieces") or []:
            if isinstance(piece, dict):
                yield "set_piece", int(armor_set.get("suit_id") or 0), piece
    for piece in payload.get("key_armor") or []:
        if isinstance(piece, dict):
            yield "key_armor", 0, piece


def audit(payload: dict[str, Any], connection: sqlite3.Connection) -> dict[str, Any]:
    results = []
    for record_type, expected_suit_id, piece in iter_pieces(payload):
        stat_tiers = {
            tier_number(row)
            for row in piece.get("tiers") or []
            if isinstance(row, dict)
        }
        stat_tiers.discard(None)
        recipes = {
            tier_number(row): row
            for row in piece.get("crafting_recipes") or []
            if isinstance(row, dict) and tier_number(row) is not None
        }
        for gear_tier in sorted(EXPECTED_TIERS - stat_tiers):
            recipe = recipes.get(gear_tier)
            if not recipe:
                continue
            blueprint_id = int(piece.get("blueprint_id") or 0)
            output_item_id = int(recipe.get("output_item_id") or 0)
            map_record_id = f"({blueprint_id}, {gear_tier})"
            mapped_items = field_values(
                connection,
                "game_common/data/blueprint_art_to_equip_map.json",
                map_record_id,
                "item_no",
            )
            blueprint_values = field_values(
                connection,
                "game_common/data/equip_data.json",
                str(output_item_id),
                "blueprint_no",
            )
            suit_values = field_values(
                connection,
                "game_common/data/equip_data.json",
                str(output_item_id),
                "suit_id",
            )
            origin_values = field_values(
                connection,
                "game_common/data/equip_data.json",
                str(output_item_id),
                "equip_origin_id",
            )
            origin_ids = origin_values or {str(output_item_id)}
            origin_exists = any(
                record_exists(
                    connection,
                    "game_common/data/equip_origin_data.json",
                    origin_id,
                )
                for origin_id in origin_ids
            )

            checks = {
                "recipe_has_output": output_item_id > 0,
                "blueprint_art_map_matches_recipe": str(output_item_id) in mapped_items,
                "equip_blueprint_matches": str(blueprint_id) in blueprint_values,
                "equip_suit_matches_variant": str(expected_suit_id) in suit_values,
                "origin_stat_record_exists": origin_exists,
            }
            if all(checks.values()):
                classification = "recoverable-exact-game-evidence"
                reason = "Recipe output, blueprint-art map, equip blueprint, suit/key identity, and origin stat record all agree."
            elif all(value for key, value in checks.items() if key != "equip_suit_matches_variant") and not checks["equip_suit_matches_variant"]:
                classification = "blocked-armor-variant-conflict"
                reason = "Blueprint/Tier and recipe evidence resolve an item from a different suit identity; do not substitute it into this player-facing variant."
            else:
                classification = "blocked-incomplete-or-conflicting-evidence"
                reason = "The independent game-data evidence layers do not all agree."

            results.append(
                {
                    "record_type": record_type,
                    "canonical_id": piece.get("canonical_id"),
                    "name": piece.get("name"),
                    "slot": piece.get("slot"),
                    "blueprint_id": blueprint_id,
                    "expected_suit_id": expected_suit_id,
                    "gear_tier": gear_tier,
                    "recipe_output_item_id": output_item_id,
                    "mapped_item_ids": sorted(mapped_items),
                    "equip_blueprint_values": sorted(blueprint_values),
                    "equip_suit_values": sorted(suit_values),
                    "equip_origin_ids": sorted(origin_ids),
                    "checks": checks,
                    "classification": classification,
                    "reason": reason,
                }
            )

    counts: dict[str, int] = {}
    for row in results:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    return {
        "schema": "dead-signal-armor-tier-recovery-audit",
        "schema_version": 1,
        "policy": {
            "recovery": "Recover only exact recipe-backed Tier rows whose blueprint-art map, equip blueprint, suit/key identity, and origin-stat evidence all agree.",
            "variants": "A blueprint match is insufficient when the resolved equip row belongs to another suit variant.",
            "synthesis": "Never interpolate or invent Armor Tier stats.",
        },
        "counts": {
            "recipe_backed_gaps_checked": len(results),
            **counts,
        },
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit exact recovery evidence for Armor Tier gaps")
    parser.add_argument("armor", type=Path, help="Compact published/web/armor.json")
    parser.add_argument("tracer", type=Path, help="indexes/reference-tracer.sqlite")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    connection = sqlite3.connect(args.tracer.expanduser().resolve())
    try:
        report = audit(load_armor(args.armor.expanduser().resolve()), connection)
    finally:
        connection.close()
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
