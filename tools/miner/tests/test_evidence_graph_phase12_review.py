from pathlib import Path
import tempfile
import unittest

from dead_signal_evidence_review import (
    ManualReviewStore,
    assess_claim,
    build_review_queue,
    export_evidence_bundle,
)


def graph(entity_type="attachment", canonical_id="att-1", claims=None):
    return {
        "entity": {
            "entity_type": entity_type,
            "canonical_id": canonical_id,
            "source_records": [
                {"table": "game_common/data/item_data.json", "record_id": "101", "layer": "base-current-merged"}
            ],
        },
        "claims": claims or [],
    }


def claim(claim_type, result, requirements=None, missing=None, conflicts=None, evidence=None, dependencies=None):
    return {
        "claim_type": claim_type,
        "result": result,
        "requirements": requirements or [],
        "missing": missing or [],
        "conflicts": conflicts or [],
        "evidence": evidence or [],
        "dependencies": dependencies or [],
    }


class Phase12EvidenceReviewTests(unittest.TestCase):
    def test_partial_claim_exposes_each_requirement_and_actionable_reason(self):
        c = claim(
            "attachment.weapon_compatibility",
            "PARTIAL",
            requirements=["attachment identity", "accessory owner", "typed weapon model selector"],
            missing=["typed weapon model selector"],
            evidence=[{"identity": "att-1"}],
            dependencies=["game_common/data/gun_accessory_base_params_data.json"],
        )
        assessment = assess_claim(graph(claims=[c]), c)
        self.assertEqual(3, len(assessment["requirements"]))
        by_req = {row["requirement"]: row for row in assessment["requirements"]}
        self.assertEqual("MISSING", by_req["typed weapon model selector"]["state"])
        self.assertIn("typed weapon model selector", assessment["actionable_reasons"])
        self.assertFalse(assessment["publication_authority"])

    def test_unresolved_without_missing_still_has_actionable_reason(self):
        c = claim("deviation.scenario_availability", "UNRESOLVED", requirements=["exact scenario owner"])
        assessment = assess_claim(graph("deviation", "ds-dev-7", [c]), c)
        self.assertTrue(assessment["actionable_reasons"])
        self.assertIn("trace the exact owner", assessment["actionable_reasons"][0])

    def test_conflict_orders_before_partial_and_invalidated_gets_priority(self):
        conflict = claim("armor.set_membership", "CONFLICT", conflicts=[{"a": 1, "b": 2}], requirements=["one exact suit owner"])
        partial = claim("attachment.acquisition", "PARTIAL", missing=["typed acquisition owner"], requirements=["typed acquisition owner"])
        g1 = graph("armor", "a-1", [conflict])
        g2 = graph("attachment", "att-1", [partial])
        report = {"review_queue": ["attachment:att-1:attachment.acquisition"]}
        queue = build_review_queue([g2, g1], invalidation_report=report)
        self.assertEqual("CONFLICT", queue["items"][0]["result"])
        att = next(row for row in queue["items"] if row["entity_type"] == "attachment")
        self.assertTrue(att["invalidated"])

    def test_queue_filters_domain_and_groups_shared_missing_owner(self):
        a = claim("attachment.acquisition", "UNRESOLVED", missing=["typed acquisition owner"], requirements=["typed acquisition owner"])
        b = claim("attachment.artwork", "UNRESOLVED", missing=["typed acquisition owner"], requirements=["artwork owner"])
        d = claim("deviation.acquisition", "UNRESOLVED", missing=["typed acquisition owner"])
        queue = build_review_queue([
            graph("attachment", "att-1", [a]),
            graph("attachment", "att-2", [b]),
            graph("deviation", "dev-1", [d]),
        ], domain="attachment")
        self.assertTrue(all(row["entity_type"] == "attachment" for row in queue["items"]))
        group = next(row for row in queue["shared_missing_groups"] if row["missing_owner_or_reason"] == "typed acquisition owner")
        self.assertEqual(2, group["count"])

    def test_navigation_contains_exact_record_and_consumer_lead(self):
        c = claim("attachment.slot_type", "UNRESOLVED", dependencies=["game_common/data/item_data.json"])
        queue = build_review_queue([graph(claims=[c])])
        nav = queue["items"][0]["navigation"]
        self.assertEqual("101", nav["exact_records"][0]["record_id"])
        self.assertEqual("game_common/data/item_data.json", nav["consumer_leads"][0]["dependency"])

    def test_manual_review_is_attributable_removable_and_cannot_assign_proven(self):
        with tempfile.TemporaryDirectory() as td:
            store = ManualReviewStore(Path(td))
            row = store.record(
                "attachment:att-1:attachment.acquisition",
                state="VERIFIED",
                reviewer="researcher@example",
                note="Exact owner inspected manually.",
                source_ref="capture-17",
            )
            self.assertEqual("researcher@example", row["reviewer"])
            self.assertFalse(row["deterministic_proof_override"])
            self.assertFalse(row["publication_authority"])
            with self.assertRaises(ValueError):
                store.record("x", state="PROVEN", reviewer="reviewer", note="This must never be allowed")
            self.assertTrue(store.remove("attachment:att-1:attachment.acquisition"))
            self.assertNotIn("attachment:att-1:attachment.acquisition", store.load()["reviews"])

    def test_manual_review_requires_reviewer(self):
        with tempfile.TemporaryDirectory() as td:
            store = ManualReviewStore(Path(td))
            with self.assertRaises(ValueError):
                store.record("x:y:z", state="CONFLICT", reviewer="", note="Conflicting exact owners found")

    def test_bounded_bundle_is_research_only(self):
        c = claim("attachment.acquisition", "UNRESOLVED", missing=["typed acquisition owner"], evidence=list(range(150)))
        g = graph(claims=[c])
        with tempfile.TemporaryDirectory() as td:
            destination = Path(td) / "bundle.json"
            bundle = export_evidence_bundle([g], ["attachment:att-1:attachment.acquisition"], destination)
            self.assertTrue(destination.is_file())
            self.assertEqual(100, len(bundle["claims"][0]["claim"]["evidence"]))
            self.assertIn("no publication authority", bundle["policy"])


if __name__ == "__main__":
    unittest.main()
