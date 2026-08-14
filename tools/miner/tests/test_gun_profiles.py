import json
import tempfile
import unittest
from pathlib import Path

from extractor.export_gun_profiles import build_profiles


class GunProfileTests(unittest.TestCase):
    def write_table(self, root, relative, data):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"data": data}), encoding="utf-8")

    def test_item_mapping_joins_gun_tables(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); base = root / "base"; current = root / "current"
            weapons = root / "weapons.json"
            weapons.write_text(json.dumps({"weapons": [{"item_id": 10, "blueprint_id": 20, "name": "Test", "category": "Pistol"}]}), encoding="utf-8")
            self.write_table(base, "game_common/data/item_to_gun_mapping_data.json", {"10": {"gun_no": 30}})
            self.write_table(base, "game_common/data/gun_base_params_data.json", {"30": {"weapon_rpm": 600, "bullet_scatter_no": 40, "bullet_pattern_no": "Pat30"}})
            self.write_table(base, "game_common/data/gun_stability_data.json", {"30": {"weapon_stability": 50}})
            self.write_table(base, "game_common/data/bullet_scatter_data.json", {"40": {"weapon_accuracy_affix_value": 60}})
            self.write_table(base, "client_data/bullet_pattern_data.json", {"Pat30": {"bullet_num": 5}})
            self.write_table(base, "game_common/data/gun_accessory_slot_params_data.json", {"(30, 8)": {"gun_no": 30, "slot_type": 8}})
            result = build_profiles(base, current, weapons)
            profile = result["profiles"][0]
            self.assertEqual(profile["gun_no"], 30)
            self.assertEqual(profile["gun_base_parameters"]["weapon_rpm"], 600)
            self.assertEqual(profile["scatter_parameters"]["weapon_accuracy_affix_value"], 60)
            self.assertEqual(profile["bullet_pattern"]["bullet_num"], 5)
            self.assertEqual(profile["linked_ids"]["bullet_pattern_no"], "Pat30")
            self.assertEqual(len(profile["accessory_slots"]), 1)
            self.assertEqual(result["record_counts"]["resolved_gun_profiles"], 1)

    def test_missing_mapping_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); base = root / "base"; current = root / "current"
            weapons = root / "weapons.json"
            weapons.write_text(json.dumps({"weapons": [{"item_id": 10, "name": "Unknown"}]}), encoding="utf-8")
            result = build_profiles(base, current, weapons)
            self.assertEqual(result["profiles"][0]["resolution_status"], "unresolved")
            self.assertEqual(result["record_counts"]["unresolved_gun_profiles"], 1)

    def test_melee_is_not_reported_as_missing_firearm_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); base = root / "base"; current = root / "current"
            weapons = root / "weapons.json"
            weapons.write_text(json.dumps({"weapons": [{"item_id": 10, "name": "Bat", "category": "Melee"}]}), encoding="utf-8")
            result = build_profiles(base, current, weapons)
            self.assertEqual(result["profiles"][0]["resolution_status"], "not-applicable-melee")
            self.assertEqual(result["record_counts"]["unresolved_gun_profiles"], 0)


if __name__ == "__main__":
    unittest.main()
