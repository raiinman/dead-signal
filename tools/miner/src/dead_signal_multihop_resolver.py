"""Dead Signal bounded exact-reference resolver for Weapon Description research.

Walks exact installed-game reference occurrences across NeoX records. Every hop is
proven by scalar equality in the reference-tracer index and exact record lookup.
The resolver is research-only: it may surface text/translation candidates but can
never assign VERIFIED or publish player-facing copy.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, deque
from pathlib import Path
from typing import Any, Iterable

from neox_data_explorer import NeoXDataExplorer

SCHEMA_VERSION = 1
MAX_DEPTH = 3
MAX_RECORDS_PER_WEAPON = 240
MAX_REFS_PER_RECORD = 32
MAX_OCCURRENCES_PER_VALUE = 80
MAX_CANDIDATES_PER_WEAPON = 120

REFERENCE_FIELD = re.compile(
    r"(?:^|_)(?:item|blueprint|prototype|gun|weapon|skill|buff|display|ui|tooltip|desc|copy|text|translation|locale|forge|recipe|equip|config|template)(?:_?(?:id|no|code|key|handle))?(?:$|_)",
    re.IGNORECASE,
)
TEXT_FIELD = re.compile(
    r"(?:^|_)(?:short_?desc|description|tooltip|copywriting|copy_?writing|display_?text|flavor|lore|intro|remark|quote|story|tip|tips)(?:$|_)",
    re.IGNORECASE,
)
METADATA_TEXT_FIELD = re.compile(r"(?:^|_)(?:type|mode|flag|switch|index|idx|sort|filter)(?:$|_)", re.IGNORECASE)
TRANSLATION_MARKER = re.compile(r"_\$S@TIDS\$_[^|]*(?:\|.)?$")
FORMAT_TAG = re.compile(r"#(?:[a-zA-Z]+[^#]*)?#|#\[s(?:=[^\]]+)?\]|#l")
DIRECT_COPY_TEXT = re.compile(r"[A-Za-z]{3,}.*[\s.,;:!?'-].*[A-Za-z]{2,}|\s+[A-Za-z]{3,}")


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _scalar(value: Any) -> str:
    if value is None or isinstance(value, bool) or isinstance(value, (dict, list)):
        return ""
    text = str(value).strip()
    if not text or text in {"0", "0.0"} or len(text) > 800:
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


def _weapon_seeds(weapon: dict[str, Any]) -> dict[str, str]:
    seeds: dict[str, str] = {}
    for key in ("blueprint_id", "item_id", "prototype_id", "gun_no"):
        value = _scalar(weapon.get(key))
        if value:
            seeds[key] = value
    for tier in weapon.get("tiers") or []:
        if not isinstance(tier, dict):
            continue
        tier_no = tier.get("tier") or "x"
        for key in ("item_id", "gun_no"):
            value = _scalar(tier.get(key))
            if value:
                seeds[f"tier_{tier_no}_{key}"] = value
    effect = weapon.get("effect_resolution") or {}
    skill = _scalar(effect.get("fixed_skill_code"))
    if skill:
        seeds["fixed_skill_code"] = skill
    return seeds


class MultiHopResolver:
    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        self.explorer = NeoXDataExplorer(self.output)
        self.tracer = self.output / "published" / "indexes" / "reference-tracer.sqlite"
        if not self.tracer.is_file():
            raise ValueError("Reference-tracer index is required for multi-hop resolution")
        self.translations = self._load_translations()

    def _connection(self) -> sqlite3.Connection:
        return sqlite3.connect(f"file:{self.tracer.as_posix()}?mode=ro", uri=True)

    def _load_translations(self) -> list[tuple[str, dict[str, str]]]:
        sources: list[tuple[str, dict[str, str]]] = []
        for layer, root in (("base", self.explorer.base), ("current", self.explorer.current)):
            for path in sorted((root / "translate").glob("translate_data_en*.json")):
                payload = _read_json(path, {}) or {}
                data = payload.get("data", payload) if isinstance(payload, dict) else {}
                if isinstance(data, dict):
                    clean = {str(k): str(v) for k, v in data.items() if isinstance(v, str) and v.strip()}
                    if clean:
                        sources.append((f"{layer}:{path.name}", clean))
        return sources

    def _occurrences(self, value: str) -> list[dict[str, str]]:
        connection = self._connection()
        try:
            rows = connection.execute(
                "SELECT layer,table_name,record_id,field,json_pointer FROM occurrences "
                "WHERE value=? ORDER BY table_name,record_id LIMIT ?",
                (value, MAX_OCCURRENCES_PER_VALUE),
            ).fetchall()
        finally:
            connection.close()
        return [
            {"layer": str(layer), "table": str(table), "record_id": str(record),
             "field": str(field), "json_pointer": str(pointer)}
            for layer, table, record, field, pointer in rows
        ]

    def _resolve_text(self, value: str) -> dict[str, Any]:
        stripped = TRANSLATION_MARKER.sub("", value)
        keys = [value]
        if stripped and stripped != value:
            keys.append(stripped)
        matches = []
        for source, translations in self.translations:
            for key in keys:
                text = translations.get(key)
                if text:
                    matches.append({"source": source, "key": key, "text": text})
        texts = sorted({m["text"] for m in matches})
        direct = texts[0] if len(texts) == 1 else (value if not matches else "")
        cleaned = FORMAT_TAG.sub("", direct).strip() if direct else ""
        return {
            "raw_value": value,
            "marker_stripped_value": stripped,
            "translation_matches": matches,
            "translation_text_count": len(texts),
            "resolved_text": cleaned,
        }

    def _text_candidates(self, record: dict[str, Any], path: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for pointer, field, raw in _walk(record):
            if not TEXT_FIELD.search(field) or METADATA_TEXT_FIELD.search(field):
                continue
            value = _scalar(raw)
            if not value:
                continue
            resolved = self._resolve_text(value)
            translated = bool(resolved["translation_matches"])
            if not translated and not TRANSLATION_MARKER.search(value) and not DIRECT_COPY_TEXT.search(value):
                continue
            out.append({
                "field": field,
                "json_pointer": pointer,
                **resolved,
                "reference_path": path,
                "hop_count": len(path),
                "publication_status": "research-only",
            })
        return out

    def _next_refs(self, record: dict[str, Any]) -> list[dict[str, str]]:
        refs = []
        seen = set()
        for pointer, field, raw in _walk(record):
            if not REFERENCE_FIELD.search(field):
                continue
            value = _scalar(raw)
            if not value or value in seen:
                continue
            seen.add(value)
            refs.append({"field": field, "json_pointer": pointer, "value": value})
            if len(refs) >= MAX_REFS_PER_RECORD:
                break
        return refs

    def resolve_weapon(self, weapon: dict[str, Any]) -> dict[str, Any]:
        seeds = _weapon_seeds(weapon)
        queue = deque()
        for seed_name, value in seeds.items():
            queue.append((value, 0, [{"kind": "weapon-seed", "field": seed_name, "value": value}]))
        visited_values: set[str] = set()
        visited_records: set[tuple[str, str, str]] = set()
        candidates = []
        expanded_records = 0
        traversed_edges = 0

        while queue and expanded_records < MAX_RECORDS_PER_WEAPON and len(candidates) < MAX_CANDIDATES_PER_WEAPON:
            value, depth, path = queue.popleft()
            if value in visited_values:
                continue
            visited_values.add(value)
            for occurrence in self._occurrences(value):
                record_key = (occurrence["layer"], occurrence["table"], occurrence["record_id"])
                if record_key in visited_records:
                    continue
                visited_records.add(record_key)
                try:
                    exact = self.explorer.record(occurrence["table"], occurrence["record_id"], layer=occurrence["layer"])
                except (ValueError, OSError):
                    continue
                expanded_records += 1
                hop = {
                    "kind": "exact-reference",
                    "value": value,
                    "source": occurrence["layer"],
                    "table": occurrence["table"],
                    "record_id": occurrence["record_id"],
                    "field": occurrence["field"],
                    "json_pointer": occurrence["json_pointer"],
                    "depth": depth,
                }
                record_path = path + [hop]
                for candidate in self._text_candidates(exact.get("raw") or {}, record_path):
                    candidate.update({
                        "source": occurrence["layer"],
                        "table": occurrence["table"],
                        "record_id": occurrence["record_id"],
                        "identity_hits": [path[0]],
                    })
                    candidates.append(candidate)
                    if len(candidates) >= MAX_CANDIDATES_PER_WEAPON:
                        break
                if depth >= MAX_DEPTH:
                    continue
                for ref in self._next_refs(exact.get("raw") or {}):
                    if ref["value"] in visited_values:
                        continue
                    traversed_edges += 1
                    queue.append((ref["value"], depth + 1, record_path + [{
                        "kind": "record-reference",
                        "field": ref["field"],
                        "json_pointer": ref["json_pointer"],
                        "value": ref["value"],
                    }]))
                if expanded_records >= MAX_RECORDS_PER_WEAPON:
                    break

        # Mark reused copy after the full report is assembled; per-weapon we only
        # know path provenance and exact traversal facts.
        return {
            "blueprint_id": weapon.get("blueprint_id"),
            "item_id": weapon.get("item_id"),
            "name": weapon.get("name"),
            "category": weapon.get("category"),
            "seed_values": seeds,
            "expanded_records": expanded_records,
            "traversed_edges": traversed_edges,
            "candidate_count": len(candidates),
            "candidates": candidates,
            "classification": "multihop-description-candidates-found" if candidates else "no-multihop-description-candidate",
        }

    def run(self, payload: dict[str, Any], *, activity=None) -> dict[str, Any]:
        activity = activity or (lambda _message: None)
        weapons = [row for row in payload.get("weapons") or [] if isinstance(row, dict)]
        rows = []
        owners: dict[str, set[str]] = {}
        for index, weapon in enumerate(weapons, start=1):
            activity(f"Multi-hop Resolver {index}/{len(weapons)}: {weapon.get('name') or weapon.get('blueprint_id')}")
            row = self.resolve_weapon(weapon)
            rows.append(row)
            owner = str(weapon.get("blueprint_id") or weapon.get("item_id") or index)
            for candidate in row["candidates"]:
                fingerprint = candidate.get("resolved_text") or candidate.get("marker_stripped_value") or candidate.get("raw_value")
                if fingerprint:
                    owners.setdefault(str(fingerprint), set()).add(owner)

        classifications: Counter[str] = Counter()
        for row in rows:
            for candidate in row["candidates"]:
                fingerprint = candidate.get("resolved_text") or candidate.get("marker_stripped_value") or candidate.get("raw_value")
                owner_count = len(owners.get(str(fingerprint), set())) if fingerprint else 0
                candidate["weapon_owner_count"] = owner_count
                candidate["shared_across_weapons"] = owner_count > 1
            classifications[row["classification"]] += 1

        return {
            "schema": "dead-signal-weapon-description-multihop",
            "schema_version": SCHEMA_VERSION,
            "brand": "Dead Signal",
            "record_counts": {
                "weapons": len(rows),
                "classifications": dict(sorted(classifications.items())),
                "candidate_rows": sum(row["candidate_count"] for row in rows),
                "expanded_records": sum(row["expanded_records"] for row in rows),
                "traversed_edges": sum(row["traversed_edges"] for row in rows),
            },
            "bounds": {
                "max_depth": MAX_DEPTH,
                "max_records_per_weapon": MAX_RECORDS_PER_WEAPON,
                "max_refs_per_record": MAX_REFS_PER_RECORD,
                "max_occurrences_per_value": MAX_OCCURRENCES_PER_VALUE,
                "max_candidates_per_weapon": MAX_CANDIDATES_PER_WEAPON,
            },
            "policy": {
                "identity": "Every hop requires exact scalar equality in the installed-game reference tracer and exact record lookup.",
                "discovery": "Reference-field selection only chooses which exact values to follow; it does not prove semantics.",
                "verification": "Multi-hop candidates remain research-only and cannot assign VERIFIED.",
                "publication": "No player-facing data is modified by this resolver.",
            },
            "weapons": rows,
        }
