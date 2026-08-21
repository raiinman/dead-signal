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

from dead_signal_cradle_adapter import CRADLE_CONTRACT, CradleAdapter  # noqa: E402
from dead_signal_evidence_contracts import validate_generalized_graph  # noqa: E402
from dead_signal_generalized_graph import DeadSignalGeneralizedGraph  # noqa: E402


def weapon(canonical_id: str, item_type: int, subtype: int, *, compatible=(), incompatible=(), unresolved=()):
    return {
        "canonical_id": canonical_id,
        "name": canonical_id,
        "compatibility": {
            "cradle": {
                "item_selector": {"item_type": item_type, "item_sub_type": subtype},
                "compatible_exact_ids": list(compatible),
                "incompatible_exact_ids": list(incompatible),
                "unresolved_ids": list(unresolved),
            }
        },
    }


class Phase8CradleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        published = self.output / "published"
        (published / "web").mkdir(parents=True)
        (published / "data").mkdir(parents=True)
        (published / "reports").mkdir(parents=True)
        (self.output / "last-run.json").write_text(
            json.dumps({"published": str(published)}), encoding="utf-8"
        )

        web = {
            "schema": "dead-signal-cradles",
            "families": [
                {
                    "canonical_id": "ds-cradle-family-active",
                    "variants": [
                        {
                            "id": 101,
                            "canonical_id": "ds-cradle-101",
                            "name": "Active Selector Cradle",
                            "buff_id": 5001,
                            "active_config_keys": ["7001"],
                            "active_season_ids": ["42"],
                            "image_reference": "icons/101.png",
                        }
                    ],
                },
                {
                    "canonical_id": "ds-cradle-family-inactive",
                    "variants": [
                        {
                            "id": 999,
                            "canonical_id": "ds-cradle-999",
                            "name": "Legacy Inactive Cradle",
                            "buff_id": 5999,
                            "active_config_keys": [],
                            "active_season_ids": [],
                        }
                    ],
                },
            ],
        }
        data = {
            "cradles": [
                {
                    "id": 101,
                    "name": "Active Selector Cradle",
                    "buff_id": 5001,
                    "image_reference": "icons/101.png",
                },
                {
                    "id": 999,
                    "name": "Legacy Inactive Cradle",
                    "buff_id": 5999,
                },
            ]
        }
        weapons = {
            "weapons": [
                weapon("ds-w-a", 1, 10, compatible=(101,)),
                weapon("ds-w-b", 1, 20, incompatible=(101,)),
            ]
        }
        report = {
            "selectors": [
                {
                    "entry_id": 101,
                    "buff_id": 5001,
                    "state": "weapon-selector-exact",
                    "positive_item_selectors": [{"item_type": 1, "item_sub_type": 10}],
                    "visited_buff_ids": [5001, 5002],
                    "logic_trees": ["cradle_test_tree"],
                    "unresolved_raw_selectors": [],
                }
            ]
        }
        for path, payload in (
            (published / "web" / "cradles.json", web),
            (published / "data" / "cradles.json", data),
            (published / "data" / "weapons.json", weapons),
            (published / "reports" / "weapon-cradle-applicability.json", report),
        ):
            path.write_text(json.dumps(payload), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def claim(self, graph, kind):
        return next(row for row in graph["claims"] if row["claim_type"] == kind)

    def test_contract_is_valid_and_has_no_generic_identity_seed(self):
        self.assertEqual([], CRADLE_CONTRACT.validate())
        self.assertNotIn("id", CRADLE_CONTRACT.identity_seeds)

    def test_active_cradle_graph_validates_and_directions_agree(self):
        graph = CradleAdapter(self.output).graph("101")
        self.assertEqual([], validate_generalized_graph(graph))
        self.assertEqual("PROVEN", self.claim(graph, "cradle.weapon_direction_consistency")["result"])
        rel = graph["compatibility"]["weapon_relationships"]
        self.assertEqual(["ds-w-a"], rel["compatible"])
        self.assertEqual(["ds-w-b"], rel["incompatible"])
        self.assertTrue(graph["compatibility"]["scenario_gate_separate"])

    def test_inactive_legacy_cradle_is_rejected(self):
        with self.assertRaises(KeyError):
            CradleAdapter(self.output).graph("999")

    def test_registry_indexes_only_active_cradles(self):
        engine = DeadSignalGeneralizedGraph(self.output)
        summary = engine.rebuild_entity_registry()
        self.assertEqual(1, summary["by_entity_type"]["cradle"])
        rows = engine.search_entities("", entity_type="cradle")
        self.assertEqual(["ds-cradle-101"], [row["canonical_id"] for row in rows])

    def test_poisoned_weapon_side_relationship_becomes_conflict(self):
        path = self.output / "published" / "data" / "weapons.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["weapons"][0]["compatibility"]["cradle"]["compatible_exact_ids"] = []
        payload["weapons"][0]["compatibility"]["cradle"]["incompatible_exact_ids"] = [101]
        path.write_text(json.dumps(payload), encoding="utf-8")
        graph = CradleAdapter(self.output).graph(101)
        claim = self.claim(graph, "cradle.weapon_direction_consistency")
        self.assertEqual("CONFLICT", claim["result"])
        self.assertTrue(claim["conflicts"])

    def test_scenario_membership_is_not_current_scenario_proof(self):
        graph = CradleAdapter(self.output).graph(101)
        claim = self.claim(graph, "cradle.scenario_availability")
        self.assertEqual("PARTIAL", claim["result"])
        self.assertIn("current runtime scenario/config selection", claim["missing"])

    def test_slot_fails_closed_until_nested_position_is_retained(self):
        graph = CradleAdapter(self.output).graph(101)
        claim = self.claim(graph, "cradle.slot")
        self.assertEqual("UNRESOLVED", claim["result"])
        self.assertTrue(claim["missing"])

    def test_raw_selector_stays_unresolved(self):
        report_path = self.output / "published" / "reports" / "weapon-cradle-applicability.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["selectors"][0]["state"] = "weapon-relation-unresolved"
        report["selectors"][0]["positive_item_selectors"] = []
        report["selectors"][0]["unresolved_raw_selectors"] = [
            {"fields": {"keyword": 123}}
        ]
        report_path.write_text(json.dumps(report), encoding="utf-8")
        # Make weapon-side projection agree with unresolved state.
        weapons_path = self.output / "published" / "data" / "weapons.json"
        weapons = json.loads(weapons_path.read_text(encoding="utf-8"))
        for row in weapons["weapons"]:
            block = row["compatibility"]["cradle"]
            block["compatible_exact_ids"] = []
            block["incompatible_exact_ids"] = []
            block["unresolved_ids"] = [101]
        weapons_path.write_text(json.dumps(weapons), encoding="utf-8")
        graph = CradleAdapter(self.output).graph(101)
        self.assertEqual("UNRESOLVED", self.claim(graph, "cradle.weapon_applicability")["result"])
        self.assertEqual("PROVEN", self.claim(graph, "cradle.weapon_direction_consistency")["result"])

    def test_no_weapon_selector_is_not_applicable_not_incompatible(self):
        report_path = self.output / "published" / "reports" / "weapon-cradle-applicability.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["selectors"][0]["state"] = "not-weapon-selected"
        report["selectors"][0]["positive_item_selectors"] = []
        report_path.write_text(json.dumps(report), encoding="utf-8")
        weapons_path = self.output / "published" / "data" / "weapons.json"
        weapons = json.loads(weapons_path.read_text(encoding="utf-8"))
        for row in weapons["weapons"]:
            block = row["compatibility"]["cradle"]
            block["compatible_exact_ids"] = []
            block["incompatible_exact_ids"] = []
            block["unresolved_ids"] = []
        weapons_path.write_text(json.dumps(weapons), encoding="utf-8")
        graph = CradleAdapter(self.output).graph(101)
        self.assertEqual("NOT APPLICABLE", self.claim(graph, "cradle.weapon_applicability")["result"])
        self.assertEqual(["ds-w-a", "ds-w-b"], graph["compatibility"]["weapon_relationships"]["not_applicable"])


if __name__ == "__main__":
    unittest.main()
