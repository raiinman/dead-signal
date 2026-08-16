"""Guided typed Weapon schema tracing for Dead Signal Data Intelligence.

This automates the manual research loop used in NeoX Explorer:

    Weapon identity -> exact owning record -> typed outbound field -> next owner

The tracer deliberately does *not* recursively follow every equal scalar in the
reference index. Each identity kind has a bounded set of canonical/diagnostic
owner tables *and* accepted owning fields. Exact occurrences outside those
owner rules are counted as references for provenance, but they are not traversed.

The output is research evidence only. It never modifies published web data and
never promotes a field to VERIFIED/PUBLISHABLE by itself.
"""
from __future__ import annotations

from collections import Counter, deque
from pathlib import Path
from typing import Any

from neox_data_explorer import NeoXDataExplorer
from research_console import ResearchConsole


SCHEMA_VERSION = 2
MAX_DEPTH = 6
MAX_IDENTITIES = 250
MAX_OWNER_RECORDS_PER_IDENTITY = 12
MAX_EXACT_REFS = 5000

# A table match alone is not enough. The full 120-weapon trace proved that equal
# scalars inside an otherwise relevant table can still jump into a neighboring
# weapon family (for example blueprint_template_no=10 being mistaken for a
# blueprint identity). Each rule therefore names both the table and the fields
# that are allowed to establish ownership for that identity kind.
OWNER_RULES: dict[str, dict[str, frozenset[str]]] = {
    "blueprint_id": {
        "game_common/data/gun_blueprint_data.json": frozenset({"record_id", "blueprint_id", "blueprint_no"}),
        "game_common/data/gun_blueprint_chip_map_data.json": frozenset({"blueprint_id", "blueprint_no"}),
        "game_common/data/gun_blueprint_attr_data.json": frozenset({"blueprint_id", "blueprint_no"}),
        "game_common/data/blueprint_recipe_season_data.json": frozenset({"record_id", "blueprint_id", "blueprint_no"}),
    },
    "item_id": {
        "game_common/data/equip_data.json": frozenset({"record_id"}),
        "game_common/data/item_data.json": frozenset({"record_id"}),
        "game_common/data/item_to_gun_mapping_data.json": frozenset({"record_id", "item_id", "item_no"}),
        "game_common/data/equip_origin_data.json": frozenset({"record_id"}),
    },
    "tier_item_id": {
        "game_common/data/equip_data.json": frozenset({"record_id"}),
        "game_common/data/item_data.json": frozenset({"record_id"}),
        "game_common/data/item_to_gun_mapping_data.json": frozenset({"record_id", "item_id", "item_no"}),
    },
    "gun_no": {
        "game_common/data/gun_base_params_data.json": frozenset({"record_id"}),
        "game_common/data/item_to_gun_mapping_data.json": frozenset({"gun_no"}),
        "game_common/data/gun_stability_data.json": frozenset({"record_id", "gun_no"}),
    },
    "prototype_id": {
        "game_common/data/weapon_prototype_data.json": frozenset({"record_id", "prototype_id", "prototype_no"}),
    },
    "fragment_id": {
        "game_common/data/gun_blueprint_chip_map_data.json": frozenset({"record_id", "fragment_id", "fragment_no"}),
        "game_common/data/item_data.json": frozenset({"record_id"}),
    },
    "ammo_item_id": {
        "game_common/data/item_data.json": frozenset({"record_id"}),
        "game_common/data/forge_data.json": frozenset({"item_id", "item_no"}),
    },
    "bullet_base_id": {
        "game_common/data/bullet_base_params_data.json": frozenset({"record_id", "bullet_base_id", "bullet_base_no"}),
    },
    "bullet_pattern_id": {
        "client_data/bullet_pattern_data.json": frozenset({"record_id", "pattern_no", "bullet_pattern_no"}),
    },
    "bullet_scatter_id": {
        "game_common/data/bullet_scatter_data.json": frozenset({"record_id", "scatter_no", "bullet_scatter_no"}),
        "client_data/bullet_scatter_data.json": frozenset({"record_id", "scatter_no", "bullet_scatter_no"}),
    },
    "crosshair_id": {
        "client_data/gun_crosshair_data.json": frozenset({"record_id", "crosshair_no", "bullet_aim_no"}),
        "client_data/crosshair_data.json": frozenset({"record_id", "crosshair_no", "bullet_aim_no"}),
    },
    "accessory_sequence_id": {
        "game_common/data/gun_accessory_slot_params_data.json": frozenset({"accessory_seq_no"}),
        "game_common/data/weapon_accessory_data.json": frozenset({"record_id", "accessory_seq_no"}),
    },
    "skill_id": {
        "game_common/data/passive_skill_data.json": frozenset({"record_id", "skill_id", "skill_no", "skill_code"}),
        "game_common/data/skill_data.json": frozenset({"record_id", "skill_id", "skill_no", "skill_code"}),
    },
    "buff_id": {
        "game_common/data/buff/buff_data.json": frozenset({"record_id", "buff_id", "buff_no"}),
        "game_common/data/buff/buff_data_0.json": frozenset({"record_id", "buff_id", "buff_no"}),
        "game_common/data/buff/buff_data_1.json": frozenset({"record_id", "buff_id", "buff_no"}),
        "game_common/data/buff/buff_data_2.json": frozenset({"record_id", "buff_id", "buff_no"}),
    },
    "forge_id": {
        "game_common/data/forge_data.json": frozenset({"record_id", "forge_id", "forge_no"}),
    },
}

