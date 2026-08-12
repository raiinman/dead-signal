from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from update_manager import UpdateError, parse_manifest, version_key  # noqa: E402


class UpdateManifestTests(unittest.TestCase):
    def test_numeric_versions_are_compared_by_component(self) -> None:
        self.assertGreater(version_key("1.5.10.0"), version_key("1.5.9.9"))

    def test_current_version_is_not_an_update(self) -> None:
        info = parse_manifest(
            {
                "schema_version": 1,
                "version": "1.5.8.0",
                "channel": "stable",
                "download_url": None,
                "sha256": None,
                "size": None,
                "notes_url": None,
            },
            "1.5.8.0",
        )
        self.assertFalse(info.update_available)
        self.assertFalse(info.installable)

    def test_newer_verified_github_package_is_installable(self) -> None:
        info = parse_manifest(
            {
                "schema_version": 1,
                "version": "1.5.9.0",
                "channel": "stable",
                "download_url": "https://github.com/raiinman/dead-signal/releases/download/v1.5.9.0/miner.zip",
                "sha256": "a" * 64,
                "size": 12345,
                "notes_url": "https://github.com/raiinman/dead-signal/releases/tag/v1.5.9.0",
            },
            "1.5.8.0",
        )
        self.assertTrue(info.update_available)
        self.assertTrue(info.installable)

    def test_non_github_download_is_rejected(self) -> None:
        with self.assertRaises(UpdateError):
            parse_manifest(
                {
                    "schema_version": 1,
                    "version": "1.5.9.0",
                    "download_url": "https://example.com/miner.zip",
                    "sha256": "a" * 64,
                    "size": 12345,
                },
                "1.5.8.0",
            )

    def test_invalid_hash_is_rejected(self) -> None:
        with self.assertRaises(UpdateError):
            parse_manifest(
                {
                    "schema_version": 1,
                    "version": "1.5.9.0",
                    "download_url": "https://github.com/raiinman/dead-signal/releases/download/v1.5.9.0/miner.zip",
                    "sha256": "not-a-hash",
                    "size": 12345,
                },
                "1.5.8.0",
            )


if __name__ == "__main__":
    unittest.main()

