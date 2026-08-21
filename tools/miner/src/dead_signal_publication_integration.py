"""Snapshot-level Phase 14 publication integration.

Builds a lean, claim-backed publication audit.  The audit is deliberately separate
from normalized research graphs and does not mutate existing public datasets.
Future/public website projectors must consume these field decisions rather than
research graphs directly.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dead_signal_generalized_graph import DeadSignalGeneralizedGraph
from dead_signal_publication_contracts import FIELD_CONTRACTS, contract_manifest, project_field


def _claim_value(claim: dict[str, Any]) -> Any:
    """Return the compact value lane explicitly carried by a claim, if present."""
    for key in ("value", "values", "relationship", "output", "result_value", "presentation"):
        if key in claim:
            return claim.get(key)
    evidence = claim.get("evidence") or []
    return evidence[0] if len(evidence) == 1 else evidence


def _contracts_for_entity(entity_type: str):
    prefix = f"{entity_type}."
    return [contract for contract in FIELD_CONTRACTS if contract.field.startswith(prefix)]


def audit_graph(graph: dict[str, Any]) -> dict[str, Any]:
    entity = graph.get("entity") or {}
    entity_type = str(entity.get("entity_type") or "")
    canonical_id = str(entity.get("canonical_id") or "")
    claims = [row for row in graph.get("claims", []) or [] if isinstance(row, dict)]
    by_type: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        by_type.setdefault(str(claim.get("claim_type") or ""), []).append(claim)
    rows = []
    for contract in _contracts_for_entity(entity_type):
        matches = by_type.get(contract.claim_type, [])
        if not matches:
            rows.append(project_field(contract.field, None, None))
            continue
        for index, claim in enumerate(matches):
            projected = project_field(contract.field, claim, _claim_value(claim))
            projected["claim_index"] = index
            rows.append(projected)
    return {
        "entity_type": entity_type,
        "canonical_id": canonical_id,
        "identity_state": entity.get("identity_state"),
        "fields": rows,
    }


class PublicationIntegration:
    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        self.engine = DeadSignalGeneralizedGraph(self.output)

    def build(self, *, limit_per_domain: int = 1000, persist: bool = True) -> dict[str, Any]:
        registry = self.engine.rebuild_entity_registry()
        entities = []
        counts = {"fields": 0, "publishable": 0, "blocked": 0, "omitted": 0, "not_applicable": 0}
        for entity_type in registry.get("adapter_types") or []:
            for row in self.engine.search_entities("", entity_type=entity_type, limit=limit_per_domain):
                graph = self.engine.entity_graph(entity_type, row["canonical_id"])
                audited = audit_graph(graph)
                entities.append(audited)
                for field in audited["fields"]:
                    decision = field.get("publication") or {}
                    counts["fields"] += 1
                    counts["publishable"] += int(bool(decision.get("publishable")))
                    counts["blocked"] += int(decision.get("decision") == "BLOCKED")
                    counts["omitted"] += int(decision.get("decision") == "OMIT")
                    counts["not_applicable"] += int(decision.get("decision") == "NOT APPLICABLE")
        entities.sort(key=lambda row: (row["entity_type"], row["canonical_id"]))
        report = {
            "schema": "dead-signal-claim-backed-publication-audit",
            "schema_version": 1,
            "record_counts": {**counts, "entities": len(entities), "contracts": len(FIELD_CONTRACTS)},
            "contract_manifest": contract_manifest(),
            "entities": entities,
            "policy": {
                "research_graphs_are_projector_input": False,
                "lean_claim_results_only": True,
                "proven_is_automatic_publication": False,
                "partial_unresolved_conflict_silent_publication": False,
                "not_applicable_is_missing": False,
                "existing_publisher_mutated": False,
            },
        }
        if persist:
            target = self.output / "published" / "reports" / "evidence-publication-contracts.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            tmp.replace(target)
            report["report"] = str(target)
        return report