# Compatibility for UI/tests that only need the ordered table list.
OWNER_TABLES: dict[str, tuple[str, ...]] = {
    kind: tuple(rules) for kind, rules in OWNER_RULES.items()
}


def _scalar(value: object) -> str:
    return str(value).strip()


def _field_kind(field: object) -> str | None:
    """Map an explicit schema field to the identity type it carries.

    This is intentionally explicit. The first fleet trace showed that a generic
    suffix heuristic turns metadata fields such as blueprint_template_no into
    false identities and then walks unrelated Weapon families.
    """
    name = str(field or "").strip().casefold()
    exact = {
        "blueprint_id": "blueprint_id",
        "blueprint_no": "blueprint_id",
        "prototype_id": "prototype_id",
        "prototype_no": "prototype_id",
        "gun_no": "gun_no",
        "gun_item_no": "item_id",
        "item_id": "item_id",
        "item_no": "item_id",
        "equip_id": "item_id",
        "equip_no": "item_id",
        "equip_origin_id": "item_id",
        "fragment_id": "fragment_id",
        "fragment_no": "fragment_id",
        "bullet_no": "ammo_item_id",
        "bullet_base_no": "bullet_base_id",
        "bullet_pattern_no": "bullet_pattern_id",
        "bullet_scatter_no": "bullet_scatter_id",
        "bullet_aim_no": "crosshair_id",
        "accessory_seq_no": "accessory_sequence_id",
        "fixed_skill": "skill_id",
        "fixed_skill_code": "skill_id",
        "skill_id": "skill_id",
        "skill_no": "skill_id",
        "gun_skill_no": "skill_id",
        "buff_id": "buff_id",
        "buff_no": "buff_id",
        "keyword_buff_id": "buff_id",
        "forge_id": "forge_id",
        "forge_no": "forge_id",
        "corr_forge_no": "forge_id",
    }
    return exact.get(name)


def _owner_ref_matches(kind: str, row: dict[str, Any]) -> bool:
    table = str(row.get("table") or "")
    field = str(row.get("field") or "").strip().casefold()
    allowed_fields = OWNER_RULES.get(kind, {}).get(table)
    return bool(allowed_fields and field in allowed_fields)


