"""Dead Signal research-suite orchestration.

This module is the single research entry point shared by the Miner pipeline and
Research Console. It runs only read-only analyzers against an already extracted
snapshot and writes research reports beneath ``published/reports``. None of the
outputs are allowed to mutate normalized or web-facing data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from dead_signal_source_finder import build_source_finder_report
from dead_signal_table_profiler import compare_profiles, profile_table
from investigate_weapon_description_sources import investigate as investigate_description_sources
from investigate_weapon_descriptions import investigate as investigate_description_identity


SCHEMA_VERSION = 1
PROFILE_TABLE_HINTS = (
    "weapon", "gun", "item", "equip", "blueprint", "prototype", "skill",
    "display", "ui", "tooltip", "desc", "copy",
)
MAX_PROFILE_TABLES = 500


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
    return sorted(paths)[:MAX_PROFILE_TABLES]


def build_table_profile_report(base: Path, current: Path) -> dict[str, Any]:
    tables = []
    for relative in _candidate_profile_paths(base, current):
        base_path = base / relative
        current_path = current / relative
        base_profile = profile_table(base_path, layer="base", table=relative) if base_path.is_file() else None
        current_profile = profile_table(current_path, layer="current", table=relative) if current_path.is_file() else None
        active = current_profile or base_profile or {}
        row: dict[str, Any] = {
            "table": relative,
            "base_present": base_profile is not None,
            "current_present": current_profile is not None,
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
            row["table"],
        ),
    )
    return {
        "schema": "dead-signal-table-profiler-catalog",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "product": "Dead Signal Table Profiler",
        "record_counts": {
            "profiled_tables": len(tables),
            "tables_with_description_like_fields": sum(
                bool((row.get("active_profile") or {}).get("description_like_fields")) for row in tables
            ),
            "tables_with_identity_like_fields": sum(
                bool((row.get("active_profile") or {}).get("identity_like_fields")) for row in tables
            ),
        },
        "tables": interesting,
        "policy": "Structural profiling is discovery-only and cannot establish identity or publish data.",
    }


def run_research_suite(base: Path, current: Path, weapons_path: Path, reports_dir: Path) -> dict[str, Any]:
    weapons = _read_json(weapons_path, {}) or {}
    if not isinstance(weapons, dict):
        raise ValueError("Weapon dataset must be a JSON object")

    reports_dir.mkdir(parents=True, exist_ok=True)

    description_identity = investigate_description_identity(weapons, base, current)
    identity_path = reports_dir / "weapon-description-identity-investigation.json"
    _write_json(identity_path, description_identity)

    description_sources = investigate_description_sources(weapons, base, current)
    sources_path = reports_dir / "weapon-description-source-investigation.json"
    _write_json(sources_path, description_sources)

    source_finder = build_source_finder_report(description_sources)
    source_finder_path = reports_dir / "dead-signal-source-finder.json"
    _write_json(source_finder_path, source_finder)

    table_profiles = build_table_profile_report(base, current)
    table_profiles_path = reports_dir / "dead-signal-table-profiles.json"
    _write_json(table_profiles_path, table_profiles)

    manifest = {
        "schema": "dead-signal-research-suite",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "record_counts": {
            "weapons": len(weapons.get("weapons") or []),
            "profiled_tables": table_profiles["record_counts"]["profiled_tables"],
            "source_finder_states": source_finder["record_counts"]["states"],
        },
        "reports": {
            "weapon_description_identity": str(identity_path),
            "weapon_description_sources": str(sources_path),
            "source_finder": str(source_finder_path),
            "table_profiles": str(table_profiles_path),
        },
        "publication_policy": (
            "Research-suite reports are non-publishing evidence products. No value is promoted into "
            "normalized or player-facing data by this suite."
        ),
    }
    _write_json(reports_dir / "dead-signal-research-suite.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Dead Signal read-only research analyzers")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--weapons", type=Path, required=True)
    parser.add_argument("--reports", type=Path, required=True)
    args = parser.parse_args()
    manifest = run_research_suite(args.base, args.current, args.weapons, args.reports)
    print(json.dumps(manifest["record_counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
