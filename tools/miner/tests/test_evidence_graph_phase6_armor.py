from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

MINER = Path(__file__).resolve().parents[1]
SRC = MINER / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_armor_adapters import (  # noqa: E402
    ARMOR_CONTRACT,
    ARMOR_SET_CONTRACT,
    ArmorAdapter,
    ArmorSetAdapter,
)
from dead_signal_evidence_contracts import validate_generalized_graph  # noqa: E402
from dead_signal_generalized_graph import DeadSignalGeneralizedGraph  # noqa: E402


def tier(item_id: int, blueprint_id: int, level: int = 1) -> dict:
    return {
        "item_id": item_id,
        "data_level": level,
        "tier_label": f"Tier {level}",
        "blueprint_id": blueprint_id,
        "attributes": [{"code": "A0200", "key": "hp", "label": "HP", "value": 100 + level}],
        "hp": 100 + level,
        "pollution_resistance": 5,
        "psi_intensity": 7,
        "icon": f"icons/{item_id}.png",
    }


def recipe(blueprint_id: int, forge_no: int) -> dict:
    return {
        "tier": 1,
        "tier_label": "Tier 1",
        "forge_no": forge_no,
        "recipe_key": f"({forge_no}, 222)",
        "recipe_server_no": 222,
        "output_item_id": blueprint_id,
        "fixed_materials": [{"item_id": 1, "name": "Metal", "quantity": 3}],
        "material_groups": [],
        "currency": {"currency_id": 1, "name": "Energy Link", "quantity": 50},
        "craft_time_seconds": 2,
        "source_status": "mined-current-recipe-layer",
    }


class PhaseSixFixture:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        self.published = self.output / "published"
        (self.published / "web").mkdir(parents=True)
        (self.output / "last-run.json").write_text(json.dumps({"published": str(self.published)}), encoding="utf-8")

        # Two suits deliberately reuse blueprint 500. Their suit-qualified
        # canonical IDs must remain distinct and bare blueprint lookup ambiguous.
        self.set_one_piece = {
            "canonical_id": "ds-a-10-500",
            "suit_id": 10,
            "blueprint_id": 500,
            "name": "Shared Blueprint Helmet A",
            "slot_id": 21,
            "slot": "Helmet",
            "rarity": "Legendary",
            "quality_code": 4,
            "image_asset": "armor/a.png",
            "tiers": [tier(50001, 500, 1), tier(50002, 500, 2)],
            "crafting_recipes": [recipe(500, 7001)],
        }
        self.set_two_piece = {
            "canonical_id": "ds-a-20-500",
            "suit_id": 20,
            "blueprint_id": 500,
            "name": "Shared Blueprint Helmet B",
            "slot_id": 21,
            "slot": "Helmet",
            "rarity": "Legendary",
            "quality_code": 4,
            "image_asset": "armor/b.png",
            "tiers": [tier(60001, 500, 1), tier(60002, 500, 2)],
            "crafting_recipes": [recipe(500, 7002)],
        }
        self.key_one = {
            "canonical_id": "ds-ka-900",
            "blueprint_id": 900,
            "name": "Key Mask One",
            "slot_id": 27,
            "slot": "Mask",
            "rarity": "Legendary",
            "quality_code": 4,
            "image_asset": "armor/k1.png",
            "passive_skill_code": "AS900",
            "passive_skill_name": "Shared Key Skill",
            "buff_id": 9900,
            "key_effect": "Gain a proven effect.",
            "tiers": [tier(90001, 900, 1)],
            "crafting_recipes": [recipe(900, 7900)],
        }
        self.key_two = {
            "canonical_id": "ds-ka-901",
            "blueprint_id": 901,
            "name": "Key Mask Two",
            "slot_id": 27,
            "slot": "Mask",
            "rarity": "Legendary",
            "quality_code": 4,
            "image_asset": "armor/k2.png",
            # Deliberately shared handles: these must not merge identity.
            "passive_skill_code": "AS900",
            "passive_skill_name": "Shared Key Skill",
            "buff_id": 9900,
            "key_effect": "Gain the same proven effect.",
            "tiers": [tier(90101, 901, 1)],
            "crafting_recipes": [recipe(901, 7901)],
        }
        self.payload = {
            "schema": "dead-signal-armor",
            "schema_version": 2,
            "armor_sets": [
                {
                    "canonical_id": "ds-as-10",
                    "suit_id": 10,
                    "name": "Set Alpha",
                    "piece_count": 1,
                    "set_bonuses": [
                        {"pieces_required": 2, "description": "+10 HP", "attribute_code": "A0200", "attribute_value": 10, "buff_info": []},
                        {"pieces_required": 4, "description": "Owned buff", "attribute_code": "", "attribute_value": 0, "buff_info": [1234]},
                    ],
                    "pieces": [self.set_one_piece],
                    "verification": {"source_status": "mined-from-installed-game", "notes": []},
                },
                {
                    "canonical_id": "ds-as-20",
                    "suit_id": 20,
                    "name": "Set Beta",
                    "piece_count": 1,
                    "set_bonuses": [
                        {"pieces_required": 2, "description": "Text without typed owner", "attribute_code": "", "attribute_value": 0, "buff_info": []},
                    ],
                    "pieces": [self.set_two_piece],
                    "verification": {"source_status": "mined-from-installed-game", "notes": []},
                },
            ],
            "key_armor": [self.key_one, self.key_two],
            "crafting_material_groups": {},
        }
        self.write()

    def write(self):
        (self.published / "web" / "armor.json").write_text(json.dumps(self.payload), encoding="utf-8")

    def close(self):
        self.temp.cleanup()


