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


def test_trace_captures_description_functions_without_executing_module(tmp_path: Path) -> None:
    root = tmp_path / "extracted"
    base = tmp_path / "base"
    current = tmp_path / "current"
    reports = tmp_path / "published" / "reports"
    sentinel = tmp_path / "executed.txt"

    item_source = f'''
from pathlib import Path
Path(r"{sentinel}").write_text("BAD")

def get_item_desc_text(item):
    return item.get("detail_desc")

def get_weapon_item_data(item):
    prototype_desc = get_item_desc_text(item)
    return {{"prototype_desc": prototype_desc}}
'''
    blueprint_source = '''
weapon_prototype_data = {}

def get_weapon_prototype_data(prototype_id):
    return weapon_prototype_data.get(prototype_id)

def get_weapon_prototype_data_val_by_key(prototype_id, key):
    data = get_weapon_prototype_data(prototype_id)
    return data.get(key) if data else None
'''
    write_pyc(root / "ui/data_tools/ItemDataTools.pyc", item_source, "ui/data_tools/ItemDataTools.py")
    write_pyc(root / "game_common/guncore/BluePrintHelper.pyc", blueprint_source, "game_common/guncore/BluePrintHelper.py")
    write_snapshot(base, root)
    write_snapshot(current, root)

    report = run_description_dataflow_trace(base, current, reports)
    assert sentinel.exists() is False
    assert report["mode"] == "offline-static-pyc-only"
    assert report["record_counts"]["target_pyc_files"] == 2
    assert report["record_counts"]["marshal_compatible_pycs"] == 2
    assert report["record_counts"]["prototype_desc_get_item_desc_text_cooccurrences"] >= 1
    assert report["target_presence"]["prototype_desc"] >= 1
    assert report["target_presence"]["get_item_desc_text"] >= 1
    functions = {row["function"] for row in report["code_objects"]}
    assert "get_weapon_item_data" in functions
    assert "get_item_desc_text" in functions
    assert "get_weapon_prototype_data_val_by_key" in functions
    weapon_row = next(row for row in report["code_objects"] if row["function"] == "get_weapon_item_data")
    assert weapon_row["relationship_signals"]["prototype_desc_and_desc_helper_cooccur"] is True
    assert weapon_row["code_capsule"]["co_code_hex"]
    assert weapon_row["raw_wordcode"]
    assert "Diagnostic only" in weapon_row["diagnostic_disassembly"]["warning"]
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
    reports = published / "reports"
    (published / "data").mkdir(parents=True)
    (published / "data" / "weapons.json").write_text(json.dumps({"weapons": []}), encoding="utf-8")

    write_pyc(
        root / "ui/data_tools/ItemDataTools.pyc",
        'def get_item_desc_text(item):\n    return item.get("detail_desc")\n\ndef get_weapon_item_data(item):\n    prototype_desc=get_item_desc_text(item)\n    return {"prototype_desc":prototype_desc}\n',
        "ui/data_tools/ItemDataTools.py",
    )
    write_pyc(
        root / "game_common/guncore/BluePrintHelper.pyc",
        'weapon_prototype_data={}\ndef get_weapon_prototype_data(x):\n    return weapon_prototype_data.get(x)\ndef get_weapon_prototype_data_val_by_key(x,k):\n    d=get_weapon_prototype_data(x)\n    return d.get(k) if d else None\n',
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
