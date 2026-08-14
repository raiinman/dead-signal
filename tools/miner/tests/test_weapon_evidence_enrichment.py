from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "extractor" / "weapon_evidence_enrichment.py"
SPEC = importlib.util.spec_from_file_location("weapon_evidence_enrichment", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class WeaponEvidenceEnrichmentTests(unittest.TestCase):
    @staticmethod
    def weapon(name: str, item_id: int, skill_code: str = "") -> dict:
        return {
            "blueprint_id": item_id + 1000,
            "item_id": item_id,
            "name": name,
            "category": "Melee",
            "blueprint_attribute_progression": {
                "levels": [{"level": 1, "fixed_skill_code": skill_code}],
            },
            "effect": None,
        }

    def test_exact_missing_skill_is_not_aliased_to_similar_id(self):
        payload = {"weapons": [self.weapon("Test", 1, "WS1301")], "record_counts": {}}
        passive = {"WS13101": {"buff_id": 123}}
        enriched = MODULE.enrich(payload, {"1": {"short_desc": "DESC_1"}}, passive, [])
        evidence = enriched["weapons"][0]["effect_resolution"]
        self.assertEqual("exact-fixed-skill-record-missing", evidence["status"])
        self.assertFalse(evidence["exact_passive_skill_record_present"])
        self.assertEqual("WS1301", evidence["fixed_skill_code"])

    def test_no_fixed_skill_is_distinct_from_missing_skill_record(self):
        payload = {"weapons": [self.weapon("No Skill", 2)], "record_counts": {}}
        enriched = MODULE.enrich(payload, {"2": {"short_desc": "DESC_2"}}, {}, [])
        self.assertEqual(
            "no-fixed-skill-reference",
            enriched["weapons"][0]["effect_resolution"]["status"],
        )

    def test_shared_description_handle_is_diagnostic_not_verified(self):
        payload = {
            "weapons": [self.weapon("Kukri", 3), self.weapon("Fish Weapon", 4)],
            "record_counts": {},
        }
        items = {"3": {"short_desc": "SHARED_DESC"}, "4": {"short_desc": "SHARED_DESC"}}
        sources = [("current/translate/translate_data_en.json", {"SHARED_DESC": "suspect text"})]
        enriched = MODULE.enrich(payload, items, {}, sources)
        for row in enriched["weapons"]:
            evidence = row["short_description_evidence"]
            self.assertEqual("translation-handle-shared-across-weapons", evidence["status"])
            self.assertEqual(2, evidence["shared_weapon_handle_count"])
            self.assertEqual("withheld-until-item-handle-identity-is-verified", evidence["publication_status"])
        self.assertEqual(1, enriched["record_counts"]["shared_short_description_handles"])

    def test_conflicting_translation_sources_are_explicit(self):
        evidence = MODULE._description_evidence(
            "DESC",
            [("base", {"DESC": "one"}), ("current", {"DESC": "two"})],
        )
        self.assertEqual("translation-source-conflict", evidence["status"])
        self.assertEqual(2, evidence["unique_translation_text_count"])


if __name__ == "__main__":
    unittest.main()
