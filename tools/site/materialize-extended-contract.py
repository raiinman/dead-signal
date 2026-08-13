#!/usr/bin/env python3
"""Materialize exact Miner compact contracts for Dead Signal static database routes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CATEGORIES = {
    "calibrations": ("dead-signal-calibrations", "calibrations.json", "DS_CALIBRATIONS_WEB", "database/calibrations/calibrations-data.js", "families"),
    "mods": ("dead-signal-mods", "mods.json", "DS_MODS_WEB", "database/mods/mods-data.js", "families"),
    "attachments": ("dead-signal-attachments", "attachments.json", "DS_ATTACHMENTS_WEB", "database/attachments/attachments-data.js", "attachments"),
    "deviations": ("dead-signal-deviations", "deviations.json", "DS_DEVIATIONS_WEB", "database/deviations/deviations-data.js", "families"),
    "cradles": ("dead-signal-cradles", "cradles.json", "DS_CRADLES_WEB", "database/cradles/cradles-data.js", "families"),
}


def resolve_source(path: Path, filename: str) -> Path:
    path = path.expanduser().resolve()
    if path.is_file():
        return path
    for candidate in (path / "web" / filename, path / filename):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Could not find {filename} under {path}")


def load_and_validate(path: Path, schema: str, collection: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != schema:
        raise ValueError(f"Expected schema {schema!r}, found {payload.get('schema')!r}")
    records = payload.get(collection)
    if not isinstance(records, list):
        raise ValueError(f"Compact contract must contain {collection!r} array")
    identity_key = "canonical_id"
    ids = [row.get(identity_key) for row in records if isinstance(row, dict)]
    if len(ids) != len(records) or any(not value for value in ids):
        raise ValueError(f"Every {collection} record must have canonical_id")
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate canonical IDs in {collection}")
    return payload


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def materialize(category: str, source_arg: Path, output_arg: Path | None = None) -> Path:
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category: {category}")
    schema, filename, variable, relative_output, collection = CATEGORIES[category]
    repository_root = Path(__file__).resolve().parents[2]
    source = resolve_source(source_arg, filename)
    payload = load_and_validate(source, schema, collection)
    output = output_arg.expanduser().resolve() if output_arg else repository_root / relative_output
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    output.write_text(
        "// Generated from Miner compact contract. Do not hand-edit.\n"
        f"// Source SHA-256: {file_sha(source)}\n"
        f"window.{variable}={encoded};\n",
        encoding="utf-8",
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Wrap one Miner compact category contract for the static site")
    parser.add_argument("category", choices=sorted(CATEGORIES))
    parser.add_argument("source", type=Path, help="Contract file, published/web/, or published/ directory")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    output = materialize(args.category, args.source, args.output)
    print(f"Materialized {args.category}: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
