"""Project normalized Weapon verification diagnostics into the compact contract.

The projector joins by exact blueprint_id + item_id. It never publishes the
normalized short-description text. Translation matches retain source/key
provenance only so bad item-handle assignments or translation-key collisions can
be investigated without leaking suspect copy into the player-facing contract.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


DESCRIPTION_WITHHELD_STATUS = "withheld-until-short-description-resolver-is-verified"


def _safe_description_evidence(source: dict[str, Any] | None) -> dict[str, Any]:
    source = source if isinstance(source, dict) else {}
    matches = []
    for row in source.get("translation_matches") or []:
        if not isinstance(row, dict):
            continue
        matches.append(
            {
                "source": row.get("source"),
                "key_kind": row.get("key_kind"),
                "key": row.get("key"),
            }
        )
    return {
        "status": source.get("status") or "evidence-unavailable",
        "source_table": source.get("source_table") or "game_common/data/item_data.json",
        "source_field": source.get("source_field") or "short_desc",
        "raw_handle": source.get("raw_handle") or "",
        "marker_stripped_handle": source.get("marker_stripped_handle") or "",
        "translation_matches": matches,
        "unique_translation_text_count": int(source.get("unique_translation_text_count") or 0),
        "shared_weapon_handle_count": int(source.get("shared_weapon_handle_count") or 0),
        "shared_weapon_identities": source.get("shared_weapon_identities") or [],
        "publication_status": DESCRIPTION_WITHHELD_STATUS,
    }


def project(normalized_payload: dict[str, Any], web_payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalized_payload.get("weapons")
    web = web_payload.get("weapons")
    if not isinstance(normalized, list):
        raise ValueError("Expected normalized weapons payload with a weapons array")
    if web_payload.get("schema") != "dead-signal-weapons" or not isinstance(web, list):
        raise ValueError("Expected compact dead-signal-weapons contract")

    by_identity = {
        (str(row.get("blueprint_id")), str(row.get("item_id"))): row
        for row in normalized
        if isinstance(row, dict)
        and row.get("blueprint_id") not in (None, "")
        and row.get("item_id") not in (None, "")
    }
    effect_statuses: Counter[str] = Counter()
    description_statuses: Counter[str] = Counter()
    missing_identities = []

    for row in web:
        if not isinstance(row, dict):
            continue
        identity = (str(row.get("blueprint_id")), str(row.get("item_id")))
        source = by_identity.get(identity)
        verification = row.setdefault("verification", {})
        if not source:
            missing_identities.append(
                {
                    "canonical_id": row.get("canonical_id"),
                    "blueprint_id": row.get("blueprint_id"),
                    "item_id": row.get("item_id"),
                }
            )
            row["effect_resolution"] = {
                "status": "normalized-evidence-missing",
                "identity_policy": "exact blueprint_id + item_id only",
            }
            verification["short_description_evidence"] = _safe_description_evidence(None)
            effect_statuses["normalized-evidence-missing"] += 1
            description_statuses["evidence-unavailable"] += 1
            continue

        effect = source.get("effect_resolution")
        if not isinstance(effect, dict):
            effect = {
                "status": "effect-resolution-evidence-missing",
                "identity_policy": "exact passive_skill_data record identity only; similarity aliases are forbidden",
            }
        row["effect_resolution"] = effect
        description = _safe_description_evidence(source.get("short_description_evidence"))
        verification["description_status"] = DESCRIPTION_WITHHELD_STATUS
        verification["short_description_evidence"] = description
        effect_statuses[str(effect.get("status") or "unknown")] += 1
        description_statuses[str(description.get("status") or "unknown")] += 1

    counts = web_payload.setdefault("record_counts", {})
    counts["effect_resolution_statuses"] = dict(sorted(effect_statuses.items()))
    counts["short_description_evidence_statuses"] = dict(sorted(description_statuses.items()))
    counts["weapon_evidence_missing_exact_identity"] = len(missing_identities)
    web_payload["weapon_evidence_missing_exact_identities"] = missing_identities
    web_payload["weapon_evidence_policy"] = {
        "effect_identity": "Exact passive_skill_data record identity only; similar IDs are never substituted.",
        "short_description": "Player-facing text remains blank. Raw item_data.short_desc handles and translation source/key matches are diagnostic only until item-handle identity is independently verified.",
        "projection_join": "Exact blueprint_id + item_id.",
    }
    return web_payload


def project_file(normalized_path: Path | str, web_path: Path | str) -> dict[str, Any]:
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
    parser = argparse.ArgumentParser(description="Project Weapon verification evidence into compact web Weapons")
    parser.add_argument("--normalized", type=Path, required=True)
    parser.add_argument("--web", type=Path, required=True)
    args = parser.parse_args()
    projected = project_file(args.normalized, args.web)
    print(json.dumps({"record_counts": projected.get("record_counts", {})}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
