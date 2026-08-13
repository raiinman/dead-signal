#!/usr/bin/env python3
"""Classify Armor Tier gaps using stat-row and crafting evidence independently."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED_TIERS = {1, 2, 3, 4, 5}


def load_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != "dead-signal-armor":
        raise ValueError("Expected dead-signal-armor compact contract")
    return payload


def tier_number(row: dict[str, Any]) -> int | None:
    value = row.get("data_level") if row.get("data_level") is not None else row.get("tier")
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def pieces(payload: dict[str, Any]):
    for armor_set in payload.get("armor_sets") or []:
        if not isinstance(armor_set, dict):
            continue
        for piece in armor_set.get("pieces") or []:
            if isinstance(piece, dict):
                yield "set_piece", piece
    for piece in payload.get("key_armor") or []:
        if isinstance(piece, dict):
            yield "key_armor", piece


def audit(payload: dict[str, Any]) -> dict[str, Any]:
    missing_stat_rows = []
    missing_recipe_rows = []
    recipe_backed_stat_gaps = []
    for record_type, piece in pieces(payload):
        stat_tiers = {tier_number(row) for row in piece.get("tiers") or [] if isinstance(row, dict)}
        recipes = [row for row in piece.get("crafting_recipes") or [] if isinstance(row, dict)]
        recipe_by_tier = {tier_number(row): row for row in recipes if tier_number(row) is not None}
        stat_tiers.discard(None)
        missing_stats = sorted(EXPECTED_TIERS - stat_tiers)
        missing_recipes = sorted(EXPECTED_TIERS - set(recipe_by_tier))
        base = {
            "record_type": record_type,
            "canonical_id": piece.get("canonical_id"),
            "blueprint_id": piece.get("blueprint_id"),
            "name": piece.get("name"),
            "slot": piece.get("slot"),
        }
        if missing_stats:
            missing_stat_rows.append({**base, "missing_gear_tiers": missing_stats})
        if missing_recipes:
            missing_recipe_rows.append({
                **base,
                "missing_gear_tiers": missing_recipes,
                "classification": "unresolved-recipe-evidence",
                "reason": "Missing recipe evidence does not prove this Armor item is non-craftable",
            })
        backed = []
        for tier in missing_stats:
            recipe = recipe_by_tier.get(tier)
            if recipe:
                backed.append({
                    "gear_tier": tier,
                    "forge_no": recipe.get("forge_no"),
                    "output_item_id": recipe.get("output_item_id"),
                    "recipe_server_no": recipe.get("recipe_server_no"),
                })
        if backed:
            recipe_backed_stat_gaps.append({
                **base,
                "classification": "crafting-output-present-stat-row-missing",
                "tiers": backed,
                "reason": "Crafting evidence proves the Tier output identity exists, but no canonical Armor stat row was recovered; do not synthesize stats.",
            })
    return {
        "schema": "dead-signal-armor-tier-evidence-audit",
        "schema_version": 1,
        "policy": {
            "stat_rows": "Player-facing Armor requires canonical Gear Tier I-V stat evidence.",
            "recipes": "Recipe presence and stat-row presence are independent evidence layers.",
            "non_craftable": "Missing recipe evidence is never auto-classified as non-craftable.",
            "missing_stats": "Recipe-backed Tier gaps remain blocked until their stat rows are recovered; values are never interpolated or invented.",
        },
        "counts": {
            "records_with_missing_stat_rows": len(missing_stat_rows),
            "records_with_missing_recipe_rows": len(missing_recipe_rows),
            "records_with_recipe_backed_stat_gaps": len(recipe_backed_stat_gaps),
        },
        "queues": {
            "missing_stat_rows": missing_stat_rows,
            "missing_recipe_rows": missing_recipe_rows,
            "recipe_backed_stat_gaps": recipe_backed_stat_gaps,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit independent Armor stat-row and recipe Tier evidence")
    parser.add_argument("source", type=Path, help="Compact published/web/armor.json")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    report = audit(load_contract(args.source.expanduser().resolve()))
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
