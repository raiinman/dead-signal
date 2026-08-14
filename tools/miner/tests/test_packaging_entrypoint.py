from pathlib import Path
import unittest


class PackagingEntrypointTests(unittest.TestCase):
    def test_build_uses_canonical_entrypoint_and_publishers(self) -> None:
        miner_root = Path(__file__).resolve().parents[1]
        build_script = (miner_root / "build.ps1").read_text(encoding="utf-8")
        self.assertIn("miner_entry.py", build_script)
        self.assertNotIn("$MainArguments += (Join-Path $Source 'dead_signal_miner.py')", build_script)
        self.assertIn("publish_extended_web_data", build_script)
        self.assertIn("publish_current_calibrations", build_script)
        self.assertIn("'research_console', 'research_window'", build_script)

    def test_canonical_entrypoint_installs_both_publishers(self) -> None:
        miner_root = Path(__file__).resolve().parents[1]
        entrypoint = (miner_root / "src" / "miner_entry.py").read_text(encoding="utf-8")
        self.assertIn('importlib.import_module("publish_extended_web_data")', entrypoint)
        self.assertIn('importlib.import_module("publish_current_calibrations")', entrypoint)
        self.assertIn("miner_core.link_published_images = link_images_and_publish_extended", entrypoint)
        self.assertIn("miner_core.self_test = self_test_with_extended_publisher", entrypoint)


if __name__ == "__main__":
    unittest.main()
