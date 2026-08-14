"""Dead Signal Miner entrypoint with compact publishing installed first."""

from __future__ import annotations

import importlib
from pathlib import Path

import miner_core
import armor_tier_completion
import mod_frame_enrichment


_original_link_published_images = miner_core.link_published_images
_original_run_module_main = miner_core.run_module_main
_original_self_test = miner_core.self_test


def run_module_main_with_completion(module_name, arguments, log):
    arguments = list(arguments)
    result = _original_run_module_main(module_name, arguments, log)

    def argument(name):
        index = arguments.index(name)
        return arguments[index + 1]

    if module_name == "normalize_armor":
        armor_tier_completion.complete_file(
            argument("--base"),
            argument("--current"),
            argument("--output"),
            log,
        )
    elif module_name == "normalize_extended":
        mod_frame_enrichment.enrich_file(
            argument("--base"),
            argument("--current"),
            Path(argument("--output-dir")) / "mods.json",
            log,
        )
    return result


def link_images_and_publish_extended(published, log):
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


def self_test_with_extended_publisher():
    checks = _original_self_test()
    resources = (
        miner_core.EXTRACTOR_ROOT / "publish_extended_web_data.py",
        miner_core.EXTRACTOR_ROOT / "publish_current_calibrations.py",
        miner_core.EXTRACTOR_ROOT / "armor_tier_normalization.py",
        miner_core.EXTRACTOR_ROOT / "armor_tier_completion.py",
        miner_core.EXTRACTOR_ROOT / "mod_frame_enrichment.py",
        miner_core.EXTRACTOR_ROOT / "project_mod_frame_evidence.py",
    )
    for resource in resources:
        checks.setdefault("resources", {})[str(resource)] = resource.is_file()
    for module_name in (
        "publish_extended_web_data",
        "publish_current_calibrations",
        "armor_tier_normalization",
        "armor_tier_completion",
        "mod_frame_enrichment",
        "project_mod_frame_evidence",
    ):
        try:
            module = importlib.import_module(module_name)
            checks.setdefault("imports", {})[module_name] = getattr(module, "__version__", "ok")
        except Exception as error:
            checks.setdefault("imports", {})[module_name] = (
                f"ERROR: {type(error).__name__}: {error}"
            )
    checks["ok"] = bool(
        all(checks.get("resources", {}).values())
        and all(
            not str(value).startswith("ERROR")
            for value in checks.get("imports", {}).values()
        )
        and checks.get("installations")
    )
    return checks


miner_core.run_module_main = run_module_main_with_completion
miner_core.link_published_images = link_images_and_publish_extended
miner_core.self_test = self_test_with_extended_publisher

from dead_signal_miner import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
