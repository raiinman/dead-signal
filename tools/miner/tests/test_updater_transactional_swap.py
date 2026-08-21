from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from miner_updater import EXPECTED_EXECUTABLE, EXPECTED_UPDATER, apply_update


class TransactionalUpdaterTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def _package(self) -> tuple[Path, str]:
        payload_root = self.root / "payload" / "Dead Signal Miner"
        payload_root.mkdir(parents=True)
        (payload_root / EXPECTED_EXECUTABLE).write_bytes(b"new-miner")
        (payload_root / EXPECTED_UPDATER).write_bytes(b"new-updater")
        (payload_root / "_internal" / "new-runtime.dll").parent.mkdir(parents=True)
        (payload_root / "_internal" / "new-runtime.dll").write_bytes(b"new-runtime")
        package = self.root / "update.zip"
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for source in payload_root.parent.rglob("*"):
                if source.is_file():
                    archive.write(source, source.relative_to(payload_root.parent))
        digest = hashlib.sha256(package.read_bytes()).hexdigest()
        return package, digest

    def _target(self) -> Path:
        target = self.root / "install" / "Dead Signal Miner"
        target.mkdir(parents=True)
        (target / EXPECTED_EXECUTABLE).write_bytes(b"old-miner")
        (target / EXPECTED_UPDATER).write_bytes(b"old-updater")
        (target / "_internal" / "obsolete-runtime.dll").parent.mkdir(parents=True)
        (target / "_internal" / "obsolete-runtime.dll").write_bytes(b"obsolete")
        (target / "old-only.txt").write_text("stale", encoding="utf-8")
        return target

    def test_update_replaces_entire_onedir_runtime_and_removes_stale_files(self):
        target = self._target()
        package, digest = self._package()
        copied = apply_update(package, target, digest)

        self.assertGreaterEqual(copied, 3)
        self.assertEqual((target / EXPECTED_EXECUTABLE).read_bytes(), b"new-miner")
        self.assertEqual((target / EXPECTED_UPDATER).read_bytes(), b"new-updater")
        self.assertTrue((target / "_internal" / "new-runtime.dll").is_file())
        self.assertFalse((target / "_internal" / "obsolete-runtime.dll").exists())
        self.assertFalse((target / "old-only.txt").exists())
        self.assertFalse(list(target.parent.glob(f".{target.name}.stage-*")))
        self.assertFalse(list(target.parent.glob(f".{target.name}.backup-*")))

    def test_hash_mismatch_leaves_existing_installation_untouched(self):
        target = self._target()
        package, _digest = self._package()
        original = (target / EXPECTED_EXECUTABLE).read_bytes()

        with self.assertRaises(ValueError):
            apply_update(package, target, "0" * 64)

        self.assertEqual((target / EXPECTED_EXECUTABLE).read_bytes(), original)
        self.assertTrue((target / "old-only.txt").is_file())


if __name__ == "__main__":
    unittest.main()
