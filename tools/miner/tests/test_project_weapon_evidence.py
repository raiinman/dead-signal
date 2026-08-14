from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "extractor" / "project_weapon_evidence.py"
SPEC = importlib.util.spec_from_file_location("project_weapon_evidence", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ProjectWeaponEvidenceTests(unittest.TestCase):
    def test_projection_preserves_provenance_without_suspect_text(self):
        normalized = {
            "weapons": [{
                "blueprint_id": 100,
                "item_id": 200,
                "effect_resolution": {
                    "status": "exact-fixed-skill-record-missing",
                    "fixed_skill_code": "WS1301",
                    "exact_passive_skill_record_present": False,
                },
                "short_description_evidence": {
                    "status": "translation-handle-shared-across-weapons",
                    "raw_handle": "DESC_HANDLE",
                    "marker_stripped_handle": "DESC_HANDLE",
                    "translation_matches": [{
                        "source": "current/translate/translate_data_en.json",
                        "key_kind": "raw",
                        "key": "DESC_HANDLE",
                        "text": "THIS SUSPECT TEXT MUST NOT LEAK",
                    }],
                    "unique_translation_text_count": 1,
                    "shared_weapon_handle_count": 2,
                    "shared_weapon_identities": [{"blueprint_id": 100}, {"blueprint_id": 101}],
                },
            }],
        }
        web = {
            "schema": "dead-signal-weapons",
            "record_counts": {"weapons": 1},
            "weapons": [{
                "canonical_id": "ds-w-100",
                "blueprint_id": 100,
                "item_id": 200,
                "description": "",
                "verification": {"description_status": MODULE.DESCRIPTION_WITHHELD_STATUS},
            }],
        }
        projected = MODULE.project(normalized, web)
        row = projected["weapons"][0]
        self.assertEqual("exact-fixed-skill-record-missing", row["effect_resolution"]["status"])
        evidence = row["verification"]["short_description_evidence"]
        self.assertEqual("DESC_HANDLE", evidence["raw_handle"])
        self.assertNotIn("text", evidence["translation_matches"][0])
        self.assertNotIn("THIS SUSPECT TEXT MUST NOT LEAK", str(projected))
        self.assertEqual(MODULE.DESCRIPTION_WITHHELD_STATUS, evidence["publication_status"])

    def test_projection_requires_exact_blueprint_and_item_identity(self):
        normalized = {"weapons": [{"blueprint_id": 100, "item_id": 999}]}
        web = {
            "schema": "dead-signal-weapons",
            "record_counts": {"weapons": 1},
            "weapons": [{"canonical_id": "ds-w-100", "blueprint_id": 100, "item_id": 200, "verification": {}}],
        }
        projected = MODULE.project(normalized, web)
        self.assertEqual(1, projected["record_counts"]["weapon_evidence_missing_exact_identity"])
        self.assertEqual("normalized-evidence-missing", projected["weapons"][0]["effect_resolution"]["status"])


if __name__ == "__main__":
    unittest.main()
