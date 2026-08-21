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
import dead_signal_cradle_applicability
import research_window
from dead_signal_analytics import DeadSignalAnalytics
from dead_signal_discovery import DeadSignalDiscovery
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
            weapon_evidence_enrichment.enrich_file(
                Path(argument("--base")),
                Path(argument("--current")),
                Path(argument("--output")),
                log,
            )
        elif module_name == "normalize_extended":
            mod_frame_enrichment.enrich_file(
                argument("--base"), argument("--current"),
                Path(argument("--output-dir")) / "mods.json", log,
            )
            extended_output = Path(argument("--output-dir")).resolve()
            dead_signal_cradle_applicability.enrich_files(
                Path(argument("--base")),
                Path(argument("--current")),
                extended_output.parent.parent,
                log,
            )
        elif module_name == "publish_web_data":
            projector = importlib.import_module("project_weapon_evidence")
            published = Path(argument("--published"))
            projected = projector.project_file(
                Path(argument("--data-dir")) / "weapons.json",
                published / "web" / "weapons.json",
            )
            log(
                "Projected Weapon verification evidence: "
                + f"{projected.get('record_counts', {}).get('effect_resolution_statuses', {})}."
            )
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
    status = "complete"
    error_text = None
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
    except Exception as error:
        status = "failed"
        error_text = f"{type(error).__name__}: {error}"
        raise
    finally:
        if _active_pipeline_recorder is not None:
            _active_pipeline_recorder.record(
                "extended-publishing",
                status=status,
                duration_seconds=time.perf_counter() - started,
                details={"published": str(published)},
                error=error_text,
            )


def _run_nonfatal_intelligence_stage(recorder, log, name, operation):
    started = time.perf_counter()
    try:
        value = operation()
        recorder.record(
            f"data-intelligence:{name}",
            duration_seconds=time.perf_counter() - started,
            details=(value.get("record_counts", {}) if isinstance(value, dict) else {}),
        )
        return value
    except Exception as error:
        recorder.record(
            f"data-intelligence:{name}",
            status="failed",
            duration_seconds=time.perf_counter() - started,
            error=f"{type(error).__name__}: {error}",
        )
        log(f"Data Intelligence warning: {name} failed: {error}")
        return None


