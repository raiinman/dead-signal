import json
import tempfile
import unittest
from pathlib import Path

from extractor.publish_web_data import build_armor_projection, build_weapon_projection


class PublishWebIntegrityRegressionTests(unittest.TestCase):
    @staticmethod
    def write(root: Path, name: str, payload: dict) -> None:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_weapon_projection_withholds_unverified_short_description(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            self.write(
                data,
                "weapons.json",
                {
                    "weapons": [
                        {
                            "blueprint_id": 10,
                            "item_id": 11,
                            "name": "Test Weapon",
                            "category": "Melee",
                            "quality": "Legendary",
                            "short_description": "Known-wrong flavor text must not escape.",
                            "tiers": [],
                            "blueprint_star_progression": {},
                        }
                    ]
                },
            )
            self.write(data, "weapon-math.json", {"weapons": []})
            self.write(data, "gun-profiles.json", {"profiles": []})
            self.write(data, "weapon-configuration.json", {})

            weapon = build_weapon_projection(data)["weapons"][0]
            self.assertEqual("", weapon["description"])
            self.assertEqual(
                "withheld-until-short-description-resolver-is-verified",
                weapon["verification"]["description_status"],
            )

    def test_armor_piece_identity_includes_suit_for_reused_blueprint(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            shared_piece = {
                "blueprint_id": 9001,
                "name": "Variant Mask",
                "slot_id": 27,
                "slot": "Mask",
                "quality": "Legendary",
                "quality_code": 4,
                "tiers": [],
                "crafting_recipes": [],
            }
            self.write(
                data,
                "armor-sets.json",
                {
                    "armor_sets": [
                        {
                            "suit_id": 100,
                            "name": "Variant Base",
                            "pieces": [dict(shared_piece)],
                            "set_bonuses": [],
                        },
                        {
                            "suit_id": 101,
                            "name": "Variant Cold",
                            "pieces": [dict(shared_piece)],
                            "set_bonuses": [],
                        },
                    ],
                    "key_armor": [],
                    "crafting_material_groups": {},
                },
            )

            armor = build_armor_projection(data)
            ids = [piece["canonical_id"] for row in armor["armor_sets"] for piece in row["pieces"]]
            self.assertEqual(["ds-a-100-9001", "ds-a-101-9001"], ids)
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(100, armor["armor_sets"][0]["pieces"][0]["suit_id"])
            self.assertEqual(101, armor["armor_sets"][1]["pieces"][0]["suit_id"])


if __name__ == "__main__":
    unittest.main()
