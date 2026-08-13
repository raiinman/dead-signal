import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "materialize-armor-web.py"
SPEC = importlib.util.spec_from_file_location("materialize_armor_web", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ArmorMaterializerTests(unittest.TestCase):
    def fixture(self):
        return {
            "schema": "dead-signal-armor",
            "schema_version": 1,
            "generated_utc": "2026-08-13T00:00:00+00:00",
            "record_counts": {"armor_sets": 2, "armor_pieces": 3},
            "armor_sets": [
                {
                    "canonical_id": "ds-as-10",
                    "suit_id": 10,
                    "name": "Base Set",
                    "pieces": [
                        {"canonical_id": "ds-a-10-100", "suit_id": 10, "blueprint_id": 100, "name": "Base Mask"}
                    ],
                },
                {
                    "canonical_id": "ds-as-20",
                    "suit_id": 20,
                    "name": "Heat Set",
                    "pieces": [
                        {"canonical_id": "ds-a-20-100", "suit_id": 20, "blueprint_id": 100, "name": "Heat Mask"}
                    ],
                },
            ],
            "key_armor": [
                {"canonical_id": "ds-ka-300", "blueprint_id": 300, "name": "Key Top"}
            ],
            "crafting_material_groups": {},
        }

    def test_variant_aware_piece_ids_are_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "armor.json"
            path.write_text(json.dumps(self.fixture()), encoding="utf-8")
            payload = MODULE.load_and_validate(path)
            self.assertEqual(2, len(payload["armor_sets"]))

    def test_duplicate_public_piece_id_is_rejected(self):
        payload = self.fixture()
        payload["armor_sets"][1]["pieces"][0]["canonical_id"] = "ds-a-10-100"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "armor.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                MODULE.load_and_validate(path)

    def test_browser_output_wraps_exact_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "armor.json"
            output = root / "armor-data.js"
            payload = self.fixture()
            source.write_text(json.dumps(payload), encoding="utf-8")
            MODULE.write_browser_payload(source, output, payload)
            text = output.read_text(encoding="utf-8")
            self.assertIn("window.DS_ARMOR_WEB=", text)
            self.assertIn('"ds-a-20-100"', text)


if __name__ == "__main__":
    unittest.main()
