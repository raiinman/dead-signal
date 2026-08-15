"""Standalone Dead Signal Data Intelligence compiler.

Runs the research extensions against an already-completed Miner snapshot without
re-reading or modifying the installed game.  It regenerates research reports,
analytics, discovery products, the advisory publication gate, and a compact ZIP
bundle suitable for review or upload.  No public website dataset is modified.
"""

from __future__ import annotations

import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dead_signal_analytics import DeadSignalAnalytics
from dead_signal_discovery import DeadSignalDiscovery
from dead_signal_publication_gate import build_gate_report
from dead_signal_research_suite import run_research_suite


SCHEMA_VERSION = 1
LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, str], None]


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def resolve_snapshot(output: Path | str) -> dict[str, Path]:
    """Resolve one completed Miner snapshot using its canonical run metadata."""
    output = Path(output).expanduser().resolve()
    if not output.is_dir():
        raise ValueError("Select a completed Dead Signal Miner data folder")

    last_run = _read_json(output / "last-run.json", {}) or {}
    active = last_run.get("active_snapshots") if isinstance(last_run, dict) else {}
    active = active if isinstance(active, dict) else {}

    base = Path(str(active.get("base") or "")).expanduser()
    current = Path(str(active.get("current") or "")).expanduser()
    if not base.is_absolute():
        base = (output / base).resolve()
    else:
        base = base.resolve()
    if not current.is_absolute():
        current = (output / current).resolve()
    else:
        current = current.resolve()

    published = output / "published"
    weapons = published / "data" / "weapons.json"
    reports = published / "reports"

    missing = []
    if not base.is_dir():
        missing.append(f"base snapshot: {base}")
    if not current.is_dir():
        missing.append(f"current snapshot: {current}")
    if not weapons.is_file():
        missing.append(f"weapon dataset: {weapons}")
    if missing:
        raise ValueError(
            "The selected folder does not contain a complete reusable Miner snapshot. Missing: "
            + "; ".join(missing)
        )

    return {
        "output": output,
        "base": base,
        "current": current,
        "published": published,
        "weapons": weapons,
        "reports": reports,
    }


def _stage(
    stages: list[dict[str, Any]],
    name: str,
    operation,
    *,
    log: LogCallback,
    progress: ProgressCallback,
    percent: int,
):
    progress(percent, name)
    log(f"Data Intelligence: {name}...")
    started = time.perf_counter()
    try:
        value = operation()
    except Exception as error:
        stages.append({
            "name": name,
            "status": "failed",
            "duration_seconds": round(time.perf_counter() - started, 6),
            "error": f"{type(error).__name__}: {error}",
        })
        raise
    stages.append({
        "name": name,
        "status": "complete",
        "duration_seconds": round(time.perf_counter() - started, 6),
    })
    return value


def _bundle_members(paths: dict[str, Path]) -> list[Path]:
    output = paths["output"]
    reports = paths["reports"]
    candidates = [
        output / "last-run.json",
        output / "catalogs" / "structured-tables.sqlite",
        output / "catalogs" / "dead-signal-analytics.duckdb",
        paths["published"] / "indexes" / "reference-tracer.sqlite",
        paths["weapons"],
    ]
    candidates.extend(sorted(reports.glob("*.json")))
    return [path for path in candidates if path.is_file()]


def build_bundle(paths: dict[str, Path], compiled: dict[str, Any]) -> Path:
    """Create a compact research bundle without raw game-table exports."""
    output = paths["output"]
    intelligence_dir = output / "intelligence"
    intelligence_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    archive = intelligence_dir / f"Dead-Signal-Intelligence-{stamp}.zip"

    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as destination:
        destination.writestr(
            "dead-signal-intelligence-compiled.json",
            json.dumps(compiled, ensure_ascii=False, indent=2) + "\n",
        )
        for path in _bundle_members(paths):
            try:
                relative = path.relative_to(output)
            except ValueError:
                continue
            destination.write(path, relative.as_posix())
    return archive


