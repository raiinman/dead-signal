"""Project fail-closed Build Lab attachment, calibration, and ammo relationships."""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from attachment_compatibility import direct_compatibility_evidence
from normalize_extended import merged_table


GAME_DATA = "game_common/data"
PLAYER_ATTACHMENT_TYPES = {"Sight", "Muzzle", "Tactical", "Magazine"}
TYPED_ATTACHMENT_SELECTORS = (
    "weapon_type_list", "gun_type_list", "weapon_item_no_list", "gun_no_list",
)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _attachment_relation(weapon: dict, attachment: dict) -> str:
    if weapon.get("category") == "Melee":
        return "not-applicable"
    evidence = attachment["compatibility_evidence"]
    if evidence.get("all_weapons"):
        return "compatible"
    categories = set(evidence.get("compatible_weapon_categories") or [])
    if weapon.get("category") in categories:
        return "compatible"
    if categories and not evidence.get("named_weapon_text_present"):
        return "incompatible"
    typed_ids = set(attachment.get("compatible_weapon_item_ids") or [])
    if typed_ids:
        return "compatible" if weapon.get("item_id") in typed_ids else "incompatible"
    return "unresolved"


def enrich(base: Path, current: Path, published: Path) -> dict[str, Any]:
    data = published / "data"
    reports = published / "reports"
    weapons_path = data / "weapons.json"
    attachments_path = data / "attachments.json"
    calibrations_path = data / "calibrations.json"
    weapons = _read(weapons_path)
    attachments = _read(attachments_path)
    calibrations = _read(calibrations_path)
    accessory_params = merged_table(base, current, f"{GAME_DATA}/gun_accessory_base_params_data.json")

    player_attachments = []
    attachment_owner_states = Counter()
    for attachment in attachments.get("attachments", []):
        if attachment.get("attachment_type") not in PLAYER_ATTACHMENT_TYPES:
            continue
        evidence = direct_compatibility_evidence(attachment.get("description"))
        owner = accessory_params.get(str(attachment.get("accessory_code") or attachment.get("id")), {})
        selectors = {
            field: owner.get(field) for field in TYPED_ATTACHMENT_SELECTORS if owner.get(field)
        }
        if evidence.get("status") == "direct-localized-installed-game-text":
            owner_state = "direct-installed-text-owner"
        elif selectors:
            owner_state = "exact-typed-selector-owner"
        else:
            owner_state = "exact-accessory-owner-compatibility-selector-unresolved"
        evidence["owner_trace"] = {
            "state": owner_state,
            "source_table": f"{GAME_DATA}/gun_accessory_base_params_data.json",
            "record_id": str(attachment.get("accessory_code") or attachment.get("id")),
            "typed_selectors": selectors,
            "named_model_alias_policy": "A model name is never converted to an item ID without a typed installed-data selector owner.",
        }
        attachment["compatibility_evidence"] = evidence
        attachment_owner_states[owner_state] += 1
        player_attachments.append(attachment)

    current_calibrations = [
        row for row in calibrations.get("calibrations", []) if row.get("status") == "current"
    ]
    relationship_counts = Counter()
    for weapon in weapons.get("weapons", []):
        attachment_states: dict[str, list[Any]] = {state: [] for state in ("compatible", "incompatible", "unresolved", "not-applicable")}
        for attachment in player_attachments:
            state = _attachment_relation(weapon, attachment)
            attachment_states[state].append(attachment.get("accessory_code") or attachment.get("id"))
            relationship_counts[f"attachment_{state}"] += 1
        weapon_code = int(weapon.get("weapon_type_code") or 0)
        calibration_states: dict[str, list[Any]] = {state: [] for state in ("compatible", "incompatible", "unresolved", "not-applicable")}
        for calibration in current_calibrations:
            calibration_id = calibration.get("id")
            codes = {int(value) for value in calibration.get("weapon_type_codes") or [] if int(value)}
            if weapon.get("category") == "Melee":
                state = "not-applicable"
            elif not weapon_code or not codes:
                state = "unresolved"
            else:
                state = "compatible" if weapon_code in codes else "incompatible"
            calibration_states[state].append(calibration_id)
            relationship_counts[f"calibration_{state}"] += 1
        ammo = weapon.get("ammo_configuration") or {}
        if weapon.get("category") == "Melee":
            ammo_state = "not-applicable"
        elif ammo.get("resolution_status") == "proven-table-relationship" and ammo.get("selectable_ammo_item_ids"):
            ammo_state = "resolved-selectable-options"
        else:
            ammo_state = "unresolved"
        ammo["state"] = ammo_state
        ammo.setdefault("selectable_ammo_item_ids", [])
        ammo["selection_policy"] = "Exact item -> gun -> slot 8 default accessory -> bullet pack -> ordered ammo item relationship only."
        weapon["ammo_configuration"] = ammo
        compatibility = weapon.setdefault("compatibility", {})
        compatibility["attachment"] = {
            "state": "resolved-four-state-relationship",
            **{f"{state.replace('-', '_')}_ids": values for state, values in attachment_states.items()},
            "evidence_report": "published/reports/weapon-build-compatibility.json",
        }
        compatibility["calibration"] = {
            "state": "resolved-four-state-relationship" if weapon_code or weapon.get("category") == "Melee" else "unresolved",
            **{f"{state.replace('-', '_')}_ids": values for state, values in calibration_states.items()},
            "source_table": f"{GAME_DATA}/gun_correct_print_data.json",
            "selector_field": "weapon_type",
            "evidence_report": "published/reports/weapon-build-compatibility.json",
        }

    report = {
        "schema": "dead-signal-weapon-build-compatibility",
        "schema_version": 1,
        "record_counts": {
            "weapons": len(weapons.get("weapons", [])),
            "player_attachments": len(player_attachments),
            "current_calibrations": len(current_calibrations),
            "attachment_owner_states": dict(sorted(attachment_owner_states.items())),
            **dict(sorted(relationship_counts.items())),
            "ammo_states": dict(sorted(Counter((row.get("ammo_configuration") or {}).get("state") for row in weapons.get("weapons", [])).items())),
        },
        "policy": {
            "four_state": ["compatible", "incompatible", "unresolved", "not-applicable"],
            "attachment": "Direct installed wording and typed selectors only; named-model spelling never establishes identity.",
            "calibration": "Exact gun_correct_print_data weapon_type selector compared with the weapon's exact prototype weapon_type.",
            "ammo": "Exact slot-8 bullet-pack relationships only.",
        },
    }
    reports.mkdir(parents=True, exist_ok=True)
    _write(weapons_path, weapons)
    _write(attachments_path, attachments)
    _write(reports / "weapon-build-compatibility.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--published", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(enrich(args.base, args.current, args.published), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
