from __future__ import annotations

import sys
import unittest
from pathlib import Path


EXTRACTOR = Path(__file__).resolve().parents[1] / "src" / "extractor"
sys.path.insert(0, str(EXTRACTOR))

from attachment_compatibility import direct_compatibility_evidence


class AttachmentCompatibilityTests(unittest.TestCase):
    def test_projects_only_explicit_generic_categories(self):
        result = direct_compatibility_evidence(
            "Can be equipped on pistols, SMGs, and assault rifles."
        )
        self.assertEqual(result["status"], "direct-localized-installed-game-text")
        self.assertEqual(
            result["compatible_weapon_categories"],
            ["Assault Rifle", "Pistol", "Submachine Gun"],
        )
        self.assertEqual(result["scope"], "weapon-categories")
        self.assertFalse(result["named_weapon_text_present"])

    def test_preserves_named_models_without_converting_them_to_ids(self):
        result = direct_compatibility_evidence(
            "Can be equipped on KV-SBR, MPS 5, and assault rifles."
        )
        self.assertEqual(result["compatible_weapon_categories"], ["Assault Rifle"])
        self.assertEqual(result["scope"], "mixed-categories-and-named-weapons")
        self.assertTrue(result["named_weapon_text_present"])
        self.assertIn("KV-SBR", result["text"])

    def test_unresolved_description_fails_closed(self):
        result = direct_compatibility_evidence("A compact tactical accessory.")
        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(result["compatible_weapon_categories"], [])


if __name__ == "__main__":
    unittest.main()
