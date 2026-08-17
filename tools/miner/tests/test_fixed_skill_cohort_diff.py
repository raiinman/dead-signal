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
            "game_common/data/gun_blueprint_data.pyc",
            "game_common/data/gun_blueprint_terms_map_data.pyc",
            "game_common/data/passive_skill_data.pyc",
        ):
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            code = compile("VALUE = 1\n", relative, "exec")
            path.write_bytes(importlib.util.MAGIC_NUMBER + (b"\x00" * 12) + marshal.dumps(code))

    def tearDown(self):
        self.temp.cleanup()

    def test_real_keyed_shapes_join_into_unresolved_and_control_cohorts(self):
        blueprints = {
            "data": {
                13431301: {
                    "blueprint_template_no": 10,
                    "gun_item_no": 10431301,
                    "endow": False,
                    "plaques": [],
                    "brand_no": "GB002",
                    "prototype_no": 404,
                },
                13451401: {
                    "blueprint_template_no": 10,
                    "gun_item_no": 10451401,
                    "endow": False,
                    "plaques": [101],
                    "prototype_no": 405,
                },
                19999999: {
                    "blueprint_template_no": 20,
                    "gun_item_no": 10999999,
                    "endow": False,
                    "plaques": [],
                },
            }
        }
        attrs = {
            "data": {
                (13431301, 1): {
                    "fixed_skill_code": "WS2001",
                    "fixed_skill_lv": 1,
                    "base_attr_name1": "E0100",
                    "base_attr_val1": 0,
                    "base_attr_name2": "E0200",
                    "base_attr_val2": 0,
                    "base_attr_name3": "E0300",
                    "base_attr_val3": 0,
                    "mystery_route": 77,
                },
                (13431301, 2): {"fixed_skill_code": "WS2001"},
                (13451401, 1): {
                    "fixed_skill_code": "WS15704",
                    "fixed_skill_lv": 1,
                    "base_attr_name1": "E0100",
                    "base_attr_val1": 0.1,
                    "base_attr_name2": "E0200",
                    "base_attr_val2": 0.25,
                    "base_attr_name3": "E0300",
                    "base_attr_val3": 0.6,
                    "normal_route": 88,
                },
                (19999999, 1): {"fixed_skill_code": "WSHIDDEN"},
            }
        }
        terms = {
            "data": {
                (13431301, 1): {"term_no": [11001]},
                (13451401, 1): {
                    "term_no": [11001],
                    "correct_skill": [303300000, 1],
                    "correct_term_id": 1003,
                },
            }
        }
        passive = {"data": {"WS15704": {"skill_code": "WS15704"}}}

        with patch(
            "dead_signal_fixed_skill_cohort_diff._parse_bindict",
            side_effect=[blueprints, attrs, terms, passive],
        ):
            result = trace_fixed_skill_cohort_diff([("base", self.source.resolve())])

        self.assertEqual("complete", result["status"])
        self.assertEqual(2, result["record_counts"]["normal_weapon_blueprints"])
        self.assertEqual(1, result["record_counts"]["unresolved_cohort"])
        self.assertEqual(1, result["record_counts"]["resolved_control_cohort"])
        self.assertEqual("WS2001", result["unresolved_cohort"][0]["identity"]["fixed_skill_code"])
        self.assertEqual("WS15704", result["resolved_control_cohort"][0]["identity"]["fixed_skill_code"])
        paths = {row["field_path"] for row in result["field_diff"]}
        self.assertIn("attr_star1.mystery_route", paths)
        self.assertIn("attr_star1.normal_route", paths)
        self.assertIn("correct_skill[0]", paths)
        self.assertIn("correct_term_id", paths)
        self.assertEqual(
            "Installed Bindict tables are parsed read-only; game modules and bytecode are never executed.",
            result["policy"]["execution"],
        )

    def test_stringified_tuple_keys_are_supported(self):
        blueprints = {"data": {13431301: {"blueprint_template_no": 10, "endow": False, "plaques": []}}}
        attrs = {
            "data": {
                "(13431301, 1)": {
                    "fixed_skill_code": "WS2001",
                    "base_attr_name1": "E0100",
                    "base_attr_val1": 0,
                    "base_attr_name2": "E0200",
                    "base_attr_val2": 0,
                    "base_attr_name3": "E0300",
                    "base_attr_val3": 0,
                }
            }
        }
        terms = {"data": {"(13431301, 1)": {"term_no": [11001]}}}
        passive = {"data": {}}
        with patch(
            "dead_signal_fixed_skill_cohort_diff._parse_bindict",
            side_effect=[blueprints, attrs, terms, passive],
        ):
            result = trace_fixed_skill_cohort_diff([("base", self.source.resolve())])
        self.assertEqual(1, result["record_counts"]["normal_weapon_blueprints"])
        self.assertEqual(1, result["record_counts"]["unresolved_cohort"])

    def test_missing_required_table_fails_closed(self):
        (self.source / "game_common/data/gun_blueprint_terms_map_data.pyc").unlink()
        result = trace_fixed_skill_cohort_diff([("base", self.source.resolve())])
        self.assertEqual("required-table-missing", result["status"])
        self.assertIn("game_common/data/gun_blueprint_terms_map_data.pyc", result["missing"])


if __name__ == "__main__":
    unittest.main()
