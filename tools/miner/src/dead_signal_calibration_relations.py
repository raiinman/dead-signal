"""Shared four-state weapon/Calibration Blueprint relationship policy.

This module consumes exact normalized weapon type codes only. It does not infer
compatibility from names, style labels, rarity, or family grouping.
"""
from __future__ import annotations

from typing import Any


FOUR_STATE_RELATIONSHIPS = ("compatible", "incompatible", "unresolved", "not-applicable")
CURRENT_CALIBRATION_SYSTEM = "current-calibration-blueprint"
PRINT_SOURCE_TABLE = "game_common/data/gun_correct_print_data.json"


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


def exact_print_owner(calibration: dict[str, Any]) -> bool:
    """Detect an exact gun_correct_print_data owner without guessing legacy state.

    Newer normalized records may carry the explicit owner fields. Older retained
    snapshots predate those fields, so the fallback requires at least one value
    that is populated only from a gun_correct_print_data rule. Empty subtype-39
    items remain unresolved rather than being called legacy.
    """
    explicit_system = calibration.get("calibration_system")
    explicit_owner = calibration.get("owner_state")
    if explicit_system is not None or explicit_owner is not None:
        return (
            explicit_system == CURRENT_CALIBRATION_SYSTEM
            and explicit_owner == "exact-gun-correct-print-owner"
        )
    return any(
        calibration.get(field) not in (None, "", 0, "0", [], {}, ())
        for field in (
            "weapon_type_codes",
            "calibration_style_code",
            "group_id",
            "buff_id",
            "season_state",
            "affix_val_range",
            "affix_ids_weight",
            "affix_ids",
        )
    )


def calibration_system_classification(calibration: dict[str, Any]) -> str:
    """Classify only the current Blueprint lane; never invent a legacy owner."""
    return CURRENT_CALIBRATION_SYSTEM if exact_print_owner(calibration) else "unresolved"


def is_current_calibration_blueprint(calibration: dict[str, Any]) -> bool:
    """Return True only for an exact, valid current Calibration Blueprint owner."""
    return exact_print_owner(calibration) and bool(calibration.get("is_valid", True))


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
