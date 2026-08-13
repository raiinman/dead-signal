from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "extractor" / "publish_current_calibrations.py"
spec = importlib.util.spec_from_file_location("publish_current_calibrations", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def make_variant(item_id: int, minimum=None, maximum=None, valid=True, rarity="Legendary", buff_id=None):
    return {
        "item_id": item_id,
        "name": f"Calibration {item_id}",
        "rarity": rarity,
        "is_valid": valid,
        "buff_id": buff_id if buff_id is not None else [item_id, 1],
        "roll_range": {"minimum_percent": minimum, "maximum_percent": maximum},
    }


def make_family(index: int, variants):
    return {
        "canonical_id": f"ds-cal-source-{index}",
        "family_key": str(index),
        "name": f"Family {index}",
        "variants": variants,
    }


def test_regroups_broad_source_families_by_shared_buff_identity():
    variants = []
    for i in range(1, 95):
        shared = [900000 + i, 1]
        variants.extend(
            [
                make_variant(i * 10, 34, 50, buff_id=shared),
                make_variant(i * 10 + 1, valid=False, buff_id=shared),
            ]
        )
    payload = {
        "schema": "dead-signal-calibrations",
        "families": [make_family(101, variants)],
    }
    result = module.project(payload)
    assert result["publication_status"] == "ready-current-system"
    assert result["record_counts"]["current_families"] == 94
    assert result["record_counts"]["legacy_or_noncurrent_variants"] == 94
    assert result["record_counts"]["ambiguous_families"] == 0
    assert len({row["family_key"] for row in result["families"]}) == 94
    assert all(row["family_key"].startswith("buff:") for row in result["families"])
    assert all(len(row["variants"]) == 1 for row in result["families"])
    assert result["main_roll_semantics"]["stat_id"] == "D0102"
    assert result["main_roll_semantics"]["rarity_ranges_percent"]["Legendary"] == [34.0, 50.0]


def test_blocks_duplicate_current_records_for_same_buff_identity():
    shared = [900001, 3]
    payload = {
        "schema": "dead-signal-calibrations",
        "families": [
            make_family(
                1,
                [
                    make_variant(10, 34, 50, buff_id=shared),
                    make_variant(11, 34, 50, buff_id=shared),
                ],
            )
        ],
    }
    result = module.project(payload)
    assert result["publication_status"] == "blocked-current-system-classification"
    assert result["record_counts"]["ambiguous_families"] == 1
    assert result["families"] == []
    assert result["ambiguous_family_ids"] == ["buff:900001:3"]


def test_requires_buff_identity_for_current_classification():
    payload = {
        "schema": "dead-signal-calibrations",
        "families": [make_family(1, [make_variant(10, 34, 50, buff_id=[])])],
    }
    result = module.project(payload)
    assert result["publication_status"] == "blocked-current-system-classification"
    assert result["record_counts"]["ambiguous_families"] == 1
    assert result["ambiguous_family_ids"] == ["missing-buff-id:10"]


def test_requires_exact_proven_rarity_range():
    assert module.is_current_variant(make_variant(1, 18, 25, rarity="Rare"))
    assert module.is_current_variant(make_variant(2, 26, 33, rarity="Epic"))
    assert module.is_current_variant(make_variant(3, 34, 50, rarity="Legendary"))
    assert not module.is_current_variant(make_variant(4, 34, 49, rarity="Legendary"))
    assert not module.is_current_variant(make_variant(5, 34, 50, rarity="Unknown"))


def test_invalid_or_partial_range_is_not_current():
    assert not module.is_current_variant(make_variant(1, 34, 50, valid=False))
    assert not module.is_current_variant(make_variant(1, None, 50))
    assert not module.is_current_variant(make_variant(1, 50, 34))


class CurrentCalibrationSecondaryTests(unittest.TestCase):
    def test_exact_secondary_contract(self):
        affixes = []
        for index, (_label, stat_ids, minimum, maximum) in enumerate(module.EXPECTED_SECONDARIES["Legendary"]):
            affixes.append(
                {
                    "affix_id": index + 1,
                    "terms": [
                        {
                            "affix_ids": sorted(stat_ids),
                            "min_val": minimum / 100.0,
                            "max_val": maximum / 100.0,
                        }
                    ],
                }
            )
        row = {
            "rarity": "Legendary",
            "affix_ids_weight": [200, 200, 200, 200],
            "affixes": affixes,
        }
        candidates = module.secondary_roll_candidates(row)
        self.assertEqual(4, len(candidates or []))
        self.assertEqual([200, 200, 200, 200], [candidate["weight"] for candidate in candidates or []])


if __name__ == "__main__":
    unittest.main()
