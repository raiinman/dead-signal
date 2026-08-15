from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dead_signal_multihop_resolver import MultiHopResolver


def _write_table(root: Path, relative: str, data: dict) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"data": data}), encoding="utf-8")
    return path


def _build_catalog(output: Path, relative_paths: list[str], base: Path, current: Path) -> None:
    catalog = output / "catalogs" / "structured-tables.sqlite"
    catalog.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(catalog)
    connection.execute(
        "CREATE TABLE tables (relative_path TEXT PRIMARY KEY, base_json_path TEXT, current_json_path TEXT, "
        "base_records INTEGER, current_records INTEGER, base_bytes INTEGER, current_bytes INTEGER, layer_status TEXT NOT NULL)"
    )
    connection.execute(
        "CREATE TABLE domain_tables (domain TEXT NOT NULL, relative_path TEXT NOT NULL, PRIMARY KEY(domain,relative_path))"
    )
    for relative in relative_paths:
        base_path = base / relative
        current_path = current / relative
        connection.execute(
            "INSERT INTO tables VALUES (?,?,?,?,?,?,?,?)",
            (
                relative,
                str(base_path) if base_path.is_file() else None,
                str(current_path) if current_path.is_file() else None,
                1 if base_path.is_file() else 0,
                1 if current_path.is_file() else 0,
                base_path.stat().st_size if base_path.is_file() else 0,
                current_path.stat().st_size if current_path.is_file() else 0,
                "current-only" if current_path.is_file() and not base_path.is_file() else "both",
            ),
        )
    connection.commit()
    connection.close()


def _build_tracer(output: Path, occurrences: list[tuple[str, str, str, str, str, str]]) -> None:
    tracer = output / "published" / "indexes" / "reference-tracer.sqlite"
    tracer.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(tracer)
    connection.execute(
        "CREATE TABLE occurrences (value TEXT NOT NULL, layer TEXT NOT NULL, table_name TEXT NOT NULL, "
        "record_id TEXT NOT NULL, field TEXT NOT NULL, json_pointer TEXT NOT NULL)"
    )
    connection.executemany("INSERT INTO occurrences VALUES (?,?,?,?,?,?)", occurrences)
    connection.commit()
    connection.close()


def test_multihop_finds_text_only_after_exact_second_record(tmp_path: Path) -> None:
    output = tmp_path / "miner"
    base = output / "snapshots" / "base"
    current = output / "snapshots" / "current"
    output.mkdir(parents=True)
    (output / "last-run.json").write_text(
        json.dumps({"active_snapshots": {"base": str(base), "current": str(current)}}), encoding="utf-8"
    )

    first = "game_common/data/weapon_link_data.json"
    second = "game_common/data/weapon_display_data.json"
    _write_table(current, first, {"101": {"item_id": 101, "display_id": 9001}})
    _write_table(current, second, {"9001": {"display_id": 9001, "tooltip": "DESC_9001"}})
    translate = current / "translate" / "translate_data_en.json"
    translate.parent.mkdir(parents=True, exist_ok=True)
    translate.write_text(json.dumps({"DESC_9001": "A second-hop player-facing description."}), encoding="utf-8")

    _build_catalog(output, [first, second], base, current)
    _build_tracer(
        output,
        [
            ("101", "current", first, "101", "item_id", "/item_id"),
            ("9001", "current", first, "101", "display_id", "/display_id"),
            ("9001", "current", second, "9001", "display_id", "/display_id"),
            ("DESC_9001", "current", second, "9001", "tooltip", "/tooltip"),
        ],
    )

    resolver = MultiHopResolver(output)
    report = resolver.run({"weapons": [{"blueprint_id": 1, "item_id": 101, "name": "Test Weapon"}]})
    row = report["weapons"][0]
    assert row["candidate_count"] >= 1
    candidate = next(c for c in row["candidates"] if c["resolved_text"] == "A second-hop player-facing description.")
    assert candidate["hop_count"] >= 2
    assert candidate["publication_status"] == "research-only"
    assert candidate["reference_path"][0]["kind"] == "weapon-seed"
    assert any(hop.get("table") == second for hop in candidate["reference_path"])


def test_multihop_never_follows_untyped_generic_scalar(tmp_path: Path) -> None:
    output = tmp_path / "miner"
    base = output / "snapshots" / "base"
    current = output / "snapshots" / "current"
    output.mkdir(parents=True)
    (output / "last-run.json").write_text(
        json.dumps({"active_snapshots": {"base": str(base), "current": str(current)}}), encoding="utf-8"
    )

    first = "game_common/data/weapon_link_data.json"
    unrelated = "game_common/data/weapon_display_data.json"
    _write_table(current, first, {"101": {"item_id": 101, "amount": 77}})
    _write_table(current, unrelated, {"77": {"display_id": 77, "description": "Must not be reached through amount."}})
    _build_catalog(output, [first, unrelated], base, current)
    _build_tracer(
        output,
        [
            ("101", "current", first, "101", "item_id", "/item_id"),
            ("77", "current", first, "101", "amount", "/amount"),
            ("77", "current", unrelated, "77", "display_id", "/display_id"),
        ],
    )

    resolver = MultiHopResolver(output)
    report = resolver.run({"weapons": [{"blueprint_id": 1, "item_id": 101, "name": "Test Weapon"}]})
    assert report["weapons"][0]["candidate_count"] == 0
