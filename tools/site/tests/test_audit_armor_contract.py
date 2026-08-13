import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "audit-armor-contract.py"
SPEC = importlib.util.spec_from_file_location("audit_armor_contract", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ArmorContractAuditTests(unittest.TestCase):
    @staticmethod
    def tiers():
        return [{"data_level": tier, "hp": 100 + tier, "pollution_resistance": tier} for tier in range(1, 6)]

    @staticmethod
    def recipes():
        return [{"tier": tier, "forge_no": 1000 + tier} for tier in range(1, 6)]

    def fixture(self):
        def piece(suit_id, blueprint_id, name):
            return {
                "canonical_id": f"ds-a-{suit_id}-{blueprint_id}",
                "suit_id": suit_id,
                "blueprint_id": blueprint_id,
                "name": name,
                "slot": "Mask",
                "rarity": "Legendary",
                "image_asset": "mask.webp",
                "tiers": self.tiers(),
                "crafting_recipes": self.recipes(),
            }

        sets = [
            {"canonical_id": "ds-as-100", "suit_id": 100, "name": "Variant Base", "piece_count": 1, "set_bonuses": [], "pieces": [piece(100, 9001, "Base Mask")]},
            {"canonical_id": "ds-as-101", "suit_id": 101, "name": "Variant Cold", "piece_count": 1, "set_bonuses": [], "pieces": [piece(101, 9001, "Cold Mask")]},
        ]
        key = [{
            "canonical_id": "ds-ka-7001", "blueprint_id": 7001, "name": "Key Top", "slot": "Top",
            "rarity": "Legendary", "image_asset": "key.webp", "key_effect": "Resolved effect",
            "tiers": self.tiers(), "crafting_recipes": self.recipes(),
        }]
        return {
            "schema": "dead-signal-armor", "schema_version": 1,
            "generated_utc": "2026-08-13T00:00:00+00:00",
            "record_counts": {"armor_sets": 2, "set_pieces": 2, "key_armor": 1, "armor_pieces": 3},
            "armor_sets": sets, "key_armor": key,
        }

    def test_cross_suit_blueprint_reuse_is_variant_family_not_collision(self):
        report = MODULE.audit(self.fixture())
        self.assertEqual("PASS", report["identity_integrity"]["status"])
        self.assertEqual(1, report["counts"]["cross_suit_variant_families"])
        family = report["queues"]["cross_suit_variant_families"][0]
        self.assertEqual(9001, family["blueprint_id"])
        self.assertEqual([100, 101], family["suit_ids"])
        self.assertEqual("expected-cross-suit-variant-family", family["classification"])

    def test_piece_must_match_parent_suit(self):
        payload = self.fixture()
        payload["armor_sets"][0]["pieces"][0]["suit_id"] = 999
        report = MODULE.audit(payload)
        self.assertEqual("FAIL", report["identity_integrity"]["status"])
        issues = report["queues"]["integrity_failures"][0]["issues"]
        self.assertTrue(any("does not match parent suit_id" in issue for issue in issues))

    def test_old_blueprint_only_piece_id_fails_closed(self):
        payload = self.fixture()
        payload["armor_sets"][0]["pieces"][0]["canonical_id"] = "ds-a-9001"
        report = MODULE.audit(payload)
        self.assertEqual("FAIL", report["identity_integrity"]["status"])
        issues = report["queues"]["integrity_failures"][0]["issues"]
        self.assertTrue(any("variant-aware canonical piece ID" in issue for issue in issues))

    def test_declared_count_and_duplicate_ids_fail(self):
        payload = self.fixture()
        payload["record_counts"]["armor_pieces"] = 99
        payload["armor_sets"][1]["pieces"][0]["canonical_id"] = "ds-a-100-9001"
        report = MODULE.audit(payload)
        self.assertEqual("FAIL", report["identity_integrity"]["status"])
        self.assertEqual(2, report["counts"]["contract_integrity_failures"])

    def test_missing_tier_and_recipe_evidence_remain_unresolved(self):
        payload = self.fixture()
        piece = payload["armor_sets"][0]["pieces"][0]
        piece["tiers"].pop()
        piece["crafting_recipes"] = piece["crafting_recipes"][:3]
        report = MODULE.audit(payload)
        self.assertEqual("FAIL", report["identity_integrity"]["status"])
        recipe = report["queues"]["missing_tier_recipes"][0]
        self.assertEqual([4, 5], recipe["missing_gear_tiers"])
        self.assertEqual("unresolved-recipe-evidence", recipe["classification"])
        self.assertNotIn("non-craftable", recipe["classification"])

    def test_key_armor_effect_and_art_gaps_are_reported(self):
        payload = self.fixture()
        payload["key_armor"][0]["key_effect"] = ""
        payload["key_armor"][0]["image_asset"] = ""
        report = MODULE.audit(payload)
        self.assertEqual(1, report["counts"]["key_armor_without_effect"])
        self.assertEqual(1, report["counts"]["records_without_artwork"])

    def test_loader_rejects_wrong_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "armor.json"
            path.write_text(json.dumps({"schema": "wrong", "armor_sets": [], "key_armor": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                MODULE.load_contract(path)


if __name__ == "__main__":
    unittest.main()
