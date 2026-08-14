"""Typed first-hop identity matching for blank fixed-skill weapon traces.

Exact scalar equality alone is insufficient for small numeric identities such as
prototype_id=204 because unrelated records may contain the same number. This
module keeps the exact-value policy but requires the field/table semantics to
match the seed type before a record can enter the weapon trace.
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


def _typed_first_pass(module: Any, base: Path, current: Path, seed_owners: dict[str, list[tuple[int, str]]]):
    found: dict[str, list[dict[str, Any]]] = defaultdict(list)
    wanted = set(seed_owners)
    for layer, root, path in module._relevant_tables(base, current):
        relative = path.relative_to(root).as_posix()
        for record_id, record in module._rows(path).items():
            matches: dict[str, list[dict[str, str]]] = defaultdict(list)
            record_key = module._scalar(record_id)
            if record_key in wanted:
                for _, kind in seed_owners[record_key]:
                    if _record_id_matches_kind(relative, kind):
                        matches[record_key].append({"field": "record_id", "json_pointer": "/data", "seed_kind": kind})
            for pointer, field, raw in module._walk(record):
                value = module._scalar(raw)
                if value not in wanted:
                    continue
                for _, kind in seed_owners[value]:
                    if _field_matches_kind(field, kind):
                        matches[value].append({"field": field, "json_pointer": pointer, "seed_kind": kind})
            if not matches:
                continue
            references = module._record_reference_values(record)
            for value, vias in matches.items():
                found[value].append({
                    "source": layer,
                    "table": relative,
                    "record_id": str(record_id),
                    "matched_via": vias,
                    "outbound_references": references,
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
    related_by_weapon: dict[int, list[dict[str, Any]]] = defaultdict(list)
    candidates_by_weapon: dict[int, dict[tuple[str, str, str, str], dict[str, Any]]] = defaultdict(dict)

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
                        "matched_via": [{k: v for k, v in via.items() if k != "seed_kind"} for via in vias],
                    })
                for reference in occurrence.get("outbound_references") or []:
                    if not reference.get("mechanic_like"):
                        continue
                    candidate_value = str(reference.get("value") or "")
                    if not candidate_value or candidate_value in seed_owners:
                        continue
                    key = (occurrence["table"], occurrence["record_id"], str(reference.get("field") or ""), candidate_value)
                    if len(candidates_by_weapon[weapon_index]) < module.MAX_MECHANIC_CANDIDATES_PER_WEAPON:
                        candidates_by_weapon[weapon_index][key] = {
                            "source": occurrence["source"],
                            "table": occurrence["table"],
                            "record_id": occurrence["record_id"],
                            "field": reference.get("field"),
                            "json_pointer": reference.get("json_pointer"),
                            "value": candidate_value,
                        }

    candidate_values = {candidate["value"] for candidates in candidates_by_weapon.values() for candidate in candidates.values()}
    second_pass = module._scan_for_exact_values(base, current, candidate_values, capture_record_references=False)

    status_counts: dict[str, int] = defaultdict(int)
    report_rows = []
    for index, weapon in enumerate(targets):
        candidates = list(candidates_by_weapon[index].values())
        for candidate in candidates:
            candidate["exact_target_occurrences"] = [
                {"source": row["source"], "table": row["table"], "record_id": row["record_id"], "matched_via": row["matched_via"]}
                for row in second_pass.get(candidate["value"], [])[:module.MAX_TARGET_OCCURRENCES_PER_CANDIDATE]
            ]
            candidate["exact_target_record_found"] = any(
                any(via.get("field") == "record_id" for via in row.get("matched_via") or [])
                for row in second_pass.get(candidate["value"], [])
            )
        related = related_by_weapon[index]
        if candidates:
            status = "blank-fixed-skill-typed-exact-trace-found-mechanic-candidates"
        elif related:
            status = "blank-fixed-skill-typed-exact-trace-related-records-no-mechanic-candidates"
        else:
            status = "blank-fixed-skill-typed-exact-trace-no-related-records"
        status_counts[status] += 1
        trace = {
            "status": status,
            "seeds": seeds_by_weapon[index],
            "exact_related_records": related,
            "mechanic_reference_candidates": candidates,
            "related_record_count": len(related),
            "mechanic_candidate_count": len(candidates),
            "trace_scope": "Typed exact identity matching on the first hop, then one exact target lookup for explicit mechanic references.",
            "publication_status": "research-only-no-automatic-mechanic-promotion",
            "identity_policy": "Exact value plus compatible identity field/table; no global bare-number joins, fuzzy matching, similar-ID substitution, or name matching.",
            "absence_policy": "No candidate found does not prove no special mechanic; it proves only that this bounded typed exact trace found none.",
        }
        weapon.setdefault("effect_resolution", {})["fallback_reference_trace"] = trace
        report_rows.append({"blueprint_id": weapon.get("blueprint_id"), "item_id": weapon.get("item_id"), "name": weapon.get("name"), "category": weapon.get("category"), **trace})

    counts = payload.setdefault("record_counts", {})
    counts["blank_fixed_skill_reference_trace_statuses"] = dict(sorted(status_counts.items()))
    counts["blank_fixed_skill_weapons_traced"] = len(targets)
    counts["blank_fixed_skill_mechanic_candidates"] = sum(row["mechanic_candidate_count"] for row in report_rows)
    return {
        "schema": "dead-signal-blank-fixed-skill-reference-trace",
        "schema_version": 2,
        "record_counts": {"weapons": len(targets), "statuses": dict(sorted(status_counts.items())), "mechanic_candidates": counts["blank_fixed_skill_mechanic_candidates"]},
        "policy": {
            "source_of_truth": "installed-game Miner snapshot",
            "fixed_skill_blank_behavior": "continue typed exact-reference tracing instead of stopping",
            "first_hop_identity": "exact value must occur in a field/table compatible with the seed type",
            "promotion": "research evidence only until an exact mechanic consumer/reference chain is proven",
        },
        "weapons": report_rows,
    }


def install(module: Any) -> None:
    module.trace_blank_fixed_skill_references = lambda payload, base, current, equipment: _typed_trace(module, payload, base, current, equipment)
