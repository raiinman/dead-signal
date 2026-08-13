#!/usr/bin/env python3
"""Materialize the Miner's compact public Armor JSON for the static website.

This wrapper preserves the exact published/web/armor.json payload. It validates
public canonical identity before creating the browser assignment and does not
reinterpret Armor mechanics or set semantics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA = "dead-signal-armor"


def resolve_source(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.is_file():
        return path
    if path.is_dir():
        for candidate in (path / "web" / "armor.json", path / "armor.json"):
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(f"Could not find published Armor JSON under: {path}")


def load_and_validate(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != EXPECTED_SCHEMA:
        raise ValueError(f"Expected schema {EXPECTED_SCHEMA!r}, found {payload.get('schema')!r}")
    sets = payload.get("armor_sets")
    key_armor = payload.get("key_armor")
    if not isinstance(sets, list) or not isinstance(key_armor, list):
        raise ValueError("Armor contract must contain armor_sets and key_armor arrays")
    pieces = [piece for armor_set in sets if isinstance(armor_set, dict) for piece in armor_set.get("pieces", []) if isinstance(piece, dict)] + [piece for piece in key_armor if isinstance(piece, dict)]
    ids = [piece.get("canonical_id") for piece in pieces]
    if any(not value for value in ids):
        raise ValueError("Every public Armor piece must have a canonical_id")
    if len(ids) != len(set(ids)):
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        raise ValueError(f"Armor contract contains duplicate canonical IDs: {duplicates}")
    set_ids = [row.get("canonical_id") for row in sets if isinstance(row, dict)]
    if any(not value for value in set_ids) or len(set_ids) != len(set(set_ids)):
        raise ValueError("Armor Sets must have unique canonical_id values")
    declared = payload.get("record_counts") or {}
    if declared.get("armor_sets") is not None and int(declared["armor_sets"]) != len(sets):
        raise ValueError("record_counts.armor_sets does not match armor_sets array")
    if declared.get("armor_pieces") is not None and int(declared["armor_pieces"]) != len(pieces):
        raise ValueError("record_counts.armor_pieces does not match published pieces")
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
        "// Generated from Miner published/web/armor.json. Do not hand-edit.\n"
        f"// Source generated_utc: {payload.get('generated_utc') or 'unknown'}\n"
        f"// Source SHA-256: {sha256(source)}\n"
    )
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(f"{header}window.DS_ARMOR_WEB={encoded};\n", encoding="utf-8")
    temporary.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Wrap Miner published/web/armor.json for Dead Signal")
    parser.add_argument("source", type=Path, help="armor.json, published/web/, or published/ directory")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    repository_root = Path(__file__).resolve().parents[2]
    source = resolve_source(args.source)
    output = args.output.expanduser().resolve() if args.output else repository_root / "database" / "armor" / "armor-data.js"
    payload = load_and_validate(source)
    write_browser_payload(source, output, payload)
    print(f"Materialized {len(payload['armor_sets'])} Armor Sets: {source} -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
