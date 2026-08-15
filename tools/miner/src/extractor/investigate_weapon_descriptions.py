#!/usr/bin/env python3
"""Investigate Weapon short-description identity without publishing suspect text.

The installed client can provide a valid translation for item_data.short_desc while
that handle is still assigned to the wrong item. This investigator therefore does
not treat translation success as identity proof. It asks a narrower question:
does the exact short-description handle co-occur on another extracted record with
one of the exact identities belonging to the same Weapon?

The report is research-only. Even a positive co-occurrence is a publication
candidate, not automatic permission to expose text. It never performs fuzzy name,
similar-ID, semantic, or family matching and never executes game bytecode.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ITEM_TABLE = "game_common/data/item_data.json"
RELEVANT_TABLE = re.compile(
    r"(?:item|equip|gun|weapon|blueprint|prototype|recipe|display|ui|desc|tooltip)",
    re.IGNORECASE,
)
IDENTITY_FIELDS = re.compile(
    r"(?:^|_)(?:item|blueprint|prototype|gun|weapon)(?:_?(?:id|no))?(?:$|_)",
    re.IGNORECASE,
)
DESCRIPTION_FIELDS = re.compile(r"(?:short_?desc|description|desc_?id|tooltip)", re.IGNORECASE)


def _scalar(value: Any) -> str:
    if value is None or isinstance(value, bool) or isinstance(value, (dict, list)):
        return ""
    text = str(value).strip()
    return text if text and text not in {"0", "0.0"} and len(text) <= 240 else ""


def _walk(value: Any, pointer: str = "") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            child_pointer = f"{pointer}/{escaped}"
            if isinstance(child, (dict, list)):
                yield from _walk(child, child_pointer)
            else:
                yield child_pointer, str(key), child
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_pointer = f"{pointer}/{index}"
            if isinstance(child, (dict, list)):
                yield from _walk(child, child_pointer)
            else:
                yield child_pointer, str(index), child


def _rows(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data", payload)
    return data if isinstance(data, dict) else {}


def _candidate_tables(base: Path, current: Path) -> Iterable[tuple[str, Path, Path]]:
    for layer, root in (("base", base), ("current", current)):
        for path in sorted(root.rglob("*.json")):
            relative = path.relative_to(root).as_posix()
            if relative.startswith("translate/") or relative == ITEM_TABLE:
                continue
            if RELEVANT_TABLE.search(relative):
                yield layer, root, path


def weapon_identity_values(weapon: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("blueprint_id", "item_id", "prototype_id", "gun_no"):
        value = _scalar(weapon.get(key))
        if value:
            out[key] = value
    for tier in weapon.get("tiers") or []:
        if not isinstance(tier, dict):
            continue
        for key in ("item_id", "gun_no"):
            value = _scalar(tier.get(key))
            if value:
                out.setdefault(f"tier_{key}", value)
    return out


def record_cooccurrence(record_id: Any, record: Any, handle: str, identities: set[str]) -> dict[str, Any] | None:
    handle_hits: list[dict[str, str]] = []
    identity_hits: list[dict[str, str]] = []
    record_key = _scalar(record_id)
    if record_key in identities:
        identity_hits.append({"field": "record_id", "json_pointer": "/data", "value": record_key})
    for pointer, field, raw in _walk(record):
        value = _scalar(raw)
        if not value:
            continue
        if value == handle and DESCRIPTION_FIELDS.search(field):
            handle_hits.append({"field": field, "json_pointer": pointer, "value": value})
        if value in identities and IDENTITY_FIELDS.search(field):
            identity_hits.append({"field": field, "json_pointer": pointer, "value": value})
    if not handle_hits or not identity_hits:
        return None
    return {"handle_hits": handle_hits, "identity_hits": identity_hits}


def investigate(payload: dict[str, Any], base: Path, current: Path) -> dict[str, Any]:
    weapons = [row for row in payload.get("weapons") or [] if isinstance(row, dict)]
    rows = []
    counts: Counter[str] = Counter()
    tables = list(_candidate_tables(base, current))

    for weapon in weapons:
        evidence = weapon.get("short_description_evidence") or {}
        handle = _scalar(evidence.get("raw_handle"))
        status = str(evidence.get("status") or "evidence-unavailable")
        identities = weapon_identity_values(weapon)
        exact_values = set(identities.values())
        matches = []

        if handle and exact_values:
            for layer, root, path in tables:
                relative = path.relative_to(root).as_posix()
                for record_id, record in _rows(path).items():
                    match = record_cooccurrence(record_id, record, handle, exact_values)
                    if match:
                        matches.append({
                            "source": layer,
                            "table": relative,
                            "record_id": str(record_id),
                            **match,
                        })

        shared_count = int(evidence.get("shared_weapon_handle_count") or 0)
        translation_count = int(evidence.get("unique_translation_text_count") or 0)
        if not handle:
            classification = "no-short-description-handle"
        elif status == "translation-source-conflict" or translation_count > 1:
            classification = "blocked-translation-conflict"
        elif shared_count > 1:
            classification = "blocked-shared-handle"
        elif not matches:
            classification = "unverified-no-independent-exact-cooccurrence"
        else:
            classification = "candidate-independent-exact-cooccurrence"
        counts[classification] += 1
        rows.append({
            "blueprint_id": weapon.get("blueprint_id"),
            "item_id": weapon.get("item_id"),
            "name": weapon.get("name"),
            "category": weapon.get("category"),
            "raw_handle": handle,
            "translation_status": status,
            "shared_weapon_handle_count": shared_count,
            "exact_identity_values": identities,
            "classification": classification,
            "independent_exact_cooccurrence_count": len(matches),
            "independent_exact_cooccurrences": matches,
            "publication_status": "research-only-manual-review-required",
        })

    return {
        "schema": "dead-signal-weapon-description-identity-investigation",
        "schema_version": 1,
        "record_counts": {"weapons": len(rows), "classifications": dict(sorted(counts.items()))},
        "policy": {
            "source_of_truth": "installed-game Miner snapshot",
            "translation": "Translation success alone is not identity proof.",
            "identity": "Only exact scalar co-occurrence with the same Weapon identities is reported; no fuzzy or semantic joins.",
            "publication": "No description text is automatically promoted by this report.",
        },
        "weapons": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Investigate exact Weapon short-description identity support")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--weapons", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.weapons.read_text(encoding="utf-8"))
    report = investigate(payload, args.base, args.current)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["record_counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
