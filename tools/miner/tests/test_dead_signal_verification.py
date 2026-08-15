from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_publication_gate import build_gate_report, candidate_key  # noqa: E402
from dead_signal_verification import delete_verification, load_verifications, save_verification  # noqa: E402


class DeadSignalVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.reports = self.root / "published" / "reports"
        self.reports.mkdir(parents=True)
        self.candidate = {
            "state": "CANDIDATE",
            "score": 90,
            "blockers": [],
            "shared_across_weapons": False,
            "source": "base",
            "table": "game_common/data/weapon_ui_data.json",
            "record_id": "100",
            "field": "description",
            "json_pointer": "/description",
            "raw_value": "DESC_A",
            "text": "Verified candidate text",
        }
        self._write_source_finder(self.candidate)

    def _write_source_finder(self, candidate):
        self.reports.joinpath("dead-signal-source-finder.json").write_text(json.dumps({
            "weapons": [{
                "blueprint_id": 100,
                "item_id": 200,
                "name": "Test Pathfinder",
                "candidates": [candidate],
            }],
        }), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def _key(self, candidate=None):
        return candidate_key("100", candidate or self.candidate)

    def test_gate_is_blocked_before_manual_verification(self):
        report = build_gate_report(self.reports)
        self.assertEqual(0, report["record_counts"]["publishable_candidates"])
        row = report["weapons"][0]["candidate_decisions"][0]
        self.assertEqual(self._key(), row["candidate_key"])
        self.assertEqual("BLOCKED", row["gate"]["decision"])

    def test_explicit_verification_can_satisfy_advisory_gate(self):
        saved = save_verification(
            self.root,
            self._key(),
            state="VERIFIED",
            evidence=["exact_identity", "independent_source"],
            note="Exact item identity confirmed in a second installed-client record.",
            source_ref="game_common/data/weapon_ui_data.json:100",
        )
        self.assertEqual("VERIFIED", saved["state"])
        report = build_gate_report(self.reports)
        self.assertEqual(1, report["record_counts"]["publishable_candidates"])
        row = report["weapons"][0]["candidate_decisions"][0]
        self.assertEqual("PUBLISHABLE", row["gate"]["decision"])
        self.assertEqual("VERIFIED", row["verification"]["state"])
        self.assertIn("public website datasets", report["policy"]["write_path"])

    def test_changed_candidate_content_invalidates_old_verification(self):
        original_key = self._key()
        save_verification(
            self.root,
            original_key,
            state="VERIFIED",
            evidence=["exact_identity", "independent_source"],
            note="Exact installed-client evidence supports the original candidate text.",
        )
        changed = dict(self.candidate)
        changed["text"] = "Different client text after a later patch"
        changed_key = self._key(changed)
        self.assertNotEqual(original_key, changed_key)
        self._write_source_finder(changed)
        report = build_gate_report(self.reports)
        row = report["weapons"][0]["candidate_decisions"][0]
        self.assertEqual(changed_key, row["candidate_key"])
        self.assertEqual({}, row["verification"])
        self.assertEqual("BLOCKED", row["gate"]["decision"])

    def test_changed_reference_path_invalidates_old_verification(self):
        original = dict(self.candidate)
        original["reference_path"] = [
            {"kind": "weapon-seed", "field": "item_id", "value": "200"},
            {"kind": "exact-reference", "source": "current", "table": "a.json", "record_id": "1", "field": "item_id", "json_pointer": "/item_id", "value": "200", "depth": 0},
        ]
        changed = dict(original)
        changed["reference_path"] = [
            {"kind": "weapon-seed", "field": "item_id", "value": "200"},
            {"kind": "exact-reference", "source": "current", "table": "b.json", "record_id": "1", "field": "item_id", "json_pointer": "/item_id", "value": "200", "depth": 0},
        ]
        self.assertNotEqual(self._key(original), self._key(changed))

    def test_missing_required_evidence_stays_blocked(self):
        save_verification(
            self.root,
            self._key(),
            state="VERIFIED",
            evidence=["exact_identity"],
            note="Identity was checked but independent source proof is still missing.",
        )
        report = build_gate_report(self.reports)
        decision = report["weapons"][0]["candidate_decisions"][0]["gate"]
        self.assertFalse(decision["publishable"])
        self.assertIn("missing-verification:independent_source", decision["blockers"])

    def test_conflict_review_blocks_candidate(self):
        save_verification(
            self.root,
            self._key(),
            state="CONFLICT",
            evidence=["exact_identity", "independent_source"],
            note="Independent source points at different player-facing copy.",
        )
        report = build_gate_report(self.reports)
        decision = report["weapons"][0]["candidate_decisions"][0]["gate"]
        self.assertFalse(decision["publishable"])
        self.assertIn("conflicting-evidence", decision["blockers"])

    def test_verification_registry_is_manual_and_removable(self):
        key = self._key()
        save_verification(
            self.root,
            key,
            state="VERIFIED",
            evidence=["exact_identity", "independent_source"],
            note="Manual review with exact installed-client evidence completed.",
        )
        registry = load_verifications(self.root)
        self.assertTrue(registry["verifications"][key]["manual"])
        self.assertTrue(delete_verification(self.root, key))
        self.assertNotIn(key, load_verifications(self.root)["verifications"])

    def test_legacy_index_key_is_read_compatible(self):
        save_verification(
            self.root,
            "100:0",
            state="VERIFIED",
            evidence=["exact_identity", "independent_source"],
            note="Legacy local review remains readable during migration.",
        )
        report = build_gate_report(self.reports)
        row = report["weapons"][0]["candidate_decisions"][0]
        self.assertEqual("100:0", row["legacy_candidate_key"])
        self.assertEqual("PUBLISHABLE", row["gate"]["decision"])

    def test_short_or_unknown_verification_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            save_verification(
                self.root, self._key(), state="VERIFIED",
                evidence=["exact_identity", "made_up"], note="Valid long note here",
            )
        with self.assertRaises(ValueError):
            save_verification(
                self.root, self._key(), state="VERIFIED",
                evidence=["exact_identity", "independent_source"], note="short",
            )


if __name__ == "__main__":
    unittest.main()
