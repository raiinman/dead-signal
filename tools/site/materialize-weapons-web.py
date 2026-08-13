#!/usr/bin/env python3
"""Materialize the Miner's compact public Weapons JSON for the static website.

This tool does not normalize or reinterpret game data. It validates the public
contract and wraps the exact JSON payload in a browser assignment so the
prepared static site can consume the Miner's published/web/weapons.json output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_SCHEMA = "dead-signal-weapons"


def resolve_source(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.is_file():
        return path
    if path.is_dir():
        for candidate in (path / "web" / "weapons.json", path / "weapons.json"):
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(f"Could not find published Weapons JSON under: {path}")


def load_and_validate(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Published Weapons payload must be a JSON object")
    if payload.get("schema") != EXPECTED_SCHEMA:
        raise ValueError(f"Expected schema {EXPECTED_SCHEMA!r}, found {payload.get('schema')!r}")
    records = payload.get("weapons")
    if not isinstance(records, list) or not records:
        raise ValueError("Published Weapons payload contains no weapon records")

    ids = [record.get("canonical_id") for record in records if isinstance(record, dict)]
    if len(ids) != len(records) or any(not value for value in ids):
        raise ValueError("Every published weapon must have a canonical_id")
    if len(ids) != len(set(ids)):
        raise ValueError("Published Weapons payload contains duplicate canonical_id values")

    declared = (payload.get("record_counts") or {}).get("weapons")
    if declared is not None and int(declared) != len(records):
        raise ValueError(f"record_counts.weapons={declared} but payload contains {len(records)} records")
    return payload


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_browser_payload(source: Path, output: Path, payload: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    header = (
        "// Generated from Miner published/web/weapons.json. Do not hand-edit.\n"
        f"// Source generated_utc: {payload.get('generated_utc') or 'unknown'}\n"
        f"// Source SHA-256: {sha256(source)}\n"
    )
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(f"{header}window.DS_WEAPONS_WEB={encoded};\n", encoding="utf-8")
    temporary.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wrap a Miner published/web/weapons.json contract for the Dead Signal static site"
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Path to weapons.json, published/web/, or the Miner published/ directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JS path (default: repository database/weapons/weapons-data.js)",
    )
    args = parser.parse_args()

    repository_root = Path(__file__).resolve().parents[2]
    source = resolve_source(args.source)
    output = (args.output.expanduser().resolve() if args.output else repository_root / "database" / "weapons" / "weapons-data.js")
    payload = load_and_validate(source)
    write_browser_payload(source, output, payload)
    print(f"Materialized {len(payload['weapons'])} weapons: {source} -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
