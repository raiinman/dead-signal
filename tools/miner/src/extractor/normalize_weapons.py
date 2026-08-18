"""Build website-ready weapon records from a mined Once Human snapshot."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from normalize_armor import (
    QUALITY_NAMES,
    Translator,
    player_facing_effect,
    source_summary,
    table,
    translation_entries,
)
from weapon_identity_spine import discover_weapon_identities


CURRENT_RECIPE_SERVER_NO = 222
WEAPON_TYPES = {
    1: "Pistol",
    2: "Shotgun",
    3: "Submachine Gun",
    4: "Assault Rifle",
    5: "Sniper Rifle",
    6: "Light Machine Gun",
    7: "Bow / Crossbow",
    8: "Heavy Weapon",
    9: "Melee",
}
PERCENT_ATTRIBUTES = {"E01", "E02", "E03"}
NAME_PREFIX = re.compile(r"^#t\([^)]*\)", re.IGNORECASE)
BLUEPRINT_ATTRIBUTE_KEY = re.compile(r"^\((\d+),\s*(\d+)\)$")


def display_name(value: str) -> str:
    """Remove an internal display prefix that leaked into one English name."""
    return NAME_PREFIX.sub("", value).strip()


def load_first_table(*paths: Path):
    for path in paths:
        if path.exists():
            return table(path)
    return {}


def overlay_table(base_path: Path, current_path: Path):
    """Overlay Current exact owners over Base without discarding unchanged Base rows."""
    merged = table(base_path) if base_path.exists() else {}
    if current_path.exists():
        merged.update(table(current_path))
    return merged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    base = args.base
    current = args.current

    blueprints = overlay_table(
        base / "game_common/data/gun_blueprint_data.json",
        current / "game_common/data/gun_blueprint_data.json",
    )
    blueprint_attributes = table(
        base / "game_common/data/gun_blueprint_attr_data.json"
    )
    prototypes = table(base / "game_common/data/weapon_prototype_data.json")
    passive_skills = table(base / "game_common/data/passive_skill_data.json")
    stability = table(base / "game_common/data/gun_stability_data.json")
    scatter = table(base / "game_common/data/bullet_scatter_data.json")
    bullet_patterns = load_first_table(
        current / "client_data/bullet_pattern_data.json",
        base / "client_data/bullet_pattern_data.json",
    )
    char_properties = load_first_table(
        current / "game_common/data/char_property_data.json",
        base / "game_common/data/char_property_data.json",
    )
    items = table(current / "game_common/data/item_data.json")
    equipment = table(current / "game_common/data/equip_data.json")
    origins = load_first_table(
        current / "game_common/data/equip_origin_data.json",
        base / "game_common/data/equip_origin_data.json",
    )
    achievements = load_first_table(
        current / "game_common/data/achieve_item_data.json",
        base / "game_common/data/achieve_item_data.json",
    )
    buff_levels = load_first_table(
        current / "game_common/data/buff_level_data.json",
        base / "game_common/data/buff_level_data.json",
    )
    gun_params = load_first_table(
        current / "game_common/data/gun_base_params_data.json",
        base / "game_common/data/gun_base_params_data.json",
    )
    forge_data = load_first_table(
        current / "game_common/data/forge_data.json",
        base / "game_common/data/forge_data.json",
    )
    currency_data = load_first_table(
        current / "game_common/data/money_material_data.json",
        base / "game_common/data/money_material_data.json",
    )

    translations = {}
    base_translation = base / "translate/translate_data_en.json"
    if base_translation.exists():
        translations.update(translation_entries(base_translation))
    for path in sorted((current / "translate").glob("translate_data_en*.json")):
        translations.update(translation_entries(path))
    translate = Translator(translations)

    attribute_labels = {}
    for key, record in char_properties.items():
        attr_id = str(record.get("attr_id") or "")
        if attr_id:
            attribute_labels[attr_id] = {
                "key": key,
                "label": translate(record.get("attr_chs_name")),
            }

    def normalized_blueprint_attributes(record: dict):
        attributes = []
        for index in range(1, 5):
            code = str(record.get(f"base_attr_name{index}") or "")
            if not code:
                continue
            short_code = code[:3]
            raw_value = record.get(f"base_attr_val{index}")
            label = attribute_labels.get(short_code, {})
            attributes.append(
                {
                    "code": code,
                    "key": label.get("key", ""),
                    "label": label.get("label", code),
                    "value": raw_value,
                    "display_value": (
                        f"{float(raw_value) * 100:g}%"
                        if short_code in PERCENT_ATTRIBUTES and raw_value is not None
                        else str(raw_value)
                    ),
                }
            )
        return attributes

    blueprint_attribute_levels = {}
    for attribute_key, record in blueprint_attributes.items():
        if not isinstance(record, dict):
            continue
        match = BLUEPRINT_ATTRIBUTE_KEY.fullmatch(str(attribute_key).strip())
        if not match:
            continue
        source_blueprint_id = int(match.group(1))
        source_level = int(match.group(2))
        blueprint_attribute_levels.setdefault(source_blueprint_id, []).append(
            {
                "level": source_level,
                "table_key": str(attribute_key),
                "fixed_skill_code": str(record.get("fixed_skill_code") or ""),
                "fixed_skill_level": int(record.get("fixed_skill_lv") or 0),
                "strength_lv": int(record.get("strength_lv") or source_level),
                # Source field is misspelled "radio" in the game table; the value is
                # already a direct multiplicative Attack ratio (1.05 = x1.05).
                "preset_attack_ratio": record.get("preset_attack_radio"),
                "preset_attack_ratio_source_field": "preset_attack_radio",
                "base_attributes": normalized_blueprint_attributes(record),
                # Keep the complete mined row so later analysis can identify
                # star/grade/enhancement semantics without rerunning extraction.
                "raw_fields": record,
            }
        )
    for rows in blueprint_attribute_levels.values():
        rows.sort(key=lambda row: row["level"])

    currencies = {}
    for currency_id, record in currency_data.items():
        currencies[str(currency_id)] = {
            "name": translate(record.get("name")) or "Currency",
            "icon": record.get("item_icon") or record.get("icon") or "",
        }

    tier_items_by_blueprint = {}
    for tier_item_id, record in equipment.items():
        blueprint_id = int(record.get("blueprint_no") or 0)
        art_level = int(record.get("art_lv") or 0)
        suffix = int(tier_item_id[-2:]) if tier_item_id[-2:].isdigit() else -1
        if (
            blueprint_id
            and 1 <= art_level <= 5
            and int(record.get("equip_lv") or 0) == 1
            and suffix == art_level
        ):
            tier_items_by_blueprint[(blueprint_id, art_level)] = int(tier_item_id)

    def recipe_for(forge_no: int, blueprint_id: int, weapon_name: str):
        current_key = f"({forge_no}, {CURRENT_RECIPE_SERVER_NO})"
        forge = forge_data.get(current_key) or forge_data.get(str(forge_no), {})
        if not forge:
            return None

        materials = []
        unresolved = []
        for item_id, quantity in zip(
            forge.get("cost_item_list", []), forge.get("cost_num_list", [])
        ):
            item_id = int(item_id)
            material = items.get(str(item_id), {})
            material_name = display_name(translate(material.get("name"))) if material else ""
            if not material_name:
                unresolved.append(item_id)
                continue
            materials.append(
                {
                    "item_id": item_id,
                    "name": material_name,
                    "quantity": int(quantity),
                    "icon": material.get("icon") or "",
                    "quality_code": int(material.get("quality") or 0),
                    "quality": QUALITY_NAMES.get(
                        int(material.get("quality") or 0), "Common"
                    ),
                }
            )
        if unresolved:
            review_queue.append(
                {
                    "blueprint_id": blueprint_id,
                    "name": weapon_name,
                    "reason": f"Recipe {forge_no} contains unresolved material identifiers",
                    "item_ids": sorted(set(unresolved)),
                }
            )

        currency_id = int(forge.get("cost_money_no") or 0)
        currency = currencies.get(str(currency_id), {})
        return {
            "forge_no": forge_no,
            "recipe_key": current_key if current_key in forge_data else str(forge_no),
            "recipe_server_no": (
                CURRENT_RECIPE_SERVER_NO if current_key in forge_data else 0
            ),
            "output_item_id": int(forge.get("item_no") or 0),
            "fixed_materials": materials,
            "currency": {
                "currency_id": currency_id,
                "name": currency.get("name", "Currency"),
                "quantity": int(forge.get("cost_money_num") or 0),
                "icon": currency.get("icon", ""),
            },
            "craft_time_seconds": int(forge.get("seconds") or 0),
            "source_status": "mined-current-recipe-layer"
            if current_key in forge_data
            else "mined-fallback-recipe-layer",
        }

    review_queue = []
    exclusions = Counter()
    weapons = []

    translated_names = {
        str(item_id): display_name(translate(record.get("name")))
        for item_id, record in items.items()
        if isinstance(record, dict)
    }
    identities, identity_exclusions = discover_weapon_identities(
        items, equipment, origins, achievements, blueprints, translated_names
    )
    exclusions.update(identity_exclusions)

    for identity in identities:
        blueprint = identity["blueprint"]
        blueprint_id = int(identity.get("blueprint_id") or 0)
        item_id = int(identity["item_id"])
        item = identity["item"]
        equip = identity["equipment"]
        prototype_id = int(blueprint.get("prototype_no") or 0)
        prototype = prototypes.get(str(prototype_id), {})
        weapon_type = int(prototype.get("weapon_type") or identity["weapon_type_code"] or 0)
        name = identity["name"]
        forge_numbers = [int(value) for value in blueprint.get("corr_forge_no", [])]
        forge_levels = [int(value) for value in blueprint.get("corr_forge_lv", [])]

        enhancement = blueprint_attributes.get(f"({blueprint_id}, 1)", {})
        fixed_skill_code = str(enhancement.get("fixed_skill_code") or "")
        fixed_skill_level = int(enhancement.get("fixed_skill_lv") or 1)
        effect = None
        if fixed_skill_code:
            skill = passive_skills.get(fixed_skill_code, {})
            buff_id = int(skill.get("buff_id") or 0)
            buff = buff_levels.get(f"({buff_id}, {fixed_skill_level})", {})
            effect_name = translate(buff.get("buff_name")) or translate(skill.get("name"))
            effect_description = player_facing_effect(
                translate(buff.get("buff_desc")), buff.get("desc_value", [])
            )
            if effect_name or effect_description:
                effect = {
                    "skill_code": fixed_skill_code,
                    "skill_level": fixed_skill_level,
                    "buff_id": buff_id,
                    "name": effect_name or "Weapon effect",
                    "description": effect_description,
                    "icon": skill.get("icons") or buff.get("icon_path") or "",
                    "keyword_buff_id": int(skill.get("keyword_buff_id") or 0),
                    "keyword_status_id": int(skill.get("keyword_status_id") or 0),
                }
            else:
                review_queue.append(
                    {
                        "blueprint_id": blueprint_id,
                        "name": name,
                        "reason": f"Fixed weapon skill {fixed_skill_code} did not resolve to player-facing text",
                    }
                )

        base_attributes = normalized_blueprint_attributes(enhancement)
        progression_levels = blueprint_attribute_levels.get(blueprint_id, [])
        if not progression_levels:
            review_queue.append(
                {
                    "blueprint_id": blueprint_id,
                    "name": name,
                    "reason": "No gun_blueprint_attr_data progression rows were found",
                }
            )
        elif not any(row["level"] == 1 for row in progression_levels):
            review_queue.append(
                {
                    "blueprint_id": blueprint_id,
                    "name": name,
                    "reason": "Blueprint attribute progression exists but level 1 is missing",
                    "levels": [row["level"] for row in progression_levels],
                }
            )

        progression_hint_fields = {
            str(key): value
            for key, value in blueprint.items()
            if re.search(r"quality|grade|star|enhanc|level|_lv|lv_", str(key), re.IGNORECASE)
        }

        tiers = []
        missing_recipe_levels = []
        tier_sources = list(zip(forge_levels, forge_numbers))
        if not tier_sources and blueprint_id:
            tier_sources = [
                (level, 0) for level in range(1, 6)
                if (blueprint_id, level) in tier_items_by_blueprint
            ]
        if not tier_sources and identity["identity_state"] == "special-equipped":
            tier_sources = [(int(equip.get("art_lv") or 0) or 1, 0)]
        for level, forge_no in tier_sources:
            recipe = recipe_for(forge_no, blueprint_id, name) if forge_no else None
            if not recipe:
                missing_recipe_levels.append(level)
            output_item_id = int(
                (recipe or {}).get("output_item_id")
                or tier_items_by_blueprint.get((blueprint_id, level))
                or (item_id if len(tier_sources) == 1 else 0)
                or 0
            )
            tier_item = items.get(str(output_item_id), {})
            tier_equip = equipment.get(str(output_item_id), {})
            origin_id = str(tier_equip.get("equip_origin_id") or output_item_id)
            origin = origins.get(origin_id, {})
            if not output_item_id or not tier_item or not tier_equip or not origin:
                review_queue.append(
                    {
                        "blueprint_id": blueprint_id,
                        "name": name,
                        "reason": f"Tier {level} did not resolve to a complete item, equipment, and origin row",
                    }
                )
            tiers.append(
                {
                    "tier": level,
                    "tier_label": f"Tier {level}",
                    "item_id": output_item_id,
                    "gun_no": int(tier_equip.get("gun_no") or 0),
                    "damage": origin.get("gun_preset_attack"),
                    "durability": tier_item.get("durability"),
                    "weight": tier_item.get("weight"),
                    "melee_attack_speed": translate(origin.get("melee_attack_speed")),
                    "melee_attack_range": translate(origin.get("melee_attack_range")),
                    "recipe": recipe,
                }
            )

        if missing_recipe_levels and identity["craftability_state"] == "standard-tier-progression":
            review_queue.append(
                {
                    "blueprint_id": blueprint_id,
                    "name": name,
                    "reason": "No forge recipe is present for the recorded weapon tiers",
                    "tiers": missing_recipe_levels,
                }
            )

        gun_no = int(equip.get("gun_no") or 0)
        gun = gun_params.get(str(gun_no), {})
        bullet_pattern_id = str(gun.get("bullet_pattern_no") or "")
        bullet_pattern = bullet_patterns.get(bullet_pattern_id, {})
        scatter_row = scatter.get(str(gun.get("bullet_scatter_no") or ""), {})
        stability_row = stability.get(str(gun_no), {}) or stability.get(
            str(gun.get("viewkick_no") or ""), {}
        )
        ranged_stats = None
        melee_stats = None
        if weapon_type != 9:
            ranged_stats = {
                "rpm": gun.get("weapon_rpm_affix_value"),
                "magazine": gun.get("weapon_magazine_size_affix_value"),
                "range_meters": gun.get("weapon_range_value"),
                "accuracy": scatter_row.get("weapon_accuracy_affix_value"),
                "stability": stability_row.get("weapon_stability"),
                "mobility": gun.get("weapon_mobility"),
                "reload_seconds": gun.get("reload_loop_time"),
                "full_damage_distance": (gun.get("dis_damage_value1") or [None])[0],
                "minimum_damage_distance": (gun.get("dis_damage_value2") or [None])[0],
                "minimum_damage_multiplier": (gun.get("dis_damage_value2") or [None, None])[1],
                "ammo_item_id": int(gun.get("bullet_no") or 0),
                "bullet_pattern_id": bullet_pattern_id,
                "projectile_count": bullet_pattern.get("bullet_num"),
            }
            missing = [
                key
                for key in ("rpm", "magazine", "range_meters")
                if ranged_stats.get(key) is None
            ]
            if missing:
                review_queue.append(
                    {
                        "blueprint_id": blueprint_id,
                        "name": name,
                        "reason": "Missing core ranged fields: " + ", ".join(missing),
                    }
                )
        else:
            melee_stats = {
                "attack_speed": tiers[0].get("melee_attack_speed") if tiers else "",
                "attack_range": tiers[0].get("melee_attack_range") if tiers else "",
            }

        quality_code = int(item.get("quality") or equip.get("equip_quality") or 0)
        acquisition_hint = display_name(translate(blueprint.get("get_way_str")))
        item_gain_path = display_name(translate(item.get("gain_path")))
        short_description = player_facing_effect(translate(item.get("short_desc")), [])
        weapons.append(
            {
                "canonical_id": identity["canonical_id"],
                "blueprint_id": blueprint_id or None,
                "item_id": item_id,
                "name": name,
                "category": WEAPON_TYPES.get(weapon_type, f"Type {weapon_type}"),
                "weapon_type_code": weapon_type,
                "prototype_id": prototype_id,
                "gun_no": int(equip.get("gun_no") or 0),
                "identity": {
                    "state": "resolved-installed-weapon",
                    "classification": identity["identity_state"],
                    "blueprint_owner_state": identity["blueprint_owner_state"],
                    "referenced_blueprint_id": identity["referenced_blueprint_id"],
                    "achievement_attrs": identity["achievement_attrs"],
                    "evidence": [
                        "game_common/data/item_data.json",
                        "game_common/data/equip_data.json",
                        "game_common/data/equip_origin_data.json",
                        "game_common/data/achieve_item_data.json",
                    ],
                },
                "availability": {"state": identity["availability_state"]},
                "craftability": {"state": identity["craftability_state"]},
                "quality_code": quality_code,
                "quality": QUALITY_NAMES.get(quality_code, "Common"),
                "icon": item.get("icon") or "",
                "icon_equip": item.get("icon_equip") or "",
                "forge_icon": item.get("forge_icon") or "",
                "durability": item.get("durability"),
                "weight": item.get("weight"),
                "short_description": short_description,
                "acquisition_hint": acquisition_hint,
                "item_gain_path": item_gain_path,
                "fragment_id": int(blueprint.get("fragment_no") or 0),
                "fragments_to_unlock": int(blueprint.get("unlock_fragment_num") or 0),
                "endowed_blueprint": bool(blueprint.get("endow")),
                "blueprint_attribute_progression": {
                    "source_table": "game_common/data/gun_blueprint_attr_data.json",
                    "interpretation_status": "mined-strength-level-with-direct-attack-ratio",
                    "level_count": len(progression_levels),
                    "levels": progression_levels,
                    "blueprint_progression_hint_fields": progression_hint_fields,
                    "note": (
                        "The table tuple level is retained alongside source strength_lv and preset_attack_radio. "
                        "The combat progression investigator validates the global Blueprint Star semantic mapping and UI rounding separately."
                    ),
                },
                "base_attributes": base_attributes,
                "ranged_stats": ranged_stats,
                "melee_stats": melee_stats,
                "effect": effect,
                "tiers": tiers,
                "verification_notes": [
                    "Weapon identity, stats, effect text, and recipes were reconstructed from the installed game snapshot.",
                    "Current availability and the exact acquisition path still require direct in-game verification.",
                ],
            }
        )

    # Build a first-class Blueprint Star view only after validating the mined source
    # fields across the complete weapon corpus. Gear Tier remains the separate five-row
    # weapon["tiers"] path derived from corr_forge_lv / art_lv.
    progression_rows = [
        level
        for weapon in weapons
        for level in weapon.get("blueprint_attribute_progression", {}).get("levels", [])
        if isinstance(level, dict)
    ]
    strength_rows = [
        level for level in progression_rows
        if int(level.get("strength_lv") or 0) > 0
    ]
    matching_strength_rows = [
        level for level in strength_rows
        if int(level.get("strength_lv") or 0) == int(level.get("level") or 0)
    ]
    ratio_rows = [
        level for level in progression_rows
        if level.get("preset_attack_ratio") is not None
    ]
    star_axis_validated = bool(progression_rows) and len(matching_strength_rows) == len(progression_rows)
    ratio_coverage_complete = bool(progression_rows) and len(ratio_rows) == len(progression_rows)

    for weapon in weapons:
        levels = weapon.get("blueprint_attribute_progression", {}).get("levels", [])
        star_rows = []
        for level in levels:
            strength_lv = int(level.get("strength_lv") or level.get("level") or 0)
            star_rows.append({
                "blueprint_stars": strength_lv,
                "source_strength_lv": strength_lv,
                "preset_attack_ratio": level.get("preset_attack_ratio"),
                "preset_attack_ratio_source_field": "preset_attack_radio",
                "fixed_skill_level": int(level.get("fixed_skill_level") or 0),
                "base_attributes": level.get("base_attributes", []),
            })
        ratio_values = [row.get("preset_attack_ratio") for row in star_rows if row.get("preset_attack_ratio") is not None]
        skill_values = [int(row.get("fixed_skill_level") or 0) for row in star_rows]
        attack_ratio_changes = len(set(ratio_values)) > 1
        fixed_skill_level_changes = len(set(skill_values)) > 1
        if attack_ratio_changes and fixed_skill_level_changes:
            progression_effect_mode = "attack-ratio-and-skill-level"
        elif attack_ratio_changes:
            progression_effect_mode = "attack-ratio"
        elif fixed_skill_level_changes:
            progression_effect_mode = "skill-level"
        else:
            progression_effect_mode = "no-changing-attack-ratio-or-skill-level"

        weapon["blueprint_star_progression"] = {
            "semantic_status": (
                "validated-source-axis"
                if star_axis_validated else "candidate-source-axis"
            ),
            "source_table": "game_common/data/gun_blueprint_attr_data.json",
            "source_level_field": "strength_lv",
            "tier_separation": "Gear Tier I-V is stored separately in weapon.tiers",
            "attack_factor_field": "preset_attack_radio",
            "attack_factor_semantics": "direct multiplier; 1.05 means x1.05",
            "progression_effect_mode": progression_effect_mode,
            "attack_ratio_changes_with_stars": attack_ratio_changes,
            "fixed_skill_level_changes_with_stars": fixed_skill_level_changes,
            "rounding_status": "unresolved-until-client-consumer-or-ui-observation",
            "stars": star_rows,
        }

    star_progression_modes = Counter(
        weapon.get("blueprint_star_progression", {}).get("progression_effect_mode", "unknown")
        for weapon in weapons
    )

    weapons.sort(key=lambda weapon: (weapon["category"], weapon["name"].casefold()))
    names = Counter(weapon["name"] for weapon in weapons)
    duplicate_names = sorted(name for name, count in names.items() if count > 1)
    if duplicate_names:
        review_queue.append(
            {
                "reason": "Duplicate canonical display names remain",
                "names": duplicate_names,
            }
        )

    categories = Counter(weapon["category"] for weapon in weapons)
    rarities = Counter(weapon["quality"] for weapon in weapons)
    all_recipes = [
        tier.get("recipe")
        for weapon in weapons
        for tier in weapon["tiers"]
        if tier.get("recipe")
    ]
    meaningful_translation_misses = sorted(
        value
        for value in translate.misses
        if not re.fullmatch(r"[A-Za-z0-9 ._\-/]+", value)
    )
    payload = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "base_snapshot": source_summary(base / "snapshot.json"),
            "current_snapshot": source_summary(current / "snapshot.json"),
            "primary_evidence": "Installed Once Human game snapshot",
            "recipe_layer": CURRENT_RECIPE_SERVER_NO,
        },
        "record_counts": {
            "weapons": len(weapons),
            "ranged_weapons": sum(
                weapon["weapon_type_code"] != 9 for weapon in weapons
            ),
            "melee_weapons": sum(
                weapon["weapon_type_code"] == 9 for weapon in weapons
            ),
            "categories": dict(sorted(categories.items())),
            "rarities": dict(sorted(rarities.items())),
            "tier_stat_rows": sum(len(weapon["tiers"]) for weapon in weapons),
            "blueprint_attribute_rows": sum(
                weapon["blueprint_attribute_progression"]["level_count"]
                for weapon in weapons
            ),
            "weapons_with_multiple_blueprint_attribute_levels": sum(
                weapon["blueprint_attribute_progression"]["level_count"] > 1
                for weapon in weapons
            ),
            "max_blueprint_attribute_level": max(
                (
                    row["level"]
                    for weapon in weapons
                    for row in weapon["blueprint_attribute_progression"]["levels"]
                ),
                default=0,
            ),
            "blueprint_strength_rows": len(strength_rows),
            "blueprint_strength_rows_matching_tuple_level": len(matching_strength_rows),
            "preset_attack_ratio_rows": len(ratio_rows),
            "blueprint_star_axis_validated": star_axis_validated,
            "preset_attack_ratio_coverage_complete": ratio_coverage_complete,
            "blueprint_star_progression_modes": dict(sorted(star_progression_modes.items())),
            "current_recipes": sum(
                recipe.get("recipe_server_no") == CURRENT_RECIPE_SERVER_NO
                for recipe in all_recipes
            ),
            "weapon_effects": sum(bool(weapon["effect"]) for weapon in weapons),
            "weapons_with_projectile_count": sum(
                (weapon.get("ranged_stats") or {}).get("projectile_count") is not None
                for weapon in weapons
            ),
            "multi_projectile_weapons": sum(
                ((weapon.get("ranged_stats") or {}).get("projectile_count") or 0) > 1
                for weapon in weapons
            ),
            "alternate_templates_excluded": exclusions["alternate-template"],
            "identity_classifications": dict(sorted(Counter(
                weapon["identity"]["classification"] for weapon in weapons
            ).items())),
            "scenario_availability_unresolved": sum(
                weapon["availability"]["state"] == "unresolved-scenario-availability"
                for weapon in weapons
            ),
            "translation_misses": len(meaningful_translation_misses),
            "review_queue": len(review_queue),
        },
        "weapons": weapons,
        "review_queue": review_queue,
        "exclusion_counts": dict(sorted(exclusions.items())),
        "translation_misses": meaningful_translation_misses,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    progression_payload = {
        "schema_version": 1,
        "generated_utc": payload["generated_utc"],
        "source": payload["source"],
        "interpretation_status": (
            "validated-blueprint-strength-axis-with-direct-attack-ratio"
            if star_axis_validated and ratio_coverage_complete
            else "partial-blueprint-progression-evidence"
        ),
        "semantic_mapping": {
            "blueprint_stars": "gun_blueprint_attr_data.strength_lv",
            "gear_tier": "weapon.tiers / corr_forge_lv / art_lv (I-V)",
            "star_attack_multiplier": "gun_blueprint_attr_data.preset_attack_radio",
            "rounding": "unresolved until client consumer or independent UI display evidence is recovered",
        },
        "record_counts": {
            "weapons": len(weapons),
            "attribute_rows": payload["record_counts"]["blueprint_attribute_rows"],
            "weapons_with_multiple_levels": payload["record_counts"][
                "weapons_with_multiple_blueprint_attribute_levels"
            ],
            "max_level": payload["record_counts"]["max_blueprint_attribute_level"],
            "strength_rows": len(strength_rows),
            "strength_rows_matching_tuple_level": len(matching_strength_rows),
            "preset_attack_ratio_rows": len(ratio_rows),
            "star_axis_validated": star_axis_validated,
            "attack_ratio_coverage_complete": ratio_coverage_complete,
            "progression_effect_modes": dict(sorted(star_progression_modes.items())),
        },
        "weapons": [
            {
                "blueprint_id": weapon["blueprint_id"],
                "item_id": weapon["item_id"],
                "name": weapon["name"],
                "category": weapon["category"],
                "quality_code": weapon["quality_code"],
                "quality": weapon["quality"],
                "crafted_tiers": [tier["tier"] for tier in weapon["tiers"]],
                "blueprint_attribute_progression": weapon[
                    "blueprint_attribute_progression"
                ],
                "blueprint_star_progression": weapon["blueprint_star_progression"],
            }
            for weapon in weapons
        ],
    }
    progression_output = args.output.with_name("weapon-blueprint-progression.json")
    progression_output.write_text(
        json.dumps(progression_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(payload["record_counts"], ensure_ascii=False, indent=2))
    print(f"Blueprint progression audit: {progression_output}")
    canonical_ids = [weapon["canonical_id"] for weapon in weapons]
    return 0 if weapons and len(canonical_ids) == len(set(canonical_ids)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
