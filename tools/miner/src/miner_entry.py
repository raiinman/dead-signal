"""Dead Signal Miner entrypoint with compact publishing installed first."""

from __future__ import annotations

import importlib

import miner_core


_original_link_published_images = miner_core.link_published_images
_original_self_test = miner_core.self_test


def link_images_and_publish_extended(published, log):
    result = _original_link_published_images(published, log)
    publisher = importlib.import_module("publish_extended_web_data")
    outputs = publisher.publish(published / "data", published)

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
    )
    for resource in resources:
        checks.setdefault("resources", {})[str(resource)] = resource.is_file()
    for module_name in ("publish_extended_web_data", "publish_current_calibrations"):
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


miner_core.link_published_images = link_images_and_publish_extended
miner_core.self_test = self_test_with_extended_publisher

from dead_signal_miner import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
