"""Batch guided schema tracing for the Dead Signal weapon database.

Runs the bounded single-item schema tracer across every published weapon and
writes a compact research-only report beneath ``output/research``. The batch
report intentionally omits full flattened NeoX fields; those remain available in
the one-item raw trace view. This keeps the export useful and reasonably small.

Any exact unresolved fixed-skill codes left by the fleet trace are handed to the
targeted raw-PYC forensic stage automatically. That second stage is read-only and
research-only; it never changes published weapon data.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dead_signal_missing_skill_forensics import run_missing_skill_forensics
from dead_signal_weapon_schema_trace import DeadSignalWeaponSchemaTrace
from research_console import ResearchConsole


SCHEMA_VERSION = 4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _identity_summary(row: dict[str, Any]) -> dict[str, Any]:
    result = {
        "kind": row.get("kind"),
        "value": row.get("value"),
        "depth": row.get("depth"),
        "state": row.get("state"),
        "exact_reference_count": row.get("exact_reference_count"),
        "owner_tables": row.get("owner_tables") or [],
        "reference_candidates": row.get("reference_candidates") or [],
        "discovered_from": row.get("discovered_from"),
    }
    if row.get("terminal_note"):
        result["terminal_note"] = row.get("terminal_note")
    return result


def summarize_trace(result: dict[str, Any]) -> dict[str, Any]:
    subject = result.get("subject") or {}
    identities = result.get("identities") or []
    records = result.get("records") or []
    terminals = [
        _identity_summary(row)
        for row in identities
        if row.get("state") == "TERMINAL-EXACT-REFERENCE"
    ]
    stops = [
        _identity_summary(row)
        for row in identities
        if row.get("state") not in {"VERIFIED", "TERMINAL-EXACT-REFERENCE"}
    ]
    branches = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        for outbound in record.get("outbound_typed_identities") or []:
            key = (str(outbound.get("kind") or ""), str(outbound.get("value") or ""))
            if key in seen:
                continue
            seen.add(key)
            branches.append({
                "kind": key[0],
                "value": key[1],
                "field": outbound.get("field"),
                "source_table": record.get("table"),
                "source_record_id": record.get("record_id"),
            })
    counts = result.get("record_counts") or {}
    status = "clean" if not stops else "stopped-with-unresolved-identities"
    return {
        "canonical_id": subject.get("canonical_id"),
        "name": subject.get("name"),
        "category": subject.get("category"),
        "blueprint_id": subject.get("blueprint_id"),
        "item_id": subject.get("item_id"),
        "prototype_id": subject.get("prototype_id"),
        "status": status,
        "identity_count": len(identities),
        "record_count": len(records),
        "typed_branch_count": len(branches),
        "terminal_reference_count": len(terminals),
        "unresolved_stop_count": len(stops),
        "skipped_broad_exact_references": int(counts.get("skipped_broad_exact_references") or 0),
        "typed_branches": branches,
        "terminal_references": terminals,
        "unresolved_stops": stops,
        "owner_records": [
            {
                "layer": row.get("layer"),
                "table": row.get("table"),
                "record_id": row.get("record_id"),
                "matched_identity": row.get("matched_identity"),
            }
            for row in records
        ],
    }


def _unresolved_skill_codes(rows: list[dict[str, Any]]) -> list[str]:
    values = {
        str(stop.get("value") or "").strip()
        for row in rows
        for stop in (row.get("unresolved_stops") or [])
        if stop.get("kind") == "skill_id" and str(stop.get("value") or "").strip()
    }
    return sorted(values)


class DeadSignalSchemaTraceBatch:
    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        self.console = ResearchConsole(self.output)
        self.tracer = DeadSignalWeaponSchemaTrace(self.output)

    def run(self, *, activity: Callable[[str], None] | None = None) -> dict[str, Any]:
        weapons = self.console.weapons()
        rows = []
        failures = []
        total = len(weapons)
        for index, weapon in enumerate(weapons, 1):
            identity = weapon.get("canonical_id") or weapon.get("blueprint_id") or weapon.get("item_id") or weapon.get("name")
            name = str(weapon.get("name") or identity or "unknown")
            if activity:
                activity(f"Tracing {index}/{total}: {name}")
            try:
                rows.append(summarize_trace(self.tracer.trace(identity)))
            except Exception as error:
                failures.append({
                    "canonical_id": weapon.get("canonical_id"),
                    "name": name,
                    "identity": identity,
                    "error": str(error),
                })

        clean = sum(1 for row in rows if row.get("status") == "clean")
        unresolved = sum(1 for row in rows if row.get("unresolved_stop_count"))
        unresolved_skills = _unresolved_skill_codes(rows)
        research_dir = self.output / "research"
        forensic_summary: dict[str, Any] = {
            "requested_skill_codes": unresolved_skills,
            "report_path": str(research_dir / "missing-fixed-skill-forensics.json"),
            "status": "not-needed" if not unresolved_skills else "pending",
        }
        if unresolved_skills:
            try:
                if activity:
                    activity(f"Fleet trace isolated {len(unresolved_skills)} unresolved fixed-skill codes; starting targeted raw forensics")
                forensic = run_missing_skill_forensics(
                    self.console.base,
                    self.console.current,
                    unresolved_skills,
                    research_dir,
                    activity=activity,
                )
                forensic_summary.update({
                    "status": forensic.get("status"),
                    "record_counts": forensic.get("record_counts") or {},
                })
            except Exception as error:
                forensic_summary.update({
                    "status": "forensic-stage-error",
                    "error": f"{type(error).__name__}: {error}",
                })

        payload = {
            "schema": "dead-signal-guided-schema-trace-batch",
            "schema_version": SCHEMA_VERSION,
            "generated_at": _utc_now(),
            "record_counts": {
                "weapons_requested": total,
                "weapons_traced": len(rows),
                "clean": clean,
                "with_unresolved_stops": unresolved,
                "failures": len(failures),
                "typed_branches": sum(int(row.get("typed_branch_count") or 0) for row in rows),
                "terminal_references": sum(int(row.get("terminal_reference_count") or 0) for row in rows),
                "owner_records": sum(int(row.get("record_count") or 0) for row in rows),
                "skipped_broad_exact_references": sum(int(row.get("skipped_broad_exact_references") or 0) for row in rows),
                "unique_unresolved_skill_codes": len(unresolved_skills),
            },
            "missing_skill_forensics": forensic_summary,
            "weapons": rows,
            "failures": failures,
            "policy": {
                "source": "published weapon identities plus installed-game exact reference tracer and NeoX tables",
                "matching": "Typed owner table + owner-field rules; no fuzzy, substring, similar-ID, bare-number, or table-only traversal.",
                "terminal_references": "Exact configuration handles that legitimately terminate at their source field are reported separately and do not make a weapon unresolved.",
                "unresolved": "Unresolved exact identities include compact table/field candidate counts so the next owner rule can be learned from evidence instead of guessed.",
                "forensics": "Remaining unresolved skill codes are automatically passed to a bounded exact raw-PYC audit; forensic hits remain research evidence only.",
                "output": "Compact research-only summary. Full NeoX fields remain in the one-item Schema Trace view.",
                "publication": "No automatic promotion or player-facing publication.",
            },
        }
        destination = research_dir / "schema-trace-all-weapons.json"
        _atomic_json(destination, payload)
        payload["report_path"] = str(destination)
        if activity:
            activity(f"Complete: {len(rows)}/{total} traced; {len(failures)} failures; {len(unresolved_skills)} unresolved skill codes")
        return payload
