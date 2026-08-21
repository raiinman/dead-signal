"""Normalize exact crafting recipes and material identities from Miner snapshots.

Recipe identity is the exact forge_data record. Cost identifiers are typed before
an edge is created: a cost may be an item_data material or a
forge_choice_material_data group identity. Bare numeric equality is never enough
to merge those two namespaces.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from normalize_armor import QUALITY_NAMES, Translator, player_facing_effect, source_summary, table, translation_entries

GAME_DATA = "game_common/data"
CLIENT_DATA = "client_data"
RECIPE_KEY = re.compile(r"^\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)$")


def _load(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    return table(path) if path.is_file() else {}


def _merged(base: Path, current: Path, relative: str) -> tuple[dict[str, Any], dict[str, str]]:
    rows: dict[str, Any] = {}
    layers: dict[str, str] = {}
    for layer, root in (("base", base), ("current", current)):
        for key, value in _load(root, relative).items():
            rows[str(key)] = value
            layers[str(key)] = layer
    return rows, layers


def _int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _translated(translate: Translator, value: object) -> str:
    text = translate(value)
    return player_facing_effect(text, []) if text else ""


def _image(row: dict[str, Any]) -> str:
    for field in ("icon", "icon_path", "item_icon", "big_icon_path", "forge_icon"):
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _source(base: Path, current: Path, translations: dict) -> dict[str, Any]:
    return {
        "base_snapshot": source_summary(base / "snapshot.json"),
        "current_snapshot": source_summary(current / "snapshot.json"),
        "primary_evidence": "Installed Once Human game snapshot",
        "english_translation_entries": len(translations),
        "merge_rule": "Current patch rows override matching Base record keys; Base-only rows remain",
    }


def _recipe_identity(key: object, row: dict[str, Any]) -> tuple[int, int]:
    text = str(key).strip()
    match = RECIPE_KEY.fullmatch(text)
    if match:
        return int(match.group(1)), int(match.group(2))
    forge_no = _int(row.get("forge_no"), _int(text))
    return forge_no, 0


def _translations(base: Path, current: Path) -> tuple[dict, Translator]:
    translations = {}
    base_translation = base / "translate/translate_data_en.json"
    if base_translation.is_file():
        translations.update(translation_entries(base_translation))
    for path in sorted((current / "translate").glob("translate_data_en*.json")):
        translations.update(translation_entries(path))
    return translations, Translator(translations)


def _choice_groups(
    rows: dict[str, Any],
    items: dict[str, Any],
    translate: Translator,
) -> dict[int, dict[str, Any]]:
    grouped: dict[int, dict[tuple[int, int], dict[str, Any]]] = defaultdict(dict)
    for record_key, row in rows.items():
        if not isinstance(row, dict):
            continue
        group_id = _int(row.get("identity"))
        item_id = _int(row.get("item_id"))
        quantity = _int(row.get("item_num"))
        if not group_id or not item_id or quantity <= 0:
            continue
        item = items.get(str(item_id), {}) if isinstance(items.get(str(item_id), {}), dict) else {}
        option = grouped[group_id].setdefault(
            (item_id, quantity),
            {
                "item_id": item_id,
                "base_quantity": quantity,
                "name": _translated(translate, item.get("name")),
                "quality_code": _int(item.get("quality")),
                "quality": QUALITY_NAMES.get(_int(item.get("quality")), "Unknown"),
                "image_reference": _image(item),
                "source_records": [],
                "effects": [],
            },
        )
        option["source_records"].append(str(record_key))
        effect_types = [_int(value) for value in row.get("effect_type_list", []) if _int(value)]
        if effect_types:
            effect = {
                "name": _translated(translate, row.get("effect_desc")),
                "description": _translated(translate, row.get("describe")),
                "type_codes": effect_types,
            }
            if effect not in option["effects"]:
                option["effects"].append(effect)
    result: dict[int, dict[str, Any]] = {}
    for group_id, options in grouped.items():
        result[group_id] = {
            "group_id": group_id,
            "canonical_id": f"ds-material-group-{group_id}",
            "options": sorted(options.values(), key=lambda row: (row["item_id"], row["base_quantity"])),
        }
    return result


def build(base: Path, current: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    translations, translate = _translations(base, current)
    source = _source(base, current, translations)
    items, item_layers = _merged(base, current, f"{GAME_DATA}/item_data.json")
    forge, forge_layers = _merged(base, current, f"{GAME_DATA}/forge_data.json")
    choice_rows, choice_layers = _merged(base, current, f"{GAME_DATA}/forge_choice_material_data.json")
    money, money_layers = _merged(base, current, f"{GAME_DATA}/money_material_data.json")
    formula_map, formula_layers = _merged(base, current, f"{CLIENT_DATA}/forge_formula_map_data.json")
    choice_groups = _choice_groups(choice_rows, items, translate)

    item_to_forge = formula_map.get("ITEM_NO_TO_FORGE_NO_MAP", {})
    reverse_formula: dict[tuple[int, int], set[int]] = defaultdict(set)
    if isinstance(item_to_forge, dict):
        for item_id_text, owner in item_to_forge.items():
            item_id = _int(item_id_text)
            if isinstance(owner, (list, tuple)) and owner:
                forge_no = _int(owner[0])
                server_no = _int(owner[1]) if len(owner) > 1 else 0
            else:
                forge_no, server_no = _int(owner), 0
            if item_id and forge_no:
                reverse_formula[(forge_no, server_no)].add(item_id)

    material_usage: dict[int, dict[str, set[str]]] = defaultdict(lambda: {
        "fixed_recipe_ids": set(),
        "selectable_recipe_ids": set(),
        "choice_group_ids": set(),
    })
    group_usage: dict[int, set[str]] = defaultdict(set)
    recipes: list[dict[str, Any]] = []
    review_queue: list[dict[str, Any]] = []
    seen_recipe_ids: set[str] = set()

    for record_key, row in forge.items():
        if not isinstance(row, dict):
            continue
        forge_no, server_no = _recipe_identity(record_key, row)
        if not forge_no:
            review_queue.append({"record_key": str(record_key), "reason": "forge recipe identity unresolved"})
            continue
        canonical_id = f"ds-recipe-{forge_no}-{server_no}"
        if canonical_id in seen_recipe_ids:
            review_queue.append({"record_key": str(record_key), "canonical_id": canonical_id, "reason": "duplicate exact recipe identity"})
            continue
        seen_recipe_ids.add(canonical_id)
        output_item_id = _int(row.get("item_no"))
        output_item = items.get(str(output_item_id), {}) if output_item_id else {}
        fixed_materials: list[dict[str, Any]] = []
        selectable_groups: list[dict[str, Any]] = []
        unresolved_cost_ids: list[int] = []
        cost_ids = list(row.get("cost_item_list", []) or [])
        cost_quantities = list(row.get("cost_num_list", []) or [])
        for index, raw_cost in enumerate(cost_ids):
            cost_id = _int(raw_cost)
            quantity = _int(cost_quantities[index]) if index < len(cost_quantities) else 0
            if cost_id in choice_groups:
                group = choice_groups[cost_id]
                group_usage[cost_id].add(canonical_id)
                options = []
                for option in group["options"]:
                    material_usage[option["item_id"]]["selectable_recipe_ids"].add(canonical_id)
                    material_usage[option["item_id"]]["choice_group_ids"].add(str(cost_id))
                    options.append({**option, "recipe_quantity": option["base_quantity"] * quantity})
                selectable_groups.append({
                    "group_id": cost_id,
                    "canonical_id": group["canonical_id"],
                    "multiplier": quantity,
                    "options": options,
                    "source_table": f"{GAME_DATA}/forge_choice_material_data.json",
                })
                continue
            item = items.get(str(cost_id)) if cost_id else None
            if isinstance(item, dict):
                material_usage[cost_id]["fixed_recipe_ids"].add(canonical_id)
                fixed_materials.append({
                    "item_id": cost_id,
                    "name": _translated(translate, item.get("name")),
                    "quantity": quantity,
                    "quality_code": _int(item.get("quality")),
                    "quality": QUALITY_NAMES.get(_int(item.get("quality")), "Unknown"),
                    "image_reference": _image(item),
                    "source_table": f"{GAME_DATA}/item_data.json",
                })
            else:
                unresolved_cost_ids.append(cost_id)

        currency_id = _int(row.get("cost_money_no"))
        currency_row = money.get(str(currency_id), {}) if currency_id else {}
        mapped_outputs = sorted(reverse_formula.get((forge_no, server_no), set()))
        if not mapped_outputs and server_no:
            mapped_outputs = sorted(reverse_formula.get((forge_no, 0), set()))
        output_conflict = bool(mapped_outputs and output_item_id and output_item_id not in mapped_outputs)
        recipes.append({
            "canonical_id": canonical_id,
            "forge_no": forge_no,
            "server_no": server_no,
            "record_key": str(record_key),
            "source_layer": forge_layers.get(str(record_key), "unresolved"),
            "output_item_id": output_item_id,
            "output_name": _translated(translate, output_item.get("name")) if isinstance(output_item, dict) else "",
            "output_image_reference": _image(output_item) if isinstance(output_item, dict) else "",
            "formula_map_output_item_ids": mapped_outputs,
            "formula_map_state": "CONFLICT" if output_conflict else "PROVEN" if mapped_outputs else "UNRESOLVED",
            "fixed_materials": fixed_materials,
            "selectable_material_groups": selectable_groups,
            "unresolved_cost_ids": unresolved_cost_ids,
            "currency": {
                "currency_id": currency_id,
                "name": _translated(translate, currency_row.get("name")) if isinstance(currency_row, dict) else "",
                "quantity": _int(row.get("cost_money_num")),
                "image_reference": _image(currency_row) if isinstance(currency_row, dict) else "",
                "source_layer": money_layers.get(str(currency_id), "unresolved") if currency_id else "not-applicable",
            },
            "craft_time_seconds": _int(row.get("seconds")),
            "source_table": f"{GAME_DATA}/forge_data.json",
        })

    referenced_material_ids = set(material_usage)
    materials: list[dict[str, Any]] = []
    for item_id in sorted(referenced_material_ids):
        item = items.get(str(item_id), {})
        usage = material_usage[item_id]
        materials.append({
            "canonical_id": f"ds-material-{item_id}",
            "item_id": item_id,
            "name": _translated(translate, item.get("name")) if isinstance(item, dict) else "",
            "description": _translated(translate, item.get("short_desc") or item.get("description") or item.get("desc")) if isinstance(item, dict) else "",
            "item_type_code": _int(item.get("type")) if isinstance(item, dict) else 0,
            "subtype_code": _int(item.get("sub_type", item.get("subtype"))) if isinstance(item, dict) else 0,
            "quality_code": _int(item.get("quality")) if isinstance(item, dict) else 0,
            "quality": QUALITY_NAMES.get(_int(item.get("quality")) if isinstance(item, dict) else 0, "Unknown"),
            "max_stack": _int(item.get("stack_num") or item.get("max_stack") or item.get("pile_limit")) if isinstance(item, dict) else 0,
            "gain_path": _translated(translate, item.get("gain_path")) if isinstance(item, dict) else "",
            "image_reference": _image(item) if isinstance(item, dict) else "",
            "source_layer": item_layers.get(str(item_id), "unresolved"),
            "fixed_recipe_ids": sorted(usage["fixed_recipe_ids"]),
            "selectable_recipe_ids": sorted(usage["selectable_recipe_ids"]),
            "choice_group_ids": sorted(_int(value) for value in usage["choice_group_ids"]),
        })

    group_records = []
    for group_id, group in sorted(choice_groups.items()):
        group_records.append({
            **group,
            "recipe_ids": sorted(group_usage.get(group_id, set())),
            "source_layers": sorted({choice_layers.get(record_id, "unresolved") for option in group["options"] for record_id in option.get("source_records", [])}),
        })

    state_counts = Counter(row["formula_map_state"] for row in recipes)
    crafting = {
        "schema": "dead-signal-crafting",
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "record_counts": {
            "recipes": len(recipes),
            "material_groups": len(group_records),
            "formula_map_states": dict(sorted(state_counts.items())),
            "review_queue": len(review_queue),
        },
        "recipes": sorted(recipes, key=lambda row: (row["forge_no"], row["server_no"])),
        "material_groups": group_records,
        "review_queue": review_queue,
        "policy": {
            "recipe_identity": "Exact forge_data record identity: forge_no plus server_no; simple keys use server 0.",
            "cost_typing": "A cost ID is tested against exact choice-group identity before exact item identity. The namespaces are never merged by scalar similarity.",
            "formula_map": "ITEM_NO_TO_FORGE_NO_MAP is corroborating output-to-recipe evidence; disagreement with forge_data.item_no is CONFLICT.",
        },
    }
    material_payload = {
        "schema": "dead-signal-materials",
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "record_counts": {"materials": len(materials)},
        "materials": materials,
        "review_queue": [],
        "policy": {
            "material_identity": "Exact item_data item ID referenced by a typed recipe cost or selectable material group.",
            "choice_group_identity": "Group IDs are separate entities and never treated as material item IDs.",
        },
    }
    return crafting, material_payload


def write_outputs(base: Path, current: Path, output_dir: Path) -> dict[str, Any]:
    crafting, materials = build(base, current)
    output_dir.mkdir(parents=True, exist_ok=True)
    crafting_path = output_dir / "crafting.json"
    materials_path = output_dir / "materials.json"
    crafting_path.write_text(json.dumps(crafting, ensure_ascii=False, indent=2), encoding="utf-8")
    materials_path.write_text(json.dumps(materials, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "crafting": {"file": str(crafting_path), "record_counts": crafting["record_counts"]},
        "materials": {"file": str(materials_path), "record_counts": materials["record_counts"]},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(write_outputs(args.base, args.current, args.output_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
