from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "audit-weapon-evidence.py"
SPEC = importlib.util.spec_from_file_location("audit_weapon_evidence", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class WeaponEvidenceAuditTests(unittest.TestCase):
    def weapon(self, status: str, *, effect=None, skill="WS1", exact=False, desc_status="translation-handle-resolves-consistently"):
        if status == "no-fixed-skill-reference":
            skill = ""
            exact = False
        elif status == "resolved-player-facing-effect":
            exact = True
            effect = effect or {"name": "Resolved"}
        elif status == "exact-fixed-skill-record-present-effect-text-unresolved":
            exact = True
            effect = None
        elif status == "exact-fixed-skill-record-missing":
            exact = False
            effect = None
        return {
            "canonical_id": f"ds-w-{status}",
            "blueprint_id": 1,
            "item_id": 2,
            "name": status,
            "rarity": "Legendary",
            "category": "Melee",
            "description": "",
            "effect": effect,
            "effect_resolution": {
                "status": status,
                "fixed_skill_code": skill,
                "exact_passive_skill_record_present": exact,
                "effect_present": bool(effect),
                "identity_policy": "exact record ID only; similarity aliases are forbidden",
            },
            "verification": {
                "description_status": MODULE.DESCRIPTION_WITHHELD_STATUS,
                "short_description_evidence": {
                    "status": desc_status,
                    "publication_status": MODULE.DESCRIPTION_WITHHELD_STATUS,
                    "raw_handle": "DESC",
                    "translation_matches": [{"source": "current/translate/a.json", "key_kind": "raw", "key": "DESC"}],
                    "shared_weapon_handle_count": 1,
                },
            },
        }

    def payload(self, weapons):
        return {"schema": "dead-signal-weapons", "generated_utc": "now", "weapons": weapons}

    def test_exact_effect_states_are_separated(self):
        weapons = [
            self.weapon("no-fixed-skill-reference"),
            self.weapon("exact-fixed-skill-record-missing", skill="WS1301"),
            self.weapon("exact-fixed-skill-record-present-effect-text-unresolved", skill="WS2"),
            self.weapon("resolved-player-facing-effect", skill="WS3"),
        ]
        report = MODULE.audit(self.payload(weapons))
        self.assertEqual("pass", report["status"])
        self.assertEqual(1, len(report["queues"]["no_fixed_skill_reference"]))
        self.assertEqual(1, len(report["queues"]["exact_fixed_skill_record_missing"]))
        self.assertEqual(1, len(report["queues"]["fixed_skill_text_unresolved"]))
        self.assertEqual(4, report["counts"]["enhanced_weapon_records"])

    def test_similarity_alias_cannot_satisfy_missing_exact_record(self):
        row = self.weapon("exact-fixed-skill-record-missing", skill="WS1301")
        report = MODULE.audit(self.payload([row]))
        self.assertEqual("pass", report["status"])
        self.assertEqual("WS1301", report["queues"]["exact_fixed_skill_record_missing"][0]["fixed_skill_code"])

    def test_suspect_translation_text_leak_is_integrity_review(self):
        row = self.weapon("no-fixed-skill-reference")
        row["verification"]["short_description_evidence"]["translation_matches"][0]["text"] = "must not leak"
        report = MODULE.audit(self.payload([row]))
        self.assertEqual("review", report["status"])
        self.assertTrue(any("translated text leaked" in issue for issue in report["issues"][0]["issues"]))

    def test_shared_handle_is_observational_queue(self):
        row = self.weapon("no-fixed-skill-reference", desc_status="translation-handle-shared-across-weapons")
        row["verification"]["short_description_evidence"]["shared_weapon_handle_count"] = 3
        report = MODULE.audit(self.payload([row]))
        self.assertEqual("pass", report["status"])
        self.assertEqual(1, len(report["queues"]["shared_short_description_handle"]))

    def test_legacy_snapshot_is_explicitly_non_inferential(self):
        payload = {"schema": "dead-signal-weapons", "weapons": [{"canonical_id": "ds-w-old"}]}
        report = MODULE.audit(payload)
        self.assertEqual("legacy-evidence-unavailable", report["status"])
        self.assertEqual(0, report["counts"]["enhanced_weapon_records"])


if __name__ == "__main__":
    unittest.main()
