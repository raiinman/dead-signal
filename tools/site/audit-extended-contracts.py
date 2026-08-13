#!/usr/bin/env python3
"""Audit extended Dead Signal compact contracts for exact unresolved research queues.

This tool is observational. It never selects a source variant, invents player
compatibility, or promotes a category into Build Lab. It converts the compact
Mod / Attachment / Deviation / Cradle contracts into explicit record-level
queues that can be reviewed after a fresh Miner snapshot.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


CONTRACTS = {
    "mods": ("mods.json", "dead-signal-mods", "families"),
    "attachments": ("attachments.json", "dead-signal-attachments", "attachments"),
    "deviations": ("deviations.json", "dead-signal-deviations", "families"),
    "cradles": ("cradles.json", "dead-signal-cradles", "families"),
}

EXPECTED_STATUS = {
    "mods": "mod-code-family-projection-variants-preserved",
    "attachments": "ready",
    "deviations": "display-name-families-with-source-variants-preserved",
    "cradles": "display-name-families-with-source-variants-preserved",
}

PLAYER_ATTACHMENT_SLOTS = {"Sight", "Muzzle", "Tactical", "Magazine"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def resolve_contract(root: Path, filename: str) -> Path:
    root = root.expanduser().resolve()
    if root.is_file():
        return root
    for candidate in (root / "web" / filename, root / filename):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Could not find {filename} under {root}")


def load_contract(path: Path, schema: str, collection: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Compact contract must be a JSON object: {path}")
    if payload.get("schema") != schema:
        raise ValueError(f"Expected schema {schema!r}, found {payload.get('schema')!r}: {path}")
    if not isinstance(payload.get(collection), list):
        raise ValueError(f"Compact contract must contain {collection!r} array: {path}")
    return payload


def _identity_issues(records: list[dict[str, Any]]) -> list[str]:
    ids = [_text(row.get("canonical_id")) for row in records]
    issues = []
    missing = sum(not value for value in ids)
    if missing:
        issues.append(f"{missing} records missing canonical_id")
    duplicates = sorted({value for value in ids if value and ids.count(value) > 1})
    if duplicates:
        issues.append(f"duplicate canonical IDs: {duplicates}")
    return issues


def _family_stub(family: dict[str, Any]) -> dict[str, Any]:
    variants = _list(family.get("variants"))
    return {
        "canonical_id": _text(family.get("canonical_id")),
        "name": _text(family.get("name")),
        "family_key": family.get("family_key"),
        "variant_count": len(variants),
        "source_ids": [row.get("id") for row in variants if isinstance(row, dict) and row.get("id") is not None],
        "item_ids": [row.get("item_id") for row in variants if isinstance(row, dict) and row.get("item_id") is not None],
    }


def audit_mods(payload: dict[str, Any]) -> dict[str, Any]:
    families = [row for row in payload.get("families", []) if isinstance(row, dict)]
    multi_variant = []
    missing_names = []
    missing_descriptions = []
    missing_main_entry_rows = []
    shiny_variants = []
    variant_count_mismatches = []
    total_variants = 0

    for family in families:
        variants = [row for row in _list(family.get("variants")) if isinstance(row, dict)]
        total_variants += len(variants)
        stub = _family_stub(family)
        declared = family.get("variant_count")
        if declared is not None:
            try:
                mismatch = int(declared) != len(variants)
            except (TypeError, ValueError):
                mismatch = True
            if mismatch:
                variant_count_mismatches.append({**stub, "declared_variant_count": declared})
        if len(variants) != 1:
            multi_variant.append(stub)
        for variant in variants:
            identity = {
                "family_id": stub["canonical_id"],
                "family_name": stub["name"],
                "item_id": variant.get("item_id"),
                "mod_code": variant.get("mod_code"),
                "rarity": _text(variant.get("rarity")),
            }
            if not _text(variant.get("name")):
                missing_names.append(identity)
            if not _text(variant.get("description")):
                missing_descriptions.append(identity)
            if not _list(variant.get("main_entry_effects")):
                missing_main_entry_rows.append({**identity, "main_entry_code": variant.get("main_entry_code")})
            if bool(variant.get("is_shiny")):
                shiny_variants.append({
                    **identity,
                    "shiny_buff_id": variant.get("shiny_buff_id"),
                    "shiny_replacement_mod_code": variant.get("shiny_replacement_mod_code"),
                })

    return {
        "contract_issues": _identity_issues(families) + ([f"unexpected publication_status={payload.get('publication_status')!r}"] if payload.get("publication_status") != EXPECTED_STATUS["mods"] else []),
        "counts": {
            "families": len(families),
            "source_variants": total_variants,
            "multi_variant_families": len(multi_variant),
            "single_variant_families": sum(len(_list(row.get("variants"))) == 1 for row in families),
            "shiny_variants": len(shiny_variants),
        },
        "queues": {
            "multi_variant_families": multi_variant,
            "variant_count_mismatches": variant_count_mismatches,
            "variants_missing_name": missing_names,
            "variants_missing_description": missing_descriptions,
            "variants_missing_main_entry_rows": missing_main_entry_rows,
            "shiny_variants": shiny_variants,
        },
    }


def audit_attachments(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in payload.get("attachments", []) if isinstance(row, dict)]
    slot_counts: Counter[str] = Counter()
    missing_effects = []
    missing_compatibility = []
    missing_images = []
    missing_names = []
    non_player_slots = []

    for row in rows:
        slot = _text(row.get("attachment_type"))
        slot_counts[slot or "<missing>"] += 1
        identity = {
            "canonical_id": _text(row.get("canonical_id")),
            "name": _text(row.get("name")),
            "attachment_type": slot,
            "accessory_code": row.get("accessory_code"),
            "item_id": row.get("item_id"),
        }
        if slot not in PLAYER_ATTACHMENT_SLOTS:
            non_player_slots.append(identity)
        if not identity["name"]:
            missing_names.append(identity)
        if not _text(row.get("effects")) and not _list(row.get("attribute_codes")) and not row.get("passive_buff_id"):
            missing_effects.append(identity)
        if not _list(row.get("compatible_weapon_types")):
            missing_compatibility.append(identity)
        if not _text(row.get("image_reference")):
            missing_images.append(identity)

    contract_issues = _identity_issues(rows)
    if payload.get("publication_status") != EXPECTED_STATUS["attachments"]:
        contract_issues.append(f"unexpected publication_status={payload.get('publication_status')!r}")
    declared_slots = set(_list(payload.get("slot_types")))
    if declared_slots != PLAYER_ATTACHMENT_SLOTS:
        contract_issues.append(f"slot_types must be exactly {sorted(PLAYER_ATTACHMENT_SLOTS)}; found {sorted(str(value) for value in declared_slots)}")
    if _list(payload.get("duplicate_canonical_ids")):
        contract_issues.append(f"publisher reports duplicate canonical IDs: {payload.get('duplicate_canonical_ids')}")

    return {
        "contract_issues": contract_issues,
        "counts": {
            "attachments": len(rows),
            "slot_counts": dict(sorted(slot_counts.items())),
            "missing_effect_evidence": len(missing_effects),
            "missing_compatibility": len(missing_compatibility),
            "missing_images": len(missing_images),
        },
        "queues": {
            "non_player_slot_records": non_player_slots,
            "missing_names": missing_names,
            "missing_effect_evidence": missing_effects,
            "missing_compatibility": missing_compatibility,
            "missing_images": missing_images,
        },
    }


def _variant_has_skill_text(variant: dict[str, Any]) -> bool:
    for collection in (_list(variant.get("skills")), _list(variant.get("skill_catalog"))):
        for skill in collection:
            if isinstance(skill, dict) and (_text(skill.get("name")) or _text(skill.get("description"))):
                return True
    return False


def audit_deviations(payload: dict[str, Any]) -> dict[str, Any]:
    families = [row for row in payload.get("families", []) if isinstance(row, dict)]
    multi_variant = []
    missing_skill_text = []
    missing_images = []
    variant_count_mismatches = []

    for family in families:
        variants = [row for row in _list(family.get("variants")) if isinstance(row, dict)]
        stub = _family_stub(family)
        if len(variants) != 1:
            multi_variant.append(stub)
        declared = family.get("variant_count")
        try:
            mismatch = declared is not None and int(declared) != len(variants)
        except (TypeError, ValueError):
            mismatch = True
        if mismatch:
            variant_count_mismatches.append({**stub, "declared_variant_count": declared})
        for variant in variants:
            identity = {
                "family_id": stub["canonical_id"],
                "family_name": stub["name"],
                "source_id": variant.get("id"),
                "name": _text(variant.get("name")),
            }
            if not _variant_has_skill_text(variant):
                missing_skill_text.append(identity)
            if not _text(variant.get("image_reference")):
                missing_images.append(identity)

    issues = _identity_issues(families)
    if payload.get("publication_status") != EXPECTED_STATUS["deviations"]:
        issues.append(f"unexpected publication_status={payload.get('publication_status')!r}")
    return {
        "contract_issues": issues,
        "counts": {
            "families": len(families),
            "multi_variant_families": len(multi_variant),
            "variants_missing_skill_text": len(missing_skill_text),
        },
        "queues": {
            "multi_variant_families": multi_variant,
            "variant_count_mismatches": variant_count_mismatches,
            "variants_missing_skill_text": missing_skill_text,
            "variants_missing_images": missing_images,
        },
    }


def audit_cradles(payload: dict[str, Any]) -> dict[str, Any]:
    families = [row for row in payload.get("families", []) if isinstance(row, dict)]
    multi_variant = []
    missing_descriptions = []
    missing_images = []
    no_effect_reference = []
    variant_count_mismatches = []

    for family in families:
        variants = [row for row in _list(family.get("variants")) if isinstance(row, dict)]
        stub = _family_stub(family)
        if len(variants) != 1:
            multi_variant.append(stub)
        declared = family.get("variant_count")
        try:
            mismatch = declared is not None and int(declared) != len(variants)
        except (TypeError, ValueError):
            mismatch = True
        if mismatch:
            variant_count_mismatches.append({**stub, "declared_variant_count": declared})
        for variant in variants:
            identity = {
                "family_id": stub["canonical_id"],
                "family_name": stub["name"],
                "source_id": variant.get("id"),
                "name": _text(variant.get("name")),
            }
            if not _text(variant.get("description")):
                missing_descriptions.append(identity)
            if not (_text(variant.get("image_reference")) or _text(variant.get("selected_image_reference")) or _text(variant.get("equipped_image_reference"))):
                missing_images.append(identity)
            if not variant.get("buff_id") and not variant.get("keyword_id") and not _list(variant.get("attribute_codes")):
                no_effect_reference.append(identity)

    issues = _identity_issues(families)
    if payload.get("publication_status") != EXPECTED_STATUS["cradles"]:
        issues.append(f"unexpected publication_status={payload.get('publication_status')!r}")
    return {
        "contract_issues": issues,
        "counts": {
            "families": len(families),
            "multi_variant_families": len(multi_variant),
            "variants_missing_description": len(missing_descriptions),
        },
        "queues": {
            "multi_variant_families": multi_variant,
            "variant_count_mismatches": variant_count_mismatches,
            "variants_missing_description": missing_descriptions,
            "variants_missing_images": missing_images,
            "variants_without_effect_reference": no_effect_reference,
        },
    }


AUDITORS = {
    "mods": audit_mods,
    "attachments": audit_attachments,
    "deviations": audit_deviations,
    "cradles": audit_cradles,
}


def audit_root(root: Path) -> dict[str, Any]:
    result = {"categories": {}, "summary": {}}
    for category, (filename, schema, collection) in CONTRACTS.items():
        source = resolve_contract(root, filename)
        payload = load_contract(source, schema, collection)
        report = AUDITORS[category](payload)
        report["source"] = str(source)
        result["categories"][category] = report
    result["summary"] = {
        "categories_with_contract_issues": [
            category for category, report in result["categories"].items() if report.get("contract_issues")
        ],
        "mod_multi_variant_families": result["categories"]["mods"]["counts"]["multi_variant_families"],
        "attachments_missing_compatibility": result["categories"]["attachments"]["counts"]["missing_compatibility"],
        "deviation_multi_variant_families": result["categories"]["deviations"]["counts"]["multi_variant_families"],
        "cradle_multi_variant_families": result["categories"]["cradles"]["counts"]["multi_variant_families"],
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit extended compact contracts for unresolved player-facing research")
    parser.add_argument("source", type=Path, help="Miner published/, published/web/, or one matching contract file")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path")
    args = parser.parse_args()
    report = audit_root(args.source)
    encoded = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
