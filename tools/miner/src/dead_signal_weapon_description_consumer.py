"""Exact UI-consumer-driven Weapon Description research.

This analyzer follows a client-consumer lead instead of exploring generic data
neighborhoods. Static PYC metadata shows the Weapon item-detail path exposing
``prototype_desc`` and the blueprint helper exposing ``weapon_prototype_data``.
The analyzer therefore resolves each weapon's exact ``prototype_id`` into the
installed NeoX ``weapon_prototype_data`` table and evaluates only the exact
``prototype_desc`` field.

The report is research-only. Even a clean translation becomes a consumer-backed
candidate, never VERIFIED and never player-facing publication, until independent
UI confirmation proves that this consumer field is the description block Dead
Signal intends to display.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable

from normalize_armor import MARKER, Translator, player_facing_effect, translation_entries

SCHEMA_VERSION = 1
PROTOTYPE_TABLE = "game_common/data/weapon_prototype_data.json"
PYC_REPORT = "weapon-progression-pyc-consumers.json"
CONSUMER_TOKENS = (
    "weapon_prototype_data",
    "get_weapon_prototype_data",
    "get_weapon_prototype_data_val_by_key",
    "prototype_desc",
    "get_item_desc_text",
    "get_weapon_item_data",
)
ActivityCallback = Callable[[str], None]


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _table(path: Path) -> dict[str, Any]:
    payload = _read_json(path, {})
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data", payload)
    return data if isinstance(data, dict) else {}


def _walk(value: Any, pointer: str = "") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            child_pointer = f"{pointer}/{escaped}"
            if isinstance(child, (dict, list)):
                yield from _walk(child, child_pointer)
            else:
                yield child_pointer, str(key), child
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_pointer = f"{pointer}/{index}"
            if isinstance(child, (dict, list)):
                yield from _walk(child, child_pointer)
            else:
                yield child_pointer, str(index), child


def _prototype_desc(record: dict[str, Any]) -> tuple[str | None, Any]:
    """Return only an exact normalized ``prototype_desc`` field."""
    for pointer, field, value in _walk(record):
        normalized = field.casefold().replace("-", "_").replace(" ", "_")
        if normalized == "prototype_desc":
            return pointer, value
    return None, None


def _translation_sources(base: Path, current: Path) -> list[tuple[str, dict[str, Any]]]:
    sources: list[tuple[str, dict[str, Any]]] = []
    base_file = base / "translate" / "translate_data_en.json"
    if base_file.is_file():
        sources.append(("base/translate/translate_data_en.json", translation_entries(base_file)))
    for path in sorted((current / "translate").glob("translate_data_en*.json")):
        try:
            relative = path.relative_to(current).as_posix()
        except ValueError:
            relative = path.name
        sources.append((f"current/{relative}", translation_entries(path)))
    return sources


def _resolve_text(raw_value: Any, sources: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    raw = Translator.raw(raw_value).strip()
    stripped = MARKER.sub("", raw).strip()
    matches: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for source_name, translations in sources:
        for key_kind, key in (("raw", raw), ("marker-stripped", stripped)):
            if not key:
                continue
            translated = translations.get(key)
            if isinstance(translated, str) and translated.strip():
                signature = (source_name, key, translated)
                if signature in seen:
                    continue
                seen.add(signature)
                matches.append({
                    "source": source_name,
                    "key_kind": key_kind,
                    "key": key,
                    "text": translated,
                })
    unique_texts = sorted({row["text"] for row in matches})
    direct_text = ""
    if raw and not matches and (" " in raw or len(raw.split()) > 1):
        direct_text = raw
    if len(unique_texts) == 1:
        status = "prototype-desc-resolved-consistently"
        text = player_facing_effect(unique_texts[0], [])
    elif len(unique_texts) > 1:
        status = "prototype-desc-translation-conflict"
        text = ""
    elif direct_text:
        status = "prototype-desc-direct-text"
        text = player_facing_effect(direct_text, [])
    else:
        status = "prototype-desc-translation-unresolved"
        text = ""
    return {
        "status": status,
        "raw_handle": raw,
        "marker_stripped_handle": stripped,
        "translation_matches": matches,
        "unique_translation_text_count": len(unique_texts),
        "text": text,
    }


def _scan_consumer_evidence(report_path: Path) -> dict[str, Any]:
    """Stream the static PYC report and stop once all target consumer tokens appear."""
    found: dict[str, list[dict[str, Any]]] = {token: [] for token in CONSUMER_TOKENS}
    if not report_path.is_file():
        return {
            "source": str(report_path),
            "report_present": False,
            "required_tokens": list(CONSUMER_TOKENS),
            "found_tokens": [],
            "all_required_tokens_found": False,
            "matches": found,
            "execution_policy": "Static report inspection only; game bytecode was not executed.",
        }

    unresolved = set(CONSUMER_TOKENS)
    with report_path.open("r", encoding="utf-8", errors="replace") as source:
        for line_number, line in enumerate(source, 1):
            for token in tuple(unresolved):
                if token in line:
                    found[token].append({"line": line_number, "excerpt": line.strip()[:1000]})
                    unresolved.discard(token)
            if not unresolved:
                break
    return {
        "source": str(report_path),
        "report_present": True,
        "required_tokens": list(CONSUMER_TOKENS),
        "found_tokens": sorted(token for token, rows in found.items() if rows),
        "all_required_tokens_found": not unresolved,
        "missing_tokens": sorted(unresolved),
        "matches": found,
        "execution_policy": "Static report inspection only; game bytecode was not executed.",
        "interpretation": (
            "These exact static tokens establish a client-consumer lead for prototype-backed Weapon detail data; "
            "they do not by themselves prove which visible UI text block uses prototype_desc."
        ),
    }


def run_weapon_description_consumer_trace(
    base: Path,
    current: Path,
    weapons_path: Path,
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    weapons_payload = _read_json(weapons_path, {}) or {}
    weapons = weapons_payload.get("weapons") if isinstance(weapons_payload, dict) else None
    if not isinstance(weapons, list):
        raise ValueError("Weapon dataset must contain a weapons list")

    current_table = current / PROTOTYPE_TABLE
    base_table = base / PROTOTYPE_TABLE
    if current_table.is_file():
        prototype_path = current_table
        prototype_layer = "current"
    elif base_table.is_file():
        prototype_path = base_table
        prototype_layer = "base"
    else:
        raise ValueError(f"Weapon prototype table is missing from both snapshot layers: {PROTOTYPE_TABLE}")

    activity(f"UI Consumer Trace: opening targeted table {PROTOTYPE_TABLE} ({prototype_layer})")
    prototypes = _table(prototype_path)
    translations = _translation_sources(base, current)
    activity(f"UI Consumer Trace: loaded {len(prototypes)} prototype records and {len(translations)} English translation sources")

    pyc_report = reports_dir / PYC_REPORT
    consumer_evidence = _scan_consumer_evidence(pyc_report)
    activity(
        "UI Consumer Trace: static consumer tokens "
        + ("complete" if consumer_evidence["all_required_tokens_found"] else "partial")
        + f" ({len(consumer_evidence['found_tokens'])}/{len(CONSUMER_TOKENS)})"
    )

    rows: list[dict[str, Any]] = []
    statuses: Counter[str] = Counter()
    candidate_text_owners: dict[str, list[str]] = {}

    for index, weapon in enumerate(weapons, start=1):
        if not isinstance(weapon, dict):
            continue
        prototype_id = str(weapon.get("prototype_id") or "").strip()
        name = str(weapon.get("name") or "")
        row: dict[str, Any] = {
            "blueprint_id": weapon.get("blueprint_id"),
            "item_id": weapon.get("item_id"),
            "prototype_id": prototype_id,
            "name": name,
            "category": weapon.get("category"),
            "source": {
                "layer": prototype_layer,
                "table": PROTOTYPE_TABLE,
                "record_id": prototype_id,
                "field": "prototype_desc",
            },
            "consumer_backed_candidate": False,
            "publication_status": "BLOCKED-PENDING-UI-CONFIRMATION",
        }
        if not prototype_id or prototype_id == "0":
            row["status"] = "no-prototype-id"
        else:
            prototype = prototypes.get(prototype_id)
            if not isinstance(prototype, dict):
                row["status"] = "prototype-record-missing"
            else:
                pointer, raw_value = _prototype_desc(prototype)
                row["source"]["json_pointer"] = pointer
                if pointer is None or raw_value in (None, "", 0, "0"):
                    row["status"] = "prototype-desc-missing"
                else:
                    resolution = _resolve_text(raw_value, translations)
                    row.update(resolution)
                    if resolution["status"] in {
                        "prototype-desc-resolved-consistently",
                        "prototype-desc-direct-text",
                    } and resolution.get("text"):
                        row["consumer_backed_candidate"] = bool(consumer_evidence["all_required_tokens_found"])
                        candidate_text_owners.setdefault(str(resolution["text"]), []).append(prototype_id)
        statuses[str(row.get("status") or "unresolved")] += 1
        rows.append(row)
        if index % 25 == 0 or index == len(weapons):
            activity(f"UI Consumer Trace: resolved {index}/{len(weapons)} weapons")

    # A prototype description shared by multiple distinct prototype IDs is not safe
    # to treat as unique Weapon copy. Preserve it as evidence but block candidacy.
    shared_texts = {text: owners for text, owners in candidate_text_owners.items() if len(set(owners)) > 1}
    for row in rows:
        text = str(row.get("text") or "")
        if text and text in shared_texts:
            row["shared_across_prototypes"] = True
            row["shared_prototype_ids"] = sorted(set(shared_texts[text]))
            row["consumer_backed_candidate"] = False
            row["publication_status"] = "BLOCKED-SHARED-PROTOTYPE-DESCRIPTION"
        else:
            row["shared_across_prototypes"] = False

    record_counts = {
        "weapons": len(rows),
        "prototype_records_found": sum(row.get("status") not in {"no-prototype-id", "prototype-record-missing"} for row in rows),
        "prototype_desc_fields_found": sum(row.get("status") not in {"no-prototype-id", "prototype-record-missing", "prototype-desc-missing"} for row in rows),
        "consistent_resolutions": sum(row.get("status") == "prototype-desc-resolved-consistently" for row in rows),
        "direct_text_resolutions": sum(row.get("status") == "prototype-desc-direct-text" for row in rows),
        "translation_conflicts": sum(row.get("status") == "prototype-desc-translation-conflict" for row in rows),
        "consumer_backed_candidates": sum(bool(row.get("consumer_backed_candidate")) for row in rows),
        "shared_candidate_texts": len(shared_texts),
        "statuses": dict(sorted(statuses.items())),
    }
    activity(
        "UI Consumer Trace complete: "
        f"{record_counts['prototype_desc_fields_found']} prototype_desc fields; "
        f"{record_counts['consistent_resolutions']} consistent translations; "
        f"{record_counts['consumer_backed_candidates']} consumer-backed candidates"
    )

    report = {
        "schema": "dead-signal-weapon-description-ui-consumer-trace",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Weapon Description",
        "hypothesis": (
            "The client Weapon item-detail path reads weapon_prototype_data and exposes prototype_desc; "
            "therefore exact prototype_id -> prototype_desc is the next bounded description-source candidate."
        ),
        "record_counts": record_counts,
        "consumer_evidence": consumer_evidence,
        "source_table": {
            "layer": prototype_layer,
            "relative_path": PROTOTYPE_TABLE,
            "records": len(prototypes),
        },
        "weapons": rows,
        "policy": {
            "identity": "Exact published Weapon prototype_id to exact weapon_prototype_data record only; no names, fuzzy joins, or family substitution.",
            "consumer": "Static PYC metadata is inspected only as a bounded client-consumer lead; bytecode is never executed.",
            "candidate": "A unique, consistently translated prototype_desc with complete consumer tokens is consumer-backed research evidence only.",
            "verification": "UI confirmation remains required before any candidate may be manually VERIFIED.",
            "publication": "This analyzer never rewrites normalized or player-facing data.",
        },
    }
    report_path = reports_dir / "weapon-description-ui-consumer-trace.json"
    _write_json(report_path, report)
    return report
