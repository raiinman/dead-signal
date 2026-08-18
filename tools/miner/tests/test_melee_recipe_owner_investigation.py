from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


EXTRACTOR = Path(__file__).resolve().parents[1] / "src" / "extractor"
sys.path.insert(0, str(EXTRACTOR))

from investigate_melee_recipe_owners import investigate


class MeleeRecipeOwnerInvestigationTests(unittest.TestCase):
    def test_exact_owner_match_does_not_accept_substrings(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root) / "base"
            current = Path(root) / "current"
            path = base / "game_common/data/blueprint_recipe_season_data.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(
                    {
                        "data": {
                            "13942101": {"0": {"corr_forge_lv": [1], "corr_forge_no": [33942101]}},
                            "x": {"note": "prefix-13942101-suffix"},
                        }
                    }
                ),
                encoding="utf-8",
            )
            report = investigate(base, current, {"13942101"})
            self.assertEqual(report["record_counts"]["exact_owner_candidates"], 1)
            self.assertEqual(report["records"][0]["record_id"], "13942101")
            self.assertTrue(
                any(hit["location"] == "record-key" for hit in report["records"][0]["hits"])
            )


if __name__ == "__main__":
    unittest.main()
