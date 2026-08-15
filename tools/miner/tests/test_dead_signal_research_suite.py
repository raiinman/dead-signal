from __future__ import annotations

import importlib.util
import json
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


def write_table(root: Path, relative: str, data: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"data": data}), encoding="utf-8")


def test_research_suite_writes_non_publishing_reports(tmp_path: Path) -> None:
    base = tmp_path / "base"
    current = tmp_path / "current"
    reports = tmp_path / "published" / "reports"

    write_table(
        current,
        "game_common/data/item_display_data.json",
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
        "dead-signal-source-finder.json",
        "dead-signal-table-profiles.json",
        "dead-signal-research-suite.json",
    ):
        assert (reports / filename).is_file()

    source_finder = json.loads((reports / "dead-signal-source-finder.json").read_text(encoding="utf-8"))
    assert source_finder["weapons"][0]["publication_status"] == "BLOCKED-PENDING-VERIFICATION"
    assert source_finder["weapons"][0]["state"] == "CANDIDATE"

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
