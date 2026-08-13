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
EXPECTED_SCHEMA_VERSION = 1


def resolve_source(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.is_file():
        return path
    if path.is_dir():
        for candidate in (path / "web" / "armor.json", path / "armor.json"):
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(f"Could not find published Armor JSON under: {path}")


def _required_id(value: Any, label: str) -> str:
    if value is None or value == "":
        raise ValueError(f"{label} is required")
    return str(value)


def load_and_validate(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != EXPECTED_SCHEMA:
        found = payload.get("schema") if isinstance(payload, dict) else None
        raise ValueError(f"Expected schema {EXPECTED_SCHEMA!r}, found {found!r}")
    if payload.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        raise ValueError(
            f"Expected schema_version {EXPECTED_SCHEMA_VERSION}, found {payload.get('schema_version')!r}"
        )

    sets = payload.get("armor_sets")
    key_armor = payload.get("key_armor")
    if not isinstance(sets, list) or not isinstance(key_armor, list):
        raise ValueError("Armor contract must contain armor_sets and key_armor arrays")
    if any(not isinstance(row, dict) for row in sets) or any(not isinstance(row, dict) for row in key_armor):
        raise ValueError("Every Armor Set and Key Armor record must be a JSON object")

    set_ids: list[str] = []
    pieces: list[dict[str, Any]] = []
    set_piece_count = 0
    for armor_set in sets:
        suit_id = _required_id(armor_set.get("suit_id"), "Armor Set suit_id")
        expected_set_id = f"ds-as-{suit_id}"
        canonical_set_id = _required_id(armor_set.get("canonical_id"), f"Armor Set {suit_id} canonical_id")
        if canonical_set_id != expected_set_id:
            raise ValueError(
                f"Armor Set {suit_id} canonical_id {canonical_set_id!r} does not match {expected_set_id!r}"
            )
        if not str(armor_set.get("name") or "").strip():
            raise ValueError(f"Armor Set {canonical_set_id} is missing a player-facing name")
        set_ids.append(canonical_set_id)

        set_pieces = armor_set.get("pieces")
        if not isinstance(set_pieces, list):
            raise ValueError(f"Armor Set {canonical_set_id} must contain a pieces array")
        if any(not isinstance(piece, dict) for piece in set_pieces):
            raise ValueError(f"Armor Set {canonical_set_id} contains a non-object piece record")
        for piece in set_pieces:
            piece_suit_id = _required_id(piece.get("suit_id"), f"Armor piece in {canonical_set_id} suit_id")
            blueprint_id = _required_id(piece.get("blueprint_id"), f"Armor piece in {canonical_set_id} blueprint_id")
            if piece_suit_id != suit_id:
                raise ValueError(
                    f"Armor piece blueprint {blueprint_id} suit_id {piece_suit_id!r} does not match parent suit_id {suit_id!r}"
                )
            expected_piece_id = f"ds-a-{suit_id}-{blueprint_id}"
            canonical_piece_id = _required_id(piece.get("canonical_id"), f"Armor piece {blueprint_id} canonical_id")
            if canonical_piece_id != expected_piece_id:
                raise ValueError(
                    f"Armor piece {canonical_piece_id!r} does not match variant-aware identity {expected_piece_id!r}"
                )
            if not str(piece.get("name") or "").strip():
                raise ValueError(f"Armor piece {canonical_piece_id} is missing a player-facing name")
            pieces.append(piece)
            set_piece_count += 1

    for piece in key_armor:
        blueprint_id = _required_id(piece.get("blueprint_id"), "Key Armor blueprint_id")
        expected_piece_id = f"ds-ka-{blueprint_id}"
        canonical_piece_id = _required_id(piece.get("canonical_id"), f"Key Armor {blueprint_id} canonical_id")
        if canonical_piece_id != expected_piece_id:
            raise ValueError(
                f"Key Armor {canonical_piece_id!r} does not match identity {expected_piece_id!r}"
            )
        if not str(piece.get("name") or "").strip():
            raise ValueError(f"Key Armor {canonical_piece_id} is missing a player-facing name")
        pieces.append(piece)

    if len(set_ids) != len(set(set_ids)):
        raise ValueError("Armor Sets must have unique canonical_id values")
    ids = [str(piece.get("canonical_id")) for piece in pieces]
    if len(ids) != len(set(ids)):
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        raise ValueError(f"Armor contract contains duplicate canonical IDs: {duplicates}")

    declared = payload.get("record_counts") or {}
    expected_counts = {
        "armor_sets": len(sets),
        "set_pieces": set_piece_count,
        "key_armor": len(key_armor),
        "armor_pieces": len(pieces),
    }
    for key, actual in expected_counts.items():
        if declared.get(key) is not None and int(declared[key]) != actual:
            raise ValueError(f"record_counts.{key}={declared[key]} but payload contains {actual}")
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