def _reference_candidates(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    """Summarize where an unresolved exact value actually occurs.

    This lets a real snapshot teach us a missing owner rule without promoting any
    of those candidates automatically.
    """
    counts: Counter[tuple[str, str]] = Counter()
    for row in rows:
        counts[(str(row.get("table") or ""), str(row.get("field") or ""))] += 1
    return [
        {"table": table, "field": field, "count": count}
        for (table, field), count in counts.most_common(limit)
    ]


def _seed_rows(weapon: dict[str, Any], console: ResearchConsole) -> list[dict[str, str]]:
    seeds: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, value: object, source: str) -> None:
        if value in (None, "", 0, "0", False, True):
            return
        row = (kind, _scalar(value))
        if row in seen:
            return
        seen.add(row)
        seeds.append({"kind": kind, "value": row[1], "source": source})

    add("blueprint_id", weapon.get("blueprint_id"), "weapon.blueprint_id")
    add("item_id", weapon.get("item_id"), "weapon.item_id")
    add("prototype_id", weapon.get("prototype_id"), "weapon.prototype_id")
    acquisition = weapon.get("acquisition") or {}
    add("fragment_id", acquisition.get("fragment_id"), "weapon.acquisition.fragment_id")
    ranged = (weapon.get("baseline") or {}).get("ranged") or {}
    add("bullet_pattern_id", ranged.get("bullet_pattern_id"), "weapon.baseline.ranged.bullet_pattern_id")
    for tier in ((weapon.get("progression") or {}).get("gear_tiers") or []):
        if not isinstance(tier, dict):
            continue
        add("tier_item_id", tier.get("item_id"), "weapon.progression.gear_tiers.item_id")
        add("gun_no", tier.get("gun_no"), "weapon.progression.gear_tiers.gun_no")
    add("skill_id", console._fixed_skill(weapon), "weapon.fixed_skill")
    return seeds


