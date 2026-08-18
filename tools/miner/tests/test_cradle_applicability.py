from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_cradle_applicability import build, enrich_files  # noqa: E402


class CradleApplicabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        self.base = self.output / "base"
        self.current = self.output / "current"
        self.base.mkdir()
        self.current.mkdir()
        self.weapons = {
            "weapons": [
                {"blueprint_id": 11, "item_id": 101, "name": "Pistol", "category": "Pistol"},
                {"blueprint_id": 22, "item_id": 202, "name": "Shotgun", "category": "Shotgun"},
            ]
        }
        self.cradles = {"cradles": [
            {"id": 1, "name": "Pistol only", "buff_id": 1001},
            {"id": 2, "name": "Raw attack selector", "buff_id": 1002},
            {"id": 3, "name": "Inactive legacy", "buff_id": 1003},
        ]}
        self.write("game_common/data/cradle_override_entry_data.json", {"data": {
            "1": {"buff_id": 1001}, "2": {"buff_id": 1002}, "3": {"buff_id": 1003},
        }})
        self.write("game_common/data/cradle_override_config_new_data.json", {"data": {
            "7": {"season_no": 700, "override_unlock_lst": [[1, 2]]},
            "extra_info": {"group_dict": {}},
        }})
        self.write("game_common/data/item_data.json", {"data": {
            "101": {"type": 1, "sub_type": 1},
            "202": {"type": 1, "sub_type": 2},
        }})
        self.write("game_common/data/buff/buff_data.json", {"data": {
            "(1001, 1)": {"logic_tree_data": ["buff_1001_1"]},
            "(1002, 1)": {"logic_tree_data": ["buff_1002_1"]},
            "(1003, 1)": {"logic_tree_data": ["buff_1003_1"]},
        }})
        self.write("game_common/data/logic_tree/buff_1001_1.json", self.logic_tree({
            "trigger_checker": [{"type": "hold_item_check", "params": {
                "check_negate": False, "hold_type": 1, "hold_sub_type": 1,
            }}],
            "reset_checker": [{"type": "hold_item_check", "params": {
                "check_negate": True, "hold_type": 1, "hold_sub_type": 1,
            }}],
        }))
        self.write("game_common/data/logic_tree/buff_1002_1.json", self.logic_tree({
            "check_args": {"attack_type": [9], "weapon_no": [], "keyword": []},
        }))
        self.write("game_common/data/logic_tree/buff_1003_1.json", self.logic_tree({}))

    def tearDown(self):
        self.temp.cleanup()

    def write(self, relative, value):
        path = self.base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    @staticmethod
    def logic_tree(params):
        return {"data": {"node_list": {"1": {"effect_params": {"params": params}}}}}

    def test_exact_positive_negative_and_unresolved_relations(self):
        report = build(self.base, self.current, self.output, self.weapons, self.cradles)
        pistol = self.weapons["weapons"][0]["compatibility"]["cradle"]
        shotgun = self.weapons["weapons"][1]["compatibility"]["cradle"]
        self.assertEqual([1], pistol["compatible_exact_ids"])
        self.assertEqual([1], shotgun["incompatible_exact_ids"])
        self.assertEqual([2], pistol["unresolved_ids"])
        self.assertEqual([2], shotgun["unresolved_ids"])
        self.assertEqual(1, report["record_counts"]["selector_states"]["weapon-selector-exact"])

    def test_inactive_legacy_record_does_not_leak(self):
        report = build(self.base, self.current, self.output, self.weapons, self.cradles)
        self.assertNotIn(3, {row["entry_id"] for row in report["selectors"]})
        self.assertNotIn(3, self.weapons["weapons"][0]["compatibility"]["cradle"]["compatible_exact_ids"])

    def test_exact_item_identity_prevents_scalar_or_sibling_leakage(self):
        self.weapons["weapons"].append({"blueprint_id": 1, "item_id": 999, "name": "Collision", "category": "Pistol"})
        report = build(self.base, self.current, self.output, self.weapons, self.cradles)
        collision = self.weapons["weapons"][-1]["compatibility"]["cradle"]
        self.assertEqual("unresolved-item-selector", collision["state"])
        self.assertEqual([], collision["compatible_exact_ids"])
        self.assertEqual(3, report["record_counts"]["weapons"])

    def test_file_projection_writes_report_and_enriches_publication_sources(self):
        data = self.output / "published" / "data"
        data.mkdir(parents=True)
        (data / "weapons.json").write_text(json.dumps(self.weapons), encoding="utf-8")
        (data / "cradles.json").write_text(json.dumps(self.cradles), encoding="utf-8")
        report = enrich_files(self.base, self.current, self.output)
        projected = json.loads((data / "weapons.json").read_text(encoding="utf-8"))
        cradles = json.loads((data / "cradles.json").read_text(encoding="utf-8"))
        self.assertEqual([1], projected["weapons"][0]["compatibility"]["cradle"]["compatible_exact_ids"])
        self.assertEqual("weapon-selector-exact", cradles["cradles"][0]["weapon_applicability"]["state"])
        self.assertTrue((self.output / "published" / "reports" / "weapon-cradle-applicability.json").is_file())
        self.assertEqual(2, report["record_counts"]["active_unique_cradles"])


if __name__ == "__main__":
    unittest.main()
