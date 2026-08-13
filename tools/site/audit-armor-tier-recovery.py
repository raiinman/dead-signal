#!/usr/bin/env python3
"""Prove which missing Armor Tier stat rows are safe to recover.

Stat-row identity and crafting-output identity are audited independently. A malformed
Tier row may still be recoverable from the exact blueprint+suit variant series even
when the generic crafting/map output points at another suit variant.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

EXPECTED_TIERS = {1, 2, 3, 4, 5}
EQUIP_TABLE = "game_common/data/equip_data.json"
ORIGIN_TABLE = "game_common/data/equip_origin_data.json"
BLUEPRINT_MAP_TABLE = "game_common/data/blueprint_art_to_equip_map.json"


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


def field_values(connection: sqlite3.Connection, table_name: str, record_id: str, field: str, layer: str | None = None) -> set[str]:
    sql = "SELECT value FROM occurrences WHERE table_name=? AND record_id=? AND field=?"
    args: list[str] = [table_name, record_id, field]
    if layer:
        sql += " AND layer=?"
        args.append(layer)
    return {str(row[0]) for row in connection.execute(sql, args)}


def record_exists(connection: sqlite3.Connection, table_name: str, record_id: str, layer: str | None = None) -> bool:
    sql = "SELECT 1 FROM occurrences WHERE table_name=? AND record_id=? AND field='record_id'"
    args: list[str] = [table_name, record_id]
    if layer:
        sql += " AND layer=?"
        args.append(layer)
    sql += " LIMIT 1"
    return connection.execute(sql, args).fetchone() is not None


def records_with_field_value(connection: sqlite3.Connection, table_name: str, field: str, value: str, layer: str = "current") -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT record_id FROM occurrences WHERE table_name=? AND layer=? AND field=? AND value=?",
            (table_name, layer, field, str(value)),
        )
    }


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


def item_suffix_matches_tier(item_id: str, gear_tier: int) -> bool:
    return item_id.isdigit() and len(item_id) >= 2 and int(item_id[-2:]) == gear_tier


def audit(payload: dict[str, Any], connection: sqlite3.Connection) -> dict[str, Any]:
    results = []
    for record_type, expected_suit_id, piece in iter_pieces(payload):
        tier_rows = [row for row in piece.get("tiers") or [] if isinstance(row, dict)]
        stat_tiers = {tier_number(row) for row in tier_rows}
        stat_tiers.discard(None)
        recipes = {
            tier_number(row): row
            for row in piece.get("crafting_recipes") or []
            if isinstance(row, dict) and tier_number(row) is not None
        }
        sibling_suffix_invariant = all(
            tier_number(row) in EXPECTED_TIERS
            and item_suffix_matches_tier(str(row.get("item_id") or ""), int(tier_number(row)))
            for row in tier_rows
        )

        blueprint_id = int(piece.get("blueprint_id") or 0)
        blueprint_records = records_with_field_value(connection, EQUIP_TABLE, "blueprint_no", str(blueprint_id))
        suit_records = records_with_field_value(connection, EQUIP_TABLE, "suit_id", str(expected_suit_id))
        exact_variant_records = blueprint_records & suit_records

        for gear_tier in sorted(EXPECTED_TIERS - stat_tiers):
            recipe = recipes.get(gear_tier) or {}
            output_item_id = int(recipe.get("output_item_id") or 0)
            map_record_id = f"({blueprint_id}, {gear_tier})"
            mapped_items = field_values(connection, BLUEPRINT_MAP_TABLE, map_record_id, "item_no", "base")

            variant_candidates = sorted(
                item_id
                for item_id in exact_variant_records
                if item_suffix_matches_tier(item_id, gear_tier)
                and record_exists(connection, ORIGIN_TABLE, item_id, "current")
            )
            exact_variant_item_id = variant_candidates[0] if len(variant_candidates) == 1 else ""
            variant_blueprints = field_values(connection, EQUIP_TABLE, exact_variant_item_id, "blueprint_no", "current") if exact_variant_item_id else set()
            variant_suits = field_values(connection, EQUIP_TABLE, exact_variant_item_id, "suit_id", "current") if exact_variant_item_id else set()

            recipe_blueprints = field_values(connection, EQUIP_TABLE, str(output_item_id), "blueprint_no", "current") if output_item_id else set()
            recipe_suits = field_values(connection, EQUIP_TABLE, str(output_item_id), "suit_id", "current") if output_item_id else set()

            stat_checks = {
                "sibling_tier_suffix_invariant": sibling_suffix_invariant,
                "unique_blueprint_suit_tier_candidate": len(variant_candidates) == 1,
                "candidate_blueprint_matches": str(blueprint_id) in variant_blueprints,
                "candidate_suit_matches_variant": str(expected_suit_id) in variant_suits,
                "candidate_origin_stat_record_exists": bool(exact_variant_item_id),
            }
            crafting_checks = {
                "recipe_has_output": output_item_id > 0,
                "blueprint_art_map_matches_recipe": str(output_item_id) in mapped_items,
                "recipe_output_blueprint_matches": str(blueprint_id) in recipe_blueprints,
                "recipe_output_suit_matches_variant": str(expected_suit_id) in recipe_suits,
                "recipe_output_is_stat_candidate": str(output_item_id) == exact_variant_item_id if output_item_id and exact_variant_item_id else False,
            }

            if all(stat_checks.values()):
                classification = "recoverable-exact-variant-series-evidence"
                reason = "The current equip table contains exactly one same-blueprint, same-suit Tier candidate matching the proven sibling suffix pattern, with an exact origin stat record."
            else:
                classification = "blocked-incomplete-or-ambiguous-stat-evidence"
                reason = "The exact blueprint+suit Tier series does not resolve one unique origin-backed stat row."

            crafting_classification = (
                "crafting-output-exact-variant"
                if all(crafting_checks.values())
                else "crafting-output-variant-or-evidence-conflict"
            )

            results.append(
                {
                    "record_type": record_type,
                    "canonical_id": piece.get("canonical_id"),
                    "name": piece.get("name"),
                    "slot": piece.get("slot"),
                    "blueprint_id": blueprint_id,
                    "expected_suit_id": expected_suit_id,
                    "gear_tier": gear_tier,
                    "stat_recovery_item_id": int(exact_variant_item_id) if exact_variant_item_id else None,
                    "variant_candidates": [int(value) for value in variant_candidates],
                    "stat_checks": stat_checks,
                    "classification": classification,
                    "recipe_output_item_id": output_item_id or None,
                    "mapped_item_ids": sorted(int(value) for value in mapped_items if value.isdigit()),
                    "recipe_output_suit_values": sorted(recipe_suits),
                    "crafting_checks": crafting_checks,
                    "crafting_classification": crafting_classification,
                    "reason": reason,
                }
            )

    counts: dict[str, int] = {}
    crafting_counts: dict[str, int] = {}
    for row in results:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
        key = row["crafting_classification"]
        crafting_counts[key] = crafting_counts.get(key, 0) + 1
    return {
        "schema": "dead-signal-armor-tier-recovery-audit",
        "schema_version": 2,
        "policy": {
            "stat_recovery": "Recover a missing Armor Tier stat row only from one exact current blueprint+suit candidate whose item suffix follows the already-proven sibling Tier pattern and whose equip_origin_data record exists.",
            "crafting": "Crafting-output identity is a separate evidence layer. A generic recipe/map output must never replace a different player-facing suit variant.",
            "synthesis": "Never interpolate or invent Armor Tier stats.",
        },
        "counts": {
            "gaps_checked": len(results),
            **counts,
            **crafting_counts,
        },
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit exact recovery evidence for Armor Tier stat gaps")
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
