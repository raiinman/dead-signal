import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "materialize-weapons-web.py"
SPEC = importlib.util.spec_from_file_location("materialize_weapons_web", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class MaterializeWeaponsWebTests(unittest.TestCase):
    @staticmethod
    def matrix(star_cap: int) -> list[dict]:
        return [
            {
                "gear_tier": tier,
                "tier_base_attack_at_1_star": 100 * tier,
                "blueprint_star_values": [
                    {
                        "blueprint_stars": stars,
                        "preset_attack_ratio": 1 + ((stars - 1) * 0.05),
                        "base_attack": int((100 * tier) * (1 + ((stars - 1) * 0.05))),
                    }
                    for stars in range(1, star_cap + 1)
                ],
            }
            for tier in range(1, 6)
        ]

    @classmethod
    def weapon(cls, canonical_id: str, name: str, rarity: str, star_cap: int, ranged: bool) -> dict:
        return {
            "schema_contract": "weapons-v1",
            "canonical_id": canonical_id,
            "name": name,
            "rarity": rarity,
            "baseline": {"ranged": {"rpm": 600} if ranged else None, "melee": None if ranged else {"attack_speed": 1}},
            "progression": {
                "gear_tiers": [{"tier": tier} for tier in range(1, 6)],
                "blueprint_stars": {
                    "semantic_status": "validated-source-axis",
                    "stars": [{"blueprint_stars": stars} for stars in range(1, star_cap + 1)],
                },
                "tier_star_matrix": cls.matrix(star_cap),
                "validation_issues": [],
            },
            "nested": {"value": 7 if ranged else 9},
            "attachment_compatibility": {"state": "resolved-four-state-relationship", "compatible_ids": [], "incompatible_ids": [], "unresolved_ids": [], "not_applicable_ids": []},
            "calibration_compatibility": {"state": "resolved-four-state-relationship", "compatible_ids": [], "incompatible_ids": [], "unresolved_ids": [], "not_applicable_ids": []},
            "ammo_configuration": {"state": "resolved-selectable-options" if ranged else "not-applicable"},
        }

    @classmethod
    def payload(cls) -> dict:
        return {
            "schema": "dead-signal-weapons",
            "schema_version": 2,
            "schema_contract": {"name": "Weapons v1", "status": "locked"},
            "generated_utc": "2026-08-13T00:00:00+00:00",
            "record_counts": {"weapons": 2, "ranged_weapons": 1, "melee_weapons": 1},
            "weapons": [
                cls.weapon("ds-w-100", "Alpha", "Legendary", 6, True),
                cls.weapon("ds-w-200", "Beta", "Epic", 5, False),
            ],
        }

    def test_materializer_wraps_exact_public_contract(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "published" / "web" / "weapons.json"
            output = root / "weapons-data.js"
            source.parent.mkdir(parents=True)
            payload = self.payload()
            source.write_text(json.dumps(payload), encoding="utf-8")

            resolved = MODULE.resolve_source(root / "published")
            loaded = MODULE.load_and_validate(resolved)
            MODULE.write_browser_payload(resolved, output, loaded)

            text = output.read_text(encoding="utf-8")
            self.assertIn("window.DS_WEAPONS_WEB=", text)
            encoded = text.split("window.DS_WEAPONS_WEB=", 1)[1].rsplit(";", 1)[0]
            self.assertEqual(payload, json.loads(encoded))

    def test_subcap_mined_star_axis_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["weapons"][1] = self.weapon("ds-w-200", "Rare Three Star", "Rare", 3, False)
            source.write_text(json.dumps(payload), encoding="utf-8")
            loaded = MODULE.load_and_validate(source)
            self.assertEqual(3, len(loaded["weapons"][1]["progression"]["blueprint_stars"]["stars"]))

    def test_duplicate_canonical_ids_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["weapons"][1]["canonical_id"] = payload["weapons"][0]["canonical_id"]
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate canonical_id"):
                MODULE.load_and_validate(source)

    def test_declared_record_count_must_match_payload(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["record_counts"]["weapons"] = 120
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "record_counts.weapons"):
                MODULE.load_and_validate(source)

    def test_schema_version_must_match_supported_contract(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["schema_version"] = 1
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "schema_version"):
                MODULE.load_and_validate(source)

    def test_gear_tiers_must_cover_unique_tier_one_through_five(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["weapons"][0]["progression"]["gear_tiers"][-1]["tier"] = 4
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unique Tier I-V"):
                MODULE.load_and_validate(source)

    def test_tier_star_matrix_must_cover_all_five_gear_tiers(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["weapons"][0]["progression"]["tier_star_matrix"].pop()
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "five Tier × Blueprint Star matrix rows"):
                MODULE.load_and_validate(source)

    def test_matrix_stars_must_match_mined_axis(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            stars = payload["weapons"][1]["progression"]["tier_star_matrix"][0]["blueprint_star_values"]
            stars.pop(1)
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly match mined Blueprint Star axis"):
                MODULE.load_and_validate(source)

    def test_mined_star_axis_must_not_exceed_rarity_cap(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            weapon = payload["weapons"][1]
            weapon["rarity"] = "Rare"
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exceeds Rare rarity cap 4"):
                MODULE.load_and_validate(source)

    def test_unknown_rarity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["weapons"][0]["rarity"] = "Mythic"
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsupported rarity"):
                MODULE.load_and_validate(source)

    def test_matrix_rows_require_numeric_tier_base_attack(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["weapons"][0]["progression"]["tier_star_matrix"][0]["tier_base_attack_at_1_star"] = None
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "numeric 1★ Base Attack evidence"):
                MODULE.load_and_validate(source)

    def test_matrix_rows_require_numeric_preset_attack_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["weapons"][0]["progression"]["tier_star_matrix"][0]["blueprint_star_values"][0]["preset_attack_ratio"] = None
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing numeric preset_attack_ratio"):
                MODULE.load_and_validate(source)

    def test_matrix_rows_require_numeric_base_attack(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["weapons"][0]["progression"]["tier_star_matrix"][0]["blueprint_star_values"][0]["base_attack"] = None
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "numeric Base Attack"):
                MODULE.load_and_validate(source)

    def test_base_attack_must_recompute_from_tier_base_and_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["weapons"][0]["progression"]["tier_star_matrix"][4]["blueprint_star_values"][5]["base_attack"] += 1
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Base Attack mismatch"):
                MODULE.load_and_validate(source)

    def test_fractional_published_base_attack_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["weapons"][0]["progression"]["tier_star_matrix"][0]["blueprint_star_values"][0]["base_attack"] = 100.5
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Base Attack mismatch"):
                MODULE.load_and_validate(source)

    def test_unresolved_progression_validation_issues_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["weapons"][0]["progression"]["validation_issues"] = ["incomplete Tier × Blueprint Star matrix"]
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unresolved progression validation issues"):
                MODULE.load_and_validate(source)

    def test_declared_ranged_and_melee_counts_must_match_payload(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["record_counts"]["ranged_weapons"] = 2
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "record_counts.ranged_weapons"):
                MODULE.load_and_validate(source)


if __name__ == "__main__":
    unittest.main()
