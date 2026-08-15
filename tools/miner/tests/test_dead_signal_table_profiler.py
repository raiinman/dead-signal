from __future__ import annotations

import importlib.util
import json
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "src" / "dead_signal_table_profiler.py"
spec = importlib.util.spec_from_file_location("dead_signal_table_profiler", MODULE)
profiler = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(profiler)


def _write_table(path: Path, rows: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"data": rows}), encoding="utf-8")


def test_profiles_identity_description_shared_values_and_shapes(tmp_path: Path) -> None:
    table = tmp_path / "weapon_ui_data.json"
    _write_table(
        table,
        {
            "100": {"item_id": 100, "tooltip": "alpha", "quality": 4},
            "101": {"item_id": 101, "tooltip": "alpha", "quality": 4},
            "102": {"item_id": 102, "tooltip": "beta", "quality": 3, "special_flag": 1},
        },
    )

    result = profiler.profile_table(table, layer="current", table="game_common/data/weapon_ui_data.json")
    fields = {row["field"]: row for row in result["fields"]}

    assert result["brand"] == "Dead Signal"
    assert result["record_count"] == 3
    assert result["record_shape_count"] == 2
    assert fields["item_id"]["identity_like"] is True
    assert fields["tooltip"]["description_like"] is True
    assert fields["special_flag"]["coverage"] == round(1 / 3, 6)
    assert any(
        row["field"] == "tooltip" and row["value"] == "alpha" and row["occurrences"] == 2
        for row in result["shared_scalar_values"]
    )
    assert result["evidence_policy"]["publication"].startswith("Profiler output cannot")


def test_profile_diff_surfaces_new_description_field(tmp_path: Path) -> None:
    base_path = tmp_path / "base.json"
    current_path = tmp_path / "current.json"
    _write_table(base_path, {"1": {"item_id": 1}, "2": {"item_id": 2}})
    _write_table(
        current_path,
        {"1": {"item_id": 1, "display_text": "A"}, "2": {"item_id": 2, "display_text": "B"}},
    )

    base = profiler.profile_table(base_path, layer="base", table="weapon_data.json")
    current = profiler.profile_table(current_path, layer="current", table="weapon_data.json")
    diff = profiler.compare_profiles(base, current)

    display = next(row for row in diff["new_fields"] if row["field"] == "display_text")
    assert display["description_like"] is True
    assert display["current_coverage"] == 1.0
    assert diff["description_field_changes"]
