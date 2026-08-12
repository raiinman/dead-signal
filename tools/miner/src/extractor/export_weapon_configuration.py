"""Export fail-closed configured-weapon inputs from normalized Miner data."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def resolved_static(modifiers: list[dict]) -> list[dict]:
    return [
        value for value in modifiers
        if value.get("type") == "stat_modifier"
        and value.get("resolution_status") == "resolved"
        and value.get("operation") in {"add_flat", "add_percent"}
        and value.get("value") is not None
    ]


def build_configuration(data_dir: Path) -> dict:
    ammo = load(data_dir / "ammo.json").get("ammo", [])
    attachments = load(data_dir / "attachments.json").get("attachments", [])
    mods = load(data_dir / "mods.json").get("mods", [])
    calibrations = load(data_dir / "calibrations.json").get("calibrations", [])

    ammo_records = []
    for row in ammo:
        bindings = []
        for binding in row.get("configuration_bindings", []):
            bindings.append({
                **binding,
                "static_modifiers": resolved_static(binding.get("static_modifiers", [])),
                "auto_apply_status": "proven-static" if not binding.get("passive_buff_id") else "static-only-passive-buff-excluded",
            })
        if bindings:
            ammo_records.append({
                "item_id": row.get("item_id"), "name": row.get("name"),
                "quality": row.get("quality"), "bindings": bindings,
            })

    attachment_records = []
    for row in attachments:
        static = resolved_static(row.get("resolved_stats", []))
        if static or row.get("passive_buff_id"):
            attachment_records.append({
                "id": row.get("id"), "item_id": row.get("item_id"),
                "name": row.get("name"), "slot": row.get("attachment_type"),
                "static_modifiers": static, "passive_buff_id": row.get("passive_buff_id"),
                "auto_apply_status": "proven-static" if not row.get("passive_buff_id") else "static-only-passive-buff-excluded",
                "source": {"dataset": "attachments.json", "affix_code": row.get("affix_code")},
            })

    weapon_mod_records = []
    for row in mods:
        applicability = row.get("resolved_applicability") or {}
        if applicability.get("category") != "weapon":
            continue
        direct_entries = []
        has_runtime_effects = False
        for entry in row.get("resolved_effects", []):
            effects = entry.get("effects", [])
            static = resolved_static(effects)
            runtime = [effect for effect in effects if effect.get("type") != "stat_modifier"]
            direct_entries.append({
                "entry_code": entry.get("entry_code"), "entry_level": entry.get("entry_level"),
                "static_modifiers": static, "runtime_effect_types": sorted({effect.get("type") for effect in runtime if effect.get("type")}),
            })
            has_runtime_effects = has_runtime_effects or bool(runtime)
        weapon_mod_records.append({
            "id": row.get("id"), "name": row.get("name"), "is_shiny": row.get("is_shiny"),
            "applicability": applicability, "entries": direct_entries,
            "auto_apply_status": "conditional-or-runtime-excluded" if has_runtime_effects else "proven-direct-static",
            "source": {"dataset": "mods.json", "mod_code": row.get("mod_code")},
        })

    current_calibrations = [
        {
            "id": row.get("id"), "name": row.get("name"), "quality": row.get("quality"),
            "weapon_damage_roll": row.get("weapon_damage_roll"),
            "affix_option_pool": row.get("affix_option_pool", []),
            "auto_apply_status": "requires-explicit-player-roll-and-selected-term",
            "source": {"dataset": "calibrations.json", "status": row.get("status")},
        }
        for row in calibrations if row.get("status") == "current"
    ]

    return {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Configured-weapon modifier inputs proven from installed-game tables",
        "application_policy": {
            "auto_apply": "Only direct resolved static modifiers with a proven operation and value",
            "excluded": [
                "passive buffs and logic-tree effects without a proven active condition",
                "conditional or runtime mod effects",
                "ammo inventory items without an exact slot-accessory-affix binding",
                "calibration values until the player supplies the exact roll and selected weighted term",
                "enemy mitigation, scenario state, proc frequency, and configured DPS",
            ],
        },
        "record_counts": {
            "ammo_with_proven_bindings": len(ammo_records),
            "ammo_bindings": sum(len(row["bindings"]) for row in ammo_records),
            "attachments_with_modifiers_or_buffs": len(attachment_records),
            "weapon_mods": len(weapon_mod_records),
            "current_calibrations": len(current_calibrations),
        },
        "layers": {
            "ammo": ammo_records,
            "attachments": attachment_records,
            "weapon_mods": weapon_mod_records,
            "calibrations": current_calibrations,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_configuration(args.data_dir)
    write(args.output, payload)
    print(json.dumps(payload["record_counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
