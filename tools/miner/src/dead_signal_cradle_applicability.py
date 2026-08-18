"""Exact installed-data Weapon -> Cradle applicability projection.

This module reads only retained JSON tables and the already-indexed static
consumer evidence.  It never imports or executes game bytecode.  A Cradle is
promoted to per-weapon compatibility only when its buff logic tree contains an
explicit positive ``hold_item_check`` whose ``hold_type`` and
``hold_sub_type`` exactly match the weapon's ``item_data.type/sub_type``.
"""
from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
CRADLE_ENTRY = "game_common/data/cradle_override_entry_data.json"
CRADLE_CONFIG = "game_common/data/cradle_override_config_new_data.json"
ITEM_DATA = "game_common/data/item_data.json"
BUFF_DIR = "game_common/data/buff"
LOGIC_TREE_DIR = "game_common/data/logic_tree"
RAW_SELECTOR_FIELDS = (
    "attack_type", "formula_attack_type", "keyword", "keyword_tag",
    "weapon_no", "sub_melee_attack_type",
)
CONSUMER_PATH = "ui/data_model/UIEquipmentData.pyc"
CONSUMER_SCOPE_SUFFIX = "get_show_equip_preset_cradle"


def _read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError):
        return default


def _table(root: Path, relative: str) -> dict[str, Any]:
    payload = _read(root / relative, {}) or {}
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    return {str(key): value for key, value in data.items()} if isinstance(data, dict) else {}


def _merged_table(base: Path, current: Path, relative: str) -> dict[str, Any]:
    result = _table(base, relative)
    result.update(_table(current, relative))
    return result


def _atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _buff_index(base: Path, current: Path) -> dict[str, Any]:
    records: dict[str, Any] = {}
    for root in (base, current):
        directory = root / BUFF_DIR
        for path in sorted(directory.glob("buff_data*.json")) if directory.is_dir() else ():
            records.update(_table(root, path.relative_to(root).as_posix()))
    return records


def _active_configurations(configs: dict[str, Any]) -> tuple[dict[str, Any], dict[int, dict[str, list[Any]]]]:
    rows: dict[str, Any] = {}
    membership: dict[int, dict[str, list[Any]]] = defaultdict(lambda: {"config_keys": [], "season_ids": []})
    for key, record in configs.items():
        if not isinstance(record, dict) or not isinstance(record.get("override_unlock_lst"), list):
            continue
        entry_ids = []
        for group in record.get("override_unlock_lst") or []:
            if not isinstance(group, list):
                continue
            for value in group:
                try:
                    entry_id = int(value)
                except (TypeError, ValueError):
                    continue
                entry_ids.append(entry_id)
                membership[entry_id]["config_keys"].append(str(key))
                season = record.get("season_no")
                if season not in (None, ""):
                    membership[entry_id]["season_ids"].append(season)
        rows[str(key)] = {
            "config_key": str(key),
            "season_id": record.get("season_no"),
            "active_cradle_ids": entry_ids,
        }
    for value in membership.values():
        value["config_keys"] = sorted(set(value["config_keys"]), key=lambda item: int(item) if item.isdigit() else item)
        value["season_ids"] = sorted(set(value["season_ids"]), key=str)
    return rows, membership


def _logic_tree(base: Path, current: Path, name: str) -> dict[str, Any]:
    relative = f"{LOGIC_TREE_DIR}/{name}.json"
    payload = _read(current / relative)
    if payload is None:
        payload = _read(base / relative, {})
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    return data if isinstance(data, dict) else {}


