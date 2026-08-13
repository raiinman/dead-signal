#!/usr/bin/env python3
"""Audit a compact Dead Signal Armor contract without inferring game behavior.

This tool verifies public identity/Tier invariants and turns evidence gaps into
explicit research queues. Cross-suit Blueprint-ID reuse is treated as a variant
family, not a collision, when the variant-aware public identity is correct.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA = "dead-signal-armor"
EXPECTED_TIERS = {1, 2, 3, 4, 5}


def resolve_source(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.is_file():
        return path
    if path.is_dir():
        for candidate in (path / "web" / "armor.json", path / "armor.json"):
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(f"Could not find published Armor JSON under: {path}")


def load_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != EXPECTED_SCHEMA:
        raise ValueError(f"Expected {EXPECTED_SCHEMA!r} compact Armor contract")
    if not isinstance(payload.get("armor_sets"), list) or not isinstance(payload.get("key_armor"), list):
        raise ValueError("Armor contract must contain armor_sets and key_armor arrays")
    return payload


def _text(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _tier_number(row: dict[str, Any]) -> int | None:
    return _int(row.get("data_level") if row.get("data_level") is not None else row.get("tier"))


def _tier_issues(piece: dict[str, Any]) -> list[str]:
    tiers = [row for row in (piece.get("tiers") or []) if isinstance(row, dict)]
    numbers = [_tier_number(row) for row in tiers]
    issues = []
    if len(tiers) != 5:
        issues.append(f"expected 5 canonical Gear Tier rows, found {len(tiers)}")
    if set(numbers) != EXPECTED_TIERS:
        issues.append(f"Gear Tier identity must be exactly I-V; found {numbers}")
    if len(numbers) != len(set(numbers)):
        issues.append("duplicate Gear Tier identity")
    return issues


def _recipe_missing_tiers(piece: dict[str, Any]) -> list[int]:
    recipes = [row for row in (piece.get("crafting_recipes") or []) if isinstance(row, dict)]
    resolved = {_tier_number(row) for row in recipes}
    resolved.discard(None)
    return sorted(EXPECTED_TIERS - resolved)


def _image_present(piece: dict[str, Any]) -> bool:
    return bool(_text(piece.get("image_asset")))


def audit(payload: dict[str, Any]) -> dict[str, Any]:
    sets = [row for row in (payload.get("armor_sets") or []) if isinstance(row, dict)]
    key_armor = [row for row in (payload.get("key_armor") or []) if isinstance(row, dict)]
    set_pieces = [piece for armor_set in sets for piece in (armor_set.get("pieces") or []) if isinstance(piece, dict)]
    pieces = set_pieces + key_armor

    contract_issues: list[str] = []
    integrity_failures: list[dict[str, Any]] = []
    missing_recipes: list[dict[str, Any]] = []
    missing_images: list[dict[str, Any]] = []
    key_effect_gaps: list[dict[str, Any]] = []
    variant_families: list[dict[str, Any]] = []

    declared = payload.get("record_counts") or {}
    actual_counts = {
        "armor_sets": len(sets),
        "set_pieces": len(set_pieces),
        "key_armor": len(key_armor),
        "armor_pieces": len(pieces),
    }
    aliases = {"set_pieces": ("set_pieces", "armor_set_pieces")}
    for key, actual in actual_counts.items():
        candidates = aliases.get(key, (key,))
        value = next((declared.get(candidate) for candidate in candidates if declared.get(candidate) is not None), None)
        if value is not None and _int(value) != actual:
            contract_issues.append(f"declared {key}={value} does not match actual records={actual}")

    set_ids = [_text(row.get("canonical_id")) for row in sets]
    piece_ids = [_text(row.get("canonical_id")) for row in pieces]
    duplicate_set_ids = sorted({value for value in set_ids if value and set_ids.count(value) > 1})
    duplicate_piece_ids = sorted({value for value in piece_ids if value and piece_ids.count(value) > 1})
    if duplicate_set_ids:
        contract_issues.append(f"duplicate canonical Armor Set IDs: {duplicate_set_ids}")
    if duplicate_piece_ids:
        contract_issues.append(f"duplicate canonical Armor piece IDs: {duplicate_piece_ids}")

    blueprint_suits: dict[int, set[int]] = defaultdict(set)

    for armor_set in sets:
        suit_id = _int(armor_set.get("suit_id"))
        set_name = _text(armor_set.get("name"))
        set_issues = []
        expected_set_id = f"ds-as-{suit_id}" if suit_id is not None else ""
        if suit_id is None:
            set_issues.append("missing suit_id")
        if not set_name:
            set_issues.append("missing set name")
        if _text(armor_set.get("canonical_id")) != expected_set_id:
            set_issues.append(f"canonical set ID must be {expected_set_id or 'unresolvable without suit_id'}")
        declared_piece_count = armor_set.get("piece_count")
        actual_piece_count = len([p for p in (armor_set.get("pieces") or []) if isinstance(p, dict)])
        if declared_piece_count is not None and _int(declared_piece_count) != actual_piece_count:
            set_issues.append(f"piece_count={declared_piece_count} does not match actual set pieces={actual_piece_count}")
        if set_issues:
            integrity_failures.append({
                "record_type": "armor_set",
                "canonical_id": _text(armor_set.get("canonical_id")),
                "name": set_name,
                "issues": set_issues,
            })

        for piece in (armor_set.get("pieces") or []):
            if not isinstance(piece, dict):
                continue
            blueprint_id = _int(piece.get("blueprint_id"))
            piece_suit_id = _int(piece.get("suit_id"))
            if suit_id is not None and blueprint_id is not None:
                blueprint_suits[blueprint_id].add(suit_id)
            issues = []
            if piece_suit_id != suit_id:
                issues.append(f"piece suit_id={piece_suit_id} does not match parent suit_id={suit_id}")
            if blueprint_id is None:
                issues.append("missing blueprint_id")
            expected = f"ds-a-{suit_id}-{blueprint_id}" if suit_id is not None and blueprint_id is not None else ""
            if _text(piece.get("canonical_id")) != expected:
                issues.append(f"variant-aware canonical piece ID must be {expected or 'unresolvable without suit_id + blueprint_id'}")
            if not _text(piece.get("name")):
                issues.append("missing piece name")
            if not _text(piece.get("slot")):
                issues.append("missing armor slot")
            issues.extend(_tier_issues(piece))
            base = {
                "record_type": "set_piece",
                "canonical_id": _text(piece.get("canonical_id")),
                "suit_id": suit_id,
                "blueprint_id": blueprint_id,
                "name": _text(piece.get("name")),
                "slot": _text(piece.get("slot")),
            }
            if issues:
                integrity_failures.append({**base, "issues": issues})
            missing = _recipe_missing_tiers(piece)
            if missing:
                missing_recipes.append({
                    **base,
                    "missing_gear_tiers": missing,
                    "classification": "unresolved-recipe-evidence",
                    "reason": "Missing crafting rows do not prove this Armor piece is non-craftable",
                })
            if not _image_present(piece):
                missing_images.append({**base, "reason": "No linked website artwork"})

    for blueprint_id, suit_ids in sorted(blueprint_suits.items()):
        if len(suit_ids) > 1:
            variant_families.append({
                "blueprint_id": blueprint_id,
                "suit_ids": sorted(suit_ids),
                "classification": "expected-cross-suit-variant-family",
                "reason": "Blueprint identity is reused across distinct suit variants; suit_id is part of canonical public identity",
            })

    for piece in key_armor:
        blueprint_id = _int(piece.get("blueprint_id"))
        expected = f"ds-ka-{blueprint_id}" if blueprint_id is not None else ""
        issues = []
        if blueprint_id is None:
            issues.append("missing blueprint_id")
        if _text(piece.get("canonical_id")) != expected:
            issues.append(f"canonical Key Armor ID must be {expected or 'unresolvable without blueprint_id'}")
        if not _text(piece.get("name")):
            issues.append("missing Key Armor name")
        if not _text(piece.get("slot")):
            issues.append("missing armor slot")
        issues.extend(_tier_issues(piece))
        base = {
            "record_type": "key_armor",
            "canonical_id": _text(piece.get("canonical_id")),
            "blueprint_id": blueprint_id,
            "name": _text(piece.get("name")),
            "slot": _text(piece.get("slot")),
        }
        if issues:
            integrity_failures.append({**base, "issues": issues})
        missing = _recipe_missing_tiers(piece)
        if missing:
            missing_recipes.append({
                **base,
                "missing_gear_tiers": missing,
                "classification": "unresolved-recipe-evidence",
                "reason": "Missing crafting rows do not prove this Key Armor is non-craftable",
            })
        if not _image_present(piece):
            missing_images.append({**base, "reason": "No linked website artwork"})
        if not _text(piece.get("key_effect")):
            key_effect_gaps.append({**base, "reason": "No resolved player-facing Key Armor effect in compact Miner contract"})

    status = "PASS" if not contract_issues and not integrity_failures else "FAIL"
    return {
        "schema": "dead-signal-armor-contract-audit",
        "schema_version": 1,
        "source_schema": payload.get("schema"),
        "source_schema_version": payload.get("schema_version"),
        "source_generated_utc": payload.get("generated_utc"),
        "policy": {
            "identity": "Set pieces require suit_id + blueprint_id identity; cross-suit Blueprint-ID reuse is valid when canonical IDs remain unique",
            "gear_tier": "Player-facing Armor Gear Tier identity is exactly I-V",
            "missing_recipe": "Missing recipe evidence is unresolved; it is never auto-classified non-craftable",
            "readiness": "A fresh installed-game snapshot must pass this identity gate before Armor is marked READY",
        },
        "counts": {
            **actual_counts,
            "contract_integrity_failures": len(contract_issues),
            "record_integrity_failures": len(integrity_failures),
            "cross_suit_variant_families": len(variant_families),
            "records_with_missing_tier_recipes": len(missing_recipes),
            "records_without_artwork": len(missing_images),
            "key_armor_without_effect": len(key_effect_gaps),
        },
        "identity_integrity": {"status": status, "issues": contract_issues},
        "queues": {
            "integrity_failures": integrity_failures,
            "cross_suit_variant_families": variant_families,
            "missing_tier_recipes": missing_recipes,
            "missing_artwork": missing_images,
            "key_armor_effect_gaps": key_effect_gaps,
        },
    }


def human_summary(report: dict[str, Any]) -> str:
    counts = report["counts"]
    lines = [
        "Dead Signal Armor contract audit",
        f"Identity integrity: {report['identity_integrity']['status']}",
        f"Armor Sets: {counts['armor_sets']}",
        f"Set pieces: {counts['set_pieces']}",
        f"Key Armor: {counts['key_armor']}",
        f"Cross-suit variant families: {counts['cross_suit_variant_families']}",
        f"Record integrity failures: {counts['record_integrity_failures']}",
        f"Records with missing Tier recipes: {counts['records_with_missing_tier_recipes']}",
        f"Records without artwork: {counts['records_without_artwork']}",
        f"Key Armor without resolved effect: {counts['key_armor_without_effect']}",
    ]
    if report["identity_integrity"]["issues"]:
        lines.extend(["", "Contract integrity issues:"])
        lines.extend(f"- {issue}" for issue in report["identity_integrity"]["issues"])
    for heading, key in (
        ("Record integrity failures", "integrity_failures"),
        ("Cross-suit variant families", "cross_suit_variant_families"),
        ("Missing Tier recipes", "missing_tier_recipes"),
    ):
        rows = report["queues"][key]
        if rows:
            lines.extend(["", heading + ":"])
            for row in rows:
                label = row.get("name") or f"Blueprint {row.get('blueprint_id')}"
                suffix = ""
                if row.get("issues"):
                    suffix = " | " + "; ".join(row["issues"])
                elif row.get("suit_ids"):
                    suffix = " | suits=" + ",".join(map(str, row["suit_ids"]))
                elif row.get("missing_gear_tiers"):
                    suffix = " | tiers=" + ",".join(map(str, row["missing_gear_tiers"]))
                lines.append(f"- {label}{suffix}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Miner published/web/armor.json")
    parser.add_argument("source", type=Path, help="armor.json, published/web/, or published/ directory")
    parser.add_argument("--json-output", type=Path, default=None)
    parser.add_argument("--text-output", type=Path, default=None)
    args = parser.parse_args()
    source = resolve_source(args.source)
    report = audit(load_contract(source))
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.text_output:
        args.text_output.parent.mkdir(parents=True, exist_ok=True)
        args.text_output.write_text(human_summary(report), encoding="utf-8")
    print(human_summary(report), end="")
    return 0 if report["identity_integrity"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
