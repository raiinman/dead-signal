#!/usr/bin/env python3
"""Materialize exact Miner compact contracts for Dead Signal static database routes.

The tool validates the public contract shape and publisher readiness markers only.
It never infers missing mechanics, compatibility, or player-selectable identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CATEGORIES = {
    "calibrations": ("dead-signal-calibrations", "calibrations.json", "DS_CALIBRATIONS_WEB", "database/calibrations/calibrations-data.js", "families"),
    "mods": ("dead-signal-mods", "mods.json", "DS_MODS_WEB", "database/mods/mods-data.js", "families"),
    "attachments": ("dead-signal-attachments", "attachments.json", "DS_ATTACHMENTS_WEB", "database/attachments/attachments-data.js", "attachments"),
    "deviations": ("dead-signal-deviations", "deviations.json", "DS_DEVIATIONS_WEB", "database/deviations/deviations-data.js", "families"),
    "cradles": ("dead-signal-cradles", "cradles.json", "DS_CRADLES_WEB", "database/cradles/cradles-data.js", "families"),
}

EXPECTED_STATUSES = {
    "mods": "mod-code-family-projection-variants-preserved",
    "attachments": "ready",
    "deviations": "display-name-families-with-source-variants-preserved",
    "cradles": "display-name-families-with-source-variants-preserved",
}

SOURCE_VARIANT_PREFIXES = {
    "deviations": "ds-dev",
    "cradles": "ds-cradle",
}

FAMILY_PREFIXES = {
    "deviations": "ds-dev-family-",
    "cradles": "ds-cradle-family-",
}

CALIBRATION_RANGES = {
    "Rare": (18.0, 25.0),
    "Epic": (26.0, 33.0),
    "Legendary": (34.0, 50.0),
}


def resolve_source(path: Path, filename: str) -> Path:
    path = path.expanduser().resolve()
    if path.is_file():
        return path
    for candidate in (path / "web" / filename, path / filename):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Could not find {filename} under {path}")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _validate_common(payload: dict[str, Any], schema: str, collection: str) -> list[dict[str, Any]]:
    if payload.get("schema") != schema:
        raise ValueError(f"Expected schema {schema!r}, found {payload.get('schema')!r}")
    records = payload.get(collection)
    if not isinstance(records, list):
        raise ValueError(f"Compact contract must contain {collection!r} array")
    if any(not isinstance(row, dict) for row in records):
        raise ValueError(f"Every {collection} record must be an object")
    ids = [_text(row.get("canonical_id")) for row in records]
    if any(not value for value in ids):
        raise ValueError(f"Every {collection} record must have canonical_id")
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate canonical IDs in {collection}")
    return records


def _validate_calibrations(payload: dict[str, Any], records: list[dict[str, Any]]) -> None:
    if payload.get("schema_version") != 2:
        raise ValueError("Current Calibration contract must use schema_version 2")
    if payload.get("publication_status") != "ready-current-system":
        raise ValueError("Current Calibration contract is not ready-current-system")
    if payload.get("expected_current_families") != 94 or len(records) != 94:
        raise ValueError("Current Calibration contract must contain exactly 94 families")
    if payload.get("duplicate_canonical_ids") or payload.get("ambiguous_family_ids") or payload.get("secondary_pool_failure_ids"):
        raise ValueError("Current Calibration contract contains unresolved identity or secondary-pool evidence")
    if (payload.get("main_roll_semantics") or {}).get("stat_id") != "D0102":
        raise ValueError("Current Calibration main roll must identify stat_id D0102")
    secondary = payload.get("secondary_roll_semantics") or {}
    if secondary.get("selection_count") != 1 or secondary.get("observed_candidate_weights") != [200, 200, 200, 200]:
        raise ValueError("Current Calibration secondary-roll contract is not proven")

    for family in records:
        canonical_id = _text(family.get("canonical_id"))
        if family.get("variant_count") != 1:
            raise ValueError(f"Calibration family {canonical_id} variant_count must be 1")
        if family.get("variant_status") != "current-system-selected-from-proven-main-roll-and-secondary-pool":
            raise ValueError(f"Calibration family {canonical_id} lacks proven current-system variant status")
        variants = family.get("variants")
        if not isinstance(variants, list) or len(variants) != 1 or not isinstance(variants[0], dict):
            raise ValueError(f"Calibration family {canonical_id} must contain exactly one current variant")
        variant = variants[0]
        rarity = _text(variant.get("rarity"))
        expected = CALIBRATION_RANGES.get(rarity)
        if expected is None:
            raise ValueError(f"Calibration family {canonical_id} has unsupported current rarity {rarity!r}")
        roll = variant.get("roll_range") or {}
        actual = (_number(roll.get("minimum_percent")), _number(roll.get("maximum_percent")))
        if actual != expected:
            raise ValueError(f"Calibration family {canonical_id} has invalid {rarity} Weapon DMG range {actual}")
        candidates = variant.get("secondary_roll_candidates")
        if not isinstance(candidates, list) or len(candidates) != 4:
            raise ValueError(f"Calibration family {canonical_id} must contain four proven secondary candidates")
        if [row.get("weight") for row in candidates if isinstance(row, dict)] != [200, 200, 200, 200]:
            raise ValueError(f"Calibration family {canonical_id} has invalid secondary candidate weights")


def _validate_attachment_contract(payload: dict[str, Any], records: list[dict[str, Any]]) -> None:
    if payload.get("schema_version") != 2 or payload.get("publication_status") != EXPECTED_STATUSES["attachments"]:
        raise ValueError("Attachment contract is not a ready schema_version 2 contract")
    if payload.get("duplicate_canonical_ids"):
        raise ValueError("Attachment contract carries duplicate canonical IDs")
    required_slots = {"Magazine", "Muzzle", "Sight", "Tactical"}
    if set(payload.get("slot_types") or []) != required_slots:
        raise ValueError("Attachment contract must expose exactly Magazine/Muzzle/Sight/Tactical player slots")
    direct = 0
    unresolved = 0
    for row in records:
        canonical_id = _text(row.get("canonical_id"))
        if _text(row.get("attachment_type")) not in required_slots:
            raise ValueError(f"Attachment {canonical_id} is not a player weapon-slot accessory")
        evidence = row.get("compatibility_evidence")
        if not isinstance(evidence, dict):
            raise ValueError(f"Attachment {canonical_id} is missing compatibility_evidence")
        status = _text(evidence.get("status"))
        if status == "direct-localized-installed-game-text":
            if not _text(evidence.get("text")) or evidence.get("source_field") != "description":
                raise ValueError(f"Attachment {canonical_id} has malformed direct compatibility evidence")
            direct += 1
        elif status == "unresolved":
            if _text(evidence.get("text")):
                raise ValueError(f"Attachment {canonical_id} unresolved evidence must not carry inferred text")
            unresolved += 1
        else:
            raise ValueError(f"Attachment {canonical_id} has unsupported compatibility evidence status {status!r}")
    counts = payload.get("record_counts") or {}
    if counts.get("direct_compatibility_text") != direct or counts.get("unresolved_compatibility") != unresolved:
        raise ValueError("Attachment compatibility evidence counts do not match record contents")


def _validate_source_variant_identity(category: str, payload: dict[str, Any], records: list[dict[str, Any]]) -> None:
    prefix = SOURCE_VARIANT_PREFIXES[category]
    family_prefix = FAMILY_PREFIXES[category]
    if payload.get("duplicate_variant_canonical_ids") or payload.get("missing_variant_canonical_ids"):
        raise ValueError(f"{category} contract contains unresolved source variant identity")
    if not _text(payload.get("variant_identity_policy")):
        raise ValueError(f"{category} contract must declare its source variant identity policy")

    variant_ids: list[str] = []
    multi = 0
    for family in records:
        family_id = _text(family.get("canonical_id"))
        if not family_id.startswith(family_prefix):
            raise ValueError(f"{category} family {family_id!r} does not use the canonical family prefix")
        variants = family.get("variants")
        if not isinstance(variants, list) or not variants:
            raise ValueError(f"{category} family {family_id} must preserve at least one source variant")
        if family.get("variant_count") != len(variants):
            raise ValueError(f"{category} family {family_id} variant_count does not match payload")
        expected_status = "single-source-record" if len(variants) == 1 else "multiple-source-variants-preserved"
        if family.get("variant_status") != expected_status:
            raise ValueError(f"{category} family {family_id} has invalid variant_status")
        if len(variants) > 1:
            multi += 1
        for variant in variants:
            if not isinstance(variant, dict):
                raise ValueError(f"{category} family {family_id} contains a non-object source variant")
            source_id = variant.get("id")
            expected_variant_id = f"{prefix}-{source_id}" if source_id not in (None, "") else ""
            canonical_variant_id = _text(variant.get("canonical_id"))
            if not expected_variant_id or canonical_variant_id != expected_variant_id:
                raise ValueError(f"{category} variant {canonical_variant_id!r} does not match source ID {source_id!r}")
            variant_ids.append(canonical_variant_id)

    if len(variant_ids) != len(set(variant_ids)):
        raise ValueError(f"{category} source variant canonical IDs must be globally unique")
    counts = payload.get("record_counts") or {}
    expected_counts = {
        "display_name_families": len(records),
        "source_variants": len(variant_ids),
        "single_variant_families": len(records) - multi,
        "multi_variant_families": multi,
    }
    for key, value in expected_counts.items():
        if counts.get(key) != value:
            raise ValueError(f"{category} record_counts.{key}={counts.get(key)!r}, expected {value}")


def _validate_family_contract(category: str, payload: dict[str, Any], records: list[dict[str, Any]]) -> None:
    if payload.get("schema_version") != 1:
        raise ValueError(f"{category} contract must use schema_version 1")
    if payload.get("publication_status") != EXPECTED_STATUSES[category]:
        raise ValueError(f"{category} contract has unexpected publication_status {payload.get('publication_status')!r}")
    if category in SOURCE_VARIANT_PREFIXES:
        _validate_source_variant_identity(category, payload, records)
        return
    for family in records:
        variants = family.get("variants")
        if not isinstance(variants, list) or not variants:
            raise ValueError(f"{category} family {_text(family.get('canonical_id'))} must preserve at least one source variant")


def load_and_validate(path: Path, category: str, schema: str, collection: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Compact contract must be a JSON object")
    records = _validate_common(payload, schema, collection)
    if category == "calibrations":
        _validate_calibrations(payload, records)
    elif category == "attachments":
        _validate_attachment_contract(payload, records)
    else:
        _validate_family_contract(category, payload, records)
    return payload


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def materialize(category: str, source_arg: Path, output_arg: Path | None = None) -> Path:
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category: {category}")
    schema, filename, variable, relative_output, collection = CATEGORIES[category]
    repository_root = Path(__file__).resolve().parents[2]
    source = resolve_source(source_arg, filename)
    payload = load_and_validate(source, category, schema, collection)
    output = output_arg.expanduser().resolve() if output_arg else repository_root / relative_output
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    output.write_text(
        "// Generated from Miner compact contract. Do not hand-edit.\n"
        f"// Source SHA-256: {file_sha(source)}\n"
        f"window.{variable}={encoded};\n",
        encoding="utf-8",
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Wrap one Miner compact category contract for the static site")
    parser.add_argument("category", choices=sorted(CATEGORIES))
    parser.add_argument("source", type=Path, help="Contract file, published/web/, or published/ directory")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    output = materialize(args.category, args.source, args.output)
    print(f"Materialized {args.category}: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
