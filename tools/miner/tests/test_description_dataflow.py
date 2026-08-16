from __future__ import annotations

import importlib.util
import json
import marshal
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
EXTRACTOR = SRC / "extractor"
for candidate in (SRC, EXTRACTOR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from dead_signal_description_dataflow import run_description_dataflow_trace  # noqa: E402
from dead_signal_description_dataflow_fallback import recover_persisted_description_capsules  # noqa: E402
from dead_signal_description_trace_compiler import compile_description_dataflow_trace  # noqa: E402


def write_pyc(path: Path, source: str, filename: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    code = compile(source, filename, "exec")
    header = importlib.util.MAGIC_NUMBER + b"\0" * 12
    path.write_bytes(header + marshal.dumps(code))


def write_snapshot(path: Path, source_root: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "snapshot.json").write_text(json.dumps({"source_root": str(source_root)}), encoding="utf-8")


def test_trace_captures_runtime_prototype_description_path_without_executing_module(tmp_path: Path) -> None:
    root = tmp_path / "extracted"
    base = tmp_path / "base"
    current = tmp_path / "current"
    reports = tmp_path / "published" / "reports"
    sentinel = tmp_path / "executed.txt"

    item_source = f'''
from pathlib import Path
Path(r"{sentinel}").write_text("BAD")

class BluePrintHelper:
    @staticmethod
    def get_weapon_prototype_data_val_by_key(prototype_no, key, default):
        return default

def get_item_desc_text(item):
    return item.get("short_desc")

def prototype_desc_formula(prototype_no):
    return BluePrintHelper.get_weapon_prototype_data_val_by_key(prototype_no, "prototype_desc", "")

def get_gun_info(item_id):
    return prototype_desc_formula(item_id)

def get_gun_item_data(item_no, item_star=1):
    return get_gun_info(item_no)

def get_weapon_item_data(item_no, item_star=1, is_melee=False):
    return get_gun_item_data(item_no, item_star)
'''
    blueprint_source = '''
WEAPON_PROTOTYPE_TABLE = "weapon_prototype_data"
class Env:
    common_data = {"weapon_prototype_data": {}}

def get_weapon_prototype_data(prototype_id):
    return Env.common_data.get(WEAPON_PROTOTYPE_TABLE, {}).get(prototype_id)

def get_weapon_prototype_data_val_by_key(prototype_id, key, default=None):
    data = get_weapon_prototype_data(prototype_id)
    return data.get(key, default) if data else default
'''
    producer_source = '''
data = {101: {"prototype_name": "Example", "prototype_desc": "Example description"}}
'''
    write_pyc(root / "ui/data_tools/ItemDataTools.pyc", item_source, "ui/data_tools/ItemDataTools.py")
    write_pyc(root / "game_common/guncore/BluePrintHelper.pyc", blueprint_source, "game_common/guncore/BluePrintHelper.py")
    write_pyc(root / "game_common/data/weapon_prototype_data.pyc", producer_source, "game_common/data/weapon_prototype_data.py")
    write_snapshot(base, root)
    write_snapshot(current, root)

    report = run_description_dataflow_trace(base, current, reports)
    assert sentinel.exists() is False
    assert report["mode"] == "offline-static-pyc-only"
    assert report["record_counts"]["target_pyc_files"] == 3
    assert report["record_counts"]["consumer_modules"] == 2
    assert report["record_counts"]["producer_candidate_modules"] == 1
    assert report["record_counts"]["marshal_compatible_pycs"] == 3
    assert report["record_counts"]["prototype_desc_prototype_lookup_functions"] >= 1
    assert report["target_presence"]["prototype_desc"] >= 1
    assert report["target_presence"]["weapon_prototype_data"] >= 1
    functions = {row["function"] for row in report["code_objects"]}
    assert "get_weapon_item_data" in functions
    assert "get_gun_item_data" in functions
    assert "get_gun_info" in functions
    assert "get_weapon_prototype_data_val_by_key" in functions
    formula_row = next(row for row in report["code_objects"] if row["function"] == "prototype_desc_formula")
    assert formula_row["relationship_signals"]["prototype_desc_and_prototype_lookup_cooccur"] is True
    assert formula_row["code_capsule"]["co_code_hex"]
    assert formula_row["raw_wordcode"]
    assert "Diagnostic only" in formula_row["diagnostic_disassembly"]["warning"]
    assert report["producer_candidates"][0]["relative_path"].endswith("weapon_prototype_data.pyc")
    assert "Never opened" in report["safety"]["game_process"]
    assert (reports / "weapon-description-static-dataflow.json").is_file()


def test_persisted_fallback_recovers_exact_code_capsule_without_loading_report_wholesale(tmp_path: Path) -> None:
    reports = tmp_path / "published" / "reports"
    reports.mkdir(parents=True)
    capsule = {
        "co_name": "get_weapon_item_data",
        "co_qualname": "get_weapon_item_data",
        "co_filename": "ui/data_tools/ItemDataTools.py",
        "co_names": ["get_item_desc_text"],
        "co_varnames": ["item", "prototype_desc"],
        "co_freevars": [],
        "co_cellvars": [],
        "co_consts": [None, "prototype_desc"],
        "co_code_hex": "64005300",
        "co_code_len": 4,
    }
    payload = {
        "padding": "x" * 10000,
        "rows": [{"code_capsule": capsule}],
    }
    (reports / "weapon-progression-pyc-consumers.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    result = recover_persisted_description_capsules(reports)
    recovered = {row["function"]: row for row in result["functions"]}
    assert "get_weapon_item_data" in recovered
    assert recovered["get_weapon_item_data"]["relationship_signals"]["contains_prototype_desc"] is True
    assert recovered["get_weapon_item_data"]["relationship_signals"]["calls_get_item_desc_text"] is True
    assert recovered["get_weapon_item_data"]["raw_wordcode"]
    assert "get_item_desc_text" in result["missing_functions"]


def test_compact_compiler_builds_only_description_trace_bundle(tmp_path: Path) -> None:
    root = tmp_path / "extracted"
    base = tmp_path / "base"
    current = tmp_path / "current"
    published = tmp_path / "published"
    (published / "data").mkdir(parents=True)
    (published / "data" / "weapons.json").write_text(json.dumps({"weapons": []}), encoding="utf-8")

    write_pyc(
        root / "ui/data_tools/ItemDataTools.pyc",
        'def get_item_desc_text(item):\n    return item.get("short_desc")\n\ndef get_weapon_item_data(item):\n    return item\n',
        "ui/data_tools/ItemDataTools.py",
    )
    write_pyc(
        root / "game_common/guncore/BluePrintHelper.pyc",
        'WEAPON_PROTOTYPE_TABLE="weapon_prototype_data"\ndef get_weapon_prototype_data(x):\n    return None\ndef get_weapon_prototype_data_val_by_key(x,k,d=None):\n    return d\n',
        "game_common/guncore/BluePrintHelper.py",
    )
    write_snapshot(base, root)
    write_snapshot(current, root)
    (tmp_path / "last-run.json").write_text(json.dumps({
        "active_snapshots": {"base": str(base), "current": str(current)},
        "published": str(published),
    }), encoding="utf-8")

    result = compile_description_dataflow_trace(tmp_path)
    archive = Path(result["bundle"])
    assert archive.is_file()
    assert result["record_counts"]["target_pyc_files"] == 2
    import zipfile
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
    assert "dead-signal-description-dataflow-summary.json" in names
    assert "published/reports/weapon-description-static-dataflow.json" in names
    assert "snapshots/base-snapshot.json" in names
    assert "snapshots/current-snapshot.json" in names
    assert "published/data/weapons.json" not in names
