from __future__ import annotations

import importlib.util
import json
import marshal
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
for candidate in (SRC, SRC / "extractor", SRC / "neoxtractor"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from dead_signal_weapon_description_full_trace import run_weapon_description_full_trace  # noqa: E402


def write_pyc(path: Path, source: str, filename: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    code = compile(source, filename, "exec")
    path.write_bytes(importlib.util.MAGIC_NUMBER + (b"\0" * 12) + marshal.dumps(code))


def write_snapshot(path: Path, source_root: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "snapshot.json").write_text(json.dumps({"source_root": str(source_root)}), encoding="utf-8")


def test_full_trace_finds_ui_and_exact_aa12_literals_without_execution(tmp_path: Path) -> None:
    root = tmp_path / "extracted"
    base = tmp_path / "base"
    current = tmp_path / "current"
    reports = tmp_path / "reports"
    sentinel = tmp_path / "executed.txt"

    write_pyc(
        root / "ui/weapon_craft_part/ScrollViewItems.pyc",
        f'''\nfrom pathlib import Path\nPath(r"{sentinel}").write_text("BAD")\ndef update_weapon_info(item):\n    discription = "description"\n    label_skill_desc = item.get("copywriting")\n    return label_skill_desc\n''',
        "ui/weapon_craft_part/ScrollViewItems.py",
    )
    write_pyc(
        root / "ui/ui_item/UIGunTipItem.pyc",
        '''\ndef update_info(item):\n    return item.get("prototype_desc")\n''',
        "ui/ui_item/UIGunTipItem.py",
    )
    write_pyc(
        root / "misc/aa12_marker.pyc",
        '''\nAA12_BLUEPRINT = "13231101"\nAA12_ITEM = "10231101"\nAA12_GUN = "10230011"\nAA12_POSTURE = "sg_aa12_sk_a_01"\n''',
        "misc/aa12_marker.py",
    )
    write_snapshot(base, root)
    write_snapshot(current, root)

    report = run_weapon_description_full_trace(base, current, reports)
    assert sentinel.exists() is False
    assert report["record_counts"]["pyc_files_scanned"] >= 3
    assert report["record_counts"]["ui_candidate_files"] >= 2
    assert report["record_counts"]["aa12_exact_literal_files"] >= 1
    assert any(row["relative_path"].endswith("ScrollViewItems.pyc") for row in report["ui_presentation_candidates"])
    assert any("label_skill_desc" in row["description_symbols"] for row in report["code_objects"])
    assert (reports / "weapon-description-full-trace.json").is_file()
    assert "never imported or executed" in report["policy"]["execution"].lower()


def test_full_trace_keeps_aa12_identity_exact(tmp_path: Path) -> None:
    root = tmp_path / "extracted"
    base = tmp_path / "base"
    current = tmp_path / "current"
    reports = tmp_path / "reports"
    write_pyc(root / "misc/near_match.pyc", 'VALUE="13231100"\n', "misc/near_match.py")
    write_pyc(root / "misc/exact.pyc", 'VALUE="13231101"\n', "misc/exact.py")
    write_snapshot(base, root)
    write_snapshot(current, root)

    report = run_weapon_description_full_trace(base, current, reports)
    paths = {row["relative_path"] for row in report["aa12_exact_literal_files"]}
    assert "misc/exact.pyc" in paths
    assert "misc/near_match.pyc" not in paths
