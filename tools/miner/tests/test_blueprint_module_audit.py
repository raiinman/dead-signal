from __future__ import annotations

import json
import py_compile
from pathlib import Path

from dead_signal_blueprint_module_audit import run_blueprint_module_audit


def _snapshot(root: Path, source_root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "snapshot.json").write_text(
        json.dumps({"source_root": str(source_root)}), encoding="utf-8"
    )
    return root


def test_blueprint_module_audit_walks_every_code_object_without_execution(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    target = source_root / "ui" / "gun_core_part" / "pc" / "BluePrintScrollViewPart.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        """
MODULE_LABEL = 'Blueprints'

def dangerous():
    raise RuntimeError('THIS MUST NEVER EXECUTE')

class BluePrintItemPC:
    label = 'Weapon Features'

    def _show_blueprint_info(self, blueprint):
        marker = 'prototype_desc'
        def nested(value):
            return lambda: value
        return nested(blueprint)

    def get_blueprint_serialized_data_for_tips(self):
        return {'blueprint_id': 123, 'item_id': 456}
""".lstrip(),
        encoding="utf-8",
    )
    pyc = target.with_suffix(".pyc")
    py_compile.compile(str(target), cfile=str(pyc), doraise=True)
    target.unlink()

    base = _snapshot(tmp_path / "base", source_root)
    current = _snapshot(tmp_path / "current", source_root)
    reports = tmp_path / "reports"

    report = run_blueprint_module_audit(base, current, reports)

    assert report["record_counts"]["candidate_modules"] == 1
    assert report["record_counts"]["marshal_compatible_modules"] == 1
    module = report["modules"][0]
    rows = module["code_objects"]
    names = {row["co_name"] for row in rows}
    assert "dangerous" in names
    assert "BluePrintItemPC" in names
    assert "_show_blueprint_info" in names
    assert "get_blueprint_serialized_data_for_tips" in names
    assert "nested" in names
    assert "<lambda>" in names

    show = next(row for row in rows if row["co_name"] == "_show_blueprint_info")
    assert "prototype_desc" in show["string_constants"]
    tips = next(row for row in rows if row["co_name"] == "get_blueprint_serialized_data_for_tips")
    assert "blueprint_id" in tips["string_constants"]
    assert "item_id" in tips["string_constants"]

    report_path = reports / "blueprint-scroll-view-full-static-audit.json"
    assert report_path.is_file()
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert persisted["policy"]["scope"].startswith("No function or symbol filtering")
    assert persisted["policy"]["execution"].startswith("The PYC marshal payload is deserialized")
