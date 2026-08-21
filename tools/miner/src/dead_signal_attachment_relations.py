"""Shared four-state weapon/attachment relationship policy.

This module contains no discovery and creates no evidence by itself. It consumes
only already-proven structured attachment scope or exact typed installed-data
selectors. Named model text alone never establishes identity.
"""
from __future__ import annotations

from typing import Any


FOUR_STATE_RELATIONSHIPS = ("compatible", "incompatible", "unresolved", "not-applicable")


def _values(value: Any) -> set[str]:
    if value in (None, "", [], (), {}):
        return set()
    if isinstance(value, dict):
        values = []
        for key, child in value.items():
            if child not in (False, None, "", 0, "0"):
                values.append(key)
        return {str(item) for item in values}
    if isinstance(value, (list, tuple, set)):
        return {str(item) for item in value if item not in (None, "")}
    return {str(value)}


def _typed_selector_relation(weapon: dict[str, Any], attachment: dict[str, Any]) -> str | None:
    """Resolve only exact selector fields whose destination type is explicit."""
    evidence = attachment.get("compatibility_evidence") or {}
    selectors = (evidence.get("owner_trace") or {}).get("typed_selectors") or {}

    item_ids = _values(selectors.get("weapon_item_no_list"))
    if item_ids:
        return "compatible" if str(weapon.get("item_id")) in item_ids else "incompatible"

    gun_nos = _values(selectors.get("gun_no_list"))
    if gun_nos:
        return "compatible" if str(weapon.get("gun_no")) in gun_nos else "incompatible"

    type_codes = _values(selectors.get("weapon_type_list")) | _values(selectors.get("gun_type_list"))
    if type_codes:
        weapon_type = weapon.get("weapon_type_code")
        if weapon_type not in (None, "", 0, "0"):
            return "compatible" if str(weapon_type) in type_codes else "incompatible"

    legacy_typed_ids = _values(attachment.get("compatible_weapon_item_ids"))
    if legacy_typed_ids:
        return "compatible" if str(weapon.get("item_id")) in legacy_typed_ids else "incompatible"
    return None


def attachment_weapon_relation(weapon: dict[str, Any], attachment: dict[str, Any]) -> str:
    """Return the fail-closed four-state relationship for one weapon/attachment pair."""
    if weapon.get("category") == "Melee":
        return "not-applicable"

    evidence = attachment.get("compatibility_evidence") or {}
    if evidence.get("all_weapons"):
        return "compatible"

    categories = set(evidence.get("compatible_weapon_categories") or [])
    if weapon.get("category") in categories:
        return "compatible"
    if categories and not evidence.get("named_weapon_text_present"):
        return "incompatible"

    typed_relation = _typed_selector_relation(weapon, attachment)
    if typed_relation is not None:
        return typed_relation

    return "unresolved"


def invert_weapon_attachment_states(
    weapons: list[dict[str, Any]],
    attachment_identity: object,
) -> dict[str, list[str]]:
    """Invert published weapon-side four-state lists for one exact attachment identity."""
    target = str(attachment_identity)
    result: dict[str, list[str]] = {state: [] for state in FOUR_STATE_RELATIONSHIPS}
    for weapon in weapons:
        compatibility = (weapon.get("compatibility") or {}).get("attachment") or {}
        canonical = str(weapon.get("canonical_id") or weapon.get("blueprint_id") or weapon.get("item_id") or "")
        if not canonical:
            continue
        matches = []
        for state in FOUR_STATE_RELATIONSHIPS:
            values = compatibility.get(f"{state.replace('-', '_')}_ids") or []
            if any(str(value) == target for value in values):
                matches.append(state)
        if len(matches) == 1:
            result[matches[0]].append(canonical)
        elif len(matches) > 1:
            # A weapon that places the same attachment in multiple states is not
            # silently reconciled; the adapter will surface this as a conflict.
            for state in matches:
                result[state].append(canonical)
    return result
