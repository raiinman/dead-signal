from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "src" / "dead_signal_source_finder.py"
spec = importlib.util.spec_from_file_location("dead_signal_source_finder", MODULE)
finder = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(finder)


def test_unique_exact_candidate_is_reviewable_but_not_verified() -> None:
    report = finder.build_source_finder_report(
        {
            "weapons": [
                {
                    "blueprint_id": 10,
                    "item_id": 20,
                    "name": "Test Rifle",
                    "category": "Assault Rifle",
                    "candidates": [
                        {
                            "source": "current",
                            "table": "game_common/data/weapon_ui_data.json",
                            "record_id": "20",
                            "field": "tooltip",
                            "json_pointer": "/tooltip",
                            "raw_value": "desc_key",
                            "resolved_text": "A verified-looking test sentence.",
                            "translation_matches": [{"source": "translate_data_en.json", "key": "desc_key", "text": "A verified-looking test sentence."}],
                            "translation_text_count": 1,
                            "identity_hits": [{"field": "item_id", "json_pointer": "/item_id", "value": "20"}],
                            "shared_across_weapons": False,
                            "weapon_owner_count": 1,
                        }
                    ],
                }
            ]
        }
    )

    weapon = report["weapons"][0]
    candidate = weapon["candidates"][0]
    assert weapon["state"] == "CANDIDATE"
    assert candidate["state"] == "CANDIDATE"
    assert candidate["publication_status"] == "BLOCKED-PENDING-VERIFICATION"
    assert "VERIFIED" in report["evidence_states"]
    assert report["policy"]["verification"].endswith("VERIFIED.")


def test_shared_copy_is_conflict_and_blocked() -> None:
    report = finder.build_source_finder_report(
        {
            "weapons": [
                {
                    "blueprint_id": 10,
                    "name": "Test Rifle",
                    "candidates": [
                        {
                            "table": "game_common/data/passive_skill_data.json",
                            "record_id": "900",
                            "field": "copywriting",
                            "raw_value": "same text",
                            "resolved_text": "same text",
                            "translation_text_count": 0,
                            "identity_hits": [{"field": "record_id", "json_pointer": "/data", "value": "900"}],
                            "shared_across_weapons": True,
                            "weapon_owner_count": 38,
                        }
                    ],
                }
            ]
        }
    )

    weapon = report["weapons"][0]
    candidate = weapon["candidates"][0]
    assert weapon["state"] == "CONFLICT"
    assert candidate["state"] == "CONFLICT"
    assert "shared-across-multiple-weapons" in candidate["blockers"]
    assert candidate["score"] < 0


def test_no_candidates_stays_unresolved() -> None:
    report = finder.build_source_finder_report(
        {"weapons": [{"blueprint_id": 10, "name": "Empty", "candidates": []}]}
    )
    assert report["weapons"][0]["state"] == "UNRESOLVED"
    assert report["record_counts"]["reviewable_candidates"] == 0
