from __future__ import annotations

import json
import marshal
import py_compile
from pathlib import Path

from dead_signal_common_data_registry_audit import run_common_data_registry_audit


def _compile(path: Path, source: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    target = path.with_suffix(".pyc")
    py_compile.compile(str(path), cfile=str(target), doraise=True)
    return target


def test_common_data_registry_audit_maps_exact_table_symbols_without_execution(tmp_path: Path) -> None:
    source_root = tmp_path / "raw"
    marker = tmp_path / "executed.txt"
    _compile(
        source_root / "game_common" / "Registry.py",
        f'''WEAPON_PROTOTYPE_TABLE = "WEAPON_PROTOTYPE_TABLE"\nITEM_TABLE = "ITEM_TABLE"\nclass Env:\n    common_data = {{}}\ndef get_weapon():\n    return Env.common_data[WEAPON_PROTOTYPE_TABLE]\ndef get_item():\n    return Env.common_data.get(ITEM_TABLE)\ndef must_not_run():\n    open(r"{marker}", "w").write("executed")\n''',
    )
    base = tmp_path / "base"
    current = tmp_path / "current"
    reports = tmp_path / "reports"
    base.mkdir()
    current.mkdir()
    (base / "snapshot.json").write_text(json.dumps({"source_root": str(source_root)}), encoding="utf-8")
    (current / "snapshot.json").write_text(json.dumps({"source_root": str(source_root)}), encoding="utf-8")

    report = run_common_data_registry_audit(base, current, reports)

    assert not marker.exists()
    symbols = {row["symbol"]: row for row in report["table_inventory"]}
    assert "WEAPON_PROTOTYPE_TABLE" in symbols
    assert "ITEM_TABLE" in symbols
    assert symbols["WEAPON_PROTOTYPE_TABLE"]["common_data_reference_count"] >= 1
    assert symbols["ITEM_TABLE"]["common_data_reference_count"] >= 1
    assert report["record_counts"]["common_data_accesses"] >= 2
    assert report["record_counts"]["unique_table_symbols"] >= 2
    assert (reports / "common-data-registry-static-audit.json").is_file()
