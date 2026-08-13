import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class ExtendedRouteWiringTests(unittest.TestCase):
    CATEGORIES = {
        "calibrations": "DS_CALIBRATIONS_WEB",
        "mods": "DS_MODS_WEB",
        "attachments": "DS_ATTACHMENTS_WEB",
        "deviations": "DS_DEVIATIONS_WEB",
        "cradles": "DS_CRADLES_WEB",
    }

    def test_routes_reference_shared_renderer_and_own_contract(self):
        for category, variable in self.CATEGORIES.items():
            with self.subTest(category=category):
                route = (ROOT / "database" / category / "index.html").read_text(encoding="utf-8")
                self.assertIn("../extended-catalogue.css", route)
                self.assertIn("../extended-catalogue.js", route)
                self.assertIn(f"{category}-data.js", route)
                placeholder = (ROOT / "database" / category / f"{category}-data.js").read_text(encoding="utf-8")
                self.assertIn(variable, placeholder)

    def test_shared_renderer_has_all_expected_contract_schemas(self):
        source = (ROOT / "database" / "extended-catalogue.js").read_text(encoding="utf-8")
        for schema in (
            "dead-signal-calibrations-current",
            "dead-signal-mods",
            "dead-signal-attachments",
            "dead-signal-deviations",
            "dead-signal-cradles",
        ):
            self.assertIn(schema, source)

    def test_copy_only_manifest_deploys_prepared_routes(self):
        manifest = (ROOT / ".cpanel.yml").read_text(encoding="utf-8")
        self.assertNotIn("/bin/rm", manifest)
        for category in ("armor", *self.CATEGORIES):
            self.assertIn(f"database/{category}", manifest)
        self.assertIn("database/extended-catalogue.js", manifest)
        self.assertIn("database/extended-catalogue.css", manifest)
        for forbidden in ("python ", "python3 ", "unzip ", "curl ", "wget ", "find "):
            self.assertNotIn(forbidden, manifest.casefold())


if __name__ == "__main__":
    unittest.main()
