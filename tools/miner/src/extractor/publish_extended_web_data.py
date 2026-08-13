"""Publish compact player-facing contracts from normalized extended Miner datasets.

This layer never guesses runtime mechanics. Where raw normalized records contain
multiple source variants for one player-facing family, every variant is retained
and the grouping key/status is explicit instead of silently discarding records.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


PLAYER_ATTACHMENT_TYPES = {"Sight", "Muzzle", "Tactical", "Magazine"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def text(value: Any) -> str:
    return str(value or "").strip()


def item_base(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": row.get("item_id"),
        "name": text(row.get("name")),
        "description": text(row.get("description")),
        "rarity": text(row.get("quality")) or "Unknown",
        "quality_code": row.get("quality_code"),
        "gain_path": text(row.get("gain_path")),
        "image_reference": text(row.get("image_asset") or row.get("image_reference")),
    }


def group_variants(
    rows: list[dict[str, Any]],
    key: Callable[[dict[str, Any]], str],
    family_prefix: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[key(row)].append(row)
    families = []
    for family_key, variants in sorted(grouped.items(), key=lambda item: item[0]):
        names = sorted({text(row.get("name")) for row in variants if text(row.get("name"))})
        families.append(
            {
                "canonical_id": f"{family_prefix}-{family_key}",
                "family_key": family_key,
                "name": names[0] if len(names) == 1 else (names[0] if names else "Unnamed"),
                "name_variants": names,
                "variant_count": len(variants),
                "variant_status": "single-source-record" if len(variants) == 1 else "multiple-source-variants-preserved",
                "variants": variants,
            }
        )
    return families


def calibration_variant(row: dict[str, Any]) -> dict[str, Any]:
    base = item_base(row)
    base.update(
        {
            "id": row.get("id"),
            "group_id": row.get("group_id"),
            "style_code": row.get("calibration_style_code"),
            "weapon_type_codes": row.get("weapon_type_codes") or [],
            "is_valid": bool(row.get("is_valid", True)),
            "season_state": row.get("season_state"),
            "buff_id": row.get("buff_id"),
            "roll_range": row.get("calibration_roll_range") or {},
            "affixes": row.get("affixes") or [],
        }
    )
    return base


def build_calibrations(payload: dict[str, Any]) -> dict[str, Any]:
    variants = [calibration_variant(row) for row in payload.get("calibrations", []) if isinstance(row, dict)]
    def key(row: dict[str, Any]) -> str:
        group = row.get("group_id")
        if group not in (None, "", 0, "0"):
            return str(group)
        return f"item-{row.get('item_id')}"
    families = group_variants(variants, key, "ds-cal")
    return {
        "schema": "dead-signal-calibrations",
        "schema_version": 1,
        "generated_utc": utc_now(),
        "source_generated_utc": payload.get("generated_utc"),
        "record_counts": {"families": len(families), "source_variants": len(variants)},
        "publication_status": "family-identity-projected-current-vs-legacy-variant-selection-required",
        "families": families,
    }


def mod_variant(row: dict[str, Any]) -> dict[str, Any]:
    base = item_base(row)
    base.update(
        {
            "id": row.get("id"),
            "mod_code": row.get("mod_code"),
            "apply_range_code": row.get("apply_range_code"),
            "genre_library_code": row.get("genre_library_code"),
            "frame_code": row.get("frame_code"),
            "main_entry_code": row.get("main_entry_code"),
            "is_shiny": bool(row.get("is_shiny")),
            "shiny_buff_id": row.get("shiny_buff_id"),
            "shiny_replacement_mod_code": row.get("shiny_replacement_mod_code"),
            "main_entry_effects": row.get("main_entry_effects") or [],
        }
    )
    return base


def build_mods(payload: dict[str, Any]) -> dict[str, Any]:
    variants = [mod_variant(row) for row in payload.get("mods", []) if isinstance(row, dict)]
    def key(row: dict[str, Any]) -> str:
        code = row.get("mod_code")
        return str(code) if code not in (None, "", 0, "0") else f"item-{row.get('item_id')}"
    families = group_variants(variants, key, "ds-mod")
    return {
        "schema": "dead-signal-mods",
        "schema_version": 1,
        "generated_utc": utc_now(),
        "source_generated_utc": payload.get("generated_utc"),
        "record_counts": {"families": len(families), "source_variants": len(variants)},
        "publication_status": "mod-code-family-projection-variants-preserved",
        "families": families,
    }


def build_attachments(payload: dict[str, Any]) -> dict[str, Any]:
    source = [row for row in payload.get("attachments", []) if isinstance(row, dict)]
    player = []
    excluded = []
    for row in source:
        normalized = item_base(row)
        normalized.update(
            {
                "canonical_id": f"ds-att-{row.get('accessory_code') or row.get('id')}",
                "accessory_code": row.get("accessory_code") or row.get("id"),
                "attachment_type": text(row.get("attachment_type")),
                "affix_code": row.get("affix_code"),
                "effects": row.get("effects") or "",
                "attribute_codes": row.get("attribute_codes") or [],
                "passive_buff_id": row.get("passive_buff_id"),
                "compatible_weapon_types": row.get("compatible_weapon_types") or [],
            }
        )
        if normalized["attachment_type"] in PLAYER_ATTACHMENT_TYPES:
            player.append(normalized)
        else:
            excluded.append({"id": normalized["accessory_code"], "name": normalized["name"], "attachment_type": normalized["attachment_type"]})
    ids = [row["canonical_id"] for row in player]
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    return {
        "schema": "dead-signal-attachments",
        "schema_version": 1,
        "generated_utc": utc_now(),
        "source_generated_utc": payload.get("generated_utc"),
        "record_counts": {"source_records": len(source), "player_weapon_attachments": len(player), "excluded_non_weapon-slot_records": len(excluded)},
        "publication_status": "ready" if not duplicates else "blocked-duplicate-canonical-id",
        "slot_types": sorted(PLAYER_ATTACHMENT_TYPES),
        "duplicate_canonical_ids": duplicates,
        "attachments": sorted(player, key=lambda row: (row["attachment_type"], row["name"].casefold(), str(row["canonical_id"]))),
        "excluded_review": excluded,
    }


def named_variant(row: dict[str, Any], include: tuple[str, ...]) -> dict[str, Any]:
    result = {"id": row.get("id"), "name": text(row.get("name")), "image_reference": text(row.get("image_asset") or row.get("image_reference"))}
    for field in include:
        result[field] = row.get(field)
    return result


def display_name_key(row: dict[str, Any]) -> str:
    name = text(row.get("name")).casefold()
    return name if name else f"id-{row.get('id')}"


def build_deviations(payload: dict[str, Any]) -> dict[str, Any]:
    variants = [named_variant(row, ("deviation_type_code", "unit_id", "unit_type", "collection_value", "containment", "mood", "skills", "skill_catalog")) for row in payload.get("deviations", []) if isinstance(row, dict)]
    families = group_variants(variants, display_name_key, "ds-dev")
    return {
        "schema": "dead-signal-deviations",
        "schema_version": 1,
        "generated_utc": utc_now(),
        "source_generated_utc": payload.get("generated_utc"),
        "record_counts": {"display_name_families": len(families), "source_variants": len(variants)},
        "publication_status": "display-name-families-with-source-variants-preserved",
        "families": families,
    }


def build_cradles(payload: dict[str, Any]) -> dict[str, Any]:
    variants = [named_variant(row, ("description", "buff_id", "keyword_id", "style_code", "attribute_codes", "attribute_values", "selected_image_reference", "equipped_image_reference")) for row in payload.get("cradles", []) if isinstance(row, dict)]
    families = group_variants(variants, display_name_key, "ds-cradle")
    return {
        "schema": "dead-signal-cradles",
        "schema_version": 1,
        "generated_utc": utc_now(),
        "source_generated_utc": payload.get("generated_utc"),
        "record_counts": {"display_name_families": len(families), "source_variants": len(variants)},
        "publication_status": "display-name-families-with-source-variants-preserved",
        "families": families,
    }


BUILDERS: dict[str, tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]] = {
    "calibrations": ("calibrations.json", build_calibrations),
    "mods": ("mods.json", build_mods),
    "attachments": ("attachments.json", build_attachments),
    "deviations": ("deviations.json", build_deviations),
    "cradles": ("cradles.json", build_cradles),
}


def publish(data_dir: Path, published: Path) -> dict[str, Any]:
    web = published / "web"
    outputs = {}
    for category, (filename, builder) in BUILDERS.items():
        source = data_dir / filename
        if not source.is_file():
            raise FileNotFoundError(f"Missing normalized source for compact {category} contract: {source}")
        payload = builder(load_json(source))
        target = web / filename
        write_json(target, payload)
        outputs[category] = {"path": str(target), "record_counts": payload.get("record_counts", {}), "publication_status": payload.get("publication_status")}
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish compact extended Dead Signal website contracts")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--published", type=Path, required=True)
    args = parser.parse_args()
    outputs = publish(args.data_dir, args.published)
    print(json.dumps(outputs, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
