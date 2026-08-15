"""Dead Signal manual verification registry.

Verification is a deliberate human evidence step.  This registry stores compact
review metadata beneath the selected Miner output's research folder; it never
edits game-derived data or public website datasets.  The Publication Gate may
read these records, but only explicit user action can create or change them.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
ALLOWED_STATES = {"VERIFIED", "CONFLICT"}
ALLOWED_EVIDENCE = {
    "exact_identity",
    "independent_source",
    "exact_fixed_skill",
    "in_game_capture",
    "official_client_text",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_output(output: Path | str) -> Path:
    path = Path(output).expanduser().resolve()
    if not path.is_dir():
        raise ValueError("Select a completed Dead Signal Miner data folder")
    return path


def registry_path(output: Path | str) -> Path:
    root = _safe_output(output)
    return root / "research" / "verifications.json"


def load_verifications(output: Path | str) -> dict[str, Any]:
    path = registry_path(output)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        payload = {}
    records = payload.get("verifications") if isinstance(payload, dict) else None
    if not isinstance(records, dict):
        records = {}
    return {
        "schema": "dead-signal-verification-registry",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "updated_utc": payload.get("updated_utc") if isinstance(payload, dict) else None,
        "verifications": records,
        "policy": "Only explicit user action creates verification records; no analyzer or workflow can write this registry.",
    }


def save_verification(output: Path | str, key: object, *, state: str, evidence: list[str],
                      note: str, source_ref: str = "") -> dict[str, Any]:
    root = _safe_output(output)
    record_key = str(key or "").strip()
    if not record_key:
        raise ValueError("Verification requires a candidate key")
    state = str(state or "").strip().upper()
    if state not in ALLOWED_STATES:
        raise ValueError(f"Verification state must be one of {sorted(ALLOWED_STATES)}")
    normalized_evidence = sorted({str(value).strip() for value in evidence if str(value).strip()})
    unknown = set(normalized_evidence) - ALLOWED_EVIDENCE
    if unknown:
        raise ValueError(f"Unknown verification evidence types: {sorted(unknown)}")
    clean_note = str(note or "").strip()
    if len(clean_note) < 8:
        raise ValueError("Verification requires a short evidence note (at least 8 characters)")
    clean_source = str(source_ref or "").strip()

    payload = load_verifications(root)
    now = _utc_now()
    record = {
        "state": state,
        "evidence": normalized_evidence,
        "note": clean_note,
        "source_ref": clean_source,
        "verified_utc": now,
        "manual": True,
    }
    payload["verifications"][record_key] = record
    payload["updated_utc"] = now
    path = registry_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return {"key": record_key, **record}


def delete_verification(output: Path | str, key: object) -> bool:
    root = _safe_output(output)
    record_key = str(key or "").strip()
    payload = load_verifications(root)
    if record_key not in payload["verifications"]:
        return False
    del payload["verifications"][record_key]
    payload["updated_utc"] = _utc_now()
    path = registry_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return True
