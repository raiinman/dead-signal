"""Build a website-readiness ledger from authoritative installed-game weapon evidence.

External/community databases are never a source of values here. They may inspire
which player questions are useful to answer, but every resolved value/state in
this report comes from the current Dead Signal published game projection or from
exact installed-game corpus evidence emitted by the hardened corpus audit.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from dead_signal_weapon_corpus_audit import (
    _iter_records,
    _normalized_name,
    _read_json,
    _typed_identity_matches,
    _walk_leaves,
    _weapon_seeds,
)

SCHEMA_VERSION = 1
ActivityCallback = Callable[[str], None]
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_SUPPLEMENTAL_EVIDENCE = 80

# Question inventory only. No external values or claims are imported.
PAGE_QUESTIONS = (
    "identity", "name", "rarity", "weapon_class", "firing_mode", "gear_tier_progression",
    "damage", "projectiles", "fire_rate", "magazine", "range_score", "effective_range",
    "ammo_type", "reload_score", "reload_time", "mobility", "ads_time", "bullet_speed",
    "full_damage_range", "minimum_damage_range", "minimum_damage_percent", "crafting",
    "description", "special_skill", "cradle_compatibility", "image",
)

DEAD_SIGNAL_ENHANCEMENTS = (
    "blueprint_identity", "item_identity", "prototype_identity", "gun_identity",
    "tier_i_v_matrix", "blueprint_stars", "recipes_by_tier", "accuracy", "stability",
    "selectable_ammo", "acquisition", "attachment_compatibility", "calibration_compatibility",
    "variant_lineage", "evidence_provenance",
)

SUPPLEMENTAL_ALIASES = {
    "rarity": ("rarity", "rare", "quality", "quality_code"),
    "reload_score": ("reload_score", "reload_value", "reload_attr", "reload_rating"),
    "cradle_compatibility": ("cradle", "cradle_override", "cradle_weapon", "cradle_effect"),
}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def _has(value: Any) -> bool:
    return value not in (None, "", [], {})


def _first_tier(weapon: dict[str, Any]) -> dict[str, Any]:
    tiers = [row for row in (weapon.get("tiers") or []) if isinstance(row, dict)]
    return min(tiers, key=lambda row: int(row.get("tier") or 999), default={})


def _published_answers(weapon: dict[str, Any]) -> dict[str, dict[str, Any]]:
    ranged = weapon.get("ranged_stats") if isinstance(weapon.get("ranged_stats"), dict) else None
    melee = weapon.get("melee_stats") if isinstance(weapon.get("melee_stats"), dict) else None
    tiers = [row for row in (weapon.get("tiers") or []) if isinstance(row, dict)]
    first = _first_tier(weapon)
    star = weapon.get("blueprint_star_progression") if isinstance(weapon.get("blueprint_star_progression"), dict) else {}
    ammo = weapon.get("ammo_configuration") if isinstance(weapon.get("ammo_configuration"), dict) else {}
    resolution = weapon.get("effect_resolution") if isinstance(weapon.get("effect_resolution"), dict) else {}

    out: dict[str, dict[str, Any]] = {}

    def resolved(question: str, value: Any, source: str) -> None:
        if _has(value):
            out[question] = {"state": "resolved-installed-game", "value": value, "source": source}

    def na(question: str, reason: str) -> None:
        out[question] = {"state": "not-applicable", "reason": reason}

    resolved("identity", {"blueprint_id": weapon.get("blueprint_id"), "item_id": weapon.get("item_id"), "prototype_id": weapon.get("prototype_id")}, "published weapon identity projection")
    resolved("name", weapon.get("name"), "published installed-game identity/translation projection")
    resolved("weapon_class", weapon.get("category"), "published installed-game weapon category")
    resolved("gear_tier_progression", [row.get("tier") for row in tiers], "published tier projection")
    resolved("damage", first.get("damage"), "published Tier I weapon projection")
    resolved("crafting", [row.get("recipe") for row in tiers if row.get("recipe")], "published per-tier current recipe projection")
    resolved("description", weapon.get("short_description"), "published verified description projection")
    resolved("image", weapon.get("image_asset") or weapon.get("image_reference") or weapon.get("icon"), "published extracted asset projection")

    if _has(weapon.get("effect")):
        resolved("special_skill", weapon.get("effect"), "published fixed-skill evidence projection")
    elif resolution:
        out["special_skill"] = {
            "state": "resolved-evidence-state" if resolution.get("status") else "unresolved",
            "value": resolution.get("status"),
            "fixed_skill_code": resolution.get("fixed_skill_code"),
            "source": resolution.get("source_table"),
        }

    if ranged is not None:
        mapping = {
            "fire_rate": ("rpm", "published ranged_stats.rpm"),
            "magazine": ("magazine", "published ranged_stats.magazine"),
            "range_score": ("range_meters", "published ranged_stats.range_meters"),
            "reload_time": ("reload_seconds", "published ranged_stats.reload_seconds"),
            "mobility": ("mobility", "published ranged_stats.mobility"),
            "full_damage_range": ("full_damage_distance", "published ranged_stats.full_damage_distance"),
            "minimum_damage_range": ("minimum_damage_distance", "published ranged_stats.minimum_damage_distance"),
            "minimum_damage_percent": ("minimum_damage_multiplier", "published ranged_stats.minimum_damage_multiplier"),
            "ammo_type": ("ammo_item_id", "published ranged_stats.ammo_item_id"),
            "projectiles": ("projectile_count", "published exact bullet-pattern projection"),
        }
        for question, (field, source) in mapping.items():
            resolved(question, ranged.get(field), source)
        resolved("effective_range", ranged.get("full_damage_distance"), "published exact full-damage-distance projection")
    else:
        for question in (
            "firing_mode", "fire_rate", "magazine", "ammo_type", "reload_score", "reload_time",
            "ads_time", "bullet_speed", "full_damage_range", "minimum_damage_range",
            "minimum_damage_percent", "projectiles",
        ):
            na(question, "firearm-only question")
        if melee:
            resolved("effective_range", melee.get("range") or melee.get("attack_range"), "published melee range projection")

    resolved("blueprint_identity", weapon.get("blueprint_id"), "published exact blueprint identity")
    resolved("item_identity", weapon.get("item_id"), "published exact item identity")
    resolved("prototype_identity", weapon.get("prototype_id"), "published exact prototype identity")
    resolved("gun_identity", sorted({row.get("gun_no") for row in tiers if _has(row.get("gun_no"))}), "published exact tier gun identity")
    resolved("tier_i_v_matrix", [{"tier": row.get("tier"), "item_id": row.get("item_id"), "gun_no": row.get("gun_no"), "damage": row.get("damage")} for row in tiers], "published exact tier matrix")
    resolved("blueprint_stars", star.get("stars"), "published gun_blueprint_attr_data progression")
    resolved("recipes_by_tier", [{"tier": row.get("tier"), "recipe": row.get("recipe")} for row in tiers if row.get("recipe")], "published current recipe layer")
    if ranged is not None:
        resolved("accuracy", ranged.get("accuracy"), "published ranged_stats.accuracy")
        resolved("stability", ranged.get("stability"), "published ranged_stats.stability")
    resolved("selectable_ammo", ammo.get("selectable_ammo_item_ids"), "published exact gun accessory/ammo relationship")
    resolved("acquisition", weapon.get("acquisition_hint") or weapon.get("item_gain_path"), "published acquisition evidence projection")
    if ammo:
        out["attachment_compatibility"] = {"state": "resolved-partial", "value": {"accessory_slot": ammo.get("accessory_slot"), "default_accessory_code": ammo.get("default_accessory_code")}, "source": ammo.get("source")}
    out["evidence_provenance"] = {"state": "resolved-installed-game", "value": True, "source": "Dead Signal exact installed-game evidence graph/projections"}
    return out


def _candidate_by_group(corpus_weapon: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in corpus_weapon.get("exact_corpus_evidence") or []:
        for field in record.get("fields") or []:
            group = str(field.get("group") or "")
            if group:
                groups[group].append({
                    "table": record.get("table"), "record_id": record.get("record_id"),
                    "matched_identity_values": record.get("matched_identity_values"),
                    "field": field.get("field"), "json_pointer": field.get("json_pointer"), "value": field.get("value"),
                })
    return groups


def _supplemental_scan(base: Path, current: Path, weapons: list[dict[str, Any]], *, activity: ActivityCallback) -> list[dict[str, list[dict[str, Any]]]]:
    seed_rows = [{"seeds": _weapon_seeds(weapon)} for weapon in weapons]
    results: list[dict[str, list[dict[str, Any]]]] = [defaultdict(list) for _ in weapons]
    for layer, root in (("base", base), ("current", current)):
        paths = list(root.rglob("*.json"))
        activity(f"Weapon Site Readiness: supplemental field scan across {len(paths)} {layer} JSON tables")
        for file_index, path in enumerate(paths, start=1):
            if file_index == 1 or file_index % 2000 == 0:
                activity(f"Weapon Site Readiness supplemental {layer}: {file_index}/{len(paths)}")
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
                payload = _read_json(path, None)
            except OSError:
                continue
            if payload is None:
                continue
            relative = path.relative_to(root).as_posix()
            for record_id, record in _iter_records(payload):
                leaves = list(_walk_leaves(record))
                present = []
                for pointer, field, value in leaves:
                    normalized = _normalized_name(field)
                    for group, aliases in SUPPLEMENTAL_ALIASES.items():
                        if any(_normalized_name(alias) in normalized for alias in aliases):
                            present.append((group, pointer, field, value))
                if not present:
                    continue
                for index, row in enumerate(seed_rows):
                    if sum(len(values) for values in results[index].values()) >= MAX_SUPPLEMENTAL_EVIDENCE:
                        continue
                    matched = _typed_identity_matches(record_id, leaves, row["seeds"])
                    if not matched:
                        continue
                    for group, pointer, field, value in present:
                        results[index][group].append({
                            "layer": layer, "table": relative, "record_id": record_id,
                            "matched_identity_values": sorted(matched), "field": field,
                            "json_pointer": pointer, "value": value,
                        })
    return results


def run_weapon_site_readiness(
    base: Path,
    current: Path,
    weapons_path: Path,
    reports_dir: Path,
    corpus_audit: dict[str, Any],
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    payload = _read_json(weapons_path, {}) or {}
    weapons = [row for row in (payload.get("weapons") or []) if isinstance(row, dict)]
    corpus_rows = {str(row.get("blueprint_id")): row for row in (corpus_audit.get("weapons") or []) if isinstance(row, dict)}
    supplemental = _supplemental_scan(base, current, weapons, activity=activity)

    rows = []
    launch_queue = []
    page_state_counts: Counter[str] = Counter()
    enhancement_state_counts: Counter[str] = Counter()

    audit_group_map = {
        "rarity": None,
        "firing_mode": "firing_mode",
        "reload_score": None,
        "ads_time": "ads_time",
        "bullet_speed": "bullet_speed",
        "cradle_compatibility": None,
        "calibration_compatibility": "calibration_compatibility",
        "attachment_compatibility": "attachment_compatibility",
        "variant_lineage": None,
    }

    for index, weapon in enumerate(weapons):
        answers = _published_answers(weapon)
        corpus_weapon = corpus_rows.get(str(weapon.get("blueprint_id")), {})
        corpus_groups = _candidate_by_group(corpus_weapon)

        for question, group in audit_group_map.items():
            if question in answers and answers[question].get("state", "").startswith("resolved"):
                continue
            candidates = []
            if group:
                candidates.extend(corpus_groups.get(group) or [])
            candidates.extend((supplemental[index].get(question) or []))
            if candidates:
                answers[question] = {
                    "state": "exact-game-record-located-needs-semantic-proof",
                    "candidate_count": len(candidates),
                    "evidence": candidates[:30],
                }

        page_questions = {}
        resolved_page = applicable_page = 0
        for question in PAGE_QUESTIONS:
            answer = answers.get(question, {"state": "unresolved"})
            state = answer.get("state", "unresolved")
            page_questions[question] = answer
            page_state_counts[state] += 1
            if state == "not-applicable":
                continue
            applicable_page += 1
            if state in ("resolved-installed-game", "resolved-evidence-state", "resolved-partial"):
                resolved_page += 1
            else:
                priority = 100 if question in ("rarity", "firing_mode", "ads_time", "bullet_speed", "reload_score") else 90
                if state == "exact-game-record-located-needs-semantic-proof":
                    priority += 5
                launch_queue.append({
                    "priority": priority, "blueprint_id": weapon.get("blueprint_id"),
                    "name": weapon.get("name"), "question": question, "state": state,
                    "candidate_count": int(answer.get("candidate_count") or 0),
                })

        enhancements = {}
        resolved_enh = 0
        for question in DEAD_SIGNAL_ENHANCEMENTS:
            answer = answers.get(question, {"state": "unresolved"})
            enhancements[question] = answer
            state = answer.get("state", "unresolved")
            enhancement_state_counts[state] += 1
            if state in ("resolved-installed-game", "resolved-evidence-state", "resolved-partial"):
                resolved_enh += 1

        rows.append({
            "blueprint_id": weapon.get("blueprint_id"), "name": weapon.get("name"), "category": weapon.get("category"),
            "reference_question_coverage": {
                "resolved": resolved_page, "applicable": applicable_page,
                "percent": round((resolved_page / applicable_page * 100.0), 2) if applicable_page else 100.0,
            },
            "dead_signal_enhancement_coverage": {
                "resolved": resolved_enh, "total": len(DEAD_SIGNAL_ENHANCEMENTS),
                "percent": round(resolved_enh / len(DEAD_SIGNAL_ENHANCEMENTS) * 100.0, 2),
            },
            "questions": page_questions,
            "enhancements": enhancements,
        })

    launch_queue.sort(key=lambda row: (-row["priority"], -row["candidate_count"], str(row["name"]), row["question"]))
    total_applicable = sum(row["reference_question_coverage"]["applicable"] for row in rows)
    total_resolved = sum(row["reference_question_coverage"]["resolved"] for row in rows)
    enhancement_total = len(rows) * len(DEAD_SIGNAL_ENHANCEMENTS)
    enhancement_resolved = sum(row["dead_signal_enhancement_coverage"]["resolved"] for row in rows)

    report = {
        "schema": "dead-signal-weapon-site-readiness",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Authoritative installed-game Weapons website readiness",
        "authority_policy": {
            "source_of_truth": "installed Once Human game corpus mined by Dead Signal",
            "external_sites": "question-set/reference only; no external numeric or semantic values are imported",
            "candidate_rule": "An exact game record can become a research lead, but semantic publication still requires the correct typed owner/consumer interpretation.",
        },
        "record_counts": {
            "weapons": len(rows), "reference_questions": len(PAGE_QUESTIONS),
            "dead_signal_enhancements": len(DEAD_SIGNAL_ENHANCEMENTS), "launch_queue": len(launch_queue),
        },
        "scoreboard": {
            "reference_question_set": {
                "resolved": total_resolved, "applicable": total_applicable,
                "percent": round((total_resolved / total_applicable * 100.0), 2) if total_applicable else 100.0,
                "state_counts": dict(page_state_counts),
            },
            "dead_signal_enhancements": {
                "resolved": enhancement_resolved, "total": enhancement_total,
                "percent": round((enhancement_resolved / enhancement_total * 100.0), 2) if enhancement_total else 100.0,
                "state_counts": dict(enhancement_state_counts),
            },
        },
        "question_inventory": list(PAGE_QUESTIONS),
        "enhancement_inventory": list(DEAD_SIGNAL_ENHANCEMENTS),
        "launch_blocker_queue": launch_queue,
        "weapons": rows,
    }
    destination = reports_dir / "weapon-site-readiness.json"
    _write_json(destination, report)
    activity(f"Weapon Site Readiness complete: {len(rows)} weapons; {len(launch_queue)} unresolved/candidate launch questions")
    return report
