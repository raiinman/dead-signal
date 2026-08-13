"""Project the compact Calibration contract to the proven current blueprint system.

The normalized extended dataset preserves current and legacy Calibration Blueprint
rows. The player-facing default must not mix those systems. Current post-2.3.1
blueprints are identified fail-closed by two installed-game invariants:

1. current and legacy partners share the same mined buff_id identity; and
2. exactly one valid record in that identity carries the rarity-specific Weapon
   DMG RNG roll range proven for the current system.

No legacy row is discarded from diagnostics; non-current variants remain in the
contract review section so a future explicit legacy UI can consume them safely.
"""

from __future__ import annotations

from collections import defaultdict
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_CURRENT_COUNT = 94
EXPECTED_MAIN_RANGES = {
    "Rare": (18.0, 25.0),
    "Epic": (26.0, 33.0),
    "Legendary": (34.0, 50.0),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _buff_key(row: dict[str, Any]) -> str | None:
    value = row.get("buff_id")
    if isinstance(value, (list, tuple)) and len(value) == 2:
        first, second = value
        if first not in (None, "") and second not in (None, ""):
            return f"{first}:{second}"
    return None


def is_current_variant(row: dict[str, Any]) -> bool:
    if not bool(row.get("is_valid", True)):
        return False
    expected = EXPECTED_MAIN_RANGES.get(str(row.get("rarity") or "").strip())
    if expected is None:
        return False
    roll = row.get("roll_range")
    if not isinstance(roll, dict):
        return False
    minimum = roll.get("minimum_percent")
    maximum = roll.get("maximum_percent")
    if not (_numeric(minimum) and _numeric(maximum)):
        return False
    return (float(minimum), float(maximum)) == expected


def project(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema") != "dead-signal-calibrations":
        raise ValueError("Expected dead-signal-calibrations compact contract")
    source_families = payload.get("families")
    if not isinstance(source_families, list):
        raise ValueError("Calibration compact contract must contain families")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unkeyed_variants: list[dict[str, Any]] = []
    for family in source_families:
        if not isinstance(family, dict):
            continue
        for row in family.get("variants", []):
            if not isinstance(row, dict):
                continue
            key = _buff_key(row)
            if key is None:
                unkeyed_variants.append(row)
                continue
            grouped[key].append(row)

    current_families: list[dict[str, Any]] = []
    review_variants: list[dict[str, Any]] = list(unkeyed_variants)
    ambiguous_families: list[str] = [f"missing-buff-id:{row.get('item_id')}" for row in unkeyed_variants]

    for family_key, variants in sorted(grouped.items()):
        current = [row for row in variants if is_current_variant(row)]
        non_current = [row for row in variants if row not in current]

        if len(current) != 1:
            ambiguous_families.append(f"buff:{family_key}")
            review_variants.extend(variants)
            continue

        selected = dict(current[0])
        item_id = selected.get("item_id") or selected.get("id")
        current_families.append(
            {
                "canonical_id": f"ds-cal-{item_id}" if item_id not in (None, "") else f"ds-cal-buff-{family_key.replace(':', '-')}",
                "family_key": f"buff:{family_key}",
                "name": selected.get("name") or "Unnamed",
                "variant_count": 1,
                "variant_status": "current-system-selected-from-shared-buff-identity-and-proven-rarity-roll-range",
                "variants": [selected],
            }
        )
        review_variants.extend(non_current)

    ids = [row.get("canonical_id") for row in current_families]
    duplicate_ids = sorted({value for value in ids if value and ids.count(value) > 1})
    ready = (
        len(current_families) == EXPECTED_CURRENT_COUNT
        and not ambiguous_families
        and not duplicate_ids
        and all(ids)
    )

    return {
        "schema": "dead-signal-calibrations",
        "schema_version": 2,
        "generated_utc": utc_now(),
        "source_generated_utc": payload.get("source_generated_utc") or payload.get("generated_utc"),
        "record_counts": {
            "current_families": len(current_families),
            "legacy_or_noncurrent_variants": len(review_variants),
            "ambiguous_families": len(ambiguous_families),
        },
        "publication_status": "ready-current-system" if ready else "blocked-current-system-classification",
        "current_system_rule": "shared mined buff_id identity plus exactly one valid Rare/Epic/Legendary variant with its proven Weapon DMG RNG range",
        "main_roll_semantics": {
            "label": "Weapon DMG",
            "stat_id": "D0102",
            "aggregation": "same additive Attack-ratio bucket as D0101",
            "rarity_ranges_percent": {name: list(values) for name, values in EXPECTED_MAIN_RANGES.items()},
        },
        "expected_current_families": EXPECTED_CURRENT_COUNT,
        "duplicate_canonical_ids": duplicate_ids,
        "ambiguous_family_ids": sorted(ambiguous_families),
        "families": sorted(current_families, key=lambda row: (str(row.get("name") or "").casefold(), str(row.get("canonical_id") or ""))),
        "legacy_or_noncurrent_review": review_variants,
    }


def project_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    projected = project(payload)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(projected, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return projected
