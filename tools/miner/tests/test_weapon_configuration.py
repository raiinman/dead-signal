import json
import sys
import tempfile
import unittest
from pathlib import Path

EXTRACTOR = Path(__file__).resolve().parents[1] / "src" / "extractor"
sys.path.insert(0, str(EXTRACTOR))

from export_weapon_configuration import build_configuration


class WeaponConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, key, values):
        (self.data / name).write_text(json.dumps({key: values}), encoding="utf-8")

    def empty_supporting_files(self):
        self.write("attachments.json", "attachments", [])
        self.write("mods.json", "mods", [])
        self.write("calibrations.json", "calibrations", [])

    def test_only_proven_direct_modifiers_are_auto_applied(self):
        modifier = {"type": "stat_modifier", "resolution_status": "resolved", "operation": "add_percent", "value": 0.1}
        self.write("ammo.json", "ammo", [{"item_id": 1, "name": "Test", "configuration_bindings": [{"static_modifiers": [modifier], "passive_buff_id": 0}]}])
        self.empty_supporting_files()
        binding = build_configuration(self.data)["layers"]["ammo"][0]["bindings"][0]
        self.assertEqual("proven-static", binding["auto_apply_status"])
        self.assertEqual([modifier], binding["static_modifiers"])

    def test_passive_ammo_buff_is_not_auto_applied(self):
        self.write("ammo.json", "ammo", [{"item_id": 1, "configuration_bindings": [{"static_modifiers": [], "passive_buff_id": 99}]}])
        self.empty_supporting_files()
        binding = build_configuration(self.data)["layers"]["ammo"][0]["bindings"][0]
        self.assertEqual("static-only-passive-buff-excluded", binding["auto_apply_status"])

    def test_runtime_weapon_mod_is_classified_not_calculated(self):
        self.write("ammo.json", "ammo", [])
        self.write("attachments.json", "attachments", [])
        self.write("mods.json", "mods", [{"id": 7, "resolved_applicability": {"category": "weapon"}, "resolved_effects": [{"entry_code": 2, "entry_level": 1, "effects": [{"type": "buff_application", "buff_id": 9}]}]}])
        self.write("calibrations.json", "calibrations", [])
        record = build_configuration(self.data)["layers"]["weapon_mods"][0]
        self.assertEqual("conditional-or-runtime-excluded", record["auto_apply_status"])


if __name__ == "__main__":
    unittest.main()
