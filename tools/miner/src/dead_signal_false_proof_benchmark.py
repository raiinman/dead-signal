"""Phase 15 adversarial benchmark for the generalized Evidence Graph.

The benchmark never assigns evidence state.  It consumes explicit probe
observations from domain regressions and fails closed when an adversarial case is
missing, lacks provenance, loses its named requirement, or returns false PROVEN.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from time import perf_counter
from typing import Any, Iterable

from dead_signal_domain_adapters import EvidenceDomainAdapter, GENERIC_IDENTITY_FIELDS

SCHEMA_VERSION = 1
MAX_CASE_SECONDS = 2.0

SCENARIOS = (
    "equal-scalar-unrelated-table",
    "same-name-different-owner",
    "missing-owner",
    "stale-base-evidence",
    "conflicting-current-records",
    "shared-translation-handle",
    "inactive-legacy-record",
    "wrong-subtype",
    "unresolved-named-model-wording",
    "removed-dependency",
    "valid-not-applicable-relationship",
    "partial-chain-missing-consumer",
)

# A scenario defines acceptable evidence outcomes.  None of these adversarial
# probes are allowed to become PROVEN merely from similarity, stale data, or a
# partial owner chain.
ALLOWED_STATES = {
    "equal-scalar-unrelated-table": frozenset({"UNRESOLVED", "PARTIAL", "CONFLICT", "NOT APPLICABLE"}),
    "same-name-different-owner": frozenset({"UNRESOLVED", "PARTIAL", "CONFLICT", "NOT APPLICABLE"}),
    "missing-owner": frozenset({"UNRESOLVED", "PARTIAL"}),
    "stale-base-evidence": frozenset({"UNRESOLVED", "PARTIAL", "CONFLICT"}),
    "conflicting-current-records": frozenset({"CONFLICT"}),
    "shared-translation-handle": frozenset({"UNRESOLVED", "PARTIAL", "CONFLICT"}),
    "inactive-legacy-record": frozenset({"UNRESOLVED", "NOT APPLICABLE"}),
    "wrong-subtype": frozenset({"UNRESOLVED", "NOT APPLICABLE"}),
    "unresolved-named-model-wording": frozenset({"UNRESOLVED", "PARTIAL"}),
    "removed-dependency": frozenset({"UNRESOLVED", "PARTIAL", "CONFLICT"}),
    "valid-not-applicable-relationship": frozenset({"NOT APPLICABLE"}),
    "partial-chain-missing-consumer": frozenset({"PARTIAL", "UNRESOLVED"}),
}

DOMAIN_REGRESSION_SOURCES = {
    "weapon": ("test_weapon_schema_trace_owner_policy.py", "test_weapon_typed_seed_trace_locality.py", "test_evidence_graph_phase11_invalidation.py"),
    "attachment": ("test_evidence_graph_phase4_attachments.py", "test_attachment_relations_phase4.py"),
    "calibration": ("test_evidence_graph_phase5_calibrations.py",),
    "armor": ("test_evidence_graph_phase6_armor.py",),
    "armor_set": ("test_evidence_graph_phase6_armor.py", "test_evidence_graph_phase6_armor_set_provenance.py"),
    "mod": ("test_evidence_graph_phase7_mods.py", "test_mod_frame_enrichment.py"),
    "cradle": ("test_evidence_graph_phase8_cradles.py", "test_cradle_applicability.py"),
    "recipe": ("test_evidence_graph_phase9_crafting_materials.py", "test_evidence_graph_phase9_adapter_contract_hotfix.py"),
    "material": ("test_evidence_graph_phase9_crafting_materials.py", "test_evidence_graph_phase9_adapter_contract_hotfix.py"),
    "deviation": ("test_evidence_graph_phase10_deviations.py",),
}


@dataclass(frozen=True)
class BenchmarkObservation:
    domain: str
    scenario: str
    case_id: str
    state: str
    missing_requirement: str
    provenance: tuple[str, ...]
    duration_seconds: float = 0.0

    def normalized(self) -> "BenchmarkObservation":
        return BenchmarkObservation(
            domain=str(self.domain).strip().casefold(),
            scenario=str(self.scenario).strip(),
            case_id=str(self.case_id).strip(),
            state=str(self.state).strip().upper().replace("_", " "),
            missing_requirement=str(self.missing_requirement or "").strip(),
            provenance=tuple(sorted({str(value).strip() for value in self.provenance if str(value).strip()})),
            duration_seconds=max(0.0, float(self.duration_seconds or 0.0)),
        )


def required_case_keys(domains: Iterable[str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(domain).casefold(), scenario) for domain in domains for scenario in SCENARIOS))


def audit_adapter_contracts(adapters: Iterable[EvidenceDomainAdapter]) -> dict[str, Any]:
    """Audit static fail-closed invariants for every registered adapter."""
    rows = []
    for adapter in sorted(adapters, key=lambda value: value.entity_type):
        contract = adapter.contract
        errors = list(contract.validate())
        blocked = {str(value).casefold() for value in contract.blocked_generic_fields}
        identity = {str(value).casefold() for value in contract.identity_seeds}
        outbound = {str(value).casefold() for value in contract.allowed_outbound_fields}
        generic = set(GENERIC_IDENTITY_FIELDS)
        if identity & (generic | blocked):
            errors.append("generic-or-blocked identity seed present")
        if outbound & generic:
            errors.append("bare generic outbound field present")
        if callable(getattr(adapter, "publish", None)):
            errors.append("adapter exposes publication authority")
        destinations = contract.destinations()
        for field in contract.collision_prone_fields:
            if field not in contract.identity_seeds and not destinations.get(field):
                errors.append(f"collision-prone outbound field lacks typed destination: {field}")
        rows.append({
            "domain": adapter.entity_type,
            "ok": not errors,
            "errors": sorted(set(errors)),
            "regression_sources": list(DOMAIN_REGRESSION_SOURCES.get(adapter.entity_type, ())),
        })
    return {
        "schema": "dead-signal-adapter-false-proof-contract-audit",
        "schema_version": SCHEMA_VERSION,
        "domains": rows,
        "ok": bool(rows) and all(row["ok"] for row in rows),
    }


def evaluate_observations(observations: Iterable[BenchmarkObservation], domains: Iterable[str]) -> dict[str, Any]:
    """Evaluate a complete cross-domain adversarial result matrix."""
    started = perf_counter()
    domain_set = tuple(sorted({str(value).strip().casefold() for value in domains if str(value).strip()}))
    required = set(required_case_keys(domain_set))
    seen: dict[tuple[str, str], BenchmarkObservation] = {}
    rows = []
    false_proven = []
    wrong_state = []
    missing_reason = []
    missing_provenance = []
    runtime_violations = []
    duplicate_keys = []

    for raw in observations:
        row = raw.normalized()
        key = (row.domain, row.scenario)
        if key in seen:
            duplicate_keys.append(f"{row.domain}:{row.scenario}")
            continue
        seen[key] = row
        errors = []
        allowed = ALLOWED_STATES.get(row.scenario)
        if row.domain not in domain_set:
            errors.append("unknown-domain")
        if allowed is None:
            errors.append("unknown-scenario")
        elif row.state not in allowed:
            errors.append("wrong-state")
            wrong_state.append(f"{row.domain}:{row.scenario}:{row.state}")
        if row.state == "PROVEN":
            errors.append("false-proven")
            false_proven.append(f"{row.domain}:{row.scenario}:{row.case_id}")
        if row.state != "NOT APPLICABLE" and not row.missing_requirement:
            errors.append("missing-actionable-requirement")
            missing_reason.append(f"{row.domain}:{row.scenario}")
        if not row.provenance:
            errors.append("missing-provenance")
            missing_provenance.append(f"{row.domain}:{row.scenario}")
        if row.duration_seconds > MAX_CASE_SECONDS:
            errors.append("runtime-bound-exceeded")
            runtime_violations.append(f"{row.domain}:{row.scenario}:{row.duration_seconds:.6f}")
        rows.append({**asdict(row), "allowed_states": sorted(allowed or ()), "ok": not errors, "errors": errors})

    missing_cases = sorted(f"{domain}:{scenario}" for domain, scenario in required - set(seen))
    unexpected_cases = sorted(f"{domain}:{scenario}" for domain, scenario in set(seen) - required)
    rows.sort(key=lambda value: (value["domain"], value["scenario"], value["case_id"]))
    duration = perf_counter() - started
    ok = not any((false_proven, wrong_state, missing_reason, missing_provenance, runtime_violations, duplicate_keys, missing_cases, unexpected_cases))
    return {
        "schema": "dead-signal-false-proof-benchmark",
        "schema_version": SCHEMA_VERSION,
        "primary_metric": {"false_proven_results": len(false_proven), "target": 0},
        "record_counts": {
            "domains": len(domain_set),
            "required_cases": len(required),
            "observed_cases": len(seen),
            "passed_cases": sum(1 for row in rows if row["ok"]),
        },
        "failures": {
            "false_proven": false_proven,
            "wrong_state": wrong_state,
            "missing_requirement": missing_reason,
            "missing_provenance": missing_provenance,
            "runtime_violations": runtime_violations,
            "duplicate_cases": sorted(duplicate_keys),
            "missing_cases": missing_cases,
            "unexpected_cases": unexpected_cases,
        },
        "stable_order": [f"{row['domain']}:{row['scenario']}:{row['case_id']}" for row in rows],
        "duration_seconds": round(duration, 6),
        "cases": rows,
        "ok": ok,
        "policy": "False PROVEN results must remain zero. Similar names/scalars, stale evidence, partial chains, or missing consumers cannot promote proof.",
    }
