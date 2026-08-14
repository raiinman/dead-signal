from __future__ import annotations

import importlib.util
import json
import tempfile
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
            "prototype_id": 301,
            "blueprint_attribute_progression": {
                "levels": [{"level": 1, "fixed_skill_code": skill_code}],
            },
            "effect": None,
            "tiers": [{"tier": 1, "item_id": item_id + 10000, "gun_no": 4001}],
        }

    @staticmethod
    def write_table(root: Path, relative: str, data: dict) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"data": data}), encoding="utf-8")

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

    def test_blank_fixed_skill_continues_exact_reference_trace(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = root / "base"
            current = root / "current"
            published = root / "published"
            weapons_path = published / "data" / "weapons.json"
            weapons_path.parent.mkdir(parents=True, exist_ok=True)

            weapon = self.weapon("AA12 Example", 1001)
            payload = {"weapons": [weapon], "record_counts": {}}
            weapons_path.write_text(json.dumps(payload), encoding="utf-8")

            self.write_table(current, MODULE.ITEM_TABLE, {"1001": {"short_desc": "DESC_AA12"}})
            self.write_table(current, MODULE.EQUIP_TABLE, {"1001": {"gun_no": 4001}})
            self.write_table(
                base,
                "game_common/data/weapon_special_map_data.json",
                {"map-aa12": {"weapon_no": 1001, "passive_skill_code": "WS9001"}},
            )
            self.write_table(
                base,
                MODULE.PASSIVE_TABLE,
                {"WS9001": {"buff_id": 555001}},
            )

            enriched = MODULE.enrich_file(base, current, weapons_path)
            evidence = enriched["weapons"][0]["effect_resolution"]
            self.assertEqual("no-fixed-skill-reference", evidence["status"])
            trace = evidence["fallback_reference_trace"]
            self.assertEqual(
                "blank-fixed-skill-exact-trace-found-mechanic-candidates",
                trace["status"],
            )
            candidate = next(
                row for row in trace["mechanic_reference_candidates"]
                if row["value"] == "WS9001"
            )
            self.assertEqual("passive_skill_code", candidate["field"])
            self.assertTrue(candidate["exact_target_record_found"])
            self.assertTrue(
                any(row["table"].endswith("passive_skill_data.json") for row in candidate["exact_target_occurrences"])
            )
            report = published / "reports" / "weapon-blank-fixed-skill-reference-trace.json"
            self.assertTrue(report.is_file())
            report_payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(1, report_payload["record_counts"]["weapons"])

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
