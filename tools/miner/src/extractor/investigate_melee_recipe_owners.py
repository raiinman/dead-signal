"""Trace exact melee item/blueprint identities through bounded crafting owners."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from normalize_armor import table


CANDIDATE_TABLES = (
    "client_data/forge_formula_map_data.json",
    "client_data/weapon_craft_para.json",
    "game_common/data/achieve_recipe_data.json",
    "game_common/data/blueprint_recipe_season_data.json",
    "game_common/data/equip_corr_craft_lv_data.json",
    "game_common/data/forge_data.json",
    "game_common/data/forge_choice_material_data.json",
    "game_common/data/forge_queue_data.json",
    "game_common/data/forge_semi_data.json",
    "game_common/data/item_forge_dis_data.json",
    "game_common/data/item_forge_repair_data.json",
    "game_common/data/weapon_craft_data.json",
)


def exact_paths(value: Any, targets: set[str], path: str = "$") -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key) in targets:
                hits.append({"path": child_path, "match": str(key), "location": "key"})
            hits.extend(exact_paths(child, targets, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(exact_paths(child, targets, f"{path}[{index}]"))
    elif str(value) in targets:
        hits.append({"path": path, "match": str(value), "location": "value"})
    return hits


def investigate(base: Path, current: Path, targets: set[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for relative in CANDIDATE_TABLES:
        layers: list[tuple[str, Path]] = [("base", base / relative)]
        if (current / relative).exists():
            layers.append(("current", current / relative))
        for layer, path in layers:
            if not path.exists():
                continue
            for record_id, record in table(path).items():
                hits = exact_paths(record, targets, f"$.{record_id}")
                if str(record_id) in targets:
                    hits.insert(0, {"path": f"$.{record_id}", "match": str(record_id), "location": "record-key"})
                if hits:
                    rows.append({
                        "layer": layer,
                        "table": relative,
                        "record_id": str(record_id),
                        "hits": hits,
                        "record": record,
                    })
    return {
        "schema": "dead-signal-melee-recipe-owner-investigation",
        "schema_version": 1,
        "targets": sorted(targets),
        "candidate_tables": list(CANDIDATE_TABLES),
        "record_counts": {"exact_owner_candidates": len(rows)},
        "records": rows,
        "policy": "Exact scalar or key equality in the bounded crafting-owner table set only; no name, substring, or fuzzy matching.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--ids", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = investigate(args.base, args.current, {str(value) for value in args.ids})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["record_counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
