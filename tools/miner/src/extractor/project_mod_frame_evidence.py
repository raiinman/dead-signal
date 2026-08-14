"""Project normalized Mod 2.0 frame evidence into compact web Mod variants.

The projector joins only by exact normalized ``item_id``. It copies already
proven frame/sub-entry identities and preserves the unresolved positional
boundary: source list order is retained, but no frame_lv_1..4 assignment is
invented.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PROVEN_STATUS = "proven-frame-and-sub-entry-family-identities"


def project(normalized_payload: dict, web_payload: dict) -> dict:
    normalized_rows = normalized_payload.get("mods")
    families = web_payload.get("families")
    if not isinstance(normalized_rows, list):
        raise ValueError("Expected normalized mods payload with a mods array")
    if web_payload.get("schema") != "dead-signal-mods" or not isinstance(families, list):
        raise ValueError("Expected compact dead-signal-mods contract with families")

    by_item = {
        str(row.get("item_id")): row
        for row in normalized_rows
        if isinstance(row, dict) and row.get("item_id") not in (None, "")
    }
    complete = 0
    unresolved = 0
    missing_normalized_item_ids = []
    used_frame_codes = set()
    used_sub_entries = set()

    for family in families:
        for variant in family.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            item_id = variant.get("item_id")
            normalized = by_item.get(str(item_id))
            evidence = normalized.get("frame_sub_entry_evidence") if normalized else None
            if not isinstance(evidence, dict):
                unresolved += 1
                missing_normalized_item_ids.append(item_id)
                variant["frame_sub_entry_evidence"] = {
                    "status": "normalized-frame-evidence-missing",
                    "order_semantics": "source-order-preserved; frame_lv_1..4 positional mapping unproven",
                }
                continue

            variant["frame_sub_entry_evidence"] = evidence
            frame_code = evidence.get("frame_code")
            if frame_code not in (None, "", 0, "0"):
                used_frame_codes.add(str(frame_code))
            used_sub_entries.update(
                str(value) for value in evidence.get("sub_entry_ids") or [] if value not in (None, "", 0, "0")
            )
            if evidence.get("status") == PROVEN_STATUS:
                complete += 1
            else:
                unresolved += 1

    counts = web_payload.setdefault("record_counts", {})
    counts["frame_evidence_complete_variants"] = complete
    counts["frame_evidence_unresolved_variants"] = unresolved
    counts["used_frame_codes"] = len(used_frame_codes)
    counts["used_sub_entry_families"] = len(used_sub_entries)
    web_payload["mod_frame_evidence_status"] = (
        "proven-entry-identities-positional-level-mapping-unresolved"
        if unresolved == 0
        else "partial-entry-identities-positional-level-mapping-unresolved"
    )
    web_payload["mod_frame_evidence_policy"] = (
        "frame_code -> four source-ordered sub-entry IDs -> stable mod_entry_data identity is proven. "
        "Source order is preserved; no sub-entry is assigned to frame_lv_1..4 until runtime consumer evidence proves the positional mapping."
    )
    web_payload["mod_frame_evidence_missing_normalized_item_ids"] = missing_normalized_item_ids
    return web_payload


def project_file(normalized_path: Path | str, web_path: Path | str) -> dict:
    normalized_path = Path(normalized_path)
    web_path = Path(web_path)
    normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
    web = json.loads(web_path.read_text(encoding="utf-8"))
    projected = project(normalized, web)
    temporary = web_path.with_suffix(web_path.suffix + ".tmp")
    temporary.write_text(json.dumps(projected, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(web_path)
    return projected


def main() -> int:
    parser = argparse.ArgumentParser(description="Project proven Mod frame identities into compact web Mods")
    parser.add_argument("--normalized", type=Path, required=True)
    parser.add_argument("--web", type=Path, required=True)
    args = parser.parse_args()
    projected = project_file(args.normalized, args.web)
    print(json.dumps({"record_counts": projected.get("record_counts", {})}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
