"""Dead Signal research-suite orchestration.

This module is the single research entry point shared by the Miner pipeline and
Research Console. It runs only read-only analyzers against an already extracted
snapshot and writes research reports beneath ``published/reports``. None of the
outputs are allowed to mutate normalized or web-facing data.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Callable

from dead_signal_multihop_resolver import MultiHopResolver
from dead_signal_research_cache import dependency_paths, fingerprint, load_cached_report, stamp_report
from dead_signal_source_finder import build_source_finder_report
from dead_signal_table_profiler import compare_profiles, profile_table
from investigate_weapon_description_sources import investigate as investigate_description_sources
from investigate_weapon_descriptions import investigate as investigate_description_identity

SCHEMA_VERSION = 2
PROFILE_TABLE_HINTS = (
    "weapon", "gun", "item", "equip", "blueprint", "prototype", "skill",
    "display", "ui", "tooltip", "desc", "copy",
)
PROFILE_PRIORITY_HINTS = (
    ("tooltip", 90), ("description", 90), ("desc", 80), ("copy", 80),
    ("display", 70), ("ui", 60), ("weapon", 55), ("gun", 55),
    ("blueprint", 45), ("item", 40), ("equip", 35), ("prototype", 35),
    ("skill", 25), ("preview", 20),
)
MAX_PROFILE_TABLES = 500
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


def _profile_path_score(relative: str) -> int:
    lowered = relative.casefold()
    score = sum(weight for token, weight in PROFILE_PRIORITY_HINTS if token in lowered)
    if lowered.startswith("game_common/data/"):
        score += 20
    if "/logic_tree/" in lowered:
        score -= 40
    return score


def _candidate_profile_paths(base: Path, current: Path) -> list[str]:
    paths: set[str] = set()
    for root in (base, current):
        for path in root.rglob("*.json"):
            relative = path.relative_to(root).as_posix()
            lowered = relative.casefold()
            if lowered.startswith("translate/") or lowered.endswith("snapshot.json"):
                continue
            if any(token in lowered for token in PROFILE_TABLE_HINTS):
                paths.add(relative)
    return sorted(paths, key=lambda relative: (-_profile_path_score(relative), relative))[:MAX_PROFILE_TABLES]


def build_table_profile_report(base: Path, current: Path, *, activity: ActivityCallback | None = None) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    candidates = _candidate_profile_paths(base, current)
    total = len(candidates)
    activity(f"Table Profiler found {total} candidate NeoX tables (ranked by Weapon/description relevance)")
    tables = []
    for index, relative in enumerate(candidates, start=1):
        activity(f"Table Profiler {index}/{total}: {relative}")
        base_path = base / relative
        current_path = current / relative
        base_profile = profile_table(base_path, layer="base", table=relative) if base_path.is_file() else None
        current_profile = profile_table(current_path, layer="current", table=relative) if current_path.is_file() else None
        active = current_profile or base_profile or {}
        row: dict[str, Any] = {
            "table": relative,
            "base_present": base_profile is not None,
            "current_present": current_profile is not None,
            "profile_priority_score": _profile_path_score(relative),
            "active_profile": active,
        }
        if base_profile and current_profile:
            row["base_current_diff"] = compare_profiles(base_profile, current_profile)
        tables.append(row)
    interesting = sorted(
        tables,
        key=lambda row: (
            -len((row.get("active_profile") or {}).get("description_like_fields") or []),
            -len((row.get("active_profile") or {}).get("identity_like_fields") or []),
            -int(row.get("profile_priority_score") or 0),
            row["table"],
        ),
    )
    activity(f"Table Profiler complete: {len(tables)} tables profiled")
    return {
        "schema": "dead-signal-table-profiler-catalog",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "product": "Dead Signal Table Profiler",
        "record_counts": {
            "profiled_tables": len(tables),
            "tables_with_description_like_fields": sum(bool((row.get("active_profile") or {}).get("description_like_fields")) for row in tables),
            "tables_with_identity_like_fields": sum(bool((row.get("active_profile") or {}).get("identity_like_fields")) for row in tables),
        },
        "tables": interesting,
        "policy": "Structural profiling is discovery-only and cannot establish identity or publish data.",
    }


def _merge_source_investigations(primary: dict[str, Any], multihop: dict[str, Any]) -> dict[str, Any]:
    multi_by_blueprint = {str(row.get("blueprint_id")): row for row in (multihop.get("weapons") or []) if isinstance(row, dict)}
    rows = []
    for row in primary.get("weapons") or []:
        if not isinstance(row, dict):
            continue
        merged = dict(row)
        direct = [candidate for candidate in (row.get("candidates") or []) if isinstance(candidate, dict)]
        multi_row = multi_by_blueprint.get(str(row.get("blueprint_id"))) or {}
        indirect = [candidate for candidate in (multi_row.get("candidates") or []) if isinstance(candidate, dict)]
        candidates, seen = [], set()
        for candidate in direct + indirect:
            key = (
                str(candidate.get("source") or ""), str(candidate.get("table") or ""),
                str(candidate.get("record_id") or ""), str(candidate.get("field") or ""),
                str(candidate.get("json_pointer") or ""), str(candidate.get("resolved_text") or ""),
                str(candidate.get("raw_value") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            candidates.append(candidate)
        merged["same_record_candidate_count"] = len(direct)
        merged["multihop_candidate_count"] = len(indirect)
        merged["candidate_count"] = len(candidates)
        merged["candidates"] = candidates
        rows.append(merged)
    return {
        "schema": "dead-signal-weapon-description-combined-investigation",
        "schema_version": SCHEMA_VERSION,
        "record_counts": {
            "weapons": len(rows),
            "same_record_candidates": sum(row["same_record_candidate_count"] for row in rows),
            "multihop_candidates": sum(row["multihop_candidate_count"] for row in rows),
            "candidate_rows": sum(row["candidate_count"] for row in rows),
        },
        "policy": {
            "identity": "Candidates preserve either exact same-record identity or an exact bounded reference path.",
            "verification": "Combined candidates are research-only until explicit verification.",
        },
        "weapons": rows,
    }


def _timed(label: str, operation, timings: list[dict[str, Any]], *, activity: ActivityCallback):
    started = time.perf_counter()
    value = operation()
    seconds = round(time.perf_counter() - started, 6)
    timings.append({"name": label, "duration_seconds": seconds, "cache_hit": False})
    activity(f"{label} complete in {seconds:.1f}s")
    return value


def _cached_or_run(
    *,
    label: str,
    path: Path,
    revision: str,
    dependencies: list[Path],
    builder,
    timings: list[dict[str, Any]],
    activity: ActivityCallback,
    allow_legacy_adoption: bool = True,
) -> dict[str, Any]:
    signature = fingerprint(dependencies, revision=revision)
    started = time.perf_counter()
    cached = load_cached_report(
        path,
        signature=signature,
        revision=revision,
        dependencies=dependencies,
        allow_legacy_adoption=allow_legacy_adoption,
    )
    if cached is not None:
        _write_json(path, cached)
        seconds = round(time.perf_counter() - started, 6)
        timings.append({"name": label, "duration_seconds": seconds, "cache_hit": True})
        activity(f"{label}: cache hit — reused unchanged snapshot report in {seconds:.1f}s")
        return cached
    activity(f"{label}: cache miss — running analyzer")
    payload = builder()
    stamp_report(payload, signature=signature, revision=revision)
    _write_json(path, payload)
    seconds = round(time.perf_counter() - started, 6)
    timings.append({"name": label, "duration_seconds": seconds, "cache_hit": False})
    activity(f"{label} complete in {seconds:.1f}s")
    return payload


def run_research_suite(base: Path, current: Path, weapons_path: Path, reports_dir: Path, *, activity: ActivityCallback | None = None) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    activity(f"Loading Weapon dataset: {weapons_path.name}")
    weapons = _read_json(weapons_path, {}) or {}
    if not isinstance(weapons, dict):
        raise ValueError("Weapon dataset must be a JSON object")
    weapon_count = len(weapons.get("weapons") or [])
    activity(f"Loaded {weapon_count} weapons")
    reports_dir.mkdir(parents=True, exist_ok=True)
    output = reports_dir.parent.parent
    deps = dependency_paths(output, base, current, weapons_path)
    timings: list[dict[str, Any]] = []

    identity_path = reports_dir / "weapon-description-identity-investigation.json"
    description_identity = _cached_or_run(
        label="Weapon Description Identity Investigator", path=identity_path,
        revision="weapon-description-identity-v1", dependencies=deps,
        builder=lambda: investigate_description_identity(weapons, base, current),
        timings=timings, activity=activity,
    )

    sources_path = reports_dir / "weapon-description-source-investigation.json"
    description_sources = _cached_or_run(
        label="Weapon Description Source Investigator", path=sources_path,
        revision="weapon-description-source-v1", dependencies=deps,
        builder=lambda: investigate_description_sources(weapons, base, current),
        timings=timings, activity=activity,
    )

    multihop_path = reports_dir / "weapon-description-multihop.json"
    multihop = _cached_or_run(
        label="Dead Signal Multi-hop Resolver", path=multihop_path,
        revision="weapon-description-multihop-v1", dependencies=deps,
        builder=lambda: MultiHopResolver(output).run(weapons, activity=activity),
        timings=timings, activity=activity,
    )

    combined_path = reports_dir / "weapon-description-combined-investigation.json"
    combined_sources = _timed(
        "Combine Description Investigations",
        lambda: _merge_source_investigations(description_sources, multihop),
        timings, activity=activity,
    )
    _write_json(combined_path, combined_sources)

    source_finder_path = reports_dir / "dead-signal-source-finder.json"
    source_finder = _timed(
        "Dead Signal Source Finder",
        lambda: build_source_finder_report(combined_sources),
        timings, activity=activity,
    )
    _write_json(source_finder_path, source_finder)

    table_profiles_path = reports_dir / "dead-signal-table-profiles.json"
    table_profiles = _cached_or_run(
        label="Dead Signal Table Profiler", path=table_profiles_path,
        revision="dead-signal-table-profiler-v1", dependencies=deps,
        builder=lambda: build_table_profile_report(base, current, activity=activity),
        timings=timings, activity=activity,
    )

    manifest = {
        "schema": "dead-signal-research-suite",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "record_counts": {
            "weapons": weapon_count,
            "profiled_tables": table_profiles["record_counts"]["profiled_tables"],
            "multihop_candidates": multihop["record_counts"]["candidate_rows"],
            "multihop_expanded_records": multihop["record_counts"]["expanded_records"],
            "source_finder_states": source_finder["record_counts"]["states"],
        },
        "stage_timings": timings,
        "cache": {
            "enabled": True,
            "cache_hits": sum(1 for row in timings if row.get("cache_hit")),
            "cache_misses": sum(1 for row in timings if row.get("cache_hit") is False),
            "policy": "Unchanged completed-snapshot reports are reused; changed inputs or analyzer revisions invalidate only the affected cached analyzer.",
        },
        "reports": {
            "weapon_description_identity": str(identity_path),
            "weapon_description_sources": str(sources_path),
            "weapon_description_multihop": str(multihop_path),
            "weapon_description_combined": str(combined_path),
            "source_finder": str(source_finder_path),
            "table_profiles": str(table_profiles_path),
        },
        "publication_policy": "Research-suite reports are non-publishing evidence products. No value is promoted into normalized or player-facing data by this suite.",
    }
    manifest_path = reports_dir / "dead-signal-research-suite.json"
    _write_json(manifest_path, manifest)
    activity(f"Research Suite complete: {manifest_path.name}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Dead Signal read-only research analyzers")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--weapons", type=Path, required=True)
    parser.add_argument("--reports", type=Path, required=True)
    args = parser.parse_args()
    manifest = run_research_suite(args.base, args.current, args.weapons, args.reports, activity=print)
    print(json.dumps(manifest["record_counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
