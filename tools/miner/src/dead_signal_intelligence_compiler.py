"""Standalone Dead Signal Data Intelligence compiler.

Runs research extensions against an already-completed Miner snapshot without
modifying the installed game. The full compiler includes canonical all-weapons
Schema Trace, ownerless fixed-skill forensics, a hardened full-corpus Weapons
audit, an authoritative website-readiness ledger, and a sanitized website-ready
Weapons projection, then packages every report into one Intelligence ZIP.
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
from dead_signal_consumer_index import run_consumer_index
from dead_signal_publication_gate import build_gate_report
from dead_signal_research_suite import run_research_suite
from dead_signal_schema_trace_batch import DeadSignalSchemaTraceBatch
from dead_signal_table_registry import run_table_registry
from dead_signal_weapon_corpus_audit import run_weapon_corpus_audit
from dead_signal_weapon_description_consumer import run_weapon_description_consumer_trace
from dead_signal_weapon_site_projection import build_weapon_site_projection
from dead_signal_weapon_site_readiness import run_weapon_site_readiness

SCHEMA_VERSION = 7
LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, str], None]
ActivityCallback = Callable[[str], None]


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
    output = Path(output).expanduser().resolve()
    if not output.is_dir():
        raise ValueError("Select a completed Dead Signal Miner data folder")
    last_run = _read_json(output / "last-run.json", {}) or {}
    active = last_run.get("active_snapshots") if isinstance(last_run, dict) else {}
    active = active if isinstance(active, dict) else {}
    base_text = str(active.get("base") or "").strip()
    current_text = str(active.get("current") or "").strip()
    if not base_text or not current_text:
        raise ValueError(
            "The completed snapshot metadata does not identify both base and current NeoX layers. "
            "Run a Complete Database harvest once with the current Miner, then Data Intelligence can be recompiled independently."
        )
    base = Path(base_text).expanduser()
    current = Path(current_text).expanduser()
    base = (output / base).resolve() if not base.is_absolute() else base.resolve()
    current = (output / current).resolve() if not current.is_absolute() else current.resolve()
    published = output / "published"
    weapons = published / "data" / "weapons.json"
    reports = published / "reports"
    research = output / "research"
    missing = []
    if not base.is_dir():
        missing.append(f"base snapshot: {base}")
    if not current.is_dir():
        missing.append(f"current snapshot: {current}")
    if not weapons.is_file():
        missing.append(f"weapon dataset: {weapons}")
    if missing:
        raise ValueError("The selected folder does not contain a complete reusable Miner snapshot. Missing: " + "; ".join(missing))
    return {
        "output": output,
        "base": base,
        "current": current,
        "published": published,
        "weapons": weapons,
        "reports": reports,
        "research": research,
    }


def _stage(stages, name, operation, *, log, progress, activity, percent):
    progress(percent, name)
    activity(f"Starting {name}")
    log(f"Data Intelligence: {name}...")
    started = time.perf_counter()
    try:
        value = operation()
    except Exception as error:
        duration = round(time.perf_counter() - started, 6)
        stages.append({"name": name, "status": "failed", "duration_seconds": duration, "error": f"{type(error).__name__}: {error}"})
        activity(f"{name} failed after {duration:.1f}s: {type(error).__name__}: {error}")
        raise
    duration = round(time.perf_counter() - started, 6)
    stages.append({"name": name, "status": "complete", "duration_seconds": duration})
    activity(f"Completed {name} in {duration:.1f}s")
    return value


def _bundle_members(paths: dict[str, Path]) -> list[Path]:
    output = paths["output"]
    candidates = [
        output / "last-run.json",
        output / "catalogs" / "structured-tables.sqlite",
        output / "catalogs" / "dead-signal-table-registry.sqlite",
        output / "catalogs" / "dead-signal-consumer-index.sqlite",
        output / "catalogs" / "dead-signal-analytics.duckdb",
        paths["published"] / "indexes" / "reference-tracer.sqlite",
        paths["weapons"],
    ]
    candidates.extend(sorted(paths["reports"].glob("*.json")))
    candidates.extend(sorted(paths["research"].glob("*.json")))
    candidates.extend(sorted((paths["published"] / "site").glob("*.json")))
    seen: set[str] = set()
    result = []
    for path in candidates:
        if not path.is_file():
            continue
        key = str(path.resolve()).casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def build_bundle(paths: dict[str, Path], compiled: dict[str, Any], *, activity: ActivityCallback | None = None) -> Path:
    activity = activity or (lambda _message: None)
    output = paths["output"]
    intelligence_dir = output / "intelligence"
    intelligence_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    archive = intelligence_dir / f"Dead-Signal-Intelligence-{stamp}.zip"
    members = _bundle_members(paths)
    activity(f"Bundling {len(members)} intelligence files")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as destination:
        destination.writestr("dead-signal-intelligence-compiled.json", json.dumps(compiled, ensure_ascii=False, indent=2) + "\n")
        for index, path in enumerate(members, start=1):
            try:
                relative = path.relative_to(output)
            except ValueError:
                continue
            activity(f"Bundle {index}/{len(members)}: {relative.as_posix()}")
            destination.write(path, relative.as_posix())
    return archive


def build_ui_consumer_bundle(paths: dict[str, Path], report: dict[str, Any]) -> Path:
    intelligence_dir = paths["output"] / "intelligence"
    intelligence_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    archive = intelligence_dir / f"Dead-Signal-Weapon-UI-Trace-{stamp}.zip"
    report_path = paths["reports"] / "weapon-description-ui-consumer-trace.json"
    summary = {
        "schema": "dead-signal-weapon-ui-trace-bundle",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_counts": report.get("record_counts") or {},
        "policy": "Targeted read-only UI-consumer research; no player-facing data was modified.",
    }
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as destination:
        destination.writestr("dead-signal-weapon-ui-trace-summary.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        destination.write(report_path, "published/reports/weapon-description-ui-consumer-trace.json")
        destination.write(paths["weapons"], "published/data/weapons.json")
        last_run = paths["output"] / "last-run.json"
        if last_run.is_file():
            destination.write(last_run, "last-run.json")
    return archive


def compile_weapon_description_ui_trace(output: Path | str, *, log=None, progress=None, activity=None) -> dict[str, Any]:
    log = log or (lambda _value: None)
    progress = progress or (lambda _value, _label: None)
    activity = activity or log
    progress(5, "Resolve Snapshot")
    activity("Resolving completed Dead Signal Miner snapshot")
    paths = resolve_snapshot(output)
    paths["reports"].mkdir(parents=True, exist_ok=True)
    progress(20, "Weapon UI Consumer Trace")
    started = time.perf_counter()
    report = run_weapon_description_consumer_trace(paths["base"], paths["current"], paths["weapons"], paths["reports"], activity=activity)
    duration = round(time.perf_counter() - started, 6)
    progress(90, "Package UI Trace")
    activity(f"Targeted UI Consumer Trace finished in {duration:.1f}s")
    archive = build_ui_consumer_bundle(paths, report)
    activity(f"Weapon UI trace bundle ready: {archive.name}")
    progress(100, "Weapon UI Trace ready")
    log(f"Dead Signal Weapon UI trace bundle ready: {archive}")
    return {
        "schema": "dead-signal-weapon-ui-trace-compiled",
        "schema_version": 1,
        "duration_seconds": duration,
        "record_counts": report.get("record_counts") or {},
        "report": str(paths["reports"] / "weapon-description-ui-consumer-trace.json"),
        "bundle": str(archive),
    }


def compile_intelligence(output: Path | str, *, log=None, progress=None, activity=None) -> dict[str, Any]:
    log = log or (lambda _value: None)
    progress = progress or (lambda _value, _label: None)
    activity = activity or log
    activity("Resolving completed Dead Signal Miner snapshot")
    paths = resolve_snapshot(output)
    activity(f"Base layer: {paths['base'].name}")
    activity(f"Current layer: {paths['current'].name}")
    paths["reports"].mkdir(parents=True, exist_ok=True)
    paths["research"].mkdir(parents=True, exist_ok=True)
    stages: list[dict[str, Any]] = []

    table_registry = _stage(
        stages, "Table Registry + Client Data Census",
        lambda: run_table_registry(paths["base"], paths["current"], paths["output"], paths["reports"], activity=activity),
        log=log, progress=progress, activity=activity, percent=2,
    )
    consumer_index = _stage(
        stages, "Static PYC Consumer Index",
        lambda: run_consumer_index(paths["base"], paths["current"], paths["output"], paths["reports"], activity=activity),
        log=log, progress=progress, activity=activity, percent=4,
    )

    ui_consumer = _stage(
        stages, "Weapon UI Consumer Trace",
        lambda: run_weapon_description_consumer_trace(paths["base"], paths["current"], paths["weapons"], paths["reports"], activity=activity),
        log=log, progress=progress, activity=activity, percent=5,
    )
    research = _stage(
        stages, "Research Suite",
        lambda: run_research_suite(paths["base"], paths["current"], paths["weapons"], paths["reports"], activity=activity),
        log=log, progress=progress, activity=activity, percent=12,
    )
    schema_trace = _stage(
        stages, "Weapon Schema + Ownerless Skill Forensics",
        lambda: DeadSignalSchemaTraceBatch(paths["output"]).run(activity=activity),
        log=log, progress=progress, activity=activity, percent=38,
    )
    corpus_audit = _stage(
        stages, "Hardened Weapons Corpus Audit",
        lambda: run_weapon_corpus_audit(paths["base"], paths["current"], paths["weapons"], paths["reports"], activity=activity),
        log=log, progress=progress, activity=activity, percent=50,
    )
    site_readiness = _stage(
        stages, "Authoritative Weapon Site Readiness",
        lambda: run_weapon_site_readiness(paths["base"], paths["current"], paths["weapons"], paths["reports"], corpus_audit, activity=activity),
        log=log, progress=progress, activity=activity, percent=60,
    )
    site_projection = _stage(
        stages, "Website Weapons V2 Projection",
        lambda: build_weapon_site_projection(paths["weapons"], paths["published"], corpus_audit, site_readiness, activity=activity),
        log=log, progress=progress, activity=activity, percent=65,
    )
    discovery = _stage(
        stages, "Discovery Engine", lambda: DeadSignalDiscovery(paths["output"]).run_all(),
        log=log, progress=progress, activity=activity, percent=71,
    )
    analytics_engine = DeadSignalAnalytics(paths["output"])
    analytics = _stage(stages, "Analytics Warehouse", analytics_engine.build, log=log, progress=progress, activity=activity, percent=80)
    description_leads = _stage(stages, "Description Leads", lambda: analytics_engine.description_leads(limit=1000), log=log, progress=progress, activity=activity, percent=86)
    suspicious_fields = _stage(stages, "Description Field Audit", lambda: analytics_engine.suspicious_description_fields(limit=1000), log=log, progress=progress, activity=activity, percent=91)
    _write_json(paths["reports"] / "dead-signal-description-leads.json", description_leads)
    activity("Wrote dead-signal-description-leads.json")
    _write_json(paths["reports"] / "dead-signal-description-field-audit.json", suspicious_fields)
    activity("Wrote dead-signal-description-field-audit.json")
    gate = _stage(stages, "Publication Gate", lambda: build_gate_report(paths["reports"]), log=log, progress=progress, activity=activity, percent=95)

    research_counts = research.get("record_counts") or {}
    ui_counts = ui_consumer.get("record_counts") or {}
    schema_counts = schema_trace.get("record_counts") or {}
    corpus_counts = corpus_audit.get("record_counts") or {}
    readiness_counts = site_readiness.get("record_counts") or {}
    readiness_score = site_readiness.get("scoreboard") or {}
    projection_counts = site_projection.get("record_counts") or {}
    forensic = schema_trace.get("missing_skill_forensics") or {}
    forensic_counts = forensic.get("record_counts") or {}
    registry_counts = (table_registry.get("summary") or {}).get("record_counts") or {}
    census_counts = (table_registry.get("client_data_census") or {}).get("record_counts") or {}
    cache_stats = table_registry.get("cache_statistics") or {}
    consumer_counts = (consumer_index.get("summary") or {}).get("record_counts") or {}
    compiled = {
        "schema": "dead-signal-intelligence-compiled",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "product": "Dead Signal Data Intelligence Compiler",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot": {"output": str(paths["output"]), "base": str(paths["base"]), "current": str(paths["current"]), "weapons": str(paths["weapons"])},
        "stages": stages,
        "record_counts": {
            "registry_tables": registry_counts.get("tables", 0),
            "consumer_index_files": consumer_counts.get("files", 0),
            "consumer_index_scopes": consumer_counts.get("scopes", 0),
            "client_data_tables": census_counts.get("tables", 0),
            "client_data_distinct_paths": census_counts.get("distinct_paths", 0),
            "weapons": research_counts.get("weapons", 0),
            "ui_consumer_candidates": ui_counts.get("consumer_backed_candidates", 0),
            "prototype_desc_fields_found": ui_counts.get("prototype_desc_fields_found", 0),
            "prototype_desc_resolved": ui_counts.get("consistent_resolutions", 0),
            "profiled_tables": research_counts.get("profiled_tables", 0),
            "source_finder_states": research_counts.get("source_finder_states", {}),
            "multihop_candidates": research_counts.get("multihop_candidates", 0),
            "multihop_expanded_records": research_counts.get("multihop_expanded_records", 0),
            "schema_trace_weapons": schema_counts.get("weapons_traced", 0),
            "unresolved_skill_codes": schema_counts.get("unique_unresolved_skill_codes", 0),
            "missing_skill_forensics_status": forensic.get("status"),
            "missing_skill_architecture_branches": forensic_counts.get("architecture_branches", 0),
            "missing_skill_architecture_functions": forensic_counts.get("architecture_functions_found", 0),
            "corpus_audit_weapons": corpus_counts.get("weapons", 0),
            "corpus_json_files_scanned": corpus_counts.get("json_files_scanned", 0),
            "corpus_json_records_scanned": corpus_counts.get("json_records_scanned", 0),
            "corpus_exact_identity_records": corpus_counts.get("exact_identity_records_with_target_fields", 0),
            "corpus_pyc_files_scanned": corpus_counts.get("pyc_files_scanned", 0),
            "corpus_ranked_gaps": corpus_counts.get("gaps", 0),
            "site_readiness_weapons": readiness_counts.get("weapons", 0),
            "site_reference_questions": readiness_counts.get("reference_questions", 0),
            "site_launch_queue": readiness_counts.get("launch_queue", 0),
            "site_reference_score": (readiness_score.get("reference_question_set") or {}).get("percent", 0),
            "site_enhancement_score": (readiness_score.get("dead_signal_enhancements") or {}).get("percent", 0),
            "site_projection_weapons": projection_counts.get("weapons", 0),
            "site_projection_gun_base_promoted": projection_counts.get("gun_base_promoted", 0),
            "site_projection_family_members": projection_counts.get("variant_family_members", 0),
            "discovery_tables": ((discovery.get("schema_clusters") or {}).get("record_counts") or {}).get("tables", 0),
            "description_hotspots": ((discovery.get("description_hotspots") or {}).get("record_counts") or {}).get("hotspots", 0),
            "analytics_rows": analytics.get("rows", {}),
            "description_leads": description_leads.get("row_count", 0),
            "description_field_rows": suspicious_fields.get("row_count", 0),
            "publishable_candidates": (gate.get("record_counts") or {}).get("publishable_candidates", 0),
        },
        "cache_statistics": cache_stats,
        "reports": {
            "table_registry_summary": str(paths["reports"] / "table-registry-summary.json"),
            "client_data_census": str(paths["reports"] / "client-data-census.json"),
            "table_registry_database": str(paths["output"] / "catalogs" / "dead-signal-table-registry.sqlite"),
            "consumer_index_summary": str(paths["reports"] / "consumer-index-summary.json"),
            "consumer_index_database": str(paths["output"] / "catalogs" / "dead-signal-consumer-index.sqlite"),
            "weapon_description_ui_consumer": str(paths["reports"] / "weapon-description-ui-consumer-trace.json"),
            "research_suite": str(paths["reports"] / "dead-signal-research-suite.json"),
            "weapon_description_multihop": str(paths["reports"] / "weapon-description-multihop.json"),
            "weapon_description_combined": str(paths["reports"] / "weapon-description-combined-investigation.json"),
            "table_profiles": str(paths["reports"] / "dead-signal-table-profiles.json"),
            "source_finder": str(paths["reports"] / "dead-signal-source-finder.json"),
            "schema_trace_all_weapons": str(paths["research"] / "schema-trace-all-weapons.json"),
            "missing_fixed_skill_forensics": str(paths["research"] / "missing-fixed-skill-forensics.json"),
            "weapon_corpus_audit": str(paths["reports"] / "weapon-corpus-audit.json"),
            "weapon_site_readiness": str(paths["reports"] / "weapon-site-readiness.json"),
            "website_weapons_v2": str(paths["published"] / "site" / "weapons-v2.json"),
            "discovery": str(paths["reports"] / "dead-signal-discovery.json"),
            "description_leads": str(paths["reports"] / "dead-signal-description-leads.json"),
            "description_field_audit": str(paths["reports"] / "dead-signal-description-field-audit.json"),
            "publication_gate": str(paths["reports"] / "dead-signal-publication-gate.json"),
            "analytics_database": str(paths["output"] / "catalogs" / "dead-signal-analytics.duckdb"),
        },
        "policy": {
            "input": "Runs only against an already-completed local Miner snapshot.",
            "game_files": "Does not write to the installed Once Human folder; forensic PYC inspection uses retained snapshot source roots read-only.",
            "publication": "Research candidates remain gated; the separate published/site/weapons-v2.json feed contains only explicit semantic promotions plus clearly labeled raw codes and unresolved states.",
            "authority": "Installed-game data mined by Dead Signal is the source of truth. External/community sites may define useful questions or UX references only; their values and semantics are never imported as evidence.",
            "forensics": "The full compiler includes canonical all-weapons Schema Trace, ownerless fixed-skill forensics, exact-identity Base/Current JSON corpus scanning, static retained-PYC consumer scanning, website-readiness scoring, and website projection generation.",
            "coverage": "The site-readiness ledger asks the full player-facing reference question set for every weapon, then separately scores Dead Signal-only progression, compatibility, recipe, identity, provenance, family inheritance, and direct website-feed coverage.",
        },
    }
    compiled_path = paths["reports"] / "dead-signal-intelligence-compiled.json"
    _write_json(compiled_path, compiled)
    activity(f"Wrote {compiled_path.name}")
    progress(97, "Compile Intelligence Bundle")
    activity("Compiling uploadable Dead Signal Intelligence ZIP")
    archive = build_bundle(paths, compiled, activity=activity)
    compiled["bundle"] = str(archive)
    _write_json(compiled_path, compiled)
    progress(100, "Data Intelligence ready")
    activity(f"Intelligence bundle ready: {archive.name}")
    log(f"Dead Signal Intelligence bundle ready: {archive}")
    return compiled
