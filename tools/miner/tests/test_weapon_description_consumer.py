from __future__ import annotations

import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
EXTRACTOR = SRC / "extractor"
for candidate in (SRC, EXTRACTOR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from dead_signal_weapon_description_consumer import run_weapon_description_consumer_trace  # noqa: E402


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_pyc_report(reports: Path) -> None:
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "weapon-progression-pyc-consumers.json").write_text(
        "\n".join([
            '{"pyc":"game_common/guncore/BluePrintHelper.pyc","name":"weapon_prototype_data"}',
            '{"pyc":"game_common/guncore/BluePrintHelper.pyc","name":"get_weapon_prototype_data"}',
            '{"pyc":"game_common/guncore/BluePrintHelper.pyc","name":"get_weapon_prototype_data_val_by_key"}',
            '{"pyc":"ui/data_tools/ItemDataTools.pyc","name":"prototype_desc"}',
            '{"pyc":"ui/data_tools/ItemDataTools.pyc","name":"get_item_desc_text"}',
            '{"pyc":"ui/data_tools/ItemDataTools.pyc","name":"get_weapon_item_data"}',
        ]) + "\n",
        encoding="utf-8",
    )


def test_exact_prototype_desc_becomes_consumer_backed_candidate(tmp_path: Path) -> None:
    base = tmp_path / "base"
    current = tmp_path / "current"
    reports = tmp_path / "published" / "reports"
    weapons = tmp_path / "published" / "data" / "weapons.json"

    write_json(base / "game_common/data/weapon_prototype_data.json", {
        "data": {"300": {"weapon_type": 5, "prototype_desc": "DESC_PROTO_300"}}
    })
    write_json(base / "translate/translate_data_en.json", {"strings": {
        "DESC_PROTO_300": "A prototype-backed weapon description."
    }})
    write_json(current / "translate/translate_data_en_patch.json", {"strings": {
        "DESC_PROTO_300": "A prototype-backed weapon description."
    }})
    write_json(weapons, {"weapons": [{
        "blueprint_id": 100, "item_id": 200, "prototype_id": 300,
        "name": "Test Pathfinder", "category": "Sniper Rifle",
    }]})
    write_pyc_report(reports)

    report = run_weapon_description_consumer_trace(base, current, weapons, reports)
    row = report["weapons"][0]
    assert row["status"] == "prototype-desc-resolved-consistently"
    assert row["text"] == "A prototype-backed weapon description."
    assert row["consumer_backed_candidate"] is True
    assert row["publication_status"] == "BLOCKED-PENDING-UI-CONFIRMATION"
    assert row["source"]["table"] == "game_common/data/weapon_prototype_data.json"
    assert row["source"]["record_id"] == "300"
    assert row["source"]["field"] == "prototype_desc"
    assert row["source"]["json_pointer"] == "/prototype_desc"
    assert report["consumer_evidence"]["all_required_tokens_found"] is True
    assert report["record_counts"]["consumer_backed_candidates"] == 1
    assert "VERIFIED" not in row.values()
    assert (reports / "weapon-description-ui-consumer-trace.json").is_file()


def test_translation_conflict_stays_blocked(tmp_path: Path) -> None:
    base = tmp_path / "base"
    current = tmp_path / "current"
    reports = tmp_path / "published" / "reports"
    weapons = tmp_path / "published" / "data" / "weapons.json"

    write_json(base / "game_common/data/weapon_prototype_data.json", {
        "data": {"300": {"prototype_desc": "DESC_PROTO_300"}}
    })
    write_json(base / "translate/translate_data_en.json", {"strings": {"DESC_PROTO_300": "Base text."}})
    write_json(current / "translate/translate_data_en_patch.json", {"strings": {"DESC_PROTO_300": "Different current text."}})
    write_json(weapons, {"weapons": [{"blueprint_id": 100, "prototype_id": 300, "name": "Test"}]})
    write_pyc_report(reports)

    row = run_weapon_description_consumer_trace(base, current, weapons, reports)["weapons"][0]
    assert row["status"] == "prototype-desc-translation-conflict"
    assert row["consumer_backed_candidate"] is False
    assert row["text"] == ""


def test_missing_exact_prototype_never_falls_back_by_name(tmp_path: Path) -> None:
    base = tmp_path / "base"
    current = tmp_path / "current"
    reports = tmp_path / "published" / "reports"
    weapons = tmp_path / "published" / "data" / "weapons.json"

    write_json(base / "game_common/data/weapon_prototype_data.json", {
        "data": {"301": {"prototype_name": "Test Pathfinder", "prototype_desc": "DESC_WRONG"}}
    })
    write_json(base / "translate/translate_data_en.json", {"strings": {"DESC_WRONG": "Wrong prototype text."}})
    write_json(weapons, {"weapons": [{
        "blueprint_id": 100, "prototype_id": 300, "name": "Test Pathfinder",
    }]})
    write_pyc_report(reports)

    row = run_weapon_description_consumer_trace(base, current, weapons, reports)["weapons"][0]
    assert row["status"] == "prototype-record-missing"
    assert row["consumer_backed_candidate"] is False
    assert "text" not in row
