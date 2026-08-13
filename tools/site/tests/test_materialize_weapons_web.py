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
    def payload() -> dict:
        return {
            "schema": "dead-signal-weapons",
            "schema_version": 1,
            "generated_utc": "2026-08-13T00:00:00+00:00",
            "record_counts": {"weapons": 2},
            "weapons": [
                {"canonical_id": "ds-w-100", "name": "Alpha", "nested": {"value": 7}},
                {"canonical_id": "ds-w-200", "name": "Beta", "nested": {"value": 9}},
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


if __name__ == "__main__":
    unittest.main()
