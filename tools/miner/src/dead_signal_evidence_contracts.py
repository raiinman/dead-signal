"""Versioned generalized evidence contracts for Dead Signal.

Phase 1 deliberately separates the new strict contracts from the protected
Weapons v1 payload.  Legacy weapon graphs can be projected into this schema
without mutating ``weapon_graph(identity)``.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any


GENERAL_SCHEMA = "dead-signal-generalized-evidence-graph"
GENERAL_SCHEMA_VERSION = 1
ENTITY_SCHEMA_VERSION = 1
CLAIM_SCHEMA_VERSION = 1
EDGE_SCHEMA_VERSION = 1
ASSESSMENT_SCHEMA_VERSION = 1

EVIDENCE_STATES = (
    "PROVEN",
    "PARTIAL",
    "UNRESOLVED",
    "NOT APPLICABLE",
    "CONFLICT",
)

_STATE_ALIASES = {
    "VERIFIED": "PROVEN",
    "PROVEN": "PROVEN",
    "PARTIAL": "PARTIAL",
    "UNRESOLVED": "UNRESOLVED",
    "UNKNOWN": "UNRESOLVED",
    "MISSING": "UNRESOLVED",
    "NOT APPLICABLE": "NOT APPLICABLE",
    "NOT_APPLICABLE": "NOT APPLICABLE",
    "N/A": "NOT APPLICABLE",
    "NA": "NOT APPLICABLE",
    "CONFLICT": "CONFLICT",
    "CONFLICTING": "CONFLICT",
}


def normalize_evidence_state(value: object) -> str:
    """Normalize known evidence labels and fail closed on unknown states."""
    text = str(value or "").strip().upper().replace("-", "_")
    normalized = _STATE_ALIASES.get(text)
    if normalized is None:
        raise ValueError(f"Unknown evidence state: {value!r}")
    return normalized


def dependency_fingerprint(*parts: object) -> str:
    """Return a stable fingerprint for one provenance/dependency tuple."""
    encoded = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _nonempty(value: object) -> bool:
    return bool(str(value or "").strip())


def validate_entity(entity: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("schema_version", "entity_type", "canonical_id", "name", "classification", "identity_state", "source_records"):
        if key not in entity:
            errors.append(f"entity missing field: {key}")
    if entity.get("schema_version") != ENTITY_SCHEMA_VERSION:
        errors.append("entity schema_version unsupported")
    for key in ("entity_type", "canonical_id", "name"):
        if key in entity and not _nonempty(entity.get(key)):
            errors.append(f"entity field must be non-empty: {key}")
    try:
        normalize_evidence_state(entity.get("identity_state"))
    except ValueError as exc:
        errors.append(str(exc))
    if not isinstance(entity.get("source_records"), list):
        errors.append("entity source_records must be a list")
    return errors


def validate_edge(edge: dict[str, Any]) -> list[str]:
    """Validate a generalized edge. Provenance is mandatory for every edge."""
    errors: list[str] = []
    required = (
        "schema_version",
        "source",
        "destination",
        "relationship_type",
        "source_table",
        "source_record",
        "selector",
        "layer",
        "authority",
        "state",
        "dependency_fingerprint",
    )
    for key in required:
        if key not in edge:
            errors.append(f"edge missing field: {key}")
    if edge.get("schema_version") != EDGE_SCHEMA_VERSION:
        errors.append("edge schema_version unsupported")
    for key in (
        "source",
        "destination",
        "relationship_type",
        "source_table",
        "source_record",
        "selector",
        "layer",
        "authority",
        "dependency_fingerprint",
    ):
        if key in edge and not _nonempty(edge.get(key)):
            errors.append(f"edge provenance must be non-empty: {key}")
    try:
        normalize_evidence_state(edge.get("state"))
    except ValueError as exc:
        errors.append(str(exc))
    fingerprint = str(edge.get("dependency_fingerprint") or "")
    if fingerprint and (len(fingerprint) != 64 or any(ch not in "0123456789abcdef" for ch in fingerprint.lower())):
        errors.append("edge dependency_fingerprint must be a SHA-256 hex digest")
    return errors


def validate_claim(claim: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "schema_version",
        "claim_type",
        "subject",
        "result",
        "requirements",
        "evidence",
        "missing",
        "conflicts",
        "dependencies",
    )
    for key in required:
        if key not in claim:
            errors.append(f"claim missing field: {key}")
    if claim.get("schema_version") != CLAIM_SCHEMA_VERSION:
        errors.append("claim schema_version unsupported")
    if not _nonempty(claim.get("claim_type")):
        errors.append("claim_type must be non-empty")
    if not isinstance(claim.get("subject"), dict):
        errors.append("claim subject must be an object")
    for key in ("requirements", "evidence", "missing", "conflicts", "dependencies"):
        if not isinstance(claim.get(key), list):
            errors.append(f"claim {key} must be a list")
    try:
        state = normalize_evidence_state(claim.get("result"))
    except ValueError as exc:
        errors.append(str(exc))
        state = None
    if state == "PROVEN":
        if not claim.get("evidence"):
            errors.append("PROVEN claim requires evidence")
        if claim.get("missing"):
            errors.append("PROVEN claim cannot have missing requirements")
        if claim.get("conflicts"):
            errors.append("PROVEN claim cannot have conflicts")
    elif state == "PARTIAL":
        if not claim.get("missing"):
            errors.append("PARTIAL claim requires a named missing requirement")
    elif state == "CONFLICT" and not claim.get("conflicts"):
        errors.append("CONFLICT claim requires conflict evidence")
    return errors


def validate_assessment(assessment: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ("schema_version", "result", "claim_counts", "missing", "conflicts")
    for key in required:
        if key not in assessment:
            errors.append(f"assessment missing field: {key}")
    if assessment.get("schema_version") != ASSESSMENT_SCHEMA_VERSION:
        errors.append("assessment schema_version unsupported")
    try:
        normalize_evidence_state(assessment.get("result"))
    except ValueError as exc:
        errors.append(str(exc))
    counts = assessment.get("claim_counts")
    if not isinstance(counts, dict):
        errors.append("assessment claim_counts must be an object")
    else:
        for state in EVIDENCE_STATES:
            value = counts.get(state, 0)
            if not isinstance(value, int) or value < 0:
                errors.append(f"assessment invalid claim count: {state}")
    for key in ("missing", "conflicts"):
        if not isinstance(assessment.get(key), list):
            errors.append(f"assessment {key} must be a list")
    return errors


def validate_generalized_graph(payload: dict[str, Any]) -> list[str]:
    """Validate the complete generalized graph without repairing invalid data."""
    errors: list[str] = []
    required = ("schema", "schema_version", "brand", "entity", "claims", "edges", "assessment", "compatibility")
    for key in required:
        if key not in payload:
            errors.append(f"graph missing top-level key: {key}")
    if payload.get("schema") != GENERAL_SCHEMA:
        errors.append("generalized graph schema changed")
    if payload.get("schema_version") != GENERAL_SCHEMA_VERSION:
        errors.append("generalized graph schema_version unsupported")
    if payload.get("brand") != "Dead Signal":
        errors.append("brand changed")

    entity = payload.get("entity")
    if isinstance(entity, dict):
        errors.extend(validate_entity(entity))
    else:
        errors.append("graph entity must be an object")

    claims = payload.get("claims")
    if isinstance(claims, list):
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                errors.append(f"claim[{index}] must be an object")
                continue
            errors.extend(f"claim[{index}]: {message}" for message in validate_claim(claim))
    else:
        errors.append("graph claims must be a list")

    edges = payload.get("edges")
    if isinstance(edges, list):
        for index, edge in enumerate(edges):
            if not isinstance(edge, dict):
                errors.append(f"edge[{index}] must be an object")
                continue
            errors.extend(f"edge[{index}]: {message}" for message in validate_edge(edge))
    else:
        errors.append("graph edges must be a list")

    assessment = payload.get("assessment")
    if isinstance(assessment, dict):
        errors.extend(validate_assessment(assessment))
    else:
        errors.append("graph assessment must be an object")
    return errors


def _legacy_source_record(root: dict[str, Any], subject: dict[str, Any]) -> str:
    return str(root.get("canonical_id") or root.get("blueprint_id") or subject.get("identity") or root.get("id") or "")


def project_legacy_weapon_graph(legacy: dict[str, Any]) -> dict[str, Any]:
    """Project protected Weapons v1 into the Phase-1 generalized contract.

    The legacy payload is preserved verbatim under ``compatibility``. Exact
    occurrence edges use reference-tracer provenance. Legacy root-to-identity
    edges retain their original authority but explicitly name the published
    weapon snapshot as their migration provenance rather than pretending a raw
    installed-game owner was discovered during projection.
    """
    if legacy.get("schema") != "dead-signal-evidence-graph":
        raise ValueError("Only the protected Weapons v1 graph can be projected")
    subject = legacy.get("subject") or {}
    if subject.get("type") != "weapon":
        raise ValueError("Legacy projection requires a weapon subject")

    nodes = {str(row.get("id")): row for row in (legacy.get("nodes") or []) if isinstance(row, dict) and row.get("id")}
    root = next((row for row in nodes.values() if row.get("kind") == "weapon"), None)
    if root is None:
        raise ValueError("Legacy weapon graph has no weapon root")

    canonical_id = _legacy_source_record(root, subject)
    entity = {
        "schema_version": ENTITY_SCHEMA_VERSION,
        "entity_type": "weapon",
        "canonical_id": canonical_id,
        "name": str(root.get("label") or subject.get("name") or "Unknown Weapon"),
        "classification": str(root.get("category") or "weapon"),
        "identity_state": normalize_evidence_state(root.get("state") or "UNRESOLVED"),
        "source_records": [],
    }

    generalized_edges: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    for index, legacy_edge in enumerate(legacy.get("edges") or []):
        if not isinstance(legacy_edge, dict):
            raise ValueError(f"Legacy edge {index} is not an object")
        source_id = str(legacy_edge.get("from") or "")
        destination_id = str(legacy_edge.get("to") or "")
        if not source_id or not destination_id:
            raise ValueError(f"Legacy edge {index} is missing endpoints")
        if not legacy_edge.get("authoritative"):
            raise ValueError(f"Legacy edge {index} is not authoritative")

        destination = nodes.get(destination_id) or {}
        relationship = str(legacy_edge.get("kind") or "legacy-exact")
        if relationship == "exact-occurrence":
            source_table = str(destination.get("table") or "")
            source_record = str(destination.get("record_id") or "")
            selector = str(legacy_edge.get("json_pointer") or legacy_edge.get("field") or "")
            layer = str(destination.get("layer") or "")
            authority = "reference-tracer-exact-occurrence"
        else:
            source_table = "published/web/weapons.json"
            source_record = canonical_id
            selector = str(legacy_edge.get("field") or destination.get("kind") or relationship)
            layer = "published-snapshot"
            authority = "legacy-authoritative-weapon-identity"

        state = normalize_evidence_state(legacy_edge.get("state") or "UNRESOLVED")
        fingerprint = dependency_fingerprint(
            source_id,
            destination_id,
            relationship,
            source_table,
            source_record,
            selector,
            layer,
            authority,
        )
        edge = {
            "schema_version": EDGE_SCHEMA_VERSION,
            "source": source_id,
            "destination": destination_id,
            "relationship_type": relationship,
            "source_table": source_table,
            "source_record": source_record,
            "selector": selector,
            "layer": layer,
            "authority": authority,
            "state": state,
            "dependency_fingerprint": fingerprint,
        }
        edge_errors = validate_edge(edge)
        if edge_errors:
            raise ValueError(f"Legacy edge {index} cannot satisfy generalized provenance: {edge_errors}")
        generalized_edges.append(edge)

        evidence_id = f"edge:{fingerprint}"
        claim = {
            "schema_version": CLAIM_SCHEMA_VERSION,
            "claim_type": f"weapon.{relationship.replace('-', '_')}",
            "subject": {"entity_type": "weapon", "canonical_id": canonical_id},
            "result": state,
            "requirements": ["exact authoritative relationship", "complete edge provenance"],
            "evidence": [evidence_id] if state in {"PROVEN", "PARTIAL", "CONFLICT"} else [],
            "missing": ["relationship unresolved"] if state == "UNRESOLVED" else [],
            "conflicts": [evidence_id] if state == "CONFLICT" else [],
            "dependencies": [fingerprint],
        }
        claims.append(claim)

    counts = Counter(claim["result"] for claim in claims)
    if counts["CONFLICT"]:
        overall = "CONFLICT"
    elif counts["UNRESOLVED"] or counts["PARTIAL"]:
        overall = "PARTIAL" if counts["PROVEN"] else "UNRESOLVED"
    elif claims:
        overall = "PROVEN"
    else:
        overall = entity["identity_state"]

    assessment = {
        "schema_version": ASSESSMENT_SCHEMA_VERSION,
        "result": overall,
        "claim_counts": {state: counts.get(state, 0) for state in EVIDENCE_STATES},
        "missing": [item for claim in claims for item in claim.get("missing", [])],
        "conflicts": [item for claim in claims for item in claim.get("conflicts", [])],
    }
    payload = {
        "schema": GENERAL_SCHEMA,
        "schema_version": GENERAL_SCHEMA_VERSION,
        "brand": "Dead Signal",
        "entity": entity,
        "claims": claims,
        "edges": generalized_edges,
        "assessment": assessment,
        "compatibility": {
            "legacy_schema": legacy.get("schema"),
            "legacy_schema_version": legacy.get("schema_version"),
            "legacy_payload": legacy,
            "migration_policy": "Weapons v1 remains authoritative and unchanged; this projection adds strict versioned contracts without promoting new evidence.",
        },
    }
    errors = validate_generalized_graph(payload)
    if errors:
        raise ValueError(f"Generalized weapon graph failed validation: {errors}")
    return payload
