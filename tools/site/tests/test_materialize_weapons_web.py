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
                "blueprint_star_values": [
                    {"blueprint_stars": stars, "base_attack": 100 * tier + stars}
                    for stars in range(1, star_cap + 1)
                ],
            }
            for tier in range(1, 6)
        ]

    @classmethod
    def weapon(cls, canonical_id: str, name: str, rarity: str, star_cap: int, ranged: bool) -> dict:
        return {
            "canonical_id": canonical_id,
            "name": name,
            "rarity": rarity,
            "baseline": {"ranged": {"rpm": 600} if ranged else None, "melee": None if ranged else {"attack_speed": 1}},
            "progression": {
                "gear_tiers": [{"tier": tier} for tier in range(1, 6)],
                "tier_star_matrix": cls.matrix(star_cap),
                "validation_issues": [],
            },
            "nested": {"value": 7 if ranged else 9},
        }

    @classmethod
    def payload(cls) -> dict:
        return {
            "schema": "dead-signal-weapons",
            "schema_version": 1,
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
            payload["schema_version"] = 2
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

    def test_blueprint_stars_cannot_exceed_rarity_cap(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["weapons"][1]["progression"]["tier_star_matrix"][0]["blueprint_star_values"].append(
                {"blueprint_stars": 6, "base_attack": 999}
            )
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Epic Blueprint Star cap"):
                MODULE.load_and_validate(source)

    def test_matrix_rows_require_numeric_base_attack(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "weapons.json"
            payload = self.payload()
            payload["weapons"][0]["progression"]["tier_star_matrix"][0]["blueprint_star_values"][0]["base_attack"] = None
            source.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "numeric Base Attack"):
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
