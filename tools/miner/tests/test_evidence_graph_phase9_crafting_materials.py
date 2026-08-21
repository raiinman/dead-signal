from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
EXTRACTOR = SRC / "extractor"
for root in (SRC, EXTRACTOR):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from dead_signal_crafting_adapters import MaterialAdapter, RecipeAdapter
from dead_signal_generalized_graph import DeadSignalGeneralizedGraph
from normalize_crafting import write_outputs


def _write_table(root: Path, relative: str, data: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"data": data}), encoding="utf-8")


class Phase9CraftingMaterialsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.root / "base"
        self.current = self.root / "current"
        self.output = self.root / "output"
        self.published = self.output / "published"
        for layer, archive in ((self.base, "base.npk"), (self.current, "current.npk")):
            layer.mkdir(parents=True, exist_ok=True)
            (layer / "snapshot.json").write_text(json.dumps({"archive": archive, "archive_sha256": archive, "tables": []}), encoding="utf-8")

        items = {
            "500": {"name": "Iron", "quality": 1, "icon": "iron.png"},
            "501": {"name": "Fiber", "quality": 2, "icon": "fiber.png", "gain_path": "Found in the wild"},
            "502": {"name": "Special Fiber", "quality": 3, "icon": "special.png"},
            # Deliberate scalar collision: these IDs also exist as choice-group identities.
            "7000": {"name": "Fake Group-Like Item", "quality": 1},
            "777": {"name": "Collision Item", "quality": 1},
            "900": {"name": "Output A", "quality": 3},
            "901": {"name": "Output B", "quality": 3},
            "902": {"name": "Output C", "quality": 3},
        }
        _write_table(self.current, "game_common/data/item_data.json", items)
        _write_table(self.base, "game_common/data/money_material_data.json", {
            "1": {"name": "Energy Link", "item_icon": "money.png"},
        })
        _write_table(self.base, "game_common/data/forge_choice_material_data.json", {
            "a": {"identity": 7000, "item_id": 501, "item_num": 4},
            "b": {"identity": 777, "item_id": 502, "item_num": 1},
        })
        _write_table(self.base, "game_common/data/forge_data.json", {
            "(100, 222)": {
                "item_no": 900,
                "cost_item_list": [500, 7000],
                "cost_num_list": [2, 3],
                "cost_money_no": 1,
                "cost_money_num": 10,
                "seconds": 5,
            },
            "(100, 333)": {
                "item_no": 901,
                "cost_item_list": [500],
                "cost_num_list": [1],
                "seconds": 7,
            },
            "(200, 222)": {
                "item_no": 902,
                "cost_item_list": [777],
                "cost_num_list": [2],
                "seconds": 1,
            },
        })
        _write_table(self.current, "client_data/forge_formula_map_data.json", {
            "ITEM_NO_TO_FORGE_NO_MAP": {
                "900": [100, 222],
                # Deliberate disagreement: recipe 100:333 says output 901.
                "999": [100, 333],
            }
        })

        write_outputs(self.base, self.current, self.published / "data")
        self.output.mkdir(parents=True, exist_ok=True)
        (self.output / "last-run.json").write_text(json.dumps({"published": str(self.published)}), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def _crafting(self):
        return json.loads((self.published / "data" / "crafting.json").read_text(encoding="utf-8"))

    def _materials(self):
        return json.loads((self.published / "data" / "materials.json").read_text(encoding="utf-8"))

    def test_choice_group_namespace_wins_over_same_numeric_item_id(self):
        recipes = {row["canonical_id"]: row for row in self._crafting()["recipes"]}
        recipe = recipes["ds-recipe-100-222"]
        self.assertEqual([500], [row["item_id"] for row in recipe["fixed_materials"]])
        self.assertEqual([7000], [row["group_id"] for row in recipe["selectable_material_groups"]])
        self.assertEqual(12, recipe["selectable_material_groups"][0]["options"][0]["recipe_quantity"])

        collision = recipes["ds-recipe-200-222"]
        self.assertEqual([], collision["fixed_materials"])
        self.assertEqual([777], [row["group_id"] for row in collision["selectable_material_groups"]])

    def test_formula_map_disagreement_is_conflict_not_overwrite(self):
        recipes = {row["canonical_id"]: row for row in self._crafting()["recipes"]}
        self.assertEqual("PROVEN", recipes["ds-recipe-100-222"]["formula_map_state"])
        self.assertEqual("CONFLICT", recipes["ds-recipe-100-333"]["formula_map_state"])
        self.assertEqual(901, recipes["ds-recipe-100-333"]["output_item_id"])
        self.assertEqual([999], recipes["ds-recipe-100-333"]["formula_map_output_item_ids"])

    def test_bare_forge_number_is_ambiguous_across_server_variants(self):
        adapter = RecipeAdapter(self.output)
        with self.assertRaises(ValueError):
            adapter.graph(100)
        graph = adapter.graph("100:222")
        self.assertEqual("ds-recipe-100-222", graph["entity"]["canonical_id"])

    def test_recipe_graph_preserves_fixed_group_currency_and_time_claims(self):
        graph = RecipeAdapter(self.output).graph("100:222")
        claims = {row["claim_type"]: row for row in graph["claims"]}
        self.assertEqual("PROVEN", claims["recipe.output_item"]["result"])
        self.assertEqual("PROVEN", claims["recipe.fixed_materials"]["result"])
        self.assertEqual("PROVEN", claims["recipe.selectable_material_groups"]["result"])
        self.assertEqual("PROVEN", claims["recipe.currency_cost"]["result"])
        self.assertEqual("PROVEN", claims["recipe.craft_time"]["result"])

    def test_conflicting_recipe_graph_fails_closed_at_assessment(self):
        graph = RecipeAdapter(self.output).graph("100:333")
        claims = {row["claim_type"]: row for row in graph["claims"]}
        self.assertEqual("CONFLICT", claims["recipe.formula_map_consistency"]["result"])
        self.assertEqual("CONFLICT", graph["assessment"]["result"])

    def test_material_reverse_usage_is_typed_and_gain_path_is_not_proven_acquisition(self):
        graph = MaterialAdapter(self.output).graph(501)
        claims = {row["claim_type"]: row for row in graph["claims"]}
        self.assertEqual("PROVEN", claims["material.recipe_usage"]["result"])
        self.assertEqual("PROVEN", claims["material.choice_group_membership"]["result"])
        self.assertEqual("PARTIAL", claims["material.acquisition"]["result"])
        usage = {(row["recipe_id"], row["mode"]) for row in claims["material.recipe_usage"]["evidence"]}
        self.assertIn(("ds-recipe-100-222", "selectable"), usage)

    def test_material_dataset_excludes_collision_ids_that_were_only_group_ids(self):
        material_ids = {row["item_id"] for row in self._materials()["materials"]}
        self.assertIn(500, material_ids)
        self.assertIn(501, material_ids)
        self.assertIn(502, material_ids)
        self.assertNotIn(7000, material_ids)
        self.assertNotIn(777, material_ids)

    def test_registry_routes_recipe_and_material_without_compact_web_files(self):
        graph = DeadSignalGeneralizedGraph(self.output)
        summary = graph.rebuild_entity_registry()
        self.assertEqual(3, summary["by_entity_type"]["recipe"])
        self.assertEqual(3, summary["by_entity_type"]["material"])
        recipe = graph.search_entities("Output A", entity_type="recipe")
        material = graph.search_entities("Fiber", entity_type="material")
        self.assertEqual("ds-recipe-100-222", recipe[0]["canonical_id"])
        self.assertTrue(any(row["canonical_id"] == "ds-material-501" for row in material))


if __name__ == "__main__":
    unittest.main()
