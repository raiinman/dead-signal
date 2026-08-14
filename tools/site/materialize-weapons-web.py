#!/usr/bin/env python3
"""Materialize the Miner's compact public Weapons JSON for the static website.

This tool does not normalize or reinterpret game data. It validates the public
contract and wraps the exact JSON payload in a browser assignment so the
prepared static site can consume the Miner's published/web/weapons.json output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


EXPECTED_SCHEMA = "dead-signal-weapons"
EXPECTED_SCHEMA_VERSION = 1
LEGAL_GEAR_TIERS = {1, 2, 3, 4, 5}
RARITY_STAR_CAPS = {
    "common": 3,
    "rare": 4,
    "epic": 5,
    "legendary": 6,
}


def resolve_source(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.is_file():
        return path
    if path.is_dir():
        for candidate in (path / "web" / "weapons.json", path / "weapons.json"):
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(f"Could not find published Weapons JSON under: {path}")


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _number(value: Any) -> float | None:
    return float(value) if _finite_number(value) else None


def _validated_star_axis(record: dict[str, Any], progression: dict[str, Any]) -> set[int]:
    canonical_id = record.get("canonical_id") or "<missing canonical_id>"
    rarity = str(record.get("rarity") or "").strip().lower()
    rarity_cap = RARITY_STAR_CAPS.get(rarity)
    if rarity_cap is None:
        raise ValueError(f"Weapon {canonical_id} has unsupported rarity {record.get('rarity')!r}")

    axis = progression.get("blueprint_stars")
    if not isinstance(axis, dict) or axis.get("semantic_status") != "validated-source-axis":
        raise ValueError(f"Weapon {canonical_id} is missing a validated mined Blueprint Star axis")
    stars = axis.get("stars")
    if not isinstance(stars, list) or not stars or any(not isinstance(row, dict) for row in stars):
        raise ValueError(f"Weapon {canonical_id} has no mined Blueprint Star source rows")

    star_numbers = [_positive_int(row.get("blueprint_stars")) for row in stars]
    if any(value is None for value in star_numbers) or len(star_numbers) != len(set(star_numbers)):
        raise ValueError(f"Weapon {canonical_id} has invalid or duplicate mined Blueprint Star rows")
    maximum = max(value for value in star_numbers if value is not None)
    expected = set(range(1, maximum + 1))
    if set(star_numbers) != expected:
        raise ValueError(f"Weapon {canonical_id} mined Blueprint Star axis must be contiguous from 1 through {maximum}")
    if maximum > rarity_cap:
        raise ValueError(
            f"Weapon {canonical_id} mined Blueprint Star axis exceeds {record.get('rarity')} rarity cap {rarity_cap}"
        )
    return expected


def _validate_progression(record: dict[str, Any]) -> None:
    canonical_id = record.get("canonical_id") or "<missing canonical_id>"
    progression = record.get("progression")
    if not isinstance(progression, dict):
        raise ValueError(f"Weapon {canonical_id} is missing progression data")

    gear_tiers = progression.get("gear_tiers")
    if not isinstance(gear_tiers, list) or len(gear_tiers) != 5:
        raise ValueError(f"Weapon {canonical_id} must contain exactly five Gear Tier rows")
    tier_numbers = [_positive_int(row.get("tier")) if isinstance(row, dict) else None for row in gear_tiers]
    if set(tier_numbers) != LEGAL_GEAR_TIERS or len(set(tier_numbers)) != 5:
        raise ValueError(f"Weapon {canonical_id} Gear Tier rows must be unique Tier I-V")

    matrix = progression.get("tier_star_matrix")
    if not isinstance(matrix, list) or len(matrix) != 5:
        raise ValueError(f"Weapon {canonical_id} must contain five Tier × Blueprint Star matrix rows")
    matrix_tiers = [_positive_int(row.get("gear_tier")) if isinstance(row, dict) else None for row in matrix]
    if set(matrix_tiers) != LEGAL_GEAR_TIERS or len(set(matrix_tiers)) != 5:
        raise ValueError(f"Weapon {canonical_id} Tier × Star matrix must cover unique Gear Tier I-V")

    expected_stars = _validated_star_axis(record, progression)

    for row in matrix:
        if not isinstance(row, dict):
            raise ValueError(f"Weapon {canonical_id} has a non-object Tier × Blueprint Star row")
        tier = _positive_int(row.get("gear_tier"))
        tier_base = _number(row.get("tier_base_attack_at_1_star"))
        if tier_base is None:
            raise ValueError(f"Weapon {canonical_id} Gear Tier {tier} is missing numeric 1★ Base Attack evidence")

        stars = row.get("blueprint_star_values")
        if not isinstance(stars, list) or not stars:
            raise ValueError(f"Weapon {canonical_id} has an empty Blueprint Star matrix row")
        star_numbers = [_positive_int(star.get("blueprint_stars")) if isinstance(star, dict) else None for star in stars]
        if any(value is None for value in star_numbers) or len(star_numbers) != len(set(star_numbers)):
            raise ValueError(f"Weapon {canonical_id} has invalid or duplicate Blueprint Star rows")
        if set(star_numbers) != expected_stars:
            raise ValueError(
                f"Weapon {canonical_id} Tier × Star rows must exactly match mined Blueprint Star axis "
                f"{sorted(expected_stars)}; found {sorted(value for value in star_numbers if value is not None)}"
            )

        for star in stars:
            if not isinstance(star, dict):
                raise ValueError(f"Weapon {canonical_id} has a non-object Blueprint Star row")
            star_no = _positive_int(star.get("blueprint_stars"))
            shown = _number(star.get("base_attack"))
            ratio = _number(star.get("preset_attack_ratio"))
            if shown is None:
                raise ValueError(f"Weapon {canonical_id} has a Tier × Star row without numeric Base Attack")
            if ratio is None:
                raise ValueError(
                    f"Weapon {canonical_id} Gear Tier {tier} Blueprint Stars {star_no} is missing numeric preset_attack_ratio"
                )
            expected_attack = int(tier_base * ratio)
            if shown != int(shown) or int(shown) != expected_attack:
                raise ValueError(
                    f"Weapon {canonical_id} Base Attack mismatch at Gear Tier {tier}, Blueprint Stars {star_no}: "
                    f"expected {expected_attack}, found {star.get('base_attack')}"
                )

    if progression.get("validation_issues"):
        raise ValueError(f"Weapon {canonical_id} carries unresolved progression validation issues")


def load_and_validate(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Published Weapons payload must be a JSON object")
    if payload.get("schema") != EXPECTED_SCHEMA:
        raise ValueError(f"Expected schema {EXPECTED_SCHEMA!r}, found {payload.get('schema')!r}")
    if payload.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        raise ValueError(
            f"Expected schema_version {EXPECTED_SCHEMA_VERSION}, found {payload.get('schema_version')!r}"
        )
    records = payload.get("weapons")
    if not isinstance(records, list) or not records:
        raise ValueError("Published Weapons payload contains no weapon records")
    if any(not isinstance(record, dict) for record in records):
        raise ValueError("Every published weapon record must be a JSON object")

    ids = [record.get("canonical_id") for record in records]
    if any(not value for value in ids):
        raise ValueError("Every published weapon must have a canonical_id")
    if len(ids) != len(set(ids)):
        raise ValueError("Published Weapons payload contains duplicate canonical_id values")

    for record in records:
        if not str(record.get("name") or "").strip():
            raise ValueError(f"Weapon {record.get('canonical_id')} is missing a player-facing name")
        _validate_progression(record)

    counts = payload.get("record_counts") or {}
    declared = counts.get("weapons")
    if declared is not None and int(declared) != len(records):
        raise ValueError(f"record_counts.weapons={declared} but payload contains {len(records)} records")

    ranged_count = sum(bool((record.get("baseline") or {}).get("ranged")) for record in records)
    melee_count = sum(bool((record.get("baseline") or {}).get("melee")) for record in records)
    if counts.get("ranged_weapons") is not None and int(counts["ranged_weapons"]) != ranged_count:
        raise ValueError(
            f"record_counts.ranged_weapons={counts['ranged_weapons']} but payload contains {ranged_count} ranged records"
        )
    if counts.get("melee_weapons") is not None and int(counts["melee_weapons"]) != melee_count:
        raise ValueError(
            f"record_counts.melee_weapons={counts['melee_weapons']} but payload contains {melee_count} melee records"
        )
    return payload


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_browser_payload(source: Path, output: Path, payload: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    header = (
        "// Generated from Miner published/web/weapons.json. Do not hand-edit.\n"
        f"// Source generated_utc: {payload.get('generated_utc') or 'unknown'}\n"
        f"// Source SHA-256: {sha256(source)}\n"
    )
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(f"{header}window.DS_WEAPONS_WEB={encoded};\n", encoding="utf-8")
    temporary.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wrap a Miner published/web/weapons.json contract for the Dead Signal static site"
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Path to weapons.json, published/web/, or the Miner published/ directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JS path (default: repository database/weapons/weapons-data.js)",
    )
    args = parser.parse_args()

    repository_root = Path(__file__).resolve().parents[2]
    source = resolve_source(args.source)
    output = (args.output.expanduser().resolve() if args.output else repository_root / "database" / "weapons" / "weapons-data.js")
    payload = load_and_validate(source)
    write_browser_payload(source, output, payload)
    print(f"Materialized {len(payload['weapons'])} weapons: {source} -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
