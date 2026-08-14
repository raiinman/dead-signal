from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from research_console import ResearchConsole
from research_window import graph_groups


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class ResearchConsoleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.base = self.root / "snapshots/full/base/a/tables"
        self.current = self.root / "snapshots/full/current/b/tables"
        self.published = self.root / "published"
        self.base.mkdir(parents=True)
        self.current.mkdir(parents=True)
        write_json(self.root / "last-run.json", {
            "active_snapshots": {"base": str(self.base), "current": str(self.current)},
            "published": str(self.published),
        })
        weapons = {
            "weapons": [{
                "canonical_id": "ds-w-100", "name": "Kukri", "blueprint_id": 100,
                "item_id": 200, "gun_no": 300,
                "effect_resolution": {"status": "exact-fixed-skill-record-missing", "fixed_skill_code": "WS1301"},
                "verification": {"short_description_evidence": {"status": "translation-source-conflict", "raw_handle": "HANDLE_A"}},
                "recipes": [],
            }]
        }
        write_json(self.published / "web/weapons.json", weapons)
        write_json(self.published / "web/attachments.json", {"attachments": [{"id": 9, "name": "Blank", "status": "unresolved"}]})
        write_json(self.published / "web/deviations.json", {"deviations": [{"source_id": 1, "name": "Bee"}, {"source_id": 2, "name": "Bee"}]})
        write_json(self.published / "web/cradles.json", {"cradles": []})
        write_json(self.published / "web/mods.json", {"mods": [{"id": 1}], "mod_frame_evidence_status": "consumer semantics unresolved"})
        write_json(self.published / "data/buffs.json", {"buffs": [{"buff_id": "B100", "name": "Burn"}]})
        write_json(self.published / "reports/weapon-progression-pyc-consumers.json", {"symbols": ["get_skill_WS1301"]})
        write_json(self.published / "reports/data-quality.json", {"overall_status": "PARTIAL"})
        write_json(self.published / "reports/validation.json", {"status": "PASS"})
        write_json(self.published / "snapshot-manifest.json", {"files": []})
        write_json(self.base / "translate/translate_data_en.json", {"HANDLE_A": "Fish"})
        write_json(self.current / "translate/translate_data_en_02.json", {"HANDLE_A": "Blade"})
        database = self.published / "indexes/reference-tracer.sqlite"
        database.parent.mkdir(parents=True)
        connection = sqlite3.connect(database)
        connection.execute("CREATE TABLE occurrences (value TEXT, layer TEXT, table_name TEXT, record_id TEXT, field TEXT, json_pointer TEXT)")
        connection.executemany("INSERT INTO occurrences VALUES (?,?,?,?,?,?)", [
            ("100", "base", "gun_blueprint_data.json", "100", "record_id", "/data/100"),
            ("200", "current", "item_data.json", "200", "record_id", "/data/200"),
            ("300", "base", "weapon_prototype_data.json", "300", "gun_no", "/data/x/gun_no"),
            ("HANDLE_A", "current", "item_data.json", "200", "short_desc", "/data/200/short_desc"),
            ("HANDLE_A", "current", "item_data.json", "201", "short_desc", "/data/201/short_desc"),
        ])
        connection.commit()
        connection.close()
        self.console = ResearchConsole(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def test_exact_and_related_are_separated(self):
        exact = self.console.search("WS1301", ["PYC symbols"])
        related = self.console.search("WS1301", ["PYC symbols"], related=True)
        self.assertEqual([], exact["results"])
        self.assertEqual("related-non-authoritative", related["mode"])
        self.assertTrue(related["results"])
        self.assertTrue(all(not row["authoritative"] for row in related["results"]))

    def test_paths_cannot_escape_output(self):
        with self.assertRaisesRegex(ValueError, "inside"):
            self.console.diff_snapshots(self.root.parent, self.published)

    def test_weapon_identity_never_fuzzy_promotes(self):
        with self.assertRaisesRegex(ValueError, "No exact"):
            self.console.find_weapon("Kuk")

    def test_translation_collision_is_withheld(self):
        result = self.console.translation_forensics("HANDLE_A")
        self.assertTrue(result["disagreement"])
        self.assertEqual(2, result["shared_usage_count"])
        self.assertEqual("withheld-suspect-translation", result["publication_status"])

    def test_graph_edges_retain_provenance(self):
        graph = self.console.evidence_graph("ds-w-100")
        self.assertTrue(graph["edges"])
        self.assertTrue(all(edge["provenance"] for edge in graph["edges"]))
        self.assertTrue(all(edge["authoritative"] for edge in graph["edges"]))

    def test_visual_graph_groups_exact_nodes_and_missing_state(self):
        evidence = self.console.investigate_weapon("ds-w-100")
        groups = {row["kind"]: row for row in graph_groups(evidence)}
        self.assertEqual("present", groups["blueprint_id"]["status"])
        self.assertEqual("missing", groups["canonical_id"]["status"])
        self.assertEqual(1, groups["blueprint_id"]["present"])

    def test_static_pyc_context_is_bounded_and_non_executing(self):
        result = self.console.static_pyc_context("WS1301", context_lines=1, limit=5)
        self.assertEqual(1, result["match_count"])
        self.assertIn("not executed", result["execution_policy"])
        self.assertEqual(0, self.console.static_pyc_context("WS130", limit=5)["match_count"])

    def test_skill_triangulation_keeps_missing_exact_record_blocked(self):
        result = self.console.triangulate_weapon_skill("ds-w-100")
        self.assertEqual("WS1301", result["exact_skill_id"])
        self.assertEqual("exact-skill-record-missing", result["status"])
        self.assertEqual("blocked-missing-exact-passive-skill-record", result["promotion_status"])

    def test_baseline_classifier_and_family_delta_use_exact_keys(self):
        payload = json.loads((self.published / "web/weapons.json").read_text(encoding="utf-8"))
        payload["weapons"].extend([
            {"canonical_id": "base-1", "name": "Base", "rarity": "Common", "prototype_id": 77,
             "item_id": 701, "effect": None, "effect_resolution": {"status": "no-fixed-skill-reference"}},
            {"canonical_id": "base-2", "name": "Base Variant", "rarity": "Common", "prototype_id": 77,
             "item_id": 702, "effect": None, "effect_resolution": {"status": "no-fixed-skill-reference"}},
        ])
        write_json(self.published / "web/weapons.json", payload)
        classification = self.console.classify_weapon_baseline("base-1")
        delta = self.console.weapon_family_delta("base-1")
        self.assertEqual("baseline-pattern-supported-no-fixed-skill", classification["status"])
        self.assertEqual(2, classification["exact_family_size"])
        self.assertEqual(1, delta["comparison_count"])
        self.assertEqual(["prototype_id"], delta["comparisons"][0]["exact_shared_keys"])

    def test_unresolved_classification(self):
        queue = self.console.unresolved_queue()
        self.assertEqual(1, queue["counts"]["exact missing skill record"])
        self.assertEqual(1, queue["counts"]["translation collision/shared handle"])
        self.assertEqual(1, queue["counts"]["unresolved attachment compatibility"])
        self.assertEqual(1, queue["counts"]["ambiguous Deviation/Cradle variants"])

    def test_snapshot_diff_prioritizes_weapon_changes(self):
        before = self.root / "comparisons/before/web"
        after = self.root / "comparisons/after/web"
        write_json(before / "weapons.json", {"weapons": [{"canonical_id": "w1", "name": "Old"}]})
        write_json(after / "weapons.json", {"weapons": [{"canonical_id": "w1", "name": "New"}]})
        result = self.console.diff_snapshots(before, after)
        self.assertEqual("weapons", result["priority"][0])
        self.assertEqual(["w1"], result["categories"]["weapons"]["changed"])


if __name__ == "__main__":
    unittest.main()
