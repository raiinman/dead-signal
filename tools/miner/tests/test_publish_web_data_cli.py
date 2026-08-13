import io
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from extractor import publish_web_data


class PublishWebDataCliTests(unittest.TestCase):
    def test_blocked_quality_is_reported_without_failing_process(self) -> None:
        result = {
            "quality": {
                "overall_status": "BLOCKED",
                "categories": {
                    "weapons": {
                        "record_count": 120,
                        "blockers": ["Unresolved firearm profiles: 1"],
                        "warnings": ["Weapon effect text unresolved or absent: 2"],
                    },
                    "armor": {"record_count": 173, "blockers": [], "warnings": []},
                },
            },
            "snapshot_manifest": "published/snapshot-manifest.json",
        }
        output = io.StringIO()
        argv = [
            "publish_web_data.py",
            "--data-dir", "data",
            "--published", "published",
            "--miner-version", "1.5.12.1",
        ]
        with patch.object(sys, "argv", argv), patch.object(publish_web_data, "publish", return_value=result):
            with redirect_stdout(output):
                exit_code = publish_web_data.main()

        text = output.getvalue()
        self.assertEqual(0, exit_code)
        self.assertIn("Web publish: BLOCKED", text)
        self.assertIn("Quality blocker [weapons]: Unresolved firearm profiles: 1", text)
        self.assertIn("Quality warning [weapons]: Weapon effect text unresolved or absent: 2", text)


if __name__ == "__main__":
    unittest.main()
