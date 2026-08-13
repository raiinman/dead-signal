from __future__ import annotations

import importlib.util
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "inspect-published-snapshot.py"
SPEC = importlib.util.spec_from_file_location("inspect_published_snapshot", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class SnapshotInspectionTests(unittest.TestCase):
    def _published(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "published"
        root.mkdir()
        return temporary, root

    def _deps(self, validation_error=None, audit_error=None):
        weapons = types.SimpleNamespace(
            resolve_source=lambda root: root / "web" / "weapons.json",
            load_contract=lambda _path: {"schema": "dead-signal-weapons"},
            audit=lambda _payload: {"schema": "weapons-audit", "counts": {"weapons": 120}},
        )
        armor = types.SimpleNamespace(
            resolve_source=lambda root: root / "web" / "armor.json",
            load_contract=lambda _path: {"schema": "dead-signal-armor"},
            audit=lambda _payload: {"schema": "armor-audit", "counts": {"armor_pieces": 173}},
        )
        if audit_error == "extended":
            extended_audit = lambda _root: (_ for _ in ()).throw(ValueError("forced extended audit failure"))
        else:
            extended_audit = lambda _root: {"summary": {"mod_multi_variant_families": 4}}
        extended = types.SimpleNamespace(audit_root=extended_audit)

        def validate_snapshot(root, site_dir):
            if validation_error:
                raise ValueError(validation_error)
            return ({}, {"status": "validated", "published_root": str(root), "contracts": {}}, ())

        materializer = types.SimpleNamespace(validate_snapshot=validate_snapshot)
        return {"weapons": weapons, "armor": armor, "extended": extended, "materializer": materializer}

    def test_valid_snapshot_receipt_allows_next_step_and_keeps_audits(self):
        temporary, published = self._published()
        self.addCleanup(temporary.cleanup)
        with mock.patch.object(module, "_dependencies", return_value=self._deps()):
            report = module.inspect_snapshot(published, site_dir=Path("unused"))

        self.assertEqual("PASS", report["strict_validation"]["status"])
        self.assertTrue(report["decision"]["may_materialize"])
        self.assertEqual("OK", report["audits"]["weapons"]["status"])
        self.assertEqual("OK", report["audits"]["armor"]["status"])
        self.assertEqual("OK", report["audits"]["extended"]["status"])
        self.assertEqual([], report["decision"]["audit_sections_with_errors"])

    def test_validation_failure_keeps_all_audit_sections(self):
        temporary, published = self._published()
        self.addCleanup(temporary.cleanup)
        with mock.patch.object(module, "_dependencies", return_value=self._deps(validation_error="bad attachments")):
            report = module.inspect_snapshot(published, site_dir=Path("unused"))

        self.assertEqual("FAIL", report["strict_validation"]["status"])
        self.assertFalse(report["decision"]["may_materialize"])
        self.assertIn("bad attachments", report["strict_validation"]["error"])
        self.assertEqual("OK", report["audits"]["weapons"]["status"])
        self.assertEqual("OK", report["audits"]["armor"]["status"])
        self.assertEqual("OK", report["audits"]["extended"]["status"])

    def test_one_audit_failure_is_isolated_and_reported(self):
        temporary, published = self._published()
        self.addCleanup(temporary.cleanup)
        with mock.patch.object(module, "_dependencies", return_value=self._deps(audit_error="extended")):
            report = module.inspect_snapshot(published, site_dir=Path("unused"))

        self.assertEqual("PASS", report["strict_validation"]["status"])
        self.assertTrue(report["decision"]["may_materialize"])
        self.assertEqual("ERROR", report["audits"]["extended"]["status"])
        self.assertEqual(["extended"], report["decision"]["audit_sections_with_errors"])
        self.assertIn("forced extended audit failure", report["audits"]["extended"]["error"])

    def test_missing_published_directory_stops_before_dependency_loading(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "missing"
            with mock.patch.object(module, "_dependencies") as dependencies:
                with self.assertRaises(FileNotFoundError):
                    module.inspect_snapshot(missing)
            dependencies.assert_not_called()


if __name__ == "__main__":
    unittest.main()
