#!/usr/bin/env python3
"""Audit the compact Weapon effect-resolution and description-provenance layer.

The audit is fail-closed for enhanced snapshots but remains observational for
older materialized contracts that predate these fields. It never interprets a
missing fixed skill as a hidden effect and never permits similarity aliases.
Short-description text must remain absent from the compact contract and from its
translation provenance metadata.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


EXPECTED_SCHEMA = "dead-signal-weapons"
DESCRIPTION_WITHHELD_STATUS = "withheld-until-short-description-resolver-is-verified"
EFFECT_STATUSES = {
    "no-fixed-skill-reference",
    "exact-fixed-skill-record-missing",
    "exact-fixed-skill-record-present-effect-text-unresolved",
    "resolved-player-facing-effect",
}
DESCRIPTION_STATUSES = {
    "no-short-description-handle",
    "translation-handle-unresolved",
    "translation-handle-resolves-consistently",
    "translation-source-conflict",
    "translation-handle-shared-across-weapons",
}


def resolve_source(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.is_file():
        return path
    if path.is_dir():
        for candidate in (path / "web" / "weapons.json", path / "weapons.json"):
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(f"Could not find published Weapons JSON under: {path}")


def load_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != EXPECTED_SCHEMA:
        raise ValueError(f"Expected {EXPECTED_SCHEMA!r} compact Weapons contract")
    if not isinstance(payload.get("weapons"), list):
        raise ValueError("Weapons contract must contain a weapons array")
    return payload


def _base(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "canonical_id": row.get("canonical_id"),
        "blueprint_id": row.get("blueprint_id"),
        "item_id": row.get("item_id"),
        "name": row.get("name"),
        "rarity": row.get("rarity"),
        "category": row.get("category"),
    }


def _effect_issues(row: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    status = str(evidence.get("status") or "")
    skill_code = str(evidence.get("fixed_skill_code") or "").strip()
    exact = bool(evidence.get("exact_passive_skill_record_present"))
    effect = bool(row.get("effect"))
    issues = []
    if status not in EFFECT_STATUSES:
        issues.append(f"unsupported effect_resolution status {status!r}")
        return issues
    if status == "no-fixed-skill-reference" and (skill_code or exact or effect):
        issues.append("no-fixed-skill-reference must have blank skill code, no exact passive record, and no effect")
    elif status == "exact-fixed-skill-record-missing" and (not skill_code or exact or effect):
        issues.append("exact-fixed-skill-record-missing requires a skill code, missing exact passive record, and no effect")
    elif status == "exact-fixed-skill-record-present-effect-text-unresolved" and (not skill_code or not exact or effect):
        issues.append("present-skill/text-unresolved requires a skill code, exact passive record, and no published effect")
    elif status == "resolved-player-facing-effect" and (not skill_code or not exact or not effect):
        issues.append("resolved-player-facing-effect requires a skill code, exact passive record, and effect")
    policy = str(evidence.get("identity_policy") or "")
    if "exact" not in policy.casefold() or "similar" not in policy.casefold():
        issues.append("effect identity policy must explicitly require exact identity and forbid similarity aliases")
    return issues


def _description_issues(row: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    issues = []
    verification = row.get("verification") or {}
    if row.get("description"):
        issues.append("player-facing description must remain blank while resolver identity is withheld")
    if verification.get("description_status") != DESCRIPTION_WITHHELD_STATUS:
        issues.append("verification.description_status must remain withheld")
    if evidence.get("publication_status") != DESCRIPTION_WITHHELD_STATUS:
        issues.append("short-description provenance publication_status must remain withheld")
    status = str(evidence.get("status") or "")
    if status not in DESCRIPTION_STATUSES:
        issues.append(f"unsupported short-description evidence status {status!r}")
    for match in evidence.get("translation_matches") or []:
        if not isinstance(match, dict):
            issues.append("translation match must be an object")
            continue
        if "text" in match:
            issues.append("suspect translated text leaked into compact provenance metadata")
        if not str(match.get("source") or "").strip() or not str(match.get("key") or "").strip():
            issues.append("translation provenance match is missing source or exact key")
    if status == "translation-handle-shared-across-weapons" and int(evidence.get("shared_weapon_handle_count") or 0) < 2:
        issues.append("shared-handle status requires shared_weapon_handle_count >= 2")
    return issues


def audit(payload: dict[str, Any]) -> dict[str, Any]:
    records = [row for row in payload.get("weapons") or [] if isinstance(row, dict)]
    enhanced = sum(isinstance(row.get("effect_resolution"), dict) for row in records)
    effect_counts: Counter[str] = Counter()
    description_counts: Counter[str] = Counter()
    issues = []
    queues = {
        "no_fixed_skill_reference": [],
        "exact_fixed_skill_record_missing": [],
        "fixed_skill_text_unresolved": [],
        "shared_short_description_handle": [],
        "translation_source_conflict": [],
        "translation_handle_unresolved": [],
    }

    if enhanced == 0:
        return {
            "schema": "dead-signal-weapon-evidence-audit",
            "schema_version": 1,
            "status": "legacy-evidence-unavailable",
            "source_generated_utc": payload.get("generated_utc"),
            "counts": {"weapons": len(records), "enhanced_weapon_records": 0},
            "issues": [],
            "queues": queues,
            "note": "Snapshot predates compact Weapon evidence enrichment; no inference is made from missing fields.",
        }
    if enhanced != len(records):
        issues.append(f"partial Weapon evidence coverage: {enhanced}/{len(records)} records")

    for row in records:
        base = _base(row)
        effect = row.get("effect_resolution")
        description = (row.get("verification") or {}).get("short_description_evidence")
        if not isinstance(effect, dict):
            issues.append({**base, "issues": ["missing effect_resolution evidence"]})
            continue
        if not isinstance(description, dict):
            issues.append({**base, "issues": ["missing short_description_evidence"]})
            continue

        effect_status = str(effect.get("status") or "")
        description_status = str(description.get("status") or "")
        effect_counts[effect_status] += 1
        description_counts[description_status] += 1
        row_issues = _effect_issues(row, effect) + _description_issues(row, description)
        if row_issues:
            issues.append({**base, "issues": row_issues})

        enriched = {**base, "fixed_skill_code": effect.get("fixed_skill_code")}
        if effect_status == "no-fixed-skill-reference":
            queues["no_fixed_skill_reference"].append(enriched)
        elif effect_status == "exact-fixed-skill-record-missing":
            queues["exact_fixed_skill_record_missing"].append(enriched)
        elif effect_status == "exact-fixed-skill-record-present-effect-text-unresolved":
            queues["fixed_skill_text_unresolved"].append(enriched)

        desc_row = {
            **base,
            "raw_handle": description.get("raw_handle"),
            "shared_weapon_handle_count": description.get("shared_weapon_handle_count"),
            "shared_weapon_identities": description.get("shared_weapon_identities") or [],
        }
        if description_status == "translation-handle-shared-across-weapons":
            queues["shared_short_description_handle"].append(desc_row)
        elif description_status == "translation-source-conflict":
            queues["translation_source_conflict"].append(desc_row)
        elif description_status == "translation-handle-unresolved":
            queues["translation_handle_unresolved"].append(desc_row)

    missing_exact = payload.get("weapon_evidence_missing_exact_identities") or []
    if missing_exact:
        issues.append(f"compact projection missing {len(missing_exact)} exact normalized Weapon identities")

    return {
        "schema": "dead-signal-weapon-evidence-audit",
        "schema_version": 1,
        "status": "pass" if not issues else "review",
        "source_generated_utc": payload.get("generated_utc"),
        "policy": {
            "effect": "Exact passive_skill_data record identity only; similar IDs are never substituted.",
            "description": "Short-description text remains withheld; only source-handle and translation key provenance may enter the compact contract.",
        },
        "counts": {
            "weapons": len(records),
            "enhanced_weapon_records": enhanced,
            "effect_resolution_statuses": dict(sorted(effect_counts.items())),
            "short_description_evidence_statuses": dict(sorted(description_counts.items())),
            "issues": len(issues),
        },
        "issues": issues,
        "queues": queues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit exact Weapon effect and short-description provenance evidence")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(load_contract(resolve_source(args.source)))
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if report["status"] in {"pass", "legacy-evidence-unavailable"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
