import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ROUTE = ROOT / "preview" / "build-lab" / "index.html"


class BuildLabV2Tests(unittest.TestCase):
    def test_current_asset_paths_exist_in_repository(self):
        route = ROUTE.read_text(encoding="utf-8")
        expected = {
            "/shared/readability.css": ROOT / "shared" / "readability.css",
            "/shared/workstation-shell.css": ROOT / "shared" / "workstation-shell.css",
            "build-lab.css": ROOT / "preview" / "build-lab" / "build-lab.css",
            "/shared/readability.js": ROOT / "shared" / "readability.js",
            "/shared/workstation-shell.js": ROOT / "shared" / "workstation-shell.js",
            "/database/weapons/weapons-data.js": ROOT / "database" / "weapons" / "weapons-data.js",
            "/database/weapons/weapon-public-adapter.js": ROOT / "database" / "weapons" / "weapon-public-adapter.js",
            "/database/armor/armor-data.js": ROOT / "database" / "armor" / "armor-data.js",
            "/database/mods/mods-data.js": ROOT / "database" / "mods" / "mods-data.js",
            "/database/calibrations/calibrations-data.js": ROOT / "database" / "calibrations" / "calibrations-data.js",
            "/database/attachments/attachments-data.js": ROOT / "database" / "attachments" / "attachments-data.js",
            "/database/deviations/deviations-data.js": ROOT / "database" / "deviations" / "deviations-data.js",
            "/database/cradles/cradles-data.js": ROOT / "database" / "cradles" / "cradles-data.js",
        }
        for url, path in expected.items():
            with self.subTest(url=url):
                self.assertIn(url, route)
                self.assertTrue(path.is_file(), path)

        for stale in (
            'href="style.css',
            'href="weapon-model-ui.css',
            'href="calibration-details-ui.css',
            'src="app.js',
            'data/community-data.js',
        ):
            self.assertNotIn(stale, route)

    def test_inline_planner_core_is_valid_javascript(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is unavailable")
        route = ROUTE.read_text(encoding="utf-8")
        inline_scripts = re.findall(r"<script>(.*?)</script>", route, flags=re.DOTALL | re.IGNORECASE)
        self.assertEqual(len(inline_scripts), 1)
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "build-lab-v2.js"
            source.write_text(inline_scripts[0], encoding="utf-8")
            result = subprocess.run([node, "--check", str(source)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_fail_closed_multi_variant_selection_is_explicit(self):
        route = ROUTE.read_text(encoding="utf-8")
        self.assertIn("multiple-source-variants-preserved", route)
        self.assertIn("player-selection identity withheld", route)
        self.assertIn("disabled:isMultiVariant(row)", route)


if __name__ == "__main__":
    unittest.main()
