from __future__ import annotations

import importlib.util
import marshal
import sys
import tempfile
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_fixed_skill_architecture_trace import trace_fixed_skill_architecture  # noqa: E402


class FixedSkillCloseoutDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _write_pyc(self, relative: str, source: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        code = compile(source, relative, "exec")
        raw = importlib.util.MAGIC_NUMBER + (b"\x00" * 12) + marshal.dumps(code)
        path.write_bytes(raw)
        return path

    def test_closeout_discovers_all_remaining_hypothesis_categories(self):
        self._write_pyc(
            "game_common/guncore/SkillConst.pyc",
            "SKILL_CODE_LEN = 8\nPASSIVE_TABLE = 'passive_skill_data'\nACTIVE_TABLE = 'active_skill_data'\n",
        )
        self._write_pyc(
            "game_common/guncore/GunCoreHelper.pyc",
            "SKILL_CODE_LEN = 8\n"
            "def climp_skill_code(skill_code):\n    return skill_code[:SKILL_CODE_LEN]\n"
            "def init_fixed_skill(skill_code):\n    return climp_skill_code(skill_code)\n",
        )
        self._write_pyc(
            "game_common/guncore/BluePrintHelper.pyc",
            "package_fixed_skill_data = {}\n"
            "equip_package_fixed_skill_data = {}\n"
            "def get_blueprint_fixed_skill(row):\n    return row.get('fixed_skill_code')\n",
        )
        self._write_pyc(
            "game_common/guncore/SkillDataHelper.pyc",
            "PASSIVE_TABLE = 'passive_skill_data'\nACTIVE_TABLE = 'active_skill_data'\n"
            "def get_table_name(skill_code, DataMgr):\n"
            "    common_data = DataMgr.common_data\n"
            "    return PASSIVE_TABLE if skill_code.startswith('WS') else ACTIVE_TABLE\n",
        )
        self._write_pyc(
            "dcs_extend/component/shoot_new/keyword/CompShootDamageSimulateClient.pyc",
            "WEAPON_TO_PASSIVE = {}\nWEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG = {}\n"
            "def get_weapon_passive_skill_config(row, passive_skill_damage_simulate_data):\n"
            "    fixed_skill_code = row.get('fixed_skill_code')\n"
            "    return passive_skill_damage_simulate_data.get(fixed_skill_code)\n",
        )
        self._write_pyc(
            "dcs_extend/component_server/CompSkillMgr.pyc",
            "def init_weapon_skill(row, passive_skill_data):\n"
            "    fixed_skill_code = row.get('fixed_skill_code')\n"
            "    return passive_skill_data.get(fixed_skill_code, {}).get('buff_id')\n",
        )
        self._write_pyc(
            "game_common/guncore/WeaponLegacyMapping.pyc",
            "def convert_weapon_skill(row, gun_blueprint_attr_data):\n"
            "    fixed_skill_code = row.get('fixed_skill_code')\n"
            "    prototype_no = row.get('prototype_no')\n"
            "    blueprint_no = row.get('blueprint_no')\n"
            "    skill_code = fixed_skill_code\n"
            "    return gun_blueprint_attr_data.get(blueprint_no), prototype_no, skill_code\n",
        )

        report = trace_fixed_skill_architecture([("current", self.root)], activity=lambda _m: None)
        self.assertEqual("complete", report["status"])
        self.assertEqual(6, report["record_counts"]["branches"])
        discovery = report["closeout_discovery"]
        self.assertEqual("complete", discovery["status"])
        counts = discovery["record_counts"]["by_category"]
        for category in (
            "skill_constants",
            "climp_callers",
            "passive_table_assembly",
            "package_fixed_skill",
            "damage_sim_indirection",
            "server_weapon_initializers",
            "blueprint_identity_fallbacks",
            "compatibility_overrides",
        ):
            self.assertGreater(counts[category], 0, category)
        self.assertIn("closeout_candidates_by_category", report["record_counts"])
        self.assertEqual(
            "PYC payloads are unmarshaled only; Once Human modules and game bytecode are never executed.",
            report["policy"]["execution"],
        )


if __name__ == "__main__":
    unittest.main()
