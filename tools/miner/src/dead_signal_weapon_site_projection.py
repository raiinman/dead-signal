"""Build the authoritative Dead Signal website Weapons projections.

The forensic v2 projection preserves research state and provenance. A second
publisher derives a lean browser payload plus an evidence sidecar from that
projection. Only installed-game evidence is authoritative.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from dead_signal_weapon_launch_gap_trace import run_weapon_launch_gap_trace
from dead_signal_weapon_site_publish import publish_weapon_site_payloads

SCHEMA_VERSION = 3
ActivityCallback = Callable[[str], None]

GUN_BASE_SEMANTIC_FIELDS = {
    "ads_time": "ads_time",
    "bullet_speed": "bullet_speed",
    "reload_score": "reload_loop_affix_value",
    "reload_time_seconds": "reload_loop_time",
    "magazine": "weapon_magazine_size_affix_value",
    "mobility": "weapon_mobility",
    "effective_range": "weapon_range_affix_value",
    "range_score": "weapon_range_value",
    "fire_rate_display_rpm": "weapon_rpm_affix_value",
}
GUN_BASE_RAW_FIELDS = {
    "firing_mode_code": "default_shoot_mode",
    "burst_bullet_num": "burst_bullet_num",
    "fire_rate_internal": "weapon_rpm",
}


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, UnicodeError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def _has(value: Any) -> bool:
    return value not in (None, "", [], {})


def _first_tier(weapon: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in (weapon.get("tiers") or []) if isinstance(row, dict)]
    return min(rows, key=lambda row: int(row.get("tier") or 999), default={})


def _field_map(record: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for field in record.get("fields") or []:
        if isinstance(field, dict) and field.get("field"):
            result[str(field["field"])].append(field)
    return result


def _gun_base_record(corpus_weapon: dict[str, Any], tier_one_gun: Any) -> dict[str, Any] | None:
    if tier_one_gun in (None, "", 0):
        return None
    target = str(tier_one_gun)
    candidates = []
    for record in corpus_weapon.get("exact_corpus_evidence") or []:
        if not isinstance(record, dict) or record.get("evidence_scope") != "variant-local":
            continue
        table = str(record.get("table") or "").replace("\\", "/").casefold()
        if not table.endswith("gun_base_params_data.json"):
            continue
        matched = {str(value) for value in (record.get("matched_identity_values") or [])}
        if str(record.get("record_id")) == target or target in matched:
            candidates.append(record)
    if not candidates:
        return None
    candidates.sort(key=lambda row: (0 if row.get("layer") == "current" else 1, str(row.get("record_id"))))
    return candidates[0]


def _promote_gun_base(record: dict[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {"state": "unresolved", "semantic": {}, "raw": {}, "provenance": None}
    fields = _field_map(record)
    semantic: dict[str, Any] = {}
    raw: dict[str, Any] = {}
    for public_name, source_name in GUN_BASE_SEMANTIC_FIELDS.items():
        rows = fields.get(source_name) or []
        if rows:
            semantic[public_name] = rows[0].get("value")
    for public_name, source_name in GUN_BASE_RAW_FIELDS.items():
        rows = fields.get(source_name) or []
        if rows:
            raw[public_name] = rows[0].get("value")
    return {
        "state": "resolved-installed-game" if semantic else "exact-record-located",
        "semantic": semantic,
        "raw": raw,
        "provenance": {
            "table": record.get("table"),
            "record_id": record.get("record_id"),
            "layer": record.get("layer"),
            "evidence_scope": record.get("evidence_scope", "variant-local"),
            "precedence": record.get("precedence", 2),
        },
    }


def _candidate_summary(answer: dict[str, Any] | None) -> dict[str, Any]:
    answer = answer if isinstance(answer, dict) else {}
    evidence = [row for row in (answer.get("evidence") or []) if isinstance(row, dict)]
    return {
        "state": answer.get("state", "unresolved"),
        "candidate_count": int(answer.get("candidate_count") or 0),
        "evidence": evidence[:10],
    }


def _family_maps(weapons: list[dict[str, Any]]):
    prototypes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    patterns: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for weapon in weapons:
        if _has(weapon.get("prototype_id")):
            prototypes[str(weapon["prototype_id"])].append(weapon)
        ranged = weapon.get("ranged_stats") if isinstance(weapon.get("ranged_stats"), dict) else {}
        if _has(ranged.get("bullet_pattern_id")):
            patterns[str(ranged["bullet_pattern_id"])].append(weapon)
    return prototypes, patterns


def _member_stub(weapon: dict[str, Any]) -> dict[str, Any]:
    return {"blueprint_id": weapon.get("blueprint_id"), "name": weapon.get("name"), "category": weapon.get("category")}


def _snapshot_layers(published_dir: Path) -> tuple[Path | None, Path | None]:
    output = published_dir.parent
    last_run = _read_json(output / "last-run.json", {}) or {}
    active = last_run.get("active_snapshots") if isinstance(last_run, dict) else {}
    active = active if isinstance(active, dict) else {}

    def resolve(raw: Any) -> Path | None:
        text = str(raw or "").strip()
        if not text:
            return None
        path = Path(text).expanduser()
        path = (output / path).resolve() if not path.is_absolute() else path.resolve()
        return path if path.is_dir() else None

    return resolve(active.get("base")), resolve(active.get("current"))


def build_weapon_site_projection(
    weapons_path: Path,
    published_dir: Path,
    corpus_audit: dict[str, Any],
    site_readiness: dict[str, Any],
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    source = _read_json(weapons_path, {}) or {}
    weapons = [row for row in (source.get("weapons") or []) if isinstance(row, dict)]
    corpus_rows = {str(row.get("blueprint_id")): row for row in (corpus_audit.get("weapons") or []) if isinstance(row, dict)}
    readiness_rows = {str(row.get("blueprint_id")): row for row in (site_readiness.get("weapons") or []) if isinstance(row, dict)}
    prototype_families, pattern_families = _family_maps(weapons)

    base_snapshot, current_snapshot = _snapshot_layers(published_dir)
    launch_gap_trace: dict[str, Any] = {"state": "snapshot-layers-unavailable"}
    if base_snapshot is not None and current_snapshot is not None:
        launch_gap_trace = run_weapon_launch_gap_trace(
            base_snapshot,
            current_snapshot,
            weapons_path,
            published_dir / "reports",
            activity=activity,
        )

    output_rows: list[dict[str, Any]] = []
    promoted_gun_base = unresolved_gun_base = variant_family_members = 0

    for weapon in weapons:
        blueprint_id = str(weapon.get("blueprint_id"))
        corpus_weapon = corpus_rows.get(blueprint_id, {})
        readiness = readiness_rows.get(blueprint_id, {})
        questions = readiness.get("questions") if isinstance(readiness.get("questions"), dict) else {}
        enhancements = readiness.get("enhancements") if isinstance(readiness.get("enhancements"), dict) else {}
        first = _first_tier(weapon)
        gun_base = _promote_gun_base(_gun_base_record(corpus_weapon, first.get("gun_no")))
        if gun_base["state"] == "resolved-installed-game":
            promoted_gun_base += 1
        else:
            unresolved_gun_base += 1

        ranged = weapon.get("ranged_stats") if isinstance(weapon.get("ranged_stats"), dict) else None
        star = weapon.get("blueprint_star_progression") if isinstance(weapon.get("blueprint_star_progression"), dict) else {}
        ammo = weapon.get("ammo_configuration") if isinstance(weapon.get("ammo_configuration"), dict) else {}
        tiers = [row for row in (weapon.get("tiers") or []) if isinstance(row, dict)]

        prototype_id = str(weapon.get("prototype_id")) if _has(weapon.get("prototype_id")) else None
        prototype_members = prototype_families.get(prototype_id, []) if prototype_id else []
        family = None
        if len(prototype_members) > 1:
            variant_family_members += 1
            family = {
                "family_id": f"prototype:{prototype_id}",
                "relation": "shared-prototype",
                "prototype_id": weapon.get("prototype_id"),
                "members": [_member_stub(row) for row in prototype_members],
            }

        ballistic_family = None
        if ranged:
            pattern_id = ranged.get("bullet_pattern_id")
            pattern_members = pattern_families.get(str(pattern_id), []) if _has(pattern_id) else []
            if len(pattern_members) > 1:
                ballistic_family = {
                    "relation": "family-shared-ballistics",
                    "bullet_pattern_id": pattern_id,
                    "allowed_inherited_groups": ["projectiles", "bullet_speed", "falloff"],
                    "precedence": {"variant-local": 2, "family-shared": 1},
                    "members": [_member_stub(row) for row in pattern_members],
                }

        acquisition_states = []
        if any(row.get("recipe") for row in tiers):
            acquisition_states.append("recipe-proven")
        if _has(weapon.get("acquisition_hint") or weapon.get("item_gain_path")):
            acquisition_states.append("acquisition-evidence-present")
        if not acquisition_states:
            acquisition_states.append("unresolved")

        output_rows.append({
            "blueprint_id": weapon.get("blueprint_id"),
            "name": weapon.get("name"),
            "category": weapon.get("category"),
            "identity": {
                "item_id": weapon.get("item_id"),
                "prototype_id": weapon.get("prototype_id"),
                "fragment_id": weapon.get("fragment_id"),
                "tier_one_gun_no": first.get("gun_no"),
            },
            "family": family,
            "ballistic_family": ballistic_family,
            "progression": {
                "tiers": [{"tier": row.get("tier"), "item_id": row.get("item_id"), "gun_no": row.get("gun_no"), "damage": row.get("damage")} for row in tiers],
                "blueprint_stars": star.get("stars"),
                "perk_slot_calibration_max": star.get("perk_slot_calibration_max"),
            },
            "handling": gun_base,
            "ranged_stats": ranged,
            "melee_stats": weapon.get("melee_stats") if isinstance(weapon.get("melee_stats"), dict) else None,
            "description": {
                "text": weapon.get("short_description"),
                "state": "resolved-installed-game" if _has(weapon.get("short_description")) else "unresolved",
            },
            "special_skill": {"text": weapon.get("effect"), "resolution": weapon.get("effect_resolution")},
            "acquisition": {
                "states": acquisition_states,
                "hint": weapon.get("acquisition_hint") or weapon.get("item_gain_path"),
                "recipes_by_tier": [{"tier": row.get("tier"), "recipe": row.get("recipe")} for row in tiers if row.get("recipe")],
            },
            "ammo": ammo or None,
            "compatibility": {
                "attachment": {
                    "state": "resolved-partial" if ammo else "unresolved",
                    "value": {"accessory_slot": ammo.get("accessory_slot"), "default_accessory_code": ammo.get("default_accessory_code")} if ammo else None,
                    "research": _candidate_summary(enhancements.get("attachment_compatibility")),
                },
                "calibration": _candidate_summary(enhancements.get("calibration_compatibility")),
                "cradle": _candidate_summary(questions.get("cradle_compatibility")),
            },
            "rarity": {
                "state": "resolved-installed-game" if _has(weapon.get("quality")) and _has(weapon.get("quality_code")) else "unresolved",
                "code": weapon.get("quality_code"),
                "label": weapon.get("quality"),
                "research": _candidate_summary(questions.get("rarity")),
            },
            "firing_mode": {
                "raw_code": (gun_base.get("raw") or {}).get("firing_mode_code"),
                "burst_bullet_num": (gun_base.get("raw") or {}).get("burst_bullet_num"),
                "label_state": "unresolved-code-map",
                "research": _candidate_summary(questions.get("firing_mode")),
            },
            "image": weapon.get("image_asset") or weapon.get("image_reference") or weapon.get("icon"),
            "publication": {
                "source_of_truth": "installed-game",
                "external_values_imported": False,
                "variant_local_overrides_family_shared": True,
            },
        })

    report = {
        "schema": "dead-signal-site-weapons-v2",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "authority": "Installed Once Human game corpus mined by Dead Signal",
        "policy": {
            "external_sources": "reference/question-set only; no external values imported",
            "precedence": "variant-local overrides family-shared",
            "raw_codes": "raw installed codes may be exposed while human labels remain gated until their mapping is proven",
            "unresolved": "absence of a promoted value is never converted into a negative gameplay claim",
        },
        "record_counts": {
            "weapons": len(output_rows),
            "gun_base_promoted": promoted_gun_base,
            "gun_base_unresolved": unresolved_gun_base,
            "variant_family_members": variant_family_members,
            "rarity_promoted": sum(1 for row in output_rows if (row.get("rarity") or {}).get("state") == "resolved-installed-game"),
            "launch_gap_shoot_mode_values": ((launch_gap_trace.get("record_counts") or {}).get("shoot_mode_values", 0) if isinstance(launch_gap_trace, dict) else 0),
            "launch_gap_projectiles_resolved": ((launch_gap_trace.get("record_counts") or {}).get("projectile_counts_resolved", 0) if isinstance(launch_gap_trace, dict) else 0),
            "launch_gap_cradle_tables": ((launch_gap_trace.get("record_counts") or {}).get("cradle_tables", 0) if isinstance(launch_gap_trace, dict) else 0),
        },
        "launch_gap_trace": launch_gap_trace,
        "weapons": output_rows,
    }
    destination = published_dir / "site" / "weapons-v2.json"
    _write_json(destination, report)
    publisher = publish_weapon_site_payloads(weapons_path, published_dir, report, activity=activity)
    report["browser_publish"] = publisher
    _write_json(destination, report)
    activity(
        f"Weapon Website Projection complete: {len(output_rows)} weapons; "
        f"{promoted_gun_base} Tier-I gun-base promotions; lean browser payload written"
    )
    return report
