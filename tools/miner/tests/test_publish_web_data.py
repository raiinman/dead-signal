import json
import tempfile
import unittest
from pathlib import Path

from extractor.publish_web_data import (
    build_armor_projection,
    build_change_report,
    build_quality_report,
    build_relationship_graph,
    build_snapshot_manifest,
    build_weapon_projection,
    publish,
)


class PublishWebDataTests(unittest.TestCase):
    def write(self, root: Path, name: str, payload: dict) -> None:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def fixture(self, root: Path) -> Path:
        data = root / "data"
        data.mkdir(parents=True, exist_ok=True)
        tiers = [
            {
                "tier": tier,
                "item_id": 100 + tier,
                "damage": 100 * tier,
                "recipe": {"forge_no": 200 + tier, "fixed_materials": []},
            }
            for tier in range(1, 6)
        ]
        self.write(
            data,
            "weapons.json",
            {
                "record_counts": {"weapons": 1},
                "weapons": [
                    {
                        "blueprint_id": 10,
                        "item_id": 11,
                        "name": "Test Rifle",
                        "category": "Assault Rifle",
                        "weapon_type_code": 4,
                        "prototype_id": 12,
                        "quality": "Legendary",
                        "quality_code": 4,
                        "image_asset": "assets/test.webp",
                        "short_description": "A test weapon",
                        "acquisition_hint": "Test source",
                        "item_gain_path": "Test gain",
                        "fragment_id": 13,
                        "fragments_to_unlock": 40,
                        "endowed_blueprint": False,
                        "durability": 100,
                        "weight": 3,
                        "base_attributes": [{"code": "E01", "value": 0.1}],
                        "ranged_stats": {
                            "rpm": 600,
                            "magazine": 30,
                            "reload_seconds": 2.1,
                            "range_meters": 60,
                            "accuracy": 70,
                            "stability": 80,
                            "mobility": 55,
                            "full_damage_distance": 30,
                            "minimum_damage_distance": 80,
                            "minimum_damage_multiplier": 0.5,
                            "ammo_item_id": 99,
                        },
                        "effect": {
                            "skill_code": "SK_TEST",
                            "skill_level": 1,
                            "buff_id": 77,
                            "name": "Test Effect",
                            "description": "Does something.",
                            "keyword_buff_id": 78,
                            "keyword_status_id": 79,
                        },
                        "tiers": tiers,
                        "blueprint_star_progression": {"progression_effect_mode": "attack-ratio"},
                        "verification_notes": [],
                    }
                ],
            },
        )
        matrix = [
            {
                "gear_tier": tier,
                "tier_item_id": 100 + tier,
                "tier_base_attack_at_1_star": 100 * tier,
                "blueprint_star_values": [{"blueprint_stars": 1, "preset_attack_ratio": 1.0, "base_attack": 100 * tier}],
            }
            for tier in range(1, 6)
        ]
        self.write(
            data,
            "weapon-math.json",
            {
                "record_counts": {"weapons": 1, "tier_star_combinations": 5},
                "validation": {"passed": True, "issues": []},
                "formula_contract": {"base_attack": "int(base * ratio)"},
                "weapons": [
                    {
                        "blueprint_id": 10,
                        "formula_status": "proven-static-base-attack",
                        "tier_star_matrix": matrix,
                        "validation_issues": [],
                    }
                ],
            },
        )
        self.write(
            data,
            "gun-profiles.json",
            {
                "record_counts": {"resolved_gun_profiles": 1, "unresolved_gun_profiles": 0},
                "profiles": [
                    {
                        "blueprint_id": 10,
                        "resolution_status": "resolved",
                        "gun_no": 123,
                        "accessory_slots": [{"record_id": "(123, 8)", "slot_type": 8}],
                        "linked_ids": {"bullet_no": 99, "gun_skill_no": 321},
                    }
                ],
            },
        )
        self.write(
            data,
            "weapon-configuration.json",
            {
                "schema_version": 1,
                "record_counts": {"ammo_bindings": 1},
                "application_policy": {"auto_apply": "direct only"},
                "layers": {"ammo": [], "attachments": [], "weapon_mods": [], "calibrations": []},
            },
        )
        armor_tiers = [{"data_level": tier, "item_id": 300 + tier, "hp": tier * 10} for tier in range(1, 6)]
        self.write(
            data,
            "armor-sets.json",
            {
                "record_counts": {"armor_sets": 1, "armor_pieces": 2},
                "armor_sets": [
                    {
                        "suit_id": 200,
                        "name": "Test Set",
                        "piece_count": 1,
                        "set_bonuses": [{"pieces_required": 2, "description": "Bonus"}],
                        "pieces": [
                            {
                                "blueprint_id": 201,
                                "name": "Test Mask",
                                "slot_id": 6,
                                "slot": "Mask",
                                "quality": "Legendary",
                                "quality_code": 4,
                                "image_asset": "assets/mask.webp",
                                "tiers": armor_tiers,
                                "crafting_recipes": [{"forge_no": 1}],
                            }
                        ],
                        "source_status": "mined-from-installed-game",
                        "verification_notes": [],
                    }
                ],
                "key_armor": [
                    {
                        "blueprint_id": 202,
                        "name": "Test Key Top",
                        "slot_id": 2,
                        "slot": "Top",
                        "quality": "Legendary",
                        "quality_code": 4,
                        "image_asset": "assets/top.webp",
                        "passive_skill_code": "SK_ARMOR",
                        "passive_skill_name": "Armor Skill",
                        "buff_id": 88,
                        "key_effect": "Armor effect",
                        "tiers": armor_tiers,
                        "crafting_recipes": [{"forge_no": 2}],
                        "source_status": "mined-from-installed-game",
                        "verification_notes": [],
                    }
                ],
                "crafting_material_groups": {},
            },
        )
        self.write(data, "image-coverage.json", {"totals": {"linked_records": 3}})
        return data

    def test_weapon_projection_keeps_player_facing_detail_and_profile(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            data = self.fixture(Path(folder))
            result = build_weapon_projection(data)
            weapon = result["weapons"][0]
            self.assertEqual("ds-w-10", weapon["canonical_id"])
            self.assertEqual(30, weapon["damage_profile"]["full_damage_distance"])
            self.assertEqual(5, len(weapon["progression"]["tier_star_matrix"]))
            self.assertEqual(123, weapon["gun_profile"]["gun_no"])
            self.assertEqual(1, result["configuration_catalog"]["record_counts"]["ammo_bindings"])
            self.assertEqual("Weapons v1", result["schema_contract"]["name"])
            self.assertEqual("locked", result["schema_contract"]["status"])
            self.assertEqual("complete-material-bodies", weapon["crafting"]["presentation_status"])

    def test_relationship_graph_records_direct_links_without_claiming_runtime_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            data = self.fixture(Path(folder))
            weapons = build_weapon_projection(data)
            armor = build_armor_projection(data)
            graph = build_relationship_graph(weapons, armor)
            relations = {(edge["source"], edge["relation"], edge["target"]) for edge in graph["edges"]}
            self.assertIn(("ds-w-10", "maps_to_gun", "gun:123"), relations)
            self.assertIn(("passive-skill:SK_TEST", "resolves_buff", "buff:77"), relations)
            self.assertIn(("ds-ka-202", "has_fixed_skill", "passive-skill:SK_ARMOR"), relations)
            self.assertIn("Trigger conditions", graph["scope"])

    def test_quality_uses_internal_invariants_not_external_item_counts(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            data = self.fixture(Path(folder))
            weapons = build_weapon_projection(data)
            armor = build_armor_projection(data)
            quality = build_quality_report(data, weapons, armor)
            self.assertEqual("READY", quality["categories"]["weapons"]["status"])
            self.assertEqual("READY", quality["categories"]["armor"]["status"])
            self.assertIn("never against community-site item counts", quality["policy"])

    def test_change_report_detects_added_removed_and_changed_records(self) -> None:
        previous = {"weapons": [{"canonical_id": "ds-w-1", "name": "Old"}, {"canonical_id": "ds-w-2", "name": "Same"}]}
        current = {"weapons": [{"canonical_id": "ds-w-2", "name": "Changed"}, {"canonical_id": "ds-w-3", "name": "New"}]}
        report = build_change_report(previous, None, current, {"armor_sets": [], "key_armor": []})
        delta = report["categories"]["weapons"]
        self.assertEqual(["ds-w-3"], delta["added"])
        self.assertEqual(["ds-w-1"], delta["removed"])
        self.assertEqual("ds-w-2", delta["changed"][0]["canonical_id"])

    def test_publish_writes_web_reports_graph_and_hashed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = self.fixture(root)
            published = root / "published"
            published.mkdir()
            target_data = published / "data"
            target_data.mkdir()
            for source in data.glob("*.json"):
                target_data.joinpath(source.name).write_bytes(source.read_bytes())
            result = publish(
                target_data, published, "1.5.12.0", "a" * 64, "b" * 64, "c" * 64, "resource-fingerprint"
            )
            self.assertTrue((published / "web" / "weapons.json").is_file())
            self.assertTrue((published / "web" / "weapon-configuration.json").is_file())
            self.assertTrue((published / "web" / "armor.json").is_file())
            self.assertTrue((published / "web" / "relationship-graph.json").is_file())
            self.assertTrue((published / "reports" / "data-quality.json").is_file())
            self.assertTrue((published / "reports" / "CHANGE-REPORT.txt").is_file())
            manifest = json.loads((published / "snapshot-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("1.5.12.0", manifest["miner_version"])
            self.assertEqual("a" * 64, manifest["source_fingerprints"]["base_script_sha256"])
            self.assertEqual("c" * 64, manifest["source_fingerprints"]["game_executable_sha256"])
            self.assertEqual("resource-fingerprint", manifest["source_fingerprints"]["resource_index_fingerprint"])
            self.assertIn("publish_web_data.py", manifest["source_fingerprints"]["pipeline_source_sha256"])
            self.assertTrue(any(row["path"] == "web/weapons.json" and len(row["sha256"]) == 64 for row in manifest["files"]))
            self.assertEqual("READY", result["quality"]["overall_status"])

    def test_runtime_source_has_no_wordpress_sync_path(self) -> None:
        root = Path(__file__).resolve().parents[1] / "src"
        for relative in ("miner_core.py", "dead_signal_miner.py"):
            text = (root / relative).read_text(encoding="utf-8").casefold()
            self.assertNotIn("wordpress", text, relative)

    def test_first_publish_establishes_change_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = self.fixture(root)
            published = root / "published"
            published.mkdir()
            target_data = published / "data"
            target_data.mkdir()
            for source in data.glob("*.json"):
                target_data.joinpath(source.name).write_bytes(source.read_bytes())
            result = publish(target_data, published, "1.5.12.0")
            self.assertEqual("baseline-created", result["change_report"]["status"])


if __name__ == "__main__":
    unittest.main()
