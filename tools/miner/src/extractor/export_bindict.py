"""Export NeoX bindict data from extracted Once Human .pyc files.

The bytecode is never executed. The script only reads the marshalled binary
dictionary payload embedded in supported data files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, set):
        return [json_safe(item) for item in sorted(value, key=repr)]
    return {"__python_type__": type(value).__name__, "repr": repr(value)}


def record_count(parsed: dict[str, Any]) -> int | None:
    data = parsed.get("data")
    return len(data) if isinstance(data, (dict, list, tuple, set)) else None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()




CURRENT_NORMALIZER_FALLBACK_TABLES = (
    "game_common/data/char_property_data.json",
    "game_common/data/equip_origin_data.json",
    "game_common/data/buff_level_data.json",
)


def materialize_base_fallback_tables(output_root: Path) -> list[dict[str, str]]:
    """Materialize stable base tables into a sparse current snapshot when absent.

    Once Human's current script patch can omit unchanged bindict tables.  The
    combat resolver already merges base + current, but the legacy weapon/armor
    normalizers still preflight these paths under current/<hash>/tables.  Copy
    only missing files from the newest available base snapshot; never overwrite
    a table exported from the current archive.
    """
    output_root = output_root.resolve()
    # Expected layout: snapshots/full/current/<hash>/tables
    try:
        current_hash_dir = output_root.parent
        current_dir = current_hash_dir.parent
        full_dir = current_dir.parent
    except Exception:
        return []
    if current_dir.name.lower() != "current":
        return []
    base_dir = full_dir / "base"
    if not base_dir.is_dir():
        return []

    base_table_roots = sorted(
        (path / "tables" for path in base_dir.iterdir() if path.is_dir() and (path / "tables").is_dir()),
        key=lambda path: path.parent.stat().st_mtime,
        reverse=True,
    )
    actions: list[dict[str, str]] = []
    for relative in CURRENT_NORMALIZER_FALLBACK_TABLES:
        target = output_root / relative
        if target.exists():
            continue
        source = next((root / relative for root in base_table_roots if (root / relative).exists()), None)
        if source is None:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        # JSON tables are small enough to copy as bytes; this preserves exact
        # mined content and avoids reparsing/reserializing source evidence.
        target.write_bytes(source.read_bytes())
        actions.append({
            "table": relative,
            "source": str(source),
            "target": str(target),
            "reason": "missing-from-current-patch-inherited-from-base",
        })
    return actions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--neoxtractor", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--game-version-file", type=Path)
    args = parser.parse_args()

    sys.path.insert(0, str(args.neoxtractor.resolve()))
    from core.bindict.parser import BindictParser  # pylint: disable=import-outside-toplevel

    bindict = BindictParser()
    # Preserve progression consumer evidence while every extracted PYC is still
    # available. This is static inspection only; bytecode is never executed.
    from weapon_progression import PYC_SCAN_SYMBOLS, PYC_TARGETS, _ascii_context, _inspect_compatible_code

    source_root = args.source.resolve()
    output_root = args.output.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    exported: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    progression_pyc_candidates: list[dict[str, Any]] = []
    scanned = 0

    for pyc_path in source_root.rglob("*.pyc"):
        scanned += 1
        raw = pyc_path.read_bytes()
        relative = pyc_path.relative_to(source_root)

        target_hits = []
        target_offsets = {}
        for target in PYC_SCAN_SYMBOLS:
            token = target.encode("ascii")
            positions = []
            start = 0
            while len(positions) < 8:
                found = raw.find(token, start)
                if found < 0:
                    break
                positions.append(found)
                start = found + 1
            if positions:
                target_hits.append(target)
                target_offsets[target] = positions
        if target_hits:
            rel_text = str(relative).replace("\\", "/")
            table_definition = bool(re.search(
                r"(?:gun_blueprint_attr_data|equip_origin_data|gun_blueprint_data)\.pyc$",
                rel_text,
                re.IGNORECASE,
            ))
            code = _inspect_compatible_code(raw)
            best_code_score = max(
                (int(row.get("score") or 0) for row in code.get("code_hits", [])),
                default=0,
            )
            score = len(target_hits) * 15 + best_code_score - (25 if table_definition else 0)
            if "preset_attack_radio" in target_hits:
                score += 25
            if "gun_preset_attack" in target_hits:
                score += 20
            if "strength_lv" in target_hits:
                score += 15
            progression_pyc_candidates.append({
                "score": score,
                "pyc": rel_text,
                "targets": target_hits,
                "target_offsets": target_offsets,
                "classification": "table-definition" if table_definition else "consumer-candidate",
                "ascii_context": {
                    target: _ascii_context(raw, positions[0])
                    for target, positions in target_offsets.items()
                },
                "code_object_inspection": code,
            })

        if not bindict.is_bindict_pyc(raw):
            continue
        try:
            parsed = bindict.extract_from_pyc(raw)
            if not parsed:
                continue
            safe = json_safe(parsed)
            json_path = output_root / relative.with_suffix(".json")
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(
                json.dumps(safe, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            exported.append(
                {
                    "source": str(relative).replace("\\", "/"),
                    "output": str(json_path.relative_to(output_root)).replace("\\", "/"),
                    "records": record_count(parsed),
                    "bytes": json_path.stat().st_size,
                }
            )
        except Exception as exc:  # keep a complete audit of unsupported tables
            errors.append(
                {
                    "source": str(relative).replace("\\", "/"),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    progression_pyc_candidates.sort(
        key=lambda row: (-int(row.get("score") or 0), row.get("classification", ""), row.get("pyc", ""))
    )
    progression_symbol_index = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "method": "raw PYC literal scan plus marshal/disassembly when runtime-compatible; no bytecode executed",
        "source_root": str(source_root),
        "targets": list(PYC_TARGETS),
        "focus_symbols": [symbol for symbol in PYC_SCAN_SYMBOLS if symbol not in PYC_TARGETS],
        "scanned_pyc_files": scanned,
        "candidate_files": len(progression_pyc_candidates),
        "consumer_candidate_files": sum(
            row.get("classification") == "consumer-candidate" for row in progression_pyc_candidates
        ),
        "arithmetic_or_rounding_candidate_files": sum(
            row.get("classification") == "consumer-candidate" and any(
                hit.get("arithmetic_ops_near_target") or hit.get("rounding_names_near_target")
                for hit in row.get("code_object_inspection", {}).get("code_hits", [])
            )
            for row in progression_pyc_candidates
        ),
        "candidates": progression_pyc_candidates,
    }
    (output_root / "pyc-progression-symbols.json").write_text(
        json.dumps(progression_symbol_index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    inherited_base_tables = materialize_base_fallback_tables(output_root)

    snapshot: dict[str, Any] = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Read-only NXPK extraction followed by NeoX bindict parsing; no game code executed",
        "source_root": str(source_root),
        "scanned_pyc_files": scanned,
        "exported_tables": len(exported),
        "parse_errors": len(errors),
        "progression_pyc_candidate_files": len(progression_pyc_candidates),
        "progression_pyc_consumer_candidates": progression_symbol_index["consumer_candidate_files"],
        "progression_pyc_arithmetic_or_rounding_candidates": progression_symbol_index["arithmetic_or_rounding_candidate_files"],
        "progression_pyc_symbol_index": "pyc-progression-symbols.json",
        "inherited_base_tables": inherited_base_tables,
        "tables": sorted(exported, key=lambda item: item["source"]),
        "errors": sorted(errors, key=lambda item: item["source"]),
    }
    if args.archive and args.archive.exists():
        snapshot["archive"] = str(args.archive.resolve())
        snapshot["archive_size"] = args.archive.stat().st_size
        snapshot["archive_sha256"] = sha256_file(args.archive)
        snapshot["archive_modified_utc"] = datetime.fromtimestamp(
            args.archive.stat().st_mtime, tz=timezone.utc
        ).isoformat()
    if args.game_version_file and args.game_version_file.exists():
        snapshot["game_version"] = args.game_version_file.read_text(
            encoding="utf-8", errors="replace"
        ).strip()

    (output_root / "snapshot.json").write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "scanned_pyc_files": scanned,
                "exported_tables": len(exported),
                "parse_errors": len(errors),
                "output": str(output_root),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
