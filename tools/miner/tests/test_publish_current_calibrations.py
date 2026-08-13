from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "extractor" / "publish_current_calibrations.py"
spec = importlib.util.spec_from_file_location("publish_current_calibrations", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def make_variant(item_id: int, minimum=None, maximum=None, valid=True, rarity="Legendary"):
    return {
        "item_id": item_id,
        "name": f"Calibration {item_id}",
        "rarity": rarity,
        "is_valid": valid,
        "roll_range": {"minimum_percent": minimum, "maximum_percent": maximum},
    }


def make_family(index: int, variants):
    return {
        "canonical_id": f"ds-cal-{index}",
        "family_key": str(index),
        "name": f"Family {index}",
        "variants": variants,
    }


def test_selects_one_current_variant_per_family():
    payload = {
        "schema": "dead-signal-calibrations",
        "families": [
            make_family(i, [make_variant(i * 10, 34, 50), make_variant(i * 10 + 1)])
            for i in range(1, 95)
        ],
    }
    result = module.project(payload)
    assert result["publication_status"] == "ready-current-system"
    assert result["record_counts"]["current_families"] == 94
    assert result["record_counts"]["legacy_or_noncurrent_variants"] == 94
    assert result["record_counts"]["ambiguous_families"] == 0
    assert all(len(row["variants"]) == 1 for row in result["families"])
    assert result["main_roll_semantics"]["stat_id"] == "D0102"
    assert result["main_roll_semantics"]["rarity_ranges_percent"]["Legendary"] == [34.0, 50.0]


def test_blocks_ambiguous_or_missing_current_family():
    payload = {
        "schema": "dead-signal-calibrations",
        "families": [
            make_family(1, [make_variant(10, 34, 50), make_variant(11, 26, 33, rarity="Epic")]),
            make_family(2, [make_variant(20)]),
        ],
    }
    result = module.project(payload)
    assert result["publication_status"] == "blocked-current-system-classification"
    assert result["record_counts"]["ambiguous_families"] == 2
    assert result["families"] == []


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
