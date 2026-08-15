"""FModel-inspired read-only explorer for Dead Signal's NeoX snapshots.

Once Human ships on NetEase's proprietary NeoX stack, not Unreal Engine, so the
Miner's equivalent of an archive/package browser should operate on the structured
NeoX tables we already extract.  This module deliberately does not publish or
normalize anything.  It exposes a bounded research API over the local snapshot:

- list every captured structured table and layer;
- open one exact table record;
- flatten its fields for UI inspection;
- search field names and scalar values inside one table;
- keep all paths inside the selected Miner output folder.

The explorer never executes game bytecode and never establishes fuzzy identity
relationships.  It is intended to back Research Console UI features.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
MAX_RECORDS = 500
MAX_FIELDS = 5000


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _safe_child(root: Path, candidate: Path | str, *, must_exist: bool = True) -> Path:
    root = root.expanduser().resolve()
    candidate = Path(candidate).expanduser().resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("Explorer paths must stay inside the selected Miner data folder") from error
    if must_exist and not candidate.exists():
        raise ValueError(f"Explorer input does not exist: {candidate}")
    if candidate.is_symlink():
        raise ValueError("Symbolic-link explorer inputs are not accepted")
    return candidate


def _walk(value: Any, pointer: str = "") -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            child_pointer = f"{pointer}/{escaped}"
            if isinstance(child, (dict, list)):
                yield from _walk(child, child_pointer)
            else:
                yield {
                    "json_pointer": child_pointer,
                    "field": str(key),
                    "value": child,
                    "value_type": type(child).__name__,
                }
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_pointer = f"{pointer}/{index}"
            if isinstance(child, (dict, list)):
                yield from _walk(child, child_pointer)
            else:
                yield {
                    "json_pointer": child_pointer,
                    "field": str(index),
                    "value": child,
                    "value_type": type(child).__name__,
                }


def _table_rows(path: Path) -> dict[str, Any]:
    payload = _read_json(path, {})
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data", payload)
    return data if isinstance(data, dict) else {}


class NeoXDataExplorer:
    """Read-only browser over one completed Dead Signal Miner output folder."""

    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        if not self.output.is_dir():
            raise ValueError("Select a Miner data folder containing last-run.json")
        self.last_run_path = _safe_child(self.output, self.output / "last-run.json")
        self.last_run = _read_json(self.last_run_path, {}) or {}
        active = self.last_run.get("active_snapshots") or {}
        self.base = _safe_child(self.output, Path(active.get("base") or ""))
        self.current = _safe_child(self.output, Path(active.get("current") or ""))
        self.catalog = _safe_child(
            self.output, self.output / "catalogs" / "structured-tables.sqlite"
        )

    def _catalog_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(f"file:{self.catalog.as_posix()}?mode=ro", uri=True)

    def list_tables(self, query: object = "", *, domain: str = "", limit: int = 500) -> dict[str, Any]:
        if limit < 1 or limit > 5000:
            raise ValueError("Table limit must be between 1 and 5000")
        needle = str(query or "").strip().casefold()
        wanted_domain = str(domain or "").strip()
        connection = self._catalog_connection()
        try:
            if wanted_domain:
                rows = connection.execute(
                    "SELECT t.relative_path,t.base_json_path,t.current_json_path,t.base_records,"
                    "t.current_records,t.layer_status FROM tables t "
                    "JOIN domain_tables d ON d.relative_path=t.relative_path "
                    "WHERE d.domain=? ORDER BY t.relative_path",
                    (wanted_domain,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT relative_path,base_json_path,current_json_path,base_records,"
                    "current_records,layer_status FROM tables ORDER BY relative_path"
                ).fetchall()
        finally:
            connection.close()

        results = []
        for relative, base_path, current_path, base_records, current_records, layer_status in rows:
            relative_text = str(relative)
            if needle and needle not in relative_text.casefold():
                continue
            results.append(
                {
                    "relative_path": relative_text,
                    "base_present": bool(base_path),
                    "current_present": bool(current_path),
                    "base_records": int(base_records or 0),
                    "current_records": int(current_records or 0),
                    "layer_status": layer_status,
                }
            )
            if len(results) >= limit:
                break
        return {
            "schema": "dead-signal-neox-table-list",
            "schema_version": SCHEMA_VERSION,
            "query": str(query or ""),
            "domain": wanted_domain,
            "result_count": len(results),
            "tables": results,
            "policy": "Read-only table inventory from the completed Miner structured-table catalog.",
        }

    def _resolve_table_path(self, relative_path: object, layer: str) -> Path:
        relative = Path(str(relative_path).replace("\\", "/"))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Table path must be a relative snapshot path")
        if layer not in {"base", "current"}:
            raise ValueError("Layer must be 'base' or 'current'")
        root = self.base if layer == "base" else self.current
        return _safe_child(self.output, root / relative)

    def table_summary(self, relative_path: object) -> dict[str, Any]:
        wanted = str(relative_path).replace("\\", "/")
        connection = self._catalog_connection()
        try:
            row = connection.execute(
                "SELECT relative_path,base_json_path,current_json_path,base_records,current_records,"
                "base_bytes,current_bytes,layer_status FROM tables WHERE relative_path=?",
                (wanted,),
            ).fetchone()
            if not row:
                raise ValueError(f"Unknown structured table: {wanted}")
            domains = [
                value[0]
                for value in connection.execute(
                    "SELECT domain FROM domain_tables WHERE relative_path=? ORDER BY domain", (wanted,)
                ).fetchall()
            ]
        finally:
            connection.close()
        return {
            "relative_path": row[0],
            "base_present": bool(row[1]),
            "current_present": bool(row[2]),
            "base_records": int(row[3] or 0),
            "current_records": int(row[4] or 0),
            "base_bytes": int(row[5] or 0),
            "current_bytes": int(row[6] or 0),
            "layer_status": row[7],
            "domains": domains,
        }

    def list_records(self, relative_path: object, *, layer: str = "current", query: object = "",
                     limit: int = 250) -> dict[str, Any]:
        if limit < 1 or limit > MAX_RECORDS:
            raise ValueError(f"Record limit must be between 1 and {MAX_RECORDS}")
        path = self._resolve_table_path(relative_path, layer)
        rows = _table_rows(path)
        needle = str(query or "").strip().casefold()
        results = []
        for record_id, record in rows.items():
            if needle:
                haystack = f"{record_id} {json.dumps(record, ensure_ascii=False)}".casefold()
                if needle not in haystack:
                    continue
            results.append(
                {
                    "record_id": str(record_id),
                    "record_type": type(record).__name__,
                    "preview": json.dumps(record, ensure_ascii=False, separators=(",", ":"))[:500],
                }
            )
            if len(results) >= limit:
                break
        return {
            "schema": "dead-signal-neox-record-list",
            "schema_version": SCHEMA_VERSION,
            "table": str(relative_path).replace("\\", "/"),
            "layer": layer,
            "query": str(query or ""),
            "total_records": len(rows),
            "result_count": len(results),
            "records": results,
        }

    def record(self, relative_path: object, record_id: object, *, layer: str = "current") -> dict[str, Any]:
        path = self._resolve_table_path(relative_path, layer)
        rows = _table_rows(path)
        wanted = str(record_id)
        if wanted not in rows:
            raise ValueError(f"Record {wanted!r} is not present in {relative_path} ({layer})")
        value = rows[wanted]
        fields = list(_walk(value))
        if len(fields) > MAX_FIELDS:
            fields = fields[:MAX_FIELDS]
        return {
            "schema": "dead-signal-neox-record",
            "schema_version": SCHEMA_VERSION,
            "table": str(relative_path).replace("\\", "/"),
            "layer": layer,
            "record_id": wanted,
            "field_count": len(fields),
            "fields_truncated": len(list(_walk(value))) > MAX_FIELDS,
            "fields": fields,
            "raw": value,
            "policy": "Exact record identity from one extracted NeoX table; no inference or fuzzy joins.",
        }

    def search_record_fields(self, relative_path: object, *, layer: str = "current",
                             query: object, limit: int = 500) -> dict[str, Any]:
        if limit < 1 or limit > MAX_FIELDS:
            raise ValueError(f"Field limit must be between 1 and {MAX_FIELDS}")
        needle = str(query or "").strip().casefold()
        if not needle:
            raise ValueError("Enter a field name or scalar value to search")
        path = self._resolve_table_path(relative_path, layer)
        matches = []
        for record_id, record in _table_rows(path).items():
            for field in _walk(record):
                value = field.get("value")
                if needle in field["field"].casefold() or needle in str(value).casefold():
                    matches.append({"record_id": str(record_id), **field})
                    if len(matches) >= limit:
                        break
            if len(matches) >= limit:
                break
        return {
            "schema": "dead-signal-neox-field-search",
            "schema_version": SCHEMA_VERSION,
            "table": str(relative_path).replace("\\", "/"),
            "layer": layer,
            "query": str(query),
            "result_count": len(matches),
            "results": matches,
            "identity_policy": "Substring search is discovery-only and never establishes an identity relationship.",
        }
