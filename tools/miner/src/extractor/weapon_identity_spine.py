"""Exact installed weapon identity discovery independent of craft progression."""
from __future__ import annotations

import re
from typing import Any

WEAPON_FAMILY_TYPES = {
    "arms_gun_pistolgun": 1,
    "arms_gun_shrapnelgun": 2,
    "arms_gun_submachinegun": 3,
    "arms_gun_assaultgun": 4,
    "arms_gun_snipergun": 5,
    "arms_gun_machinegun": 6,
    "arms_project_bow": 7,
    "arms_gun_heavygun": 8,
    "arms_hand": 9,
}
TEST_MARKER = re.compile(r"(?:\btemp\b|_temp\b|\btest\b|测试)", re.IGNORECASE)


def _attrs(record: Any) -> set[str]:
    if not isinstance(record, dict):
        return set()
    return {str(value) for value in (record.get("attrs") or [])}


def weapon_type_from_evidence(item: dict[str, Any], achievement: dict[str, Any]) -> int:
    """Resolve the public weapon family from exact item and achievement fields."""
    if int(item.get("type") or 0) == 2:
        return 9
    attrs = _attrs(achievement)
    for marker, weapon_type in WEAPON_FAMILY_TYPES.items():
        if marker in attrs or (marker == "arms_hand" and any(value.startswith("arms_hand") for value in attrs)):
            return weapon_type
    subtype = int(item.get("sub_type") or 0)
    return subtype if 1 <= subtype <= 8 else 0


def _is_weapon_family(achievement: dict[str, Any]) -> bool:
    attrs = _attrs(achievement)
    return any(value.startswith("arms_hand") for value in attrs) or "arms_gun_lv1" in attrs


def discover_weapon_identities(
    items: dict[str, Any],
    equipment: dict[str, Any],
    origins: dict[str, Any],
    achievements: dict[str, Any],
    blueprints: dict[str, Any],
    translated_names: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Return one exact current identity per weapon, with explicit exclusion counts.

    Blueprint-backed identities require an exact blueprint->gun_item owner match.
    Missing-owner references are admitted only at the exact tier-I equipment row.
    Blueprint-free identities remain item-owned special records. Achievement fields
    corroborate family membership but are never counted directly as identities.
    """
    exclusions: dict[str, int] = {}

    def reject(reason: str) -> None:
        exclusions[reason] = exclusions.get(reason, 0) + 1

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    exact_owner_gun_nos: set[int] = set()
    for item_key, equip in equipment.items():
        if not isinstance(equip, dict):
            continue
        blueprint_id = int(equip.get("blueprint_no") or 0)
        blueprint = blueprints.get(str(blueprint_id), {}) if blueprint_id else {}
        if (
            isinstance(blueprint, dict)
            and int(blueprint.get("blueprint_template_no") or 0) == 10
            and int(blueprint.get("gun_item_no") or 0) == int(item_key)
            and int(equip.get("gun_no") or 0)
        ):
            exact_owner_gun_nos.add(int(equip["gun_no"]))
    for item_key, equip in sorted(equipment.items(), key=lambda row: str(row[0])):
        if not isinstance(equip, dict):
            continue
        item = items.get(str(item_key))
        if not isinstance(item, dict):
            reject("missing-current-item")
            continue
        if int(item.get("type") or 0) not in (1, 2):
            continue
        if int(item.get("temp_item") or 0):
            reject("temporary-item")
            continue
        if int(item.get("private_server_item") or 0):
            reject("private-server-item")
            continue
        achievement = achievements.get(str(item_key), {})
        if "arms_gun_lv0" in _attrs(achievement):
            reject("non-player-level-zero-weapon")
            continue
        name = str(translated_names.get(str(item_key)) or "").strip()
        if not name:
            reject("missing-name")
            continue
        raw_name = str(item.get("name") or "")
        if TEST_MARKER.search(name) or TEST_MARKER.search(raw_name):
            reject("explicit-test-record")
            continue
        origin_id = str(equip.get("equip_origin_id") or item_key)
        if not isinstance(origins.get(origin_id), dict):
            reject("missing-current-origin")
            continue
        blueprint_id = int(equip.get("blueprint_no") or 0)
        blueprint = blueprints.get(str(blueprint_id), {}) if blueprint_id else {}
        referenced_blueprint_id = blueprint_id or None
        if blueprint:
            if int(blueprint.get("blueprint_template_no") or 0) != 10:
                reject("non-current-blueprint-template")
                continue
            if int(blueprint.get("gun_item_no") or 0) != int(item_key):
                continue
        elif blueprint_id:
            art_level = int(equip.get("art_lv") or 0)
            suffix = int(str(item_key)[-2:]) if str(item_key)[-2:].isdigit() else -1
            special_melee = int(item.get("type") or 0) == 2 and any(
                value.startswith("arms_hand") for value in _attrs(achievement)
            )
            if special_melee and art_level in (0, 1) and int(equip.get("equip_lv") or 0) == 1:
                blueprint_id = 0
            elif art_level != 1 or suffix != 1:
                continue
        if not blueprint and not _is_weapon_family(achievement):
            reject("not-tier-one-weapon-family")
            continue
        if not blueprint_id:
            gun_no = int(equip.get("gun_no") or 0)
            if gun_no and gun_no in exact_owner_gun_nos:
                reject("duplicate-exact-gun-owner")
                continue
            expected_tab = 2 if int(item.get("type") or 0) == 2 else 10
            if int(item.get("item_belonge_tab") or 0) != expected_tab:
                reject("weapon-tab-family-mismatch")
                continue
        # No blueprint reference is a distinct, exact item-owned identity.
        canonical_id = f"blueprint:{blueprint_id}" if blueprint_id else f"item:{item_key}"
        if canonical_id in seen:
            continue
        seen.add(canonical_id)
        forge_numbers = list(blueprint.get("corr_forge_no") or [])
        forge_levels = list(blueprint.get("corr_forge_lv") or [])
        standard_progression = len(forge_numbers) == len(forge_levels) == 5
        if blueprint and standard_progression:
            identity_state = "standard-blueprint"
        elif blueprint_id:
            identity_state = "nonstandard-blueprint"
        else:
            identity_state = "special-equipped"
        result.append({
            "canonical_id": canonical_id,
            "item_id": int(item_key),
            "blueprint_id": blueprint_id or None,
            "referenced_blueprint_id": referenced_blueprint_id,
            "blueprint": blueprint,
            "item": item,
            "equipment": equip,
            "achievement_attrs": sorted(_attrs(achievement)),
            "weapon_type_code": weapon_type_from_evidence(item, achievement),
            "name": name,
            "identity_state": identity_state,
            "blueprint_owner_state": (
                "exact-owner" if blueprint else
                "referenced-owner-missing" if blueprint_id else
                "not-applicable"
            ),
            "availability_state": (
                "unresolved-scenario-availability"
                if identity_state == "special-equipped"
                else "installed-current-identity"
            ),
            "craftability_state": (
                "standard-tier-progression" if standard_progression else
                "unresolved-nonstandard-progression" if blueprint_id else
                "not-applicable-no-blueprint"
            ),
        })
    return result, dict(sorted(exclusions.items()))
