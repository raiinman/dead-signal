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
        report = run_missing_skill_forensics(
            self.base,
            self.current,
            ["WS2001", "WS9999"],
            self.reports,
        )
        rows = {row["skill_code"]: row for row in report["skills"]}
        self.assertEqual("exact-code-metadata-hit", rows["WS2001"]["status"])
        self.assertTrue(rows["WS2001"]["raw_exact_files"])
        self.assertTrue(rows["WS2001"]["marshal_hits"])
        self.assertEqual("no-exact-raw-hit-in-targeted-modules", rows["WS9999"]["status"])
        self.assertTrue((self.reports / "missing-fixed-skill-forensics.json").is_file())
        self.assertEqual(
            "No game module is imported or executed; no game bytecode is executed.",
            report["policy"]["execution"],
        )

    def test_fixed_skill_consumer_symbol_is_reported_without_execution(self):
        self._write_pyc(
            "client/item/weapon_card_helper.pyc",
            "def resolve_weapon_skill(record):\n"
            "    fixed_skill_code = record.get('fixed_skill_code')\n"
            "    return fixed_skill_code\n",
        )
        report = run_missing_skill_forensics(
            self.base,
            self.current,
            ["WS2001"],
            self.reports,
        )
        consumer = report["consumer_trace"]
        self.assertEqual("complete", consumer["status"])
        self.assertEqual(1, consumer["record_counts"]["direct_consumer_candidate_files"])
        self.assertEqual("client/item/weapon_card_helper.pyc", consumer["direct_consumer_candidates"][0]["relative_path"])
        hits = consumer["direct_consumer_candidates"][0]["code_hits"]
        self.assertTrue(any("fixed_skill_code" in hit["direct_consumer_symbols"] for hit in hits))

    def test_preload_table_reference_is_context_not_direct_consumer(self):
        self._write_pyc(
            "client_data_preload_pc.pyc",
            "PRELOAD = ['active_skill_config_data', 'gun_blueprint_attr_data', 'skill_tags_data']\n",
        )
        report = run_missing_skill_forensics(
            self.base,
            self.current,
            ["WS2001"],
            self.reports,
        )
        consumer = report["consumer_trace"]
        self.assertEqual(0, consumer["record_counts"]["direct_consumer_candidate_files"])
        self.assertEqual(1, consumer["record_counts"]["context_reference_candidate_files"])
        self.assertEqual("client_data_preload_pc.pyc", consumer["context_reference_candidates"][0]["relative_path"])

    def test_consumer_scan_reports_partial_when_guardrail_is_hit(self):
        self._write_pyc("a.pyc", "VALUE = 'skill_data'\n")
        self._write_pyc("b.pyc", "VALUE = 'fixed_skill_code'\n")
        result = _scan_consumers(
            [("base", self.base_source)],
            activity=lambda _message: None,
            max_files_per_root=1,
        )
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
