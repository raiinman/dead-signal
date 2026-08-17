from __future__ import annotations

import importlib.util
import marshal
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_fixed_skill_cohort_diff import trace_fixed_skill_cohort_diff  # noqa: E402


class FixedSkillCohortDiffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir(parents=True, exist_ok=True)
        for relative in (
            "game_common/data/gun_blueprint_attr_data.pyc",
            "game_common/data/passive_skill_data.pyc",
        ):
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            code = compile("VALUE = 1\n", relative, "exec")
            path.write_bytes(importlib.util.MAGIC_NUMBER + (b"\x00" * 12) + marshal.dumps(code))

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_unresolved_and_same_endow_control_are_separated(self):
        gun = {
            1: {
                "blueprint_template_no": 10,
                "blueprint_id": 13431301,
                "fixed_skill_code": "WS2001",
                "endow": False,
                "plaques": [],
                "correct_skill": None,
                "correct_term_id": None,
                "base_attr": {"E0100": 0, "E0200": 0, "E0300": 0},
                "mystery_route": 77,
            },
            2: {
                "blueprint_template_no": 10,
                "blueprint_id": 99900002,
                "fixed_skill_code": "WS15704",
                "endow": False,
                "plaques": [1],
                "correct_skill": "WS15704",
                "correct_term_id": 22,
                "base_attr": {"E0100": 1, "E0200": 0, "E0300": 0},
                "normal_route": 88,
            },
            3: {
                "blueprint_template_no": 10,
                "blueprint_id": 99900003,
                "fixed_skill_code": "WSOTHER",
                "endow": True,
                "plaques": [],
                "base_attr": {"E0100": 0, "E0200": 0, "E0300": 0},
            },
        }
        passive = {"WS15704": {"skill_code": "WS15704"}}

        with patch("dead_signal_fixed_skill_cohort_diff._parse_bindict", side_effect=[gun, passive]):
            result = trace_fixed_skill_cohort_diff([("base", self.source.resolve())])

        self.assertEqual("complete", result["status"])
        self.assertEqual(3, result["record_counts"]["normal_weapon_blueprints"])
        self.assertEqual(1, result["record_counts"]["unresolved_cohort"])
        self.assertEqual(1, result["record_counts"]["resolved_control_cohort"])
        self.assertEqual("WS2001", result["unresolved_cohort"][0]["identity"]["fixed_skill_code"])
        self.assertEqual("WS15704", result["resolved_control_cohort"][0]["identity"]["fixed_skill_code"])
        paths = {row["field_path"] for row in result["field_diff"]}
        self.assertIn("mystery_route", paths)
        self.assertIn("normal_route", paths)
        self.assertEqual(
            "Installed Bindict tables are parsed read-only; game modules and bytecode are never executed.",
            result["policy"]["execution"],
        )

    def test_missing_required_table_fails_closed(self):
        (self.source / "game_common/data/passive_skill_data.pyc").unlink()
        result = trace_fixed_skill_cohort_diff([("base", self.source.resolve())])
        self.assertEqual("required-table-missing", result["status"])
        self.assertIn("game_common/data/passive_skill_data.pyc", result["missing"])


if __name__ == "__main__":
    unittest.main()
