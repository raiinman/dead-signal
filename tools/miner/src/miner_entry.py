"""Dead Signal Miner entrypoint with compact publishing and Data Intelligence."""

from __future__ import annotations

import importlib
import time
from pathlib import Path

import miner_core
import armor_tier_completion
import mod_frame_enrichment
import weapon_evidence_enrichment
import weapon_reference_filter
import weapon_typed_seed_trace
import research_window
from dead_signal_analytics import DeadSignalAnalytics
from dead_signal_intelligence_hub import open_data_intelligence
from dead_signal_pipeline_inspector import PipelineRecorder
from dead_signal_publication_gate import build_gate_report
from dead_signal_research_suite import run_research_suite


weapon_reference_filter.install(weapon_evidence_enrichment)
weapon_typed_seed_trace.install(weapon_evidence_enrichment)

_original_link_published_images = miner_core.link_published_images
_original_run_module_main = miner_core.run_module_main
_original_run_pipeline = miner_core.run_pipeline
_original_self_test = miner_core.self_test
_original_open_research_console = research_window.open_research_console
_active_pipeline_recorder: PipelineRecorder | None = None


def open_dead_signal_data_intelligence(parent, output):
    """Open the branded research hub while preserving the exact-evidence console."""
    return open_data_intelligence(parent, output, _original_open_research_console)


def run_module_main_with_completion(module_name, arguments, log):
    arguments = list(arguments)
    started = time.perf_counter()
    status = "complete"
    error_text = None
    try:
        result = _original_run_module_main(module_name, arguments, log)

        def argument(name):
            index = arguments.index(name)
            return arguments[index + 1]

        if module_name == "normalize_armor":
            armor_tier_completion.complete_file(argument("--base"), argument("--current"), argument("--output"), log)
        elif module_name == "normalize_weapons":
            base = Path(argument("--base"))
            current = Path(argument("--current"))
            weapons_output = Path(argument("--output"))
            weapon_evidence_enrichment.enrich_file(base, current, weapons_output, log)
            reports = weapons_output.parent.parent / "reports"
            research = run_research_suite(base, current, weapons_output, reports)
            log(
                "Dead Signal research suite ready: "
                + f"{research.get('record_counts', {}).get('profiled_tables', 0)} profiled tables; "
                + f"Source Finder states {research.get('record_counts', {}).get('source_finder_states', {})}."
            )
        elif module_name == "normalize_extended":
            mod_frame_enrichment.enrich_file(argument("--base"), argument("--current"), Path(argument("--output-dir")) / "mods.json", log)
        elif module_name == "publish_web_data":
            projector = importlib.import_module("project_weapon_evidence")
            published = Path(argument("--published"))
            projected = projector.project_file(Path(argument("--data-dir")) / "weapons.json", published / "web" / "weapons.json")
            log("Projected Weapon verification evidence: " + f"{projected.get('record_counts', {}).get('effect_resolution_statuses', {})}.")
        return result
    except Exception as error:
        status = "failed"
        error_text = f"{type(error).__name__}: {error}"
        raise
    finally:
        if _active_pipeline_recorder is not None:
            _active_pipeline_recorder.record(
                f"module:{module_name}",
                status=status,
                duration_seconds=time.perf_counter() - started,
                details={"arguments": [str(value) for value in arguments[:20]]},
                error=error_text,
            )


def link_images_and_publish_extended(published, log):
    started = time.perf_counter()
    try:
        result = _original_link_published_images(published, log)
        publisher = importlib.import_module("publish_extended_web_data")
        outputs = publisher.publish(published / "data", published)
        mod_projector = importlib.import_module("project_mod_frame_evidence")
        mod_path = published / "web" / "mods.json"
        projected_mods = mod_projector.project_file(published / "data" / "mods.json", mod_path)
        outputs["mods"]["record_counts"] = projected_mods.get("record_counts", {})
        outputs["mods"]["mod_frame_evidence_status"] = projected_mods.get("mod_frame_evidence_status")
        calibration_projector = importlib.import_module("publish_current_calibrations")
        calibration_path = published / "web" / "calibrations.json"
        calibration = calibration_projector.project_file(calibration_path)
        outputs["calibrations"]["record_counts"] = calibration.get("record_counts", {})
        outputs["calibrations"]["publication_status"] = calibration.get("publication_status")
        log("Published compact extended website contracts: " + ", ".join(sorted(outputs)))
        return result
    finally:
        if _active_pipeline_recorder is not None:
            _active_pipeline_recorder.record(
                "extended-publishing",
                duration_seconds=time.perf_counter() - started,
                details={"published": str(published)},
            )


