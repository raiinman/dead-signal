from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "audit-extended-contracts.py"
SPEC = importlib.util.spec_from_file_location("audit_extended_contracts", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ExtendedContractAuditTests(unittest.TestCase):
    def _root(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        web = root / "web"
        web.mkdir()
        return temporary, root, web

    def _write(self, web: Path, name: str, payload: dict):
        (web / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")

    def _write_valid_minimums(self, web: Path):
        self._write(web, "mods", {
            "schema": "dead-signal-mods",
            "schema_version": 1,
            "publication_status": "mod-code-family-projection-variants-preserved",
            "families": [{
                "canonical_id": "ds-mod-10",
                "family_key": "10",
                "name": "Test Mod",
                "variant_count": 1,
                "variants": [{
                    "id": 10,
                    "item_id": 100,
                    "mod_code": 10,
                    "name": "Test Mod",
                    "description": "Does a thing",
                    "rarity": "Legendary",
                    "main_entry_effects": [{"level": 1, "description": "+1"}],
                }],
            }],
        })
        self._write(web, "attachments", {
            "schema": "dead-signal-attachments",
            "schema_version": 1,
            "publication_status": "ready",
            "slot_types": ["Sight", "Muzzle", "Tactical", "Magazine"],
            "duplicate_canonical_ids": [],
            "attachments": [{
                "canonical_id": "ds-att-1",
                "name": "Test Sight",
                "attachment_type": "Sight",
                "accessory_code": 1,
                "effects": "+1 Accuracy",
                "compatible_weapon_types": [1],
                "image_reference": "a.png",
            }],
        })
        self._write(web, "deviations", {
            "schema": "dead-signal-deviations",
            "schema_version": 1,
            "publication_status": "display-name-families-with-source-variants-preserved",
            "families": [{
                "canonical_id": "ds-dev-test",
                "name": "Test Deviant",
                "variant_count": 1,
                "variants": [{
                    "id": 1,
                    "name": "Test Deviant",
                    "image_reference": "d.png",
                    "skills": [{"name": "Skill", "description": "Skill text"}],
                }],
            }],
        })
        self._write(web, "cradles", {
            "schema": "dead-signal-cradles",
            "schema_version": 1,
            "publication_status": "display-name-families-with-source-variants-preserved",
            "families": [{
                "canonical_id": "ds-cradle-test",
                "name": "Test Cradle",
                "variant_count": 1,
                "variants": [{
                    "id": 1,
                    "name": "Test Cradle",
                    "description": "Cradle text",
                    "image_reference": "c.png",
                    "buff_id": 99,
                }],
            }],
        })

    def test_clean_minimum_contracts_have_no_contract_issues(self):
        temporary, root, web = self._root()
        self.addCleanup(temporary.cleanup)
        self._write_valid_minimums(web)
        report = module.audit_root(root)
        self.assertEqual([], report["summary"]["categories_with_contract_issues"])
        self.assertEqual(0, report["summary"]["mod_multi_variant_families"])
        self.assertEqual(0, report["summary"]["attachments_missing_compatibility"])

    def test_mod_multi_variant_family_and_missing_evidence_are_queued(self):
        temporary, root, web = self._root()
        self.addCleanup(temporary.cleanup)
        self._write_valid_minimums(web)
        payload = json.loads((web / "mods.json").read_text(encoding="utf-8"))
        family = payload["families"][0]
        family["variant_count"] = 2
        family["variants"].append({
            "id": 11,
            "item_id": 101,
            "mod_code": 10,
            "name": "Test Mod Variant",
            "description": "",
            "rarity": "Epic",
            "main_entry_code": 55,
            "main_entry_effects": [],
            "is_shiny": True,
            "shiny_buff_id": 500,
        })
        self._write(web, "mods", payload)
        report = module.audit_root(root)["categories"]["mods"]
        self.assertEqual(1, report["counts"]["multi_variant_families"])
        self.assertEqual(1, len(report["queues"]["variants_missing_description"]))
        self.assertEqual(1, len(report["queues"]["variants_missing_main_entry_rows"]))
        self.assertEqual(1, report["counts"]["shiny_variants"])

    def test_attachment_missing_compatibility_and_effect_evidence_are_exact_queues(self):
        temporary, root, web = self._root()
        self.addCleanup(temporary.cleanup)
        self._write_valid_minimums(web)
        payload = json.loads((web / "attachments.json").read_text(encoding="utf-8"))
        row = payload["attachments"][0]
        row["effects"] = ""
        row["attribute_codes"] = []
        row["passive_buff_id"] = 0
        row["compatible_weapon_types"] = []
        self._write(web, "attachments", payload)
        report = module.audit_root(root)["categories"]["attachments"]
        self.assertEqual(1, report["counts"]["missing_effect_evidence"])
        self.assertEqual(1, report["counts"]["missing_compatibility"])
        self.assertEqual("ds-att-1", report["queues"]["missing_compatibility"][0]["canonical_id"])

    def test_deviation_missing_skill_text_and_multi_variant_identity_are_separate(self):
        temporary, root, web = self._root()
        self.addCleanup(temporary.cleanup)
        self._write_valid_minimums(web)
        payload = json.loads((web / "deviations.json").read_text(encoding="utf-8"))
        family = payload["families"][0]
        family["variant_count"] = 2
        family["variants"].append({"id": 2, "name": "Test Deviant", "image_reference": "", "skills": []})
        self._write(web, "deviations", payload)
        report = module.audit_root(root)["categories"]["deviations"]
        self.assertEqual(1, report["counts"]["multi_variant_families"])
        self.assertEqual(1, report["counts"]["variants_missing_skill_text"])
        self.assertEqual(1, len(report["queues"]["variants_missing_images"]))

    def test_cradle_missing_description_and_effect_reference_are_observational_queues(self):
        temporary, root, web = self._root()
        self.addCleanup(temporary.cleanup)
        self._write_valid_minimums(web)
        payload = json.loads((web / "cradles.json").read_text(encoding="utf-8"))
        variant = payload["families"][0]["variants"][0]
        variant["description"] = ""
        variant["buff_id"] = 0
        variant["keyword_id"] = 0
        variant["attribute_codes"] = []
        self._write(web, "cradles", payload)
        report = module.audit_root(root)["categories"]["cradles"]
        self.assertEqual(1, report["counts"]["variants_missing_description"])
        self.assertEqual(1, len(report["queues"]["variants_without_effect_reference"]))

    def test_unexpected_publisher_status_is_reported_not_silently_accepted(self):
        temporary, root, web = self._root()
        self.addCleanup(temporary.cleanup)
        self._write_valid_minimums(web)
        payload = json.loads((web / "mods.json").read_text(encoding="utf-8"))
        payload["publication_status"] = "some-new-unverified-status"
        self._write(web, "mods", payload)
        report = module.audit_root(root)
        self.assertIn("mods", report["summary"]["categories_with_contract_issues"])
        self.assertIn("unexpected publication_status", report["categories"]["mods"]["contract_issues"][0])


if __name__ == "__main__":
    unittest.main()
