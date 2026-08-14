"""Export canonical item -> gun profiles without inventing field semantics."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


GAME_DATA = "game_common/data"


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload.get("data", payload) if isinstance(payload, dict) else {}


def merged(base: Path, current: Path, relative: str) -> dict:
    result = dict(load(base / relative))
    result.update(load(current / relative))
    return result


def as_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def build_profiles(base: Path, current: Path, weapons_path: Path) -> dict:
    weapons = load(weapons_path).get("weapons", [])
    item_to_gun = merged(base, current, f"{GAME_DATA}/item_to_gun_mapping_data.json")
    gun_base = merged(base, current, f"{GAME_DATA}/gun_base_params_data.json")
    stability = merged(base, current, f"{GAME_DATA}/gun_stability_data.json")
    scatter = merged(base, current, f"{GAME_DATA}/bullet_scatter_data.json")
    bullet_patterns = merged(base, current, "client_data/bullet_pattern_data.json")
    slots = merged(base, current, f"{GAME_DATA}/gun_accessory_slot_params_data.json")
    range_templates = merged(base, current, f"{GAME_DATA}/gun_range_formula_template_data.json")
    reload_templates = merged(base, current, f"{GAME_DATA}/gun_reload_formula_template_data.json")

    profiles = []
    unresolved = []
    for weapon in weapons:
        item_id = as_int(weapon.get("item_id"))
        mapping = item_to_gun.get(str(item_id), {})
        gun_no = as_int(mapping.get("gun_no"))
        base_row = gun_base.get(str(gun_no), {})
        stability_row = stability.get(str(gun_no), {}) or stability.get(str(base_row.get("viewkick_no") or ""), {})
        scatter_no = str(base_row.get("bullet_scatter_no") or "")
        bullet_pattern_no = str(base_row.get("bullet_pattern_no") or "")
        slot_rows = [
            {"record_id": key, **row}
            for key, row in slots.items() if as_int(row.get("gun_no")) == gun_no
        ]
        range_no = str(base_row.get("weapon_range_template_no") or "")
        reload_no = str(base_row.get("reload_loop_template_no") or "")
        is_melee = weapon.get("category") == "Melee"
        status = "resolved" if gun_no and base_row else ("not-applicable-melee" if is_melee else "unresolved")
        if status == "unresolved":
            unresolved.append({"item_id": item_id, "name": weapon.get("name"), "gun_no": gun_no})
        profiles.append({
            "item_id": item_id,
            "blueprint_id": weapon.get("blueprint_id"),
            "name": weapon.get("name"),
            "category": weapon.get("category"),
            "gun_no": gun_no or None,
            "resolution_status": status,
            "gun_base_parameters": base_row,
            "stability_parameters": stability_row,
            "scatter_parameters": scatter.get(scatter_no, {}),
            "bullet_pattern": bullet_patterns.get(bullet_pattern_no, {}),
            "accessory_slots": sorted(slot_rows, key=lambda row: as_int(row.get("slot_type"))),
            "range_formula_template": range_templates.get(range_no, {}),
            "reload_formula_template": reload_templates.get(reload_no, {}),
            "linked_ids": {
                "bullet_no": base_row.get("bullet_no"),
                "bullet_base_no": base_row.get("bullet_base_no"),
                "bullet_scatter_no": base_row.get("bullet_scatter_no"),
                "bullet_pattern_no": base_row.get("bullet_pattern_no"),
                "gun_skill_no": base_row.get("gun_skill_no"),
                "viewkick_no": base_row.get("viewkick_no"),
                "range_template_no": base_row.get("weapon_range_template_no"),
                "reload_template_no": base_row.get("reload_loop_template_no"),
            },
            "source": {
                "identity": {"table": f"{GAME_DATA}/item_to_gun_mapping_data.json", "record_id": str(item_id)},
                "base": {"table": f"{GAME_DATA}/gun_base_params_data.json", "record_id": str(gun_no)},
                "stability": {"table": f"{GAME_DATA}/gun_stability_data.json", "record_id": str(gun_no)},
                "scatter": {"table": f"{GAME_DATA}/bullet_scatter_data.json", "record_id": scatter_no},
                "bullet_pattern": {"table": "client_data/bullet_pattern_data.json", "record_id": bullet_pattern_no},
                "slots": {"table": f"{GAME_DATA}/gun_accessory_slot_params_data.json", "gun_no": gun_no},
            },
        })

    return {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Canonical weapon-item to internal-gun profiles; raw fields are preserved and are not automatically combat formulas.",
        "record_counts": {
            "weapons": len(profiles),
            "resolved_gun_profiles": sum(row["resolution_status"] == "resolved" for row in profiles),
            "not_applicable_melee_profiles": sum(row["resolution_status"] == "not-applicable-melee" for row in profiles),
            "unresolved_gun_profiles": len(unresolved),
            "distinct_gun_numbers": len({row["gun_no"] for row in profiles if row["gun_no"]}),
        },
        "profiles": profiles,
        "unresolved": unresolved,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--weapons", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_profiles(args.base, args.current, args.weapons)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
