"""Run exact Armor Tier completion after the normal Armor normalizer."""

from __future__ import annotations

import json
from pathlib import Path

from armor_tier_normalization import complete_piece_tiers

INCOMPLETE_TIER_REASON = "Canonical Tier I-V series is incomplete in the current equipment table"


def _table(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("data", {}) if isinstance(payload, dict) else {}


def _first_table(*paths: Path):
    for path in paths:
        if path.exists():
            return _table(path)
    return {}


def complete_file(base, current, output, log=print):
    base = Path(base)
    current = Path(current)
    output = Path(output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    equipment = _table(current / "game_common/data/equip_data.json")
    items = _table(current / "game_common/data/item_data.json")
    origins = _first_table(
        current / "game_common/data/equip_origin_data.json",
        base / "game_common/data/equip_origin_data.json",
    )

    recovered = []
    unresolved = []
    conflicts = []
    for armor_set in payload.get("armor_sets") or []:
        suit_id = int(armor_set.get("suit_id") or 0)
        for piece in armor_set.get("pieces") or []:
            if not isinstance(piece, dict):
                continue
            done, missing, variant_conflicts = complete_piece_tiers(
                piece, suit_id, "set_piece", equipment, origins, items
            )
            recovered.extend(done)
            unresolved.extend(missing)
            conflicts.extend(variant_conflicts)
    for piece in payload.get("key_armor") or []:
        if not isinstance(piece, dict):
            continue
        done, missing, variant_conflicts = complete_piece_tiers(
            piece, 0, "key_armor", equipment, origins, items
        )
        recovered.extend(done)
        unresolved.extend(missing)
        conflicts.extend(variant_conflicts)

    recovered_blueprints = {
        int(row["blueprint_id"])
        for row in recovered
        if row.get("blueprint_id") is not None
    }
    review_queue = []
    for row in payload.get("review_queue") or []:
        try:
            blueprint_id = int(row.get("blueprint_id") or 0)
        except (TypeError, ValueError):
            blueprint_id = 0
        if (
            blueprint_id in recovered_blueprints
            and row.get("reason") == INCOMPLETE_TIER_REASON
        ):
            continue
        review_queue.append(row)
    review_queue.extend(unresolved)
    review_queue.extend(conflicts)
    payload["review_queue"] = review_queue

    set_rows = sum(
        len(piece.get("tiers") or [])
        for armor_set in payload.get("armor_sets") or []
        for piece in armor_set.get("pieces") or []
    )
    key_rows = sum(
        len(piece.get("tiers") or []) for piece in payload.get("key_armor") or []
    )
    counts = payload.setdefault("record_counts", {})
    counts["set_tier_stat_rows"] = set_rows
    counts["key_armor_tier_stat_rows"] = key_rows
    counts["tier_stat_rows"] = set_rows + key_rows
    counts["recovered_tier_stat_rows"] = len(recovered)
    counts["crafting_variant_conflicts"] = len(conflicts)

    payload["armor_tier_recovery"] = {
        "status": "complete" if not unresolved else "partial",
        "recovered": recovered,
        "unresolved": unresolved,
        "crafting_variant_conflicts": conflicts,
    }

    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    temporary.replace(output)
    log(
        "Armor Tier normalization: "
        f"{len(recovered)} recovered, {len(unresolved)} unresolved, "
        f"{len(conflicts)} crafting variant conflicts"
    )
    return payload["armor_tier_recovery"]
