"""Add fail-closed Weapon effect and short-description provenance diagnostics.

This module does not alter weapon mechanics or publish short-description text.
It records exact installed-game evidence needed to distinguish:
- no fixed skill reference;
- an exact fixed skill ID absent from passive_skill_data;
- an exact skill record whose player-facing effect text remains unresolved;
- a resolved player-facing effect.

For short descriptions it preserves the raw item_data.short_desc handle and the
translation source files/keys that match it. The resolved text remains research
only because a valid translation lookup does not prove the game assigned the
correct handle to the weapon (the known Kukri/frozen-fish cross-wire reproduces
in installed data).
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from normalize_armor import MARKER, Translator, table, translation_entries


PASSIVE_TABLE = "game_common/data/passive_skill_data.json"
ITEM_TABLE = "game_common/data/item_data.json"


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
        "effect_identity": "Exact passive_skill_data record identity only; similar skill IDs are never substituted.",
        "short_description": "Raw item_data.short_desc and translation-source matches are diagnostic only; player-facing description remains withheld until item-handle identity is independently verified.",
    }
    return payload


def enrich_file(base: Path | str, current: Path | str, weapons_path: Path | str, log: Callable[[str], None] | None = None) -> dict[str, Any]:
    base = Path(base)
    current = Path(current)
    weapons_path = Path(weapons_path)
    payload = json.loads(weapons_path.read_text(encoding="utf-8"))
    items = table(current / ITEM_TABLE)
    passive_skills = table(base / PASSIVE_TABLE)
    sources = _translation_sources(base, current)
    enriched = enrich(payload, items, passive_skills, sources)
    temporary = weapons_path.with_suffix(weapons_path.suffix + ".tmp")
    temporary.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(weapons_path)
    if log:
        counts = enriched.get("record_counts", {})
        log(
            "Classified Weapon evidence: "
            f"effects={counts.get('effect_resolution_statuses', {})}; "
            f"short descriptions={counts.get('short_description_evidence_statuses', {})}."
        )
    return enriched


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich normalized Weapons with exact effect and description provenance")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--weapons", type=Path, required=True)
    args = parser.parse_args()
    enriched = enrich_file(args.base, args.current, args.weapons)
    print(json.dumps({"record_counts": enriched.get("record_counts", {})}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
