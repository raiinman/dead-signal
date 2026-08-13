from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "src" / "extractor"
if str(EXTRACTOR) not in sys.path:
    sys.path.insert(0, str(EXTRACTOR))

SPEC = importlib.util.spec_from_file_location(
    "armor_tier_completion", EXTRACTOR / "armor_tier_completion.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def write_table(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"data": data}), encoding="utf-8")


def tier_row(item_id: int, tier: int):
    return {
        "item_id": item_id,
        "data_level": tier,
        "tier_label": f"Tier {tier}",
        "attributes": [
            {"code": "A0200", "key": "hp", "label": "HP", "value": tier * 100},
            {"code": "R3600", "key": "pollution", "label": "Pollution Resistance", "value": tier},
            {"code": "D4100", "key": "psi", "label": "Psi Intensity", "value": tier * 10},
        ],
        "blueprint_id": 24303101,
    }


def test_complete_file_recovers_exact_variant_and_preserves_recipe_conflict():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        base = root / "base"
        current = root / "current"
        output = root / "armor-sets.json"

        piece = {
            "name": "Blackstone Boots - Cold",
            "blueprint_id": 24303101,
            "tiers": [
                tier_row(24003301, 1),
                tier_row(24003302, 2),
                tier_row(24003304, 4),
                tier_row(24003305, 5),
            ],
            "crafting_recipes": [
                {"tier": 3, "output_item_id": 24003103}
            ],
        }
        output.write_text(
            json.dumps(
                {
                    "armor_sets": [{"suit_id": 1033, "pieces": [piece]}],
                    "key_armor": [],
                    "record_counts": {},
                    "review_queue": [],
                }
            ),
            encoding="utf-8",
        )
        write_table(
            current / "game_common/data/equip_data.json",
            {
                "24003303": {
                    "blueprint_no": 24303101,
                    "suit_id": 1033,
                    "equip_origin_id": 24003303,
                },
                "24003103": {
                    "blueprint_no": 24303101,
                    "suit_id": 1031,
                    "equip_origin_id": 24003103,
                },
            },
        )
        write_table(
            current / "game_common/data/equip_origin_data.json",
            {
                "24003303": {
                    "base_attr_name_list": ["A0200", "R3600", "D4100"],
                    "base_attr_val_list": [333, 13, 33],
                },
                "24003103": {
                    "base_attr_name_list": ["A0200", "R3600", "D4100"],
                    "base_attr_val_list": [999, 99, 99],
                },
            },
        )
        write_table(
            current / "game_common/data/item_data.json",
            {
                "24003303": {
                    "durability": 100,
                    "weight": 2,
                    "icon": "cold-boots",
                    "forge_icon": "cold-boots-forge",
                }
            },
        )

        report = MODULE.complete_file(base, current, output, log=lambda _message: None)
        payload = json.loads(output.read_text(encoding="utf-8"))
        tiers = payload["armor_sets"][0]["pieces"][0]["tiers"]
        tier_three = next(row for row in tiers if row["data_level"] == 3)

        assert tier_three["item_id"] == 24003303
        assert tier_three["hp"] == 333
        assert tier_three["recovery_status"] == "recovered-exact-blueprint-suit-tier-series"
        assert report["status"] == "complete"
        assert len(report["recovered"]) == 1
        assert len(report["crafting_variant_conflicts"]) == 1
        recipe = payload["armor_sets"][0]["pieces"][0]["crafting_recipes"][0]
        assert recipe["output_item_id"] == 24003103
        assert recipe["variant_identity_status"] == "unresolved-output-variant"
        assert recipe["variant_stat_item_id"] == 24003303


def test_ambiguous_variant_candidates_remain_unresolved():
    equipment = {
        "23001401": {"blueprint_no": 23301401, "suit_id": 1005},
        "99999901": {"blueprint_no": 23301401, "suit_id": 1005},
    }
    origins = {
        "23001401": {"base_attr_name_list": ["A0200"], "base_attr_val_list": [100]},
        "99999901": {"base_attr_name_list": ["A0200"], "base_attr_val_list": [200]},
    }
    piece = {
        "name": "Blast Pants",
        "blueprint_id": 23301401,
        "tiers": [
            {
                "item_id": 23001402,
                "data_level": 2,
                "attributes": [{"code": "A0200", "key": "hp", "label": "HP", "value": 200}],
            },
            {
                "item_id": 23001403,
                "data_level": 3,
                "attributes": [{"code": "A0200", "key": "hp", "label": "HP", "value": 300}],
            },
            {
                "item_id": 23001404,
                "data_level": 4,
                "attributes": [{"code": "A0200", "key": "hp", "label": "HP", "value": 400}],
            },
            {
                "item_id": 23001405,
                "data_level": 5,
                "attributes": [{"code": "A0200", "key": "hp", "label": "HP", "value": 500}],
            },
        ],
        "crafting_recipes": [],
    }
    recovered, unresolved, conflicts = MODULE.complete_piece_tiers(
        piece, 1005, "set_piece", equipment, origins, {}
    )
    assert recovered == []
    assert conflicts == []
    assert len(unresolved) == 1
    assert sorted(unresolved[0]["candidate_item_ids"]) == [23001401, 99999901]
