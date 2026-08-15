from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "extractor" / "investigate_weapon_descriptions.py"
SPEC = importlib.util.spec_from_file_location("investigate_weapon_descriptions", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class InvestigateWeaponDescriptionsTests(unittest.TestCase):
    def test_record_cooccurrence_requires_exact_handle_and_identity(self):
        record = {
            "weapon_item_id": 200,
            "short_desc": "DESC_200",
            "other": "DESC_999",
        }
        hit = MODULE.record_cooccurrence("x", record, "DESC_200", {"200"})
        self.assertIsNotNone(hit)
        self.assertEqual("short_desc", hit["handle_hits"][0]["field"])
        self.assertEqual("weapon_item_id", hit["identity_hits"][0]["field"])
        self.assertIsNone(MODULE.record_cooccurrence("x", record, "DESC_200", {"999"}))
        self.assertIsNone(MODULE.record_cooccurrence("x", record, "DESC_999", {"200"}))

    def test_investigate_blocks_shared_handle_before_candidate_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base"
            current = root / "current"
            table = current / "game_common" / "data" / "weapon_display_data.json"
            table.parent.mkdir(parents=True)
            base.mkdir(parents=True)
            table.write_text(
                '{"data":{"1":{"weapon_item_id":200,"short_desc":"DESC_200"}}}',
                encoding="utf-8",
            )
            payload = {
                "weapons": [{
                    "blueprint_id": 100,
                    "item_id": 200,
                    "name": "Test Weapon",
                    "short_description_evidence": {
                        "status": "translation-handle-shared-across-weapons",
                        "raw_handle": "DESC_200",
                        "unique_translation_text_count": 1,
                        "shared_weapon_handle_count": 2,
                    },
                }],
            }
            report = MODULE.investigate(payload, base, current)
            row = report["weapons"][0]
            self.assertEqual("blocked-shared-handle", row["classification"])
            self.assertEqual(1, row["independent_exact_cooccurrence_count"])
            self.assertEqual("research-only-manual-review-required", row["publication_status"])

    def test_investigate_marks_unique_consistent_exact_cooccurrence_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base"
            current = root / "current"
            table = current / "game_common" / "data" / "weapon_display_data.json"
            table.parent.mkdir(parents=True)
            base.mkdir(parents=True)
            table.write_text(
                '{"data":{"1":{"weapon_item_id":200,"short_desc":"DESC_200"}}}',
                encoding="utf-8",
            )
            payload = {
                "weapons": [{
                    "blueprint_id": 100,
                    "item_id": 200,
                    "name": "Test Weapon",
                    "short_description_evidence": {
                        "status": "translation-handle-resolves-consistently",
                        "raw_handle": "DESC_200",
                        "unique_translation_text_count": 1,
                        "shared_weapon_handle_count": 1,
                    },
                }],
            }
            report = MODULE.investigate(payload, base, current)
            row = report["weapons"][0]
            self.assertEqual("candidate-independent-exact-cooccurrence", row["classification"])
            self.assertEqual(1, row["independent_exact_cooccurrence_count"])


if __name__ == "__main__":
    unittest.main()