def run_pipeline_with_intelligence(config, log, progress, cancel=None):
    """Run the proven pipeline, then finish non-publishing intelligence products."""
    global _active_pipeline_recorder
    recorder = PipelineRecorder()
    _active_pipeline_recorder = recorder
    result = None
    try:
        result = _original_run_pipeline(config, log, progress, cancel)
        output = Path(result.get("config", {}).get("output") or config.output).expanduser().resolve()
        reports = output / "published" / "reports"

        started = time.perf_counter()
        try:
            gate = build_gate_report(reports)
            recorder.record(
                "data-intelligence:publication-gate",
                duration_seconds=time.perf_counter() - started,
                details={"publishable_candidates": gate.get("record_counts", {}).get("publishable_candidates", 0)},
            )
            log("Dead Signal Publication Gate review generated (advisory; public data unchanged).")
        except Exception as error:  # research add-ons must not invalidate a healthy extraction
            recorder.record(
                "data-intelligence:publication-gate",
                status="failed",
                duration_seconds=time.perf_counter() - started,
                error=f"{type(error).__name__}: {error}",
            )
            log(f"Data Intelligence warning: Publication Gate report failed: {error}")

        started = time.perf_counter()
        try:
            analytics = DeadSignalAnalytics(output).build()
            recorder.record(
                "data-intelligence:analytics-warehouse",
                duration_seconds=time.perf_counter() - started,
                details=analytics.get("rows", {}),
            )
            log("Dead Signal Analytics warehouse refreshed.")
        except Exception as error:  # packaging/dependency diagnostics stay non-fatal
            recorder.record(
                "data-intelligence:analytics-warehouse",
                status="failed",
                duration_seconds=time.perf_counter() - started,
                error=f"{type(error).__name__}: {error}",
            )
            log(f"Data Intelligence warning: analytics warehouse unavailable: {error}")

        recorder.report(output, result=result)
        return result
    except Exception:
        try:
            output = Path(getattr(config, "output", ".")).expanduser().resolve()
            recorder.report(output, result=result)
        except Exception:
            pass
        raise
    finally:
        _active_pipeline_recorder = None


def self_test_with_extended_publisher():
    checks = _original_self_test()
    resources = (
        miner_core.EXTRACTOR_ROOT / "publish_extended_web_data.py",
        miner_core.EXTRACTOR_ROOT / "publish_current_calibrations.py",
        miner_core.EXTRACTOR_ROOT / "armor_tier_normalization.py",
        miner_core.EXTRACTOR_ROOT / "armor_tier_completion.py",
        miner_core.EXTRACTOR_ROOT / "mod_frame_enrichment.py",
        miner_core.EXTRACTOR_ROOT / "project_mod_frame_evidence.py",
        miner_core.EXTRACTOR_ROOT / "weapon_evidence_enrichment.py",
        miner_core.EXTRACTOR_ROOT / "weapon_reference_filter.py",
        miner_core.EXTRACTOR_ROOT / "weapon_typed_seed_trace.py",
        miner_core.EXTRACTOR_ROOT / "project_weapon_evidence.py",
        miner_core.EXTRACTOR_ROOT / "investigate_weapon_descriptions.py",
        miner_core.EXTRACTOR_ROOT / "investigate_weapon_description_sources.py",
        miner_core.ROOT / "dead_signal_research_suite.py",
        miner_core.ROOT / "dead_signal_source_finder.py",
        miner_core.ROOT / "dead_signal_table_profiler.py",
        miner_core.ROOT / "dead_signal_intelligence_window.py",
        miner_core.ROOT / "dead_signal_intelligence_advanced.py",
        miner_core.ROOT / "dead_signal_intelligence_hub.py",
        miner_core.ROOT / "dead_signal_analytics.py",
        miner_core.ROOT / "dead_signal_evidence_graph.py",
        miner_core.ROOT / "dead_signal_workflow_lab.py",
        miner_core.ROOT / "dead_signal_pipeline_inspector.py",
        miner_core.ROOT / "dead_signal_publication_gate.py",
        miner_core.ROOT / "neox_data_explorer.py",
    )
    for resource in resources:
        checks.setdefault("resources", {})[str(resource)] = resource.is_file()
    for module_name in (
        "publish_extended_web_data", "publish_current_calibrations", "armor_tier_normalization",
        "armor_tier_completion", "mod_frame_enrichment", "project_mod_frame_evidence",
        "weapon_evidence_enrichment", "weapon_reference_filter", "weapon_typed_seed_trace",
        "project_weapon_evidence", "research_console", "research_window",
        "dead_signal_research_suite", "dead_signal_source_finder", "dead_signal_table_profiler",
        "dead_signal_intelligence_window", "dead_signal_intelligence_advanced", "dead_signal_intelligence_hub",
        "dead_signal_analytics", "dead_signal_evidence_graph", "dead_signal_workflow_lab",
        "dead_signal_pipeline_inspector", "dead_signal_publication_gate", "neox_data_explorer",
        "investigate_weapon_descriptions", "investigate_weapon_description_sources",
        "duckdb", "polars", "pyarrow",
    ):
        try:
            module = importlib.import_module(module_name)
            checks.setdefault("imports", {})[module_name] = getattr(module, "__version__", "ok")
        except Exception as error:
            checks.setdefault("imports", {})[module_name] = f"ERROR: {type(error).__name__}: {error}"
    checks["ok"] = bool(all(checks.get("resources", {}).values()) and all(not str(value).startswith("ERROR") for value in checks.get("imports", {}).values()) and checks.get("installations"))
    return checks


miner_core.run_module_main = run_module_main_with_completion
miner_core.link_published_images = link_images_and_publish_extended
miner_core.run_pipeline = run_pipeline_with_intelligence
miner_core.self_test = self_test_with_extended_publisher
research_window.open_research_console = open_dead_signal_data_intelligence

from dead_signal_miner import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
