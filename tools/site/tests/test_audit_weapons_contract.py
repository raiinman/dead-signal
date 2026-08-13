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
    @staticmethod
    def matrix(base_start=100):
        return [
            {
                "gear_tier": tier,
                "tier_base_attack_at_1_star": base_start + tier,
                "blueprint_star_values": [
                    {
                        "blueprint_stars": star,
                        "preset_attack_ratio": 1.0 + 0.05 * (star - 1),
                        "base_attack": int((base_start + tier) * (1.0 + 0.05 * (star - 1))),
                    }
                    for star in (1, 2, 3)
                ],
            }
            for tier in range(1, 6)
        ]

    def fixture(self):
        tiers_with_recipe = [
            {"tier": tier, "recipe": {"forge_no": 100 + tier, "fixed_materials": []}}
            for tier in range(1, 6)
        ]
        tiers_missing = [
            {"tier": tier, "recipe": None if tier in {2, 4} else {"forge_no": 200 + tier}}
            for tier in range(1, 6)
        ]

        def progression(tiers, base):
            return {
                "gear_tiers": tiers,
                "tier_star_matrix": self.matrix(base),
                "formula_status": "proven-static-base-attack",
                "validation_issues": [],
            }

        weapons = [
            {
                "canonical_id": "ds-w-1",
                "blueprint_id": 1,
                "item_id": 11,
                "name": "Legendary Test",
                "rarity": "Legendary",
                "category": "Assault Rifle",
                "effect": None,
                "description": "",
                "verification": {
                    "description_status": "withheld-until-short-description-resolver-is-verified"
                },
                "image_asset": "asset.webp",
                "acquisition": {},
                "progression": progression(tiers_missing, 100),
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
                "description": "",
                "verification": {
                    "description_status": "withheld-until-short-description-resolver-is-verified"
                },
                "image_asset": "",
                "acquisition": {"hint": "Starter"},
                "progression": progression(tiers_with_recipe, 200),
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
                "description": "",
                "verification": {
                    "description_status": "withheld-until-short-description-resolver-is-verified"
                },
                "image_asset": "asset.webp",
                "acquisition": {"fragment_id": 123},
                "progression": progression(tiers_with_recipe, 300),
                "gun_profile": {"resolution_status": "unresolved", "gun_no": 60},
            },
        ]
        return {
            "schema": "dead-signal-weapons",
            "schema_version": 1,
            "generated_utc": "2026-08-13T00:00:00+00:00",
            "record_counts": {"weapons": len(weapons)},
            "weapons": weapons,
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

    def test_contract_integrity_passes_proven_fixture(self):
        report = MODULE.audit(self.fixture())
        self.assertEqual("PASS", report["contract_integrity"]["status"])
        self.assertEqual(0, report["counts"]["weapon_integrity_failures"])
        self.assertEqual(0, report["counts"]["contract_integrity_failures"])

    def test_contract_integrity_catches_count_duplicates_and_tier_shape(self):
        payload = self.fixture()
        payload["record_counts"]["weapons"] = 99
        payload["weapons"][1]["canonical_id"] = payload["weapons"][0]["canonical_id"]
        payload["weapons"][0]["progression"]["gear_tiers"] = payload["weapons"][0]["progression"]["gear_tiers"][:-1]

        report = MODULE.audit(payload)

        self.assertEqual("FAIL", report["contract_integrity"]["status"])
        self.assertEqual(2, report["counts"]["contract_integrity_failures"])
        self.assertGreaterEqual(report["counts"]["weapon_integrity_failures"], 1)
        issues = " ".join(report["contract_integrity"]["issues"])
        self.assertIn("record_counts.weapons", issues)
        self.assertIn("duplicate canonical weapon IDs", issues)

    def test_contract_integrity_recomputes_every_base_attack_cell(self):
        payload = self.fixture()
        payload["weapons"][0]["progression"]["tier_star_matrix"][4]["blueprint_star_values"][2]["base_attack"] += 1

        report = MODULE.audit(payload)

        self.assertEqual("FAIL", report["contract_integrity"]["status"])
        row = report["queues"]["integrity_failures"][0]
        self.assertTrue(any("Base Attack mismatch" in issue for issue in row["issues"]))

    def test_contract_integrity_catches_inconsistent_star_rows(self):
        payload = self.fixture()
        payload["weapons"][0]["progression"]["tier_star_matrix"][3]["blueprint_star_values"].pop()

        report = MODULE.audit(payload)

        row = report["queues"]["integrity_failures"][0]
        self.assertTrue(any("inconsistent legal Blueprint Star rows" in issue for issue in row["issues"]))

    def test_contract_integrity_catches_withheld_description_leak(self):
        payload = self.fixture()
        payload["weapons"][0]["description"] = "This must remain withheld."

        report = MODULE.audit(payload)

        row = report["queues"]["integrity_failures"][0]
        self.assertTrue(any("description text leaked" in issue for issue in row["issues"]))

    def test_contract_loader_rejects_wrong_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "weapons.json"
            path.write_text(json.dumps({"schema": "wrong", "weapons": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                MODULE.load_contract(path)


if __name__ == "__main__":
    unittest.main()
