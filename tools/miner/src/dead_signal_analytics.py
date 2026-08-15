"""Dead Signal embedded analytics engine.

DuckDB, Polars, and Arrow are implementation details beneath the branded Data
Intelligence workspace.  This module builds a local analytical warehouse from
research-only reports and exact-reference occurrences.  It never replaces the
SQLite reference tracer as identity authority and never publishes game data.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
SAFE_QUERY = re.compile(r"^\s*(?:select|with|describe|show|explain)\b", re.IGNORECASE)


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _safe_child(root: Path, candidate: Path | str, *, must_exist: bool = False) -> Path:
    root = root.expanduser().resolve()
    path = Path(candidate).expanduser().resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError("Analytics paths must stay inside the selected Miner data folder") from error
    if must_exist and not path.exists():
        raise ValueError(f"Analytics input does not exist: {path}")
    if path.exists() and path.is_symlink():
        raise ValueError("Symbolic-link analytics inputs are not accepted")
    return path


def dependency_status() -> dict[str, Any]:
    status = {}
    for name in ("duckdb", "polars", "pyarrow"):
        try:
            module = __import__(name)
            status[name] = {"available": True, "version": str(getattr(module, "__version__", "unknown"))}
        except Exception as error:  # pragma: no cover - packaging diagnostic
            status[name] = {"available": False, "error": f"{type(error).__name__}: {error}"}
    return status


def flatten_source_finder(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for weapon in payload.get("weapons") or []:
        if not isinstance(weapon, dict):
            continue
        candidates = weapon.get("candidates") or []
        if not candidates:
            rows.append({
                "blueprint_id": str(weapon.get("blueprint_id") or ""),
                "item_id": str(weapon.get("item_id") or ""),
                "weapon": str(weapon.get("name") or ""),
                "category": str(weapon.get("category") or ""),
                "weapon_state": str(weapon.get("state") or "UNRESOLVED"),
                "candidate_state": "UNRESOLVED",
                "score": 0,
                "table_name": "",
                "record_id": "",
                "field": "",
                "text": "",
                "shared": False,
                "owner_count": 0,
                "blockers": "no-candidates",
            })
            continue
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            rows.append({
                "blueprint_id": str(weapon.get("blueprint_id") or ""),
                "item_id": str(weapon.get("item_id") or ""),
                "weapon": str(weapon.get("name") or ""),
                "category": str(weapon.get("category") or ""),
                "weapon_state": str(weapon.get("state") or "UNRESOLVED"),
                "candidate_state": str(candidate.get("state") or "UNRESOLVED"),
                "score": int(candidate.get("score") or 0),
                "table_name": str(candidate.get("table") or ""),
                "record_id": str(candidate.get("record_id") or ""),
                "field": str(candidate.get("field") or ""),
                "text": str(candidate.get("text") or ""),
                "shared": bool(candidate.get("shared_across_weapons")),
                "owner_count": int(candidate.get("weapon_owner_count") or 0),
                "blockers": ",".join(str(value) for value in candidate.get("blockers") or []),
            })
    return rows


def flatten_table_profiles(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tables: list[dict[str, Any]] = []
    fields: list[dict[str, Any]] = []
    profiles = payload.get("profiles") if isinstance(payload, dict) else None
    if not isinstance(profiles, list):
        profiles = payload.get("tables") if isinstance(payload, dict) else []
    for profile in profiles or []:
        if not isinstance(profile, dict):
            continue
        table = str(profile.get("table") or "")
        layer = str(profile.get("layer") or "")
        tables.append({
            "table_name": table,
            "layer": layer,
            "record_count": int(profile.get("record_count") or 0),
            "field_count": int(profile.get("field_count") or 0),
            "record_shape_count": int(profile.get("record_shape_count") or 0),
            "description_shared_warnings": int((profile.get("warnings") or {}).get("description_like_shared_values") or 0),
            "rare_field_count": int((profile.get("warnings") or {}).get("rare_field_count") or 0),
        })
        for field in profile.get("fields") or []:
            if not isinstance(field, dict):
                continue
            fields.append({
                "table_name": table,
                "layer": layer,
                "field": str(field.get("field") or ""),
                "coverage": float(field.get("coverage") or 0.0),
                "present_records": int(field.get("present_records") or 0),
                "missing_records": int(field.get("missing_records") or 0),
                "unique_scalar_values": int(field.get("unique_scalar_values") or 0),
                "repeated_scalar_values": int(field.get("repeated_scalar_values") or 0),
                "identity_like": bool(field.get("identity_like")),
                "description_like": bool(field.get("description_like")),
            })
    return tables, fields


class DeadSignalAnalytics:
    """Build and query one local Dead Signal analytical warehouse."""

    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        if not self.output.is_dir():
            raise ValueError("Select a completed Dead Signal Miner data folder")
        self.database = _safe_child(self.output, self.output / "catalogs" / "dead-signal-analytics.duckdb")
        self.published = _safe_child(self.output, self.output / "published", must_exist=True)
        self.reports = _safe_child(self.output, self.published / "reports", must_exist=True)
        self.tracer = _safe_child(self.output, self.published / "indexes" / "reference-tracer.sqlite")

    @staticmethod
    def _modules():
        import duckdb  # type: ignore
        import polars as pl  # type: ignore
        import pyarrow as pa  # type: ignore
        return duckdb, pl, pa

    def _reference_rows(self, limit: int = 2_000_000) -> Iterable[tuple[str, str, str, str, str, str]]:
        if not self.tracer.is_file():
            return []
        uri = f"file:{self.tracer.as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        try:
            cursor = connection.execute(
                "SELECT value,layer,table_name,record_id,field,json_pointer FROM occurrences LIMIT ?",
                (limit,),
            )
            return cursor.fetchall()
        finally:
            connection.close()

    def build(self) -> dict[str, Any]:
        duckdb, pl, _pa = self._modules()
        source_payload = _read_json(self.reports / "dead-signal-source-finder.json", {}) or {}
        profile_payload = _read_json(self.reports / "dead-signal-table-profiles.json", {}) or {}
        source_rows = flatten_source_finder(source_payload)
        table_rows, field_rows = flatten_table_profiles(profile_payload)
        reference_rows = list(self._reference_rows())

        self.database.parent.mkdir(parents=True, exist_ok=True)
        connection = duckdb.connect(str(self.database))
        try:
            for name in ("source_finder", "table_profiles", "field_profiles", "exact_references"):
                connection.execute(f"DROP TABLE IF EXISTS {name}")

            datasets = {
                "source_finder": source_rows,
                "table_profiles": table_rows,
                "field_profiles": field_rows,
            }
            for name, rows in datasets.items():
                if rows:
                    frame = pl.DataFrame(rows)
                    connection.register(f"_{name}", frame.to_arrow())
                    connection.execute(f"CREATE TABLE {name} AS SELECT * FROM _{name}")
                    connection.unregister(f"_{name}")
                else:
                    connection.execute(f"CREATE TABLE {name} AS SELECT NULL::VARCHAR AS empty WHERE FALSE")

            if reference_rows:
                frame = pl.DataFrame(
                    reference_rows,
                    schema=["value", "layer", "table_name", "record_id", "field", "json_pointer"],
                    orient="row",
                )
                connection.register("_exact_references", frame.to_arrow())
                connection.execute("CREATE TABLE exact_references AS SELECT * FROM _exact_references")
                connection.unregister("_exact_references")
            else:
                connection.execute(
                    "CREATE TABLE exact_references(value VARCHAR,layer VARCHAR,table_name VARCHAR,record_id VARCHAR,field VARCHAR,json_pointer VARCHAR)"
                )
            connection.execute("CREATE INDEX IF NOT EXISTS exact_reference_value_idx ON exact_references(value)")
        finally:
            connection.close()

        return {
            "schema": "dead-signal-analytics-build",
            "schema_version": SCHEMA_VERSION,
            "brand": "Dead Signal",
            "database": str(self.database),
            "rows": {
                "source_finder": len(source_rows),
                "table_profiles": len(table_rows),
                "field_profiles": len(field_rows),
                "exact_references": len(reference_rows),
            },
            "dependencies": dependency_status(),
            "authority_policy": "Analytics can rank and aggregate research evidence; exact-reference SQLite remains identity authority.",
            "publication_policy": "The analytics warehouse has no publication write path.",
        }

    def query(self, sql: str, *, limit: int = 1000) -> dict[str, Any]:
        if limit < 1 or limit > 10000:
            raise ValueError("Analytics row limit must be between 1 and 10000")
        statement = str(sql or "").strip().rstrip(";")
        if not SAFE_QUERY.match(statement):
            raise ValueError("Data Intelligence accepts read-only SELECT/WITH/DESCRIBE/SHOW/EXPLAIN queries only")
        if not self.database.is_file():
            self.build()
        duckdb, _pl, _pa = self._modules()
        connection = duckdb.connect(str(self.database), read_only=True)
        try:
            relation = connection.sql(f"SELECT * FROM ({statement}) AS ds_query LIMIT {int(limit)}") if statement.casefold().startswith(("select", "with")) else connection.sql(statement)
            arrow = relation.arrow()
            columns = list(arrow.schema.names)
            rows = arrow.to_pylist()[:limit]
        finally:
            connection.close()
        return {
            "schema": "dead-signal-analytics-query",
            "schema_version": SCHEMA_VERSION,
            "query": statement,
            "columns": columns,
            "row_count": len(rows),
            "rows": rows,
            "policy": "Read-only analytical result; query output never establishes identity or publication eligibility.",
        }

    def description_leads(self, *, limit: int = 250) -> dict[str, Any]:
        return self.query(
            "SELECT weapon, category, candidate_state, score, table_name, record_id, field, text, shared, owner_count, blockers "
            "FROM source_finder ORDER BY (candidate_state='CANDIDATE') DESC, score DESC, weapon",
            limit=limit,
        )

    def suspicious_description_fields(self, *, limit: int = 250) -> dict[str, Any]:
        return self.query(
            "SELECT table_name, layer, field, coverage, unique_scalar_values, repeated_scalar_values "
            "FROM field_profiles WHERE description_like = TRUE "
            "ORDER BY repeated_scalar_values DESC, coverage DESC",
            limit=limit,
        )
