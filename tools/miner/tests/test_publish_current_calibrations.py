from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR_ROOT = ROOT / "src" / "extractor"


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, EXTRACTOR_ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


module = load_module("publish_current_calibrations", "publish_current_calibrations.py")
extended = load_module("publish_extended_web_data_for_calibration_test", "publish_extended_web_data.py")


def make_affixes(rarity: str):
    rows = []
    for index, (_label, stat_ids, minimum, maximum) in enumerate(module.EXPECTED_SECONDARIES[rarity], start=1):
        rows.append(
            {
                "affix_id": 7000 + index,
                "terms": [
                    {
                        "affix_ids": sorted(stat_ids),
                        "min_val": minimum / 100.0,
                        "max_val": maximum / 100.0,
                    }
                ],
            }
        )
    return rows


def make_variant(item_id: int, minimum=None, maximum=None, valid=True, rarity="Legendary", buff_id=None):
    return {
        "item_id": item_id,
        "name": f"Calibration {item_id}",
        "rarity": rarity,
        "is_valid": valid,
        "buff_id": buff_id if buff_id is not None else [item_id, 1],
        "roll_range": {"minimum_percent": minimum, "maximum_percent": maximum},
        "affix_ids_weight": [200, 200, 200, 200],
        "affixes": make_affixes(rarity),
    }


def make_family(index: int, variants):
    return {
        "canonical_id": f"ds-cal-source-{index}",
        "family_key": str(index),
        "name": f"Family {index}",
        "variants": variants,
    }


class CurrentCalibrationTests(unittest.TestCase):
    def test_regroups_source_families_by_shared_buff_identity(self):
        variants = []
        for i in range(1, 95):
            shared = [900000 + i, 1]
            variants.extend(
                [
                    make_variant(i * 10, 34, 50, buff_id=shared),
                    make_variant(i * 10 + 1, valid=False, buff_id=shared),
                ]
            )
        payload = {"schema": "dead-signal-calibrations", "families": [make_family(101, variants)]}
        result = module.project(payload)
        self.assertEqual("ready-current-system", result["publication_status"])
        self.assertEqual(94, result["record_counts"]["current_families"])
        self.assertEqual(94, result["record_counts"]["legacy_or_noncurrent_variants"])
        self.assertEqual(0, result["record_counts"]["ambiguous_families"])
        self.assertEqual(0, result["record_counts"]["secondary_pool_failures"])
        self.assertEqual(94, len({row["family_key"] for row in result["families"]}))
        self.assertTrue(all(row["family_key"].startswith("buff:") for row in result["families"]))
        self.assertTrue(all(len(row["variants"]) == 1 for row in result["families"]))
        self.assertTrue(all(len(row["variants"][0]["secondary_roll_candidates"]) == 4 for row in result["families"]))
        self.assertEqual("D0102", result["main_roll_semantics"]["stat_id"])
        self.assertEqual([34.0, 50.0], result["main_roll_semantics"]["rarity_ranges_percent"]["Legendary"])
        self.assertEqual(1, result["secondary_roll_semantics"]["selection_count"])

    def test_blocks_duplicate_current_records_for_same_buff_identity(self):
        shared = [900001, 3]
        payload = {
            "schema": "dead-signal-calibrations",
            "families": [make_family(1, [make_variant(10, 34, 50, buff_id=shared), make_variant(11, 34, 50, buff_id=shared)])],
        }
        result = module.project(payload)
        self.assertEqual("blocked-current-system-classification", result["publication_status"])
        self.assertEqual(1, result["record_counts"]["ambiguous_families"])
        self.assertEqual([], result["families"])
        self.assertEqual(["buff:900001:3"], result["ambiguous_family_ids"])

    def test_requires_buff_identity_for_current_classification(self):
        payload = {
            "schema": "dead-signal-calibrations",
            "families": [make_family(1, [make_variant(10, 34, 50, buff_id=[])])],
        }
        result = module.project(payload)
        self.assertEqual("blocked-current-system-classification", result["publication_status"])
        self.assertEqual(["missing-buff-id:10"], result["ambiguous_family_ids"])

    def test_requires_exact_proven_rarity_range(self):
        self.assertTrue(module.is_current_variant(make_variant(1, 18, 25, rarity="Rare")))
        self.assertTrue(module.is_current_variant(make_variant(2, 26, 33, rarity="Epic")))
        self.assertTrue(module.is_current_variant(make_variant(3, 34, 50, rarity="Legendary")))
        self.assertFalse(module.is_current_variant(make_variant(4, 34, 49, rarity="Legendary")))

    def test_secondary_pool_requires_exact_equal_weights(self):
        row = make_variant(1, 34, 50)
        candidates = module.secondary_roll_candidates(row)
        self.assertEqual(4, len(candidates or []))
        self.assertEqual([200, 200, 200, 200], [candidate["weight"] for candidate in candidates or []])
        row["affix_ids_weight"] = [200, 200, 200, 199]
        self.assertIsNone(module.secondary_roll_candidates(row))

    def test_compact_projection_preserves_candidate_weights(self):
        source = {
            "item_id": 123,
            "quality": "Legendary",
            "affix_ids_weight": [200, 200, 200, 200],
            "affixes": make_affixes("Legendary"),
        }
        compact = extended.calibration_variant(source)
        self.assertEqual([200, 200, 200, 200], compact["affix_ids_weight"])


if __name__ == "__main__":
    unittest.main()
