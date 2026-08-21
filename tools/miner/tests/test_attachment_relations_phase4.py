from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_attachment_relations import attachment_weapon_relation  # noqa: E402


class PhaseFourAttachmentRelationTests(unittest.TestCase):
    def test_exact_weapon_item_selector_resolves_named_model_without_spelling_join(self):
        attachment = {
            "compatibility_evidence": {
                "all_weapons": False,
                "compatible_weapon_categories": [],
                "named_weapon_text_present": True,
                "owner_trace": {
                    "typed_selectors": {"weapon_item_no_list": [20]},
                },
            }
        }
        self.assertEqual("compatible", attachment_weapon_relation({"category": "Pistol", "item_id": 20}, attachment))
        self.assertEqual("incompatible", attachment_weapon_relation({"category": "Pistol", "item_id": 21}, attachment))

    def test_exact_gun_selector_is_typed(self):
        attachment = {
            "compatibility_evidence": {
                "all_weapons": False,
                "compatible_weapon_categories": [],
                "named_weapon_text_present": True,
                "owner_trace": {
                    "typed_selectors": {"gun_no_list": [501]},
                },
            }
        }
        self.assertEqual("compatible", attachment_weapon_relation({"category": "Sniper Rifle", "gun_no": 501}, attachment))
        self.assertEqual("incompatible", attachment_weapon_relation({"category": "Sniper Rifle", "gun_no": 502}, attachment))

    def test_exact_weapon_type_selector_requires_weapon_type_identity(self):
        attachment = {
            "compatibility_evidence": {
                "all_weapons": False,
                "compatible_weapon_categories": [],
                "named_weapon_text_present": True,
                "owner_trace": {
                    "typed_selectors": {"weapon_type_list": [4]},
                },
            }
        }
        self.assertEqual("compatible", attachment_weapon_relation({"category": "Assault Rifle", "weapon_type_code": 4}, attachment))
        self.assertEqual("incompatible", attachment_weapon_relation({"category": "Pistol", "weapon_type_code": 1}, attachment))
        self.assertEqual("unresolved", attachment_weapon_relation({"category": "Pistol"}, attachment))

    def test_named_text_without_typed_selector_remains_unresolved(self):
        attachment = {
            "compatibility_evidence": {
                "all_weapons": False,
                "compatible_weapon_categories": [],
                "named_weapon_text_present": True,
                "owner_trace": {"typed_selectors": {}},
            }
        }
        self.assertEqual("unresolved", attachment_weapon_relation({"category": "Pistol", "item_id": 20}, attachment))


if __name__ == "__main__":
    unittest.main()
