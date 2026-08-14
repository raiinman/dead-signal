"""Enrich normalized Mod 2.0 records with proven frame/sub-entry identities.

Evidence boundary:
- ``frame_code`` selects one exact ``new_mod_frame_lib_data`` row.
- That row preserves four ordered ``sub_entry_item_no`` IDs.
- Each ID resolves to one ``mod_entry_data`` family.
- Regular Levels 1-5 must preserve one stable attribute-code OR buff identity.

The source order is preserved, but this module deliberately does NOT map list
position 0..3 to ``frame_lv_1..4``. Runtime consumer evidence is still required
for that positional claim. Numeric magnitude semantics are likewise untouched.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Callable

from normalize_extended import GAME_DATA, as_int, key_parts, merged_table


REGULAR_LEVELS = {1, 2, 3, 4, 5}
FRAME_TABLE = f"{GAME_DATA}/new_mod_frame_lib_data.json"
ENTRY_TABLE = f"{GAME_DATA}/mod_entry_data.json"


def _entry_rows(entries: dict) -> dict[int, list[tuple[int, dict]]]:
    grouped: dict[int, list[tuple[int, dict]]] = defaultdict(list)
    for key, entry in entries.items():
        parts = [as_int(part) for part in key_parts(key) if part.lstrip("-").isdigit()]
        if not parts or not isinstance(entry, dict):
            continue
        grouped[parts[0]].append((parts[1] if len(parts) > 1 else 0, entry))
    return grouped


def _identity(entry: dict) -> tuple[tuple[str, ...], tuple[int, ...]]:
    attributes = tuple(sorted(str(value) for value in (entry.get("attr_no_list") or []) if str(value).strip()))
    buff_id = as_int(entry.get("buff_id"))
    buffs = (buff_id,) if buff_id else ()
    return attributes, buffs


def entry_family(entry_id: int, entries_by_number: dict[int, list[tuple[int, dict]]]) -> dict:
    rows = sorted(entries_by_number.get(entry_id, []), key=lambda pair: pair[0])
    levels = {level: entry for level, entry in rows}
    available = sorted(levels)
    missing_regular = sorted(REGULAR_LEVELS - set(levels))
    result = {
        "entry_id": entry_id,
        "regular_levels": sorted(REGULAR_LEVELS),
        "available_levels": available,
        "identity_status": "unresolved",
        "source_kind": "",
        "attribute_codes": [],
        "buff_ids": [],
    }
    if missing_regular:
        result["identity_status"] = "missing-regular-levels"
        result["missing_regular_levels"] = missing_regular
        return result

    signatures = []
    for level in sorted(REGULAR_LEVELS):
        signature = _identity(levels[level])
        attributes, buffs = signature
        if bool(attributes) == bool(buffs):
            result["identity_status"] = "ambiguous-attribute-or-buff-identity"
            result["ambiguous_level"] = level
            return result
        signatures.append(signature)

    if len(set(signatures)) != 1:
        result["identity_status"] = "identity-changes-across-regular-levels"
        result["regular_level_identities"] = [
            {
                "level": level,
                "attribute_codes": list(_identity(levels[level])[0]),
                "buff_ids": list(_identity(levels[level])[1]),
            }
            for level in sorted(REGULAR_LEVELS)
        ]
        return result

    attributes, buffs = signatures[0]
    result.update(
        {
            "identity_status": "proven-stable-regular-level-identity",
            "source_kind": "attribute" if attributes else "buff",
            "attribute_codes": list(attributes),
            "buff_ids": list(buffs),
        }
    )
    return result


def frame_evidence(frame_code: int, frames: dict, entries_by_number: dict[int, list[tuple[int, dict]]]) -> dict:
    frame = frames.get(str(frame_code)) or frames.get(frame_code) or {}
    raw_ids = frame.get("sub_entry_item_no") if isinstance(frame, dict) else None
    ids = [as_int(value) for value in raw_ids] if isinstance(raw_ids, list) else []
    result = {
        "frame_code": frame_code,
        "sub_entry_ids": ids,
        "sub_entry_families": [],
        "status": "unresolved",
        "order_semantics": "source-order-preserved; frame_lv_1..4 positional mapping unproven",
    }
    if len(ids) != 4 or any(not value for value in ids):
        result["status"] = "frame-missing-exact-four-sub-entry-ids"
        return result

    families = [entry_family(entry_id, entries_by_number) for entry_id in ids]
    result["sub_entry_families"] = families
    if all(family.get("identity_status") == "proven-stable-regular-level-identity" for family in families):
        result["status"] = "proven-frame-and-sub-entry-family-identities"
    else:
        result["status"] = "sub-entry-family-identity-unresolved"
    return result


def enrich(payload: dict, frames: dict, entries: dict) -> dict:
    mods = payload.get("mods")
    if not isinstance(mods, list):
        raise ValueError("Expected normalized mods payload with a mods array")

    entries_by_number = _entry_rows(entries)
    complete = 0
    unresolved = 0
    used_frames = set()
    used_entries = set()
    unresolved_mod_ids = []

    for row in mods:
        if not isinstance(row, dict):
            continue
        frame_code = as_int(row.get("frame_code"))
        evidence = frame_evidence(frame_code, frames, entries_by_number)
        row["frame_sub_entry_evidence"] = evidence
        if frame_code:
            used_frames.add(frame_code)
        used_entries.update(value for value in evidence.get("sub_entry_ids", []) if value)
        if evidence.get("status") == "proven-frame-and-sub-entry-family-identities":
            complete += 1
        else:
            unresolved += 1
            unresolved_mod_ids.append(row.get("item_id") or row.get("mod_code") or row.get("id"))

    counts = payload.setdefault("record_counts", {})
    counts["frame_evidence_complete"] = complete
    counts["frame_evidence_unresolved"] = unresolved
    counts["used_frame_codes"] = len(used_frames)
    counts["used_sub_entry_families"] = len(used_entries)
    payload["mod_frame_evidence_policy"] = (
        "frame_code -> new_mod_frame_lib_data -> four ordered sub-entry IDs -> stable mod_entry_data identity is proven; "
        "source order is preserved but no position is assigned to frame_lv_1..4 without runtime consumer evidence"
    )
    payload["mod_frame_evidence_unresolved_ids"] = unresolved_mod_ids
    return payload


def enrich_file(
    base: Path | str,
    current: Path | str,
    mods_path: Path | str,
    log: Callable[[str], None] | None = None,
) -> dict:
    base = Path(base)
    current = Path(current)
    mods_path = Path(mods_path)
    payload = json.loads(mods_path.read_text(encoding="utf-8"))
    frames = merged_table(base, current, FRAME_TABLE)
    entries = merged_table(base, current, ENTRY_TABLE)
    enriched = enrich(payload, frames, entries)
    temporary = mods_path.with_suffix(mods_path.suffix + ".tmp")
    temporary.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(mods_path)
    if log:
        counts = enriched.get("record_counts", {})
        log(
            "Resolved Mod 2.0 frame evidence: "
            f"{counts.get('frame_evidence_complete', 0):,} complete / "
            f"{counts.get('frame_evidence_unresolved', 0):,} unresolved; "
            f"{counts.get('used_frame_codes', 0):,} frame codes / "
            f"{counts.get('used_sub_entry_families', 0):,} sub-entry families."
        )
    return enriched


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich normalized Mods with proven Mod 2.0 frame identities")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--mods", type=Path, required=True)
    args = parser.parse_args()
    enriched = enrich_file(args.base, args.current, args.mods)
    print(json.dumps({"record_counts": enriched.get("record_counts", {})}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
