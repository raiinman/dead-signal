"""Portable read-only export of every structured NeoX table captured by the Miner.

The exporter copies exact structured-table JSON bytes from the active base/current
snapshots into one ZIP plus a manifest. It never executes game bytecode, never
normalizes records, and never publishes the bundle. The output is a local research
artifact intended for manual inspection and handoff.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import zipfile

from neox_data_explorer import NeoXDataExplorer


SCHEMA_VERSION = 1


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _catalog_rows(explorer: NeoXDataExplorer) -> list[tuple]:
    connection = sqlite3.connect(f"file:{explorer.catalog.as_posix()}?mode=ro", uri=True)
    try:
        return connection.execute(
            "SELECT relative_path,base_json_path,current_json_path,base_records,current_records,"
            "base_bytes,current_bytes,layer_status FROM tables ORDER BY relative_path"
        ).fetchall()
    finally:
        connection.close()


def export_all_neox_tables(
    explorer: NeoXDataExplorer,
    destination: Path | str | None = None,
    *,
    activity=None,
) -> dict:
    """Export every catalogued base/current NeoX table into one portable ZIP.

    Source files are copied byte-for-byte. The manifest records per-layer hashes,
    byte sizes, record counts, and any catalog entry whose expected file was not
    available. The source snapshots and catalog remain read-only.
    """
    rows = _catalog_rows(explorer)
    if destination is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
        destination = explorer.output / "research" / f"neox-all-tables-{stamp}.zip"
    destination = Path(destination).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_suffix(destination.suffix + ".tmp")
    if temp_path.exists():
        temp_path.unlink()

    entries = []
    missing = []
    exported_files = 0
    exported_bytes = 0

    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            total = len(rows)
            for index, row in enumerate(rows, 1):
                (
                    relative_path,
                    base_json_path,
                    current_json_path,
                    base_records,
                    current_records,
                    base_bytes,
                    current_bytes,
                    layer_status,
                ) = row
                relative = str(relative_path).replace("\\", "/")
                table_entry = {
                    "relative_path": relative,
                    "layer_status": layer_status,
                    "layers": {},
                }
                for layer, catalog_path, records, catalog_bytes in (
                    ("base", base_json_path, base_records, base_bytes),
                    ("current", current_json_path, current_records, current_bytes),
                ):
                    if not catalog_path:
                        continue
                    source = explorer._resolve_table_path(relative, layer)
                    if not source.is_file():
                        missing.append({"relative_path": relative, "layer": layer})
                        continue
                    arcname = f"{layer}/{relative}"
                    archive.write(source, arcname=arcname)
                    size = source.stat().st_size
                    table_entry["layers"][layer] = {
                        "archive_path": arcname,
                        "records": int(records or 0),
                        "bytes": size,
                        "catalog_bytes": int(catalog_bytes or 0),
                        "sha256": _sha256(source),
                    }
                    exported_files += 1
                    exported_bytes += size
                entries.append(table_entry)
                if activity and (index == 1 or index == total or index % 100 == 0):
                    activity(f"Exporting NeoX tables {index}/{total}: {relative}")

            manifest = {
                "schema": "dead-signal-neox-all-tables-export",
                "schema_version": SCHEMA_VERSION,
                "brand": "Dead Signal",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "mode": "offline-read-only-exact-table-export",
                "record_counts": {
                    "catalog_tables": len(rows),
                    "exported_table_files": exported_files,
                    "exported_source_bytes": exported_bytes,
                    "missing_expected_files": len(missing),
                },
                "tables": entries,
                "missing_expected_files": missing,
                "policy": {
                    "source": "Exact structured NeoX table JSON bytes from the active Miner base/current snapshots.",
                    "execution": "No game module or game bytecode is imported or executed.",
                    "publication": "Research export only; no player-facing data is published or normalized.",
                },
            }
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        temp_path.replace(destination)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

    return {
        "schema": "dead-signal-neox-all-tables-export-result",
        "schema_version": SCHEMA_VERSION,
        "path": str(destination),
        "archive_bytes": destination.stat().st_size,
        "catalog_tables": len(rows),
        "exported_table_files": exported_files,
        "exported_source_bytes": exported_bytes,
        "missing_expected_files": len(missing),
        "policy": "Read-only research export; source snapshots are never modified.",
    }
