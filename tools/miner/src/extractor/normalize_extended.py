"""Publish the remaining DeadSignalDB categories from an existing game snapshot.

This module is deliberately a normalizer, not another miner.  It consumes the
same base/current table folders already produced by Dead Signal Miner and adds
website-ready JSON files beside weapons.json and armor-sets.json.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
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


GAME_DATA = "game_common/data"
ATTACHMENT_TYPES = {61: "Sight", 62: "Muzzle", 63: "Tactical", 64: "Magazine"}
SKILL_SOURCES = (
    ("passive", "passive_skill_data.json"),
    ("deviation", "deviation_skills_data.json"),
    ("character_active", "character_active_skill_data.json"),
    ("active", "active_skill_data.json"),
    ("common", "common_skill_data.json"),
)
PROGRESSION_SOURCES = (
    ("character_level", "avatar_level_data.json"),
    ("character_level_current", "avatar_level_data_new.json"),
    ("memetics", "meme_level_data.json"),
    ("blueprint_collection", "blueprint_collection_level_data.json"),
    ("mod_level", "new_mod_level_data.json"),
    ("legacy_mod_level", "mod_level_lib_data.json"),
    ("deviation_level", "deviation_level_data.json"),
    ("deviation_race_level", "deviation_level_race_data.json"),
    ("cradle_training", "cradle_train_level_data.json"),
    ("hive_level", "hive_level_data.json"),
    ("hive_tech", "hive_tech_level_data.json"),
    ("technology_invention", "tech_invent_level_data.json"),
    ("season_rank", "season_dan_level_data.json"),
)


def load_table(root: Path, relative: str) -> dict:
    path = root / relative
    return table(path) if path.exists() else {}


def merged_table(base: Path, current: Path, relative: str) -> dict:
    """Apply current patch rows over the base table without losing base-only rows."""
    result = dict(load_table(base, relative))
    result.update(load_table(current, relative))
    return result


def as_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def key_parts(value: object) -> list[str]:
    return re.findall(r"[A-Za-z]+[A-Za-z0-9_]*|-?\d+", str(value))


def first_int(value: object, fallback=0) -> int:
    for part in key_parts(value):
        if re.fullmatch(r"-?\d+", part):
            return int(part)
    return fallback


def normalize_scalar(value, translate: Translator):
    if isinstance(value, dict):
        if "lan_translate" in value:
            return translate(value)
        return {str(key): normalize_scalar(child, translate) for key, child in value.items()}
    if isinstance(value, list):
        return [normalize_scalar(child, translate) for child in value]
    return value


def translated_text(translate: Translator, value, replacements=None) -> str:
    text = translate(value)
    return player_facing_effect(text, replacements or []) if text else ""


def image_reference(record: dict, *extra_fields: str) -> str:
    for field in (
        *extra_fields,
        "icon",
        "icon_path",
        "big_icon_path",
        "forge_icon",
        "pal_icon",
        "skill_icon",
        "share_big_icon",
    ):
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def item_type_name(item: dict, translate: Translator) -> str:
    return translate(item.get("item_type_name") or item.get("type_name")).strip()


def item_subtype(item: dict) -> int:
    return as_int(item.get("sub_type", item.get("subtype")))


def normalized_item(item_id: object, item: dict, translate: Translator) -> dict:
    quality_code = as_int(item.get("quality"))
    return {
        "item_id": as_int(item_id, first_int(item_id)),
        "name": translated_text(translate, item.get("name")),
        "description": translated_text(
            translate,
            item.get("short_desc") or item.get("description") or item.get("desc"),
        ),
        "item_type": item_type_name(item, translate),
        "item_type_code": as_int(item.get("type")),
        "subtype_code": item_subtype(item),
        "quality_code": quality_code,
        "quality": QUALITY_NAMES.get(quality_code, "Unknown"),
        "max_stack": as_int(item.get("stack_num") or item.get("max_stack") or item.get("pile_limit")),
        "weight": item.get("weight"),
        "gain_path": translated_text(translate, item.get("gain_path")),
        "image_reference": image_reference(item),
    }


def source_block(base: Path, current: Path, translations: dict) -> dict:
    return {
        "base_snapshot": source_summary(base / "snapshot.json"),
        "current_snapshot": source_summary(current / "snapshot.json"),
        "primary_evidence": "Installed Once Human game snapshot",
        "english_translation_entries": len(translations),
        "merge_rule": "Current patch rows override matching base rows; base-only rows remain",
    }


def write_dataset(
    output_dir: Path,
    filename: str,
    collection: str,
    records: list,
    source: dict,
    extra_counts: dict | None = None,
    extra: dict | None = None,
) -> dict:
    records.sort(
        key=lambda row: (
            str(row.get("name") or row.get("track") or row.get("id") or "").casefold(),
            str(row.get("item_id") or row.get("id") or row.get("key") or ""),
        )
    )
    payload = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "record_counts": {collection: len(records), **(extra_counts or {})},
        collection: records,
        "review_queue": [],
    }
    if extra:
        payload.update(extra)
    path = output_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"file": str(path), "record_counts": payload["record_counts"]}


def build_mods(base: Path, current: Path, items: dict, translate: Translator) -> list:
    item_map = merged_table(base, current, f"{GAME_DATA}/new_mod_item_data.json")
    properties = merged_table(base, current, f"{GAME_DATA}/new_mod_property_data.json")
    entries = merged_table(base, current, f"{GAME_DATA}/mod_entry_data.json")
    entries_by_number: dict[int, list] = defaultdict(list)
    for key, entry in entries.items():
        parts = [as_int(part) for part in key_parts(key) if part.lstrip("-").isdigit()]
        if parts:
            entries_by_number[parts[0]].append((parts[1] if len(parts) > 1 else 0, entry))

    records = []
    for item_id, link in item_map.items():
        item = items.get(str(item_id), {})
        mod_code = as_int(link.get("mod_code"))
        prop = properties.get(str(mod_code), {})
        if not item and not prop:
            continue
        record = normalized_item(item_id, item, translate)
        record.update(
            {
                "id": mod_code,
                "mod_code": mod_code,
                "name": record["name"] or translated_text(translate, prop.get("mod_name")),
                "apply_range_code": as_int(prop.get("apply_range")),
                "genre_library_code": as_int(prop.get("genre_lib")),
                "frame_code": as_int(prop.get("frame")),
                "main_entry_code": as_int(prop.get("main_entry_no")),
                "is_shiny": bool(prop.get("is_shiny_mod")),
                "shiny_buff_id": as_int(prop.get("shiny_buff_id")),
                "shiny_replacement_mod_code": as_int(prop.get("shiny_replace_mod_code")),
            }
        )
        main_entry = as_int(prop.get("main_entry_no"))
        effects = []
        for level, entry in sorted(entries_by_number.get(main_entry, [])):
            effects.append(
                {
                    "level": level,
                    "name": translated_text(translate, entry.get("name"), entry.get("name_replace")),
                    "description": translated_text(translate, entry.get("desc"), entry.get("desc_replace")),
                    "attribute_codes": entry.get("attr_no_list", []),
                    "attribute_values": entry.get("attr_value_list", []),
                    "buff_id": as_int(entry.get("buff_id")),
                    "image_reference": image_reference(entry),
                }
            )
        record["main_entry_effects"] = effects
        records.append(record)
    return records


def build_calibrations(base: Path, current: Path, items: dict, translate: Translator) -> list:
    prints = merged_table(base, current, f"{GAME_DATA}/gun_correct_print_data.json")
    terms = merged_table(base, current, f"{GAME_DATA}/gun_correct_common_terms_data.json")
    records = []
    for item_id, item in items.items():
        if item_subtype(item) != 39:
            continue
        record = normalized_item(item_id, item, translate)
        rule = prints.get(str(item_id), {})
        affix_ids = [as_int(value) for value in rule.get("affix_ids", [])]
        record.update(
            {
                "id": record["item_id"],
                "weapon_type_codes": rule.get("weapon_type_lst", []),
                "calibration_style_code": as_int(rule.get("correct_style")),
                "group_id": as_int(rule.get("group_id")),
                "buff_id": rule.get("buff_id"),
                "season_state": rule.get("season_state"),
                "is_valid": bool(rule.get("is_valid", True)),
                # Current calibration blueprints carry a rarity-wide RNG value
                # range in gun_correct_print_data.affix_val_range. Preserve it
                # verbatim and expose a percent-normalized view without assuming
                # what combat stat it ultimately scales; PYC consumer tracing
                # determines that separately.
                "affix_val_range": rule.get("affix_val_range", []),
                "affix_ids_weight": rule.get("affix_ids_weight", []),
                "calibration_roll_range": {
                    "raw_minimum": (rule.get("affix_val_range") or [None, None])[0] if len(rule.get("affix_val_range") or []) > 0 else None,
                    "raw_maximum": (rule.get("affix_val_range") or [None, None])[1] if len(rule.get("affix_val_range") or []) > 1 else None,
                    "minimum_percent": ((rule.get("affix_val_range") or [None])[0] * 100) if len(rule.get("affix_val_range") or []) > 0 and isinstance((rule.get("affix_val_range") or [None])[0], (int, float)) else None,
                    "maximum_percent": ((rule.get("affix_val_range") or [None, None])[1] * 100) if len(rule.get("affix_val_range") or []) > 1 and isinstance((rule.get("affix_val_range") or [None, None])[1], (int, float)) else None,
                    "source_table": f"{GAME_DATA}/gun_correct_print_data.json",
                    "source_field": "affix_val_range",
                    "semantics_status": "range-proven-combat-application-under-investigation",
                },
                "affix_ids": affix_ids,
                "affixes": [
                    {"affix_id": affix_id, **normalize_scalar(terms.get(str(affix_id), {}), translate)}
                    for affix_id in affix_ids
                ],
            }
        )
        records.append(record)
    return records


def build_ammo(items: dict, translate: Translator) -> list:
    records = []
    for item_id, item in items.items():
        type_name = item_type_name(item, translate).casefold()
        if type_name != "ammo" and item_subtype(item) not in {9, 25}:
            continue
        record = normalized_item(item_id, item, translate)
        record["id"] = record["item_id"]
        record["ammo_parameters"] = {
            key: normalize_scalar(value, translate)
            for key, value in item.items()
            if any(token in key.casefold() for token in ("damage", "bullet", "ammo", "penetr", "element"))
        }
        records.append(record)
    return records


def build_attachments(base: Path, current: Path, items: dict, translate: Translator) -> list:
    mapping = merged_table(base, current, f"{GAME_DATA}/gun_accessory_item_to_accessory_map_data.json")
    params = merged_table(base, current, f"{GAME_DATA}/gun_accessory_base_params_data.json")
    attributes = merged_table(base, current, f"{GAME_DATA}/gun_accessory_attr_data.json")
    records = []
    seen_accessories = set()
    for item_id, link in mapping.items():
        item = items.get(str(item_id), {})
        subtype = item_subtype(item)
        accessory_code = str(link.get("accessory_no") or link.get("accessory_id") or "")
        if not accessory_code or accessory_code in seen_accessories:
            continue
        seen_accessories.add(accessory_code)
        param = params.get(accessory_code, {})
        affix_code = str(param.get("affix_name") or "")
        affix = attributes.get(affix_code, {})
        record = normalized_item(item_id, item, translate)
        record.update(
            {
                "id": accessory_code,
                "accessory_code": accessory_code,
                "attachment_type": ATTACHMENT_TYPES.get(subtype, "Weapon Attachment"),
                "name": record["name"] or translated_text(translate, param.get("name")),
                "quality_code": as_int(param.get("quality"), record["quality_code"]),
                "affix_code": affix_code,
                "effects": translated_text(translate, affix.get("affix_desc_list")),
                "attribute_codes": affix.get("affix_list_new") or affix.get("affix_list") or [],
                "passive_buff_id": as_int(affix.get("passive_buff_id")),
                "compatible_weapon_types": param.get("weapon_type_list") or param.get("gun_type_list") or [],
                "image_reference": image_reference(item) or image_reference(param),
            }
        )
        record["quality"] = QUALITY_NAMES.get(record["quality_code"], "Unknown")
        records.append(record)
    return records


def build_cradles(base: Path, current: Path, translate: Translator) -> list:
    entries = merged_table(base, current, f"{GAME_DATA}/cradle_override_entry_data.json")
    records = []
    for entry_id, entry in entries.items():
        records.append(
            {
                "id": first_int(entry_id),
                "name": translated_text(translate, entry.get("name")),
                "description": translated_text(translate, entry.get("desc"), entry.get("desc_replace")),
                "buff_id": as_int(entry.get("buff_id")),
                "keyword_id": as_int(entry.get("key_word_no")),
                "style_code": as_int(entry.get("style_no")),
                "attribute_codes": entry.get("attr_no_list", []),
                "attribute_values": entry.get("attr_value_list", []),
                "image_reference": image_reference(entry),
                "selected_image_reference": entry.get("selected_icon_path", ""),
                "equipped_image_reference": entry.get("equip_icon_path", ""),
                "disabled_image_reference": entry.get("disable_icon_path", ""),
            }
        )
    return records


def build_deviations(base: Path, current: Path, translate: Translator) -> list:
    deviations = merged_table(base, current, f"{GAME_DATA}/deviation_base_data.json")
    skill_table = merged_table(base, current, f"{GAME_DATA}/deviation_skills_data.json")
    named_skills = {
        first_int(key): {
            "id": first_int(key),
            "name": translated_text(translate, row.get("skill_name")),
            "description": translated_text(translate, row.get("skill_info"), row.get("replace_list")),
            "image_reference": image_reference(row),
        }
        for key, row in skill_table.items()
    }
    records = []
    for deviation_id, row in deviations.items():
        embedded_skills = []
        names = row.get("skill_name_lst", [])
        descriptions = row.get("skill_info_lst", [])
        icons = row.get("skill_icon_lst", [])
        for index in range(max(len(names), len(descriptions), len(icons))):
            embedded_skills.append(
                {
                    "name": translated_text(translate, names[index]) if index < len(names) else "",
                    "description": translated_text(translate, descriptions[index]) if index < len(descriptions) else "",
                    "image_reference": icons[index] if index < len(icons) else "",
                }
            )
        records.append(
            {
                "id": first_int(deviation_id),
                "name": translated_text(translate, row.get("name")),
                "deviation_type_code": as_int(row.get("deviation_type")),
                "unit_id": row.get("unit_id"),
                "unit_type": row.get("unit_type"),
                "collection_value": row.get("collection_value"),
                "containment": {
                    "base": row.get("containment_base"),
                    "maximum": row.get("max_containment"),
                    "minimum_for_work": row.get("min_work_containment"),
                    "recovery": row.get("containment_recover_base"),
                },
                "mood": {
                    "base": row.get("mood_base"),
                    "maximum": row.get("max_mood"),
                    "recovery": row.get("mood_recover_base"),
                },
                "temperature": {
                    "base": row.get("base_temperature"),
                    "frostbite": row.get("frostbite_point"),
                    "heatstroke": row.get("heatstroke_point"),
                },
                "quality_coefficients": row.get("quality_dict", {}),
                "power_coefficients": row.get("deviation_degree_coe", {}),
                "balance_coefficients": row.get("balance_degree_coe", {}),
                "territory_effects": row.get("terr_effect_lst", []),
                "meme_ids": row.get("meme_ids", []),
                "skills": embedded_skills,
                "skill_catalog": [named_skills[skill_id] for skill_id in row.get("skill_ids", []) if skill_id in named_skills],
                "image_reference": image_reference(row),
            }
        )
    return records


def build_consumables(base: Path, current: Path, items: dict, translate: Translator) -> list:
    use_parameters = merged_table(base, current, f"{GAME_DATA}/item_use_para_data.json")
    accepted = {"food", "creative cuisine", "creative beverages", "beverages", "medicine", "consumable"}
    records = []
    for item_id, item in items.items():
        type_name = item_type_name(item, translate).casefold()
        if type_name not in accepted:
            continue
        record = normalized_item(item_id, item, translate)
        usage = use_parameters.get(str(item_id), {})
        record.update(
            {
                "id": record["item_id"],
                "decay_duration": item.get("duration") or item.get("decay_duration") or item.get("expired_time"),
                "use_function": usage.get("related_func"),
                "survival_values": {
                    key: value
                    for key, value in usage.items()
                    if any(token in key.casefold() for token in ("food", "water", "sanity", "health", "energy"))
                },
                "buff_effects": normalize_scalar(
                    usage.get("buff_effect_list") or usage.get("buff_list") or [], translate
                ),
                "use_parameters": normalize_scalar(usage, translate),
            }
        )
        records.append(record)
    return records


def build_buffs(base: Path, current: Path, translate: Translator) -> tuple[list, dict, list]:
    levels = merged_table(base, current, f"{GAME_DATA}/buff_level_data.json")
    definitions = merged_table(base, current, f"{GAME_DATA}/buff/buff_data.json")
    records = []
    by_id = defaultdict(list)
    for key, row in levels.items():
        parts = [as_int(part) for part in key_parts(key) if part.lstrip("-").isdigit()]
        # buff_level_data uses the current-client field names buff_template_id,
        # buff_lv and buff_desc.  Older normalizers only checked buff_id/level/desc,
        # which left Calibration Style names/descriptions blank even though the
        # localized source text was present in the mined table.
        buff_id = as_int(
            row.get("buff_id") or row.get("buff_template_id"),
            parts[0] if parts else 0,
        )
        level = as_int(
            row.get("level") or row.get("buff_lv"),
            parts[1] if len(parts) > 1 else 0,
        )
        name = translated_text(
            translate,
            row.get("name") or row.get("buff_name"),
            row.get("name_replace") or row.get("name_value"),
        )
        description = translated_text(
            translate,
            row.get("desc") or row.get("description") or row.get("buff_desc"),
            row.get("desc_replace") or row.get("desc_value"),
        )
        definition = definitions.get(str(buff_id), {})
        record = {
            "id": f"{buff_id}:{level}",
            "buff_id": buff_id,
            "level": level,
            "name": name,
            "description": description,
            "buff_type": translated_text(translate, row.get("buff_type")),
            "attribute_codes": row.get("attr_no_list", []),
            "attribute_values": row.get("attr_value_list", []),
            "tags": definition.get("tag_list") or definition.get("buff_tag_list") or row.get("tag_list") or [],
            "lifetime": definition.get("life_time") or definition.get("lifetime"),
            "maximum_stacks": definition.get("max_overlay") or definition.get("max_stack"),
            "visible_in_ui": row.get("show_in_ui", row.get("is_show", None)),
            "image_reference": image_reference(row),
        }
        records.append(record)
        by_id[buff_id].append(record)
    definition_records = [
        {
            "id": first_int(buff_id),
            "name": "",
            "image_reference": image_reference(row),
            "game_definition": normalize_scalar(row, translate),
        }
        for buff_id, row in definitions.items()
    ]
    return records, by_id, definition_records


def build_keywords_and_statuses(
    base: Path,
    current: Path,
    translate: Translator,
    passive_skills: dict,
    buffs_by_id: dict,
) -> tuple[list, list]:
    tags = merged_table(base, current, f"{GAME_DATA}/buff_tag_data.json")
    status_tips = merged_table(base, current, f"{GAME_DATA}/survival_ui_status_tips_text.json")
    keyword_refs = defaultdict(list)
    status_refs = defaultdict(list)
    for skill_id, row in passive_skills.items():
        skill_name = translated_text(translate, row.get("name"))
        keyword_id = as_int(row.get("keyword_buff_id"))
        status_id = as_int(row.get("keyword_status_id"))
        ref = {"skill_id": str(skill_id), "skill_name": skill_name}
        if keyword_id:
            keyword_refs[keyword_id].append(ref)
        if status_id:
            status_refs[status_id].append(ref)

    keywords = []
    statuses = []
    for tag_id_text, row in tags.items():
        tag_id = first_int(tag_id_text)
        keyword_buff_id = as_int(row.get("buff"))
        normalized = {
            "id": tag_id,
            "buff_id": keyword_buff_id,
            "name": translated_text(translate, row.get("chs_name") or row.get("name")),
            "description": translated_text(translate, row.get("simp_desc") or row.get("tag_des")),
            "is_keyword": bool(row.get("is_keyword")) or keyword_buff_id in keyword_refs,
            "is_debuff": bool(row.get("is_debuff")),
            "tag_type": row.get("tag_type"),
            "suffix": row.get("suffix_debuff_name"),
            "parent_tags": row.get("upper_tag", []),
            "cancelled_tags": row.get("cancel_list", []),
            "immune_tags": row.get("immunity_list", []),
            "related_skills": keyword_refs.get(keyword_buff_id, []) + status_refs.get(tag_id, []),
            "related_buffs": [
                {"buff_id": buff_id, "levels": len(level_rows)}
                for buff_id, level_rows in buffs_by_id.items()
                if buff_id == keyword_buff_id or tag_id in (level_rows[0].get("tags") or [])
            ],
        }
        if normalized["is_keyword"]:
            keywords.append(dict(normalized))
        if normalized["is_debuff"] or tag_id in status_refs:
            statuses.append(dict(normalized))

    known_status_ids = {row["id"] for row in statuses}
    for status_id, refs in status_refs.items():
        if status_id not in known_status_ids:
            statuses.append(
                {
                    "id": status_id,
                    "name": "",
                    "description": "",
                    "is_keyword": False,
                    "is_debuff": False,
                    "related_skills": refs,
                    "verification_needed": True,
                }
            )
    for tip_id, row in status_tips.items():
        statuses.append(
            {
                "id": f"survival-tip:{tip_id}",
                "name": translated_text(translate, row.get("title") or row.get("name")),
                "description": translated_text(translate, row.get("text") or row.get("desc")),
                "status_attributes": normalize_scalar(row, translate),
                "source_type": "survival-ui-tip",
            }
        )
    return keywords, statuses


def build_skills(base: Path, current: Path, translate: Translator) -> list:
    records = []
    seen = set()
    for source_name, filename in SKILL_SOURCES:
        rows = merged_table(base, current, f"{GAME_DATA}/{filename}")
        for skill_id, row in rows.items():
            key = (source_name, str(skill_id))
            if key in seen:
                continue
            seen.add(key)
            name = translated_text(translate, row.get("name") or row.get("skill_name"))
            description = translated_text(
                translate,
                row.get("desc") or row.get("skill_info") or row.get("description"),
                row.get("desc_replace") or row.get("replace_list"),
            )
            records.append(
                {
                    "id": f"{source_name}:{skill_id}",
                    "source_type": source_name,
                    "game_id": str(skill_id),
                    "name": name,
                    "description": description,
                    "skill_type": translated_text(translate, row.get("skill_func_type")),
                    "skill_tip": translated_text(translate, row.get("skill_tip")),
                    "rarity_code": as_int(row.get("rare")),
                    "buff_id": as_int(row.get("buff_id")),
                    "keyword_buff_id": as_int(row.get("keyword_buff_id")),
                    "keyword_status_id": as_int(row.get("keyword_status_id")),
                    "image_reference": image_reference(row, "icons"),
                    "parameters": {
                        key: normalize_scalar(value, translate)
                        for key, value in row.items()
                        if key.endswith("_params_list") or key in {"cost", "type", "ability_type", "active_type"}
                    },
                    "game_definition": normalize_scalar(row, translate),
                }
            )
    return records


def build_stat_definitions(base: Path, current: Path, translate: Translator) -> list:
    rows = merged_table(base, current, f"{GAME_DATA}/char_property_data.json")
    records = []
    for key, row in rows.items():
        records.append(
            {
                "id": str(row.get("attr_id") or key),
                "key": str(key),
                "name": translated_text(translate, row.get("attr_chs_name") or row.get("name")),
                "calculation_type": row.get("calc_type"),
                "entity_type": row.get("ent_type"),
                "value_type": row.get("val_type"),
                "initial_value": row.get("init_val"),
                "minimum_value": row.get("min_val"),
                "maximum_value": row.get("max_val"),
                "parent_stat": row.get("parent_attr") or row.get("parent"),
                "game_definition": normalize_scalar(row, translate),
            }
        )
    return records


def build_progression(base: Path, current: Path, translate: Translator) -> tuple[list, dict]:
    records = []
    track_counts = Counter()
    for track, filename in PROGRESSION_SOURCES:
        rows = merged_table(base, current, f"{GAME_DATA}/{filename}")
        track_counts[track] = len(rows)
        for key, row in rows.items():
            records.append(
                {
                    "id": f"{track}:{key}",
                    "track": track,
                    "level_key": str(key),
                    "level": as_int(row.get("level") or row.get("lv"), first_int(key)),
                    "experience_required": row.get("exp_need") or row.get("need_exp") or row.get("exp"),
                    "game_definition": normalize_scalar(row, translate),
                }
            )
    return records, dict(sorted(track_counts.items()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    translations = {}
    base_translation = args.base / "translate/translate_data_en.json"
    if base_translation.exists():
        translations.update(translation_entries(base_translation))
    for path in sorted((args.current / "translate").glob("translate_data_en*.json")):
        translations.update(translation_entries(path))
    translate = Translator(translations)
    source = source_block(args.base, args.current, translations)
    items = merged_table(args.base, args.current, f"{GAME_DATA}/item_data.json")
    passive_skills = merged_table(args.base, args.current, f"{GAME_DATA}/passive_skill_data.json")

    buffs, buffs_by_id, buff_definitions = build_buffs(args.base, args.current, translate)
    keywords, statuses = build_keywords_and_statuses(
        args.base, args.current, translate, passive_skills, buffs_by_id
    )
    progression, progression_tracks = build_progression(args.base, args.current, translate)

    outputs = {
        "mods": write_dataset(args.output_dir, "mods.json", "mods", build_mods(args.base, args.current, items, translate), source),
        "calibrations": write_dataset(args.output_dir, "calibrations.json", "calibrations", build_calibrations(args.base, args.current, items, translate), source),
        "ammo": write_dataset(args.output_dir, "ammo.json", "ammo", build_ammo(items, translate), source),
        "attachments": write_dataset(args.output_dir, "attachments.json", "attachments", build_attachments(args.base, args.current, items, translate), source),
        "cradles": write_dataset(args.output_dir, "cradles.json", "cradles", build_cradles(args.base, args.current, translate), source),
        "deviations": write_dataset(args.output_dir, "deviations.json", "deviations", build_deviations(args.base, args.current, translate), source),
        "consumables": write_dataset(args.output_dir, "consumables.json", "consumables", build_consumables(args.base, args.current, items, translate), source),
        "buffs": write_dataset(
            args.output_dir,
            "buffs.json",
            "buffs",
            buffs,
            source,
            {"buff_definitions": len(buff_definitions)},
            {"buff_definitions": buff_definitions},
        ),
        "statuses": write_dataset(args.output_dir, "statuses.json", "statuses", statuses, source),
        "keywords": write_dataset(args.output_dir, "keywords.json", "keywords", keywords, source),
        "skills": write_dataset(args.output_dir, "skills.json", "skills", build_skills(args.base, args.current, translate), source),
        "stat_definitions": write_dataset(args.output_dir, "stat-definitions.json", "stat_definitions", build_stat_definitions(args.base, args.current, translate), source),
        "progression": write_dataset(args.output_dir, "progression.json", "progression", progression, source, {"tracks": progression_tracks}),
    }
    print(json.dumps(outputs, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
