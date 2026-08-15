"""Generalized Dead Signal Publication Gate.

Publication eligibility is intentionally separate from extraction, resolution,
analytics, and workflow discovery. A field can only become publishable through an
explicit policy plus independent verification evidence. This module does not
rewrite public datasets; it emits gate decisions for review and later projectors.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from dead_signal_verification import load_verifications


SCHEMA_VERSION = 1
STATES = ("EXTRACTED", "RESOLVED", "CANDIDATE", "VERIFIED", "CONFLICT", "UNRESOLVED")

DEFAULT_POLICIES = {
    "weapon.description": {
        "required_state": "VERIFIED",
        "allow_shared": False,
        "allow_conflict": False,
        "required_evidence": ("exact_identity", "independent_source"),
    },
    "weapon.special_skill": {
        "required_state": "VERIFIED",
        "allow_shared": True,
        "allow_conflict": False,
        "required_evidence": ("exact_fixed_skill",),
    },
    "generic.player_facing_text": {
        "required_state": "VERIFIED",
        "allow_shared": False,
        "allow_conflict": False,
        "required_evidence": ("exact_identity",),
    },
}


def _stable_reference_path(candidate: dict[str, Any]) -> list[dict[str, str]]:
    """Project only exact path provenance into the verification hash."""
    stable = []
    for hop in candidate.get("reference_path") or []:
        if not isinstance(hop, dict):
            continue
        stable.append({
            key: str(hop.get(key) or "")
            for key in (
                "kind", "field", "value", "source", "table", "record_id",
                "json_pointer", "depth",
            )
        })
    return stable


def candidate_key(weapon_key: object, candidate: dict[str, Any]) -> str:
    """Return a stable review key bound to exact candidate provenance and content."""
    weapon = str(weapon_key or "").strip()
    provenance = {
        "weapon": weapon,
        "source": str(candidate.get("source") or ""),
        "table": str(candidate.get("table") or ""),
        "record_id": str(candidate.get("record_id") or ""),
        "field": str(candidate.get("field") or ""),
        "json_pointer": str(candidate.get("json_pointer") or ""),
        "raw_value": str(candidate.get("raw_value") or ""),
        "text": str(candidate.get("text") or ""),
        "reference_path": _stable_reference_path(candidate),
    }
    encoded = json.dumps(provenance, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{weapon}:{hashlib.sha256(encoded).hexdigest()[:20]}"


def decide(subject: str, candidate: dict[str, Any], verification: dict[str, Any] | None = None,
           *, policies: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    policies = policies or DEFAULT_POLICIES
    policy = policies.get(subject) or policies["generic.player_facing_text"]
    verification = verification or {}
    candidate_state = str(candidate.get("state") or "UNRESOLVED").upper()
    verified_state = str(verification.get("state") or "").upper()
    evidence = set(str(value) for value in verification.get("evidence") or [])
    shared = bool(candidate.get("shared_across_weapons") or candidate.get("shared"))
    blockers = list(candidate.get("blockers") or [])

    if candidate_state == "CONFLICT" or verified_state == "CONFLICT" or verification.get("conflict"):
        blockers.append("conflicting-evidence")
    if shared and not policy.get("allow_shared"):
        blockers.append("shared-value-not-allowed")
    missing_evidence = [value for value in policy.get("required_evidence") or () if value not in evidence]
    blockers.extend(f"missing-verification:{value}" for value in missing_evidence)
    if verified_state != policy.get("required_state"):
        blockers.append(f"state-must-be-{policy.get('required_state')}")

    unique_blockers = sorted(set(str(value) for value in blockers if value))
    publishable = not unique_blockers
    return {
        "schema": "dead-signal-publication-gate-decision",
        "schema_version": SCHEMA_VERSION,
        "subject": subject,
        "candidate_state": candidate_state,
        "verification_state": verified_state or "NONE",
        "publishable": publishable,
        "decision": "PUBLISHABLE" if publishable else "BLOCKED",
        "blockers": unique_blockers,
        "required_evidence": list(policy.get("required_evidence") or ()),
        "evidence_present": sorted(evidence),
        "verification_note": verification.get("note"),
        "verification_source_ref": verification.get("source_ref"),
        "policy": policy,
    }


def gate_source_finder(source_finder: dict[str, Any], verifications: dict[str, Any] | None = None) -> dict[str, Any]:
    verifications = verifications or {}
    rows = []
    publishable = 0
    for weapon in source_finder.get("weapons") or []:
        if not isinstance(weapon, dict):
            continue
        weapon_key = str(weapon.get("blueprint_id") or weapon.get("item_id") or weapon.get("name") or "")
        candidate_rows = []
        for index, candidate in enumerate(weapon.get("candidates") or []):
            stable_key = candidate_key(weapon_key, candidate)
            legacy_key = f"{weapon_key}:{index}"
            verification = verifications.get(stable_key) or verifications.get(legacy_key) or verifications.get(weapon_key) or {}
            decision = decide("weapon.description", candidate, verification)
            candidate_rows.append({
                "candidate_key": stable_key,
                "legacy_candidate_key": legacy_key,
                "candidate": candidate,
                "verification": verification,
                "gate": decision,
            })
            publishable += int(decision["publishable"])
        rows.append({
            "blueprint_id": weapon.get("blueprint_id"),
            "item_id": weapon.get("item_id"),
            "name": weapon.get("name"),
            "candidate_decisions": candidate_rows,
            "publishable_candidate_count": sum(int(row["gate"]["publishable"]) for row in candidate_rows),
        })
    return {
        "schema": "dead-signal-publication-gate-report",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Weapon Description",
        "record_counts": {"weapons": len(rows), "publishable_candidates": publishable, "manual_verifications": len(verifications)},
        "weapons": rows,
        "policy": {
            "separation": "Extraction, resolution, candidacy, verification, and publication are separate states.",
            "verification": "Only explicit independent verification can satisfy the gate.",
            "verification_keys": "Candidate verification keys are stable hashes of exact endpoint provenance, exact reference path, and content; changed evidence requires fresh review.",
            "write_path": "This report is advisory; it does not rewrite public website datasets.",
        },
    }


def build_gate_report(reports: Path | str) -> dict[str, Any]:
    reports = Path(reports).expanduser().resolve()
    source_path = reports / "dead-signal-source-finder.json"
    output = reports.parent.parent
    try:
        source = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        source = {"weapons": []}
    verification_payload = load_verifications(output)
    verifications = verification_payload.get("verifications") or {}
    report = gate_source_finder(source, verifications)
    report["verification_registry"] = str(output / "research" / "verifications.json")
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "dead-signal-publication-gate.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report