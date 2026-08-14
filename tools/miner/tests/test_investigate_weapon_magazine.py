import importlib.util
import sys
import json
import py_compile
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("investigate_weapon_magazine.py")
spec = importlib.util.spec_from_file_location("magprobe", MODULE_PATH)
magprobe = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = magprobe
spec.loader.exec_module(magprobe)


def test_exact_json_and_static_pyc_metadata(tmp_path):
    data = tmp_path / "game_common" / "data"
    data.mkdir(parents=True)
    (data / "gun_base_params_data.json").write_text(json.dumps({
        "10230331": {
            "weapon_magazine_size_affix": "Q1100",
            "weapon_magazine_size_affix_value": 8,
            "unrelated": 10,
        }
    }), encoding="utf-8")
    (data / "ids.json").write_text(json.dumps({
        "item": 10233301,
        "blueprint": "13233301",
        "gun": 10230331,
        "near_miss": "Q11000",
    }), encoding="utf-8")

    source = tmp_path / "fixture.py"
    source.write_text(
        'def get_gun_magazine_size(item_no, all_affix_add):\n'
        '    magazine = all_affix_add.get("Q1100", 0)\n'
        '    rate = all_affix_add.get("Q1101", 0)\n'
        '    return magazine, rate\n',
        encoding="utf-8",
    )
    py_compile.compile(str(source), cfile=str(tmp_path / "fixture.pyc"), doraise=True)

    report = magprobe.build_report(tmp_path, 10233301, 13233301, 10230331, "Q1100", "Q1101")
    labels = {hit["matched"] for hit in report["json_hits"]}
    assert {"item_id", "blueprint_id", "gun_no", "absolute_affix"} <= labels
    assert all(hit["value"] != "Q11000" for hit in report["json_hits"])
    assert "get_gun_magazine_size" in report["summary"]["focus_functions_found"]
    assert report["summary"]["q1100_pyc_functions"]
    assert report["summary"]["q1101_pyc_functions"]
    assert report["resolution"]["final_magazine"] is None
    assert report["safety"]["game_bytecode_executed"] is False


def test_missing_or_invalid_pyc_is_fail_closed(tmp_path):
    (tmp_path / "bad.pyc").write_bytes(b"not a pyc")
    report = magprobe.build_report(tmp_path, 1, 2, 3, "Q1100", "Q1101")
    assert report["pyc_hits"] == []
    assert report["resolution"]["status"] == "evidence-only-unresolved"
