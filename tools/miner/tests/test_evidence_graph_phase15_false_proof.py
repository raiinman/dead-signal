from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

MINER = Path(__file__).resolve().parents[1]
SRC = MINER / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_false_proof_benchmark import (  # noqa: E402
    BenchmarkObservation,
    DOMAIN_REGRESSION_SOURCES,
    SCENARIOS,
    audit_adapter_contracts,
    evaluate_observations,
)
from dead_signal_generalized_graph import DeadSignalGeneralizedGraph  # noqa: E402


SAFE_STATE = {
    "conflicting-current-records": "CONFLICT",
    "valid-not-applicable-relationship": "NOT APPLICABLE",
    "partial-chain-missing-consumer": "PARTIAL",
}


def observations(domains):
    rows = []
    for domain in domains:
        for scenario in SCENARIOS:
            state = SAFE_STATE.get(scenario, "UNRESOLVED")
            rows.append(BenchmarkObservation(
                domain=domain,
                scenario=scenario,
                case_id=f"{domain}-{scenario}",
                state=state,
                missing_requirement="" if state == "NOT APPLICABLE" else f"resolve exact owner for {scenario}",
                provenance=(f"regression:{domain}", f"scenario:{scenario}"),
                duration_seconds=0.001,
            ))
    return rows


class EvidenceGraphPhaseFifteenFalseProofTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        engine = DeadSignalGeneralizedGraph(Path(self.temp.name))
        self.domains = engine.registry.entity_types()
        self.adapters = [engine.registry.get(domain) for domain in self.domains]

    def test_all_registered_adapters_pass_static_false_proof_contract_audit(self):
        report = audit_adapter_contracts(self.adapters)
        self.assertTrue(report["ok"], report)
        self.assertEqual(set(self.domains), {row["domain"] for row in report["domains"]})
        for row in report["domains"]:
            self.assertTrue(row["regression_sources"], row)

    def test_every_domain_has_existing_behavioral_regression_sources(self):
        tests = Path(__file__).resolve().parent
        self.assertEqual(set(self.domains), set(DOMAIN_REGRESSION_SOURCES))
        for domain, names in DOMAIN_REGRESSION_SOURCES.items():
            self.assertTrue(names, domain)
            for name in names:
                self.assertTrue((tests / name).is_file(), f"{domain} missing regression source {name}")

    def test_complete_matrix_passes_with_zero_false_proven(self):
        report = evaluate_observations(observations(self.domains), self.domains)
        self.assertTrue(report["ok"], report)
        self.assertEqual(0, report["primary_metric"]["false_proven_results"])
        self.assertEqual(len(self.domains) * len(SCENARIOS), report["record_counts"]["required_cases"])
        self.assertEqual(report["record_counts"]["required_cases"], report["record_counts"]["observed_cases"])

    def test_deliberate_false_proven_fails_benchmark(self):
        rows = observations(self.domains)
        original = rows[0]
        rows[0] = BenchmarkObservation(
            domain=original.domain,
            scenario=original.scenario,
            case_id=original.case_id,
            state="PROVEN",
            missing_requirement="",
            provenance=original.provenance,
            duration_seconds=original.duration_seconds,
        )
        report = evaluate_observations(rows, self.domains)
        self.assertFalse(report["ok"])
        self.assertEqual(1, report["primary_metric"]["false_proven_results"])
        self.assertTrue(report["failures"]["false_proven"])

    def test_missing_case_fails_closed(self):
        rows = observations(self.domains)[:-1]
        report = evaluate_observations(rows, self.domains)
        self.assertFalse(report["ok"])
        self.assertEqual(1, len(report["failures"]["missing_cases"]))

    def test_missing_provenance_and_requirement_fail_closed(self):
        rows = observations(self.domains)
        original = rows[0]
        rows[0] = BenchmarkObservation(
            domain=original.domain,
            scenario=original.scenario,
            case_id=original.case_id,
            state="UNRESOLVED",
            missing_requirement="",
            provenance=(),
            duration_seconds=0.001,
        )
        report = evaluate_observations(rows, self.domains)
        self.assertFalse(report["ok"])
        self.assertTrue(report["failures"]["missing_requirement"])
        self.assertTrue(report["failures"]["missing_provenance"])

    def test_wrong_state_for_conflict_fails(self):
        rows = observations(self.domains)
        index = next(i for i, row in enumerate(rows) if row.scenario == "conflicting-current-records")
        original = rows[index]
        rows[index] = BenchmarkObservation(
            domain=original.domain,
            scenario=original.scenario,
            case_id=original.case_id,
            state="UNRESOLVED",
            missing_requirement="resolve current conflict",
            provenance=original.provenance,
            duration_seconds=0.001,
        )
        report = evaluate_observations(rows, self.domains)
        self.assertFalse(report["ok"])
        self.assertTrue(report["failures"]["wrong_state"])

    def test_runtime_bound_is_enforced(self):
        rows = observations(self.domains)
        original = rows[0]
        rows[0] = BenchmarkObservation(
            domain=original.domain,
            scenario=original.scenario,
            case_id=original.case_id,
            state=original.state,
            missing_requirement=original.missing_requirement,
            provenance=original.provenance,
            duration_seconds=2.5,
        )
        report = evaluate_observations(rows, self.domains)
        self.assertFalse(report["ok"])
        self.assertTrue(report["failures"]["runtime_violations"])

    def test_ordering_is_stable(self):
        rows = observations(self.domains)
        forward = evaluate_observations(rows, self.domains)
        reverse = evaluate_observations(list(reversed(rows)), self.domains)
        self.assertEqual(forward["stable_order"], reverse["stable_order"])


if __name__ == "__main__":
    unittest.main()
