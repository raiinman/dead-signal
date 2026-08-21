"""Shared four-state weapon/Calibration Blueprint relationship policy.

This module consumes exact normalized weapon type codes only. It does not infer
compatibility from names, style labels, rarity, or family grouping.
"""
from __future__ import annotations

from typing import Any


FOUR_STATE_RELATIONSHIPS = ("compatible", "incompatible", "unresolved", "not-applicable")
CURRENT_CALIBRATION_SYSTEM = "current-calibration-blueprint"


def _int_set(values: Any) -> set[int]:
    result: set[int] = set()
    for value in values or []:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number:
            result.add(number)
    return result


def is_current_calibration_blueprint(calibration: dict[str, Any]) -> bool:
    """Return True only for an exact current Calibration Blueprint owner."""
    return (
        calibration.get("calibration_system") == CURRENT_CALIBRATION_SYSTEM
        and calibration.get("owner_state") == "exact-gun-correct-print-owner"
        and bool(calibration.get("is_valid", True))
    )


def calibration_weapon_relation(weapon: dict[str, Any], calibration: dict[str, Any]) -> str:
    """Return the fail-closed four-state relationship for one exact pair."""
    if weapon.get("category") == "Melee":
        return "not-applicable"
    if not is_current_calibration_blueprint(calibration):
        return "unresolved"

    try:
        weapon_type = int(weapon.get("weapon_type_code") or 0)
    except (TypeError, ValueError):
        weapon_type = 0
    calibration_types = _int_set(calibration.get("weapon_type_codes"))
    if not weapon_type or not calibration_types:
        return "unresolved"
    return "compatible" if weapon_type in calibration_types else "incompatible"


def invert_weapon_calibration_states(
    weapons: list[dict[str, Any]],
    calibration_identity: object,
) -> dict[str, list[str]]:
    """Invert weapon-side four-state lists for one exact calibration identity."""
    target = str(calibration_identity)
    result: dict[str, list[str]] = {state: [] for state in FOUR_STATE_RELATIONSHIPS}
    for weapon in weapons:
        compatibility = (weapon.get("compatibility") or {}).get("calibration") or {}
        canonical = str(
            weapon.get("canonical_id")
            or weapon.get("blueprint_id")
            or weapon.get("item_id")
            or ""
        )
        if not canonical:
            continue
        matches = []
        for state in FOUR_STATE_RELATIONSHIPS:
            values = compatibility.get(f"{state.replace('-', '_')}_ids") or []
            if any(str(value) == target for value in values):
                matches.append(state)
        for state in matches:
            result[state].append(canonical)
    return result
