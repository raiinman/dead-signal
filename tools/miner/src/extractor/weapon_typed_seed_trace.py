"""Typed, locality-bounded tracing for blank fixed-skill weapon references.

Exact scalar equality is not enough for small numeric identities, and a match in
one node of an aggregate logic-tree record must not inherit references from an
unrelated sibling node. This tracer therefore requires typed first-hop identity
matching and harvests outbound references only from the local matched list node.

Shared gun_skill_no values are preserved as system/progression evidence, but are
kept separate from weapon-specific mechanic candidates.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any


_ITEM_KINDS = {"item_id", "tier_item_id"}
_GUN_KINDS = {"gun_no", "tier_gun_no"}


def _field_matches_kind(field: str, kind: str) -> bool:
    text = str(field or "").lower()
    if kind == "blueprint_id":
        return "blueprint" in text
    if kind in _ITEM_KINDS:
        return "item" in text
    if kind == "prototype_id":
        return "prototype" in text
    if kind in _GUN_KINDS:
        return bool(re.search(r"(?:^|_)gun(?:_|$)", text))
    if kind == "short_description_handle":
        return text == "short_desc"
    return False


def _record_id_matches_kind(relative: str, kind: str) -> bool:
    path = relative.lower()
    if kind == "blueprint_id":
        return "blueprint" in path
    if kind in _ITEM_KINDS:
        return "item_data" in path or "equip_data" in path
    if kind == "prototype_id":
        return "prototype" in path
    if kind in _GUN_KINDS:
        return "gun_" in path or "/gun" in path
    return False


def _unescape_pointer(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")


def _local_scope(record: Any, pointer: str) -> tuple[Any, str]:
    """Return the deepest matched list element and its pointer.

    Many extracted logic-tree tables expose one top-level record such as
    ``node_list`` whose value is a list of independent nodes. If a weapon item is
    mentioned in node 1, references from node 24 are not evidence for that item.
    For ordinary dict records (gun_base_params_data, item_data, etc.) the entire
    record remains the local scope.
    """
    parts = [_unescape_pointer(part) for part in str(pointer or "").split("/") if part]
    current = record
    scope = record
    scope_parts: list[str] = []
    walked: list[str] = []
    for part in parts:
        if isinstance(current, list):
            try:
                index = int(part)
                current = current[index]
            except (ValueError, IndexError, TypeError):
                break
            walked.append(part)
            scope = current
            scope_parts = list(walked)
        elif isinstance(current, dict):
            if part not in current:
                break
            current = current[part]
            walked.append(part)
        else:
            break
    return scope, "/" + "/".join(scope_parts) if scope_parts else ""


def _gun_skill_usage(module: Any, base: Path, current: Path) -> dict[str, set[str]]:
    usage: dict[str, set[str]] = defaultdict(set)
    for layer, root in (("base", base), ("current", current)):
        path = root / "game_common/data/gun_base_params_data.json"
        if not path.is_file():
            continue
        for record_id, record in module._rows(path).items():
            if not isinstance(record, dict):
                continue
            value = module._scalar(record.get("gun_skill_no"))
            if value:
                usage[value].add(f"{layer}:{record_id}")
    return usage


def _typed_first_pass(module: Any, base: Path, current: Path, seed_owners: dict[str, list[tuple[int, str]]]):
    found: dict[str, list[dict[str, Any]]] = defaultdict(list)
    wanted = set(seed_owners)
    for layer, root, path in module._relevant_tables(base, current):
        relative = path.relative_to(root).as_posix()
        for record_id, record in module._rows(path).items():
            record_key = module._scalar(record_id)
            if record_key in wanted:
                for _, kind in seed_owners[record_key]:
                    if _record_id_matches_kind(relative, kind):
                        found[record_key].append({
                            "source": layer,
                            "table": relative,
                            "record_id": str(record_id),
                            "matched_via": [{"field": "record_id", "json_pointer": "/data", "seed_kind": kind}],
                            "outbound_references": module._record_reference_values(record),
                            "scope_pointer": "",
                        })

            for pointer, field, raw in module._walk(record):
                value = module._scalar(raw)
                if value not in wanted:
                    continue
                for _, kind in seed_owners[value]:
                    if not _field_matches_kind(field, kind):
                        continue
                    scope, scope_pointer = _local_scope(record, pointer)
                    found[value].append({
                        "source": layer,
                        "table": relative,
                        "record_id": str(record_id),
                        "matched_via": [{"field": field, "json_pointer": pointer, "seed_kind": kind}],
                        "outbound_references": module._record_reference_values(scope),
                        "scope_pointer": scope_pointer,
                    })
    return found


def _typed_trace(module: Any, payload: dict[str, Any], base: Path, current: Path, equipment: dict[str, Any]) -> dict[str, Any]:
    weapons = [row for row in payload.get("weapons", []) if isinstance(row, dict)]
    targets = [row for row in weapons if not module._fixed_skill_code(row)]
    seed_owners: dict[str, list[tuple[int, str]]] = defaultdict(list)
    seeds_by_weapon: dict[int, list[dict[str, str]]] = {}
    for index, weapon in enumerate(targets):
        seeds = module._weapon_seeds(weapon, equipment)
        seeds_by_weapon[index] = seeds
        for seed in seeds:
            seed_owners[seed["value"]].append((index, seed["kind"]))

    first_pass = _typed_first_pass(module, base, current, seed_owners)
    gun_skill_usage = _gun_skill_usage(module, base, current)
    related_by_weapon: dict[int, list[dict[str, Any]]] = defaultdict(list)
    candidates_by_weapon: dict[int, dict[tuple[str, str, str, str], dict[str, Any]]] = defaultdict(dict)
    system_by_weapon: dict[int, dict[tuple[str, str, str, str], dict[str, Any]]] = defaultdict(dict)

    for seed_value, occurrences in first_pass.items():
        for weapon_index, seed_kind in seed_owners.get(seed_value, []):
            for occurrence in occurrences:
                vias = [via for via in occurrence.get("matched_via", []) if via.get("seed_kind") == seed_kind]
                if not vias:
                    continue
                if len(related_by_weapon[weapon_index]) < module.MAX_RELATED_RECORDS_PER_WEAPON:
                    related_by_weapon[weapon_index].append({
                        "seed_kind": seed_kind,
                        "seed_value": seed_value,
                        "source": occurrence["source"],
                        "table": occurrence["table"],
                        "record_id": occurrence["record_id"],
                        "scope_pointer": occurrence.get("scope_pointer") or "",
                        "matched_via": [{k: v for k, v in via.items() if k != "seed_kind"} for via in vias],
                    })
                for reference in occurrence.get("outbound_references") or []:
                    if not reference.get("mechanic_like"):
                        continue
                    candidate_value = str(reference.get("value") or "")
                    if not candidate_value or candidate_value in seed_owners:
                        continue
                    field = str(reference.get("field") or "")
                    key = (occurrence["table"], occurrence["record_id"], field, candidate_value)
                    entry = {
                        "source": occurrence["source"],
                        "table": occurrence["table"],
                        "record_id": occurrence["record_id"],
                        "scope_pointer": occurrence.get("scope_pointer") or "",
                        "field": field,
                        "json_pointer": reference.get("json_pointer"),
                        "value": candidate_value,
                    }
                    if field == "gun_skill_no" and len(gun_skill_usage.get(candidate_value, set())) > 1:
                        entry["classification"] = "shared-gun-system-skill"
                        entry["gun_record_usage_count"] = len(gun_skill_usage[candidate_value])
                        system_by_weapon[weapon_index][key] = entry
                    elif len(candidates_by_weapon[weapon_index]) < module.MAX_MECHANIC_CANDIDATES_PER_WEAPON:
                        entry["classification"] = "weapon-specific-mechanic-reference-candidate"
                        candidates_by_weapon[weapon_index][key] = entry

    all_refs = {
        entry["value"]
        for buckets in (candidates_by_weapon, system_by_weapon)
        for rows in buckets.values()
        for entry in rows.values()
    }
    second_pass = module._scan_for_exact_values(base, current, all_refs, capture_record_references=False)

    def resolve(entry: dict[str, Any]) -> None:
        entry["exact_target_occurrences"] = [
            {"source": row["source"], "table": row["table"], "record_id": row["record_id"], "matched_via": row["matched_via"]}
            for row in second_pass.get(entry["value"], [])[:module.MAX_TARGET_OCCURRENCES_PER_CANDIDATE]
        ]
        entry["exact_target_record_found"] = any(
            any(via.get("field") == "record_id" for via in row.get("matched_via") or [])
            for row in second_pass.get(entry["value"], [])
        )

    status_counts: dict[str, int] = defaultdict(int)
    report_rows = []
    for index, weapon in enumerate(targets):
        candidates = list(candidates_by_weapon[index].values())
        system_refs = list(system_by_weapon[index].values())
        for entry in candidates + system_refs:
            resolve(entry)
        related = related_by_weapon[index]
        if candidates:
            status = "blank-fixed-skill-local-typed-trace-found-weapon-specific-candidates"
        elif system_refs:
            status = "blank-fixed-skill-local-typed-trace-shared-system-references-only"
        elif related:
            status = "blank-fixed-skill-local-typed-trace-related-records-no-mechanic-candidates"
        else:
            status = "blank-fixed-skill-local-typed-trace-no-related-records"
        status_counts[status] += 1
        trace = {
            "status": status,
            "seeds": seeds_by_weapon[index],
            "exact_related_records": related,
            "mechanic_reference_candidates": candidates,
            "shared_system_references": system_refs,
            "related_record_count": len(related),
            "mechanic_candidate_count": len(candidates),
            "shared_system_reference_count": len(system_refs),
            "trace_scope": "Typed exact first-hop identity matching with outbound references bounded to the matched aggregate list node; shared gun-system skills are retained separately.",
            "publication_status": "research-only-no-automatic-mechanic-promotion",
            "identity_policy": "Exact value plus compatible identity field/table; no global bare-number joins, sibling-node leakage, fuzzy matching, similar-ID substitution, or name matching.",
            "absence_policy": "No weapon-specific candidate found does not prove no special mechanic; it proves only that this bounded local typed trace found none.",
        }
        weapon.setdefault("effect_resolution", {})["fallback_reference_trace"] = trace
        report_rows.append({"blueprint_id": weapon.get("blueprint_id"), "item_id": weapon.get("item_id"), "name": weapon.get("name"), "category": weapon.get("category"), **trace})

    counts = payload.setdefault("record_counts", {})
    counts["blank_fixed_skill_reference_trace_statuses"] = dict(sorted(status_counts.items()))
    counts["blank_fixed_skill_weapons_traced"] = len(targets)
    counts["blank_fixed_skill_mechanic_candidates"] = sum(row["mechanic_candidate_count"] for row in report_rows)
    counts["blank_fixed_skill_shared_system_references"] = sum(row["shared_system_reference_count"] for row in report_rows)
    return {
        "schema": "dead-signal-blank-fixed-skill-reference-trace",
        "schema_version": 3,
        "record_counts": {
            "weapons": len(targets),
            "statuses": dict(sorted(status_counts.items())),
            "mechanic_candidates": counts["blank_fixed_skill_mechanic_candidates"],
            "shared_system_references": counts["blank_fixed_skill_shared_system_references"],
        },
        "policy": {
            "source_of_truth": "installed-game Miner snapshot",
            "fixed_skill_blank_behavior": "continue local typed exact-reference tracing instead of stopping",
            "first_hop_identity": "exact value must occur in a field/table compatible with the seed type",
            "aggregate_locality": "outbound references from aggregate list records are limited to the matched list element",
            "shared_gun_skills": "retained as system/progression evidence and excluded from weapon-specific mechanic candidate counts when used by multiple gun records",
            "promotion": "research evidence only until an exact mechanic consumer/reference chain is proven",
        },
        "weapons": report_rows,
    }


def install(module: Any) -> None:
    module.trace_blank_fixed_skill_references = lambda payload, base, current, equipment: _typed_trace(module, payload, base, current, equipment)
