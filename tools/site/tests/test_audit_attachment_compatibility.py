from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "audit-attachment-compatibility.py"
spec = importlib.util.spec_from_file_location("audit_attachment_compatibility", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class AttachmentCompatibilityAuditTests(unittest.TestCase):
    def payload(self):
        return {
            "schema": "dead-signal-attachments",
            "schema_version": 2,
            "publication_status": "ready",
            "record_counts": {
                "player_weapon_attachments": 4,
                "direct_compatibility_text": 3,
                "unresolved_compatibility": 1,
            },
            "attachments": [
                {
                    "canonical_id": "ds-att-sight",
                    "name": "Sight",
                    "attachment_type": "Sight",
                    "compatible_weapon_types": [],
                    "compatibility_evidence": {"status": "direct-localized-installed-game-text", "text": "Can be equipped on sniper rifles", "source_field": "description"},
                },
                {
                    "canonical_id": "ds-att-muzzle",
                    "name": "Muzzle",
                    "attachment_type": "Muzzle",
                    "compatible_weapon_types": [],
                    "compatibility_evidence": {"status": "direct-localized-installed-game-text", "text": "Can be equipped on pistols", "source_field": "description"},
                },
                {
                    "canonical_id": "ds-att-tactical",
                    "name": "Tactical",
                    "attachment_type": "Tactical",
                    "compatible_weapon_types": [],
                    "compatibility_evidence": {"status": "direct-localized-installed-game-text", "text": "Can be equipped on KAM Series Weapons", "source_field": "description"},
                },
                {
                    "canonical_id": "ds-att-magazine",
                    "name": "Magazine",
                    "attachment_type": "Magazine",
                    "compatible_weapon_types": [],
                    "compatibility_evidence": {"status": "unresolved", "text": "", "source_field": "description"},
                },
            ],
        }

    def test_direct_text_is_valid_without_inferred_codes(self):
        report = module.audit(self.payload())
        self.assertTrue(report["ready"])
        self.assertEqual(3, report["counts"]["direct_localized_compatibility"])
        self.assertEqual(1, report["counts"]["unresolved_compatibility"])
        self.assertEqual(0, report["counts"]["coded_compatibility_records"])

    def test_declared_count_mismatch_blocks_ready(self):
        payload = self.payload()
        payload["record_counts"]["direct_compatibility_text"] = 4
        report = module.audit(payload)
        self.assertFalse(report["ready"])
        self.assertIn("record_counts.direct_compatibility_text", report["count_mismatches"])


if __name__ == "__main__":
    unittest.main()
