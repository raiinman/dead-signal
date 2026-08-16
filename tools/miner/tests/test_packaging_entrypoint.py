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

    def test_build_packages_data_intelligence_runtime(self) -> None:
        miner_root = Path(__file__).resolve().parents[1]
        build_script = (miner_root / "build.ps1").read_text(encoding="utf-8")
        requirements = (miner_root / "requirements.txt").read_text(encoding="utf-8")
        for module in (
            "dead_signal_intelligence_hub",
            "dead_signal_analytics",
            "dead_signal_discovery",
            "dead_signal_verification",
            "dead_signal_verification_tab",
            "dead_signal_evidence_graph",
            "dead_signal_workflow_lab",
            "dead_signal_pipeline_inspector",
            "dead_signal_publication_gate",
            "dead_signal_multihop_resolver",
            "dead_signal_research_cache",
            "dead_signal_weapon_description_consumer",
            "neox_data_explorer",
        ):
            self.assertIn(module, build_script)
        for dependency in ("duckdb", "polars", "pyarrow"):
            self.assertIn(f"--collect-all', '{dependency}", build_script)
            self.assertIn(f"{dependency}==", requirements)

    def test_canonical_entrypoint_installs_publishers_and_intelligence_pipeline(self) -> None:
        miner_root = Path(__file__).resolve().parents[1]
        entrypoint = (miner_root / "src" / "miner_entry.py").read_text(encoding="utf-8")
        self.assertIn('importlib.import_module("publish_extended_web_data")', entrypoint)
        self.assertIn('importlib.import_module("publish_current_calibrations")', entrypoint)
        self.assertIn("miner_core.link_published_images = link_images_and_publish_extended", entrypoint)
        self.assertIn("miner_core.run_pipeline = run_pipeline_with_intelligence", entrypoint)
        self.assertIn("miner_core.self_test = self_test_with_extended_publisher", entrypoint)
        self.assertIn("research_window.open_research_console = open_dead_signal_data_intelligence", entrypoint)
        self.assertIn("run_research_suite", entrypoint)
        self.assertIn("DeadSignalDiscovery", entrypoint)
        self.assertIn("DeadSignalAnalytics", entrypoint)
        self.assertIn("build_gate_report", entrypoint)

    def test_data_intelligence_remains_post_run_and_nonfatal(self) -> None:
        miner_root = Path(__file__).resolve().parents[1]
        entrypoint = (miner_root / "src" / "miner_entry.py").read_text(encoding="utf-8")
        pipeline_start = entrypoint.index("def run_pipeline_with_intelligence")
        pipeline = entrypoint[pipeline_start:]
        canonical_call = pipeline.index("_original_run_pipeline")
        research_call = pipeline.index("run_research_suite")
        self.assertLess(canonical_call, research_call)
        self.assertIn("_run_nonfatal_intelligence_stage", pipeline)
        self.assertIn("public data unchanged", pipeline)


if __name__ == "__main__":
    unittest.main()