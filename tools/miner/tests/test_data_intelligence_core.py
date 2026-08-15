from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dead_signal_analytics import flatten_source_finder, flatten_table_profiles  # noqa: E402
from dead_signal_discovery import description_hotspots, schema_clusters  # noqa: E402
from dead_signal_evidence_graph import DeadSignalEvidenceGraph  # noqa: E402
from dead_signal_pipeline_inspector import PipelineRecorder, inspect_existing_run  # noqa: E402
from dead_signal_publication_gate import decide, gate_source_finder  # noqa: E402
from dead_signal_workflow_lab import DeadSignalWorkflowLab, default_description_workflow  # noqa: E402


class DataIntelligenceCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        published = self.root / "published"
        (published / "web").mkdir(parents=True)
        (published / "data").mkdir(parents=True)
        (published / "reports").mkdir(parents=True)
        (published / "indexes").mkdir(parents=True)
        base = self.root / "base"
        current = self.root / "current"
        (base / "translate").mkdir(parents=True)
        (current / "translate").mkdir(parents=True)
        (base / "translate" / "translate_data_en.json").write_text(json.dumps({"DESC_A": "A verified-looking sentence"}), encoding="utf-8")
        (current / "translate" / "translate_data_en.json").write_text(json.dumps({"DESC_A": "A verified-looking sentence"}), encoding="utf-8")

        weapon = {
            "canonical_id": "weapon-100",
            "blueprint_id": 100,
            "item_id": 200,
            "prototype_id": 300,
            "name": "Test Pathfinder",
            "category": "Sniper Rifle",
            "rarity": "Legendary",
            "effect_resolution": {"fixed_skill_code": 400, "status": "resolved-player-facing-effect"},
        }
        (published / "web" / "weapons.json").write_text(json.dumps({"weapons": [weapon]}), encoding="utf-8")
        (self.root / "last-run.json").write_text(json.dumps({
            "published": str(published),
            "active_snapshots": {"base": str(base), "current": str(current)},
        }), encoding="utf-8")

        table_payloads = {
            ("base", "game_common/data/gun_blueprint_data.json"): {"100": {"blueprint_id": 100, "description": "DESC_A"}},
            ("current", "game_common/data/item_data.json"): {"200": {"item_id": 200, "name": "Test Pathfinder"}},
            ("base", "game_common/data/weapon_prototype_data.json"): {"300": {"prototype_id": 300}},
            ("base", "game_common/data/passive_skill_data.json"): {"400": {"skill_no": 400, "description": "Special skill text"}},
        }
        roots = {"base": base, "current": current}
        for (layer, relative), rows in table_payloads.items():
            path = roots[layer] / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"data": rows}), encoding="utf-8")

        catalogs = self.root / "catalogs"
        catalogs.mkdir()
        catalog = sqlite3.connect(catalogs / "structured-tables.sqlite")
        catalog.executescript("""
            CREATE TABLE tables (
                relative_path TEXT PRIMARY KEY,
                base_json_path TEXT,
                current_json_path TEXT,
                base_records INTEGER,
                current_records INTEGER,
                base_bytes INTEGER,
                current_bytes INTEGER,
                layer_status TEXT NOT NULL
            );
            CREATE TABLE domain_tables (
                domain TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                PRIMARY KEY (domain, relative_path)
            );
        """)
        for relative in sorted({key[1] for key in table_payloads}):
            base_path = base / relative
            current_path = current / relative
            base_present = base_path.is_file()
            current_present = current_path.is_file()
            status = "base-and-current-patch" if base_present and current_present else "current-patch-only" if current_present else "base-only"
            catalog.execute("INSERT INTO tables VALUES (?,?,?,?,?,?,?,?)", (
                relative,
                str(base_path) if base_present else None,
                str(current_path) if current_present else None,
                1 if base_present else 0,
                1 if current_present else 0,
                base_path.stat().st_size if base_present else 0,
                current_path.stat().st_size if current_present else 0,
                status,
            ))
            catalog.execute("INSERT INTO domain_tables VALUES (?,?)", ("weapons", relative))
        catalog.commit()
        catalog.close()

        tracer = sqlite3.connect(published / "indexes" / "reference-tracer.sqlite")
        tracer.execute("CREATE TABLE occurrences(value TEXT, layer TEXT, table_name TEXT, record_id TEXT, field TEXT, json_pointer TEXT)")
        tracer.executemany("INSERT INTO occurrences VALUES (?,?,?,?,?,?)", [
            ("100", "base", "game_common/data/gun_blueprint_data.json", "100", "blueprint_id", "/blueprint_id"),
            ("200", "current", "game_common/data/item_data.json", "200", "item_id", "/item_id"),
            ("300", "base", "game_common/data/weapon_prototype_data.json", "300", "prototype_id", "/prototype_id"),
            ("400", "base", "game_common/data/passive_skill_data.json", "400", "skill_no", "/skill_no"),
        ])
        tracer.commit()
        tracer.close()

    def tearDown(self):
        self.temp.cleanup()

    def test_evidence_graph_only_uses_exact_occurrences(self):
        graph = DeadSignalEvidenceGraph(self.root).weapon_graph("weapon-100")
        self.assertGreaterEqual(graph["record_counts"]["exact_occurrences"], 4)
        self.assertTrue(all(edge["authoritative"] for edge in graph["edges"]))
        self.assertIn("exact", graph["policy"]["edges"].lower())

    def test_identity_map_keeps_missing_paths_unresolved(self):
        identity = DeadSignalEvidenceGraph(self.root).identity_map("weapon-100")
        kinds = {row["kind"] for row in identity["families"]}
        self.assertIn("blueprint_id", kinds)
        self.assertIn("item_id", kinds)

    def test_workflow_lab_opens_exact_records_and_never_publishes(self):
        result = DeadSignalWorkflowLab(self.root).run(
            default_description_workflow(), context={"weapon_identity": "weapon-100"}
        )
        self.assertEqual("BLOCKED", result["result"]["publication"])
        self.assertNotEqual("VERIFIED", result["result"]["state"])
        self.assertGreater(result["result"]["candidate_count"], 0)
        self.assertTrue(any(row.get("field") == "description" for row in result["result"]["result"]))
        self.assertIn("cannot assign VERIFIED", result["policy"]["verification"])

    def test_publication_gate_requires_independent_verification(self):
        candidate = {"state": "CANDIDATE", "shared_across_weapons": False, "blockers": []}
        blocked = decide("weapon.description", candidate, {})
        self.assertFalse(blocked["publishable"])
        approved = decide("weapon.description", candidate, {
            "state": "VERIFIED",
            "evidence": ["exact_identity", "independent_source"],
        })
        self.assertTrue(approved["publishable"])

    def test_source_finder_gate_defaults_to_blocked(self):
        report = gate_source_finder({"weapons": [{
            "blueprint_id": 100,
            "name": "Test Pathfinder",
            "candidates": [{"state": "CANDIDATE", "blockers": [], "shared_across_weapons": False}],
        }]})
        self.assertEqual(0, report["record_counts"]["publishable_candidates"])

    def test_analytics_flatteners_support_research_suite_shape(self):
        source_rows = flatten_source_finder({"weapons": [{
            "blueprint_id": 100, "item_id": 200, "name": "Test Pathfinder", "state": "CANDIDATE",
            "candidates": [{"state": "CANDIDATE", "score": 90, "table": "x.json", "field": "description", "text": "Text"}],
        }]})
        self.assertEqual("Test Pathfinder", source_rows[0]["weapon"])
        tables, fields = flatten_table_profiles({"tables": [{
            "table": "x.json", "current_present": True,
            "active_profile": {
                "table": "x.json", "layer": "current", "record_count": 2, "field_count": 1,
                "record_shape_count": 1, "warnings": {},
                "fields": [{"field": "description", "coverage": 1.0, "present_records": 2,
                            "missing_records": 0, "unique_scalar_values": 2, "repeated_scalar_values": 0,
                            "identity_like": False, "description_like": True}],
            },
        }]})
        self.assertEqual(1, len(tables))
        self.assertEqual("description", fields[0]["field"])

    def test_discovery_is_structural_and_marked_non_authoritative(self):
        payload = {"tables": [
            {"table": "a.json", "active_profile": {"fields": [
                {"field": "item_id", "coverage": 1, "identity_like": True},
                {"field": "description", "coverage": 1, "description_like": True},
            ], "description_like_fields": [{"field": "description", "coverage": 1}],
               "identity_like_fields": [{"field": "item_id", "coverage": 1}], "warnings": {}, "record_count": 10}},
            {"table": "b.json", "active_profile": {"fields": [
                {"field": "item_id", "coverage": 1, "identity_like": True},
                {"field": "description", "coverage": 0.8, "description_like": True},
            ], "description_like_fields": [{"field": "description", "coverage": 0.8}],
               "identity_like_fields": [{"field": "item_id", "coverage": 1}], "warnings": {}, "record_count": 8}},
        ]}
        clusters = schema_clusters(payload, threshold=0.5)
        hotspots = description_hotspots(payload)
        self.assertEqual(1, clusters["record_counts"]["clusters"])
        self.assertEqual(2, hotspots["record_counts"]["hotspots"])
        self.assertIn("discovery-only", clusters["policy"])
        self.assertIn("exact IDs", hotspots["policy"])

    def test_pipeline_inspector_writes_branded_report(self):
        recorder = PipelineRecorder()
        recorder.record("module:test", duration_seconds=0.1)
        payload = recorder.report(self.root, result={"published": str(self.root / "published")})
        self.assertEqual("Dead Signal", payload["brand"])
        loaded = inspect_existing_run(self.root)
        self.assertEqual(1, loaded["record_counts"]["events"])


if __name__ == "__main__":
    unittest.main()
