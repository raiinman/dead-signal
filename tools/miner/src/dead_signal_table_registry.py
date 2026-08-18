"""Persistent structural registry for completed Dead Signal table snapshots.

The registry profiles JSON tables without assigning gameplay meaning.  Paths,
field shapes, and reference-looking names are discovery hints only; consumers
must still prove typed ownership before promoting player-facing semantics.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 2
REFERENCE_SUFFIXES = ("_id", "_no", "_code", "_list", "_lst", "_map")
TRANSLATION_TOKENS = ("translate", "translation", "localization", "locale", "text_key", "language")
PRESENTATION_TOKENS = ("name", "desc", "description", "display", "title", "label", "tip")
DOMAIN_RULES = {
    "Weapons": ("weapon", "gun_blueprint", "gun_base"),
    "Weapon UI": ("gun_preview", "weapon_preview", "weapon_ui"),
    "Weapon Preview": ("preview_accessory", "preview_model"),
    "Ballistics": ("bullet", "ballistic", "scatter", "falloff"),
    "Crosshair": ("crosshair",),
    "Attachments": ("accessory", "attachment"),
    "Equipment": ("equipment", "equip_"),
    "Armor": ("armor",),
    "Melee": ("melee",),
    "Crafting": ("craft", "recipe", "formula"),
    "Calibration": ("calibration", "affix"),
    "Cradle": ("cradle",),
    "Effects / Keywords": ("effect", "keyword", "buff", "passive_skill"),
    "Deviations": ("deviation",),
    "Seasons": ("season",),
    "Maps": ("map_", "big_map", "small_map"),
    "Items": ("item",),
    "Translation / presentation": ("translate", "localization", "description", "display"),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _namespace(relative_path: str) -> str:
    parts = relative_path.casefold().split("/")
    for name in ("game_common", "client_data"):
        if name in parts:
            return name
    return parts[0] if parts else "other"


def classify_domains(relative_path: str, fields: Iterable[str] = ()) -> list[str]:
    haystack = " ".join([relative_path, *fields]).casefold()
    tags = [domain for domain, tokens in DOMAIN_RULES.items() if any(token in haystack for token in tokens)]
    return tags or ["unknown"]


def _records(payload: Any) -> tuple[list[Any], str, list[str]]:
    if isinstance(payload, list):
        return payload, "list", []
    if not isinstance(payload, dict):
        return [payload], "scalar", []
    if not payload:
        return [], "empty-object", []
    for container in ("records", "data", "items", "rows"):
        value = payload.get(container)
        if isinstance(value, list):
            return value, f"object.{container}", []
        if isinstance(value, dict) and value and all(isinstance(row, dict) for row in value.values()):
            return list(value.values()), f"object.{container}-map", [str(key) for key in value.keys()]
    values = list(payload.values())
    object_values = sum(isinstance(value, dict) for value in values)
    if object_values >= max(1, len(values) // 2):
        return values, "keyed-object-map", [str(key) for key in payload.keys()]
    return [payload], "single-object", []


def _walk_shape(value: Any, path: str, shapes: Counter[tuple[str, str]]) -> None:
    kind = _json_type(value)
    shapes[(path or "$", kind)] += 1
    if isinstance(value, dict):
        for key, child in value.items():
            _walk_shape(child, f"{path}.{key}" if path else str(key), shapes)
    elif isinstance(value, list):
        for child in value[:50]:
            _walk_shape(child, f"{path}[]" if path else "[]", shapes)


def profile_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    fingerprint = hashlib.sha256(raw).hexdigest()
    payload = json.loads(raw.decode("utf-8-sig"))
    records, key_shape, map_keys = _records(payload)
    field_counts: Counter[str] = Counter()
    field_types: dict[str, Counter[str]] = defaultdict(Counter)
    null_counts: Counter[str] = Counter()
    shapes: Counter[tuple[str, str]] = Counter()
    object_records = 0
    for record in records:
        _walk_shape(record, "", shapes)
        if not isinstance(record, dict):
            continue
        object_records += 1
        for field, value in record.items():
            name = str(field)
            field_counts[name] += 1
            field_types[name][_json_type(value)] += 1
            if value is None:
                null_counts[name] += 1
    fields = []
    for name in sorted(field_counts, key=str.casefold):
        present = field_counts[name]
        fields.append({
            "name": name,
            "frequency": present,
            "types": dict(sorted(field_types[name].items())),
            "missing_rate": round((object_records - present) / object_records, 6) if object_records else 0.0,
            "null_rate": round(null_counts[name] / present, 6) if present else 0.0,
            "reference_kind": "dict" if name.casefold().endswith("_map") else "list" if name.casefold().endswith(("_list", "_lst")) else "scalar" if name.casefold().endswith(REFERENCE_SUFFIXES) else None,
            "translation_hint": any(token in name.casefold() for token in TRANSLATION_TOKENS),
            "presentation_hint": any(token in name.casefold() for token in PRESENTATION_TOKENS),
        })
    candidates = []
    for name in ("id", "no", "code", "record_id"):
        if field_counts.get(name) == object_records and object_records:
            candidates.append(name)
    if map_keys:
        candidates.insert(0, "$map_key")
    return {
        "fingerprint": fingerprint,
        "file_size": len(raw),
        "record_count": len(records),
        "key_shape": key_shape,
        "candidate_keys": candidates,
        "fields": fields,
        "nested_shapes": [
            {"path": shape_path, "value_type": kind, "observations": count}
            for (shape_path, kind), count in sorted(shapes.items())
        ],
    }


class TableRegistry:
    """Query and incrementally update the persistent table registry."""

    def __init__(self, database: Path | str):
        self.database = Path(database)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS registry_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tables (
                    layer TEXT NOT NULL, relative_path TEXT NOT NULL, namespace TEXT NOT NULL,
                    file_size INTEGER NOT NULL, sha256 TEXT NOT NULL, record_count INTEGER NOT NULL,
                    parser_source TEXT NOT NULL, key_shape TEXT NOT NULL, candidate_keys_json TEXT NOT NULL,
                    domains_json TEXT NOT NULL, profile_json TEXT NOT NULL, first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL, PRIMARY KEY (layer, relative_path)
                );
                CREATE INDEX IF NOT EXISTS idx_tables_path ON tables(relative_path);
                CREATE INDEX IF NOT EXISTS idx_tables_namespace ON tables(namespace);
            """)
            existing = connection.execute("SELECT value FROM registry_meta WHERE key='schema_version'").fetchone()
            if existing and existing[0] != str(SCHEMA_VERSION):
                connection.execute("DELETE FROM tables")
            connection.execute("INSERT OR REPLACE INTO registry_meta(key, value) VALUES('schema_version', ?)", (str(SCHEMA_VERSION),))

    def query_tables(self, *, layer: str | None = None, namespace: str | None = None) -> list[dict[str, Any]]:
        clauses, values = [], []
        if layer:
            clauses.append("layer = ?")
            values.append(layer)
        if namespace:
            clauses.append("namespace = ?")
            values.append(namespace)
        sql = "SELECT * FROM tables" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY layer, relative_path"
        with closing(self._connect()) as connection:
            return [dict(row) for row in connection.execute(sql, values)]

    def get_table(self, layer: str, relative_path: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT * FROM tables WHERE layer=? AND relative_path=?", (layer, relative_path)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["profile"] = json.loads(result.pop("profile_json"))
        result["domains"] = json.loads(result.pop("domains_json"))
        return result

    def query_effective_tables(self, *, namespace: str | None = None) -> list[dict[str, Any]]:
        """Return one row per path, with Current taking precedence over Base."""
        rows = self.query_tables(namespace=namespace)
        effective: dict[str, dict[str, Any]] = {}
        for row in rows:
            path = row["relative_path"]
            if path not in effective or row["layer"] == "current":
                effective[path] = row
        return [effective[path] for path in sorted(effective, key=str.casefold)]

    def update(self, layers: dict[str, Path], *, activity=None) -> dict[str, Any]:
        self.initialize()
        activity = activity or (lambda _message: None)
        started = time.perf_counter()
        stats = {"files_considered": 0, "files_changed": 0, "files_reused": 0, "tables_reprofiled": 0, "tables_reused": 0, "tables_removed": 0, "parse_failures": 0}
        now = _utc_now()
        with closing(self._connect()) as connection, connection:
            known = {(row["layer"], row["relative_path"]): dict(row) for row in connection.execute("SELECT * FROM tables")}
            seen: set[tuple[str, str]] = set()
            for layer in ("base", "current"):
                root = Path(layers[layer])
                files = sorted(root.rglob("*.json"), key=lambda item: item.as_posix().casefold())
                activity(f"Table Registry: {layer} layer has {len(files)} JSON tables")
                for path in files:
                    relative = path.relative_to(root).as_posix()
                    key = (layer, relative)
                    seen.add(key)
                    stats["files_considered"] += 1
                    raw = path.read_bytes()
                    fingerprint = hashlib.sha256(raw).hexdigest()
                    cached = known.get(key)
                    if cached and cached["sha256"] == fingerprint:
                        connection.execute("UPDATE tables SET last_seen=? WHERE layer=? AND relative_path=?", (now, layer, relative))
                        stats["files_reused"] += 1
                        stats["tables_reused"] += 1
                        continue
                    try:
                        profile = profile_json(path)
                    except (OSError, UnicodeError, json.JSONDecodeError) as error:
                        stats["parse_failures"] += 1
                        activity(f"Table Registry skipped invalid JSON: {layer}/{relative}: {type(error).__name__}")
                        continue
                    field_names = [field["name"] for field in profile["fields"]]
                    domains = classify_domains(relative, field_names)
                    first_seen = cached["first_seen"] if cached else now
                    connection.execute("""
                        INSERT OR REPLACE INTO tables
                        (layer, relative_path, namespace, file_size, sha256, record_count, parser_source,
                         key_shape, candidate_keys_json, domains_json, profile_json, first_seen, last_seen)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (layer, relative, _namespace(relative), profile["file_size"], profile["fingerprint"],
                          profile["record_count"], "structured-json", profile["key_shape"],
                          json.dumps(profile["candidate_keys"], sort_keys=True), json.dumps(domains, sort_keys=True),
                          json.dumps(profile, ensure_ascii=False, sort_keys=True), first_seen, now))
                    stats["files_changed"] += 1
                    stats["tables_reprofiled"] += 1
            for key in sorted(set(known) - seen):
                connection.execute("DELETE FROM tables WHERE layer=? AND relative_path=?", key)
                stats["tables_removed"] += 1
        stats["duration_seconds"] = round(time.perf_counter() - started, 6)
        return stats


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def build_client_data_census(registry: TableRegistry, reports: Path | str, stats: dict[str, Any]) -> dict[str, Any]:
    rows = registry.query_tables(namespace="client_data")
    layer_counts = Counter(row["layer"] for row in rows)
    path_layers: dict[str, set[str]] = defaultdict(set)
    domain_counts: Counter[str] = Counter()
    highlights = []
    for row in rows:
        path_layers[row["relative_path"]].add(row["layer"])
        profile = json.loads(row["profile_json"])
        domains = json.loads(row["domains_json"])
        domain_counts.update(domains)
        reference_fields = [field["name"] for field in profile["fields"] if field.get("reference_kind")]
        translation_fields = [field["name"] for field in profile["fields"] if field.get("translation_hint")]
        presentation_fields = [field["name"] for field in profile["fields"] if field.get("presentation_hint")]
        highlights.append({
            "layer": row["layer"], "path": row["relative_path"], "records": row["record_count"],
            "domains": domains, "reference_fields": reference_fields,
            "translation_fields": translation_fields, "presentation_fields": presentation_fields,
            "sha256": row["sha256"],
        })
    highlights.sort(key=lambda item: (-len(item["reference_fields"]), -item["records"], item["layer"], item["path"].casefold()))
    report = {
        "schema": "dead-signal-client-data-census", "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "record_counts": {
            "tables": len(rows), "distinct_paths": len(path_layers), "base_tables": layer_counts["base"],
            "current_tables": layer_counts["current"],
            "base_and_current_paths": sum(layers == {"base", "current"} for layers in path_layers.values()),
        },
        "domain_counts": dict(sorted(domain_counts.items())),
        "top_reference_bearing_tables": highlights[:100],
        "tables": sorted(highlights, key=lambda item: (item["layer"], item["path"].casefold())),
        "cache_statistics": stats,
        "policy": "Domain, presentation, translation, and reference classifications are structural hints only; they are not semantic proof.",
    }
    _atomic_json(Path(reports) / "client-data-census.json", report)
    return report


def run_table_registry(base: Path | str, current: Path | str, output: Path | str, reports: Path | str, *, activity=None) -> dict[str, Any]:
    database = Path(output) / "catalogs" / "dead-signal-table-registry.sqlite"
    registry = TableRegistry(database)
    stats = registry.update({"base": Path(base), "current": Path(current)}, activity=activity)
    rows = registry.query_tables()
    layer_counts = Counter(row["layer"] for row in rows)
    namespace_counts = Counter(row["namespace"] for row in rows)
    summary = {
        "schema": "dead-signal-table-registry-summary", "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(), "database": str(database),
        "record_counts": {"tables": len(rows), "base_tables": layer_counts["base"], "current_tables": layer_counts["current"]},
        "namespace_counts": dict(sorted(namespace_counts.items())), "cache_statistics": stats,
    }
    _atomic_json(Path(reports) / "table-registry-summary.json", summary)
    census = build_client_data_census(registry, reports, stats)
    return {"summary": summary, "client_data_census": census, "cache_statistics": stats, "database": str(database)}
