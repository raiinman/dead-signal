import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "audit-weapons-contract.py"
SPEC = importlib.util.spec_from_file_location("audit_weapons_contract", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class WeaponsContractAuditTests(unittest.TestCase):
    def fixture(self):
        tiers_with_recipe = [
            {"tier": tier, "recipe": {"forge_no": 100 + tier, "fixed_materials": []}}
            for tier in range(1, 6)
        ]
        tiers_missing = [
            {"tier": tier, "recipe": None if tier in {2, 4} else {"forge_no": 200 + tier}}
            for tier in range(1, 6)
        ]
        return {
            "schema": "dead-signal-weapons",
            "schema_version": 1,
            "generated_utc": "2026-08-13T00:00:00+00:00",
            "weapons": [
                {
                    "canonical_id": "ds-w-1",
                    "blueprint_id": 1,
                    "item_id": 11,
                    "name": "Legendary Test",
                    "rarity": "Legendary",
                    "category": "Assault Rifle",
                    "effect": None,
                    "image_asset": "asset.webp",
                    "acquisition": {},
                    "progression": {"gear_tiers": tiers_missing},
                    "gun_profile": {
                        "resolution_status": "resolved",
                        "gun_no": 50,
                        "linked_ids": {"gun_skill_no": 999},
                    },
                },
                {
                    "canonical_id": "ds-w-2",
                    "blueprint_id": 2,
                    "item_id": 22,
                    "name": "Common Test",
                    "rarity": "Common",
                    "category": "Melee",
                    "effect": None,
                    "image_asset": "",
                    "acquisition": {"hint": "Starter"},
                    "progression": {"gear_tiers": tiers_with_recipe},
                    "gun_profile": {},
                },
                {
                    "canonical_id": "ds-w-3",
                    "blueprint_id": 3,
                    "item_id": 33,
                    "name": "Resolved Test",
                    "rarity": "Epic",
                    "category": "Pistol",
                    "effect": {"name": "Effect", "description": "Verified"},
                    "image_asset": "asset.webp",
                    "acquisition": {"fragment_id": 123},
                    "progression": {"gear_tiers": tiers_with_recipe},
                    "gun_profile": {"resolution_status": "unresolved", "gun_no": 60},
                },
            ],
        }

    def test_audit_separates_research_required_from_common_absence(self):
        report = MODULE.audit(self.fixture())
        self.assertEqual(1, report["counts"]["unresolved_non_common_effects"])
        self.assertEqual(1, report["counts"]["candidate_common_no_effect"])
        row = report["queues"]["unresolved_non_common_effects"][0]
        self.assertEqual("Legendary Test", row["name"])
        self.assertEqual(999, row["linked_ids"]["gun_skill_no"])

    def test_missing_recipe_is_never_called_non_craftable(self):
        report = MODULE.audit(self.fixture())
        row = report["queues"]["missing_tier_recipes"][0]
        self.assertEqual([2, 4], row["missing_gear_tiers"])
        self.assertEqual("unresolved-recipe-evidence", row["classification"])
        self.assertNotIn("non-craftable", row["classification"])

    def test_other_exact_queues_are_reported(self):
        report = MODULE.audit(self.fixture())
        self.assertEqual(1, report["counts"]["weapons_without_acquisition_evidence"])
        self.assertEqual(1, report["counts"]["weapons_without_artwork"])
        self.assertEqual(1, report["counts"]["unresolved_ranged_profiles"])
        self.assertEqual("Resolved Test", report["queues"]["unresolved_ranged_profiles"][0]["name"])

    def test_contract_loader_rejects_wrong_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "weapons.json"
            path.write_text(json.dumps({"schema": "wrong", "weapons": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                MODULE.load_contract(path)


if __name__ == "__main__":
    unittest.main()
