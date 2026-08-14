#!/usr/bin/env python3
"""Produce one read-only inspection receipt for a fresh Dead Signal Miner snapshot.

The receipt combines strict all-seven contract validation with observational
Weapons, Weapon evidence, Armor, Mod, Attachment, Deviation, and Cradle audits.
Audits still run when strict materialization validation fails, so a bad snapshot
yields an actionable report instead of only an exception.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load inspection dependency: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dependencies(site_dir: Path) -> dict[str, ModuleType]:
    return {
        "materializer": _load_module(site_dir / "materialize-published-snapshot.py", "dead_signal_snapshot_materializer"),
        "weapons": _load_module(site_dir / "audit-weapons-contract.py", "dead_signal_weapons_audit"),
        "weapon_evidence": _load_module(site_dir / "audit-weapon-evidence.py", "dead_signal_weapon_evidence_audit"),
        "armor": _load_module(site_dir / "audit-armor-contract.py", "dead_signal_armor_audit"),
        "extended": _load_module(site_dir / "audit-extended-contracts.py", "dead_signal_extended_audit"),
    }


def _safe_audit(label: str, callback) -> dict[str, Any]:
    try:
        return {"status": "OK", "report": callback()}
    except Exception as error:  # audit receipt should preserve all other sections
        return {
            "status": "ERROR",
            "error": f"{type(error).__name__}: {error}",
            "audit": label,
        }


def inspect_snapshot(published: Path, *, site_dir: Path | None = None) -> dict[str, Any]:
    published = published.expanduser().resolve()
    if not published.is_dir():
        raise FileNotFoundError(f"Miner published directory not found: {published}")

    site_dir = site_dir or Path(__file__).resolve().parent
    deps = _dependencies(site_dir)
    weapons = deps["weapons"]
    weapon_evidence = deps["weapon_evidence"]
    armor = deps["armor"]
    extended = deps["extended"]
    materializer = deps["materializer"]

    weapon_source = weapons.resolve_source(published)
    weapon_audit = _safe_audit(
        "weapons",
        lambda: weapons.audit(weapons.load_contract(weapon_source)),
    )
    weapon_evidence_audit = _safe_audit(
        "weapon_evidence",
        lambda: weapon_evidence.audit(weapon_evidence.load_contract(weapon_source)),
    )
    armor_audit = _safe_audit(
        "armor",
        lambda: armor.audit(armor.load_contract(armor.resolve_source(published))),
    )
    extended_audit = _safe_audit("extended", lambda: extended.audit_root(published))

    try:
        _validated, validation_receipt, _modules = materializer.validate_snapshot(published, site_dir=site_dir)
        validation = {
            "status": "PASS",
            "materialization_allowed": True,
            "receipt": validation_receipt,
        }
    except Exception as error:
        validation = {
            "status": "FAIL",
            "materialization_allowed": False,
            "error": f"{type(error).__name__}: {error}",
        }

    sections = (
        ("weapons", weapon_audit),
        ("weapon_evidence", weapon_evidence_audit),
        ("armor", armor_audit),
        ("extended", extended_audit),
    )
    audit_errors = [name for name, section in sections if section.get("status") != "OK"]

    result = {
        "schema": "dead-signal-published-snapshot-inspection",
        "schema_version": 1,
        "published_root": str(published),
        "strict_validation": validation,
        "audits": {
            "weapons": weapon_audit,
            "weapon_evidence": weapon_evidence_audit,
            "armor": armor_audit,
            "extended": extended_audit,
        },
        "decision": {
            "may_materialize": bool(validation.get("materialization_allowed")),
            "audit_sections_with_errors": audit_errors,
            "note": (
                "Strict validation controls whether the seven browser payloads may be materialized. "
                "Research queues are observational and do not by themselves promote a category to READY or Build Lab."
            ),
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a fresh Miner published snapshot without changing repository data")
    parser.add_argument("published", type=Path, help="Fresh Miner published/ directory")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON inspection receipt path")
    args = parser.parse_args()

    report = inspect_snapshot(args.published)
    encoded = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if report["strict_validation"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
