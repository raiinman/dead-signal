"""Phase 12 evidence assessment and human review support.

This module never assigns deterministic proof.  It turns generalized claims into
requirement-by-requirement assessments, builds a deterministic review queue,
stores attributable/removable human review overlays, and exports bounded evidence
bundles for forensic work.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
REVIEW_STATES = {"VERIFIED", "CONFLICT"}
MAX_BUNDLE_CLAIMS = 50
MAX_BUNDLE_EVIDENCE = 100
MAX_TEXT = 4000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def claim_key(graph: dict[str, Any], claim: dict[str, Any]) -> str:
    entity = graph.get("entity") or {}
    return f"{entity.get('entity_type')}:{entity.get('canonical_id')}:{claim.get('claim_type')}"


def _norm(value: object) -> str:
    return " ".join(str(value or "").casefold().replace("_", " ").replace("-", " ").split())


def _overlaps(requirement: str, reason: str) -> bool:
    req = set(_norm(requirement).split())
    why = set(_norm(reason).split())
    return bool(req and why and (req <= why or why <= req or len(req & why) >= min(2, len(req), len(why))))


def assess_claim(graph: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
    """Produce an actionable, deterministic assessment without changing truth."""
    result = str(claim.get("result") or "UNRESOLVED").upper()
    missing = [str(v) for v in claim.get("missing", []) if str(v or "").strip()]
    conflicts = [v for v in claim.get("conflicts", []) if v not in (None, "", [], {})]
    requirements = [str(v) for v in claim.get("requirements", []) if str(v or "").strip()]
    evidence = list(claim.get("evidence", []) or [])
    rows: list[dict[str, Any]] = []
    for requirement in requirements:
        matched_missing = [reason for reason in missing if _overlaps(requirement, reason)]
        if result == "CONFLICT":
            state = "CONFLICT"
            reason = "conflicting evidence must be resolved"
        elif matched_missing:
            state = "MISSING"
            reason = matched_missing[0]
        elif result in {"PROVEN", "NOT APPLICABLE"}:
            state = "SATISFIED"
            reason = "deterministic claim assessment satisfied this requirement"
        elif evidence:
            state = "PARTIAL"
            reason = missing[0] if missing else "evidence exists but this requirement is not independently closed"
        else:
            state = "UNRESOLVED"
            reason = missing[0] if missing else "required owner or consumer has not been resolved"
        rows.append({"requirement": requirement, "state": state, "reason": reason})

    actionable = list(missing)
    if conflicts:
        actionable.append("resolve conflicting evidence and identify the authoritative exact owner")
    if result in {"PARTIAL", "UNRESOLVED"} and not actionable:
        actionable.append("trace the exact owner or runtime consumer required by this claim")
    if not requirements and result in {"PARTIAL", "UNRESOLVED", "CONFLICT"}:
        actionable.append("claim contract must declare an explicit evidence requirement")

    entity = graph.get("entity") or {}
    return {
        "schema": "dead-signal-claim-assessment",
        "schema_version": SCHEMA_VERSION,
        "claim_key": claim_key(graph, claim),
        "entity_type": entity.get("entity_type"),
        "canonical_id": entity.get("canonical_id"),
        "claim_type": claim.get("claim_type"),
        "result": result,
        "requirements": rows,
        "actionable_reasons": sorted(dict.fromkeys(actionable)),
        "dependencies": sorted({str(v) for v in claim.get("dependencies", []) if str(v or "").strip()}),
        "publication_authority": False,
    }


def _impact_score(result: str, invalidated: bool, missing_count: int, conflict_count: int) -> int:
    base = {"CONFLICT": 100, "UNRESOLVED": 75, "PARTIAL": 65, "PROVEN": 0, "NOT APPLICABLE": 0}.get(result, 50)
    return base + (25 if invalidated else 0) + min(20, missing_count * 3) + min(20, conflict_count * 5)


def navigation_targets(graph: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
    entity = graph.get("entity") or {}
    exact_records = []
    for row in entity.get("source_records", []) or []:
        if isinstance(row, dict) and row.get("table") and row.get("record_id") not in (None, ""):
            exact_records.append({
                "table": str(row.get("table")),
                "record_id": str(row.get("record_id")),
                "layer": row.get("layer"),
            })
    consumer_leads = [{"dependency": str(dep), "action": "open-consumer-search"} for dep in claim.get("dependencies", []) if str(dep or "").strip()]
    return {"exact_records": exact_records, "consumer_leads": consumer_leads}


def build_review_queue(graphs: Iterable[dict[str, Any]], *, invalidation_report: dict[str, Any] | None = None,
                       domain: str | None = None) -> dict[str, Any]:
    invalidated = set((invalidation_report or {}).get("review_queue") or [])
    items = []
    missing_groups: dict[str, list[str]] = {}
    for graph in graphs:
        if not isinstance(graph, dict):
            continue
        entity = graph.get("entity") or {}
        if domain and str(entity.get("entity_type")) != str(domain):
            continue
        for claim in graph.get("claims", []) or []:
            if not isinstance(claim, dict):
                continue
            assessment = assess_claim(graph, claim)
            key = assessment["claim_key"]
            result = assessment["result"]
            if result not in {"PARTIAL", "UNRESOLVED", "CONFLICT"} and key not in invalidated:
                continue
            missing = assessment["actionable_reasons"]
            for reason in missing:
                missing_groups.setdefault(reason, []).append(key)
            item = {
                "claim_key": key,
                "entity_type": assessment["entity_type"],
                "canonical_id": assessment["canonical_id"],
                "claim_type": assessment["claim_type"],
                "result": result,
                "invalidated": key in invalidated,
                "launch_impact": _impact_score(result, key in invalidated, len(claim.get("missing", []) or []), len(claim.get("conflicts", []) or [])),
                "assessment": assessment,
                "navigation": navigation_targets(graph, claim),
            }
            items.append(item)
    items.sort(key=lambda row: (-row["launch_impact"], str(row["entity_type"]), str(row["canonical_id"]), str(row["claim_type"])))
    groups = [{"missing_owner_or_reason": reason, "claim_keys": sorted(keys), "count": len(keys)} for reason, keys in missing_groups.items()]
    groups.sort(key=lambda row: (-row["count"], row["missing_owner_or_reason"]))
    return {
        "schema": "dead-signal-evidence-review-queue",
        "schema_version": SCHEMA_VERSION,
        "filters": {"domain": domain},
        "items": items,
        "shared_missing_groups": groups,
        "policy": "Queue ordering is deterministic. Human review overlays cannot assign deterministic PROVEN or publish automatically.",
    }


class ManualReviewStore:
    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        self.path = self.output / "research" / "claim-reviews.json"

    def load(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = {}
        reviews = payload.get("reviews") if isinstance(payload, dict) else None
        return {
            "schema": "dead-signal-claim-review-registry",
            "schema_version": SCHEMA_VERSION,
            "updated_at": payload.get("updated_at") if isinstance(payload, dict) else None,
            "reviews": reviews if isinstance(reviews, dict) else {},
            "publication_authority": False,
        }

    def record(self, key: object, *, state: str, reviewer: str, note: str, source_ref: str = "") -> dict[str, Any]:
        claim = str(key or "").strip()
        state = str(state or "").strip().upper()
        reviewer = str(reviewer or "").strip()
        note = str(note or "").strip()
        if not claim:
            raise ValueError("Manual review requires a claim key")
        if state not in REVIEW_STATES:
            raise ValueError(f"Manual review state must be one of {sorted(REVIEW_STATES)}")
        if not reviewer:
            raise ValueError("Manual review requires an attributable reviewer")
        if len(note) < 8:
            raise ValueError("Manual review requires an evidence note of at least 8 characters")
        payload = self.load()
        now = _now()
        row = {
            "state": state,
            "reviewer": reviewer,
            "note": note[:MAX_TEXT],
            "source_ref": str(source_ref or "").strip()[:MAX_TEXT],
            "reviewed_at": now,
            "manual": True,
            "deterministic_proof_override": False,
            "publication_authority": False,
        }
        payload["reviews"][claim] = row
        payload["updated_at"] = now
        _atomic(self.path, payload)
        return {"claim_key": claim, **row}

    def remove(self, key: object) -> bool:
        claim = str(key or "").strip()
        payload = self.load()
        if claim not in payload["reviews"]:
            return False
        del payload["reviews"][claim]
        payload["updated_at"] = _now()
        _atomic(self.path, payload)
        return True


def export_evidence_bundle(graphs: Iterable[dict[str, Any]], claim_keys: Iterable[str], destination: Path | str) -> dict[str, Any]:
    wanted = set(str(v) for v in claim_keys)
    rows = []
    for graph in graphs:
        for claim in graph.get("claims", []) or []:
            if not isinstance(claim, dict):
                continue
            key = claim_key(graph, claim)
            if key not in wanted:
                continue
            bounded_claim = dict(claim)
            bounded_claim["evidence"] = list(claim.get("evidence", []) or [])[:MAX_BUNDLE_EVIDENCE]
            rows.append({
                "claim_key": key,
                "entity": graph.get("entity"),
                "claim": bounded_claim,
                "assessment": assess_claim(graph, claim),
                "navigation": navigation_targets(graph, claim),
            })
            if len(rows) >= MAX_BUNDLE_CLAIMS:
                break
        if len(rows) >= MAX_BUNDLE_CLAIMS:
            break
    bundle = {
        "schema": "dead-signal-bounded-evidence-bundle",
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        "requested_claim_count": len(wanted),
        "exported_claim_count": len(rows),
        "bounded": len(rows) >= MAX_BUNDLE_CLAIMS,
        "claims": rows,
        "policy": "Research-only bounded export. It carries no publication authority and cannot assign deterministic proof.",
    }
    _atomic(Path(destination), bundle)
    return bundle
