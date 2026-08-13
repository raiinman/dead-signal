from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MOD_ROUTE = REPOSITORY_ROOT / "database" / "mods" / "index.html"


class ModRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = MOD_ROUTE.read_text(encoding="utf-8")

    def test_route_uses_dedicated_renderer_not_generic_catalogue(self):
        self.assertNotIn('../extended-catalogue.js', self.html)
        self.assertIn("window.DS_MODS_WEB", self.html)
        self.assertIn("mod-code-family-projection-variants-preserved", self.html)

    def test_route_preserves_variant_ambiguity_and_mined_level_evidence(self):
        self.assertIn("Variant ambiguity preserved", self.html)
        self.assertIn("main_entry_effects", self.html)
        self.assertIn("Main entry", self.html)
        self.assertIn("Apply range", self.html)
        self.assertIn("Genre library", self.html)
        self.assertIn("Shiny", self.html)

    def test_inline_renderer_is_valid_javascript(self):
        scripts = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", self.html, flags=re.IGNORECASE | re.DOTALL)
        self.assertEqual(1, len(scripts), "Expected one inline Mod route renderer")
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
            handle.write(scripts[0])
            path = Path(handle.name)
        try:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, check=False)
            self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
