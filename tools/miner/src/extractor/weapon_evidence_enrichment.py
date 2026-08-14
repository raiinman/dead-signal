"""Add fail-closed Weapon effect, description, and fallback-reference diagnostics.

This module never invents mechanics and never executes game bytecode. The normal
fixed-skill path remains authoritative when present. When fixed_skill_code is
blank, the enrichment no longer stops there: it performs a bounded exact-value
trace from the weapon's mined identities across relevant extracted tables, then
resolves any mechanic-bearing references found on those exact matching records.

Short-description text remains withheld until item-handle identity is proven.
The fallback trace is research evidence only; it cannot promote a mechanic by
similarity, naming, fuzzy matching, or family resemblance.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable

from normalize_armor import MARKER, Translator, table, translation_entries


PASSIVE_TABLE = "game_common/data/passive_skill_data.json"
ITEM_TABLE = "game_common/data/item_data.json"
EQUIP_TABLE = "game_common/data/equip_data.json"

REFERENCE_FIELD = re.compile(
    r"(?:^|_)(?:id|ids|no|code|ref|buff|skill|status|keyword|logic|behavior|"
    r"ability|effect|trigger|passive|gun|weapon|item|blueprint|prototype|affix)(?:$|_)",
    re.IGNORECASE,
)
MECHANIC_FIELD = re.compile(
    r"(?:buff|skill|status|keyword|logic|behavior|ability|effect|trigger|passive)",
    re.IGNORECASE,
)
RELEVANT_TABLE = re.compile(
    r"(?:buff|skill|status|keyword|logic|behavior|ability|effect|trigger|passive|"
    r"gun_|weapon|equip|item_data|blueprint|prototype|affix)",
    re.IGNORECASE,
)
MAX_RELATED_RECORDS_PER_WEAPON = 120
MAX_MECHANIC_CANDIDATES_PER_WEAPON = 80
MAX_TARGET_OCCURRENCES_PER_CANDIDATE = 40


def _translation_sources(base: Path, current: Path) -> list[tuple[str, dict[str, Any]]]:
    sources: list[tuple[str, dict[str, Any]]] = []
    base_file = base / "translate" / "translate_data_en.json"
    if base_file.is_file():
        sources.append(("base/translate/translate_data_en.json", translation_entries(base_file)))
    for path in sorted((current / "translate").glob("translate_data_en*.json")):
        sources.append((f"current/translate/{path.name}", translation_entries(path)))
    return sources


def _description_evidence(raw_value: Any, sources: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    raw = Translator.raw(raw_value)
    stripped = MARKER.sub("", raw)
    matches = []
    for source_name, translations in sources:
        for candidate_kind, candidate in (("raw", raw), ("marker-stripped", stripped)):
            if not candidate:
                continue
            translated = translations.get(candidate)
            if isinstance(translated, str) and translated:
                matches.append(
                    {
                        "source": source_name,
                        "key_kind": candidate_kind,
                        "key": candidate,
                        "text": translated,
                    }
                )
    unique_texts = sorted({row["text"] for row in matches})
    if not raw or raw == "0":
        status = "no-short-description-handle"
    elif not matches:
        status = "translation-handle-unresolved"
    elif len(unique_texts) == 1:
        status = "translation-handle-resolves-consistently"
    else:
        status = "translation-source-conflict"
    return {
        "status": status,
        "source_table": ITEM_TABLE,
        "source_field": "short_desc",
        "raw_handle": raw,
        "marker_stripped_handle": stripped,
        "translation_matches": matches,
        "unique_translation_text_count": len(unique_texts),
        "publication_status": "withheld-until-item-handle-identity-is-verified",
    }


def _fixed_skill_code(weapon: dict[str, Any]) -> str:
    levels = ((weapon.get("blueprint_attribute_progression") or {}).get("levels") or [])
    level_one = next(
        (row for row in levels if isinstance(row, dict) and int(row.get("level") or 0) == 1),
        None,
    )
    source = level_one or (levels[0] if levels and isinstance(levels[0], dict) else {})
    return str(source.get("fixed_skill_code") or "").strip()


def _effect_evidence(weapon: dict[str, Any], passive_skills: dict[str, Any]) -> dict[str, Any]:
    skill_code = _fixed_skill_code(weapon)
    exact_skill = passive_skills.get(skill_code) if skill_code else None
    effect = weapon.get("effect")
    if not skill_code:
        status = "no-fixed-skill-reference"
    elif not isinstance(exact_skill, dict):
        status = "exact-fixed-skill-record-missing"
    elif effect:
        status = "resolved-player-facing-effect"
    else:
        status = "exact-fixed-skill-record-present-effect-text-unresolved"
    return {
        "status": status,
        "fixed_skill_code": skill_code,
        "exact_passive_skill_record_present": isinstance(exact_skill, dict),
        "effect_present": bool(effect),
        "source_table": PASSIVE_TABLE,
        "identity_policy": "exact record ID only; similarity aliases are forbidden",
    }


def _walk(value: Any, pointer: str = "") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            child_pointer = f"{pointer}/{escaped}"
            if isinstance(child, (dict, list)):
                yield from _walk(child, child_pointer)
            else:
                yield child_pointer, str(key), child
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_pointer = f"{pointer}/{index}"
            if isinstance(child, (dict, list)):
                yield from _walk(child, child_pointer)
            else:
                yield child_pointer, str(index), child


def _scalar(value: Any) -> str:
    if value is None or isinstance(value, bool) or isinstance(value, (dict, list)):
        return ""
    text = str(value).strip()
    if not text or text in {"0", "0.0"} or len(text) > 160:
        return ""
    if text.lstrip("-").isdigit() and len(text.lstrip("-")) < 3:
        return ""
    return text


def _rows(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data", payload)
    return data if isinstance(data, dict) else {}


def _relevant_tables(base: Path, current: Path) -> Iterable[tuple[str, Path, Path]]:
    for layer, root in (("base", base), ("current", current)):
        for path in sorted(root.rglob("*.json")):
            if path.name == "snapshot.json":
                continue
            relative = path.relative_to(root)
            if RELEVANT_TABLE.search(relative.as_posix()):
                yield layer, root, path


def _record_reference_values(record: Any) -> list[dict[str, str]]:
    values = []
    for pointer, field, value in _walk(record):
        text = _scalar(value)
        if text and (REFERENCE_FIELD.search(field) or field == "short_desc"):
            values.append(
                {
                    "field": field,
                    "json_pointer": pointer,
                    "value": text,
                    "mechanic_like": bool(MECHANIC_FIELD.search(field)),
                }
            )
    return values


def _weapon_seeds(weapon: dict[str, Any], equipment: dict[str, Any]) -> list[dict[str, str]]:
    seeds: list[dict[str, str]] = []

    def add(kind: str, value: Any) -> None:
        text = _scalar(value)
        if text and not any(row["kind"] == kind and row["value"] == text for row in seeds):
            seeds.append({"kind": kind, "value": text})

    add("blueprint_id", weapon.get("blueprint_id"))
    add("item_id", weapon.get("item_id"))
    add("prototype_id", weapon.get("prototype_id"))
    equip = equipment.get(str(weapon.get("item_id")), {})
    if isinstance(equip, dict):
        add("gun_no", equip.get("gun_no"))
    for tier in weapon.get("tiers") or []:
        if isinstance(tier, dict):
            add("tier_gun_no", tier.get("gun_no"))
            add("tier_item_id", tier.get("item_id"))
    description = weapon.get("short_description_evidence") or {}
    add("short_description_handle", description.get("raw_handle"))
    return seeds


def _scan_for_exact_values(
    base: Path,
    current: Path,
    wanted: set[str],
    *,
    capture_record_references: bool,
) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not wanted:
        return found
    for layer, root, path in _relevant_tables(base, current):
        relative = path.relative_to(root).as_posix()
        for record_id, record in _rows(path).items():
            matches: dict[str, list[dict[str, str]]] = defaultdict(list)
            record_key = _scalar(record_id)
            if record_key in wanted:
                matches[record_key].append({"field": "record_id", "json_pointer": "/data"})
            for pointer, field, raw in _walk(record):
                if not (REFERENCE_FIELD.search(field) or field == "short_desc"):
                    continue
                value = _scalar(raw)
                if value in wanted:
                    matches[value].append({"field": field, "json_pointer": pointer})
            if not matches:
                continue
            references = _record_reference_values(record) if capture_record_references else []
            for value, vias in matches.items():
                found[value].append(
                    {
                        "source": layer,
                        "table": relative,
                        "record_id": str(record_id),
                        "matched_via": vias,
                        "outbound_references": references,
                    }
                )
    return found


def trace_blank_fixed_skill_references(
    payload: dict[str, Any],
    base: Path,
    current: Path,
    equipment: dict[str, Any],
) -> dict[str, Any]:
    weapons = [row for row in payload.get("weapons", []) if isinstance(row, dict)]
    targets = [row for row in weapons if not _fixed_skill_code(row)]
    seed_owners: dict[str, list[tuple[int, str]]] = defaultdict(list)
    seeds_by_weapon: dict[int, list[dict[str, str]]] = {}
    for index, weapon in enumerate(targets):
        seeds = _weapon_seeds(weapon, equipment)
        seeds_by_weapon[index] = seeds
        for seed in seeds:
            seed_owners[seed["value"]].append((index, seed["kind"]))

    first_pass = _scan_for_exact_values(
        base, current, set(seed_owners), capture_record_references=True
    )
    related_by_weapon: dict[int, list[dict[str, Any]]] = defaultdict(list)
    candidates_by_weapon: dict[int, dict[tuple[str, str, str, str], dict[str, Any]]] = defaultdict(dict)

    for seed_value, occurrences in first_pass.items():
        for weapon_index, seed_kind in seed_owners.get(seed_value, []):
            for occurrence in occurrences:
                if len(related_by_weapon[weapon_index]) < MAX_RELATED_RECORDS_PER_WEAPON:
                    related_by_weapon[weapon_index].append(
                        {
                            "seed_kind": seed_kind,
                            "seed_value": seed_value,
                            "source": occurrence["source"],
                            "table": occurrence["table"],
                            "record_id": occurrence["record_id"],
                            "matched_via": occurrence["matched_via"],
                        }
                    )
                for reference in occurrence.get("outbound_references") or []:
                    if not reference.get("mechanic_like"):
                        continue
                    candidate_value = str(reference.get("value") or "")
                    if not candidate_value or candidate_value in seed_owners:
                        continue
                    key = (
                        occurrence["table"],
                        occurrence["record_id"],
                        str(reference.get("field") or ""),
                        candidate_value,
                    )
                    if len(candidates_by_weapon[weapon_index]) < MAX_MECHANIC_CANDIDATES_PER_WEAPON:
                        candidates_by_weapon[weapon_index][key] = {
                            "source": occurrence["source"],
                            "table": occurrence["table"],
                            "record_id": occurrence["record_id"],
                            "field": reference.get("field"),
                            "json_pointer": reference.get("json_pointer"),
                            "value": candidate_value,
                        }

    candidate_values = {
        candidate["value"]
        for candidates in candidates_by_weapon.values()
        for candidate in candidates.values()
    }
    second_pass = _scan_for_exact_values(
        base, current, candidate_values, capture_record_references=False
    )

    status_counts: dict[str, int] = defaultdict(int)
    report_rows = []
    for index, weapon in enumerate(targets):
        candidates = list(candidates_by_weapon[index].values())
        for candidate in candidates:
            candidate["exact_target_occurrences"] = [
                {
                    "source": row["source"],
                    "table": row["table"],
                    "record_id": row["record_id"],
                    "matched_via": row["matched_via"],
                }
                for row in second_pass.get(candidate["value"], [])[:MAX_TARGET_OCCURRENCES_PER_CANDIDATE]
            ]
            candidate["exact_target_record_found"] = any(
                any(via.get("field") == "record_id" for via in row.get("matched_via") or [])
                for row in second_pass.get(candidate["value"], [])
            )

        related = related_by_weapon[index]
        if candidates:
            status = "blank-fixed-skill-exact-trace-found-mechanic-candidates"
        elif related:
            status = "blank-fixed-skill-exact-trace-related-records-no-mechanic-candidates"
        else:
            status = "blank-fixed-skill-exact-trace-no-related-records"
        status_counts[status] += 1
        trace = {
            "status": status,
            "seeds": seeds_by_weapon[index],
            "exact_related_records": related,
            "mechanic_reference_candidates": candidates,
            "related_record_count": len(related),
            "mechanic_candidate_count": len(candidates),
            "trace_scope": "Exact scalar equality across relevant extracted tables, then one exact target lookup for mechanic-bearing outbound references.",
            "publication_status": "research-only-no-automatic-mechanic-promotion",
            "identity_policy": "No fuzzy matching, similar-ID substitution, name matching, or inferred family joins.",
            "absence_policy": "No candidate found does not prove no special mechanic; it proves only that this bounded exact trace found none.",
        }
        effect = weapon.setdefault("effect_resolution", {})
        effect["fallback_reference_trace"] = trace
        report_rows.append(
            {
                "blueprint_id": weapon.get("blueprint_id"),
                "item_id": weapon.get("item_id"),
                "name": weapon.get("name"),
                "category": weapon.get("category"),
                **trace,
            }
        )

    counts = payload.setdefault("record_counts", {})
    counts["blank_fixed_skill_reference_trace_statuses"] = dict(sorted(status_counts.items()))
    counts["blank_fixed_skill_weapons_traced"] = len(targets)
    counts["blank_fixed_skill_mechanic_candidates"] = sum(
        row["mechanic_candidate_count"] for row in report_rows
    )
    return {
        "schema": "dead-signal-blank-fixed-skill-reference-trace",
        "schema_version": 1,
        "record_counts": {
            "weapons": len(targets),
            "statuses": dict(sorted(status_counts.items())),
            "mechanic_candidates": counts["blank_fixed_skill_mechanic_candidates"],
        },
        "policy": {
            "source_of_truth": "installed-game Miner snapshot",
            "fixed_skill_blank_behavior": "continue exact-reference tracing instead of stopping",
            "promotion": "research evidence only until an exact mechanic consumer/reference chain is proven",
        },
        "weapons": report_rows,
    }


def enrich(payload: dict[str, Any], items: dict[str, Any], passive_skills: dict[str, Any], translation_sources: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    weapons = payload.get("weapons")
    if not isinstance(weapons, list):
        raise ValueError("Expected normalized weapons payload with a weapons array")

    handle_to_weapons: dict[str, list[dict[str, Any]]] = defaultdict(list)
    status_counts: dict[str, int] = defaultdict(int)
    description_status_counts: dict[str, int] = defaultdict(int)

    for weapon in weapons:
        if not isinstance(weapon, dict):
            continue
        item_id = weapon.get("item_id")
        item = items.get(str(item_id), {}) if item_id not in (None, "") else {}
        description = _description_evidence(item.get("short_desc") if isinstance(item, dict) else None, translation_sources)
        effect = _effect_evidence(weapon, passive_skills)
        weapon["short_description_evidence"] = description
        weapon["effect_resolution"] = effect
        status_counts[effect["status"]] += 1
        description_status_counts[description["status"]] += 1
        handle = str(description.get("raw_handle") or "")
        if handle:
            handle_to_weapons[handle].append(weapon)

    shared_handles = 0
    for handle, rows in handle_to_weapons.items():
        shared = len(rows)
        if shared > 1:
            shared_handles += 1
        identities = [
            {
                "blueprint_id": row.get("blueprint_id"),
                "item_id": row.get("item_id"),
                "name": row.get("name"),
                "category": row.get("category"),
            }
            for row in rows
        ]
        for row in rows:
            evidence = row["short_description_evidence"]
            evidence["shared_weapon_handle_count"] = shared
            evidence["shared_weapon_identities"] = identities if shared > 1 else []
            if shared > 1 and evidence["status"] == "translation-handle-resolves-consistently":
                evidence["status"] = "translation-handle-shared-across-weapons"
                description_status_counts["translation-handle-resolves-consistently"] -= 1
                description_status_counts["translation-handle-shared-across-weapons"] += 1

    counts = payload.setdefault("record_counts", {})
    counts["effect_resolution_statuses"] = dict(sorted(status_counts.items()))
    counts["short_description_evidence_statuses"] = {
        key: value for key, value in sorted(description_status_counts.items()) if value
    }
    counts["shared_short_description_handles"] = shared_handles
    payload["weapon_evidence_policy"] = {
        "effect_identity": "Exact passive_skill_data record identity only; similar IDs are never substituted.",
        "blank_fixed_skill": "A blank fixed_skill_code is a branch condition, not a terminal conclusion; the Miner continues with a bounded exact-reference trace.",
        "short_description": "Raw item_data.short_desc and translation-source matches are diagnostic only; player-facing description remains withheld until item-handle identity is independently verified.",
    }
    return payload


def enrich_file(base: Path | str, current: Path | str, weapons_path: Path | str, log: Callable[[str], None] | None = None) -> dict[str, Any]:
    base = Path(base)
    current = Path(current)
    weapons_path = Path(weapons_path)
    payload = json.loads(weapons_path.read_text(encoding="utf-8"))
    items = table(current / ITEM_TABLE)
    equipment = table(current / EQUIP_TABLE)
    passive_skills = table(base / PASSIVE_TABLE)
    sources = _translation_sources(base, current)
    enriched = enrich(payload, items, passive_skills, sources)
    trace_report = trace_blank_fixed_skill_references(enriched, base, current, equipment)
    reports_dir = weapons_path.parent.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "weapon-blank-fixed-skill-reference-trace.json"
    report_path.write_text(json.dumps(trace_report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary = weapons_path.with_suffix(weapons_path.suffix + ".tmp")
    temporary.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(weapons_path)
    if log:
        counts = enriched.get("record_counts", {})
        log(
            "Classified Weapon evidence: "
            f"effects={counts.get('effect_resolution_statuses', {})}; "
            f"short descriptions={counts.get('short_description_evidence_statuses', {})}; "
            f"blank fixed-skill traces={counts.get('blank_fixed_skill_reference_trace_statuses', {})}."
        )
        log(f"Blank fixed-skill exact-reference report: {report_path}")
    return enriched


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich normalized Weapons with exact effect, description, and fallback-reference provenance")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--weapons", type=Path, required=True)
    args = parser.parse_args()
    enriched = enrich_file(args.base, args.current, args.weapons)
    print(json.dumps({"record_counts": enriched.get("record_counts", {})}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
