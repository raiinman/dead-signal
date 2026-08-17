from __future__ import annotations

import importlib.util
import json
import marshal
import sys
import tempfile
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_fixed_skill_architecture_trace import trace_fixed_skill_architecture  # noqa: E402
from dead_signal_fixed_skill_flow_trace import _fallback_instruction_windows  # noqa: E402
from dead_signal_missing_skill_forensics import _scan_consumers, run_missing_skill_forensics  # noqa: E402
from dead_signal_schema_trace_batch import _unresolved_skill_codes  # noqa: E402


class MissingSkillForensicsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.root / "snapshots" / "base"
        self.current = self.root / "snapshots" / "current"
        self.base_source = self.root / "source-base"
        self.current_source = self.root / "source-current"
        self.reports = self.root / "research"
        for path in (self.base, self.current, self.base_source, self.current_source, self.reports):
            path.mkdir(parents=True, exist_ok=True)
        (self.base / "snapshot.json").write_text(
            json.dumps({"source_root": str(self.base_source)}), encoding="utf-8"
        )
        (self.current / "snapshot.json").write_text(
            json.dumps({"source_root": str(self.current_source)}), encoding="utf-8"
        )

    def tearDown(self):
        self.temp.cleanup()

    def _write_pyc(self, relative: str, source: str) -> Path:
        path = self.base_source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        code = compile(source, relative, "exec")
        raw = importlib.util.MAGIC_NUMBER + (b"\x00" * 12) + marshal.dumps(code)
        path.write_bytes(raw)
        return path

    def test_exact_unresolved_skill_constant_is_found_without_execution(self):
        self._write_pyc(
            "game_common/data/hidden_weapon_skill_helper.pyc",
            "MISSING_FIXED_SKILL = 'WS2001'\n\ndef lookup():\n    return MISSING_FIXED_SKILL\n",
        )
        report = run_missing_skill_forensics(self.base, self.current, ["WS2001", "WS9999"], self.reports)
        rows = {row["skill_code"]: row for row in report["skills"]}
        self.assertEqual("exact-code-metadata-hit", rows["WS2001"]["status"])
        self.assertTrue(rows["WS2001"]["raw_exact_files"])
        self.assertTrue(rows["WS2001"]["marshal_hits"])
        self.assertEqual("no-exact-raw-hit-in-targeted-modules", rows["WS9999"]["status"])
        self.assertTrue((self.reports / "missing-fixed-skill-forensics.json").is_file())
        self.assertEqual("No game module is imported or executed; no game bytecode is executed.", report["policy"]["execution"])

    def test_fixed_skill_consumer_symbol_is_reported_without_execution(self):
        self._write_pyc(
            "client/item/weapon_card_helper.pyc",
            "def resolve_weapon_skill(record):\n"
            "    fixed_skill_code = record.get('fixed_skill_code')\n"
            "    return fixed_skill_code\n",
        )
        report = run_missing_skill_forensics(self.base, self.current, ["WS2001"], self.reports)
        consumer = report["consumer_trace"]
        self.assertEqual("complete", consumer["status"])
        self.assertEqual(1, consumer["record_counts"]["direct_consumer_candidate_files"])
        self.assertEqual("client/item/weapon_card_helper.pyc", consumer["direct_consumer_candidates"][0]["relative_path"])
        hits = consumer["direct_consumer_candidates"][0]["code_hits"]
        self.assertTrue(any("fixed_skill_code" in hit["direct_consumer_symbols"] for hit in hits))

    def test_direct_consumer_gets_bounded_static_instruction_flow(self):
        self._write_pyc(
            "game_common/guncore/BluePrintHelper.pyc",
            "def get_blueprint_fixed_skill(row, passive_skill_data):\n"
            "    fixed_skill_code = row.get('fixed_skill_code')\n"
            "    return passive_skill_data.get(fixed_skill_code)\n",
        )
        report = run_missing_skill_forensics(self.base, self.current, ["WS2001"], self.reports)
        flow = report["fixed_skill_flow_trace"]
        self.assertEqual("complete", flow["status"])
        self.assertEqual(1, flow["record_counts"]["candidate_files"])
        self.assertEqual(1, flow["record_counts"]["consumer_functions"])
        self.assertGreaterEqual(flow["record_counts"]["fixed_skill_instruction_anchors"], 1)
        function = flow["functions"][0]
        self.assertEqual("get_blueprint_fixed_skill", function["qualname"])
        self.assertIn("passive_skill_data", function["local_names"])
        self.assertTrue(any(row.get("is_fixed_skill_anchor") for row in function["instruction_window"] if not row.get("gap")))
        self.assertEqual("PYC code objects are unmarshaled and decoded only; game bytecode is never executed.", flow["policy"]["execution"])

    def test_tolerant_wordcode_fallback_finds_exact_fixed_skill_constant(self):
        module = compile(
            "def get_blueprint_fixed_skill(row):\n"
            "    return row.get('fixed_skill_code')\n",
            "fixture.py",
            "exec",
        )
        function = next(value for value in module.co_consts if hasattr(value, "co_code") and value.co_name == "get_blueprint_fixed_skill")
        rows, anchors, error = _fallback_instruction_windows(function)
        self.assertIsNone(error)
        self.assertGreaterEqual(anchors, 1)
        self.assertTrue(any(row.get("is_fixed_skill_anchor") for row in rows if not row.get("gap")))
        self.assertTrue(any(row.get("argval") == "fixed_skill_code" for row in rows if not row.get("gap")))

    def test_all_six_architecture_branches_are_static_and_bounded(self):
        self._write_pyc(
            "dcs_extend/component/shoot_new/keyword/CompShootDamageSimulateClient.pyc",
            "WEAPON_TO_PASSIVE = {}\nWEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG = {}\n"
            "def get_weapon_passive_skill_config(row):\n"
            "    fixed_skill_code = row.get('fixed_skill_code')\n"
            "    return WEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG.get(fixed_skill_code)\n",
        )
        self._write_pyc(
            "game_common/guncore/GunCoreHelper.pyc",
            "SKILL_CODE_LEN = 8\nMAX_SKILL_LEVEL = 6\n"
            "def climp_skill_code(skill_code):\n    return skill_code[:SKILL_CODE_LEN]\n"
            "def init_fixed_skill(skill_code):\n    return climp_skill_code(skill_code)\n"
            "def get_blueprint_fixed_skill(row):\n    return row.get('fixed_skill_code')\n",
        )
        self._write_pyc(
            "dcs_extend/component/CompCamera.pyc",
            "def _get_gun_sp_track_time(row, stardust_gun_skill_data, passive_skill_data):\n"
            "    skill_code = row.get('fixed_skill_code')\n"
            "    star_skill_no = stardust_gun_skill_data.get(skill_code)\n"
            "    return passive_skill_data.get(star_skill_no, {}).get('skill_cast_time')\n",
        )
        self._write_pyc(
            "ui/weapon_craft_part/ScrollViewItems.pyc",
            "class WRGunInfoPart:\n"
            "    def update_fixed_skills(self, fixed_passive_skill, skill_data, PassiveSkillHelper):\n"
            "        skill_code = fixed_passive_skill.get('skill_code')\n"
            "        return PassiveSkillHelper.get_passive_skill_name(skill_code)\n",
        )
        result = trace_fixed_skill_architecture(
            [("base", self.base_source.resolve())], activity=lambda _message: None
        )
        self.assertEqual("complete", result["status"])
        self.assertEqual(6, result["record_counts"]["branches"])
        self.assertGreaterEqual(result["record_counts"]["files_found"], 4)
        self.assertGreaterEqual(result["record_counts"]["functions_found"], 4)
        self.assertTrue(result["branches"]["damage_passive_mapping"]["functions_found"])
        self.assertTrue(result["branches"]["guncore_normalization"]["functions_found"])
        self.assertTrue(result["branches"]["star_stardust_resolution"]["functions_found"])
        self.assertTrue(result["branches"]["player_facing_ui"]["functions_found"])
        self.assertIn("helper_fallback_resolution", result["branches"])
        self.assertIn("server_buff_resolution", result["branches"])
        self.assertEqual(
            "PYC payloads are unmarshaled only; Once Human modules and game bytecode are never executed.",
            result["policy"]["execution"],
        )

    def test_integrated_report_exposes_architecture_trace(self):
        self._write_pyc(
            "game_common/guncore/GunCoreHelper.pyc",
            "def get_blueprint_fixed_skill(row):\n    return row.get('fixed_skill_code')\n",
        )
        report = run_missing_skill_forensics(self.base, self.current, ["WS2001"], self.reports)
        self.assertIn("fixed_skill_architecture_trace", report)
        self.assertEqual(6, report["record_counts"]["architecture_branches"])
        self.assertIn("guncore_normalization", report["fixed_skill_architecture_trace"]["branches"])
        self.assertIn("helper_fallback_resolution", report["fixed_skill_architecture_trace"]["branches"])
        self.assertIn("server_buff_resolution", report["fixed_skill_architecture_trace"]["branches"])

    def test_preload_table_reference_is_context_not_direct_consumer(self):
        self._write_pyc(
            "client_data_preload_pc.pyc",
            "ACTIVE = 'active_skill_config_data'\n"
            "BLUEPRINT = 'gun_blueprint_attr_data'\n"
            "TAGS = 'skill_tags_data'\n",
        )
        report = run_missing_skill_forensics(self.base, self.current, ["WS2001"], self.reports)
        consumer = report["consumer_trace"]
        self.assertEqual(0, consumer["record_counts"]["direct_consumer_candidate_files"])
        self.assertEqual(1, consumer["record_counts"]["context_reference_candidate_files"])
        self.assertEqual("client_data_preload_pc.pyc", consumer["context_reference_candidates"][0]["relative_path"])

    def test_consumer_scan_reports_partial_when_guardrail_is_hit(self):
        self._write_pyc("a.pyc", "VALUE = 'skill_data'\n")
        self._write_pyc("b.pyc", "VALUE = 'fixed_skill_code'\n")
        result = _scan_consumers([("base", self.base_source.resolve())], activity=lambda _message: None, max_files_per_root=1)
        self.assertEqual("partial-limit", result["status"])
        self.assertEqual(["base"], result["roots_truncated_at_limit"])

    def test_batch_extracts_unique_unresolved_skill_codes_only(self):
        rows = [
            {"unresolved_stops": [
                {"kind": "skill_id", "value": "WS2001"},
                {"kind": "crosshair_id", "value": "Xhair1"},
            ]},
            {"unresolved_stops": [
                {"kind": "skill_id", "value": "WS1301"},
                {"kind": "skill_id", "value": "WS2001"},
            ]},
        ]
        self.assertEqual(["WS1301", "WS2001"], _unresolved_skill_codes(rows))


if __name__ == "__main__":
    unittest.main()
