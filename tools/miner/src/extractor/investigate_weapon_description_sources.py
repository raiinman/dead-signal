#!/usr/bin/env python3
"""Find exact installed-client candidates for Weapon Description text.

This is a research-only investigator. It never publishes text, never matches by
weapon name, and never executes game bytecode. For each normalized Weapon it
scans extracted structured tables for records that contain one of that Weapon's
exact identifiers and also expose description-like fields. The goal is to locate
the client path used by modern weapons whose item_data.short_desc is empty.

Candidate text/handles are evidence, not truth. Repeated placeholder copy,
shared values, conflicting sources, and records without exact weapon identity
must remain blocked from player-facing publication.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


TABLE_HINT = re.compile(
    r"(?:weapon|gun|item|equip|blueprint|prototype|skill|display|ui|tooltip|desc|copy|preview)",
    re.IGNORECASE,
)
IDENTITY_FIELD = re.compile(
    r"(?:^|_)(?:item|blueprint|prototype|gun|weapon)(?:_?(?:id|no|code))?(?:$|_)",
    re.IGNORECASE,
)
TEXT_FIELD = re.compile(
    r"(?:short_?desc|description|desc(?:ription)?_?(?:id|key|no)?|tooltip|copywriting|copy_?writing|flavor|lore|intro|remark|quote|story|tips?)",
    re.IGNORECASE,
)
TRANSLATION_MARKER = re.compile(r"_\$S@TIDS\$_[^|]*(?:\|.)?$")
FORMAT_TAG = re.compile(r"#(?:[a-zA-Z]+[^#]*)?#|#\[s(?:=[^\]]+)?\]|#l")
MAX_VALUE = 800
MAX_MATCHES_PER_WEAPON = 160


def _scalar(value: Any) -> str:
    if value is None or isinstance(value, bool) or isinstance(value, (dict, list)):
        return ""
    text = str(value).strip()
    if not text or text in {"0", "0.0"} or len(text) > MAX_VALUE:
        return ""
    return text


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


def _tables(base: Path, current: Path) -> Iterable[tuple[str, Path, Path]]:
    for layer, root in (("base", base), ("current", current)):
        for path in sorted(root.rglob("*.json")):
            relative = path.relative_to(root).as_posix()
            if relative.startswith("translate/") or relative.endswith("snapshot.json"):
                continue
            if TABLE_HINT.search(relative):
                yield layer, root, path


def _translations(base: Path, current: Path) -> list[tuple[str, dict[str, str]]]:
    sources: list[tuple[str, dict[str, str]]] = []
    candidates = [base / "translate" / "translate_data_en.json"]
    candidates.extend(sorted((current / "translate").glob("translate_data_en*.json")))
    for path in candidates:
        if not path.is_file():
            continue
        payload = _rows(path)
        if not payload:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                raw = {}
            payload = raw.get("data", raw) if isinstance(raw, dict) else {}
        clean = {str(k): str(v) for k, v in payload.items() if isinstance(v, str) and v.strip()}
        if clean:
            sources.append((path.name, clean))
    return sources


def _resolve_text(value: str, sources: list[tuple[str, dict[str, str]]]) -> dict[str, Any]:
    stripped = TRANSLATION_MARKER.sub("", value)
    candidates = [value]
    if stripped and stripped != value:
        candidates.append(stripped)
    matches = []
    for source, translations in sources:
        for key in candidates:
            translated = translations.get(key)
            if translated:
                matches.append({"source": source, "key": key, "text": translated})
    texts = sorted({m["text"] for m in matches})
    direct_text = value
    if matches:
        direct_text = texts[0] if len(texts) == 1 else ""
    cleaned = FORMAT_TAG.sub("", direct_text).strip() if direct_text else ""
    return {
        "raw_value": value,
        "marker_stripped_value": stripped,
        "translation_matches": matches,
        "translation_text_count": len(texts),
        "resolved_text": cleaned,
    }


def weapon_identities(weapon: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("blueprint_id", "item_id", "prototype_id", "gun_no"):
        value = _scalar(weapon.get(key))
        if value:
            out[key] = value
    for tier in weapon.get("tiers") or []:
        if not isinstance(tier, dict):
            continue
        tier_no = tier.get("tier") or len(out)
        for key in ("item_id", "gun_no"):
            value = _scalar(tier.get(key))
            if value:
                out[f"tier_{tier_no}_{key}"] = value
    effect = weapon.get("effect_resolution") or {}
    skill = _scalar(effect.get("fixed_skill_code"))
    if skill:
        out["fixed_skill_code"] = skill
    return out


def _record_identity_hits(record_id: Any, record: Any, identities: set[str]) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    key = _scalar(record_id)
    if key in identities:
        hits.append({"field": "record_id", "json_pointer": "/data", "value": key})
    for pointer, field, raw in _walk(record):
        value = _scalar(raw)
        if value in identities and (IDENTITY_FIELD.search(field) or field in {"skill_no", "skill_code"}):
            hits.append({"field": field, "json_pointer": pointer, "value": value})
    return hits


def _record_text_candidates(record: Any, translations: list[tuple[str, dict[str, str]]]) -> list[dict[str, Any]]:
    candidates = []
    for pointer, field, raw in _walk(record):
        if not TEXT_FIELD.search(field):
            continue
        value = _scalar(raw)
        if not value:
            continue
        candidate = {"field": field, "json_pointer": pointer, **_resolve_text(value, translations)}
        candidates.append(candidate)
    return candidates


def investigate(payload: dict[str, Any], base: Path, current: Path) -> dict[str, Any]:
    weapons = [row for row in payload.get("weapons") or [] if isinstance(row, dict)]
    translations = _translations(base, current)
    tables = list(_tables(base, current))
    rows = []
    value_owners: dict[str, set[str]] = defaultdict(set)

    for weapon in weapons:
        identities = weapon_identities(weapon)
        identity_values = set(identities.values())
        matches = []
        if identity_values:
            for layer, root, path in tables:
                relative = path.relative_to(root).as_posix()
                for record_id, record in _rows(path).items():
                    identity_hits = _record_identity_hits(record_id, record, identity_values)
                    if not identity_hits:
                        continue
                    text_candidates = _record_text_candidates(record, translations)
                    for candidate in text_candidates:
                        if len(matches) >= MAX_MATCHES_PER_WEAPON:
                            break
                        fingerprint = candidate.get("resolved_text") or candidate.get("marker_stripped_value") or candidate.get("raw_value")
                        if fingerprint:
                            value_owners[str(fingerprint)].add(str(weapon.get("blueprint_id")))
                        matches.append({
                            "source": layer,
                            "table": relative,
                            "record_id": str(record_id),
                            "identity_hits": identity_hits,
                            **candidate,
                        })
                    if len(matches) >= MAX_MATCHES_PER_WEAPON:
                        break
                if len(matches) >= MAX_MATCHES_PER_WEAPON:
                    break
        rows.append({
            "blueprint_id": weapon.get("blueprint_id"),
            "item_id": weapon.get("item_id"),
            "name": weapon.get("name"),
            "category": weapon.get("category"),
            "exact_identity_values": identities,
            "candidate_count": len(matches),
            "candidates": matches,
        })

    classifications: Counter[str] = Counter()
    for row in rows:
        candidates = row["candidates"]
        for candidate in candidates:
            fingerprint = candidate.get("resolved_text") or candidate.get("marker_stripped_value") or candidate.get("raw_value")
            owner_count = len(value_owners.get(str(fingerprint), set())) if fingerprint else 0
            candidate["weapon_owner_count"] = owner_count
            candidate["shared_across_weapons"] = owner_count > 1
            candidate["publication_status"] = "research-only"
        unique = [c for c in candidates if not c.get("shared_across_weapons") and c.get("translation_text_count") in {0, 1}]
        if not candidates:
            classification = "no-description-like-field-on-exact-record"
        elif not unique:
            classification = "only-shared-or-conflicting-candidates"
        else:
            classification = "exact-record-description-candidates-found"
        row["classification"] = classification
        row["unique_candidate_count"] = len(unique)
        classifications[classification] += 1

    return {
        "schema": "dead-signal-weapon-description-source-investigation",
        "schema_version": 1,
        "record_counts": {
            "weapons": len(rows),
            "classifications": dict(sorted(classifications.items())),
            "candidate_rows": sum(r["candidate_count"] for r in rows),
        },
        "policy": {
            "source_of_truth": "installed-game Miner snapshot",
            "identity": "Exact weapon identifiers only; names and similar IDs are never used for joins.",
            "candidate": "Description-like fields are evidence candidates only and are not automatically published.",
            "shared_copy": "Text/handles observed on multiple Weapon identities are flagged as shared and blocked from automatic promotion.",
        },
        "weapons": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Find exact client-side Weapon Description source candidates")
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
