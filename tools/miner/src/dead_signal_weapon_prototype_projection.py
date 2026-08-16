"""Exact Weapon Description projection from the raw NeoX weapon prototype bindict.

The player client reads ``prototype_desc`` from ``weapon_prototype_data``.  The
normal JSON table projection historically omitted that nested field even though
the canonical bindict parser exposes it.  This research-only stage therefore
reads the already-extracted ``weapon_prototype_data.pyc`` bytes through the same
BindictParser, joins by exact published ``prototype_id``, and resolves English
translation handles.  It never executes game bytecode and never publishes or
marks descriptions VERIFIED.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from dead_signal_weapon_description_consumer import _resolve_text, _translation_sources
from neoxtractor.core.bindict.parser import BindictParser

SCHEMA_VERSION = 1
PROTOTYPE_PYC = "game_common/data/weapon_prototype_data.pyc"
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


def _source_root(snapshot: Path) -> Path | None:
    metadata = _read_json(snapshot / "snapshot.json", {}) or {}
    value = str(metadata.get("source_root") or "").strip() if isinstance(metadata, dict) else ""
    if not value:
        return None
    root = Path(value).expanduser()
    return root if root.is_absolute() else (snapshot / root).resolve()


def _normalize_table(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[str(key)] = value
    return result


def _parse_layer(snapshot: Path, layer: str) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    root = _source_root(snapshot)
    source = root / PROTOTYPE_PYC if root is not None else None
    metadata: dict[str, Any] = {
        "layer": layer,
        "relative_path": PROTOTYPE_PYC,
        "source_root_present": root is not None,
        "source_present": bool(source and source.is_file()),
        "records": 0,
        "parser": "neoxtractor.core.bindict.parser.BindictParser",
    }
    if source is None or not source.is_file():
        return {}, metadata
    raw = source.read_bytes()
    parsed = BindictParser(debug=False).extract_from_pyc(raw)
    table = _normalize_table(parsed)
    metadata["bytes"] = len(raw)
    metadata["records"] = len(table)
    metadata["prototype_desc_records"] = sum(
        1 for record in table.values() if record.get("prototype_desc") not in (None, "", 0, "0")
    )
    metadata["prototype_name_records"] = sum(
        1 for record in table.values() if record.get("prototype_name") not in (None, "", 0, "0")
    )
    return table, metadata


def run_weapon_prototype_projection(
    base: Path,
    current: Path,
    weapons_path: Path,
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    payload = _read_json(weapons_path, {}) or {}
    weapons = payload.get("weapons") if isinstance(payload, dict) else None
    if not isinstance(weapons, list):
        raise ValueError("Weapon dataset must contain a weapons list")

    base_table, base_meta = _parse_layer(base, "base")
    current_table, current_meta = _parse_layer(current, "current")
    if not base_table and not current_table:
        raise ValueError(f"Raw weapon prototype bindict is unavailable in both snapshot layers: {PROTOTYPE_PYC}")

    activity(
        "Prototype Projection: canonical bindict parser exposed "
        f"base {len(base_table)} records, current patch {len(current_table)} records"
    )
    translations = _translation_sources(base, current)
    activity(f"Prototype Projection: loaded {len(translations)} English translation sources")

    rows: list[dict[str, Any]] = []
    statuses: Counter[str] = Counter()
    source_layers: Counter[str] = Counter()
    text_owners: dict[str, set[str]] = {}

    for index, weapon in enumerate(weapons, 1):
        if not isinstance(weapon, dict):
            continue
        prototype_id = str(weapon.get("prototype_id") or "").strip()
        row: dict[str, Any] = {
            "blueprint_id": weapon.get("blueprint_id"),
            "item_id": weapon.get("item_id"),
            "prototype_id": prototype_id,
            "name": weapon.get("name"),
            "category": weapon.get("category"),
            "publication_status": "UNRESOLVED",
            "verified": False,
        }
        if not prototype_id or prototype_id == "0":
            row["status"] = "no-prototype-id"
        else:
            if prototype_id in current_table:
                record, layer = current_table[prototype_id], "current"
            else:
                record, layer = base_table.get(prototype_id), "base"
            row["source"] = {
                "layer": layer,
                "relative_path": PROTOTYPE_PYC,
                "record_id": prototype_id,
                "field": "prototype_desc",
                "parser": "BindictParser",
            }
            if not isinstance(record, dict):
                row["status"] = "prototype-record-missing"
            else:
                source_layers[layer] += 1
                raw_value = record.get("prototype_desc")
                row["prototype_name_raw"] = record.get("prototype_name")
                row["weapon_type_raw"] = record.get("weapon_type")
                if raw_value in (None, "", 0, "0"):
                    row["status"] = "prototype-desc-missing"
                else:
                    resolution = _resolve_text(raw_value, translations)
                    row.update(resolution)
                    if resolution.get("text") and resolution.get("status") in {
                        "prototype-desc-resolved-consistently",
                        "prototype-desc-direct-text",
                    }:
                        row["publication_status"] = "CANDIDATE-PENDING-UI-CONFIRMATION"
                        text_owners.setdefault(str(resolution["text"]), set()).add(prototype_id)
        statuses[str(row.get("status") or "unresolved")] += 1
        rows.append(row)
        if index % 25 == 0 or index == len(weapons):
            activity(f"Prototype Projection: processed {index}/{len(weapons)} weapons")

    shared_texts = {text: sorted(ids) for text, ids in text_owners.items() if len(ids) > 1}
    for row in rows:
        text = str(row.get("text") or "")
        if text and text in shared_texts:
            row["shared_across_prototypes"] = True
            row["shared_prototype_ids"] = shared_texts[text]
            row["publication_status"] = "BLOCKED-SHARED-PROTOTYPE-DESCRIPTION"
        else:
            row["shared_across_prototypes"] = False

    counts = {
        "weapons": len(rows),
        "prototype_records_found": sum(
            row.get("status") not in {"no-prototype-id", "prototype-record-missing"} for row in rows
        ),
        "prototype_desc_fields_found": sum(
            row.get("status") not in {"no-prototype-id", "prototype-record-missing", "prototype-desc-missing"}
            for row in rows
        ),
        "consistent_resolutions": sum(row.get("status") == "prototype-desc-resolved-consistently" for row in rows),
        "direct_text_resolutions": sum(row.get("status") == "prototype-desc-direct-text" for row in rows),
        "translation_conflicts": sum(row.get("status") == "prototype-desc-translation-conflict" for row in rows),
        "translation_unresolved": sum(row.get("status") == "prototype-desc-translation-unresolved" for row in rows),
        "shared_resolved_texts": len(shared_texts),
        "record_source_layers": dict(sorted(source_layers.items())),
        "statuses": dict(sorted(statuses.items())),
    }
    activity(
        f"Prototype Projection complete: {counts['prototype_desc_fields_found']} fields; "
        f"{counts['consistent_resolutions']} consistent translations; "
        f"{counts['translation_unresolved']} unresolved handles"
    )

    report = {
        "schema": "dead-signal-weapon-prototype-description-projection",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Weapon Description",
        "mode": "offline-read-only-raw-bindict-projection",
        "record_counts": counts,
        "source_layers": [base_meta, current_meta],
        "weapons": rows,
        "policy": {
            "identity": "Exact published Weapon prototype_id to exact raw weapon_prototype_data bindict record only.",
            "parser": "Uses the canonical Dead Signal NeoX BindictParser against already-extracted snapshot bytes; game bytecode is never executed.",
            "layers": "Current exact record overrides base exact record; absent current IDs fall back to base.",
            "translation": "English translation handles are resolved only by exact raw/marker-stripped key lookup.",
            "verification": "Resolved text remains CANDIDATE until player-facing UI confirmation or equivalent independent exact evidence.",
            "publication": "This stage writes only a research report and never modifies normalized/public website datasets.",
        },
        "safety": {
            "game_process": "No process handle, memory read, debugger, hook, injection, or anti-cheat interaction.",
            "bytecode_execution": "None. The raw PYC payload is parsed as bindict bytes only.",
            "filesystem": "Read-only snapshot input; report output only.",
        },
    }
    _write_json(reports_dir / "weapon-description-prototype-projection.json", report)
    return report
