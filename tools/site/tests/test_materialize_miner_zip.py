from __future__ import annotations

import importlib.util
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "materialize-miner-zip.py"
SPEC = importlib.util.spec_from_file_location("materialize_miner_zip", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MinerZipMaterializerTests(unittest.TestCase):
    def test_path_traversal_member_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "bad.zip"
            destination = root / "out"
            destination.mkdir()
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("../escape.txt", "nope")
            with self.assertRaisesRegex(ValueError, "escapes extraction root"):
                MODULE._extract_archive(archive, destination)
            self.assertFalse((root / "escape.txt").exists())

    def test_dry_run_delegates_to_existing_transactional_materializer(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "miner.zip"
            repository = root / "repo"
            repository.mkdir()
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("web/weapons.json", "{}")

            calls = []
            fake = types.SimpleNamespace(
                ingest_snapshot=lambda published, repository_root, dry_run: calls.append(
                    (published, repository_root, dry_run)
                ) or {"status": "validated-dry-run", "outputs_replaced": False}
            )
            with mock.patch.object(MODULE, "_load_materializer", return_value=fake):
                report = MODULE.materialize_zip(archive, repository_root=repository, dry_run=True)

            self.assertEqual("validated-dry-run", report["status"])
            self.assertFalse(report["outputs_replaced"])
            self.assertEqual(1, len(calls))
            _published, used_repo, used_dry_run = calls[0]
            self.assertEqual(repository.resolve(), used_repo)
            self.assertTrue(used_dry_run)


if __name__ == "__main__":
    unittest.main()
