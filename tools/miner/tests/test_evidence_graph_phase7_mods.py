from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

MINER = Path(__file__).resolve().parents[1]
SRC = MINER / "src"
EXTRACTOR = SRC / "extractor"
for path in (SRC, EXTRACTOR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from dead_signal_evidence_contracts import validate_generalized_graph  # noqa: E402
from dead_signal_generalized_graph import DeadSignalGeneralizedGraph  # noqa: E402
from dead_signal_mod_adapter import MOD_CONTRACT, ModAdapter  # noqa: E402
from mod_frame_enrichment import enrich as enrich_frames  # noqa: E402
from project_mod_frame_evidence import project as project_frames  # noqa: E402


def effects(levels=range(1, 18), entry=700):
    return [
        {
            "level": level,
            "name": f"Main {level}",
            "description": f"Effect level {level}",
            "attribute_codes": ["A1000"],
            "attribute_values": [level],
            "buff_id": 0,
        }
        for level in levels
    ]


def frame_evidence(frame_code=300):
    families = []
    for entry_id in (801, 802, 803, 804):
        families.append(
            {
                "entry_id": entry_id,
                "regular_levels": [1, 2, 3, 4, 5],
                "available_levels": [1, 2, 3, 4, 5],
                "identity_status": "proven-stable-regular-level-identity",
                "source_kind": "attribute",
                "attribute_codes": [f"S{entry_id}"],
                "buff_ids": [],
            }
        )
    return {
        "frame_code": frame_code,
        "sub_entry_ids": [801, 802, 803, 804],
        "sub_entry_families": families,
        "status": "proven-frame-and-sub-entry-family-identities",
        "order_semantics": "source-order-preserved; frame_lv_1..4 positional mapping unproven",
    }


def mod_row(item_id: int, *, shiny=False, missing_level_17=False) -> dict:
    return {
        "item_id": item_id,
        "id": 500,
        "mod_code": 500,
        "name": "Precision Mod" if item_id == 1001 else "Precision Mod Shiny",
        "quality": "Legendary",
        "quality_code": 4,
        "gain_path": "Securement Silo",
        "image_reference": f"icons/{item_id}.png",
        "apply_range_code": 21,
        "genre_library_code": 9,
        "frame_code": 300,
        "main_entry_code": 700,
        "is_shiny": shiny,
        "shiny_buff_id": 9901 if shiny else 0,
        "shiny_replacement_mod_code": 500 if shiny else 0,
        "main_entry_effects": effects(range(1, 17) if missing_level_17 else range(1, 18)),
        "frame_sub_entry_evidence": frame_evidence(),
        "mod_system": "current-mod-2.0",
        "owner_state": "exact-new-mod-item-owner",
        "owner_source_table": "game_common/data/new_mod_item_data.json",
    }


def web_variant(row: dict) -> dict:
    return {
        "item_id": row["item_id"],
        "id": row["id"],
        "mod_code": row["mod_code"],
        "name": row["name"],
        "rarity": row["quality"],
        "gain_path": row["gain_path"],
        "image_reference": row["image_reference"],
        "apply_range_code": row["apply_range_code"],
        "genre_library_code": row["genre_library_code"],
        "frame_code": row["frame_code"],
        "main_entry_code": row["main_entry_code"],
        "is_shiny": row["is_shiny"],
        "shiny_buff_id": row["shiny_buff_id"],
        "shiny_replacement_mod_code": row["shiny_replacement_mod_code"],
        "main_entry_effects": row["main_entry_effects"],
        "frame_sub_entry_evidence": row["frame_sub_entry_evidence"],
        "mod_system": row["mod_system"],
        "owner_state": row["owner_state"],
    }


class Phase7ModTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.output = Path(self.tmp.name)
        published = self.output / "published"
        (published / "web").mkdir(parents=True)
        (published / "data").mkdir(parents=True)
        (self.output / "last-run.json").write_text(
            json.dumps({"published": str(published)}), encoding="utf-8"
        )
        self.rows = [mod_row(1001), mod_row(1002, shiny=True)]
        (published / "data" / "mods.json").write_text(
            json.dumps({"mods": self.rows}), encoding="utf-8"
        )
        (published / "web" / "mods.json").write_text(
            json.dumps(
                {
                    "schema": "dead-signal-mods",
                    "families": [
                        {
                            "canonical_id": "ds-mod-500",
                            "family_key": "500",
                            "name": "Precision Mod",
                            "variants": [web_variant(row) for row in self.rows],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def claim(self, graph, claim_type):
        matches = [row for row in graph["claims"] if row["claim_type"] == claim_type]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_contract_is_valid(self):
        self.assertEqual(MOD_CONTRACT.validate(), [])

    def test_exact_variant_graph_is_valid_and_current(self):
        graph = ModAdapter(self.output).graph("ds-mod-var-1001")
        self.assertEqual(validate_generalized_graph(graph), [])
        self.assertEqual(graph["entity"]["canonical_id"], "ds-mod-var-1001")
        self.assertEqual(graph["compatibility"]["mod_system"], "current-mod-2.0")
        self.assertFalse(graph["compatibility"]["legacy_random_roll_records_mixed"])
        self.assertEqual(self.claim(graph, "mod.system_classification")["result"], "PROVEN")

    def test_shared_mod_code_is_ambiguous_not_identity_proof(self):
        adapter = ModAdapter(self.output)
        with self.assertRaises(ValueError):
            adapter.graph(500)
        first = adapter.graph(1001)
        second = adapter.graph(1002)
        self.assertNotEqual(first["entity"]["canonical_id"], second["entity"]["canonical_id"])

    def test_slot_family_and_main_entry_are_exact_typed_selectors(self):
        graph = ModAdapter(self.output).graph(1001)
        self.assertEqual(self.claim(graph, "mod.slot_compatibility")["result"], "PROVEN")
        self.assertEqual(self.claim(graph, "mod.family_main_attribute")["result"], "PROVEN")
        relations = {edge["relationship_type"] for edge in graph["edges"]}
        self.assertIn("mod-slot-compatibility-selector", relations)
        self.assertIn("mod-genre-family", relations)
        self.assertIn("mod-main-entry-owner", relations)

    def test_exact_levels_1_through_17_are_required(self):
        graph = ModAdapter(self.output).graph(1001)
        level_claim = self.claim(graph, "mod.levels_1_17")
        self.assertEqual(level_claim["result"], "PROVEN")
        self.assertEqual(level_claim["evidence"][0]["available_levels"], list(range(1, 18)))

        data_path = self.output / "published" / "data" / "mods.json"
        payload = json.loads(data_path.read_text(encoding="utf-8"))
        payload["mods"][0] = mod_row(1001, missing_level_17=True)
        data_path.write_text(json.dumps(payload), encoding="utf-8")
        partial = ModAdapter(self.output).graph(1001)
        partial_claim = self.claim(partial, "mod.levels_1_17")
        self.assertEqual(partial_claim["result"], "PARTIAL")
        self.assertEqual(partial_claim["missing"], [{"missing_levels": [17]}])

    def test_fixed_sub_entry_families_are_proven_but_frame_position_is_not(self):
        graph = ModAdapter(self.output).graph(1001)
        fixed = self.claim(graph, "mod.fixed_sub_attributes")
        suffix = self.claim(graph, "mod.suffix_frame_family")
        self.assertEqual(fixed["result"], "PROVEN")
        self.assertEqual(fixed["evidence"][0]["sub_entry_ids"], [801, 802, 803, 804])
        self.assertEqual(suffix["result"], "PARTIAL")
        self.assertIn("frame_lv_1..4", suffix["missing"][0])
        self.assertFalse(graph["compatibility"]["frame_position_mapping_proven"])

    def test_shiny_classification_names_exact_buff_owner(self):
        graph = ModAdapter(self.output).graph(1002)
        shiny = self.claim(graph, "mod.shiny_classification")
        self.assertEqual(shiny["result"], "PROVEN")
        self.assertTrue(shiny["evidence"][0]["is_shiny"])
        self.assertEqual(shiny["evidence"][0]["shiny_buff_id"], 9901)
        self.assertTrue(any(edge["destination"] == "buff:9901" for edge in graph["edges"]))

    def test_effect_rows_must_name_attribute_or_buff_owner(self):
        data_path = self.output / "published" / "data" / "mods.json"
        payload = json.loads(data_path.read_text(encoding="utf-8"))
        payload["mods"][0]["main_entry_effects"][0]["attribute_codes"] = []
        payload["mods"][0]["main_entry_effects"][0]["buff_id"] = 0
        data_path.write_text(json.dumps(payload), encoding="utf-8")
        graph = ModAdapter(self.output).graph(1001)
        claim = self.claim(graph, "mod.effect_ownership")
        self.assertEqual(claim["result"], "PARTIAL")
        self.assertEqual(claim["missing"][0]["level"], 1)
        self.assertIn("effect owner", claim["missing"][0]["missing"])

    def test_registry_indexes_exact_variants_and_mod_code_as_alias(self):
        graph = DeadSignalGeneralizedGraph(self.output)
        summary = graph.rebuild_entity_registry()
        self.assertEqual(summary["by_entity_type"]["mod"], 2)
        rows = graph.search_entities("500", entity_type="mod")
        self.assertEqual({row["canonical_id"] for row in rows}, {"ds-mod-var-1001", "ds-mod-var-1002"})
        routed = graph.mod_entity_graph("ds-mod-var-1001")
        self.assertEqual(routed["entity"]["entity_type"], "mod")

    def test_enrichment_stamps_current_system_and_projector_flags_wrong_system(self):
        payload = {"mods": [{"item_id": 1001, "mod_code": 500, "frame_code": 0}]}
        enriched = enrich_frames(payload, {}, {})
        self.assertEqual(enriched["mods"][0]["mod_system"], "current-mod-2.0")
        self.assertEqual(enriched["mods"][0]["owner_state"], "exact-new-mod-item-owner")
        self.assertFalse(enriched["legacy_random_roll_records_included"])

        legacyish = json.loads(json.dumps(enriched))
        legacyish["mods"][0]["mod_system"] = "legacy-random-roll-mod"
        web = {
            "schema": "dead-signal-mods",
            "record_counts": {},
            "families": [{"canonical_id": "ds-mod-500", "variants": [{"item_id": 1001}]}],
        }
        projected = project_frames(legacyish, web)
        self.assertEqual(projected["record_counts"]["mod_system_classification_failures"], 1)
        self.assertEqual(projected["mod_system_classification_failure_item_ids"], [1001])


if __name__ == "__main__":
    unittest.main()
