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

from dead_signal_calibration_adapter import CALIBRATION_CONTRACT, CalibrationAdapter  # noqa: E402
from dead_signal_calibration_relations import (  # noqa: E402
    calibration_system_classification,
    calibration_weapon_relation,
    exact_print_owner,
)
from dead_signal_evidence_contracts import validate_generalized_graph  # noqa: E402
from dead_signal_generalized_graph import DeadSignalGeneralizedGraph  # noqa: E402


class PhaseFiveFixture:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        self.published = self.output / "published"
        (self.published / "web").mkdir(parents=True)
        (self.published / "data").mkdir(parents=True)
        (self.output / "last-run.json").write_text(
            json.dumps({"published": str(self.published)}), encoding="utf-8"
        )

        self.web_variant = {
            "id": 9001,
            "item_id": 9001,
            "name": "Precision Calibration",
            "rarity": "Epic",
            "quality_code": 4,
            "gain_path": "Found in Securement Silo rewards.",
            "image_reference": "icons/cal-9001.png",
            "group_id": 77,
            "style_code": 12,
            "weapon_type_codes": [1],
            "is_valid": True,
            "season_state": 1,
            "buff_id": 500,
            "roll_range": {
                "raw_minimum": 0.7,
                "raw_maximum": 1.0,
                "minimum_percent": 70.0,
                "maximum_percent": 100.0,
                "source_table": "game_common/data/gun_correct_print_data.json",
                "source_field": "affix_val_range",
                "semantics_status": "range-proven-combat-application-under-investigation",
            },
            "affix_ids_weight": [[101, 10], [102, 5]],
            "affixes": [{"affix_id": 101}, {"affix_id": 102}],
        }
        self.unresolved_variant = {
            "id": 9002,
            "item_id": 9002,
            "name": "Ownerless Calibration Item",
            "rarity": "Rare",
            "quality_code": 3,
            "gain_path": "",
            "group_id": 0,
            "style_code": 0,
            "weapon_type_codes": [],
            "is_valid": True,
            "roll_range": {},
            "affix_ids_weight": [],
            "affixes": [],
        }
        self.write_web()

        self.data_current = {
            "id": 9001,
            "item_id": 9001,
            "name": "Precision Calibration",
            "quality": "Epic",
            "quality_code": 4,
            "gain_path": "Found in Securement Silo rewards.",
            "image_reference": "icons/cal-9001.png",
            "weapon_type_codes": [1],
            "calibration_style_code": 12,
            "group_id": 77,
            "buff_id": 500,
            "season_state": 1,
            "is_valid": True,
            "affix_val_range": [0.7, 1.0],
            "affix_ids_weight": [[101, 10], [102, 5]],
            "calibration_roll_range": self.web_variant["roll_range"],
            "affix_ids": [101, 102],
            "affixes": [{"affix_id": 101, "name": "A"}, {"affix_id": 102, "name": "B"}],
        }
        self.data_unresolved = {
            "id": 9002,
            "item_id": 9002,
            "name": "Ownerless Calibration Item",
            "quality": "Rare",
            "quality_code": 3,
            "gain_path": "",
            "weapon_type_codes": [],
            "calibration_style_code": 0,
            "group_id": 0,
            "buff_id": None,
            "season_state": None,
            "is_valid": True,
            "affix_val_range": [],
            "affix_ids_weight": [],
            "calibration_roll_range": {},
            "affix_ids": [],
            "affixes": [],
        }
        self.write_calibrations()

        self.weapons = [
            {
                "canonical_id": "ds-w-ar",
                "item_id": 1,
                "name": "AR",
                "category": "Assault Rifle",
                "weapon_type_code": 1,
                "compatibility": {"calibration": {
                    "compatible_ids": [9001], "incompatible_ids": [],
                    "unresolved_ids": [], "not_applicable_ids": [],
                }},
            },
            {
                "canonical_id": "ds-w-pistol",
                "item_id": 2,
                "name": "Pistol",
                "category": "Pistol",
                "weapon_type_code": 2,
                "compatibility": {"calibration": {
                    "compatible_ids": [], "incompatible_ids": [9001],
                    "unresolved_ids": [], "not_applicable_ids": [],
                }},
            },
            {
                "canonical_id": "ds-w-melee",
                "item_id": 3,
                "name": "Melee",
                "category": "Melee",
                "weapon_type_code": 0,
                "compatibility": {"calibration": {
                    "compatible_ids": [], "incompatible_ids": [],
                    "unresolved_ids": [], "not_applicable_ids": [9001],
                }},
            },
        ]
        self.write_weapons()

    def write_web(self):
        payload = {
            "schema": "dead-signal-calibrations",
            "schema_version": 1,
            "families": [
                {
                    "canonical_id": "ds-cal-77",
                    "family_key": "77",
                    "name": "Precision Calibration",
                    "variant_count": 1,
                    "variants": [self.web_variant],
                },
                {
                    "canonical_id": "ds-cal-item-9002",
                    "family_key": "item-9002",
                    "name": "Ownerless Calibration Item",
                    "variant_count": 1,
                    "variants": [self.unresolved_variant],
                },
            ],
        }
        (self.published / "web" / "calibrations.json").write_text(json.dumps(payload), encoding="utf-8")

    def write_calibrations(self):
        (self.published / "data" / "calibrations.json").write_text(
            json.dumps({"calibrations": [self.data_current, self.data_unresolved]}), encoding="utf-8"
        )

    def write_weapons(self):
        (self.published / "data" / "weapons.json").write_text(
            json.dumps({"weapons": self.weapons}), encoding="utf-8"
        )

    def close(self):
        self.temp.cleanup()


class EvidenceGraphPhaseFiveCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = PhaseFiveFixture()

    def tearDown(self):
        self.fixture.close()

    def test_contract_is_typed_and_blocks_generic_identity(self):
        self.assertEqual([], CALIBRATION_CONTRACT.validate())
        self.assertNotIn("id", CALIBRATION_CONTRACT.identity_seeds)
        self.assertNotIn("code", CALIBRATION_CONTRACT.allowed_outbound_fields)
        self.assertIn("calibration.secondary_attribute_pool", CALIBRATION_CONTRACT.supported_claims)

    def test_current_owner_and_four_state_relation_are_exact(self):
        current = self.fixture.data_current
        self.assertTrue(exact_print_owner(current))
        self.assertEqual("current-calibration-blueprint", calibration_system_classification(current))
        self.assertEqual("compatible", calibration_weapon_relation(self.fixture.weapons[0], current))
        self.assertEqual("incompatible", calibration_weapon_relation(self.fixture.weapons[1], current))
        self.assertEqual("not-applicable", calibration_weapon_relation(self.fixture.weapons[2], current))

    def test_ownerless_subtype_item_is_not_called_legacy(self):
        unresolved = self.fixture.data_unresolved
        self.assertFalse(exact_print_owner(unresolved))
        self.assertEqual("unresolved", calibration_system_classification(unresolved))
        self.assertEqual("unresolved", calibration_weapon_relation(self.fixture.weapons[0], unresolved))
        graph = CalibrationAdapter(self.fixture.output).graph("9002")
        classification = next(
            row for row in graph["claims"] if row["claim_type"] == "calibration.system_classification"
        )
        self.assertEqual("UNRESOLVED", classification["result"])
        self.assertFalse(graph["compatibility"]["legacy_gear_calibration_mixed"])

    def test_graph_validates_and_forward_reverse_agree(self):
        graph = CalibrationAdapter(self.fixture.output).graph("ds-cal-var-9001")
        self.assertEqual([], validate_generalized_graph(graph))
        self.assertEqual("calibration", graph["entity"]["entity_type"])
        self.assertTrue(graph["compatibility"]["forward_reverse_agreement"])
        relationships = [row for row in graph["claims"] if row["claim_type"] == "calibration.weapon_relationship"]
        by_weapon = {
            row["subject"]["relationship"]["weapon"]: row["subject"]["relationship"]["state"]
            for row in relationships
        }
        self.assertEqual("compatible", by_weapon["ds-w-ar"])
        self.assertEqual("incompatible", by_weapon["ds-w-pistol"])
        self.assertEqual("not-applicable", by_weapon["ds-w-melee"])

    def test_poisoned_reverse_relationship_becomes_conflict(self):
        self.fixture.weapons[1]["compatibility"]["calibration"]["incompatible_ids"] = []
        self.fixture.weapons[1]["compatibility"]["calibration"]["compatible_ids"] = [9001]
        self.fixture.write_weapons()
        graph = CalibrationAdapter(self.fixture.output).graph(9001)
        self.assertFalse(graph["compatibility"]["forward_reverse_agreement"])
        self.assertEqual("CONFLICT", graph["assessment"]["result"])
        consistency = next(
            row for row in graph["claims"] if row["claim_type"] == "calibration.compatibility_consistency"
        )
        self.assertEqual("CONFLICT", consistency["result"])

    def test_attack_range_keeps_combat_semantics_partial(self):
        graph = CalibrationAdapter(self.fixture.output).graph(9001)
        claim = next(row for row in graph["claims"] if row["claim_type"] == "calibration.attack_range")
        self.assertEqual("PARTIAL", claim["result"])
        self.assertIn("combat application semantics", claim["missing"])
        self.assertEqual(0.7, claim["evidence"][0]["raw_minimum"])
        self.assertEqual(1.0, claim["evidence"][0]["raw_maximum"])

    def test_secondary_pool_preserves_raw_weights_without_probability_inference(self):
        graph = CalibrationAdapter(self.fixture.output).graph(9001)
        claim = next(
            row for row in graph["claims"] if row["claim_type"] == "calibration.secondary_attribute_pool"
        )
        self.assertEqual("PROVEN", claim["result"])
        evidence = claim["evidence"][0]
        self.assertEqual([[101, 10], [102, 5]], evidence["raw_weights"])
        self.assertIn("not inferred", evidence["probability_policy"])
        self.assertNotIn("probabilities", evidence)

    def test_registry_indexes_exact_variants_not_family_as_identity(self):
        graph = DeadSignalGeneralizedGraph(self.fixture.output)
        summary = graph.rebuild_entity_registry()
        self.assertIn("calibration", summary["adapter_types"])
        self.assertEqual(2, summary["by_entity_type"]["calibration"])
        rows = graph.search_entities("9001", entity_type="calibration")
        self.assertEqual(["ds-cal-var-9001"], [row["canonical_id"] for row in rows])
        payload = graph.calibration_entity_graph("ds-cal-var-9001")
        self.assertEqual("calibration", payload["entity"]["entity_type"])


if __name__ == "__main__":
    unittest.main()
