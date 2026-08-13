#!/usr/bin/env python3
"""Check the proven Mod level frame sum without inferring frame semantics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FRAME_FIELDS = ("frame_lv_1", "frame_lv_2", "frame_lv_3", "frame_lv_4")
EXPECTED_LEVELS = list(range(1, 18))


def audit(payload: dict) -> dict:
    rows = [row for row in payload.get("progression", []) if isinstance(row, dict) and row.get("track") == "mod_level"]
    levels = []
    problems = []
    for row in rows:
        level = row.get("level")
        definition = row.get("game_definition") or {}
        values = [definition.get(field) for field in FRAME_FIELDS]
        if not isinstance(level, int) or isinstance(level, bool) or any(not isinstance(value, int) or isinstance(value, bool) for value in values):
            problems.append({"level": level, "reason": "missing-or-nonnumeric-frame"})
            continue
        levels.append(level)
        if sum(values) != level:
            problems.append({"level": level, "frame_values": values, "frame_sum": sum(values)})
    ready = sorted(levels) == EXPECTED_LEVELS and len(levels) == 17 and not problems
    return {
        "schema": "dead-signal-mod-frame-arithmetic-audit",
        "schema_version": 1,
        "ready": ready,
        "formula": "frame_lv_1 + frame_lv_2 + frame_lv_3 + frame_lv_4 = mod_level",
        "semantic_limit": "No frame-to-sub-attribute assignment, ordering, upgrade behavior, or Shiny meaning is inferred.",
        "levels": sorted(levels),
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    if source.is_dir():
        source = source / "data" / "progression.json"
    report = audit(json.loads(source.read_text(encoding="utf-8")))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
