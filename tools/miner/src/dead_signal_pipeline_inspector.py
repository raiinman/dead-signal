"""Dead Signal Pipeline Inspector.

Collects read-only execution telemetry around the packaged Miner without changing
extraction semantics.  Reports stages, durations, statuses, and produced research
artifacts so failures can be diagnosed from one branded report.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable


SCHEMA_VERSION = 1


class PipelineRecorder:
    def __init__(self):
        self.started = time.time()
        self.events: list[dict[str, Any]] = []

    def stage(self, name: str, operation: Callable[[], Any], *, details: dict[str, Any] | None = None) -> Any:
        started = time.perf_counter()
        event = {"stage": name, "status": "running", "details": dict(details or {})}
        try:
            result = operation()
            event["status"] = "complete"
            return result
        except Exception as error:
            event["status"] = "failed"
            event["error"] = f"{type(error).__name__}: {error}"
            raise
        finally:
            event["duration_seconds"] = round(time.perf_counter() - started, 6)
            self.events.append(event)

    def record(self, name: str, *, status: str = "complete", duration_seconds: float | None = None,
               details: dict[str, Any] | None = None, error: str | None = None) -> None:
        row = {"stage": name, "status": status, "details": dict(details or {})}
        if duration_seconds is not None:
            row["duration_seconds"] = round(float(duration_seconds), 6)
        if error:
            row["error"] = error
        self.events.append(row)

    def report(self, output: Path | str, *, result: dict[str, Any] | None = None) -> dict[str, Any]:
        output = Path(output).expanduser().resolve()
        reports = output / "published" / "reports"
        artifacts = []
        if reports.is_dir():
            for path in sorted(reports.glob("*.json")):
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
                artifacts.append({"name": path.name, "bytes": size})
        statuses: dict[str, int] = {}
        for event in self.events:
            state = str(event.get("status") or "unknown")
            statuses[state] = statuses.get(state, 0) + 1
        payload = {
            "schema": "dead-signal-pipeline-inspector",
            "schema_version": SCHEMA_VERSION,
            "brand": "Dead Signal",
            "elapsed_seconds": round(time.time() - self.started, 6),
            "record_counts": {"events": len(self.events), "statuses": statuses, "report_artifacts": len(artifacts)},
            "events": self.events,
            "artifacts": artifacts,
            "snapshot": {
                "completed_utc": (result or {}).get("completed_utc"),
                "active_snapshots": (result or {}).get("active_snapshots"),
                "published": (result or {}).get("published"),
            },
            "policy": "Pipeline Inspector records execution metadata only; it never changes game extraction or publication semantics.",
        }
        reports.mkdir(parents=True, exist_ok=True)
        path = reports / "dead-signal-pipeline-inspector.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return payload


def inspect_existing_run(output: Path | str) -> dict[str, Any]:
    output = Path(output).expanduser().resolve()
    path = output / "published" / "reports" / "dead-signal-pipeline-inspector.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        last = output / "last-run.json"
        try:
            run = json.loads(last.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            run = {}
        return {
            "schema": "dead-signal-pipeline-inspector",
            "schema_version": SCHEMA_VERSION,
            "brand": "Dead Signal",
            "record_counts": {"events": 0},
            "events": [],
            "snapshot": {
                "completed_utc": run.get("completed_utc"),
                "active_snapshots": run.get("active_snapshots"),
                "published": run.get("published"),
            },
            "status": "legacy-run-no-stage-telemetry",
        }
