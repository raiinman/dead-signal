from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_deviation_adapter import DEVIATION_CONTRACT, DeviationAdapter
from dead_signal_generalized_graph import DeadSignalGeneralizedGraph


class Phase10DeviationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        self.published = self.output / "published"
        data = self.published / "data"
        data.mkdir(parents=True, exist_ok=True)
        payload = {
            "deviations": [
                {
                    "id": 101,
                    "name": "Murderous Rabbit",
                    "deviation_type_code": 2,
                    "unit_id": 5001,
                    "unit_type": 9,
                    "collection_value": 12,
                    "containment": {"base": 10, "maximum": 100, "minimum_for_work": 20, "recovery": 2},
                    "mood": {"base": 50, "maximum": 100, "recovery": 3},
                    "temperature": {"base": 20, "frostbite": -20, "heatstroke": 45},
                    "quality_coefficients": {"1": 1.0},
                    "power_coefficients": {"1": 1.2},
                    "balance_coefficients": {"1": 0.8},
                    "territory_effects": [7001],
                    "meme_ids": [8001],
                    "skills": [{"name": "Pounce", "description": "Embedded display text", "image_reference": "pounce.png"}],
                    "skill_catalog": [{"id": 9101, "name": "Pounce", "description": "Exact skill row", "image_reference": "pounce.png"}],
                    "image_reference": "rabbit-a.png",
                },
                {
                    "id": 102,
                    "name": "Murderous Rabbit",
                    "deviation_type_code": 2,
                    "unit_id": 5002,
                    "unit_type": 9,
                    "collection_value": 13,
                    "containment": {"base": 12, "maximum": 100, "minimum_for_work": 25, "recovery": 2},
                    "mood": {"base": 55, "maximum": 100, "recovery": 2},
                    "temperature": {},
                    "quality_coefficients": {},
                    "power_coefficients": {},
                    "balance_coefficients": {},
                    "territory_effects": [],
                    "meme_ids": [],
                    "skills": [{"name": "Unknown Bite", "description": "Text without an exact skill id", "image_reference": ""}],
                    "skill_catalog": [],
                    "image_reference": "rabbit-b.png",
                },
                {
                    "id": 103,
                    "name": "Lone Wolf's Whisper",
                    "deviation_type_code": 3,
                    "unit_id": 5003,
                    "unit_type": 10,
                    "collection_value": 20,
                    "containment": {},
                    "mood": {},
                    "temperature": {},
                    "quality_coefficients": {},
                    "power_coefficients": {},
                    "balance_coefficients": {},
                    "territory_effects": [],
                    "meme_ids": [8123],
                    "skills": [],
                    "skill_catalog": [],
                    "image_reference": "",
                },
            ]
        }
        (data / "deviations.json").write_text(json.dumps(payload), encoding="utf-8")
        (self.output / "last-run.json").write_text(
            json.dumps({"published": str(self.published)}), encoding="utf-8"
        )

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _claims(graph):
        return {row["claim_type"]: row for row in graph["claims"]}

    def test_contract_is_valid(self):
        self.assertEqual([], DEVIATION_CONTRACT.validate())

    def test_same_display_name_never_collapses_exact_source_variants(self):
        adapter = DeviationAdapter(self.output)
        first = adapter.graph(101)
        second = adapter.graph(102)
        self.assertEqual("ds-dev-101", first["entity"]["canonical_id"])
        self.assertEqual("ds-dev-102", second["entity"]["canonical_id"])
        with self.assertRaises(KeyError):
            adapter.graph("Murderous Rabbit")
        family = self._claims(first)["deviation.variant_family"]["evidence"][0]
        self.assertEqual([101, 102], family["variant_ids"])
        self.assertEqual(2, family["variant_count"])

    def test_exact_skill_id_proves_ability_and_creates_typed_edge(self):
        graph = DeviationAdapter(self.output).graph(101)
        claims = self._claims(graph)
        self.assertEqual("PROVEN", claims["deviation.abilities"]["result"])
        self.assertTrue(any(edge["destination"] == "deviation-skill:9101" for edge in graph["edges"]))

    def test_embedded_skill_text_without_id_stays_partial(self):
        graph = DeviationAdapter(self.output).graph(102)
        claim = self._claims(graph)["deviation.abilities"]
        self.assertEqual("PARTIAL", claim["result"])
        self.assertTrue(claim["missing"])
        self.assertEqual([], graph["edges"])

    def test_raw_trait_handles_do_not_become_player_facing_trait_proof(self):
        claim = self._claims(DeviationAdapter(self.output).graph(101))["deviation.trait_ownership"]
        self.assertEqual("PARTIAL", claim["result"])
        self.assertIn("territory_effects", claim["evidence"][0])
        self.assertTrue(claim["missing"])

    def test_meme_ids_do_not_prove_scenario_availability(self):
        claim = self._claims(DeviationAdapter(self.output).graph(103))["deviation.scenario_availability"]
        self.assertEqual("UNRESOLVED", claim["result"])
        self.assertEqual([8123], claim["evidence"][0]["meme_ids"])
        self.assertTrue(claim["missing"])

    def test_acquisition_remains_unresolved_without_typed_owner(self):
        claim = self._claims(DeviationAdapter(self.output).graph(101))["deviation.acquisition"]
        self.assertEqual("UNRESOLVED", claim["result"])
        self.assertTrue(claim["missing"])

    def test_containment_mood_power_and_artwork_preserve_exact_source_values(self):
        claims = self._claims(DeviationAdapter(self.output).graph(101))
        self.assertEqual("PROVEN", claims["deviation.containment"]["result"])
        self.assertEqual("PROVEN", claims["deviation.mood_power"]["result"])
        self.assertEqual("PROVEN", claims["deviation.artwork"]["result"])

    def test_registry_indexes_exact_variants_from_normalized_data_without_web_file(self):
        graph = DeadSignalGeneralizedGraph(self.output)
        summary = graph.rebuild_entity_registry()
        self.assertEqual(3, summary["by_entity_type"]["deviation"])
        matches = graph.search_entities("Murderous Rabbit", entity_type="deviation")
        self.assertEqual({"ds-dev-101", "ds-dev-102"}, {row["canonical_id"] for row in matches})
        exact = graph.search_entities("103", entity_type="deviation")
        self.assertEqual("ds-dev-103", exact[0]["canonical_id"])

    def test_presentation_never_has_publication_authority(self):
        presentation = DeviationAdapter(self.output).presentation(101)
        self.assertFalse(presentation["publication_authority"])


if __name__ == "__main__":
    unittest.main()
