import json
import tempfile
import unittest
from pathlib import Path

from dead_signal_table_registry import TableRegistry, profile_json, run_table_registry


class TableRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.root / "base"
        self.current = self.root / "current"
        self.reports = self.root / "published" / "reports"
        self.base.mkdir()
        self.current.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, root, relative, payload):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_schema_profile_preserves_scalar_list_and_dict_reference_shapes(self):
        path = self._write(self.base, "client_data/example.json", {
            "one": {"id": 1, "owner_id": 9, "skill_list": [10, 11], "entry_map": {"a": 12}, "display_name": "Alpha"},
            "two": {"id": 2, "owner_id": None, "skill_list": [], "entry_map": {}, "display_name": "Beta"},
        })
        profile = profile_json(path)
        fields = {row["name"]: row for row in profile["fields"]}
        self.assertEqual(2, profile["record_count"])
        self.assertEqual("keyed-object-map", profile["key_shape"])
        self.assertIn("$map_key", profile["candidate_keys"])
        self.assertEqual("scalar", fields["owner_id"]["reference_kind"])
        self.assertEqual("list", fields["skill_list"]["reference_kind"])
        self.assertEqual("dict", fields["entry_map"]["reference_kind"])
        self.assertTrue(fields["display_name"]["presentation_hint"])
        self.assertIn({"path": "skill_list[]", "value_type": "integer", "observations": 2}, profile["nested_shapes"])

    def test_normalized_data_wrapper_profiles_the_underlying_record_map(self):
        path = self._write(self.base, "client_data/bullet_pattern_data.json", {
            "data": {"Pat1": {"bullet_num": 1}, "Pat2": {"bullet_num": 5}}
        })
        profile = profile_json(path)
        self.assertEqual(2, profile["record_count"])
        self.assertEqual("object.data-map", profile["key_shape"])
        self.assertIn("$map_key", profile["candidate_keys"])
        self.assertEqual(["bullet_num"], [field["name"] for field in profile["fields"]])

    def test_incremental_fingerprints_reuse_and_invalidate_only_changed_table(self):
        self._write(self.base, "game_common/data/a.json", [{"id": 1}])
        changed = self._write(self.current, "client_data/b.json", [{"gun_id": 2}])
        first = run_table_registry(self.base, self.current, self.root, self.reports)
        self.assertEqual(2, first["cache_statistics"]["tables_reprofiled"])
        second = run_table_registry(self.base, self.current, self.root, self.reports)
        self.assertEqual(0, second["cache_statistics"]["tables_reprofiled"])
        self.assertEqual(2, second["cache_statistics"]["tables_reused"])
        changed.write_text(json.dumps([{"gun_id": 3}, {"gun_id": 4}]), encoding="utf-8")
        third = run_table_registry(self.base, self.current, self.root, self.reports)
        self.assertEqual(1, third["cache_statistics"]["tables_reprofiled"])
        self.assertEqual(1, third["cache_statistics"]["tables_reused"])

    def test_base_and_current_same_path_coexist_with_current_queryable(self):
        relative = "client_data/bullet_pattern_data.json"
        self._write(self.base, relative, {"Pat1": {"bullet_num": 1}})
        self._write(self.current, relative, {"Pat1": {"bullet_num": 5}})
        result = run_table_registry(self.base, self.current, self.root, self.reports)
        registry = TableRegistry(result["database"])
        base = registry.get_table("base", relative)
        current = registry.get_table("current", relative)
        self.assertIsNotNone(base)
        self.assertIsNotNone(current)
        self.assertNotEqual(base["sha256"], current["sha256"])
        effective = registry.query_effective_tables(namespace="client_data")
        self.assertEqual(1, len(effective))
        self.assertEqual("current", effective[0]["layer"])
        self.assertEqual(2, result["client_data_census"]["record_counts"]["tables"])
        self.assertEqual(1, result["client_data_census"]["record_counts"]["base_and_current_paths"])

    def test_client_data_is_first_class_and_census_is_deterministic(self):
        self._write(self.base, "client_data/cradle_override_style_data.json", {
            "row": {"weapon_id": 1, "translation_key": "Cradle_1", "display_desc": ""}
        })
        self._write(self.current, "game_common/data/weapon_data.json", {"row": {"weapon_id": 1}})
        result = run_table_registry(self.base, self.current, self.root, self.reports)
        census = result["client_data_census"]
        self.assertEqual(1, census["record_counts"]["tables"])
        table = census["tables"][0]
        self.assertIn("Cradle", table["domains"])
        self.assertIn("weapon_id", table["reference_fields"])
        self.assertIn("translation_key", table["translation_fields"])
        self.assertIn("display_desc", table["presentation_fields"])
        on_disk = json.loads((self.reports / "client-data-census.json").read_text(encoding="utf-8"))
        self.assertEqual(census["record_counts"], on_disk["record_counts"])


if __name__ == "__main__":
    unittest.main()
