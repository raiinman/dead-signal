from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from miner_updater import (  # noqa: E402
    EXPECTED_EXECUTABLE,
    apply_update,
    locate_payload_root,
    safe_members,
    validate_target,
)


class UpdaterTests(unittest.TestCase):
    def test_archive_path_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../outside.txt", "no")
            with zipfile.ZipFile(archive_path) as archive:
                with self.assertRaises(ValueError):
                    safe_members(archive)

    def test_payload_root_is_found_inside_single_wrapper_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root / "Dead Signal Miner"
            payload.mkdir()
            (payload / EXPECTED_EXECUTABLE).write_bytes(b"exe")
            self.assertEqual(locate_payload_root(root), payload)

    def test_non_miner_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                validate_target(Path(temporary))

    def test_verified_package_updates_existing_installation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "installed" / "Dead Signal Miner"
            target.mkdir(parents=True)
            (target / EXPECTED_EXECUTABLE).write_bytes(b"old-executable")
            (target / "old-only.txt").write_text("preserved", encoding="utf-8")
            package = root / "update.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr(f"Dead Signal Miner/{EXPECTED_EXECUTABLE}", b"new-executable")
                archive.writestr("Dead Signal Miner/_internal/VERSION", "1.5.9.0")
            digest = hashlib.sha256(package.read_bytes()).hexdigest()

            copied = apply_update(package, target, digest)

            self.assertEqual(copied, 2)
            self.assertEqual((target / EXPECTED_EXECUTABLE).read_bytes(), b"new-executable")
            self.assertEqual((target / "_internal" / "VERSION").read_text(encoding="utf-8"), "1.5.9.0")
            self.assertEqual((target / "old-only.txt").read_text(encoding="utf-8"), "preserved")


if __name__ == "__main__":
    unittest.main()

