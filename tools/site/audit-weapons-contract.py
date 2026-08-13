#!/usr/bin/env python3
"""Audit a compact Dead Signal Weapons contract for unresolved player-facing work.

This tool is observational only. It does not normalize game data, infer runtime
mechanics, or classify missing recipes as non-craftable. It turns aggregate
coverage gaps into exact record-level queues for follow-up research.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


EXPECTED_SCHEMA = "dead-signal-weapons"
COMMON_NAMES = {"common"}


def resolve_source(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.is_file():
        return path
    if path.is_dir():
        for candidate in (path / "web" / "weapons.json", path / "weapons.json"):
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(f"Could not find published Weapons JSON under: {path}")


def load_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != EXPECTED_SCHEMA:
        raise ValueError(f"Expected {EXPECTED_SCHEMA!r} compact Weapons contract")
    records = payload.get("weapons")
    if not isinstance(records, list):
        raise ValueError("Weapons contract must contain a weapons array")
    return payload


def _text(value: Any) -> str:
    return str(value or "").strip()


def _recipe_missing_tiers(weapon: dict[str, Any]) -> list[int]:
    missing: list[int] = []
    for row in ((weapon.get("progression") or {}).get("gear_tiers") or []):
        if not isinstance(row, dict):
            continue
        tier = row.get("tier")
        if not row.get("recipe"):
            try:
                missing.append(int(tier))
            except (TypeError, ValueError):
                continue
    return sorted(set(missing))


def _acquisition_evidence(weapon: dict[str, Any]) -> dict[str, Any]:
    acquisition = weapon.get("acquisition") or {}
    return {
        "hint": _text(acquisition.get("hint")),
        "gain_path": _text(acquisition.get("gain_path")),
        "fragment_id": acquisition.get("fragment_id"),
        "fragments_to_unlock": acquisition.get("fragments_to_unlock"),
        "endowed_blueprint": bool(acquisition.get("endowed_blueprint")),
    }


def _has_acquisition(evidence: dict[str, Any]) -> bool:
    return bool(
        evidence["hint"]
        or evidence["gain_path"]
        or evidence["endowed_blueprint"]
        or evidence["fragment_id"]
        or evidence["fragments_to_unlock"]
    )


def audit(payload: dict[str, Any]) -> dict[str, Any]:
    unresolved_effects: list[dict[str, Any]] = []
    missing_recipes: list[dict[str, Any]] = []
    missing_acquisition: list[dict[str, Any]] = []
    missing_images: list[dict[str, Any]] = []
    unresolved_profiles: list[dict[str, Any]] = []
    rarity_counts: Counter[str] = Counter()

    for weapon in payload.get("weapons") or []:
        if not isinstance(weapon, dict):
            continue
        canonical_id = _text(weapon.get("canonical_id"))
        name = _text(weapon.get("name"))
        rarity = _text(weapon.get("rarity")) or "Unknown"
        category = _text(weapon.get("category"))
        rarity_counts[rarity] += 1
        base = {
            "canonical_id": canonical_id,
            "blueprint_id": weapon.get("blueprint_id"),
            "item_id": weapon.get("item_id"),
            "name": name,
            "rarity": rarity,
            "category": category,
        }

        if not weapon.get("effect"):
            common = rarity.casefold() in COMMON_NAMES
            unresolved_effects.append({
                **base,
                "priority": "candidate-legitimate-absence" if common else "research-required",
                "reason": "No resolved player-facing weapon effect in compact Miner contract",
                "linked_ids": ((weapon.get("gun_profile") or {}).get("linked_ids") or {}),
            })

        tiers = _recipe_missing_tiers(weapon)
        if tiers:
            missing_recipes.append({
                **base,
                "missing_gear_tiers": tiers,
                "classification": "unresolved-recipe-evidence",
                "reason": "One or more recorded Gear Tiers have no resolved recipe; non-craftable is not proven",
            })

        acquisition = _acquisition_evidence(weapon)
        if not _has_acquisition(acquisition):
            missing_acquisition.append({**base, "reason": "No player-facing acquisition evidence resolved"})

        if not _text(weapon.get("image_asset")):
            missing_images.append({**base, "reason": "No linked website artwork"})

        profile = weapon.get("gun_profile") or {}
        resolution = _text(profile.get("resolution_status"))
        if category.casefold() != "melee" and resolution and resolution.casefold() != "resolved":
            unresolved_profiles.append({
                **base,
                "resolution_status": resolution,
                "gun_no": profile.get("gun_no"),
                "linked_ids": profile.get("linked_ids") or {},
            })

    unresolved_non_common = [row for row in unresolved_effects if row["priority"] == "research-required"]
    unresolved_common = [row for row in unresolved_effects if row["priority"] == "candidate-legitimate-absence"]
    return {
        "schema": "dead-signal-weapons-contract-audit",
        "schema_version": 1,
        "source_schema": payload.get("schema"),
        "source_schema_version": payload.get("schema_version"),
        "source_generated_utc": payload.get("generated_utc"),
        "policy": {
            "missing_effect": "Non-Common absence enters research queue; Common absence is only a candidate legitimate absence",
            "missing_recipe": "Reported as unresolved recipe evidence; never auto-classified non-craftable",
            "linked_skill_evidence": "Identifier links are preserved as evidence and do not prove player-facing runtime semantics",
        },
        "counts": {
            "weapons": len(payload.get("weapons") or []),
            "rarities": dict(sorted(rarity_counts.items())),
            "unresolved_effects": len(unresolved_effects),
            "unresolved_non_common_effects": len(unresolved_non_common),
            "candidate_common_no_effect": len(unresolved_common),
            "weapons_with_missing_tier_recipes": len(missing_recipes),
            "weapons_without_acquisition_evidence": len(missing_acquisition),
            "weapons_without_artwork": len(missing_images),
            "unresolved_ranged_profiles": len(unresolved_profiles),
        },
        "queues": {
            "unresolved_non_common_effects": unresolved_non_common,
            "candidate_common_no_effect": unresolved_common,
            "missing_tier_recipes": missing_recipes,
            "missing_acquisition": missing_acquisition,
            "missing_artwork": missing_images,
            "unresolved_ranged_profiles": unresolved_profiles,
        },
    }


def human_summary(report: dict[str, Any]) -> str:
    counts = report["counts"]
    lines = [
        "Dead Signal Weapons contract audit",
        f"Weapons: {counts['weapons']}",
        f"Unresolved non-Common effects: {counts['unresolved_non_common_effects']}",
        f"Candidate Common no-effect records: {counts['candidate_common_no_effect']}",
        f"Weapons with missing Tier recipes: {counts['weapons_with_missing_tier_recipes']}",
        f"Weapons without acquisition evidence: {counts['weapons_without_acquisition_evidence']}",
        f"Weapons without artwork: {counts['weapons_without_artwork']}",
        f"Unresolved ranged profiles: {counts['unresolved_ranged_profiles']}",
    ]
    for heading, key in (
        ("Research-required effects", "unresolved_non_common_effects"),
        ("Missing Tier recipes", "missing_tier_recipes"),
    ):
        rows = report["queues"][key]
        if rows:
            lines.extend(["", heading + ":"])
            for row in rows:
                suffix = f" | tiers={','.join(map(str, row['missing_gear_tiers']))}" if "missing_gear_tiers" in row else ""
                lines.append(f"- {row['name']} [{row['rarity']}] {row['canonical_id']}{suffix}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit exact unresolved records in Miner published/web/weapons.json")
    parser.add_argument("source", type=Path, help="weapons.json, published/web/, or published/ directory")
    parser.add_argument("--json-output", type=Path, default=None)
    parser.add_argument("--text-output", type=Path, default=None)
    args = parser.parse_args()
    source = resolve_source(args.source)
    report = audit(load_contract(source))
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.text_output:
        args.text_output.parent.mkdir(parents=True, exist_ok=True)
        args.text_output.write_text(human_summary(report), encoding="utf-8")
    print(human_summary(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
