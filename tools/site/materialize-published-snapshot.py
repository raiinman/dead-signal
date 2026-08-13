#!/usr/bin/env python3
"""Validate and materialize one complete Dead Signal Miner website snapshot.

This is the repository-side handoff for a fresh Miner ``published/`` directory.
It is intentionally fail-closed and transactional:

1. require/validate every compact website contract;
2. stage every browser payload outside the live repository paths;
3. only replace repository data files after the whole snapshot passes;
4. restore the prior repository payloads if the final commit phase fails.

The tool does not normalize game data or infer missing mechanics. It delegates
category semantics to the existing strict materializers.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any


EXTENDED_CATEGORIES = ("calibrations", "mods", "attachments", "deviations", "cradles")
FINAL_OUTPUTS = {
    "weapons": Path("database/weapons/weapons-data.js"),
    "armor": Path("database/armor/armor-data.js"),
    "calibrations": Path("database/calibrations/calibrations-data.js"),
    "mods": Path("database/mods/mods-data.js"),
    "attachments": Path("database/attachments/attachments-data.js"),
    "deviations": Path("database/deviations/deviations-data.js"),
    "cradles": Path("database/cradles/cradles-data.js"),
}


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load materializer module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_materializers(site_dir: Path) -> tuple[ModuleType, ModuleType, ModuleType]:
    return (
        _load_module(site_dir / "materialize-weapons-web.py", "dead_signal_materialize_weapons"),
        _load_module(site_dir / "materialize-armor-web.py", "dead_signal_materialize_armor"),
        _load_module(site_dir / "materialize-extended-contract.py", "dead_signal_materialize_extended"),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _record_count(category: str, payload: dict[str, Any]) -> int:
    if category == "weapons":
        return len(payload.get("weapons") or [])
    if category == "armor":
        return sum(len(row.get("pieces") or []) for row in payload.get("armor_sets") or []) + len(payload.get("key_armor") or [])
    if category == "attachments":
        return len(payload.get("attachments") or [])
    return len(payload.get("families") or [])


def _report_file_state(published: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name in ("data-quality.json", "change-report.json"):
        path = published / "reports" / name
        result[name] = {
            "present": path.is_file(),
            "sha256": _sha256(path) if path.is_file() else None,
        }
    return result


def validate_snapshot(
    published: Path,
    *,
    site_dir: Path,
) -> tuple[dict[str, tuple[Path, dict[str, Any]]], dict[str, Any], tuple[ModuleType, ModuleType, ModuleType]]:
    published = published.expanduser().resolve()
    if not published.is_dir():
        raise FileNotFoundError(f"Miner published directory not found: {published}")

    weapons, armor, extended = _load_materializers(site_dir)
    validated: dict[str, tuple[Path, dict[str, Any]]] = {}

    weapons_source = weapons.resolve_source(published)
    validated["weapons"] = (weapons_source, weapons.load_and_validate(weapons_source))

    armor_source = armor.resolve_source(published)
    validated["armor"] = (armor_source, armor.load_and_validate(armor_source))

    for category in EXTENDED_CATEGORIES:
        schema, filename, _variable, _relative_output, collection = extended.CATEGORIES[category]
        source = extended.resolve_source(published, filename)
        payload = extended.load_and_validate(source, category, schema, collection)
        validated[category] = (source, payload)

    report = {
        "status": "validated",
        "published_root": str(published),
        "contracts": {
            category: {
                "source": str(source),
                "sha256": _sha256(source),
                "schema": payload.get("schema"),
                "schema_version": payload.get("schema_version"),
                "publication_status": payload.get("publication_status"),
                "generated_utc": payload.get("generated_utc"),
                "records": _record_count(category, payload),
            }
            for category, (source, payload) in validated.items()
        },
        "miner_reports": _report_file_state(published),
    }
    return validated, report, (weapons, armor, extended)


def _stage_snapshot(
    published: Path,
    validated: dict[str, tuple[Path, dict[str, Any]]],
    modules: tuple[ModuleType, ModuleType, ModuleType],
    staging_root: Path,
) -> dict[str, Path]:
    weapons, armor, extended = modules
    staged: dict[str, Path] = {}

    for category, relative_output in FINAL_OUTPUTS.items():
        output = staging_root / relative_output
        output.parent.mkdir(parents=True, exist_ok=True)
        staged[category] = output

    weapons_source, weapons_payload = validated["weapons"]
    weapons.write_browser_payload(weapons_source, staged["weapons"], weapons_payload)

    armor_source, armor_payload = validated["armor"]
    armor.write_browser_payload(armor_source, staged["armor"], armor_payload)

    for category in EXTENDED_CATEGORIES:
        extended.materialize(category, published, staged[category])

    missing = [category for category, path in staged.items() if not path.is_file()]
    if missing:
        raise RuntimeError(f"Snapshot staging did not create outputs for: {', '.join(missing)}")
    return staged


def _commit_staged(repository_root: Path, staged: dict[str, Path]) -> None:
    originals: dict[Path, bytes | None] = {}
    committed: list[Path] = []

    for category, relative_output in FINAL_OUTPUTS.items():
        if category not in staged or not staged[category].is_file():
            raise RuntimeError(f"Missing staged output for {category}")
        target = repository_root / relative_output
        originals[target] = target.read_bytes() if target.is_file() else None

    try:
        for category, relative_output in FINAL_OUTPUTS.items():
            target = repository_root / relative_output
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + ".snapshot-tmp")
            shutil.copyfile(staged[category], temporary)
            temporary.replace(target)
            committed.append(target)
    except Exception:
        for target in reversed(committed):
            previous = originals[target]
            if previous is None:
                target.unlink(missing_ok=True)
            else:
                rollback = target.with_suffix(target.suffix + ".rollback-tmp")
                rollback.write_bytes(previous)
                rollback.replace(target)
        raise


def ingest_snapshot(
    published: Path,
    *,
    repository_root: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    repository_root = repository_root.expanduser().resolve()
    site_dir = Path(__file__).resolve().parent
    validated, report, modules = validate_snapshot(published, site_dir=site_dir)

    if dry_run:
        report["status"] = "validated-dry-run"
        report["outputs_replaced"] = False
        return report

    with tempfile.TemporaryDirectory(prefix="dead-signal-snapshot-", dir=repository_root) as temp_dir:
        staged = _stage_snapshot(published.expanduser().resolve(), validated, modules, Path(temp_dir))
        _commit_staged(repository_root, staged)

    report["status"] = "materialized"
    report["outputs_replaced"] = True
    report["outputs"] = {
        category: str(repository_root / relative_output)
        for category, relative_output in FINAL_OUTPUTS.items()
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and transactionally materialize a complete Miner published snapshot"
    )
    parser.add_argument("published", type=Path, help="Fresh Miner published/ directory")
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=None,
        help="Dead Signal repository root (default: inferred from this script)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate every contract without replacing website data files")
    parser.add_argument("--report", type=Path, default=None, help="Optional JSON receipt path")
    args = parser.parse_args()

    repository_root = (
        args.repository_root.expanduser().resolve()
        if args.repository_root
        else Path(__file__).resolve().parents[2]
    )
    report = ingest_snapshot(args.published, repository_root=repository_root, dry_run=args.dry_run)

    encoded = json.dumps(report, indent=2, sort_keys=True)
    if args.report:
        report_path = args.report.expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