class EvidenceGraphPhaseSixArmorTests(unittest.TestCase):
    def setUp(self):
        self.fixture = PhaseSixFixture()

    def tearDown(self):
        self.fixture.close()

    def test_contracts_are_typed_and_valid(self):
        self.assertEqual([], ARMOR_CONTRACT.validate())
        self.assertEqual([], ARMOR_SET_CONTRACT.validate())
        self.assertNotIn("id", ARMOR_CONTRACT.identity_seeds)
        self.assertNotIn("code", ARMOR_SET_CONTRACT.identity_seeds)

    def test_reused_blueprint_requires_suit_qualified_identity(self):
        adapter = ArmorAdapter(self.fixture.output)
        with self.assertRaisesRegex(ValueError, "Ambiguous armor identity"):
            adapter.graph("500")
        first = adapter.graph("ds-a-10-500")
        second = adapter.graph("ds-a-20-500")
        self.assertEqual("ds-a-10-500", first["entity"]["canonical_id"])
        self.assertEqual("ds-a-20-500", second["entity"]["canonical_id"])

    def test_set_piece_graph_has_exact_slot_membership_and_attributes(self):
        graph = ArmorAdapter(self.fixture.output).graph("ds-a-10-500")
        self.assertEqual([], validate_generalized_graph(graph))
        results = {row["claim_type"]: row["result"] for row in graph["claims"]}
        self.assertEqual("PROVEN", results["armor.equipment_owner"])
        self.assertEqual("PROVEN", results["armor.slot"])
        self.assertEqual("PROVEN", results["armor.rarity"])
        self.assertEqual("PROVEN", results["armor.base_attributes"])
        self.assertEqual("PROVEN", results["armor.crafting"])
        self.assertEqual("PARTIAL", results["armor.acquisition"])
        self.assertEqual("PROVEN", results["armor.set_membership"])
        self.assertEqual("NOT APPLICABLE", results["armor.key_armor_effect"])

    def test_key_armor_is_standalone_and_effect_chain_is_proven(self):
        graph = ArmorAdapter(self.fixture.output).graph("ds-ka-900")
        results = {row["claim_type"]: row["result"] for row in graph["claims"]}
        self.assertEqual("NOT APPLICABLE", results["armor.set_membership"])
        self.assertEqual("PROVEN", results["armor.key_armor_effect"])
        destinations = {row["destination"] for row in graph["edges"]}
        self.assertIn("passive-skill:AS900", destinations)
        self.assertIn("buff:9900", destinations)

    def test_shared_key_armor_handles_do_not_merge_identity(self):
        adapter = ArmorAdapter(self.fixture.output)
        one = adapter.graph("ds-ka-900")
        two = adapter.graph("ds-ka-901")
        self.assertNotEqual(one["entity"]["canonical_id"], two["entity"]["canonical_id"])
        one_effect = next(row for row in one["claims"] if row["claim_type"] == "armor.key_armor_effect")
        two_effect = next(row for row in two["claims"] if row["claim_type"] == "armor.key_armor_effect")
        self.assertEqual("AS900", one_effect["evidence"][0]["passive_skill_code"])
        self.assertEqual("AS900", two_effect["evidence"][0]["passive_skill_code"])

    def test_conflicting_tier_blueprint_ownership_fails_closed(self):
        self.fixture.set_one_piece["tiers"][1]["blueprint_id"] = 999
        self.fixture.write()
        graph = ArmorAdapter(self.fixture.output).graph("ds-a-10-500")
        owner = next(row for row in graph["claims"] if row["claim_type"] == "armor.equipment_owner")
        self.assertEqual("CONFLICT", owner["result"])
        self.assertEqual("CONFLICT", graph["assessment"]["result"])

    def test_set_thresholds_and_bonus_owners_are_exact(self):
        graph = ArmorSetAdapter(self.fixture.output).graph("10")
        self.assertEqual([], validate_generalized_graph(graph))
        results = {row["claim_type"]: row["result"] for row in graph["claims"]}
        self.assertEqual("PROVEN", results["armor_set.pieces"])
        self.assertEqual("PROVEN", results["armor_set.activation_thresholds"])
        self.assertEqual("PROVEN", results["armor_set.bonus_owners"])
        self.assertEqual("NOT APPLICABLE", results["armor_set.key_armor_membership"])

    def test_description_without_bonus_owner_is_partial_not_proven(self):
        graph = ArmorSetAdapter(self.fixture.output).graph("ds-as-20")
        bonus = next(row for row in graph["claims"] if row["claim_type"] == "armor_set.bonus_owners")
        self.assertEqual("PARTIAL", bonus["result"])

    def test_registry_indexes_sets_and_pieces_without_collapsing_reused_blueprints(self):
        graph = DeadSignalGeneralizedGraph(self.fixture.output)
        summary = graph.rebuild_entity_registry()
        self.assertIn("armor", summary["adapter_types"])
        self.assertIn("armor_set", summary["adapter_types"])
        pieces = graph.search_entities("500", entity_type="armor")
        self.assertEqual({"ds-a-10-500", "ds-a-20-500"}, {row["canonical_id"] for row in pieces})
        sets = graph.search_entities("Set Alpha", entity_type="armor_set")
        self.assertEqual(["ds-as-10"], [row["canonical_id"] for row in sets])
        self.assertEqual("armor", graph.armor_entity_graph("ds-ka-900")["entity"]["entity_type"])
        self.assertEqual("armor_set", graph.armor_set_entity_graph("ds-as-10")["entity"]["entity_type"])


if __name__ == "__main__":
    unittest.main()
