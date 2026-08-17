"""Publish lean website Weapons payloads from the authoritative projection.

The forensic v2 projection intentionally carries research detail. This module
splits it into a browser-facing payload and an evidence sidecar, while promoting
only values already authoritative in the installed-game weapon dataset.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 1
ActivityCallback = Callable[[str], None]


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


def _lean_family(value: Any) -> Any:
    if not isinstance(value, dict):
        return None
    result = {k: value.get(k) for k in ("family_id", "relation", "prototype_id", "bullet_pattern_id", "allowed_inherited_groups", "precedence") if k in value}
    members = value.get("members") or []
    if members:
        result["members"] = [
            {"blueprint_id": row.get("blueprint_id"), "name": row.get("name"), "category": row.get("category")}
            for row in members if isinstance(row, dict)
        ]
    return result


def publish_weapon_site_payloads(
    weapons_path: Path,
    published_dir: Path,
    projection: dict[str, Any],
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    source = _source_map(weapons_path)
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

        description = row.get("description") if isinstance(row.get("description"), dict) else {}
        if _has(description.get("text")):
            resolved_counts["description"] += 1
        if handling.get("state") == "resolved-installed-game":
            resolved_counts["gun_base"] += 1

        projectile_count = ranged.get("projectile_count") if ranged else None
        if _has(projectile_count):
            resolved_counts["projectiles"] += 1

        firing_mode = {
            "code": raw.get("firing_mode_code"),
            "burst_bullet_num": raw.get("burst_bullet_num"),
            "label": None,
            "label_state": "unresolved-code-map" if raw.get("firing_mode_code") is not None else "not-applicable",
        }

        progression = row.get("progression") if isinstance(row.get("progression"), dict) else {}
        acquisition = row.get("acquisition") if isinstance(row.get("acquisition"), dict) else {}
        compatibility = row.get("compatibility") if isinstance(row.get("compatibility"), dict) else {}
        ammo = row.get("ammo") if isinstance(row.get("ammo"), dict) else None
        special = row.get("special_skill") if isinstance(row.get("special_skill"), dict) else {}

        lean = {
            "blueprint_id": row.get("blueprint_id"),
            "name": row.get("name"),
            "category": row.get("category"),
            "rarity": rarity,
            "identity": row.get("identity"),
            "family": _lean_family(row.get("family")),
            "ballistic_family": _lean_family(row.get("ballistic_family")),
            "progression": progression,
            "stats": {
                "damage_tiers": progression.get("tiers"),
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
                "melee": melee,
            },
            "firing_mode": firing_mode,
            "description": description.get("text"),
            "special_skill": {
                "text": special.get("text"),
                "state": ((special.get("resolution") or {}).get("publication_status") if isinstance(special.get("resolution"), dict) else None)
                    or ((special.get("resolution") or {}).get("status") if isinstance(special.get("resolution"), dict) else None),
            },
            "acquisition": {
                "states": acquisition.get("states"),
                "hint": acquisition.get("hint"),
                "recipes_by_tier": acquisition.get("recipes_by_tier"),
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
            "special_skill_resolution": special.get("resolution"),
            "compatibility_research": compatibility,
            "firing_mode_research": row.get("firing_mode"),
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
    activity(f"Lean Weapon Publisher complete: {len(lean_rows)} weapons; rarity promoted for {resolved_counts['rarity']}")
    return {
        "record_counts": {"weapons": len(lean_rows), **resolved_counts},
        "scoreboard": scoreboard,
        "outputs": {
            "weapons": str(site_dir / "weapons.json"),
            "evidence": str(site_dir / "weapon-evidence.json"),
        },
    }
