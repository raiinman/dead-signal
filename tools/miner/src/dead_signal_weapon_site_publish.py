"""Publish lean website Weapons payloads from the authoritative projection.

The forensic v2 projection intentionally carries research detail. This module
splits it into a browser-facing payload and an evidence/detail sidecar, while
promoting only values already authoritative in the installed-game weapon
dataset. Heavy Blueprint-Star records and full recipe bodies stay out of the
listing payload so the website does not download research/detail data up front.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 4
ActivityCallback = Callable[[str], None]
SHOOT_DISPLAY = {
    "NONE": "None",
    "SINGLE": "Single",
    "BURST": "Burst",
    "AUTO": "Auto",
}


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, UnicodeError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temp.replace(path)


def _has(value: Any) -> bool:
    return value not in (None, "", [], {})


def _source_map(weapons_path: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(weapons_path, {}) or {}
    return {
        str(row.get("blueprint_id")): row
        for row in (payload.get("weapons") or [])
        if isinstance(row, dict) and row.get("blueprint_id") not in (None, "")
    }


def _prototype_description_map(published_dir: Path) -> dict[str, dict[str, Any]]:
    report = _read_json(
        published_dir / "reports" / "weapon-description-prototype-projection.json",
        {},
    ) or {}
    result: dict[str, dict[str, Any]] = {}
    for row in report.get("weapons") or []:
        if not isinstance(row, dict) or row.get("blueprint_id") in (None, ""):
            continue
        result[str(row.get("blueprint_id"))] = row
    return result


def _launch_gap_maps(published_dir: Path) -> tuple[dict[Any, str], dict[str, dict[str, Any]], dict[str, Any]]:
    report = _read_json(published_dir / "reports" / "weapon-launch-gap-trace.json", {}) or {}
    firing = report.get("firing_mode") if isinstance(report.get("firing_mode"), dict) else {}
    raw_mapping = firing.get("mapping") if isinstance(firing.get("mapping"), dict) else {}
    reverse: dict[Any, str] = {}
    if str(firing.get("state") or "").startswith("resolved-static"):
        for symbol, code in raw_mapping.items():
            if isinstance(code, (int, float)) and not isinstance(code, bool):
                reverse[code] = str(symbol)

    projectile_rows: dict[str, dict[str, Any]] = {}
    projectiles = report.get("projectiles") if isinstance(report.get("projectiles"), dict) else {}
    for row in projectiles.get("weapons") or []:
        if not isinstance(row, dict) or row.get("blueprint_id") in (None, ""):
            continue
        projectile_rows[str(row.get("blueprint_id"))] = row
    return reverse, projectile_rows, report


def _promote_description(
    projection_description: dict[str, Any],
    prototype_row: dict[str, Any] | None,
) -> tuple[str | None, str, dict[str, Any] | None]:
    local_text = projection_description.get("text") if isinstance(projection_description, dict) else None
    if _has(local_text):
        return str(local_text), "resolved-installed-game-weapon-local", {
            "scope": "variant-local",
            "source": "published/data/weapons.json",
            "precedence": 2,
        }

    row = prototype_row if isinstance(prototype_row, dict) else {}
    status = str(row.get("status") or "")
    text = row.get("text")
    if status == "prototype-desc-resolved-consistently" and _has(text):
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        shared = bool(row.get("shared_across_prototypes"))
        return str(text), "resolved-installed-game-prototype", {
            "scope": "family-shared" if shared else "prototype-local",
            "precedence": 1,
            "prototype_id": row.get("prototype_id"),
            "shared_across_prototypes": shared,
            "shared_prototype_ids": row.get("shared_prototype_ids") or [],
            "table": source.get("relative_path"),
            "record_id": source.get("record_id"),
            "field": source.get("field"),
            "layer": source.get("layer"),
            "translation_match_count": len(row.get("translation_matches") or []),
            "translation_state": status,
        }

    unresolved = {
        "scope": "unresolved",
        "prototype_id": row.get("prototype_id"),
        "translation_state": status or "prototype-description-unavailable",
    } if row else None
    return None, "unresolved", unresolved


def _lean_family(value: Any) -> Any:
    if not isinstance(value, dict):
        return None
    result = {
        k: value.get(k)
        for k in (
            "family_id",
            "relation",
            "prototype_id",
            "bullet_pattern_id",
            "allowed_inherited_groups",
            "precedence",
        )
        if k in value
    }
    members = value.get("members") or []
    if members:
        result["members"] = [
            {
                "blueprint_id": row.get("blueprint_id"),
                "name": row.get("name"),
                "category": row.get("category"),
            }
            for row in members
            if isinstance(row, dict)
        ]
    return result


def _tier_summary(progression: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for row in progression.get("tiers") or []:
        if not isinstance(row, dict):
            continue
        result.append({
            "tier": row.get("tier"),
            "damage": row.get("damage"),
            "item_id": row.get("item_id"),
            "gun_no": row.get("gun_no"),
        })
    return result


def _star_summary(progression: dict[str, Any]) -> dict[str, Any]:
    stars = [row for row in (progression.get("blueprint_stars") or []) if isinstance(row, dict)]
    return {
        "levels": [row.get("blueprint_stars") for row in stars if row.get("blueprint_stars") is not None],
        "count": len(stars),
        "perk_slot_calibration_max": progression.get("perk_slot_calibration_max"),
    }


def publish_weapon_site_payloads(
    weapons_path: Path,
    published_dir: Path,
    projection: dict[str, Any],
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    source = _source_map(weapons_path)
    prototype_descriptions = _prototype_description_map(published_dir)
    shoot_code_to_symbol, launch_projectiles, launch_gap_report = _launch_gap_maps(published_dir)
    rows = [row for row in (projection.get("weapons") or []) if isinstance(row, dict)]
    lean_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    resolved_counts = {
        "rarity": 0,
        "description": 0,
        "gun_base": 0,
        "firing_mode_label": 0,
        "projectiles": 0,
        "cradle": 0,
    }

    for row in rows:
        bid = str(row.get("blueprint_id"))
        original = source.get(bid, {})
        handling = row.get("handling") if isinstance(row.get("handling"), dict) else {}
        semantic = handling.get("semantic") if isinstance(handling.get("semantic"), dict) else {}
        raw = handling.get("raw") if isinstance(handling.get("raw"), dict) else {}
        ranged = row.get("ranged_stats") if isinstance(row.get("ranged_stats"), dict) else None
        melee = row.get("melee_stats") if isinstance(row.get("melee_stats"), dict) else None

        rarity = None
        if _has(original.get("quality")) and _has(original.get("quality_code")):
            rarity = {
                "code": original.get("quality_code"),
                "label": original.get("quality"),
                "state": "resolved-installed-game",
            }
            resolved_counts["rarity"] += 1

        projection_description = row.get("description") if isinstance(row.get("description"), dict) else {}
        description_text, description_state, description_provenance = _promote_description(
            projection_description,
            prototype_descriptions.get(bid),
        )
        if _has(description_text):
            resolved_counts["description"] += 1

        if handling.get("state") == "resolved-installed-game":
            resolved_counts["gun_base"] += 1

        projectile_trace = launch_projectiles.get(bid, {})
        projectile_count = ranged.get("projectile_count") if ranged else None
        projectile_state = "resolved-installed-game-normalized" if _has(projectile_count) else "unresolved"
        projectile_provenance = None
        if not _has(projectile_count):
            traced = projectile_trace.get("projectile_count") if isinstance(projectile_trace, dict) else None
            if _has(traced) and projectile_trace.get("state") == "resolved-exact-pattern-record":
                projectile_count = traced
                projectile_state = "resolved-installed-game-pattern"
                projectile_provenance = {
                    "table": ((projectile_trace.get("source") or {}).get("pattern_table") if isinstance(projectile_trace.get("source"), dict) else None),
                    "record_id": projectile_trace.get("bullet_pattern_no"),
                    "field": projectile_trace.get("projectile_count_field"),
                    "scope": "family-shared" if row.get("ballistic_family") else "variant-local",
                }
        if _has(projectile_count):
            resolved_counts["projectiles"] += 1

        firing_code = raw.get("firing_mode_code")
        firing_symbol = shoot_code_to_symbol.get(firing_code)
        if firing_symbol:
            firing_mode = {
                "code": firing_code,
                "symbol": firing_symbol,
                "burst_bullet_num": raw.get("burst_bullet_num"),
                "label": SHOOT_DISPLAY.get(firing_symbol, firing_symbol.title()),
                "label_state": "resolved-installed-game-enum",
            }
            resolved_counts["firing_mode_label"] += 1
        else:
            firing_mode = {
                "code": firing_code,
                "symbol": None,
                "burst_bullet_num": raw.get("burst_bullet_num"),
                "label": None,
                "label_state": "unresolved-code-map" if firing_code is not None else "not-applicable",
            }

        progression = row.get("progression") if isinstance(row.get("progression"), dict) else {}
        acquisition = row.get("acquisition") if isinstance(row.get("acquisition"), dict) else {}
        compatibility = row.get("compatibility") if isinstance(row.get("compatibility"), dict) else {}
        ammo = row.get("ammo") if isinstance(row.get("ammo"), dict) else None
        special = row.get("special_skill") if isinstance(row.get("special_skill"), dict) else {}
        tiers = _tier_summary(progression)

        lean = {
            "blueprint_id": row.get("blueprint_id"),
            "name": row.get("name"),
            "category": row.get("category"),
            "rarity": rarity,
            "identity": row.get("identity"),
            "family": _lean_family(row.get("family")),
            "ballistic_family": _lean_family(row.get("ballistic_family")),
            "progression": {
                "tiers": tiers,
                "blueprint_stars": _star_summary(progression),
            },
            "stats": {
                "damage_tiers": [{"tier": tier.get("tier"), "damage": tier.get("damage")} for tier in tiers],
                "ads_time": semantic.get("ads_time"),
                "bullet_speed": semantic.get("bullet_speed"),
                "reload_score": semantic.get("reload_score"),
                "reload_time_seconds": semantic.get("reload_time_seconds"),
                "magazine": semantic.get("magazine"),
                "mobility": semantic.get("mobility"),
                "effective_range": semantic.get("effective_range"),
                "range_score": semantic.get("range_score"),
                "fire_rate_rpm": semantic.get("fire_rate_display_rpm"),
                "accuracy": ranged.get("accuracy") if ranged else None,
                "stability": ranged.get("stability") if ranged else None,
                "full_damage_distance": ranged.get("full_damage_distance") if ranged else None,
                "minimum_damage_distance": ranged.get("minimum_damage_distance") if ranged else None,
                "minimum_damage_multiplier": ranged.get("minimum_damage_multiplier") if ranged else None,
                "projectile_count": projectile_count,
                "projectile_count_state": projectile_state,
                "melee": melee,
            },
            "firing_mode": firing_mode,
            "description": description_text,
            "description_state": description_state,
            "special_skill": {
                "text": special.get("text"),
                "state": ((special.get("resolution") or {}).get("publication_status") if isinstance(special.get("resolution"), dict) else None)
                    or ((special.get("resolution") or {}).get("status") if isinstance(special.get("resolution"), dict) else None),
            },
            "acquisition": {
                "states": acquisition.get("states"),
                "hint": acquisition.get("hint"),
                "recipe_tiers": [entry.get("tier") for entry in (acquisition.get("recipes_by_tier") or []) if isinstance(entry, dict)],
            },
            "ammo": ammo,
            "compatibility": {
                "attachment": {
                    "state": ((compatibility.get("attachment") or {}).get("state") if isinstance(compatibility.get("attachment"), dict) else "unresolved"),
                    "value": ((compatibility.get("attachment") or {}).get("value") if isinstance(compatibility.get("attachment"), dict) else None),
                },
                "calibration_state": ((compatibility.get("calibration") or {}).get("state") if isinstance(compatibility.get("calibration"), dict) else "unresolved"),
                "cradle_state": ((compatibility.get("cradle") or {}).get("state") if isinstance(compatibility.get("cradle"), dict) else "unresolved"),
            },
            "image": row.get("image"),
        }
        lean_rows.append(lean)

        evidence_rows.append({
            "blueprint_id": row.get("blueprint_id"),
            "name": row.get("name"),
            "handling": {
                "provenance": handling.get("provenance"),
                "raw": raw,
            },
            "rarity": {
                "source": "published/data/weapons.json",
                "quality_code": original.get("quality_code"),
                "quality": original.get("quality"),
            },
            "description": {
                "state": description_state,
                "text": description_text,
                "provenance": description_provenance,
                "prototype_projection": prototype_descriptions.get(bid),
            },
            "projectiles": {
                "state": projectile_state,
                "value": projectile_count,
                "provenance": projectile_provenance,
                "launch_gap_trace": projectile_trace,
            },
            "firing_mode": {
                "published": firing_mode,
                "enum_trace": (launch_gap_report.get("firing_mode") if isinstance(launch_gap_report, dict) else None),
                "research": row.get("firing_mode"),
            },
            "progression": progression,
            "acquisition": acquisition,
            "special_skill_resolution": special.get("resolution"),
            "compatibility_research": compatibility,
            "projection_publication": row.get("publication"),
        })

    applicable = len(lean_rows) * 6
    resolved_total = sum(resolved_counts.values())
    scoreboard = {
        "tracked_fields": list(resolved_counts.keys()),
        "resolved": resolved_counts,
        "resolved_total": resolved_total,
        "applicable_slots": applicable,
        "percent": round((resolved_total / applicable * 100.0) if applicable else 0.0, 2),
        "note": "This compact post-promotion scoreboard tracks only the six launch fields listed here; detailed readiness remains in weapon-site-readiness.json.",
    }

    site_dir = published_dir / "site"
    lean_payload = {
        "schema": "dead-signal-site-weapons",
        "schema_version": SCHEMA_VERSION,
        "authority": "installed-game",
        "record_counts": {"weapons": len(lean_rows)},
        "scoreboard": scoreboard,
        "weapons": lean_rows,
    }
    evidence_payload = {
        "schema": "dead-signal-site-weapon-evidence",
        "schema_version": SCHEMA_VERSION,
        "authority": "installed-game",
        "record_counts": {"weapons": len(evidence_rows)},
        "weapons": evidence_rows,
    }
    _write_json(site_dir / "weapons.json", lean_payload)
    _write_json(site_dir / "weapon-evidence.json", evidence_payload)
    activity(
        f"Lean Weapon Publisher complete: {len(lean_rows)} weapons; "
        f"rarity {resolved_counts['rarity']}; descriptions {resolved_counts['description']}; "
        f"firing modes {resolved_counts['firing_mode_label']}; projectiles {resolved_counts['projectiles']}"
    )
    return {
        "record_counts": {"weapons": len(lean_rows), **resolved_counts},
        "scoreboard": scoreboard,
        "outputs": {
            "weapons": str(site_dir / "weapons.json"),
            "evidence": str(site_dir / "weapon-evidence.json"),
        },
    }
