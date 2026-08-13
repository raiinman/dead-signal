import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "audit-armor-tier-evidence.py"
SPEC = importlib.util.spec_from_file_location("audit_armor_tier_evidence", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ArmorTierEvidenceTests(unittest.TestCase):
    @staticmethod
    def fixture():
        return {
            "schema": "dead-signal-armor",
            "armor_sets": [{
                "pieces": [{
                    "canonical_id": "ds-a-100-200",
                    "blueprint_id": 200,
                    "name": "Test Gloves",
                    "slot": "Gloves",
                    "tiers": [{"data_level": tier} for tier in (1, 2, 4, 5)],
                    "crafting_recipes": [
                        {"tier": tier, "forge_no": 3000 + tier, "output_item_id": 4000 + tier, "recipe_server_no": 222}
                        for tier in range(1, 6)
                    ],
                }],
            }],
            "key_armor": [],
        }

    def test_recipe_backed_missing_stat_row_is_explicit_and_not_synthesized(self):
        report = MODULE.audit(self.fixture())
        self.assertEqual(1, report["counts"]["records_with_missing_stat_rows"])
        self.assertEqual(0, report["counts"]["records_with_missing_recipe_rows"])
        self.assertEqual(1, report["counts"]["records_with_recipe_backed_stat_gaps"])
        gap = report["queues"]["recipe_backed_stat_gaps"][0]
        self.assertEqual("crafting-output-present-stat-row-missing", gap["classification"])
        self.assertEqual(3, gap["tiers"][0]["gear_tier"])
        self.assertEqual(4003, gap["tiers"][0]["output_item_id"])

    def test_missing_recipe_never_becomes_non_craftable(self):
        payload = self.fixture()
        payload["armor_sets"][0]["pieces"][0]["crafting_recipes"] = []
        report = MODULE.audit(payload)
        row = report["queues"]["missing_recipe_rows"][0]
        self.assertEqual("unresolved-recipe-evidence", row["classification"])
        self.assertNotIn("non-craftable", row["classification"])


if __name__ == "__main__":
    unittest.main()
