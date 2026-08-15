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


def _build_tracer(output: Path, occurrences: list[tuple[str, str, str, str, str, str]]) -> None:
    tracer = output / "published" / "indexes" / "reference-tracer.sqlite"
    tracer.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(tracer)
    connection.execute(
        "CREATE TABLE occurrences (value TEXT NOT NULL, layer TEXT NOT NULL, table_name TEXT NOT NULL, "
        "record_id TEXT NOT NULL, field TEXT NOT NULL, json_pointer TEXT NOT NULL)"
    )
    connection.execute("CREATE INDEX occurrence_value_idx ON occurrences(value)")
    connection.execute("CREATE INDEX occurrence_table_idx ON occurrences(table_name)")
    connection.executemany("INSERT INTO occurrences VALUES (?,?,?,?,?,?)", occurrences)
    connection.commit()
    connection.close()


def _snapshot(output: Path) -> tuple[Path, Path]:
    base = output / "snapshots" / "base"
    current = output / "snapshots" / "current"
    base.mkdir(parents=True, exist_ok=True)
    current.mkdir(parents=True, exist_ok=True)
    (output / "last-run.json").write_text(
        json.dumps({"active_snapshots": {"base": str(base), "current": str(current)}}),
        encoding="utf-8",
    )
    return base, current


def test_multihop_finds_text_only_after_exact_second_record(tmp_path: Path) -> None:
    output = tmp_path / "miner"
    output.mkdir(parents=True)
    _base, current = _snapshot(output)

    first = "game_common/data/weapon_link_data.json"
    second = "game_common/data/weapon_display_data.json"
    # Raw tables exist to model the completed snapshot, but the resolver must not
    # reopen them during traversal; all flattened record fields come from SQLite.
    _write_table(current, first, {"101": {"item_id": 101, "display_id": 9001}})
    _write_table(current, second, {"9001": {"display_id": 9001, "tooltip": "DESC_9001"}})
    translate = current / "translate" / "translate_data_en.json"
    translate.parent.mkdir(parents=True, exist_ok=True)
    translate.write_text(
        json.dumps({"DESC_9001": "A second-hop player-facing description."}), encoding="utf-8"
    )

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
    candidate = next(
        candidate
        for candidate in row["candidates"]
        if candidate["resolved_text"] == "A second-hop player-facing description."
    )
    assert candidate["hop_count"] >= 2
    assert candidate["publication_status"] == "research-only"
    assert candidate["reference_path"][0]["kind"] == "weapon-seed"
    assert any(hop.get("table") == second for hop in candidate["reference_path"])
    assert report["performance"]["record_source"] == "reference-tracer.sqlite flattened scalar rows"
    assert report["performance"]["raw_neox_table_reparse"] is False


def test_multihop_never_follows_untyped_generic_scalar(tmp_path: Path) -> None:
    output = tmp_path / "miner"
    output.mkdir(parents=True)
    _base, current = _snapshot(output)

    first = "game_common/data/weapon_link_data.json"
    unrelated = "game_common/data/weapon_display_data.json"
    _write_table(current, first, {"101": {"item_id": 101, "amount": 77}})
    _write_table(
        current,
        unrelated,
        {"77": {"display_id": 77, "description": "Must not be reached through amount."}},
    )
    _build_tracer(
        output,
        [
            ("101", "current", first, "101", "item_id", "/item_id"),
            ("77", "current", first, "101", "amount", "/amount"),
            ("77", "current", unrelated, "77", "display_id", "/display_id"),
            (
                "Must not be reached through amount.",
                "current",
                unrelated,
                "77",
                "description",
                "/description",
            ),
        ],
    )

    resolver = MultiHopResolver(output)
    report = resolver.run({"weapons": [{"blueprint_id": 1, "item_id": 101, "name": "Test Weapon"}]})
    assert report["weapons"][0]["candidate_count"] == 0
