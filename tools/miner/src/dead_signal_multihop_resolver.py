"""Dead Signal bounded exact-reference resolver for Weapon Description research.

Walks exact installed-game reference occurrences across NeoX records. Every hop is
proven by scalar equality in the read-only reference-tracer index. The resolver is
research-only: it may surface text/translation candidates but can never assign
VERIFIED or publish player-facing copy.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, OrderedDict, deque
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_DEPTH = 3
MAX_RECORDS_PER_WEAPON = 240
MAX_REFS_PER_RECORD = 32
MAX_OCCURRENCES_PER_VALUE = 80
MAX_CANDIDATES_PER_WEAPON = 120
MAX_OCCURRENCE_CACHE = 20000
MAX_RECORD_CACHE = 20000

REFERENCE_FIELD = re.compile(
    r"(?:^|_)(?:item|blueprint|prototype|gun|weapon|skill|buff|display|ui|tooltip|desc|copy|text|translation|locale|forge|recipe|equip|config|template)(?:_?(?:id|no|code|key|handle))?(?:$|_)",
    re.IGNORECASE,
)
TEXT_FIELD = re.compile(
    r"(?:^|_)(?:short_?desc|description|tooltip|copywriting|copy_?writing|display_?text|flavor|lore|intro|remark|quote|story|tip|tips)(?:$|_)",
    re.IGNORECASE,
)
METADATA_TEXT_FIELD = re.compile(
    r"(?:^|_)(?:type|mode|flag|switch|index|idx|sort|filter)(?:$|_)", re.IGNORECASE
)
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


def _safe_snapshot_root(output: Path, value: object, label: str) -> Path:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"Completed snapshot metadata does not identify the {label} NeoX layer")
    path = Path(text).expanduser()
    path = path.resolve() if path.is_absolute() else (output / path).resolve()
    try:
        path.relative_to(output)
    except ValueError as error:
        raise ValueError(f"{label.capitalize()} snapshot must stay inside the selected Miner data folder") from error
    if not path.is_dir() or path.is_symlink():
        raise ValueError(f"{label.capitalize()} snapshot is not a readable local directory: {path}")
    return path


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
        if not self.output.is_dir():
            raise ValueError("Select a completed Dead Signal Miner data folder")
        last_run = _read_json(self.output / "last-run.json", {}) or {}
        active = last_run.get("active_snapshots") if isinstance(last_run, dict) else {}
        active = active if isinstance(active, dict) else {}
        self.base = _safe_snapshot_root(self.output, active.get("base"), "base")
        self.current = _safe_snapshot_root(self.output, active.get("current"), "current")
        self.tracer = self.output / "published" / "indexes" / "reference-tracer.sqlite"
        if not self.tracer.is_file() or self.tracer.is_symlink():
            raise ValueError("Reference-tracer index is required for multi-hop resolution")
        self.translations = self._load_translations()
        self._db: sqlite3.Connection | None = None
        self._occurrence_cache: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
        self._record_cache: OrderedDict[tuple[str, str, str], list[dict[str, str]]] = OrderedDict()

    def _connection(self) -> sqlite3.Connection:
        if self._db is None:
            self._db = sqlite3.connect(f"file:{self.tracer.as_posix()}?mode=ro", uri=True)
        return self._db

    def close(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None

    def _load_translations(self) -> list[tuple[str, dict[str, str]]]:
        sources: list[tuple[str, dict[str, str]]] = []
        for layer, root in (("base", self.base), ("current", self.current)):
            for path in sorted((root / "translate").glob("translate_data_en*.json")):
                payload = _read_json(path, {}) or {}
                data = payload.get("data", payload) if isinstance(payload, dict) else {}
                if isinstance(data, dict):
                    clean = {
                        str(key): str(value)
                        for key, value in data.items()
                        if isinstance(value, str) and value.strip()
                    }
                    if clean:
                        sources.append((f"{layer}:{path.name}", clean))
        return sources

    def _occurrences(self, value: str) -> list[dict[str, str]]:
        cached = self._occurrence_cache.get(value)
        if cached is not None:
            self._occurrence_cache.move_to_end(value)
            return cached
        rows = self._connection().execute(
            "SELECT layer,table_name,record_id,field,json_pointer FROM occurrences "
            "WHERE value=? ORDER BY table_name,record_id,json_pointer LIMIT ?",
            (value, MAX_OCCURRENCES_PER_VALUE),
        ).fetchall()
        result = [
            {
                "layer": str(layer),
                "table": str(table),
                "record_id": str(record),
                "field": str(field),
                "json_pointer": str(pointer),
            }
            for layer, table, record, field, pointer in rows
        ]
        self._occurrence_cache[value] = result
        self._occurrence_cache.move_to_end(value)
        while len(self._occurrence_cache) > MAX_OCCURRENCE_CACHE:
            self._occurrence_cache.popitem(last=False)
        return result

    def _record_fields(self, layer: str, table: str, record_id: str) -> list[dict[str, str]]:
        """Read one exact record's flattened scalar fields directly from the tracer."""
        key = (layer, table, record_id)
        cached = self._record_cache.get(key)
        if cached is not None:
            self._record_cache.move_to_end(key)
            return cached
        rows = self._connection().execute(
            "SELECT field,json_pointer,value FROM occurrences "
            "WHERE layer=? AND table_name=? AND record_id=? ORDER BY json_pointer",
            (layer, table, record_id),
        ).fetchall()
        result = [
            {"field": str(field), "json_pointer": str(pointer), "value": str(value)}
            for field, pointer, value in rows
        ]
        self._record_cache[key] = result
        self._record_cache.move_to_end(key)
        while len(self._record_cache) > MAX_RECORD_CACHE:
            self._record_cache.popitem(last=False)
        return result

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
        texts = sorted({match["text"] for match in matches})
        direct = texts[0] if len(texts) == 1 else (value if not matches else "")
        cleaned = FORMAT_TAG.sub("", direct).strip() if direct else ""
        return {
            "raw_value": value,
            "marker_stripped_value": stripped,
            "translation_matches": matches,
            "translation_text_count": len(texts),
            "resolved_text": cleaned,
        }

    def _text_candidates(
        self, fields: list[dict[str, str]], path: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        candidates = []
        for row in fields:
            field = row["field"]
            if not TEXT_FIELD.search(field) or METADATA_TEXT_FIELD.search(field):
                continue
            value = _scalar(row["value"])
            if not value:
                continue
            resolved = self._resolve_text(value)
            translated = bool(resolved["translation_matches"])
            if not translated and not TRANSLATION_MARKER.search(value) and not DIRECT_COPY_TEXT.search(value):
                continue
            candidates.append(
                {
                    "field": field,
                    "json_pointer": row["json_pointer"],
                    **resolved,
                    "reference_path": path,
                    "hop_count": len(path),
                    "publication_status": "research-only",
                }
            )
        return candidates

    def _next_refs(self, fields: list[dict[str, str]]) -> list[dict[str, str]]:
        references = []
        seen = set()
        for row in fields:
            field = row["field"]
            if not REFERENCE_FIELD.search(field):
                continue
            value = _scalar(row["value"])
            if not value or value in seen:
                continue
            seen.add(value)
            references.append(
                {"field": field, "json_pointer": row["json_pointer"], "value": value}
            )
            if len(references) >= MAX_REFS_PER_RECORD:
                break
        return references

    def resolve_weapon(self, weapon: dict[str, Any]) -> dict[str, Any]:
        seeds = _weapon_seeds(weapon)
        queue = deque(
            (value, 0, [{"kind": "weapon-seed", "field": seed_name, "value": value}])
            for seed_name, value in seeds.items()
        )
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
                fields = self._record_fields(*record_key)
                if not fields:
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
                for candidate in self._text_candidates(fields, record_path):
                    candidate.update(
                        {
                            "source": occurrence["layer"],
                            "table": occurrence["table"],
                            "record_id": occurrence["record_id"],
                            "identity_hits": [path[0]],
                        }
                    )
                    candidates.append(candidate)
                    if len(candidates) >= MAX_CANDIDATES_PER_WEAPON:
                        break
                if depth >= MAX_DEPTH:
                    continue
                for reference in self._next_refs(fields):
                    if reference["value"] in visited_values:
                        continue
                    traversed_edges += 1
                    queue.append(
                        (
                            reference["value"],
                            depth + 1,
                            record_path
                            + [
                                {
                                    "kind": "record-reference",
                                    "field": reference["field"],
                                    "json_pointer": reference["json_pointer"],
                                    "value": reference["value"],
                                }
                            ],
                        )
                    )
                if expanded_records >= MAX_RECORDS_PER_WEAPON:
                    break

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
            "classification": (
                "multihop-description-candidates-found"
                if candidates
                else "no-multihop-description-candidate"
            ),
        }

    def run(self, payload: dict[str, Any], *, activity=None) -> dict[str, Any]:
        activity = activity or (lambda _message: None)
        weapons = [row for row in payload.get("weapons") or [] if isinstance(row, dict)]
        rows = []
        owners: dict[str, set[str]] = {}
        try:
            for index, weapon in enumerate(weapons, start=1):
                activity(
                    f"Multi-hop Resolver {index}/{len(weapons)}: "
                    f"{weapon.get('name') or weapon.get('blueprint_id')}"
                )
                row = self.resolve_weapon(weapon)
                rows.append(row)
                owner = str(weapon.get("blueprint_id") or weapon.get("item_id") or index)
                for candidate in row["candidates"]:
                    fingerprint = (
                        candidate.get("resolved_text")
                        or candidate.get("marker_stripped_value")
                        or candidate.get("raw_value")
                    )
                    if fingerprint:
                        owners.setdefault(str(fingerprint), set()).add(owner)
        finally:
            self.close()

        classifications: Counter[str] = Counter()
        for row in rows:
            for candidate in row["candidates"]:
                fingerprint = (
                    candidate.get("resolved_text")
                    or candidate.get("marker_stripped_value")
                    or candidate.get("raw_value")
                )
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
                "max_cached_occurrence_values": MAX_OCCURRENCE_CACHE,
                "max_cached_records": MAX_RECORD_CACHE,
            },
            "performance": {
                "record_source": "reference-tracer.sqlite flattened scalar rows",
                "raw_neox_table_reparse": False,
                "sqlite_mode": "read-only",
            },
            "policy": {
                "identity": "Every hop requires exact scalar equality in the installed-game reference tracer and exact record provenance.",
                "discovery": "Reference-field selection only chooses which exact values to follow; it does not prove semantics.",
                "verification": "Multi-hop candidates remain research-only and cannot assign VERIFIED.",
                "publication": "No player-facing data is modified by this resolver.",
            },
            "weapons": rows,
        }
