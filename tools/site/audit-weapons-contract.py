#!/usr/bin/env python3
"""Audit a compact Dead Signal Weapons contract for unresolved player-facing work.

This tool is observational only. It does not normalize game data, infer runtime
mechanics, or classify missing recipes as non-craftable. It turns aggregate
coverage gaps into exact record-level queues for follow-up research and verifies
that the browser contract still preserves the proven static Weapons invariants.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


EXPECTED_SCHEMA = "dead-signal-weapons"
COMMON_NAMES = {"common"}
EXPECTED_GEAR_TIERS = {1, 2, 3, 4, 5}
PROVEN_FORMULA_STATUS = "proven-static-base-attack"
WITHHELD_DESCRIPTION_STATUS = "withheld-until-short-description-resolver-is-verified"


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


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _recipe_missing_tiers(weapon: dict[str, Any]) -> list[int]:
    missing: list[int] = []
    for row in ((weapon.get("progression") or {}).get("gear_tiers") or []):
        if not isinstance(row, dict):
            continue
        tier = row.get("tier")
        if not row.get("recipe"):
            parsed = _int(tier)
            if parsed is not None:
                missing.append(parsed)
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


def _identity_issues(weapon: dict[str, Any]) -> list[str]:
    issues = []
    if not _text(weapon.get("canonical_id")):
        issues.append("missing canonical_id")
    if weapon.get("blueprint_id") in (None, ""):
        issues.append("missing blueprint_id")
    if not _text(weapon.get("name")):
        issues.append("missing name")
    return issues


def _tier_shape_issues(weapon: dict[str, Any]) -> list[str]:
    tiers = (weapon.get("progression") or {}).get("gear_tiers") or []
    tier_numbers = [_int(row.get("tier")) for row in tiers if isinstance(row, dict)]
    issues = []
    if len(tiers) != 5:
        issues.append(f"expected 5 Gear Tier rows, found {len(tiers)}")
    if set(tier_numbers) != EXPECTED_GEAR_TIERS:
        issues.append(f"Gear Tier identity must be exactly I-V; found {tier_numbers}")
    if len(tier_numbers) != len(set(tier_numbers)):
        issues.append("duplicate Gear Tier identity")
    return issues


def _matrix_integrity_issues(weapon: dict[str, Any]) -> list[str]:
    progression = weapon.get("progression") or {}
    matrix = progression.get("tier_star_matrix") or []
    issues: list[str] = []

    if progression.get("formula_status") not in (None, "", PROVEN_FORMULA_STATUS):
        issues.append(f"unexpected formula_status={progression.get('formula_status')!r}")

    inherited = progression.get("validation_issues") or []
    if inherited:
        issues.append(f"upstream weapon-math validation issues present: {inherited}")

    if len(matrix) != 5:
        issues.append(f"expected 5 Tier × Star matrix rows, found {len(matrix)}")
        return issues

    matrix_tiers = [_int(row.get("gear_tier")) for row in matrix if isinstance(row, dict)]
    if set(matrix_tiers) != EXPECTED_GEAR_TIERS:
        issues.append(f"matrix Gear Tier identity must be exactly I-V; found {matrix_tiers}")
    if len(matrix_tiers) != len(set(matrix_tiers)):
        issues.append("duplicate Gear Tier in Tier × Star matrix")

    expected_star_set: set[int] | None = None
    for row in matrix:
        if not isinstance(row, dict):
            issues.append("non-object Tier × Star matrix row")
            continue
        tier = _int(row.get("gear_tier"))
        tier_base = _number(row.get("tier_base_attack_at_1_star"))
        stars = row.get("blueprint_star_values") or []
        star_numbers = [_int(star.get("blueprint_stars")) for star in stars if isinstance(star, dict)]
        current_set = {value for value in star_numbers if value is not None}
        if len(star_numbers) != len(set(star_numbers)):
            issues.append(f"duplicate Blueprint Star row at Gear Tier {tier}")
        if expected_star_set is None:
            expected_star_set = current_set
        elif current_set != expected_star_set:
            issues.append(
                f"inconsistent legal Blueprint Star rows at Gear Tier {tier}: "
                f"expected {sorted(expected_star_set)}, found {sorted(current_set)}"
            )

        for star in stars:
            if not isinstance(star, dict):
                issues.append(f"non-object Blueprint Star row at Gear Tier {tier}")
                continue
            star_no = _int(star.get("blueprint_stars"))
            ratio = _number(star.get("preset_attack_ratio"))
            shown = _number(star.get("base_attack"))
            if tier_base is None or ratio is None or shown is None:
                issues.append(
                    f"incomplete Base Attack evidence at Gear Tier {tier}, Blueprint Stars {star_no}"
                )
                continue
            expected = int(tier_base * ratio)
            if int(shown) != expected or shown != int(shown):
                issues.append(
                    f"Base Attack mismatch at Gear Tier {tier}, Blueprint Stars {star_no}: "
                    f"expected {expected}, found {star.get('base_attack')}"
                )
    return issues


def _description_integrity_issues(weapon: dict[str, Any]) -> list[str]:
    description = _text(weapon.get("description"))
    status = _text((weapon.get("verification") or {}).get("description_status"))
    if description and status == WITHHELD_DESCRIPTION_STATUS:
        return ["description text leaked while verification status says it must be withheld"]
    return []


def audit(payload: dict[str, Any]) -> dict[str, Any]:
    unresolved_effects: list[dict[str, Any]] = []
    missing_recipes: list[dict[str, Any]] = []
    missing_acquisition: list[dict[str, Any]] = []
    missing_images: list[dict[str, Any]] = []
    unresolved_profiles: list[dict[str, Any]] = []
    integrity_failures: list[dict[str, Any]] = []
    rarity_counts: Counter[str] = Counter()

    records = [row for row in (payload.get("weapons") or []) if isinstance(row, dict)]
    canonical_ids = [_text(row.get("canonical_id")) for row in records]
    duplicate_ids = sorted({value for value in canonical_ids if value and canonical_ids.count(value) > 1})
    declared_count = ((payload.get("record_counts") or {}).get("weapons"))
    contract_issues = []
    if declared_count is not None and _int(declared_count) != len(records):
        contract_issues.append(
            f"declared record_counts.weapons={declared_count} does not match actual records={len(records)}"
        )
    if duplicate_ids:
        contract_issues.append(f"duplicate canonical weapon IDs: {duplicate_ids}")

    for weapon in records:
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

        issues = (
            _identity_issues(weapon)
            + _tier_shape_issues(weapon)
            + _matrix_integrity_issues(weapon)
            + _description_integrity_issues(weapon)
        )
        if issues:
            integrity_failures.append({**base, "issues": issues})

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
        "schema_version": 2,
        "source_schema": payload.get("schema"),
        "source_schema_version": payload.get("schema_version"),
        "source_generated_utc": payload.get("generated_utc"),
        "policy": {
            "missing_effect": "Non-Common absence enters research queue; Common absence is only a candidate legitimate absence",
            "missing_recipe": "Reported as unresolved recipe evidence; never auto-classified non-craftable",
            "linked_skill_evidence": "Identifier links are preserved as evidence and do not prove player-facing runtime semantics",
            "base_attack": "Every published Base Attack cell must equal int(tier_base_attack_at_1_star * preset_attack_ratio)",
            "gear_tier": "Player-facing Gear Tier identity is exactly I-V",
            "description": "Description text must stay blank while verification status says the short-description resolver is withheld",
        },
        "counts": {
            "weapons": len(records),
            "rarities": dict(sorted(rarity_counts.items())),
            "contract_integrity_failures": len(contract_issues),
            "weapon_integrity_failures": len(integrity_failures),
            "unresolved_effects": len(unresolved_effects),
            "unresolved_non_common_effects": len(unresolved_non_common),
            "candidate_common_no_effect": len(unresolved_common),
            "weapons_with_missing_tier_recipes": len(missing_recipes),
            "weapons_without_acquisition_evidence": len(missing_acquisition),
            "weapons_without_artwork": len(missing_images),
            "unresolved_ranged_profiles": len(unresolved_profiles),
        },
        "contract_integrity": {
            "status": "PASS" if not contract_issues and not integrity_failures else "FAIL",
            "issues": contract_issues,
        },
        "queues": {
            "integrity_failures": integrity_failures,
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
        f"Contract integrity: {report['contract_integrity']['status']}",
        f"Contract-level integrity issues: {counts['contract_integrity_failures']}",
        f"Weapon integrity failures: {counts['weapon_integrity_failures']}",
        f"Unresolved non-Common effects: {counts['unresolved_non_common_effects']}",
        f"Candidate Common no-effect records: {counts['candidate_common_no_effect']}",
        f"Weapons with missing Tier recipes: {counts['weapons_with_missing_tier_recipes']}",
        f"Weapons without acquisition evidence: {counts['weapons_without_acquisition_evidence']}",
        f"Weapons without artwork: {counts['weapons_without_artwork']}",
        f"Unresolved ranged profiles: {counts['unresolved_ranged_profiles']}",
    ]
    if report["contract_integrity"]["issues"]:
        lines.extend(["", "Contract integrity issues:"])
        lines.extend(f"- {issue}" for issue in report["contract_integrity"]["issues"])
    for heading, key in (
        ("Weapon integrity failures", "integrity_failures"),
        ("Research-required effects", "unresolved_non_common_effects"),
        ("Missing Tier recipes", "missing_tier_recipes"),
    ):
        rows = report["queues"][key]
        if rows:
            lines.extend(["", heading + ":"])
            for row in rows:
                suffix = f" | tiers={','.join(map(str, row['missing_gear_tiers']))}" if "missing_gear_tiers" in row else ""
                if "issues" in row:
                    suffix += " | " + "; ".join(row["issues"])
                lines.append(f"- {row['name']} [{row['rarity']}] {row['canonical_id']}{suffix}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit exact unresolved records in Miner published/web/weapons.json")
    parser.add_argument("source", type=Path, help="weapons.json, published/web/, or published/ directory")
    parser.add_argument("--json-output", type=Path, default=None)
    parser.add_argument("--text-output", type=Path, default=None)
    args = parser.parse_args()
    source_path = resolve_source(args.source)
    report = audit(load_contract(source_path))
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.text_output:
        args.text_output.parent.mkdir(parents=True, exist_ok=True)
        args.text_output.write_text(human_summary(report), encoding="utf-8")
    print(human_summary(report), end="")
    return 0 if report["contract_integrity"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
