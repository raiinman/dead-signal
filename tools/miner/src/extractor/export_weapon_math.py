"""Export evidence-backed static weapon math for every normalized weapon.

This module deliberately stops at the static weapon-card boundary. Runtime
procs, enemy defenses, conditional buffs, mods, armor, cradles, deviations,
and consumables are not collapsed into speculative DPS.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def finite_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def intrinsic_attack(tier_base_attack: float, blueprint_star_multiplier: float) -> int:
    """Mirror the proven positive-Attack client conversion: int(base * ratio)."""
    return int(tier_base_attack * blueprint_star_multiplier)


def static_attack_float(intrinsic: float, ratio_additions=(), flat_additions=()) -> float:
    """Combine proven D0101/D0102 ratio inputs and D0100 flat inputs additively."""
    return intrinsic * (1.0 + sum(ratio_additions)) + sum(flat_additions)


def _star_rows(weapon: dict) -> list[dict]:
    progression = weapon.get("blueprint_attribute_progression") or {}
    return progression.get("levels") or []


def _tier_rows(weapon: dict) -> list[dict]:
    return weapon.get("tiers") or []


def build_weapon_math(weapons_payload: dict) -> dict:
    records = []
    invalid = []
    total_combinations = 0

    for weapon in weapons_payload.get("weapons", []):
        tiers = _tier_rows(weapon)
        stars = _star_rows(weapon)
        matrix = []
        for tier in tiers:
            base = finite_number(tier.get("damage"))
            tier_no = tier.get("tier")
            if base is None:
                continue
            star_values = []
            for star in stars:
                multiplier = finite_number(star.get("preset_attack_ratio"))
                star_no = star.get("strength_lv") or star.get("level")
                if multiplier is None or multiplier <= 0:
                    continue
                raw = base * multiplier
                star_values.append(
                    {
                        "blueprint_stars": star_no,
                        "preset_attack_ratio": multiplier,
                        "unrounded_attack": raw,
                        "base_attack": intrinsic_attack(base, multiplier),
                        "base_attributes": star.get("base_attributes", []),
                        "fixed_skill_code": star.get("fixed_skill_code"),
                        "fixed_skill_level": star.get("fixed_skill_level"),
                    }
                )
                total_combinations += 1
            matrix.append(
                {
                    "gear_tier": tier_no,
                    "tier_item_id": tier.get("item_id"),
                    "tier_base_attack_at_1_star": base,
                    "blueprint_star_values": star_values,
                }
            )

        issues = []
        if len(tiers) != 5:
            issues.append(f"expected 5 Gear Tier rows, found {len(tiers)}")
        if not stars:
            issues.append("no Blueprint Star rows")
        if any(len(row["blueprint_star_values"]) != len(stars) for row in matrix):
            issues.append("incomplete Tier × Blueprint Star matrix")
        if issues:
            invalid.append({"blueprint_id": weapon.get("blueprint_id"), "name": weapon.get("name"), "issues": issues})

        records.append(
            {
                "blueprint_id": weapon.get("blueprint_id"),
                "item_id": weapon.get("item_id"),
                "name": weapon.get("name"),
                "category": weapon.get("category"),
                "rarity": weapon.get("quality"),
                "progression_effect_mode": (weapon.get("blueprint_star_progression") or {}).get("progression_effect_mode"),
                "formula_status": "proven-static-base-attack",
                "tier_star_matrix": matrix,
                "static_inputs": {
                    "ranged_stats": weapon.get("ranged_stats"),
                    "melee_stats": weapon.get("melee_stats"),
                    "weapon_effect": weapon.get("effect"),
                },
                "validation_issues": issues,
            }
        )

    passed = bool(records) and not invalid
    return {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "All normalized player-facing weapons; static weapon-card math only",
        "formula_contract": {
            "base_attack": "int(tier_base_attack * preset_attack_ratio[blueprint_stars])",
            "static_attack_float": "base_attack * (1 + sum(D0101) + sum(D0102)) + sum(D0100_flat)",
            "final_display": "D0100 uses zero-decimal fixed-point formatting after static aggregation",
            "ratio_policy": "D0101 Weapon DMG and D0102 Calibration Weapon DMG share one additive ratio bucket",
        },
        "excluded_from_claimed_math": [
            "runtime proc frequency and proc damage without a fully resolved logic path",
            "enemy defense, resistance, level scaling, and scenario modifiers",
            "conditional weapon effects and temporary buffs",
            "mods, armor, set bonuses, cradles, deviations, consumables, and team buffs",
            "configured DPS unless every selected input and runtime layer is independently proven",
        ],
        "record_counts": {
            "weapons": len(records),
            "tier_star_combinations": total_combinations,
            "weapons_with_complete_math": len(records) - len(invalid),
            "weapons_with_validation_issues": len(invalid),
        },
        "validation": {"passed": passed, "issues": invalid},
        "weapons": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export evidence-backed Dead Signal weapon math")
    parser.add_argument("--weapons", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_weapon_math(read_json(args.weapons))
    write_json(args.output, payload)
    counts = payload["record_counts"]
    print(
        f"Weapon math: {counts['weapons_with_complete_math']}/{counts['weapons']} complete weapons, "
        f"{counts['tier_star_combinations']} Tier × Star combinations"
    )
    if not payload["validation"]["passed"]:
        raise SystemExit("Weapon math validation failed; see validation.issues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
