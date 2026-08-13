from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "audit-mod-frame-arithmetic.py"
spec = importlib.util.spec_from_file_location("audit_mod_frame_arithmetic", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class ModFrameArithmeticTests(unittest.TestCase):
    def payload(self):
        return {
            "progression": [
                {
                    "track": "mod_level",
                    "level": level,
                    "game_definition": {
                        "frame_lv_1": level,
                        "frame_lv_2": 0,
                        "frame_lv_3": 0,
                        "frame_lv_4": 0,
                    },
                }
                for level in range(1, 18)
            ]
        }

    def test_exact_levels_and_frame_sum_are_ready(self):
        report = module.audit(self.payload())
        self.assertTrue(report["ready"])
        self.assertEqual(list(range(1, 18)), report["levels"])
        self.assertEqual([], report["problems"])

    def test_frame_sum_mismatch_blocks_ready(self):
        payload = self.payload()
        payload["progression"][7]["game_definition"]["frame_lv_1"] = 99
        report = module.audit(payload)
        self.assertFalse(report["ready"])
        self.assertEqual(1, len(report["problems"]))

    def test_missing_level_blocks_ready(self):
        payload = self.payload()
        payload["progression"].pop()
        self.assertFalse(module.audit(payload)["ready"])


if __name__ == "__main__":
    unittest.main()
