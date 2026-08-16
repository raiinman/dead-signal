"""Batch guided schema tracing for the Dead Signal weapon database.

Runs the bounded single-item schema tracer across every published weapon and
writes a compact research-only report beneath ``output/research``. The batch
report intentionally omits full flattened NeoX fields; those remain available in
the one-item raw trace view. This keeps the export useful and reasonably small.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dead_signal_weapon_schema_trace import DeadSignalWeaponSchemaTrace
from research_console import ResearchConsole


SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def summarize_trace(result: dict[str, Any]) -> dict[str, Any]:
    subject = result.get("subject") or {}
    identities = result.get("identities") or []
    records = result.get("records") or []
    stops = [
        {
            "kind": row.get("kind"),
            "value": row.get("value"),
            "depth": row.get("depth"),
            "state": row.get("state"),
            "exact_reference_count": row.get("exact_reference_count"),
            "owner_tables": row.get("owner_tables") or [],
            "discovered_from": row.get("discovered_from"),
        }
        for row in identities
        if row.get("state") != "VERIFIED"
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
        "unresolved_stop_count": len(stops),
        "skipped_broad_exact_references": int(counts.get("skipped_broad_exact_references") or 0),
        "typed_branches": branches,
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
                "owner_records": sum(int(row.get("record_count") or 0) for row in rows),
                "skipped_broad_exact_references": sum(int(row.get("skipped_broad_exact_references") or 0) for row in rows),
            },
            "weapons": rows,
            "failures": failures,
            "policy": {
                "source": "published weapon identities plus installed-game exact reference tracer and NeoX tables",
                "matching": "Same typed-owner rules as the guided one-item trace; no fuzzy, substring, similar-ID, or bare-number traversal.",
                "output": "Compact research-only summary. Full NeoX fields remain in the one-item Schema Trace view.",
                "publication": "No automatic promotion or player-facing publication.",
            },
        }
        destination = self.output / "research" / "schema-trace-all-weapons.json"
        _atomic_json(destination, payload)
        payload["report_path"] = str(destination)
        if activity:
            activity(f"Complete: {len(rows)}/{total} traced; {len(failures)} failures")
        return payload
