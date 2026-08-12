from __future__ import annotations

import hashlib
import unittest
from pathlib import Path


MINER_ROOT = Path(__file__).resolve().parents[1]


class RecoveredSourceTests(unittest.TestCase):
    def test_weapon_progression_matches_verified_release(self) -> None:
        path = MINER_ROOT / "src" / "extractor" / "weapon_progression.py"
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            "b2ad070e1f96fd7dae5a15094ff7d7a9a22ccee2f19703865d77beefffad94df",
        )

    def test_known_transport_corruption_is_absent(self) -> None:
        text = (MINER_ROOT / "src" / "extractor" / "weapon_progression.py").read_text(encoding="utf-8")
        for corrupt_token in ("cuArent", "cuABLE", "occuArences", "accuAacy"):
            self.assertNotIn(corrupt_token, text)


if __name__ == "__main__":
    unittest.main()

