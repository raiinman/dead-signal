from __future__ import annotations

import importlib.util
import json
import marshal
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_missing_skill_forensics import run_missing_skill_forensics  # noqa: E402


class MissingSkillCohortIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.root / "snapshots" / "base"
        self.current = self.root / "snapshots" / "current"
        self.source = self.root / "source"
        self.reports = self.root / "research"
        for path in (self.base, self.current, self.source, self.reports):
            path.mkdir(parents=True, exist_ok=True)
        (self.base / "snapshot.json").write_text(json.dumps({"source_root": str(self.source)}), encoding="utf-8")
        (self.current / "snapshot.json").write_text(json.dumps({"source_root": str(self.source)}), encoding="utf-8")
        path = self.source / "game_common/data/gun_blueprint_attr_data.pyc"
        path.parent.mkdir(parents=True, exist_ok=True)
        code = compile("MISSING = 'WS2001'\n", str(path), "exec")
        path.write_bytes(importlib.util.MAGIC_NUMBER + (b"\x00" * 12) + marshal.dumps(code))

    def tearDown(self):
        self.temp.cleanup()

    def test_integrated_report_exposes_cohort_diff_and_counts(self):
        cohort = {
            "status": "complete",
            "record_counts": {
                "normal_weapon_blueprints": 147,
                "unresolved_cohort": 14,
                "resolved_control_cohort": 14,
                "discriminating_field_paths": 9,
            },
            "unresolved_cohort": [{"identity": {"fixed_skill_code": "WS2001"}}],
            "resolved_control_cohort": [{"identity": {"fixed_skill_code": "WS15704"}}],
            "field_diff": [{"field_path": "mystery_route"}],
        }
        with patch("dead_signal_missing_skill_forensics.trace_fixed_skill_cohort_diff", return_value=cohort):
            report = run_missing_skill_forensics(self.base, self.current, ["WS2001"], self.reports)

        self.assertEqual(6, report["schema_version"])
        self.assertEqual(cohort, report["fixed_skill_cohort_diff"])
        self.assertEqual(147, report["record_counts"]["cohort_normal_weapon_blueprints"])
        self.assertEqual(14, report["record_counts"]["cohort_unresolved"])
        self.assertEqual(14, report["record_counts"]["cohort_resolved_controls"])
        self.assertEqual(9, report["record_counts"]["cohort_discriminating_field_paths"])
        self.assertIn("cohort_evidence", report["policy"])
        self.assertTrue((self.reports / "missing-fixed-skill-forensics.json").is_file())


if __name__ == "__main__":
    unittest.main()
