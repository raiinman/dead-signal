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

from dead_signal_attachment_adapter import ATTACHMENT_CONTRACT, AttachmentAdapter  # noqa: E402
from dead_signal_attachment_relations import attachment_weapon_relation  # noqa: E402
from dead_signal_domain_adapters import validate_adapter_contract  # noqa: E402
from dead_signal_evidence_contracts import validate_generalized_graph  # noqa: E402
from dead_signal_generalized_graph import DeadSignalGeneralizedGraph  # noqa: E402


class PhaseFourFixture:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        self.published = self.output / "published"
        (self.published / "web").mkdir(parents=True)
        (self.published / "data").mkdir(parents=True)
        (self.output / "last-run.json").write_text(
            json.dumps({"published": str(self.published)}), encoding="utf-8"
        )

        self.web_attachment = {
            "canonical_id": "ds-att-acc-1",
            "accessory_code": "acc-1",
            "item_id": 100,
            "name": "Exact Scope",
            "attachment_type": "Sight",
            "rarity": "Epic",
            "description": "Can be equipped on Assault Rifles.",
            "gain_path": "Found in a weapon crate.",
            "image_reference": "icons/acc-1.png",
        }
        (self.published / "web" / "attachments.json").write_text(
            json.dumps({"attachments": [self.web_attachment]}), encoding="utf-8"
        )

        self.data_attachment = {
            **self.web_attachment,
            "id": "acc-1",
            "subtype_code": 61,
            "affix_code": "affix-1",
            "effects": "+Accuracy",
            "attribute_codes": [123],
            "passive_buff_id": 0,
            "compatible_weapon_item_ids": [],
            "compatibility_evidence": {
                "status": "direct-localized-installed-game-text",
                "text": "Can be equipped on Assault Rifles",
                "all_weapons": False,
                "compatible_weapon_categories": ["Assault Rifle"],
                "named_weapon_text_present": False,
                "owner_trace": {
                    "state": "direct-installed-text-owner",
                    "source_table": "game_common/data/gun_accessory_base_params_data.json",
                    "record_id": "acc-1",
                    "typed_selectors": {},
                },
            },
        }
        (self.published / "data" / "attachments.json").write_text(
            json.dumps({"attachments": [self.data_attachment]}), encoding="utf-8"
        )

        self.weapons = [
            {
                "canonical_id": "ds-w-ar",
                "item_id": 1,
                "name": "AR",
                "category": "Assault Rifle",
                "compatibility": {"attachment": {
                    "compatible_ids": ["acc-1"],
                    "incompatible_ids": [],
                    "unresolved_ids": [],
                    "not_applicable_ids": [],
                }},
            },
            {
                "canonical_id": "ds-w-pistol",
                "item_id": 2,
                "name": "Pistol",
                "category": "Pistol",
                "compatibility": {"attachment": {
                    "compatible_ids": [],
                    "incompatible_ids": ["acc-1"],
                    "unresolved_ids": [],
                    "not_applicable_ids": [],
                }},
            },
            {
                "canonical_id": "ds-w-melee",
                "item_id": 3,
                "name": "Melee",
                "category": "Melee",
                "compatibility": {"attachment": {
                    "compatible_ids": [],
                    "incompatible_ids": [],
                    "unresolved_ids": [],
                    "not_applicable_ids": ["acc-1"],
                }},
            },
        ]
        self.write_weapons()

    def write_weapons(self):
        (self.published / "data" / "weapons.json").write_text(
            json.dumps({"weapons": self.weapons}), encoding="utf-8"
        )

    def close(self):
        self.temp.cleanup()


class EvidenceGraphPhaseFourAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.fixture = PhaseFourFixture()

    def tearDown(self):
        self.fixture.close()

    def test_attachment_contract_is_typed_and_valid(self):
        self.assertEqual([], validate_adapter_contract(ATTACHMENT_CONTRACT))
        self.assertNotIn("id", ATTACHMENT_CONTRACT.identity_seeds)
        self.assertNotIn("code", ATTACHMENT_CONTRACT.allowed_outbound_fields)
        self.assertIn("attachment.weapon_relationship", ATTACHMENT_CONTRACT.supported_claims)

    def test_shared_relation_policy_preserves_four_states(self):
        attachment = self.fixture.data_attachment
        self.assertEqual("compatible", attachment_weapon_relation(self.fixture.weapons[0], attachment))
        self.assertEqual("incompatible", attachment_weapon_relation(self.fixture.weapons[1], attachment))
        self.assertEqual("not-applicable", attachment_weapon_relation(self.fixture.weapons[2], attachment))
        named_only = {
            "compatibility_evidence": {
                "all_weapons": False,
                "compatible_weapon_categories": [],
                "named_weapon_text_present": True,
            }
        }
        self.assertEqual("unresolved", attachment_weapon_relation(self.fixture.weapons[1], named_only))

    def test_attachment_graph_validates_and_forward_reverse_agree(self):
        graph = AttachmentAdapter(self.fixture.output).graph("ds-att-acc-1")
        self.assertEqual([], validate_generalized_graph(graph))
        self.assertEqual("attachment", graph["entity"]["entity_type"])
        self.assertTrue(graph["compatibility"]["forward_reverse_agreement"])
        relationships = [
            row for row in graph["claims"]
            if row["claim_type"] == "attachment.weapon_relationship"
        ]
        by_weapon = {
            row["subject"]["relationship"]["weapon"]: row["subject"]["relationship"]["state"]
            for row in relationships
        }
        self.assertEqual("compatible", by_weapon["ds-w-ar"])
        self.assertEqual("incompatible", by_weapon["ds-w-pistol"])
        self.assertEqual("not-applicable", by_weapon["ds-w-melee"])

    def test_poisoned_reverse_relationship_is_conflict(self):
        self.fixture.weapons[1]["compatibility"]["attachment"]["incompatible_ids"] = []
        self.fixture.weapons[1]["compatibility"]["attachment"]["compatible_ids"] = ["acc-1"]
        self.fixture.write_weapons()
        graph = AttachmentAdapter(self.fixture.output).graph("acc-1")
        self.assertFalse(graph["compatibility"]["forward_reverse_agreement"])
        self.assertEqual("CONFLICT", graph["assessment"]["result"])
        consistency = next(
            row for row in graph["claims"]
            if row["claim_type"] == "attachment.compatibility_consistency"
        )
        self.assertEqual("CONFLICT", consistency["result"])
        self.assertTrue(consistency["conflicts"])

    def test_named_model_text_without_typed_owner_stays_unresolved(self):
        self.fixture.data_attachment["compatibility_evidence"] = {
            "status": "direct-localized-installed-game-text",
            "text": "Can be equipped on Named Model X",
            "all_weapons": False,
            "compatible_weapon_categories": [],
            "named_weapon_text_present": True,
            "owner_trace": {
                "state": "exact-accessory-owner-compatibility-selector-unresolved",
                "source_table": "game_common/data/gun_accessory_base_params_data.json",
                "record_id": "acc-1",
                "typed_selectors": {},
            },
        }
        (self.fixture.published / "data" / "attachments.json").write_text(
            json.dumps({"attachments": [self.fixture.data_attachment]}), encoding="utf-8"
        )
        for weapon in self.fixture.weapons:
            relation = "not-applicable" if weapon["category"] == "Melee" else "unresolved"
            compat = weapon["compatibility"]["attachment"]
            for state in ("compatible", "incompatible", "unresolved", "not_applicable"):
                compat[f"{state}_ids"] = []
            compat[f"{relation.replace('-', '_')}_ids"] = ["acc-1"]
        self.fixture.write_weapons()
        graph = AttachmentAdapter(self.fixture.output).graph("acc-1")
        firearm_claims = [
            row for row in graph["claims"]
            if row["claim_type"] == "attachment.weapon_relationship"
            and row["subject"]["relationship"]["weapon"] != "ds-w-melee"
        ]
        self.assertTrue(firearm_claims)
        self.assertTrue(all(row["result"] == "UNRESOLVED" for row in firearm_claims))
        owner = next(row for row in graph["claims"] if row["claim_type"] == "attachment.accessory_owner")
        self.assertEqual("UNRESOLVED", owner["result"])

    def test_stats_acquisition_and_artwork_are_evidence_gated(self):
        graph = AttachmentAdapter(self.fixture.output).graph("100")
        results = {
            row["claim_type"]: row["result"]
            for row in graph["claims"]
            if row["claim_type"] in {
                "attachment.stat_modifiers", "attachment.acquisition", "attachment.artwork"
            }
        }
        self.assertEqual("PROVEN", results["attachment.stat_modifiers"])
        self.assertEqual("PROVEN", results["attachment.acquisition"])
        self.assertEqual("PROVEN", results["attachment.artwork"])

        self.fixture.data_attachment.update({"effects": "", "attribute_codes": [], "passive_buff_id": 0, "gain_path": "", "image_reference": ""})
        self.fixture.web_attachment.update({"gain_path": "", "image_reference": ""})
        (self.fixture.published / "data" / "attachments.json").write_text(
            json.dumps({"attachments": [self.fixture.data_attachment]}), encoding="utf-8"
        )
        (self.fixture.published / "web" / "attachments.json").write_text(
            json.dumps({"attachments": [self.fixture.web_attachment]}), encoding="utf-8"
        )
        graph = AttachmentAdapter(self.fixture.output).graph("acc-1")
        results = {
            row["claim_type"]: row["result"]
            for row in graph["claims"]
            if row["claim_type"] in {
                "attachment.stat_modifiers", "attachment.acquisition", "attachment.artwork"
            }
        }
        self.assertEqual("UNRESOLVED", results["attachment.stat_modifiers"])
        self.assertEqual("UNRESOLVED", results["attachment.acquisition"])
        self.assertEqual("UNRESOLVED", results["attachment.artwork"])

    def test_generalized_engine_registers_and_indexes_attachments(self):
        graph = DeadSignalGeneralizedGraph(self.fixture.output)
        summary = graph.rebuild_entity_registry()
        self.assertIn("attachment", summary["adapter_types"])
        rows = graph.search_entities("Exact Scope", entity_type="attachment")
        self.assertEqual(["ds-att-acc-1"], [row["canonical_id"] for row in rows])
        payload = graph.attachment_entity_graph("ds-att-acc-1")
        self.assertEqual("attachment", payload["entity"]["entity_type"])


if __name__ == "__main__":
    unittest.main()
