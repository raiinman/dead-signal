from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

MINER = Path(__file__).resolve().parents[1]
SRC = MINER / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_armor_set_adapter import ArmorSetAdapter  # noqa: E402


class ArmorSetProvenanceTests(unittest.TestCase):
    def test_membership_edge_uses_exact_equipment_record(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            published = output / "published"
            (published / "web").mkdir(parents=True)
            (output / "last-run.json").write_text(json.dumps({"published": str(published)}), encoding="utf-8")
            payload = {
                "armor_sets": [{
                    "canonical_id": "ds-as-10",
                    "suit_id": 10,
                    "name": "Exact Set",
                    "set_bonuses": [{"pieces_required": 2, "attribute_code": "A0200", "attribute_value": 10, "buff_info": [], "description": "+HP"}],
                    "pieces": [{
                        "canonical_id": "ds-a-10-500",
                        "blueprint_id": 500,
                        "name": "Exact Helmet",
                        "slot_id": 21,
                        "slot": "Helmet",
                        "rarity": "Legendary",
                        "tiers": [{"item_id": 50001, "data_level": 1, "blueprint_id": 500, "attributes": [{"code": "A0200", "value": 100}]}],
                        "crafting_recipes": [],
                    }],
                }],
                "key_armor": [],
            }
            (published / "web" / "armor.json").write_text(json.dumps(payload), encoding="utf-8")
            graph = ArmorSetAdapter(output).graph("ds-as-10")
            edge = next(row for row in graph["edges"] if row["relationship_type"] == "armor-set-contains-piece")
            self.assertEqual("game_common/data/equip_data.json", edge["source_table"])
            self.assertEqual("50001", edge["source_record"])
            self.assertEqual("/suit_id", edge["selector"])


if __name__ == "__main__":
    unittest.main()
