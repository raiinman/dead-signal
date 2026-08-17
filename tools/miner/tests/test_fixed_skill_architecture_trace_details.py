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


class FixedSkillArchitectureTraceDetailsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _write_pyc(self, relative: str, source: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        code = compile(source, relative, "exec")
        path.write_bytes(importlib.util.MAGIC_NUMBER + (b"\x00" * 12) + marshal.dumps(code))

    def test_raw_wordcode_and_indexed_pools_are_preserved(self):
        self._write_pyc(
            "dcs_extend/component/shoot_new/keyword/CompShootDamageSimulateClient.pyc",
            "WEAPON_TO_PASSIVE = {1001: 'WS2001'}\n"
            "WEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG = {'WS2001': 77}\n"
            "def get_weapon_passive_skill_config(row):\n"
            "    fixed_skill_code = row.get('fixed_skill_code')\n"
            "    return WEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG.get(fixed_skill_code)\n",
        )
        result = trace_fixed_skill_architecture([("base", self.root)])
        functions = result["branches"]["damage_passive_mapping"]["targets"][0]["functions"]
        module = next(row for row in functions if row["qualname"] == "<module>")
        function = next(row for row in functions if row["co_name"] == "get_weapon_passive_skill_config")
        self.assertTrue(module["raw_wordcode"])
        self.assertTrue(function["raw_wordcode"])
        self.assertIn("WEAPON_TO_PASSIVE", [row["value"] for row in module["co_names_indexed"]])
        scalar_values = [row["value"] for row in module["co_consts_indexed"]]
        self.assertIn("WS2001", scalar_values)
        self.assertIn(77, scalar_values)
        self.assertIn("wordcode", result["policy"])

    def test_skill_data_helper_includes_table_router_functions(self):
        self._write_pyc(
            "game_common/guncore/SkillDataHelper.pyc",
            "def is_passive(skill_code):\n"
            "    return skill_code.startswith('S')\n"
            "def get_table_name(skill_code):\n"
            "    if skill_code.startswith('WS'):\n"
            "        return 'weapon_skill_data'\n"
            "    return 'passive_skill_data'\n"
            "def is_skill_exist(skill_code):\n"
            "    return bool(get_table_name(skill_code))\n",
        )
        result = trace_fixed_skill_architecture([("base", self.root)])
        functions = result["branches"]["helper_fallback_resolution"]["targets"][1]["functions"]
        names = {row["co_name"] for row in functions}
        self.assertIn("get_table_name", names)
        self.assertIn("is_passive", names)
        router = next(row for row in functions if row["co_name"] == "get_table_name")
        self.assertIn("weapon_skill_data", router["safe_scalar_constants"])
        self.assertTrue(router["raw_wordcode"])

    def test_guncore_module_context_exposes_skill_code_len_constant_pool(self):
        self._write_pyc(
            "game_common/guncore/GunCoreHelper.pyc",
            "SKILL_CODE_LEN = 8\n"
            "def climp_skill_code(skill_code):\n"
            "    return skill_code[:SKILL_CODE_LEN]\n",
        )
        result = trace_fixed_skill_architecture([("base", self.root)])
        functions = result["branches"]["guncore_normalization"]["targets"][0]["functions"]
        module = next(row for row in functions if row["qualname"] == "<module>")
        clamp = next(row for row in functions if row["co_name"] == "climp_skill_code")
        self.assertIn(8, [row["value"] for row in module["co_consts_indexed"]])
        self.assertIn("SKILL_CODE_LEN", [row["value"] for row in module["co_names_indexed"]])
        self.assertTrue(clamp["raw_wordcode"])


if __name__ == "__main__":
    unittest.main()
