import sys
import unittest
from pathlib import Path


MINER_ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = MINER_ROOT / "src" / "extractor"
sys.path.insert(0, str(EXTRACTOR))

from export_weapon_math import build_weapon_math, intrinsic_attack, static_attack_float


class WeaponMathTests(unittest.TestCase):
    def test_proven_attack_conversion_truncates_positive_fraction(self) -> None:
        self.assertEqual(683, intrinsic_attack(547, 1.25))

    def test_attack_ratio_sources_share_one_additive_bucket(self) -> None:
        self.assertAlmostEqual(792.28, static_attack_float(683, [0.12, 0.04], [0]))

    def test_complete_weapon_builds_full_tier_star_matrix(self) -> None:
        weapon = {
            "blueprint_id": 1,
            "item_id": 2,
            "name": "Test Weapon",
            "category": "Test",
            "quality": "Rare",
            "tiers": [{"tier": tier, "item_id": tier + 10, "damage": tier * 100} for tier in range(1, 6)],
            "blueprint_attribute_progression": {
                "levels": [
                    {"level": 1, "strength_lv": 1, "preset_attack_ratio": 1.0, "base_attributes": []},
                    {"level": 2, "strength_lv": 2, "preset_attack_ratio": 1.1, "base_attributes": []},
                ]
            },
        }
        result = build_weapon_math({"weapons": [weapon]})
        self.assertTrue(result["validation"]["passed"])
        self.assertEqual(10, result["record_counts"]["tier_star_combinations"])
        self.assertEqual(550, result["weapons"][0]["tier_star_matrix"][4]["blueprint_star_values"][1]["base_attack"])

    def test_incomplete_tier_data_fails_closed(self) -> None:
        result = build_weapon_math({"weapons": [{"blueprint_id": 1, "name": "Broken", "tiers": [], "blueprint_attribute_progression": {"levels": []}}]})
        self.assertFalse(result["validation"]["passed"])
        self.assertEqual(1, result["record_counts"]["weapons_with_validation_issues"])


if __name__ == "__main__":
    unittest.main()