def _selector_evidence(entry_id: int, buff_id: int, buffs: dict[str, Any], base: Path, current: Path) -> dict[str, Any]:
    hold_checks = []
    raw_selectors = []
    logic_trees = []
    visited: set[int] = set()

    def visit(current_buff: int, depth: int = 0) -> None:
        if current_buff in visited or depth > 8:
            return
        visited.add(current_buff)
        buff = buffs.get(f"({current_buff}, 1)")
        if not isinstance(buff, dict):
            return
        for tree_name in buff.get("logic_tree_data") or []:
            tree_name = str(tree_name)
            if tree_name not in logic_trees:
                logic_trees.append(tree_name)
            tree = _logic_tree(base, current, tree_name)
            nodes = tree.get("node_list") or {}
            if not isinstance(nodes, dict):
                continue
            child_buffs = []
            for node_id, node in nodes.items():
                params = (((node or {}).get("effect_params") or {}).get("params") or {})
                for location in ("trigger_checker", "reset_checker"):
                    for checker in params.get(location) or []:
                        if not isinstance(checker, dict) or checker.get("type") != "hold_item_check":
                            continue
                        values = checker.get("params") or {}
                        hold_checks.append({
                            "buff_id": current_buff,
                            "logic_tree": tree_name,
                            "node_id": str(node_id),
                            "location": location,
                            "check_negate": bool(values.get("check_negate")),
                            "hold_type": values.get("hold_type"),
                            "hold_sub_type": values.get("hold_sub_type"),
                        })
                check_args = params.get("check_args") or {}
                selected = {field: check_args.get(field) for field in RAW_SELECTOR_FIELDS if check_args.get(field)}
                if selected:
                    raw_selectors.append({
                        "buff_id": current_buff,
                        "logic_tree": tree_name,
                        "node_id": str(node_id),
                        "fields": selected,
                    })
                node_type = str(((node or {}).get("effect_params") or {}).get("type") or "")
                if node_type == "NodeCastBuffToTarget" and params.get("buff_id") not in (None, ""):
                    try:
                        child_buffs.append(int(params["buff_id"]))
                    except (TypeError, ValueError):
                        pass
            for child in child_buffs:
                visit(child, depth + 1)

    visit(buff_id)
    positive = sorted({
        (int(row["hold_type"]), int(row["hold_sub_type"]))
        for row in hold_checks
        if not row["check_negate"] and row["hold_type"] is not None and row["hold_sub_type"] is not None
    })
    if positive:
        state = "weapon-selector-exact"
    elif raw_selectors:
        state = "weapon-relation-unresolved"
    else:
        state = "not-weapon-selected"
    return {
        "entry_id": entry_id,
        "buff_id": buff_id,
        "state": state,
        "positive_item_selectors": [
            {"item_type": item_type, "item_sub_type": sub_type}
            for item_type, sub_type in positive
        ],
        "hold_item_checks": hold_checks,
        "unresolved_raw_selectors": raw_selectors,
        "logic_trees": logic_trees,
        "visited_buff_ids": sorted(visited),
    }


def _consumer_proof(database: Path) -> dict[str, Any]:
    if not database.is_file():
        return {"status": "consumer-index-unavailable", "path": CONSUMER_PATH, "scope": CONSUMER_SCOPE_SUFFIX}
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT path,qualname,names_json,strings_json,numbers_json FROM scopes "
            "WHERE layer='base' AND path=? AND qualname LIKE ? LIMIT 1",
            (CONSUMER_PATH, f"%{CONSUMER_SCOPE_SUFFIX}"),
        ).fetchone()
    if not row:
        return {"status": "scope-unresolved", "path": CONSUMER_PATH, "scope": CONSUMER_SCOPE_SUFFIX}
    return {
        "status": "exact-static-scope-located",
        "path": row["path"],
        "qualname": row["qualname"],
        "co_names": json.loads(row["names_json"]),
        "string_constants": json.loads(row["strings_json"]),
        "number_constants": json.loads(row["numbers_json"]),
        "proof_limit": "Static scope proves active-config/entry/style/keyword consumption. Weapon applicability is promoted only from exact logic-tree hold_item_check selectors.",
    }


