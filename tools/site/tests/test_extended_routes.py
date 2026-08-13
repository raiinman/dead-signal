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
    DEDICATED_CATEGORIES = ("calibrations", "mods")
    SHARED_CATEGORIES = ("attachments", "deviations", "cradles")
    BUILD_LAB_CATEGORIES = ("calibrations", "attachments", "deviations", "cradles")

    def test_routes_load_own_contract_and_expected_renderer(self):
        for category, variable in self.CATEGORIES.items():
            with self.subTest(category=category):
                route = (ROOT / "database" / category / "index.html").read_text(encoding="utf-8")
                self.assertIn("../extended-catalogue.css", route)
                self.assertIn(f"{category}-data.js", route)
                if category in self.SHARED_CATEGORIES:
                    self.assertIn('src="../extended-catalogue.js', route)
                else:
                    self.assertNotIn('src="../extended-catalogue.js', route)
                    self.assertIn(variable, route)
                placeholder = (ROOT / "database" / category / f"{category}-data.js").read_text(encoding="utf-8")
                self.assertIn(variable, placeholder)

    def test_shared_renderer_covers_all_routes_that_still_load_it(self):
        source = (ROOT / "database" / "extended-catalogue.js").read_text(encoding="utf-8")
        for schema in (
            "dead-signal-attachments",
            "dead-signal-deviations",
            "dead-signal-cradles",
        ):
            self.assertIn(schema, source)

    def test_dedicated_current_category_routes_enforce_supported_contracts(self):
        calibrations = (ROOT / "database" / "calibrations" / "index.html").read_text(encoding="utf-8")
        self.assertIn("dead-signal-calibrations", calibrations)
        self.assertIn("ready-current-system", calibrations)
        self.assertIn("expected_current_families === 94", calibrations)

        mods = (ROOT / "database" / "mods" / "index.html").read_text(encoding="utf-8")
        self.assertIn("dead-signal-mods", mods)
        self.assertIn("mod-code-family-projection-variants-preserved", mods)
        self.assertIn("main_entry_effects", mods)

    def test_build_lab_loads_canonical_contracts_guard_and_bridge_before_legacy_app(self):
        route = (ROOT / "preview" / "build-lab" / "index.html").read_text(encoding="utf-8")
        app_index = route.index('src="app.js')
        guard_index = route.index('src="canonical-category-variant-guard.js')
        bridge_index = route.index('src="canonical-category-bridge.js')
        self.assertLess(guard_index, bridge_index)
        self.assertLess(bridge_index, app_index)
        for category in self.BUILD_LAB_CATEGORIES:
            contract_index = route.index(f'src="{category}-data.js')
            self.assertLess(contract_index, guard_index)

    def test_variant_guard_covers_family_contracts_that_preserve_source_variants(self):
        source = (ROOT / "preview" / "build-lab" / "canonical-category-variant-guard.js").read_text(encoding="utf-8")
        self.assertIn("DS_DEVIATIONS_WEB", source)
        self.assertIn("DS_CRADLES_WEB", source)
        self.assertIn("family.variants.length !== 1", source)

    def test_copy_only_manifest_deploys_prepared_routes_and_build_lab_bridge(self):
        manifest = (ROOT / ".cpanel.yml").read_text(encoding="utf-8")
        self.assertNotIn("/bin/rm", manifest)
        for category in ("armor", *self.CATEGORIES):
            self.assertIn(f"database/{category}", manifest)
        self.assertIn("database/extended-catalogue.js", manifest)
        self.assertIn("database/extended-catalogue.css", manifest)
        for category in self.BUILD_LAB_CATEGORIES:
            self.assertIn(
                f"database/{category}/{category}-data.js $DEPLOYPATH/{category}-data.js",
                manifest,
            )
        self.assertIn(
            "preview/build-lab/canonical-category-variant-guard.js $DEPLOYPATH/canonical-category-variant-guard.js",
            manifest,
        )
        self.assertIn(
            "preview/build-lab/canonical-category-bridge.js $DEPLOYPATH/canonical-category-bridge.js",
            manifest,
        )
        for forbidden in ("python ", "python3 ", "unzip ", "curl ", "wget ", "find "):
            self.assertNotIn(forbidden, manifest.casefold())


if __name__ == "__main__":
    unittest.main()
