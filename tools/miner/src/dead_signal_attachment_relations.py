"""Shared four-state weapon/attachment relationship policy.

This module contains no discovery and creates no evidence by itself. It consumes
only already-proven structured attachment scope or exact typed weapon item IDs.
Named model text alone never establishes identity.
"""
from __future__ import annotations

from typing import Any


FOUR_STATE_RELATIONSHIPS = ("compatible", "incompatible", "unresolved", "not-applicable")


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

    typed_ids = {
        value for value in attachment.get("compatible_weapon_item_ids") or []
        if value not in (None, "")
    }
    if typed_ids:
        return "compatible" if weapon.get("item_id") in typed_ids else "incompatible"

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
