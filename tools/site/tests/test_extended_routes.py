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
    BUILD_LAB_CATEGORIES = ("calibrations", "mods", "attachments", "deviations", "cradles")

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
        self.assertIn("data.schema_version === 2", source)
        self.assertIn("direct-localized-installed-game-text", source)

    def test_dedicated_current_category_routes_enforce_supported_contracts(self):
        calibrations = (ROOT / "database" / "calibrations" / "index.html").read_text(encoding="utf-8")
        self.assertIn("dead-signal-calibrations", calibrations)
        self.assertIn("ready-current-system", calibrations)
        self.assertIn("expected_current_families === 94", calibrations)

        mods = (ROOT / "database" / "mods" / "index.html").read_text(encoding="utf-8")
        self.assertIn("dead-signal-mods", mods)
        self.assertIn("mod-code-family-projection-variants-preserved", mods)
        self.assertIn("main_entry_effects", mods)

    def test_build_lab_v2_loads_current_contracts_and_shared_workstation_shell(self):
        route = (ROOT / "preview" / "build-lab" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/shared/readability.css"', route)
        self.assertIn('href="/shared/workstation-shell.css"', route)
        self.assertIn('src="/shared/readability.js"', route)
        self.assertIn('src="/shared/workstation-shell.js"', route)
        self.assertIn('src="/database/weapons/weapons-data.js', route)
        self.assertIn('src="/database/weapons/weapon-public-adapter.js', route)
        self.assertIn('src="/database/armor/armor-data.js', route)
        for category in self.BUILD_LAB_CATEGORIES:
            self.assertIn(f'src="/database/{category}/{category}-data.js', route)
        self.assertNotIn('src="app.js', route)
        self.assertNotIn('data/community-data.js', route)
        for variable in (
            "DS_WEAPON_MATH",
            "DS_ARMOR_WEB",
            "DS_MODS_WEB",
            "DS_CALIBRATIONS_WEB",
            "DS_ATTACHMENTS_WEB",
            "DS_DEVIATIONS_WEB",
            "DS_CRADLES_WEB",
        ):
            self.assertIn(variable, route)
        self.assertIn("family.variants", (ROOT / "preview" / "build-lab" / "canonical-category-variant-guard.js").read_text(encoding="utf-8"))
        self.assertIn("multiple-source-variants-preserved", route)

    def test_variant_guard_blocks_ambiguous_families_and_accepts_attachment_v2(self):
        source = (ROOT / "preview" / "build-lab" / "canonical-category-variant-guard.js").read_text(encoding="utf-8")
        self.assertIn("DS_DEVIATIONS_WEB", source)
        self.assertIn("DS_CRADLES_WEB", source)
        self.assertIn("family.variants.length !== 1", source)
        self.assertIn("attachments.schema_version === 2", source)
        self.assertIn("direct-localized-installed-game-text", source)

    def test_calibration_bridge_requires_proven_secondary_pool(self):
        source = (ROOT / "preview" / "build-lab" / "canonical-category-bridge.js").read_text(encoding="utf-8")
        self.assertIn("secondary_pool_failure_ids", source)
        self.assertIn("current-system-selected-from-shared-buff-identity-and-proven-main-plus-secondary-rolls", source)
        self.assertIn("secondary_roll_candidates", source)
        self.assertIn("observed_candidate_weights", source)

    def test_copy_only_manifest_deploys_prepared_routes_and_build_lab_bridge(self):
        manifest = (ROOT / ".cpanel.yml").read_text(encoding="utf-8")
        self.assertNotIn("/bin/rm", manifest)
        for category in ("armor", *self.CATEGORIES):
            self.assertIn(f"database/{category}", manifest)
        self.assertIn("database/extended-catalogue.js", manifest)
        self.assertIn("database/extended-catalogue.css", manifest)
        for category in ("calibrations", "attachments", "deviations", "cradles"):
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
