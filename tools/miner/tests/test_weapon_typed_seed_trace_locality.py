from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from pathlib import Path

import weapon_evidence_enrichment as evidence
import weapon_reference_filter
import weapon_typed_seed_trace


weapon_reference_filter.install(evidence)
weapon_typed_seed_trace.install(evidence)


class WeaponTypedSeedTraceLocalityTests(unittest.TestCase):
    @staticmethod
    def write_table(root: Path, relative: str, data: dict) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"data": data}), encoding="utf-8")

    @staticmethod
    def weapon(name: str, item_id: int, gun_no: int) -> dict:
        return {
            "blueprint_id": item_id + 3000000,
            "item_id": item_id,
            "prototype_id": 204,
            "name": name,
            "category": "Shotgun",
            "blueprint_attribute_progression": {"levels": [{"level": 1, "fixed_skill_code": ""}]},
            "tiers": [{"tier": 1, "item_id": item_id, "gun_no": gun_no}],
            "effect_resolution": {"status": "no-fixed-skill-reference"},
            "short_description_evidence": {},
        }

    def test_logic_tree_sibling_nodes_do_not_cross_contaminate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = root / "base"
            current = root / "current"
            weapon = self.weapon("Old Machete Example", 10912101, 10912101)
            payload = {"weapons": [weapon], "record_counts": {}}
            self.write_table(current, evidence.EQUIP_TABLE, {"10912101": {"gun_no": 10912101}})
            self.write_table(
                base,
                "game_common/data/logic_tree/test.json",
                {
                    "node_list": [
                        {"effect_params": {"params": {"summon_data": {"unit_hold_item": 10912101}}}},
                        {"effect_params": {"params": {"buff_id": 60142000}}},
                    ]
                },
            )
            report = evidence.trace_blank_fixed_skill_references(
                payload, base, current, {"10912101": {"gun_no": 10912101}}
            )
            row = report["weapons"][0]
            self.assertEqual([], row["mechanic_reference_candidates"])

    def test_shared_gun_skill_is_preserved_but_not_counted_as_unique_mechanic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = root / "base"
            current = root / "current"
            aa12 = self.weapon("AA12 Example", 10231101, 10230011)
            payload = {"weapons": [aa12], "record_counts": {}}
            self.write_table(current, evidence.EQUIP_TABLE, {"10231101": {"gun_no": 10230011}})
            self.write_table(
                base,
                "game_common/data/gun_base_params_data.json",
                {
                    "10230011": {"gun_skill_no": "wp_dust_1000"},
                    "10230131": {"gun_skill_no": "wp_dust_1000"},
                },
            )
            report = evidence.trace_blank_fixed_skill_references(
                payload, base, current, {"10231101": {"gun_no": 10230011}}
            )
            row = report["weapons"][0]
            self.assertEqual([], row["mechanic_reference_candidates"])
            self.assertEqual(1, row["shared_system_reference_count"])
            self.assertEqual("shared-gun-system-skill", row["shared_system_references"][0]["classification"])
            self.assertEqual("wp_dust_1000", row["shared_system_references"][0]["value"])


if __name__ == "__main__":
    unittest.main()
