"""Publish compact Dead Signal web datasets and integrity reports.

This stage consumes only normalized Miner outputs. It does not mine new game
files, execute game code, or infer mechanics. Its job is to turn audit-grade
normalized data into stable player-facing contracts, measure internal coverage,
record snapshot fingerprints, and expose direct relationship evidence for later
mechanic resolution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WEB_SCHEMA_VERSION = 1
QUALITY_SCHEMA_VERSION = 1
GRAPH_SCHEMA_VERSION = 1
MANIFEST_SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _map_by(rows: list[dict], key: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for row in rows:
        value = row.get(key)
        if value not in (None, ""):
            result[str(value)] = row
    return result


def _image_asset(record: dict) -> str:
    for key in ("image_asset", "image_path", "resolved_image", "web_image"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _compact_accessory_slots(profile: dict) -> list[dict]:
    result = []
    for slot in profile.get("accessory_slots") or []:
        if not isinstance(slot, dict):
            continue
        row = {"record_id": slot.get("record_id"), "slot_type": slot.get("slot_type")}
        for key in ("slot_name", "slot_no", "unlock_level", "unlock_lv"):
            if slot.get(key) is not None:
                row[key] = slot.get(key)
        result.append(row)
    return result


def build_weapon_projection(data_dir: Path) -> dict:
    weapons_payload = load_json(data_dir / "weapons.json", {}) or {}
    math_payload = load_json(data_dir / "weapon-math.json", {}) or {}
    profiles_payload = load_json(data_dir / "gun-profiles.json", {}) or {}
    configuration = load_json(data_dir / "weapon-configuration.json", {}) or {}

    math_by_blueprint = _map_by(math_payload.get("weapons", []), "blueprint_id")
    profile_by_blueprint = _map_by(profiles_payload.get("profiles", []), "blueprint_id")
    records = []

    for weapon in weapons_payload.get("weapons", []):
        blueprint_id = weapon.get("blueprint_id")
        math = math_by_blueprint.get(str(blueprint_id), {})
        profile = profile_by_blueprint.get(str(blueprint_id), {})
        ranged = weapon.get("ranged_stats") or {}
        records.append(
            {
                "canonical_id": f"ds-w-{blueprint_id}",
                "blueprint_id": blueprint_id,
                "item_id": weapon.get("item_id"),
                "name": weapon.get("name"),
                "category": weapon.get("category"),
                "weapon_type_code": weapon.get("weapon_type_code"),
                "prototype_id": weapon.get("prototype_id"),
                "rarity": weapon.get("quality"),
                "quality_code": weapon.get("quality_code"),
                "image_asset": _image_asset(weapon),
                # Normalized short descriptions are currently known to contain
                # cross-wired localization records for some weapons. Keep the
                # public contract fail-closed until that resolver is verified.
                "description": "",
                "acquisition": {
                    "hint": weapon.get("acquisition_hint") or "",
                    "gain_path": weapon.get("item_gain_path") or "",
                    "fragment_id": weapon.get("fragment_id"),
                    "fragments_to_unlock": weapon.get("fragments_to_unlock"),
                    "endowed_blueprint": bool(weapon.get("endowed_blueprint")),
                },
                "baseline": {
                    "durability": weapon.get("durability"),
                    "weight": weapon.get("weight"),
                    "attributes": weapon.get("base_attributes") or [],
                    "ranged": ranged or None,
                    "melee": weapon.get("melee_stats"),
                },
                "damage_profile": {
                    "full_damage_distance": ranged.get("full_damage_distance"),
                    "minimum_damage_distance": ranged.get("minimum_damage_distance"),
                    "minimum_damage_multiplier": ranged.get("minimum_damage_multiplier"),
                } if ranged else None,
                "ammo_item_id": ranged.get("ammo_item_id") if ranged else None,
                "effect": weapon.get("effect"),
                "progression": {
                    "gear_tiers": weapon.get("tiers") or [],
                    "blueprint_stars": weapon.get("blueprint_star_progression") or {},
                    "tier_star_matrix": math.get("tier_star_matrix") or [],
                    "formula_status": math.get("formula_status"),
                    "validation_issues": math.get("validation_issues") or [],
                },
                "gun_profile": {
                    "resolution_status": profile.get("resolution_status"),
                    "gun_no": profile.get("gun_no"),
                    "accessory_slots": _compact_accessory_slots(profile),
                    "linked_ids": profile.get("linked_ids") or {},
                },
                "verification": {
                    "source_status": "mined-from-installed-game",
                    "description_status": "withheld-until-short-description-resolver-is-verified",
                    "notes": weapon.get("verification_notes") or [],
                },
            }
        )

    return {
        "schema": "dead-signal-weapons",
        "schema_version": WEB_SCHEMA_VERSION,
        "generated_utc": utc_now(),
        "record_counts": {
            "weapons": len(records),
            "ranged_weapons": sum(bool(row.get("baseline", {}).get("ranged")) for row in records),
            "melee_weapons": sum(bool(row.get("baseline", {}).get("melee")) for row in records),
        },
        "formula_contract": math_payload.get("formula_contract") or {},
        "configuration_catalog": {
            "dataset": "weapon-configuration.json",
            "schema_version": configuration.get("schema_version"),
            "application_policy": configuration.get("application_policy") or {},
            "record_counts": configuration.get("record_counts") or {},
        },
        "weapons": records,
    }


def build_configuration_projection(data_dir: Path) -> dict:
    source = load_json(data_dir / "weapon-configuration.json", {}) or {}
    return {
        "schema": "dead-signal-weapon-configuration",
        "schema_version": WEB_SCHEMA_VERSION,
        "generated_utc": utc_now(),
        "source_schema_version": source.get("schema_version"),
        "scope": source.get("scope") or "Configured-weapon inputs proven from installed-game tables",
        "application_policy": source.get("application_policy") or {},
        "record_counts": source.get("record_counts") or {},
        "layers": source.get("layers") or {},
    }


def build_armor_projection(data_dir: Path) -> dict:
    source = load_json(data_dir / "armor-sets.json", {}) or {}
    sets = []
    for armor_set in source.get("armor_sets", []):
        suit_id = armor_set.get("suit_id")
        pieces = []
        for piece in armor_set.get("pieces", []):
            tiers = piece.get("tiers") or []
            blueprint_id = piece.get("blueprint_id") or ((tiers[0] or {}).get("blueprint_id") if tiers else None)
            pieces.append(
                {
                    # Blueprint IDs can legitimately repeat across named suit
                    # variants (for example base/cold/heat families). The suit
                    # identity is therefore part of the public piece identity.
                    "canonical_id": f"ds-a-{suit_id}-{blueprint_id}",
                    "suit_id": suit_id,
                    "blueprint_id": blueprint_id,
                    "name": piece.get("name"),
                    "slot_id": piece.get("slot_id"),
                    "slot": piece.get("slot"),
                    "rarity": piece.get("quality"),
                    "quality_code": piece.get("quality_code"),
                    "image_asset": _image_asset(piece) or (_image_asset(tiers[0]) if tiers else ""),
                    "tiers": tiers,
                    "crafting_recipes": piece.get("crafting_recipes") or [],
                }
            )
        sets.append(
            {
                "canonical_id": f"ds-as-{suit_id}",
                "suit_id": suit_id,
                "name": armor_set.get("name"),
                "image_asset": _image_asset(armor_set),
                "piece_count": armor_set.get("piece_count"),
                "set_bonuses": armor_set.get("set_bonuses") or [],
                "pieces": pieces,
                "verification": {
                    "source_status": armor_set.get("source_status") or "mined-from-installed-game",
                    "notes": armor_set.get("verification_notes") or [],
                },
            }
        )

    key_armor = []
    for piece in source.get("key_armor", []):
        tiers = piece.get("tiers") or []
        blueprint_id = piece.get("blueprint_id") or ((tiers[0] or {}).get("blueprint_id") if tiers else None)
        key_armor.append(
            {
                "canonical_id": f"ds-ka-{blueprint_id}",
                "blueprint_id": blueprint_id,
                "name": piece.get("name"),
                "slot_id": piece.get("slot_id"),
                "slot": piece.get("slot"),
                "rarity": piece.get("quality"),
                "quality_code": piece.get("quality_code"),
                "image_asset": _image_asset(piece) or (_image_asset(tiers[0]) if tiers else ""),
                "passive_skill_code": piece.get("passive_skill_code"),
                "passive_skill_name": piece.get("passive_skill_name"),
                "buff_id": piece.get("buff_id"),
                "key_effect": piece.get("key_effect") or "",
                "tiers": tiers,
                "crafting_recipes": piece.get("crafting_recipes") or [],
                "verification": {
                    "source_status": piece.get("source_status") or "mined-from-installed-game",
                    "notes": piece.get("verification_notes") or [],
                },
            }
        )

    return {
        "schema": "dead-signal-armor",
        "schema_version": WEB_SCHEMA_VERSION,
        "generated_utc": utc_now(),
        "record_counts": {
            "armor_sets": len(sets),
            "set_pieces": sum(len(row["pieces"]) for row in sets),
            "key_armor": len(key_armor),
            "armor_pieces": sum(len(row["pieces"]) for row in sets) + len(key_armor),
        },
        "armor_sets": sets,
        "key_armor": key_armor,
        "crafting_material_groups": source.get("crafting_material_groups") or {},
    }


def _unique(values: list[Any]) -> tuple[bool, list[Any]]:
    seen = set()
    duplicates = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return not duplicates, duplicates


def _quality_status(blockers: list[str], warnings: list[str]) -> str:
    if blockers:
        return "BLOCKED"
    if warnings:
        return "PARTIAL"
    return "READY"


def build_quality_report(data_dir: Path, weapons_web: dict, armor_web: dict) -> dict:
    math_payload = load_json(data_dir / "weapon-math.json", {}) or {}
    profiles_payload = load_json(data_dir / "gun-profiles.json", {}) or {}
    image_coverage = load_json(data_dir / "image-coverage.json", {}) or {}

    weapons = weapons_web.get("weapons", [])
    weapon_ids = [row.get("canonical_id") for row in weapons]
    weapon_unique, weapon_duplicates = _unique(weapon_ids)
    weapon_blockers = []
    weapon_warnings = []
    if not weapons:
        weapon_blockers.append("No player-facing weapon records were published")
    if not weapon_unique:
        weapon_blockers.append(f"Duplicate canonical weapon IDs: {weapon_duplicates}")
    if not (math_payload.get("validation") or {}).get("passed", False):
        weapon_blockers.append("Static weapon math validation did not pass")
    incomplete_tiers = [row.get("canonical_id") for row in weapons if len((row.get("progression") or {}).get("gear_tiers") or []) != 5]
    if incomplete_tiers:
        weapon_blockers.append(f"Weapons without exactly five Gear Tier rows: {len(incomplete_tiers)}")
    unresolved_ranged = int((profiles_payload.get("record_counts") or {}).get("unresolved_gun_profiles") or 0)
    if unresolved_ranged:
        weapon_blockers.append(f"Unresolved firearm profiles: {unresolved_ranged}")
    missing_effects = sum(not bool(row.get("effect")) for row in weapons)
    missing_recipes = sum(
        not all((tier.get("recipe") for tier in (row.get("progression") or {}).get("gear_tiers") or []))
        for row in weapons
    )
    missing_images = sum(not bool(row.get("image_asset")) for row in weapons)
    if missing_effects:
        weapon_warnings.append(f"Weapon effect text unresolved or absent: {missing_effects}")
    if missing_recipes:
        weapon_warnings.append(f"Weapons with one or more missing Tier recipes: {missing_recipes}")
    if missing_images:
        weapon_warnings.append(f"Weapons without linked website artwork: {missing_images}")

    sets = armor_web.get("armor_sets", [])
    key_armor = armor_web.get("key_armor", [])
    armor_pieces = [piece for row in sets for piece in row.get("pieces", [])] + list(key_armor)
    armor_ids = [piece.get("canonical_id") for piece in armor_pieces]
    armor_unique, armor_duplicates = _unique(armor_ids)
    armor_blockers = []
    armor_warnings = []
    if not armor_pieces:
        armor_blockers.append("No player-facing armor records were published")
    if not armor_unique:
        armor_blockers.append(f"Duplicate canonical armor IDs: {armor_duplicates}")
    incomplete_armor_tiers = [piece.get("canonical_id") for piece in armor_pieces if len(piece.get("tiers") or []) != 5]
    if incomplete_armor_tiers:
        armor_warnings.append(f"Armor records without exactly five canonical Tier rows: {len(incomplete_armor_tiers)}")
    key_without_effect = sum(not bool(piece.get("key_effect")) for piece in key_armor)
    if key_without_effect:
        armor_warnings.append(f"Key Armor records without resolved effect text: {key_without_effect}")
    armor_without_recipes = sum(not bool(piece.get("crafting_recipes")) for piece in armor_pieces)
    if armor_without_recipes:
        armor_warnings.append(f"Armor records without crafting recipes: {armor_without_recipes}")
    armor_missing_images = sum(not bool(piece.get("image_asset")) for piece in armor_pieces)
    if armor_missing_images:
        armor_warnings.append(f"Armor records without linked website artwork: {armor_missing_images}")

    categories = {
        "weapons": {
            "status": _quality_status(weapon_blockers, weapon_warnings),
            "record_count": len(weapons),
            "blockers": weapon_blockers,
            "warnings": weapon_warnings,
            "metrics": {
                "canonical_ids_unique": weapon_unique,
                "exactly_five_tiers": len(weapons) - len(incomplete_tiers),
                "weapon_effects": len(weapons) - missing_effects,
                "complete_tier_recipes": len(weapons) - missing_recipes,
                "linked_artwork": len(weapons) - missing_images,
                "unresolved_firearm_profiles": unresolved_ranged,
                "tier_star_combinations": (math_payload.get("record_counts") or {}).get("tier_star_combinations", 0),
            },
        },
        "armor": {
            "status": _quality_status(armor_blockers, armor_warnings),
            "record_count": len(armor_pieces),
            "blockers": armor_blockers,
            "warnings": armor_warnings,
            "metrics": {
                "armor_sets": len(sets),
                "key_armor": len(key_armor),
                "canonical_ids_unique": armor_unique,
                "exactly_five_tiers": len(armor_pieces) - len(incomplete_armor_tiers),
                "key_armor_effects": len(key_armor) - key_without_effect,
                "records_with_crafting_recipes": len(armor_pieces) - armor_without_recipes,
                "linked_artwork": len(armor_pieces) - armor_missing_images,
            },
        },
    }
    overall = "READY"
    if any(row["status"] == "BLOCKED" for row in categories.values()):
        overall = "BLOCKED"
    elif any(row["status"] == "PARTIAL" for row in categories.values()):
        overall = "PARTIAL"

    return {
        "schema": "dead-signal-data-quality",
        "schema_version": QUALITY_SCHEMA_VERSION,
        "generated_utc": utc_now(),
        "policy": "Completeness is measured against internally mined player-facing records and required relationships, never against community-site item counts.",
        "overall_status": overall,
        "categories": categories,
        "image_coverage_totals": image_coverage.get("totals") or {},
    }


def build_relationship_graph(weapons_web: dict, armor_web: dict) -> dict:
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    edge_keys = set()

    def add_node(node_id: str, node_type: str, label: str | None = None, **details) -> None:
        if not node_id:
            return
        current = nodes.setdefault(node_id, {"id": node_id, "type": node_type})
        if label:
            current.setdefault("label", label)
        for key, value in details.items():
            if value not in (None, "", [], {}):
                current.setdefault(key, value)

    def add_edge(source: str, relation: str, target: str, evidence: dict) -> None:
        if not source or not target:
            return
        key = (source, relation, target, json.dumps(evidence, sort_keys=True, default=str))
        if key in edge_keys:
            return
        edge_keys.add(key)
        edges.append(
            {
                "source": source,
                "relation": relation,
                "target": target,
                "resolution_status": "proven-direct-link",
                "evidence": evidence,
            }
        )

    for weapon in weapons_web.get("weapons", []):
        weapon_id = weapon.get("canonical_id")
        add_node(weapon_id, "weapon", weapon.get("name"), blueprint_id=weapon.get("blueprint_id"), item_id=weapon.get("item_id"))
        profile = weapon.get("gun_profile") or {}
        gun_no = profile.get("gun_no")
        if gun_no:
            gun_id = f"gun:{gun_no}"
            add_node(gun_id, "gun", f"gun_no {gun_no}", gun_no=gun_no)
            add_edge(weapon_id, "maps_to_gun", gun_id, {"dataset": "gun-profiles.json", "field": "gun_no"})
            linked = profile.get("linked_ids") or {}
            bullet = linked.get("bullet_no")
            if bullet:
                bullet_id = f"ammo:{bullet}"
                add_node(bullet_id, "ammo", f"item {bullet}", item_id=bullet)
                add_edge(gun_id, "uses_ammo", bullet_id, {"dataset": "gun-profiles.json", "field": "linked_ids.bullet_no"})
            gun_skill = linked.get("gun_skill_no")
            if gun_skill:
                skill_id = f"skill:{gun_skill}"
                add_node(skill_id, "skill", f"skill {gun_skill}")
                add_edge(gun_id, "links_skill", skill_id, {"dataset": "gun-profiles.json", "field": "linked_ids.gun_skill_no"})

        effect = weapon.get("effect") or {}
        skill_code = effect.get("skill_code")
        if skill_code:
            skill_id = f"passive-skill:{skill_code}"
            add_node(skill_id, "passive_skill", effect.get("name") or str(skill_code), skill_level=effect.get("skill_level"))
            add_edge(weapon_id, "has_fixed_skill", skill_id, {"dataset": "weapons.json", "field": "effect.skill_code"})
            buff_id = effect.get("buff_id")
            if buff_id:
                buff_node = f"buff:{buff_id}"
                add_node(buff_node, "buff", effect.get("name") or f"buff {buff_id}")
                add_edge(skill_id, "resolves_buff", buff_node, {"dataset": "weapons.json", "field": "effect.buff_id"})
            keyword_buff = effect.get("keyword_buff_id")
            if keyword_buff:
                target = f"buff:{keyword_buff}"
                add_node(target, "buff", f"keyword buff {keyword_buff}")
                add_edge(skill_id, "keyword_buff", target, {"dataset": "weapons.json", "field": "effect.keyword_buff_id"})
            keyword_status = effect.get("keyword_status_id")
            if keyword_status:
                target = f"status:{keyword_status}"
                add_node(target, "status", f"status {keyword_status}")
                add_edge(skill_id, "keyword_status", target, {"dataset": "weapons.json", "field": "effect.keyword_status_id"})

    for armor_set in armor_web.get("armor_sets", []):
        set_id = armor_set.get("canonical_id")
        add_node(set_id, "armor_set", armor_set.get("name"), suit_id=armor_set.get("suit_id"))
        for piece in armor_set.get("pieces", []):
            piece_id = piece.get("canonical_id")
            add_node(piece_id, "armor_piece", piece.get("name"), suit_id=piece.get("suit_id"), blueprint_id=piece.get("blueprint_id"), slot=piece.get("slot"))
            add_edge(piece_id, "belongs_to_set", set_id, {"dataset": "armor-sets.json", "field": "armor_sets[].pieces"})

    for piece in armor_web.get("key_armor", []):
        piece_id = piece.get("canonical_id")
        add_node(piece_id, "key_armor", piece.get("name"), blueprint_id=piece.get("blueprint_id"), slot=piece.get("slot"))
        skill_code = piece.get("passive_skill_code")
        if skill_code:
            skill_id = f"passive-skill:{skill_code}"
            add_node(skill_id, "passive_skill", piece.get("passive_skill_name") or str(skill_code))
            add_edge(piece_id, "has_fixed_skill", skill_id, {"dataset": "armor-sets.json", "field": "key_armor[].passive_skill_code"})
            buff_id = piece.get("buff_id")
            if buff_id:
                buff_node = f"buff:{buff_id}"
                add_node(buff_node, "buff", f"buff {buff_id}")
                add_edge(skill_id, "resolves_buff", buff_node, {"dataset": "armor-sets.json", "field": "key_armor[].buff_id"})

    nodes_sorted = sorted(nodes.values(), key=lambda row: (row.get("type", ""), row.get("id", "")))
    edges.sort(key=lambda row: (row["source"], row["relation"], row["target"]))
    return {
        "schema": "dead-signal-relationship-graph",
        "schema_version": GRAPH_SCHEMA_VERSION,
        "generated_utc": utc_now(),
        "scope": "Direct mined identity relationships only. Trigger conditions, proc chance, duration, stacks, cooldowns, and modifier semantics remain unresolved unless a later resolver proves them.",
        "record_counts": {"nodes": len(nodes_sorted), "edges": len(edges)},
        "nodes": nodes_sorted,
        "edges": edges,
    }


def _record_map(payload: dict, collection: str) -> dict[str, dict]:
    result = {}
    for row in payload.get(collection, []):
        key = row.get("canonical_id")
        if key:
            result[str(key)] = row
    return result


def _flatten_armor_records(payload: dict) -> dict[str, dict]:
    result = {}
    for row in payload.get("armor_sets", []):
        if row.get("canonical_id"):
            result[row["canonical_id"]] = row
        for piece in row.get("pieces", []):
            if piece.get("canonical_id"):
                result[piece["canonical_id"]] = piece
    for piece in payload.get("key_armor", []):
        if piece.get("canonical_id"):
            result[piece["canonical_id"]] = piece
    return result


def _changed_paths(before: Any, after: Any, prefix: str = "", limit: int = 40) -> list[str]:
    if before == after:
        return []
    if len(prefix) > 180:
        return [prefix]
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(set(before) | set(after), key=str):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after:
                result.append(path)
            else:
                result.extend(_changed_paths(before[key], after[key], path, limit))
            if len(result) >= limit:
                return result[:limit]
        return result
    if isinstance(before, list) and isinstance(after, list):
        return [prefix or "<list>"]
    return [prefix or "<value>"]


def _diff_records(previous: dict[str, dict], current: dict[str, dict]) -> dict:
    previous_ids = set(previous)
    current_ids = set(current)
    added = sorted(current_ids - previous_ids)
    removed = sorted(previous_ids - current_ids)
    changed = []
    for record_id in sorted(previous_ids & current_ids):
        if _canonical_hash(previous[record_id]) == _canonical_hash(current[record_id]):
            continue
        changed.append({"canonical_id": record_id, "fields": _changed_paths(previous[record_id], current[record_id])})
    return {"added": added, "removed": removed, "changed": changed}


def build_change_report(previous_weapons: dict | None, previous_armor: dict | None, weapons: dict, armor: dict) -> dict:
    if not previous_weapons and not previous_armor:
        return {
            "schema": "dead-signal-change-report",
            "schema_version": 1,
            "generated_utc": utc_now(),
            "status": "baseline-created",
            "categories": {},
        }
    categories = {
        "weapons": _diff_records(_record_map(previous_weapons or {}, "weapons"), _record_map(weapons, "weapons")),
        "armor": _diff_records(_flatten_armor_records(previous_armor or {}), _flatten_armor_records(armor)),
    }
    return {
        "schema": "dead-signal-change-report",
        "schema_version": 1,
        "generated_utc": utc_now(),
        "status": "compared-to-previous-published-web-snapshot",
        "categories": categories,
    }


def render_change_report(report: dict) -> str:
    lines = ["DEAD SIGNAL MINER — CHANGE REPORT", f"Generated: {report.get('generated_utc', '')}", ""]
    if report.get("status") == "baseline-created":
        lines.append("No previous web snapshot was available. This run establishes the comparison baseline.")
        return "\n".join(lines) + "\n"
    for category, delta in report.get("categories", {}).items():
        lines.append(category.upper())
        lines.append(f"  + added:   {len(delta.get('added', []))}")
        lines.append(f"  - removed: {len(delta.get('removed', []))}")
        lines.append(f"  ~ changed: {len(delta.get('changed', []))}")
        for record_id in delta.get("added", []):
            lines.append(f"    + {record_id}")
        for record_id in delta.get("removed", []):
            lines.append(f"    - {record_id}")
        for row in delta.get("changed", []):
            fields = ", ".join(row.get("fields", [])[:8]) or "record changed"
            lines.append(f"    ~ {row.get('canonical_id')}: {fields}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _catalog_index(data_dir: Path) -> dict:
    datasets = {}
    for path in sorted(data_dir.glob("*.json")):
        payload = load_json(path, {}) or {}
        counts = payload.get("record_counts")
        if isinstance(counts, dict):
            datasets[path.name] = counts
    return {
        "schema": "dead-signal-catalog-index",
        "schema_version": 1,
        "generated_utc": utc_now(),
        "datasets": datasets,
    }


def build_snapshot_manifest(
    published: Path,
    miner_version: str,
    base_sha256: str,
    current_sha256: str,
    quality: dict,
    executable_sha256: str = "",
    resource_fingerprint: str = "",
) -> dict:
    files = []
    for folder in (published / "data", published / "web", published / "reports"):
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if not path.is_file() or path.suffix.casefold() not in {".json", ".txt"}:
                continue
            files.append(
                {
                    "path": path.relative_to(published).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )

    source_dir = Path(__file__).resolve().parent
    pipeline_sources = (
        "normalize_weapons.py",
        "normalize_armor.py",
        "normalize_extended.py",
        "combat_resolver.py",
        "export_weapon_math.py",
        "export_weapon_configuration.py",
        "export_gun_profiles.py",
        "link_published_images.py",
        "publish_web_data.py",
    )
    code_fingerprints = {}
    for name in pipeline_sources:
        path = source_dir / name
        if path.is_file():
            code_fingerprints[name] = sha256_file(path)

    return {
        "schema": "dead-signal-snapshot-manifest",
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_utc": utc_now(),
        "miner_version": miner_version,
        "source_fingerprints": {
            "base_script_sha256": base_sha256,
            "current_script_sha256": current_sha256,
            "game_executable_sha256": executable_sha256,
            "resource_index_fingerprint": resource_fingerprint,
            "pipeline_source_sha256": code_fingerprints,
        },
        "quality_status": quality.get("overall_status"),
        "files": files,
    }


def publish(
    data_dir: Path,
    published: Path,
    miner_version: str,
    base_sha256: str = "",
    current_sha256: str = "",
    executable_sha256: str = "",
    resource_fingerprint: str = "",
) -> dict:
    web_dir = published / "web"
    reports_dir = published / "reports"
    previous_weapons = load_json(web_dir / "weapons.json", None)
    previous_armor = load_json(web_dir / "armor.json", None)

    weapons = build_weapon_projection(data_dir)
    configuration = build_configuration_projection(data_dir)
    armor = build_armor_projection(data_dir)
    quality = build_quality_report(data_dir, weapons, armor)
    graph = build_relationship_graph(weapons, armor)
    changes = build_change_report(previous_weapons, previous_armor, weapons, armor)
    catalog = _catalog_index(data_dir)

    web_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    write_json(web_dir / "weapons.json", weapons)
    write_json(web_dir / "weapon-configuration.json", configuration)
    write_json(web_dir / "armor.json", armor)
    write_json(data_dir / "relationship-graph.json", graph)
    write_json(web_dir / "relationship-graph.json", graph)
    write_json(web_dir / "catalog-index.json", catalog)
    write_json(reports_dir / "data-quality.json", quality)
    write_json(reports_dir / "change-report.json", changes)
    (reports_dir / "CHANGE-REPORT.txt").write_text(render_change_report(changes), encoding="utf-8")

    manifest = build_snapshot_manifest(
        published, miner_version, base_sha256, current_sha256, quality, executable_sha256, resource_fingerprint
    )
    write_json(published / "snapshot-manifest.json", manifest)
    return {
        "web": {
            "weapons": str((web_dir / "weapons.json").resolve()),
            "weapon_configuration": str((web_dir / "weapon-configuration.json").resolve()),
            "armor": str((web_dir / "armor.json").resolve()),
            "relationship_graph": str((web_dir / "relationship-graph.json").resolve()),
            "catalog_index": str((web_dir / "catalog-index.json").resolve()),
        },
        "quality": quality,
        "change_report": changes,
        "snapshot_manifest": str((published / "snapshot-manifest.json").resolve()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish Dead Signal website datasets and integrity reports")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--published", type=Path, required=True)
    parser.add_argument("--miner-version", required=True)
    parser.add_argument("--base-sha256", default="")
    parser.add_argument("--current-sha256", default="")
    parser.add_argument("--executable-sha256", default="")
    parser.add_argument("--resource-fingerprint", default="")
    args = parser.parse_args()
    result = publish(
        args.data_dir, args.published, args.miner_version, args.base_sha256, args.current_sha256,
        args.executable_sha256, args.resource_fingerprint
    )
    quality = result["quality"]
    print(
        f"Web publish: {quality['overall_status']} · "
        f"weapons={quality['categories']['weapons']['record_count']} · "
        f"armor={quality['categories']['armor']['record_count']}"
    )
    for category_name, category in quality.get("categories", {}).items():
        for blocker in category.get("blockers", []):
            print(f"Quality blocker [{category_name}]: {blocker}")
        for warning in category.get("warnings", []):
            print(f"Quality warning [{category_name}]: {warning}")
    print(f"Snapshot manifest: {result['snapshot_manifest']}")

    # BLOCKED is a data-quality state, not an extractor crash. The reports and
    # manifest are intentionally written even when a website dataset should not
    # be promoted yet. Exceptions still propagate and fail the Miner normally.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
