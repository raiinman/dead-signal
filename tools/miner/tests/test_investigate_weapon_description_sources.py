from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "extractor" / "investigate_weapon_description_sources.py"
SPEC = importlib.util.spec_from_file_location("investigate_weapon_description_sources", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class WeaponDescriptionSourceInvestigationTests(unittest.TestCase):
    def _write_table(self, root: Path, relative: str, data: dict) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"data": data}, ensure_ascii=False), encoding="utf-8")

    def test_requires_exact_identity_and_flags_shared_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base"
            current = root / "current"
            self._write_table(
                base,
                "game_common/data/weapon_ui_data.json",
                {
                    "a": {"item_id": 101, "description": "Unique Alpha copy"},
                    "b": {"item_id": 202, "description": "Shared copy"},
                    "c": {"item_id": 303, "description": "Shared copy"},
                    "noise": {"item_id": 999, "description": "Must not join by name"},
                },
            )
            payload = {
                "weapons": [
                    {"blueprint_id": 1, "item_id": 101, "name": "Alpha"},
                    {"blueprint_id": 2, "item_id": 202, "name": "Beta"},
                    {"blueprint_id": 3, "item_id": 303, "name": "Gamma"},
                ]
            }
            report = MODULE.investigate(payload, base, current)
            by_name = {row["name"]: row for row in report["weapons"]}
            self.assertEqual("exact-record-description-candidates-found", by_name["Alpha"]["classification"])
            self.assertEqual(1, by_name["Alpha"]["unique_candidate_count"])
            self.assertEqual("only-shared-or-conflicting-candidates", by_name["Beta"]["classification"])
            self.assertTrue(by_name["Beta"]["candidates"][0]["shared_across_weapons"])
            self.assertEqual("only-shared-or-conflicting-candidates", by_name["Gamma"]["classification"])

    def test_translation_handle_resolves_without_becoming_publication_truth(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base"
            current = root / "current"
            self._write_table(
                base,
                "game_common/data/gun_display_data.json",
                {"x": {"gun_no": 7001, "tooltip": "DESC_KEY"}},
            )
            self._write_table(
                base,
                "translate/translate_data_en.json",
                {"DESC_KEY": "Verified-looking English text"},
            )
            payload = {"weapons": [{"blueprint_id": 7, "item_id": 70, "gun_no": 7001, "name": "Test"}]}
            report = MODULE.investigate(payload, base, current)
            candidate = report["weapons"][0]["candidates"][0]
            self.assertEqual("Verified-looking English text", candidate["resolved_text"])
            self.assertEqual("research-only", candidate["publication_status"])
            self.assertEqual("exact-record-description-candidates-found", report["weapons"][0]["classification"])


if __name__ == "__main__":
    unittest.main()
