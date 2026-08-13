"""Project the compact Calibration contract to the proven current blueprint system.

Current and legacy rows are paired by mined buff_id. A player-facing current family is
published only when exactly one valid variant carries both the proven rarity-specific
Weapon DMG roll and the proven one-of-four secondary pool. The normalized source row
is used only to restore candidate weights omitted by the generic compact family layer.
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
EXPECTED_SECONDARIES = {
    "Rare": (
        ("Weakspot DMG", frozenset({"E0300"}), 12.0, 18.0),
        ("Crit Rate", frozenset({"E0100"}), 8.0, 12.0),
        ("Elemental DMG", frozenset({"E3200", "E3300", "E3400", "E3800"}), 12.0, 18.0),
        ("Crit DMG", frozenset({"E0200"}), 20.0, 30.0),
    ),
    "Epic": (
        ("Weakspot DMG", frozenset({"E0300"}), 15.0, 21.0),
        ("Crit Rate", frozenset({"E0100"}), 10.0, 14.0),
        ("Elemental DMG", frozenset({"E3200", "E3300", "E3400", "E3800"}), 12.0, 18.0),
        ("Crit DMG", frozenset({"E0200"}), 25.0, 35.0),
    ),
    "Legendary": (
        ("Weakspot DMG", frozenset({"E0300"}), 18.0, 24.0),
        ("Crit Rate", frozenset({"E0100"}), 12.0, 16.0),
        ("Elemental DMG", frozenset({"E3200", "E3300", "E3400", "E3800"}), 15.0, 20.0),
        ("Crit DMG", frozenset({"E0200"}), 30.0, 40.0),
    ),
}
EXPECTED_SECONDARY_WEIGHTS = [200, 200, 200, 200]


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


def _candidate_term(affix: dict[str, Any]) -> tuple[frozenset[str], float, float] | None:
    terms = affix.get("terms")
    if not isinstance(terms, list):
        return None
    candidates = []
    for term in terms:
        if not isinstance(term, dict):
            continue
        stat_ids = frozenset(str(value) for value in term.get("affix_ids") or [] if str(value))
        minimum = term.get("min_val")
        maximum = term.get("max_val")
        if stat_ids and _numeric(minimum) and _numeric(maximum):
            candidates.append((stat_ids, float(minimum) * 100.0, float(maximum) * 100.0))
    return candidates[0] if len(candidates) == 1 else None


def secondary_roll_candidates(row: dict[str, Any]) -> list[dict[str, Any]] | None:
    rarity = str(row.get("rarity") or "").strip()
    expected = EXPECTED_SECONDARIES.get(rarity)
    if expected is None:
        return None
    weights = row.get("affix_ids_weight")
    affixes = row.get("affixes")
    if list(weights or []) != EXPECTED_SECONDARY_WEIGHTS or not isinstance(affixes, list) or len(affixes) != 4:
        return None

    actual = []
    for index, affix in enumerate(affixes):
        if not isinstance(affix, dict):
            return None
        term = _candidate_term(affix)
        if term is None:
            return None
        stat_ids, minimum, maximum = term
        actual.append(
            {
                "affix_id": affix.get("affix_id"),
                "stat_ids": stat_ids,
                "minimum_percent": minimum,
                "maximum_percent": maximum,
                "weight": int(weights[index]),
            }
        )

    result = []
    used = set()
    for label, stat_ids, minimum, maximum in expected:
        matches = [
            (index, candidate)
            for index, candidate in enumerate(actual)
            if index not in used
            and candidate["stat_ids"] == stat_ids
            and candidate["minimum_percent"] == minimum
            and candidate["maximum_percent"] == maximum
        ]
        if len(matches) != 1:
            return None
        index, candidate = matches[0]
        used.add(index)
        result.append(
            {
                "label": label,
                "affix_id": candidate["affix_id"],
                "stat_ids": sorted(candidate["stat_ids"]),
                "minimum_percent": minimum,
                "maximum_percent": maximum,
                "weight": candidate["weight"],
            }
        )
    return result if len(used) == 4 else None


def _normalized_variants(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(payload, dict):
        return result
    for row in payload.get("calibrations") or []:
        if not isinstance(row, dict):
            continue
        item_id = row.get("item_id")
        if item_id not in (None, ""):
            result[str(item_id)] = row
    return result


def project(payload: dict[str, Any], normalized_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if payload.get("schema") != "dead-signal-calibrations":
        raise ValueError("Expected dead-signal-calibrations compact contract")
    source_families = payload.get("families")
    if not isinstance(source_families, list):
        raise ValueError("Calibration compact contract must contain families")

    normalized_by_item = _normalized_variants(normalized_payload)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unkeyed_variants: list[dict[str, Any]] = []
    for family in source_families:
        if not isinstance(family, dict):
            continue
        for source_row in family.get("variants", []):
            if not isinstance(source_row, dict):
                continue
            row = dict(source_row)
            normalized = normalized_by_item.get(str(row.get("item_id")))
            if normalized:
                row["affix_ids_weight"] = normalized.get("affix_ids_weight") or []
            key = _buff_key(row)
            if key is None:
                unkeyed_variants.append(row)
                continue
            grouped[key].append(row)

    current_families: list[dict[str, Any]] = []
    review_variants: list[dict[str, Any]] = list(unkeyed_variants)
    ambiguous_families: list[str] = [f"missing-buff-id:{row.get('item_id')}" for row in unkeyed_variants]
    secondary_failures: list[str] = []

    for family_key, variants in sorted(grouped.items()):
        current = [row for row in variants if is_current_variant(row)]
        non_current = [row for row in variants if row not in current]

        if len(current) != 1:
            ambiguous_families.append(f"buff:{family_key}")
            review_variants.extend(variants)
            continue

        selected = dict(current[0])
        secondaries = secondary_roll_candidates(selected)
        if secondaries is None:
            secondary_failures.append(f"buff:{family_key}")
            review_variants.extend(variants)
            continue
        selected["secondary_roll_candidates"] = secondaries
        selected["secondary_roll_rule"] = "exactly-one-candidate-selected; equal observed source weight 200 each"
        item_id = selected.get("item_id") or selected.get("id")
        current_families.append(
            {
                "canonical_id": f"ds-cal-{item_id}" if item_id not in (None, "") else f"ds-cal-buff-{family_key.replace(':', '-')}",
                "family_key": f"buff:{family_key}",
                "name": selected.get("name") or "Unnamed",
                "variant_count": 1,
                "variant_status": "current-system-selected-from-shared-buff-identity-and-proven-main-plus-secondary-rolls",
                "variants": [selected],
            }
        )
        review_variants.extend(non_current)

    ids = [row.get("canonical_id") for row in current_families]
    duplicate_ids = sorted({value for value in ids if value and ids.count(value) > 1})
    ready = (
        len(current_families) == EXPECTED_CURRENT_COUNT
        and not ambiguous_families
        and not secondary_failures
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
            "secondary_pool_failures": len(secondary_failures),
        },
        "publication_status": "ready-current-system" if ready else "blocked-current-system-classification",
        "current_system_rule": "shared mined buff_id identity plus exactly one valid Rare/Epic/Legendary variant with its proven Weapon DMG RNG range and exact one-of-four secondary pool",
        "main_roll_semantics": {
            "label": "Weapon DMG",
            "stat_id": "D0102",
            "aggregation": "same additive Attack-ratio bucket as D0101",
            "rarity_ranges_percent": {name: list(values) for name, values in EXPECTED_MAIN_RANGES.items()},
        },
        "secondary_roll_semantics": {
            "selection_count": 1,
            "observed_candidate_weights": EXPECTED_SECONDARY_WEIGHTS,
            "weight_interpretation": "equal observed source weights; no probability percentage is invented",
            "rarity_candidates": {
                rarity: [
                    {
                        "label": label,
                        "stat_ids": sorted(stat_ids),
                        "minimum_percent": minimum,
                        "maximum_percent": maximum,
                    }
                    for label, stat_ids, minimum, maximum in candidates
                ]
                for rarity, candidates in EXPECTED_SECONDARIES.items()
            },
        },
        "expected_current_families": EXPECTED_CURRENT_COUNT,
        "duplicate_canonical_ids": duplicate_ids,
        "ambiguous_family_ids": sorted(ambiguous_families),
        "secondary_pool_failure_ids": sorted(secondary_failures),
        "families": sorted(current_families, key=lambda row: (str(row.get("name") or "").casefold(), str(row.get("canonical_id") or ""))),
        "legacy_or_noncurrent_review": review_variants,
    }


def project_file(path: Path, normalized_path: Path | None = None) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    normalized_payload = None
    if normalized_path is not None and normalized_path.is_file():
        normalized_payload = json.loads(normalized_path.read_text(encoding="utf-8"))
    projected = project(payload, normalized_payload)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(projected, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return projected
