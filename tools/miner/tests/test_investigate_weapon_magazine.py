import json
import py_compile
import sys
import tempfile
import unittest
from pathlib import Path

EXTRACTOR_DIR = Path(__file__).resolve().parents[1] / "src" / "extractor"
if str(EXTRACTOR_DIR) not in sys.path:
    sys.path.insert(0, str(EXTRACTOR_DIR))

import investigate_weapon_magazine as magprobe


class WeaponMagazineInvestigationTests(unittest.TestCase):
    def test_exact_json_and_static_pyc_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "game_common" / "data"
            data.mkdir(parents=True)
            (data / "gun_base_params_data.json").write_text(json.dumps({
                "10230331": {
                    "weapon_magazine_size_affix": "Q1100",
                    "weapon_magazine_size_affix_value": 8,
                    "unrelated": 10,
                }
            }), encoding="utf-8")
            (data / "ids.json").write_text(json.dumps({
                "item": 10233301,
                "blueprint": "13233301",
                "gun": 10230331,
                "near_miss": "Q11000",
            }), encoding="utf-8")

            source = root / "fixture.py"
            source.write_text(
                'def get_gun_magazine_size(item_no, all_affix_add):\n'
                '    magazine = all_affix_add.get("Q1100", 0)\n'
                '    rate = all_affix_add.get("Q1101", 0)\n'
                '    return magazine, rate\n',
                encoding="utf-8",
            )
            py_compile.compile(str(source), cfile=str(root / "fixture.pyc"), doraise=True)

            report = magprobe.build_report(root, 10233301, 13233301, 10230331, "Q1100", "Q1101")
            labels = {hit["matched"] for hit in report["json_hits"]}
            self.assertTrue({"item_id", "blueprint_id", "gun_no", "absolute_affix"} <= labels)
            self.assertTrue(all(hit["value"] != "Q11000" for hit in report["json_hits"]))
            self.assertIn("get_gun_magazine_size", report["summary"]["focus_functions_found"])
            self.assertTrue(report["summary"]["q1100_pyc_functions"])
            self.assertTrue(report["summary"]["q1101_pyc_functions"])
            self.assertIsNone(report["resolution"]["final_magazine"])
            self.assertFalse(report["safety"]["game_bytecode_executed"])

    def test_missing_or_invalid_pyc_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bad.pyc").write_bytes(b"not a pyc")
            report = magprobe.build_report(root, 1, 2, 3, "Q1100", "Q1101")
            self.assertEqual([], report["pyc_hits"])
            self.assertEqual("evidence-only-unresolved", report["resolution"]["status"])


if __name__ == "__main__":
    unittest.main()
