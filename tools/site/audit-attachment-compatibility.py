#!/usr/bin/env python3
"""Audit Attachment compatibility provenance without converting text to weapon IDs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


EXPECTED_SLOTS = {"Sight", "Muzzle", "Tactical", "Magazine"}
DIRECT_STATUS = "direct-localized-installed-game-text"


def resolve_source(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.is_file():
        return path
    for candidate in (path / "web" / "attachments.json", path / "attachments.json"):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Could not find compact attachments.json under {path}")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Attachment contract must be a JSON object")
    return payload


def audit(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema") != "dead-signal-attachments" or payload.get("schema_version") != 2:
        raise ValueError("Expected dead-signal-attachments schema_version 2")
    rows = payload.get("attachments")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Attachment contract must contain an attachments object array")

    slot_counts: Counter[str] = Counter()
    direct = []
    unresolved = []
    invalid = []
    coded = []
    for row in rows:
        canonical_id = str(row.get("canonical_id") or "").strip()
        slot = str(row.get("attachment_type") or "").strip()
        slot_counts[slot] += 1
        evidence = row.get("compatibility_evidence")
        if row.get("compatible_weapon_types"):
            coded.append(canonical_id)
        if not canonical_id or slot not in EXPECTED_SLOTS or not isinstance(evidence, dict):
            invalid.append(canonical_id or "missing-canonical-id")
            continue
        status = str(evidence.get("status") or "").strip()
        evidence_text = str(evidence.get("text") or "").strip()
        if status == DIRECT_STATUS and evidence_text and evidence.get("source_field") == "description":
            direct.append({"canonical_id": canonical_id, "name": row.get("name"), "text": evidence_text})
        elif status == "unresolved" and not evidence_text:
            unresolved.append({"canonical_id": canonical_id, "name": row.get("name")})
        else:
            invalid.append(canonical_id)

    declared = payload.get("record_counts") or {}
    count_mismatches = []
    if declared.get("direct_compatibility_text") != len(direct):
        count_mismatches.append("record_counts.direct_compatibility_text")
    if declared.get("unresolved_compatibility") != len(unresolved):
        count_mismatches.append("record_counts.unresolved_compatibility")
    if declared.get("player_weapon_attachments") != len(rows):
        count_mismatches.append("record_counts.player_weapon_attachments")

    return {
        "schema": "dead-signal-attachment-compatibility-audit",
        "schema_version": 1,
        "policy": "Localized compatibility wording is direct evidence; it is never converted into inferred weapon IDs or class codes by this audit.",
        "counts": {
            "attachments": len(rows),
            "direct_localized_compatibility": len(direct),
            "unresolved_compatibility": len(unresolved),
            "coded_compatibility_records": len(coded),
            "invalid_records": len(invalid),
        },
        "slot_counts": dict(sorted(slot_counts.items())),
        "ready": (
            payload.get("publication_status") == "ready"
            and set(slot_counts) == EXPECTED_SLOTS
            and not invalid
            and not count_mismatches
            and len(direct) + len(unresolved) == len(rows)
        ),
        "direct_evidence": direct,
        "unresolved": unresolved,
        "coded_compatibility_records": coded,
        "count_mismatches": count_mismatches,
        "invalid_records": invalid,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit compact Attachment compatibility provenance")
    parser.add_argument("source", type=Path, help="attachments.json, published/web/, or published/")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    source = resolve_source(args.source)
    report = audit(load_json(source))
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
