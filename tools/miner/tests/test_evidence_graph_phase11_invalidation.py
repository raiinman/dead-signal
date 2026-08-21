from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_dependency_invalidation import DependencyInvalidationStore


def _claim(kind: str, dependency: str, *, result: str = "PROVEN", value: object = 1) -> dict:
    return {
        "claim_type": kind,
        "result": result,
        "requirements": ["exact typed owner"],
        "evidence": [{"value": value}],
        "missing": [] if result == "PROVEN" else ["recomputed owner"],
        "conflicts": ["conflict"] if result == "CONFLICT" else [],
        "dependencies": [dependency],
    }


def _graph(*claims: dict) -> dict:
    return {"entity": {"entity_type": "dummy", "canonical_id": "x"}, "claims": list(claims)}


class Phase11InvalidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        self.base = self.output / "base"
        self.current = self.output / "current"
        self.published = self.output / "published"
        for path in (self.base, self.current, self.published):
            path.mkdir(parents=True, exist_ok=True)
        (self.output / "last-run.json").write_text(json.dumps({
            "base": str(self.base), "current": str(self.current), "published": str(self.published)
        }), encoding="utf-8")
        for name, value in (("a.json", {"v": 1}), ("b.json", {"v": 1})):
            path = self.base / "game_common" / "data" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value), encoding="utf-8")
        self.store = DependencyInvalidationStore(self.output)
        self.a = "game_common/data/a.json"
        self.b = "game_common/data/b.json"
        self.c1 = "dummy:x:dummy.a"
        self.c2 = "dummy:x:dummy.b"

    def tearDown(self):
        self.temp.cleanup()

    def test_one_changed_source_invalidates_only_dependent_claim(self):
        first = self.store.evaluate([_graph(_claim("dummy.a", self.a), _claim("dummy.b", self.b))])
        self.assertEqual(0, first["claim_counts"]["invalidated"])

        path = self.current / self.a
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"v": 2}), encoding="utf-8")
        plan = self.store.invalidation_plan()
        self.assertEqual([self.c1], plan["dirty_claim_keys"])
        self.assertIn(self.c2, plan["unchanged_claim_keys"])

    def test_selective_recompute_leaves_unrelated_claim_byte_current(self):
        self.store.evaluate([_graph(_claim("dummy.a", self.a), _claim("dummy.b", self.b))])
        before = self.store.load()["claims"][self.c2]
        path = self.current / self.a
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"v": 2}), encoding="utf-8")

        report = self.store.evaluate([_graph(_claim("dummy.a", self.a, value=2))], full_snapshot=False)
        after = self.store.load()["claims"][self.c2]
        self.assertEqual(before, after)
        self.assertEqual(1, report["claim_counts"]["recomputed"])
        self.assertEqual(1, report["claim_counts"]["untouched"])
        self.assertEqual([self.c1], report["review_queue"])

    def test_patch_absent_current_table_uses_base_without_false_invalidation(self):
        self.store.evaluate([_graph(_claim("dummy.a", self.a))])
        plan = self.store.invalidation_plan()
        self.assertEqual([], plan["dirty_claim_keys"])

    def test_removed_claim_cannot_remain_current_proven(self):
        self.store.evaluate([_graph(_claim("dummy.a", self.a), _claim("dummy.b", self.b))])
        report = self.store.evaluate([], full_snapshot=False, removed_claim_keys=[self.c1])
        claims = self.store.load()["claims"]
        self.assertNotIn(self.c1, claims)
        self.assertIn(self.c2, claims)
        self.assertEqual([self.c1], report["review_queue"])
        self.assertEqual("UNRESOLVED", report["invalidated_claims"][0]["current_result"])

    def test_conflict_recomputation_is_reviewed_even_without_dependency_change(self):
        self.store.evaluate([_graph(_claim("dummy.a", self.a))])
        report = self.store.evaluate([_graph(_claim("dummy.a", self.a, result="CONFLICT", value=9))], full_snapshot=False)
        self.assertEqual([self.c1], report["review_queue"])
        self.assertEqual("CONFLICT", self.store.load()["claims"][self.c1]["result"])

    def test_history_retains_old_proof_without_making_it_current(self):
        self.store.evaluate([_graph(_claim("dummy.a", self.a))])
        self.store.evaluate([], full_snapshot=False, removed_claim_keys=[self.c1])
        payload = self.store.load()
        self.assertNotIn(self.c1, payload["claims"])
        self.assertEqual("PROVEN", payload["history"][-1]["claims"][self.c1]["result"])

    def test_affected_page_keys_are_emitted_for_review(self):
        self.store.evaluate([_graph(_claim("dummy.a", self.a))])
        path = self.current / self.a
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"v": 2}), encoding="utf-8")
        report = self.store.evaluate([_graph(_claim("dummy.a", self.a, value=2))], full_snapshot=False)
        self.assertEqual(["dummy:x"], report["affected_website_pages"])


if __name__ == "__main__":
    unittest.main()
