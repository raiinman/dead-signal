"""Build website-ready armor set records from mined Once Human tables."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


SLOT_NAMES = {
    21: "Helmet",
    22: "Top",
    23: "Pants",
    24: "Shoes",
    25: "Gloves",
    27: "Mask",
}
QUALITY_NAMES = {
    1: "Common",
    2: "Rare",
    3: "Epic",
    4: "Legendary",
    5: "Mythic",
}
CURRENT_RECIPE_SERVER_NO = 222
MARKER = re.compile(r"_\$S@TIDS\$_[^|]+\|[0-9a-z]+$", re.IGNORECASE)
DISPLAY_TAG = re.compile(
    r"#E\([^)]*\)|#\[[^]]+\]|#(?:e|l)|#\d+#",
    re.IGNORECASE,
)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as source:
        return json.load(source)


def table(path: Path):
    return load_json(path).get("data", {})


def load_first_table(*paths: Path):
    for path in paths:
        if path.exists():
            return table(path)
    return {}


def translation_entries(path: Path):
    payload = load_json(path)
    merged = {}
    for value in payload.values():
        if isinstance(value, dict):
            merged.update(value)
    return merged


class Translator:
    def __init__(self, translations):
        self.translations = translations
        self.misses = set()

    @staticmethod
    def raw(value) -> str:
        if isinstance(value, dict):
            value = value.get("lan_translate", [""])
        if isinstance(value, list):
            value = value[0] if value else ""
        return value if isinstance(value, str) else str(value or "")

    def __call__(self, value) -> str:
        raw = self.raw(value)
        if not raw or raw == "0":
            return ""
        stripped = MARKER.sub("", raw)
        for candidate in (raw, stripped):
            translated = self.translations.get(candidate)
            if isinstance(translated, str) and translated:
                return translated
        self.misses.add(stripped)
        return stripped


def source_summary(snapshot_path: Path):
    snapshot = load_json(snapshot_path)
    return {
        "archive": snapshot.get("archive"),
        "archive_size": snapshot.get("archive_size"),
        "archive_sha256": snapshot.get("archive_sha256"),
        "archive_modified_utc": snapshot.get("archive_modified_utc"),
        "scanned_pyc_files": snapshot.get("scanned_pyc_files"),
        "exported_tables": snapshot.get("exported_tables"),
        "parse_errors": snapshot.get("parse_errors"),
    }


def player_facing_effect(description: str, values) -> str:
    """Resolve game placeholders and remove its UI-only rich-text markers."""
    for index, value in enumerate(values or [], start=1):
        description = description.replace("{" + str(index) + "}", str(value))
    description = description.replace("#[/u]", " ")
    description = DISPLAY_TAG.sub("", description)
    description = description.replace("{param}", "")
    description = description.replace("++", "+")
    description = re.sub(r"\n\s*\.\s*", ". ", description)
    description = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", description)
    description = re.sub(r"(?<=%)(?=[A-Za-z])", " ", description)
    description = re.sub(
        r"(?<=\d)(?=(?:bullet|shot|stack|time)\b)",
        " ",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(r"\b1 more times\b", "1 more time", description)
    description = re.sub(r"\b1 times\b", "1 time", description)
    description = description.replace(
        "Unstable Bomber 1 trigger point",
        "Unstable Bomber trigger point",
    )
    description = re.sub(r"[ \t]+", " ", description)
    description = re.sub(r"\s+([,.;:!?])", r"\1", description)
    description = re.sub(r" *\n *", "\n", description)
    return description.strip()


def crafting_group_label(group_id: int) -> str:
    if 8000 <= group_id < 9000:
        slot_index = (group_id // 10) % 10
        slot_names = {
            1: "Helmet material",
            2: "Top material",
            3: "Pants material",
            4: "Shoes material",
            5: "Gloves material",
            6: "Mask material",
        }
        return slot_names.get(slot_index, "Armor material")
    if 9300 <= group_id < 9400:
        return "Climate material"
    if 9400 <= group_id < 9500:
        return "Fiber material"
    if 950 <= group_id < 1000:
        return "Gene fabric"
    return "Selectable material"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    base = args.base
    current = args.current
    equip = table(current / "game_common/data/equip_data.json")
    items = table(current / "game_common/data/item_data.json")
    origins = load_first_table(
        current / "game_common/data/equip_origin_data.json",
        base / "game_common/data/equip_origin_data.json",
    )
    char_properties = load_first_table(
        current / "game_common/data/char_property_data.json",
        base / "game_common/data/char_property_data.json",
    )
    suits = table(base / "game_common/data/suit_data.json")
    blueprints = table(base / "game_common/data/equip_blueprint_data.json")
    blueprint_attributes = table(
        base / "game_common/data/equip_blueprint_attr_data.json"
    )
    passive_skills = table(base / "game_common/data/passive_skill_data.json")
    buff_levels = load_first_table(
        current / "game_common/data/buff_level_data.json",
        base / "game_common/data/buff_level_data.json",
    )
    forge_data = table(base / "game_common/data/forge_data.json")
    current_choice_materials = current / "game_common/data/forge_choice_material_data.json"
    if current_choice_materials.exists():
        choice_materials = table(current_choice_materials)
    else:
        choice_materials = table(base / "game_common/data/forge_choice_material_data.json")
    money_materials = table(base / "game_common/data/money_material_data.json")

    translations = {}
    base_translation = base / "translate/translate_data_en.json"
    if base_translation.exists():
        translations.update(translation_entries(base_translation))
    for path in sorted((current / "translate").glob("translate_data_en*.json")):
        translations.update(translation_entries(path))
    translate = Translator(translations)

    crafting_groups = {}
    choice_options = defaultdict(dict)
    for record in choice_materials.values():
        group_id = int(record.get("identity") or 0)
        item_id = int(record.get("item_id") or 0)
        base_quantity = int(record.get("item_num") or 0)
        item = items.get(str(item_id), {})
        name = translate(item.get("name")) if item else ""
        if not group_id or not item_id or not base_quantity or not name:
            continue
        option_key = (item_id, base_quantity)
        option = choice_options[group_id].get(option_key)
        if not option:
            option = {
                "item_id": item_id,
                "name": name,
                "base_quantity": base_quantity,
                "icon": item.get("icon", ""),
                "quality_code": int(item.get("quality") or 0),
                "quality": QUALITY_NAMES.get(int(item.get("quality") or 0), "Common"),
                "plain_option": False,
                "has_material_effect": False,
                "effects": [],
            }
            choice_options[group_id][option_key] = option
        effect_types = [int(value) for value in record.get("effect_type_list", [])]
        option["plain_option"] = option["plain_option"] or not effect_types
        if effect_types:
            effect_name = player_facing_effect(
                translate(record.get("effect_desc")), []
            )
            effect_description = player_facing_effect(
                translate(record.get("describe")), []
            )
            effect = {
                "name": effect_name or "Material effect",
                "description": effect_description or effect_name,
                "type_codes": effect_types,
            }
            effect_signature = (
                effect["name"],
                effect["description"],
                tuple(effect["type_codes"]),
            )
            existing_signatures = {
                (
                    existing.get("name", ""),
                    existing.get("description", ""),
                    tuple(existing.get("type_codes", [])),
                )
                for existing in option["effects"]
            }
            if effect_signature not in existing_signatures:
                option["effects"].append(effect)
        option["has_material_effect"] = bool(option["effects"])

    for group_id, options_by_key in choice_options.items():
        options = sorted(
            options_by_key.values(),
            key=lambda option: (
                not option["plain_option"],
                option["name"].casefold(),
                option["item_id"],
            ),
        )
        crafting_groups[str(group_id)] = {
            "group_id": group_id,
            "label": crafting_group_label(group_id),
            "option_count": len(options),
            "options": options,
        }

    currency_names = {}
    for currency_id, record in money_materials.items():
        currency_names[str(currency_id)] = {
            "name": translate(record.get("name")),
            "icon": record.get("item_icon") or record.get("icon", ""),
        }

    used_crafting_group_ids = set()
    recipe_review_queue = []

    def crafting_recipes_for_blueprint(blueprint_id: int, item_name: str):
        blueprint = blueprints.get(str(blueprint_id), {})
        levels = blueprint.get("corr_forge_lv", [])
        forge_numbers = blueprint.get("corr_forge_no", [])
        recipes = []
        if not blueprint or not levels or not forge_numbers:
            recipe_review_queue.append(
                {
                    "blueprint_id": blueprint_id,
                    "name": item_name,
                    "reason": "No armor crafting recipe series resolved for this blueprint",
                }
            )
            return recipes

        for level, forge_no in zip(levels, forge_numbers):
            current_key = f"({int(forge_no)}, {CURRENT_RECIPE_SERVER_NO})"
            forge = forge_data.get(current_key) or forge_data.get(str(forge_no), {})
            if not forge:
                recipe_review_queue.append(
                    {
                        "blueprint_id": blueprint_id,
                        "name": item_name,
                        "reason": f"Forge recipe {forge_no} was not present",
                    }
                )
                continue

            fixed_materials = {}
            material_group_multipliers = {}
            unresolved_costs = []
            for cost_item_id, quantity in zip(
                forge.get("cost_item_list", []),
                forge.get("cost_num_list", []),
            ):
                cost_item_id = int(cost_item_id)
                quantity = int(quantity)
                group = crafting_groups.get(str(cost_item_id))
                if group:
                    used_crafting_group_ids.add(cost_item_id)
                    material_group_multipliers[cost_item_id] = (
                        material_group_multipliers.get(cost_item_id, 0) + quantity
                    )
                    continue

                item = items.get(str(cost_item_id), {})
                material_name = translate(item.get("name")) if item else ""
                if not item or not material_name:
                    unresolved_costs.append(cost_item_id)
                    continue
                if cost_item_id not in fixed_materials:
                    fixed_materials[cost_item_id] = {
                        "item_id": cost_item_id,
                        "name": material_name,
                        "quantity": 0,
                        "icon": item.get("icon", ""),
                        "quality_code": int(item.get("quality") or 0),
                        "quality": QUALITY_NAMES.get(
                            int(item.get("quality") or 0), "Common"
                        ),
                    }
                fixed_materials[cost_item_id]["quantity"] += quantity

            if unresolved_costs:
                recipe_review_queue.append(
                    {
                        "blueprint_id": blueprint_id,
                        "name": item_name,
                        "reason": f"Recipe {forge_no} contains unresolved material identifiers",
                        "item_ids": sorted(set(unresolved_costs)),
                    }
                )

            material_groups = []
            for group_id, multiplier in material_group_multipliers.items():
                group = crafting_groups[str(group_id)]
                plain_options = [
                    option for option in group["options"] if option["plain_option"]
                ]
                example = plain_options[0] if plain_options else group["options"][0]
                material_groups.append(
                    {
                        "group_id": group_id,
                        "label": group["label"],
                        "multiplier": multiplier,
                        "option_count": group["option_count"],
                        "plain_example": {
                            "item_id": example["item_id"],
                            "name": example["name"],
                            "quantity": example["base_quantity"] * multiplier,
                        },
                    }
                )

            currency_id = int(forge.get("cost_money_no") or 0)
            currency = currency_names.get(str(currency_id), {})
            recipes.append(
                {
                    "tier": int(level),
                    "tier_label": f"Tier {int(level)}",
                    "forge_no": int(forge_no),
                    "recipe_key": current_key if current_key in forge_data else str(forge_no),
                    "recipe_server_no": CURRENT_RECIPE_SERVER_NO
                    if current_key in forge_data
                    else 0,
                    "output_item_id": int(forge.get("item_no") or 0),
                    "fixed_materials": list(fixed_materials.values()),
                    "material_groups": material_groups,
                    "currency": {
                        "currency_id": currency_id,
                        "name": currency.get("name", "Currency"),
                        "quantity": int(forge.get("cost_money_num") or 0),
                        "icon": currency.get("icon", ""),
                    },
                    "craft_time_seconds": int(forge.get("seconds") or 0),
                    "source_status": "mined-current-recipe-layer",
                }
            )
        return recipes

    attr_labels = {}
    for property_key, record in char_properties.items():
        attr_id = record.get("attr_id")
        if not attr_id:
            continue
        attr_labels[attr_id] = {
            "key": property_key,
            "label": translate(record.get("attr_chs_name")),
        }

    by_suit = defaultdict(list)
    for item_id, record in equip.items():
        suit_id = int(record.get("suit_id") or 0)
        equip_type = int(record.get("equip_type") or 0)
        if suit_id and equip_type in SLOT_NAMES:
            by_suit[str(suit_id)].append((item_id, record))

    normalized_sets = []
    review_queue = []
    for suit_id, suit in suits.items():
        equipment = by_suit.get(suit_id, [])
        if not equipment:
            continue

        bonuses = []
        needs = suit.get("affix_need_num_list", [])
        codes = suit.get("affix_name_list", [])
        values = suit.get("affix_val_list", [])
        descriptions = suit.get("affix_suit_value_list", [])
        buffs = suit.get("buff_info_list", [])
        for index, needed in enumerate(needs):
            if not needed:
                continue
            description = translate(descriptions[index] if index < len(descriptions) else "")
            code = codes[index] if index < len(codes) else ""
            buff_info = buffs[index] if index < len(buffs) else []
            value = values[index] if index < len(values) else 0
            if not (description or code or buff_info):
                continue
            bonuses.append(
                {
                    "pieces_required": needed,
                    "description": description,
                    "attribute_code": code,
                    "attribute_value": value,
                    "buff_info": buff_info,
                }
            )

        pieces_by_slot = defaultdict(list)
        variants_to_review = []
        for item_id, record in equipment:
            art_level = int(record.get("art_lv") or 0)
            item_suffix = int(item_id[-2:]) if item_id[-2:].isdigit() else -1
            canonical = (
                int(record.get("equip_lv") or 0) == 1
                and 1 <= art_level <= 5
                and item_suffix == art_level
            )
            if not canonical:
                if art_level == 6 and item_suffix == 6:
                    variants_to_review.append(item_id)
                continue

            item = items.get(item_id, {})
            origin_id = str(record.get("equip_origin_id") or item_id)
            origin = origins.get(origin_id, {})
            codes_for_item = origin.get("base_attr_name_list", [])
            values_for_item = origin.get("base_attr_val_list", [])
            attributes = []
            for code, value in zip(codes_for_item, values_for_item):
                short_code = code[:3]
                label = attr_labels.get(short_code, {})
                attributes.append(
                    {
                        "code": code,
                        "key": label.get("key", ""),
                        "label": label.get("label", code),
                        "value": value,
                    }
                )

            pieces_by_slot[int(record["equip_type"])].append(
                {
                    "item_id": int(item_id),
                    "data_level": art_level,
                    "tier_label": f"Tier {art_level}",
                    "hp": next((x["value"] for x in attributes if x["code"] == "A0200"), None),
                    "pollution_resistance": next(
                        (x["value"] for x in attributes if x["code"] == "R3600"), None
                    ),
                    "psi_intensity": next(
                        (x["value"] for x in attributes if x["code"] == "D4100"), None
                    ),
                    "attributes": attributes,
                    "durability": item.get("durability"),
                    "weight": item.get("weight"),
                    "icon": item.get("icon", ""),
                    "forge_icon": item.get("forge_icon", ""),
                    "blueprint_id": record.get("blueprint_no"),
                }
            )

        pieces = []
        for slot_id in SLOT_NAMES:
            tiers = sorted(pieces_by_slot.get(slot_id, []), key=lambda item: item["data_level"])
            if not tiers:
                continue
            tier_one_item = items.get(str(tiers[0]["item_id"]), {})
            piece_name = translate(tier_one_item.get("name"))
            blueprint_id = int(tiers[0].get("blueprint_id") or 0)
            pieces.append(
                {
                    "slot_id": slot_id,
                    "slot": SLOT_NAMES[slot_id],
                    "name": piece_name,
                    "quality_code": next(
                        (
                            record.get("equip_quality")
                            for item_id, record in equipment
                            if item_id == str(tiers[0]["item_id"])
                        ),
                        None,
                    ),
                    "quality": QUALITY_NAMES.get(
                        next(
                            (
                                record.get("equip_quality")
                                for item_id, record in equipment
                                if item_id == str(tiers[0]["item_id"])
                            ),
                            None,
                        ),
                        "Unknown",
                    ),
                    "tiers": tiers,
                    "crafting_recipes": crafting_recipes_for_blueprint(
                        blueprint_id, piece_name
                    ),
                }
            )

        set_name = translate(suit.get("suit_name"))
        if not pieces:
            review_queue.append(
                {
                    "suit_id": int(suit_id),
                    "name": set_name,
                    "reason": "Internal or alternate set record has no canonical Tier I-V pieces",
                    "item_ids": sorted(int(item_id) for item_id, _ in equipment),
                }
            )
            continue
        record = {
            "suit_id": int(suit_id),
            "name": set_name,
            "icon": suit.get("suit_icon", ""),
            "piece_count": len(pieces),
            "set_bonuses": bonuses,
            "pieces": pieces,
            "source_status": "mined-from-installed-game",
            "in_game_verification_needed": True,
            "verification_notes": [
                "Confirm the set is currently obtainable in the live scenario.",
                "Confirm that data levels 1-5 correspond to the displayed Tier I-V labels.",
            ],
        }
        if variants_to_review:
            record["verification_notes"].append(
                "The files contain data-level-6 variants; confirm whether players can obtain them."
            )
            review_queue.append(
                {
                    "suit_id": int(suit_id),
                    "name": set_name,
                    "reason": "Data-level-6 armor variants exist",
                    "item_ids": sorted(int(value) for value in variants_to_review),
                }
            )
        normalized_sets.append(record)

    standalone_groups = defaultdict(list)
    for item_id, record in equip.items():
        equip_type = int(record.get("equip_type") or 0)
        art_level = int(record.get("art_lv") or 0)
        item_suffix = int(item_id[-2:]) if item_id[-2:].isdigit() else -1
        blueprint_id = int(record.get("blueprint_no") or 0)
        canonical = (
            not int(record.get("suit_id") or 0)
            and equip_type in SLOT_NAMES
            and int(record.get("equip_lv") or 0) == 1
            and 1 <= art_level <= 5
            and item_suffix == art_level
            and blueprint_id > 0
        )
        if canonical:
            standalone_groups[str(blueprint_id)].append((item_id, record))

    key_armor = []
    for blueprint_id, equipment in standalone_groups.items():
        equipment.sort(key=lambda value: int(value[1].get("art_lv") or 0))
        first_item_id, first_record = equipment[0]
        first_item = items.get(first_item_id, {})
        slot_id = int(first_record.get("equip_type") or 0)
        tiers = []
        for item_id, record in equipment:
            item = items.get(item_id, {})
            origin_id = str(record.get("equip_origin_id") or item_id)
            origin = origins.get(origin_id, {})
            attributes = []
            for code, value in zip(
                origin.get("base_attr_name_list", []),
                origin.get("base_attr_val_list", []),
            ):
                short_code = code[:3]
                label = attr_labels.get(short_code, {})
                attributes.append(
                    {
                        "code": code,
                        "key": label.get("key", ""),
                        "label": label.get("label", code),
                        "value": value,
                    }
                )

            art_level = int(record.get("art_lv") or 0)
            tiers.append(
                {
                    "item_id": int(item_id),
                    "data_level": art_level,
                    "tier_label": f"Tier {art_level}",
                    "hp": next(
                        (x["value"] for x in attributes if x["code"] == "A0200"),
                        None,
                    ),
                    "pollution_resistance": next(
                        (x["value"] for x in attributes if x["code"] == "R3600"),
                        None,
                    ),
                    "psi_intensity": next(
                        (x["value"] for x in attributes if x["code"] == "D4100"),
                        None,
                    ),
                    "attributes": attributes,
                    "durability": item.get("durability"),
                    "weight": item.get("weight"),
                    "icon": item.get("icon", ""),
                    "forge_icon": item.get("forge_icon", ""),
                    "blueprint_id": record.get("blueprint_no"),
                }
            )

        blueprint = blueprint_attributes.get(f"({blueprint_id}, 1)", {})
        skill_code = blueprint.get("fixed_skill_code", "")
        skill = passive_skills.get(skill_code, {})
        buff_id = int(skill.get("buff_id") or 0)
        buff = buff_levels.get(f"({buff_id}, 1)", {}) if buff_id else {}
        effect = player_facing_effect(
            translate(buff.get("buff_desc")),
            buff.get("desc_value", []),
        )
        quality_code = int(first_item.get("quality") or first_record.get("equip_quality") or 0)
        name = translate(first_item.get("name"))
        verification_notes = [
            "Confirm this Key Armor is currently obtainable in the live scenario.",
            "Confirm the unique-effect wording and values against the current in-game tooltip.",
            "Confirm that data levels 1-5 correspond to the displayed Tier I-V labels.",
        ]
        if len(tiers) < 5:
            verification_notes.append(
                f"Only {len(tiers)} canonical tier rows were present in the current equipment table."
            )
            review_queue.append(
                {
                    "blueprint_id": int(blueprint_id),
                    "name": name,
                    "reason": "Canonical Tier I-V series is incomplete in the current equipment table",
                    "item_ids": [int(item["item_id"]) for item in tiers],
                }
            )
        if not skill_code or not effect:
            verification_notes.append(
                "The Key Armor passive-skill relationship or player-facing effect text needs manual review."
            )
            review_queue.append(
                {
                    "blueprint_id": int(blueprint_id),
                    "name": name,
                    "reason": "Key Armor passive-skill relationship did not fully resolve",
                    "item_ids": [int(item["item_id"]) for item in tiers],
                }
            )

        key_armor.append(
            {
                "classification": "Key Armor",
                "name": name,
                "slot_id": slot_id,
                "slot": SLOT_NAMES[slot_id],
                "quality_code": quality_code,
                "quality": QUALITY_NAMES.get(quality_code, "Unknown"),
                "blueprint_id": int(blueprint_id),
                "passive_skill_code": skill_code,
                "passive_skill_name": translate(skill.get("name")),
                "buff_id": buff_id,
                "key_effect": effect,
                "tiers": tiers,
                "crafting_recipes": crafting_recipes_for_blueprint(
                    int(blueprint_id), name
                ),
                "source_status": "mined-from-installed-game",
                "in_game_verification_needed": True,
                "verification_notes": verification_notes,
            }
        )

    normalized_sets.sort(key=lambda item: (item["name"].casefold(), item["suit_id"]))
    key_armor.sort(key=lambda item: (item["name"].casefold(), item["blueprint_id"]))
    set_piece_count = sum(item["piece_count"] for item in normalized_sets)
    set_tier_rows = sum(
        len(piece["tiers"])
        for item in normalized_sets
        for piece in item["pieces"]
    )
    key_tier_rows = sum(len(item["tiers"]) for item in key_armor)
    review_queue.extend(recipe_review_queue)
    used_crafting_groups = {
        str(group_id): crafting_groups[str(group_id)]
        for group_id in sorted(used_crafting_group_ids)
    }
    crafting_recipe_rows = sum(
        len(piece.get("crafting_recipes", []))
        for item in normalized_sets
        for piece in item["pieces"]
    ) + sum(len(item.get("crafting_recipes", [])) for item in key_armor)
    payload = {
        "schema_version": 4,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Current patch equipment and material-choice tables over base rules, including material effect text and the current server-222 direct-crafting recipe layer, joined to current English localization; no game code executed",
        "sources": {
            "base": source_summary(base / "snapshot.json"),
            "current_patch": source_summary(current / "snapshot.json"),
            "english_translation_entries": len(translations),
            "crafting_recipe_server_no": CURRENT_RECIPE_SERVER_NO,
            "crafting_system_version": "2.3.6+",
            "crafting_update_url": "https://www.oncehuman.game/m/news/update/20260408/40780_1295195.html",
        },
        "record_counts": {
            "armor_sets": len(normalized_sets),
            "armor_set_pieces": set_piece_count,
            "key_armor": len(key_armor),
            "armor_pieces": set_piece_count + len(key_armor),
            "set_tier_stat_rows": set_tier_rows,
            "key_armor_tier_stat_rows": key_tier_rows,
            "tier_stat_rows": set_tier_rows + key_tier_rows,
            "set_bonuses": sum(len(item["set_bonuses"]) for item in normalized_sets),
            "crafting_recipe_rows": crafting_recipe_rows,
            "crafting_material_groups": len(used_crafting_groups),
            "crafting_material_options": sum(
                group["option_count"] for group in used_crafting_groups.values()
            ),
            "crafting_material_effect_options": sum(
                1
                for group in used_crafting_groups.values()
                for option in group["options"]
                if option["has_material_effect"]
            ),
            "crafting_material_effects": sum(
                len(option["effects"])
                for group in used_crafting_groups.values()
                for option in group["options"]
            ),
            "translation_misses": len(translate.misses),
            "review_queue": len(review_queue),
        },
        "armor_sets": normalized_sets,
        "key_armor": key_armor,
        "crafting_material_groups": used_crafting_groups,
        "review_queue": review_queue,
        "translation_misses": sorted(translate.misses),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload["record_counts"], indent=2))
    print(f"Output: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
