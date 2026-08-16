"""Compact compiler for the offline Weapon Description static data-flow trace."""
from __future__ import annotations

import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dead_signal_description_dataflow import run_description_dataflow_trace
from dead_signal_intelligence_compiler import resolve_snapshot

LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, str], None]
ActivityCallback = Callable[[str], None]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _build_bundle(paths: dict[str, Path], report: dict[str, Any], duration: float) -> Path:
    intelligence = paths["output"] / "intelligence"
    intelligence.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    archive = intelligence / f"Dead-Signal-Description-DataFlow-{stamp}.zip"
    report_path = paths["reports"] / "weapon-description-static-dataflow.json"
    summary = {
        "schema": "dead-signal-description-dataflow-bundle",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": duration,
        "record_counts": report.get("record_counts") or {},
        "target_presence": report.get("target_presence") or {},
        "mode": "offline-static-pyc-only",
        "safety": report.get("safety") or {},
    }
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as destination:
        destination.writestr(
            "dead-signal-description-dataflow-summary.json",
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        )
        destination.write(report_path, "published/reports/weapon-description-static-dataflow.json")
        last_run = paths["output"] / "last-run.json"
        if last_run.is_file():
            destination.write(last_run, "last-run.json")
        for layer in ("base", "current"):
            snapshot = paths[layer] / "snapshot.json"
            if snapshot.is_file():
                destination.write(snapshot, f"snapshots/{layer}-snapshot.json")
    return archive


def compile_description_dataflow_trace(
    output: Path | str,
    *,
    log: LogCallback | None = None,
    progress: ProgressCallback | None = None,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    """Run only the offline static PYC description data-flow trace."""
    log = log or (lambda _value: None)
    progress = progress or (lambda _value, _label: None)
    activity = activity or log

    progress(5, "Resolve Snapshot")
    activity("Resolving completed Dead Signal Miner snapshot")
    paths = resolve_snapshot(output)
    paths["reports"].mkdir(parents=True, exist_ok=True)

    progress(20, "Static Description Data Flow")
    started = time.perf_counter()
    report = run_description_dataflow_trace(
        paths["base"], paths["current"], paths["reports"], activity=activity
    )
    duration = round(time.perf_counter() - started, 6)

    progress(90, "Package Data Flow Trace")
    activity(f"Static Description Data Flow finished in {duration:.1f}s")
    archive = _build_bundle(paths, report, duration)
    activity(f"Description data-flow bundle ready: {archive.name}")
    progress(100, "Description Data Flow ready")
    log(f"Dead Signal Description Data Flow bundle ready: {archive}")
    return {
        "schema": "dead-signal-description-dataflow-compiled",
        "schema_version": 1,
        "duration_seconds": duration,
        "record_counts": report.get("record_counts") or {},
        "target_presence": report.get("target_presence") or {},
        "report": str(paths["reports"] / "weapon-description-static-dataflow.json"),
        "bundle": str(archive),
    }
