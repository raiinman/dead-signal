from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "src"
EXTRACTOR = ROOT / "extractor"
for candidate in (ROOT, EXTRACTOR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

spec = importlib.util.spec_from_file_location("dead_signal_research_suite", ROOT / "dead_signal_research_suite.py")
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def write_table(root: Path, relative: str, data: dict) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"data": data}), encoding="utf-8")
    return path


def write_research_indexes(output: Path, base: Path, current: Path, relative: str) -> None:
    (output / "last-run.json").write_text(
        json.dumps({"active_snapshots": {"base": str(base), "current": str(current)}}), encoding="utf-8"
    )
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
    current_path = current / relative
    connection.execute(
        "INSERT INTO tables VALUES (?,?,?,?,?,?,?,?)",
        (relative, None, str(current_path), 0, 1, 0, current_path.stat().st_size, "current-only"),
    )
    connection.commit()
    connection.close()

    tracer = output / "published" / "indexes" / "reference-tracer.sqlite"
    tracer.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(tracer)
    connection.execute(
        "CREATE TABLE occurrences (value TEXT NOT NULL, layer TEXT NOT NULL, table_name TEXT NOT NULL, "
        "record_id TEXT NOT NULL, field TEXT NOT NULL, json_pointer TEXT NOT NULL)"
    )
    connection.executemany(
        "INSERT INTO occurrences VALUES (?,?,?,?,?,?)",
        [
            ("7001", "current", relative, "7001", "item_id", "/item_id"),
            ("weapon_desc_7001", "current", relative, "7001", "tooltip", "/tooltip"),
        ],
    )
    connection.commit()
    connection.close()


def test_research_suite_writes_non_publishing_reports(tmp_path: Path) -> None:
    base = tmp_path / "base"
    current = tmp_path / "current"
    reports = tmp_path / "published" / "reports"
    relative = "game_common/data/item_display_data.json"

    write_table(
        current,
        relative,
        {
            "7001": {
                "item_id": 7001,
                "tooltip": "weapon_desc_7001",
            }
        },
    )
    translate = current / "translate" / "translate_data_en.json"
    translate.parent.mkdir(parents=True, exist_ok=True)
    translate.write_text(json.dumps({"weapon_desc_7001": "A precise test weapon."}), encoding="utf-8")
    write_research_indexes(tmp_path, base, current, relative)

    weapons_path = tmp_path / "weapons.json"
    weapons_path.write_text(
        json.dumps(
            {
                "weapons": [
                    {
                        "blueprint_id": 1001,
                        "item_id": 7001,
                        "name": "Test Weapon",
                        "category": "Rifle",
                        "short_description_evidence": {},
                        "effect_resolution": {},
                        "tiers": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    manifest = module.run_research_suite(base, current, weapons_path, reports)

    assert manifest["schema"] == "dead-signal-research-suite"
    assert "No value is promoted" in manifest["publication_policy"]
    for filename in (
        "weapon-description-identity-investigation.json",
        "weapon-description-source-investigation.json",
        "weapon-description-multihop.json",
        "weapon-description-combined-investigation.json",
        "dead-signal-source-finder.json",
        "dead-signal-table-profiles.json",
        "dead-signal-research-suite.json",
    ):
        assert (reports / filename).is_file()

    source_finder = json.loads((reports / "dead-signal-source-finder.json").read_text(encoding="utf-8"))
    assert source_finder["weapons"][0]["publication_status"] == "BLOCKED-PENDING-VERIFICATION"
    assert source_finder["weapons"][0]["state"] == "CANDIDATE"

    multihop = json.loads((reports / "weapon-description-multihop.json").read_text(encoding="utf-8"))
    assert multihop["record_counts"]["candidate_rows"] >= 1

    profiles = json.loads((reports / "dead-signal-table-profiles.json").read_text(encoding="utf-8"))
    assert profiles["record_counts"]["profiled_tables"] == 1
    active = profiles["tables"][0]["active_profile"]
    assert any(row["field"] == "tooltip" for row in active["description_like_fields"])


def test_profile_path_priority_favors_description_and_weapon_tables(tmp_path: Path) -> None:
    base = tmp_path / "base"
    current = tmp_path / "current"
    write_table(base, "client_data/item_misc_data.json", {"1": {"item_id": 1}})
    write_table(base, "game_common/data/weapon_display_tooltip_data.json", {"1": {"weapon_id": 1}})
    write_table(base, "game_common/data/gun_blueprint_data.json", {"1": {"gun_no": 1}})

    paths = module._candidate_profile_paths(base, current)
    assert paths[0] == "game_common/data/weapon_display_tooltip_data.json"
    assert module._profile_path_score(paths[0]) > module._profile_path_score("client_data/item_misc_data.json")
