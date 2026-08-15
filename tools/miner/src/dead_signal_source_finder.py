"""Dead Signal Source Finder for unresolved player-facing Weapon descriptions.

This module consumes the research-only output from
``investigate_weapon_description_sources`` and turns it into a compact, branded
review queue.  It never upgrades a candidate to VERIFIED on its own.  Exact game
identity is necessary for candidacy, while uniqueness, translation agreement,
and non-template copy are quality signals only.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


SCHEMA_VERSION = 1

STATE_EXTRACTED = "EXTRACTED"
STATE_RESOLVED = "RESOLVED"
STATE_CANDIDATE = "CANDIDATE"
STATE_VERIFIED = "VERIFIED"
STATE_CONFLICT = "CONFLICT"
STATE_UNRESOLVED = "UNRESOLVED"


def _candidate_text(candidate: dict[str, Any]) -> str:
    return str(
        candidate.get("resolved_text")
        or candidate.get("marker_stripped_value")
        or candidate.get("raw_value")
        or ""
    ).strip()


def classify_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    translation_count = int(candidate.get("translation_text_count") or 0)
    shared = bool(candidate.get("shared_across_weapons"))
    identity_hits = candidate.get("identity_hits") or []
    text = _candidate_text(candidate)

    blockers: list[str] = []
    if not identity_hits:
        blockers.append("no-exact-weapon-identity-hit")
    if not text:
        blockers.append("no-resolved-or-direct-text")
    if translation_count > 1:
        blockers.append("translation-source-conflict")
    if shared:
        blockers.append("shared-across-multiple-weapons")

    if "translation-source-conflict" in blockers or "shared-across-multiple-weapons" in blockers:
        state = STATE_CONFLICT
    elif blockers:
        state = STATE_UNRESOLVED
    elif candidate.get("translation_matches"):
        state = STATE_RESOLVED
    else:
        state = STATE_EXTRACTED

    # Exact co-occurrence plus non-shared, non-conflicting text earns review
    # candidacy, never automatic verification.
    if not blockers and identity_hits and text:
        state = STATE_CANDIDATE

    identity_fields = sorted({str(hit.get("field") or "") for hit in identity_hits if hit.get("field")})
    score = 0
    if identity_hits:
        score += 50
    if len(identity_fields) > 1:
        score += 10
    if candidate.get("translation_matches") and translation_count == 1:
        score += 15
    if not shared:
        score += 15
    if text:
        score += 10
    if blockers:
        score -= 100

    return {
        "state": state,
        "score": score,
        "blockers": blockers,
        "table": candidate.get("table"),
        "source": candidate.get("source"),
        "record_id": candidate.get("record_id"),
        "field": candidate.get("field"),
        "json_pointer": candidate.get("json_pointer"),
        "text": text,
        "raw_value": candidate.get("raw_value"),
        "identity_hits": identity_hits,
        "identity_fields": identity_fields,
        "translation_matches": candidate.get("translation_matches") or [],
        "translation_text_count": translation_count,
        "shared_across_weapons": shared,
        "weapon_owner_count": int(candidate.get("weapon_owner_count") or 0),
        "publication_status": "BLOCKED-PENDING-VERIFICATION",
    }


def build_source_finder_report(investigation: dict[str, Any]) -> dict[str, Any]:
    weapons = []
    states: Counter[str] = Counter()
    for row in investigation.get("weapons") or []:
        if not isinstance(row, dict):
            continue
        candidates = [
            classify_candidate(candidate)
            for candidate in (row.get("candidates") or [])
            if isinstance(candidate, dict)
        ]
        candidates.sort(
            key=lambda candidate: (
                -int(candidate["score"]),
                str(candidate.get("table") or ""),
                str(candidate.get("record_id") or ""),
                str(candidate.get("field") or ""),
            )
        )
        candidate_states = Counter(candidate["state"] for candidate in candidates)
        if candidate_states.get(STATE_CANDIDATE):
            overall = STATE_CANDIDATE
        elif candidate_states.get(STATE_CONFLICT):
            overall = STATE_CONFLICT
        elif candidates:
            overall = STATE_UNRESOLVED
        else:
            overall = STATE_UNRESOLVED
        states[overall] += 1
        weapons.append({
            "blueprint_id": row.get("blueprint_id"),
            "item_id": row.get("item_id"),
            "name": row.get("name"),
            "category": row.get("category"),
            "state": overall,
            "candidate_count": len(candidates),
            "reviewable_candidate_count": candidate_states.get(STATE_CANDIDATE, 0),
            "conflict_candidate_count": candidate_states.get(STATE_CONFLICT, 0),
            "candidates": candidates,
            "publication_status": "BLOCKED-PENDING-VERIFICATION",
        })

    weapons.sort(key=lambda row: (row["state"] != STATE_CANDIDATE, str(row.get("category") or ""), str(row.get("name") or "")))
    return {
        "schema": "dead-signal-source-finder",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "product": "Dead Signal Source Finder",
        "subject": "Weapon Description",
        "record_counts": {
            "weapons": len(weapons),
            "states": dict(sorted(states.items())),
            "reviewable_candidates": sum(row["reviewable_candidate_count"] for row in weapons),
            "conflict_candidates": sum(row["conflict_candidate_count"] for row in weapons),
        },
        "evidence_states": {
            STATE_EXTRACTED: "A raw value exists in installed-game data.",
            STATE_RESOLVED: "A reference or translation target resolves, but ownership is not proven.",
            STATE_CANDIDATE: "Exact weapon identity and non-conflicting copy make this worth manual evidence review.",
            STATE_VERIFIED: "Reserved for an independent verification/promotion step; Source Finder never assigns it.",
            STATE_CONFLICT: "The candidate is shared, contradictory, or otherwise unsafe.",
            STATE_UNRESOLVED: "No candidate currently satisfies the review threshold.",
        },
        "policy": {
            "identity": "Only exact installed-game identities inherited from the source investigation are eligible.",
            "discovery": "Ranking is a research convenience and is never evidence by itself.",
            "verification": "Source Finder cannot assign VERIFIED.",
            "publication": "All results remain blocked until a separate exact verification gate approves them.",
        },
        "weapons": weapons,
    }
