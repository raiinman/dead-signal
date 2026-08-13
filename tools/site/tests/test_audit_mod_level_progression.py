from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "audit-mod-level-progression.py"
SPEC = importlib.util.spec_from_file_location("audit_mod_level_progression", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ModLevelProgressionAuditTests(unittest.TestCase):
    def test_numeric_tokens_walk_nested_values_without_treating_bool_as_number(self):
        tokens = module.numeric_tokens({
            "a": "mod 120 / entry -9",
            "b": [True, None, 17, {"value": "frame_3"}],
        })
        self.assertEqual({"120", "-9", "17", "3"}, tokens)

    def test_audit_reports_level_span_and_overlap_as_research_leads_only(self):
        mods = {
            "schema": "dead-signal-mods",
            "families": [{
                "variants": [{"mod_code": 120, "main_entry_code": 9001}],
            }],
        }
        progression = {
            "progression": [
                {
                    "id": "mod_level:1",
                    "track": "mod_level",
                    "level_key": "1",
                    "level": 1,
                    "game_definition": {"frame_lv_1": 1},
                },
                {
                    "id": "mod_level:17",
                    "track": "mod_level",
                    "level_key": "17",
                    "level": 17,
                    "game_definition": {"candidate": "120", "entry": 9001},
                },
                {"id": "weapon:5", "track": "weapon", "level_key": "5", "level": 5},
            ],
        }
        report = module.audit(mods, progression)
        self.assertEqual("Numeric overlap is correlation evidence only; no field relationship is inferred.", report["policy"])
        self.assertEqual(2, report["counts"]["mod_level_rows"])
        self.assertEqual(1, report["counts"]["minimum_level"])
        self.assertEqual(17, report["counts"]["maximum_level"])
        self.assertEqual(1, report["counts"]["rows_with_mod_code_token_overlap"])
        self.assertEqual(1, report["counts"]["rows_with_main_entry_code_token_overlap"])
        leads = report["queues"]["numeric_overlap_research_leads"]
        self.assertEqual(1, len(leads))
        self.assertEqual(["120"], leads[0]["mod_code_token_hits"])
        self.assertEqual(["9001"], leads[0]["main_entry_code_token_hits"])

    def test_resolve_sources_accepts_published_web_and_data_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "web").mkdir()
            (root / "data").mkdir()
            mods_path = root / "web" / "mods.json"
            progression_path = root / "data" / "progression.json"
            mods_path.write_text(json.dumps({"schema": "dead-signal-mods", "families": []}), encoding="utf-8")
            progression_path.write_text(json.dumps({"progression": []}), encoding="utf-8")
            self.assertEqual((mods_path, progression_path), module.resolve_sources(root))


if __name__ == "__main__":
    unittest.main()