def run_pipeline_with_intelligence(config, log, progress, cancel=None):
    """Run the canonical pipeline, then finish non-publishing intelligence products."""
    global _active_pipeline_recorder
    recorder = PipelineRecorder()
    _active_pipeline_recorder = recorder
    result = None
    phase = {"label": None, "started": time.perf_counter(), "percent": 0}

    def inspected_progress(value, label):
        now = time.perf_counter()
        if phase["label"] is not None:
            recorder.record(
                f"phase:{phase['label']}",
                duration_seconds=now - phase["started"],
                details={"start_percent": phase["percent"], "end_percent": value},
            )
        phase["label"] = str(label)
        phase["started"] = now
        phase["percent"] = int(value)
        progress(value, label)

    try:
        result = _original_run_pipeline(config, log, inspected_progress, cancel)
        if phase["label"] is not None:
            recorder.record(
                f"phase:{phase['label']}",
                duration_seconds=time.perf_counter() - phase["started"],
                details={"start_percent": phase["percent"], "end_percent": 100},
            )
            phase["label"] = None

        output = Path(result.get("config", {}).get("output") or config.output).expanduser().resolve()
        published = output / "published"
        reports = published / "reports"
        active = result.get("active_snapshots") or {}
        base = Path(active.get("base") or "")
        current = Path(active.get("current") or "")
        weapons = published / "data" / "weapons.json"

        research = _run_nonfatal_intelligence_stage(
            recorder,
            log,
            "research-suite",
            lambda: run_research_suite(base, current, weapons, reports),
        )
        if research is not None:
            log(
                "Dead Signal research suite ready: "
                + f"{research.get('record_counts', {}).get('profiled_tables', 0)} profiled tables; "
                + f"Source Finder states {research.get('record_counts', {}).get('source_finder_states', {})}."
            )

        gate = _run_nonfatal_intelligence_stage(
            recorder, log, "publication-gate", lambda: build_gate_report(reports)
        )
        if gate is not None:
            log("Dead Signal Publication Gate review generated (advisory; public data unchanged).")

        discovery = _run_nonfatal_intelligence_stage(
            recorder, log, "discovery", lambda: DeadSignalDiscovery(output).run_all()
        )
        if discovery is not None:
            log("Dead Signal Discovery report generated (research leads only).")

        analytics = _run_nonfatal_intelligence_stage(
            recorder, log, "analytics-warehouse", lambda: DeadSignalAnalytics(output).build()
        )
        if analytics is not None:
            log("Dead Signal Analytics warehouse refreshed.")

        recorder.report(output, result=result)
        return result
    except Exception:
        if phase["label"] is not None:
            recorder.record(
                f"phase:{phase['label']}",
                status="failed",
                duration_seconds=time.perf_counter() - phase["started"],
                details={"start_percent": phase["percent"]},
            )
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
    # Physical resource checks are reserved for extractor modules that are
    # intentionally copied into the packaged app as data. Ordinary Python
    # modules (including Data Intelligence) are frozen into PyInstaller's module
    # archive and are validated by the import checks below instead of by a
    # neighboring .py file existing on disk.
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
        miner_core.EXTRACTOR_ROOT / "weapon_build_compatibility.py",
        miner_core.EXTRACTOR_ROOT / "project_weapon_evidence.py",
        miner_core.EXTRACTOR_ROOT / "investigate_weapon_descriptions.py",
        miner_core.EXTRACTOR_ROOT / "investigate_weapon_description_sources.py",
    )
    for resource in resources:
        checks.setdefault("resources", {})[str(resource)] = resource.is_file()
    for module_name in (
        "publish_extended_web_data", "publish_current_calibrations", "armor_tier_normalization",
        "armor_tier_completion", "mod_frame_enrichment", "project_mod_frame_evidence",
        "weapon_evidence_enrichment", "weapon_reference_filter", "weapon_typed_seed_trace", "weapon_build_compatibility",
        "project_weapon_evidence", "research_console", "research_window",
        "dead_signal_research_suite", "dead_signal_source_finder", "dead_signal_table_profiler",
        "dead_signal_intelligence_window", "dead_signal_intelligence_advanced", "dead_signal_intelligence_hub",
        "dead_signal_discovery", "dead_signal_discovery_tab", "dead_signal_verification",
        "dead_signal_verification_tab", "dead_signal_analytics", "dead_signal_evidence_graph",
        "dead_signal_workflow_lab", "dead_signal_pipeline_inspector", "dead_signal_publication_gate",
        "dead_signal_generalized_workspace", "dead_signal_phase13_shell",
        "neox_data_explorer", "investigate_weapon_descriptions", "investigate_weapon_description_sources",
        "duckdb", "polars", "pyarrow",
    ):
        try:
            module = importlib.import_module(module_name)
            checks.setdefault("imports", {})[module_name] = getattr(module, "__version__", "ok")
        except Exception as error:
            checks.setdefault("imports", {})[module_name] = f"ERROR: {type(error).__name__}: {error}"
    checks["ok"] = bool(
        all(checks.get("resources", {}).values())
        and all(not str(value).startswith("ERROR") for value in checks.get("imports", {}).values())
        and checks.get("installations")
    )
    return checks


miner_core.run_module_main = run_module_main_with_completion
miner_core.link_published_images = link_images_and_publish_extended
miner_core.run_pipeline = run_pipeline_with_intelligence
miner_core.self_test = self_test_with_extended_publisher
research_window.open_research_console = open_dead_signal_data_intelligence

# Import the desktop UI only after the canonical pipeline hooks above are installed.
# A completed/cancelled/failed run is terminal as soon as the UI returns to its idle
# controls. Clear the worker handle at that same transition so window-close and
# update checks cannot mistake a finished daemon thread's final unwind for active
# mining.
import dead_signal_miner as _miner_ui  # noqa: E402
from dead_signal_phase13_shell import install_phase13_shell  # noqa: E402

_original_set_idle_buttons = _miner_ui.DeadSignalMinerApp._set_idle_buttons
_original_build_ui = _miner_ui.DeadSignalMinerApp._build_ui


def _set_idle_buttons_and_clear_worker(self):
    self.worker = None
    return _original_set_idle_buttons(self)


def _build_ui_with_phase13_shell(self):
    _original_build_ui(self)
    install_phase13_shell(self)


_miner_ui.DeadSignalMinerApp._set_idle_buttons = _set_idle_buttons_and_clear_worker
_miner_ui.DeadSignalMinerApp._build_ui = _build_ui_with_phase13_shell
main = _miner_ui.main


if __name__ == "__main__":
    raise SystemExit(main())
