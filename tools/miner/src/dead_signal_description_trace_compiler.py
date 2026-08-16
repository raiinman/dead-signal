"""Compact compiler for the offline Weapon Description static data-flow trace."""
from __future__ import annotations

import json
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dead_signal_bindict_schema_audit import run_weapon_prototype_bindict_audit
from dead_signal_blueprint_module_audit import run_blueprint_module_audit
from dead_signal_common_data_registry_audit import run_common_data_registry_audit
from dead_signal_data_proxy_architecture import run_data_proxy_architecture_audit
from dead_signal_datamgr_map_audit import run_datamgr_map_audit
from dead_signal_fixed_skill_text_audit import run_fixed_skill_text_audit
from dead_signal_description_dataflow import run_description_dataflow_trace
from dead_signal_description_dataflow_fallback import recover_persisted_description_capsules
from dead_signal_intelligence_compiler import resolve_snapshot
from dead_signal_weapon_prototype_projection import run_weapon_prototype_projection

LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, str], None]
ActivityCallback = Callable[[str], None]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _merge_persisted_fallback(report: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    report["persisted_fallback"] = fallback
    recovered = [row for row in fallback.get("functions") or [] if isinstance(row, dict)]
    existing = {
        (str(row.get("function") or ""), str((row.get("code_capsule") or {}).get("co_filename") or ""))
        for row in report.get("code_objects") or []
        if isinstance(row, dict)
    }
    for row in recovered:
        key = (str(row.get("function") or ""), str((row.get("code_capsule") or {}).get("co_filename") or ""))
        if key in existing:
            continue
        report.setdefault("code_objects", []).append(row)
        existing.add(key)

    code_objects = [row for row in report.get("code_objects") or [] if isinstance(row, dict)]
    counts = report.setdefault("record_counts", {})
    counts["selected_code_objects"] = len(code_objects)
    counts["persisted_code_capsules_recovered"] = len(recovered)
    counts["functions"] = dict(sorted(Counter(str(row.get("function") or "") for row in code_objects).items()))

    cooccurrence = []
    for row in code_objects:
        signals = row.get("relationship_signals") or {}
        if signals.get("prototype_desc_and_desc_helper_cooccur") or (
            signals.get("contains_prototype_desc") and signals.get("calls_get_item_desc_text")
        ):
            cooccurrence.append({
                "pyc": row.get("pyc") or (row.get("code_capsule") or {}).get("co_filename"),
                "qualname": row.get("qualname"),
                "function": row.get("function"),
                "signals": signals,
                "source_mode": row.get("source_mode") or "snapshot-pyc",
            })
    report["cooccurrence_signals"] = cooccurrence
    counts["prototype_desc_get_item_desc_text_cooccurrences"] = len(cooccurrence)

    target_presence = report.setdefault("target_presence", {})
    for row in recovered:
        function = str(row.get("function") or "")
        if function:
            target_presence[function] = int(target_presence.get(function) or 0) + 1
        names = set(map(str, row.get("co_names") or []))
        consts = set(map(str, row.get("string_constants") or []))
        for target in ("prototype_desc", "get_item_desc_text", "get_weapon_prototype_data", "get_weapon_prototype_data_val_by_key", "weapon_prototype_data"):
            if target in names or target in consts:
                target_presence[target] = int(target_presence.get(target) or 0) + 1
    return report


def _build_bundle(
    paths: dict[str, Path],
    report: dict[str, Any],
    bindict_audit: dict[str, Any],
    prototype_projection: dict[str, Any],
    blueprint_audit: dict[str, Any],
    common_data_audit: dict[str, Any],
    data_proxy_audit: dict[str, Any],
    datamgr_map_audit: dict[str, Any],
    fixed_skill_audit: dict[str, Any],
    duration: float,
) -> Path:
    intelligence = paths["output"] / "intelligence"
    intelligence.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    archive = intelligence / f"Dead-Signal-Description-DataFlow-{stamp}.zip"
    report_path = paths["reports"] / "weapon-description-static-dataflow.json"
    bindict_path = paths["reports"] / "weapon-prototype-bindict-schema-audit.json"
    projection_path = paths["reports"] / "weapon-description-prototype-projection.json"
    blueprint_path = paths["reports"] / "blueprint-scroll-view-full-static-audit.json"
    common_data_path = paths["reports"] / "common-data-registry-static-audit.json"
    data_proxy_path = paths["reports"] / "data-proxy-architecture-static-audit.json"
    datamgr_map_path = paths["reports"] / "datamgr-map-static-audit.json"
    fixed_skill_path = paths["reports"] / "fixed-skill-text-static-audit.json"
    summary = {
        "schema": "dead-signal-description-dataflow-bundle",
        "schema_version": 8,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": duration,
        "record_counts": report.get("record_counts") or {},
        "target_presence": report.get("target_presence") or {},
        "bindict_schema_audit": {
            "status": (bindict_audit.get("interpretation") or {}).get("status"),
            "record_counts": bindict_audit.get("record_counts") or {},
            "field_presence": bindict_audit.get("field_presence") or {},
        },
        "prototype_projection": {
            "record_counts": prototype_projection.get("record_counts") or {},
            "source_layers": prototype_projection.get("source_layers") or [],
        },
        "blueprint_scroll_view_full_audit": {
            "record_counts": blueprint_audit.get("record_counts") or {},
            "target_basename": blueprint_audit.get("target_basename"),
            "mode": blueprint_audit.get("mode"),
        },
        "common_data_registry_audit": {
            "record_counts": common_data_audit.get("record_counts") or {},
            "mode": common_data_audit.get("mode"),
        },
        "data_proxy_architecture_audit": {
            "record_counts": data_proxy_audit.get("record_counts") or {},
            "mode": data_proxy_audit.get("mode"),
        },
        "datamgr_map_audit": {
            "record_counts": datamgr_map_audit.get("record_counts") or {},
            "mode": datamgr_map_audit.get("mode"),
        },
        "fixed_skill_text_audit": {
            "record_counts": fixed_skill_audit.get("record_counts") or {},
            "mode": fixed_skill_audit.get("mode"),
        },
        "mode": "offline-static-pyc-only",
        "safety": report.get("safety") or {},
    }
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as destination:
        destination.writestr(
            "dead-signal-description-dataflow-summary.json",
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        )
        destination.write(report_path, "published/reports/weapon-description-static-dataflow.json")
        for path, arcname in (
            (bindict_path, "published/reports/weapon-prototype-bindict-schema-audit.json"),
            (projection_path, "published/reports/weapon-description-prototype-projection.json"),
            (blueprint_path, "published/reports/blueprint-scroll-view-full-static-audit.json"),
            (common_data_path, "published/reports/common-data-registry-static-audit.json"),
            (data_proxy_path, "published/reports/data-proxy-architecture-static-audit.json"),
            (datamgr_map_path, "published/reports/datamgr-map-static-audit.json"),
            (fixed_skill_path, "published/reports/fixed-skill-text-static-audit.json"),
        ):
            if path.is_file():
                destination.write(path, arcname)
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
    """Run the offline static description, Blueprint, registry, proxy, DataMgr, and fixed-skill audits."""
    log = log or (lambda _value: None)
    progress = progress or (lambda _value, _label: None)
    activity = activity or log

    progress(5, "Resolve Snapshot")
    activity("Resolving completed Dead Signal Miner snapshot")
    paths = resolve_snapshot(output)
    paths["reports"].mkdir(parents=True, exist_ok=True)

    progress(14, "Static Description Data Flow")
    started = time.perf_counter()
    report = run_description_dataflow_trace(paths["base"], paths["current"], paths["reports"], activity=activity)

    target_functions = {
        str(row.get("function") or "")
        for row in report.get("code_objects") or []
        if isinstance(row, dict)
    }
    needed = {"get_weapon_item_data", "get_item_desc_text", "get_weapon_prototype_data", "get_weapon_prototype_data_val_by_key"}
    if not needed.issubset(target_functions):
        progress(30, "Persisted PYC Capsule Fallback")
        fallback = recover_persisted_description_capsules(paths["reports"], activity=activity)
        report = _merge_persisted_fallback(report, fallback)
        _write_json(paths["reports"] / "weapon-description-static-dataflow.json", report)

    progress(40, "Weapon Prototype Bindict Schema Audit")
    bindict_audit = run_weapon_prototype_bindict_audit(paths["base"], paths["current"], paths["reports"], activity=activity)

    progress(50, "Exact Prototype Description Projection")
    prototype_projection = run_weapon_prototype_projection(paths["base"], paths["current"], paths["weapons"], paths["reports"], activity=activity)

    progress(60, "Full BlueprintScrollViewPart Audit")
    blueprint_audit = run_blueprint_module_audit(paths["base"], paths["current"], paths["reports"], activity=activity)

    progress(70, "Common Data Registry Audit")
    common_data_audit = run_common_data_registry_audit(paths["base"], paths["current"], paths["reports"], activity=activity)

    progress(82, "Common / Client / Server Data Proxy Architecture")
    data_proxy_audit = run_data_proxy_architecture_audit(paths["base"], paths["current"], paths["reports"], activity=activity)

    progress(90, "DataMgr Type / Package / Proxy Map Audit")
    datamgr_map_audit = run_datamgr_map_audit(paths["base"], paths["current"], paths["reports"], activity=activity)

    progress(94, "Fixed Skill Player-Facing Text Audit")
    fixed_skill_audit = run_fixed_skill_text_audit(paths["base"], paths["current"], paths["reports"], activity=activity)

    duration = round(time.perf_counter() - started, 6)
    progress(97, "Package Data Flow Trace")
    activity(f"Static Description Data Flow finished in {duration:.1f}s")
    archive = _build_bundle(
        paths, report, bindict_audit, prototype_projection, blueprint_audit,
        common_data_audit, data_proxy_audit, datamgr_map_audit, fixed_skill_audit, duration
    )
    activity(f"Description data-flow bundle ready: {archive.name}")
    progress(100, "Description Data Flow ready")
    log(f"Dead Signal Description Data Flow bundle ready: {archive}")
    return {
        "schema": "dead-signal-description-dataflow-compiled",
        "schema_version": 8,
        "duration_seconds": duration,
        "record_counts": report.get("record_counts") or {},
        "target_presence": report.get("target_presence") or {},
        "bindict_schema_audit": {"status": (bindict_audit.get("interpretation") or {}).get("status"), "field_presence": bindict_audit.get("field_presence") or {}},
        "prototype_projection": prototype_projection.get("record_counts") or {},
        "blueprint_scroll_view_full_audit": blueprint_audit.get("record_counts") or {},
        "common_data_registry_audit": common_data_audit.get("record_counts") or {},
        "data_proxy_architecture_audit": data_proxy_audit.get("record_counts") or {},
        "datamgr_map_audit": datamgr_map_audit.get("record_counts") or {},
        "fixed_skill_text_audit": fixed_skill_audit.get("record_counts") or {},
        "report": str(paths["reports"] / "weapon-description-static-dataflow.json"),
        "bindict_report": str(paths["reports"] / "weapon-prototype-bindict-schema-audit.json"),
        "projection_report": str(paths["reports"] / "weapon-description-prototype-projection.json"),
        "blueprint_audit_report": str(paths["reports"] / "blueprint-scroll-view-full-static-audit.json"),
        "common_data_registry_report": str(paths["reports"] / "common-data-registry-static-audit.json"),
        "data_proxy_architecture_report": str(paths["reports"] / "data-proxy-architecture-static-audit.json"),
        "datamgr_map_report": str(paths["reports"] / "datamgr-map-static-audit.json"),
        "fixed_skill_text_report": str(paths["reports"] / "fixed-skill-text-static-audit.json"),
        "bundle": str(archive),
    }