def build(base: Path | str, current: Path | str, output: Path | str, weapons_payload: dict[str, Any], cradles_payload: dict[str, Any]) -> dict[str, Any]:
    base, current, output = Path(base), Path(current), Path(output)
    entries = _merged_table(base, current, CRADLE_ENTRY)
    configs = _merged_table(base, current, CRADLE_CONFIG)
    items = _merged_table(base, current, ITEM_DATA)
    buffs = _buff_index(base, current)
    configuration_rows, membership = _active_configurations(configs)
    active_ids = sorted(membership)
    selectors = {}
    for entry_id in active_ids:
        entry = entries.get(str(entry_id)) or {}
        try:
            buff_id = int(entry.get("buff_id"))
        except (TypeError, ValueError):
            buff_id = 0
        selectors[entry_id] = _selector_evidence(entry_id, buff_id, buffs, base, current)

    cradle_by_id = {int(row.get("id")): row for row in cradles_payload.get("cradles") or [] if row.get("id") is not None}
    for entry_id, evidence in selectors.items():
        cradle = cradle_by_id.get(entry_id)
        if not cradle:
            continue
        cradle["active_config_keys"] = membership[entry_id]["config_keys"]
        cradle["active_season_ids"] = membership[entry_id]["season_ids"]
        cradle["weapon_applicability"] = {
            "state": evidence["state"],
            "positive_item_selectors": evidence["positive_item_selectors"],
            "evidence_report": "published/reports/weapon-cradle-applicability.json",
        }

    state_counts = Counter(evidence["state"] for evidence in selectors.values())
    controls = []
    relationship_counts = Counter()
    for weapon in weapons_payload.get("weapons") or []:
        item_id = str(weapon.get("item_id") or "")
        item = items.get(item_id) or {}
        item_type, item_sub_type = item.get("type"), item.get("sub_type")
        compatible, incompatible, unresolved = [], [], []
        for entry_id, evidence in selectors.items():
            state = evidence["state"]
            if state == "weapon-selector-exact":
                allowed = {(row["item_type"], row["item_sub_type"]) for row in evidence["positive_item_selectors"]}
                (compatible if (item_type, item_sub_type) in allowed else incompatible).append(entry_id)
            elif state == "weapon-relation-unresolved":
                unresolved.append(entry_id)
        relation_state = "resolved-installed-game" if item_type is not None and item_sub_type is not None else "unresolved-item-selector"
        weapon["compatibility"] = dict(weapon.get("compatibility") or {})
        weapon["compatibility"]["cradle"] = {
            "state": relation_state,
            "item_selector": {"item_type": item_type, "item_sub_type": item_sub_type},
            "compatible_exact_ids": compatible,
            "incompatible_exact_ids": incompatible,
            "unresolved_ids": unresolved,
            "not_weapon_selected_count": state_counts["not-weapon-selected"],
            "evidence_report": "published/reports/weapon-cradle-applicability.json",
        }
        relationship_counts["weapons"] += 1
        relationship_counts["compatible_exact"] += len(compatible)
        relationship_counts["incompatible_exact"] += len(incompatible)
        relationship_counts["unresolved"] += len(unresolved)
        relationship_counts["not_applicable"] += state_counts["not-weapon-selected"]
        if not any(row.get("category") == weapon.get("category") for row in controls):
            controls.append({
                "canonical_id": weapon.get("canonical_id"),
                "weapon": weapon.get("name"),
                "blueprint_id": weapon.get("blueprint_id"),
                "item_id": weapon.get("item_id"),
                "category": weapon.get("category"),
                "item_selector": {"source_table": ITEM_DATA, "item_type": item_type, "item_sub_type": item_sub_type},
                "compatible_exact_ids": compatible,
                "incompatible_exact_ids": incompatible,
                "unresolved_ids": unresolved,
                "result": "COMPATIBLE / NOT COMPATIBLE proven only for weapon-selector-exact Cradles; raw attack/keyword selectors remain UNRESOLVED.",
            })

    report = {
        "schema": "dead-signal-weapon-cradle-applicability",
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_counts": {
            "cradle_entries": len(entries),
            "active_configuration_records": len(configuration_rows),
            "active_unique_cradles": len(active_ids),
            "selector_states": dict(sorted(state_counts.items())),
            **dict(relationship_counts),
        },
        "data_model": {
            "identity_owner": CRADLE_ENTRY,
            "active_configuration_owner": CRADLE_CONFIG,
            "weapon_selector_owner": ITEM_DATA,
            "effect_owner": "game_common/data/buff/buff_data*.json",
            "condition_owner": "game_common/data/logic_tree/<buff logic_tree_data>.json",
            "typed_chain": "Cradle config override_unlock_lst -> Cradle entry -> buff_id -> buff logic tree -> positive hold_item_check(type/sub_type) -> exact weapon item_data.type/sub_type",
        },
        "consumer_proof": _consumer_proof(output / "catalogs" / "dead-signal-consumer-index.sqlite"),
        "configurations": list(configuration_rows.values()),
        "selectors": [selectors[key] | membership[key] for key in active_ids],
        "controls": controls,
        "policy": {
            "compatible_exact": "Positive hold_item_check item type/subtype exactly matches the weapon item record.",
            "incompatible_exact": "A weapon-selector-exact Cradle has one or more positive item selectors and none match the weapon item record.",
            "not_applicable": "The Cradle logic tree contains no weapon-identity selector; this is not a claim that the effect is inactive or unusable.",
            "unresolved": "Attack, formula, keyword, weapon-number, or melee-event selectors remain raw until their typed weapon relationship is independently proven.",
            "active": "Active means referenced by at least one installed cradle_override_config_new_data override_unlock_lst; configuration/season membership is preserved and never collapsed into one current scenario claim.",
        },
    }
    return report


def enrich_files(base: Path | str, current: Path | str, output: Path | str, log=None) -> dict[str, Any]:
    output = Path(output)
    weapons_path = output / "published" / "data" / "weapons.json"
    cradles_path = output / "published" / "data" / "cradles.json"
    weapons = _read(weapons_path, {}) or {}
    cradles = _read(cradles_path, {}) or {}
    report = build(base, current, output, weapons, cradles)
    _atomic(weapons_path, weapons)
    _atomic(cradles_path, cradles)
    _atomic(output / "published" / "reports" / "weapon-cradle-applicability.json", report)
    if log:
        counts = report["record_counts"]
        log(f"Projected exact Weapon/Cradle applicability: {counts.get('compatible_exact', 0)} compatible and {counts.get('incompatible_exact', 0)} incompatible relations; {counts.get('unresolved', 0)} remain unresolved.")
    return report