def compile_intelligence(
    output: Path | str,
    *,
    log: LogCallback | None = None,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Regenerate all standalone Data Intelligence products for one snapshot."""
    log = log or (lambda _value: None)
    progress = progress or (lambda _value, _label: None)
    paths = resolve_snapshot(output)
    paths["reports"].mkdir(parents=True, exist_ok=True)
    stages: list[dict[str, Any]] = []

    research = _stage(
        stages,
        "Research Suite",
        lambda: run_research_suite(paths["base"], paths["current"], paths["weapons"], paths["reports"]),
        log=log,
        progress=progress,
        percent=10,
    )
    discovery = _stage(
        stages,
        "Discovery Engine",
        lambda: DeadSignalDiscovery(paths["output"]).run_all(),
        log=log,
        progress=progress,
        percent=45,
    )
    analytics_engine = DeadSignalAnalytics(paths["output"])
    analytics = _stage(
        stages,
        "Analytics Warehouse",
        analytics_engine.build,
        log=log,
        progress=progress,
        percent=65,
    )
    description_leads = _stage(
        stages,
        "Description Leads",
        lambda: analytics_engine.description_leads(limit=1000),
        log=log,
        progress=progress,
        percent=76,
    )
    suspicious_fields = _stage(
        stages,
        "Description Field Audit",
        lambda: analytics_engine.suspicious_description_fields(limit=1000),
        log=log,
        progress=progress,
        percent=82,
    )
    _write_json(paths["reports"] / "dead-signal-description-leads.json", description_leads)
    _write_json(paths["reports"] / "dead-signal-description-field-audit.json", suspicious_fields)

    gate = _stage(
        stages,
        "Publication Gate",
        lambda: build_gate_report(paths["reports"]),
        log=log,
        progress=progress,
        percent=90,
    )

    compiled = {
        "schema": "dead-signal-intelligence-compiled",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "product": "Dead Signal Data Intelligence Compiler",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot": {
            "output": str(paths["output"]),
            "base": str(paths["base"]),
            "current": str(paths["current"]),
            "weapons": str(paths["weapons"]),
        },
        "stages": stages,
        "record_counts": {
            "weapons": (research.get("record_counts") or {}).get("weapons", 0),
            "profiled_tables": (research.get("record_counts") or {}).get("profiled_tables", 0),
            "source_finder_states": (research.get("record_counts") or {}).get("source_finder_states", {}),
            "discovery_tables": ((discovery.get("schema_clusters") or {}).get("record_counts") or {}).get("tables", 0),
            "description_hotspots": ((discovery.get("description_hotspots") or {}).get("record_counts") or {}).get("hotspots", 0),
            "analytics_rows": analytics.get("rows", {}),
            "description_leads": description_leads.get("row_count", 0),
            "description_field_rows": suspicious_fields.get("row_count", 0),
            "publishable_candidates": (gate.get("record_counts") or {}).get("publishable_candidates", 0),
        },
        "reports": {
            "research_suite": str(paths["reports"] / "dead-signal-research-suite.json"),
            "table_profiles": str(paths["reports"] / "dead-signal-table-profiles.json"),
            "source_finder": str(paths["reports"] / "dead-signal-source-finder.json"),
            "discovery": str(paths["reports"] / "dead-signal-discovery.json"),
            "description_leads": str(paths["reports"] / "dead-signal-description-leads.json"),
            "description_field_audit": str(paths["reports"] / "dead-signal-description-field-audit.json"),
            "publication_gate": str(paths["reports"] / "dead-signal-publication-gate.json"),
            "analytics_database": str(paths["output"] / "catalogs" / "dead-signal-analytics.duckdb"),
        },
        "policy": {
            "input": "Runs only against an already-completed local Miner snapshot.",
            "game_files": "Does not read from or write to the installed Once Human folder.",
            "publication": "Compiled intelligence is research-only and does not rewrite player-facing datasets.",
            "authority": "Discovery and analytics create leads only; exact evidence and explicit verification remain authoritative.",
        },
    }
    compiled_path = paths["reports"] / "dead-signal-intelligence-compiled.json"
    _write_json(compiled_path, compiled)

    progress(96, "Compile Intelligence Bundle")
    archive = build_bundle(paths, compiled)
    compiled["bundle"] = str(archive)
    _write_json(compiled_path, compiled)
    progress(100, "Data Intelligence ready")
    log(f"Dead Signal Intelligence bundle ready: {archive}")
    return compiled