def _preferred_layer(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return one representative occurrence per exact record, preferring current."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    order: list[tuple[str, str]] = []
    for row in rows:
        key = (str(row.get("table") or ""), str(row.get("record_id") or ""))
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(row)
    selected: list[dict[str, Any]] = []
    for key in order:
        candidates = grouped[key]
        current = [row for row in candidates if row.get("source") == "current"]
        base = [row for row in candidates if row.get("source") == "base"]
        selected.append((current or base or candidates)[0])
    return selected


class DeadSignalWeaponSchemaTrace:
    """Follow a Weapon through canonical NeoX owner records using typed fields."""

    def __init__(self, output: Path | str):
        self.console = ResearchConsole(output)
        self.explorer = NeoXDataExplorer(output)
        self.output = self.console.output

    def trace(self, identity: object, *, max_depth: int = MAX_DEPTH) -> dict[str, Any]:
        if max_depth < 1 or max_depth > 12:
            raise ValueError("Weapon schema trace depth must be between 1 and 12")
        weapon = self.console.find_weapon(identity)
        seeds = _seed_rows(weapon, self.console)
        queue = deque((row["kind"], row["value"], 0, row["source"]) for row in seeds)
        queued = {(row["kind"], row["value"]) for row in seeds}
        processed: set[tuple[str, str]] = set()
        identities: list[dict[str, Any]] = []
        records: dict[tuple[str, str, str], dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        skipped_reference_counts: Counter[str] = Counter()

        while queue and len(processed) < MAX_IDENTITIES:
            kind, value, depth, discovered_from = queue.popleft()
            key = (kind, value)
            if key in processed:
                continue
            processed.add(key)
            allowed = OWNER_TABLES.get(kind, ())
            all_refs = self.console._trace(value, MAX_EXACT_REFS)
            owner_refs = [row for row in all_refs if _owner_ref_matches(kind, row)]
            owner_refs = _preferred_layer(owner_refs)
            owner_refs.sort(key=lambda row: (
                0 if str(row.get("record_id")) == value else 1,
                allowed.index(str(row.get("table"))) if str(row.get("table")) in allowed else 999,
                str(row.get("record_id")),
            ))
            owner_refs = owner_refs[:MAX_OWNER_RECORDS_PER_IDENTITY]
            skipped_reference_counts[kind] += max(0, len(all_refs) - len(owner_refs))
            state = "VERIFIED" if owner_refs else ("EXACT-REFS-NO-TYPED-OWNER" if all_refs else "UNRESOLVED")
            identity_row = {
                "kind": kind,
                "value": value,
                "depth": depth,
                "discovered_from": discovered_from,
                "exact_reference_count": len(all_refs),
                "followed_owner_record_count": len(owner_refs),
                "owner_tables": list(allowed),
                "state": state,
            }
            if not owner_refs and all_refs:
                identity_row["reference_candidates"] = _reference_candidates(all_refs)
            identities.append(identity_row)

            for ref in owner_refs:
                layer = str(ref.get("source") or "")
                table = str(ref.get("table") or "")
                record_id = str(ref.get("record_id") or "")
                record_key = (layer, table, record_id)
                edges.append({
                    "from_type": "identity", "from_kind": kind, "from": value,
                    "to_type": "record", "layer": layer, "table": table,
                    "record_id": record_id, "field": ref.get("field"),
                    "json_pointer": ref.get("json_pointer"), "match": "exact",
                    "relationship": "typed-owner-field-exact-reference", "authoritative": True,
                })
                if record_key in records:
                    continue
                try:
                    opened = self.explorer.record(table, record_id, layer=layer)
                except (ValueError, OSError):
                    continue
                outbound = []
                for field in opened.get("fields") or []:
                    next_kind = _field_kind(field.get("field"))
                    scalar_value = field.get("value")
                    if next_kind is None or scalar_value in (None, "", 0, "0", False, True):
                        continue
                    next_value = _scalar(scalar_value)
                    relationship = {
                        "kind": next_kind,
                        "value": next_value,
                        "field": field.get("field"),
                        "json_pointer": field.get("json_pointer"),
                    }
                    outbound.append(relationship)
                    edges.append({
                        "from_type": "record", "layer": layer, "table": table,
                        "record_id": record_id, "to_type": "identity",
                        "to_kind": next_kind, "to": next_value,
                        "field": field.get("field"), "json_pointer": field.get("json_pointer"),
                        "relationship": "typed-schema-field", "authoritative": False,
                        "note": "Typed outbound field; next identity->owner edge must independently resolve by exact tracer evidence.",
                    })
                    next_key = (next_kind, next_value)
                    if depth < max_depth and next_kind in OWNER_RULES and next_key not in queued and next_key not in processed:
                        queue.append((next_kind, next_value, depth + 1, f"{layer}|{table}|{record_id}{field.get('json_pointer') or ''}"))
                        queued.add(next_key)
                records[record_key] = {
                    "layer": layer,
                    "table": table,
                    "record_id": record_id,
                    "matched_identity": {"kind": kind, "value": value},
                    "matched_field": ref.get("field"),
                    "matched_json_pointer": ref.get("json_pointer"),
                    "outbound_typed_identities": outbound,
                    "fields": opened.get("fields") or [],
                }

        return {
            "schema": "dead-signal-guided-weapon-schema-trace",
            "schema_version": SCHEMA_VERSION,
            "brand": "Dead Signal",
            "subject": {
                "canonical_id": weapon.get("canonical_id"),
                "name": weapon.get("name"),
                "blueprint_id": weapon.get("blueprint_id"),
                "item_id": weapon.get("item_id"),
                "prototype_id": weapon.get("prototype_id"),
                "category": weapon.get("category"),
            },
            "seeds": seeds,
            "record_counts": {
                "identities_processed": len(processed),
                "records_opened": len(records),
                "edges": len(edges),
                "queued_remaining": len(queue),
                "skipped_broad_exact_references": sum(skipped_reference_counts.values()),
            },
            "identities": identities,
            "records": list(records.values()),
            "edges": edges,
            "policy": {
                "workflow": "Locate exact identity -> require typed owner table + owner field -> open exact NeoX record -> harvest explicit typed outbound fields -> independently exact-resolve the next owner.",
                "matching": "No fuzzy, substring, similar-ID, bare-number, table-only, or metadata-field traversal. Equal scalars outside the identity kind's explicit owner table/field rules are provenance only and are not followed.",
                "authority": "Identity-to-record edges are authoritative only when the exact tracer occurrence satisfies a typed owner table/field rule. Record-to-identity fields are typed schema leads until the next exact owner edge resolves.",
                "scope": "Bounded guided research trace; the exhaustive Identity Map ZIP remains available separately.",
                "publication": "Research evidence only. This trace never promotes or publishes player-facing data automatically.",
            },
        }
