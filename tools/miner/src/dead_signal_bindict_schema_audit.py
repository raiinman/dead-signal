"""Read-only schema audit for Once Human weapon_prototype_data bindict payloads.

This diagnostic exists to explain a narrow evidence mismatch: the player UI asks
BluePrintHelper for ``prototype_desc`` from ``weapon_prototype_data``, the raw
PYC contains that token, but the normal JSON projection does not expose the
field.  The audit instruments the existing NeoX bindict parser without changing
its production behavior or executing game bytecode.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from core.bindict.parser import BindictParser

ActivityCallback = Callable[[str], None]
TARGET_BASENAME = "weapon_prototype_data.pyc"
TARGET_FIELDS = ("prototype_desc", "prototype_name")


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


def _source_roots(base: Path, current: Path) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for layer, snapshot in (("current", current / "snapshot.json"), ("base", base / "snapshot.json")):
        payload = _read_json(snapshot, {}) or {}
        raw = payload.get("source_root") if isinstance(payload, dict) else None
        if not raw:
            continue
        root = Path(str(raw)).expanduser()
        if not root.exists():
            continue
        root = root.resolve()
        key = str(root).casefold()
        if key in seen:
            continue
        seen.add(key)
        roots.append((layer, root))
    return roots


def _find_target(base: Path, current: Path) -> dict[str, Any] | None:
    for layer, root in _source_roots(base, current):
        for path in root.rglob("*.pyc"):
            if path.name.casefold() == TARGET_BASENAME:
                return {
                    "layer": layer,
                    "root": root,
                    "path": path,
                    "relative_path": path.relative_to(root).as_posix(),
                }
    return None


def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            yield from _walk(child)


def _record_field_counts(parsed: Any) -> Counter:
    counts: Counter = Counter()
    data = parsed.get("data") if isinstance(parsed, dict) else None
    if not isinstance(data, dict):
        return counts
    for record in data.values():
        if not isinstance(record, dict):
            continue
        for key in record:
            counts[str(key)] += 1
    return counts


class AuditedBindictParser(BindictParser):
    """Existing parser plus passive key-definition/string-pool telemetry."""

    def __init__(self):
        super().__init__(debug=False)
        self.key_def_events: list[dict[str, Any]] = []
        self.dictionary_events: list[dict[str, Any]] = []

    def _parse_key_defs(self, data: bytes, offset: int):  # type: ignore[override]
        key_defs, key_count, bitmap_bit_size = super()._parse_key_defs(data, offset)
        defs = key_defs or []
        names = [str(row.get("name")) for row in defs if isinstance(row, dict)]
        target_defs = [
            {
                "index": row.get("index"),
                "name": row.get("name"),
                "type": row.get("type"),
            }
            for row in defs
            if isinstance(row, dict) and str(row.get("name")) in TARGET_FIELDS
        ]
        self.key_def_events.append({
            "offset": offset,
            "key_count": key_count,
            "bitmap_bit_size": bitmap_bit_size,
            "target_definitions": target_defs,
            "field_names": names if target_defs else [],
        })
        return key_defs, key_count, bitmap_bit_size

    def _parse_dictionary_data(self, dict_data: bytes):  # type: ignore[override]
        before = len(self.key_def_events)
        result = super()._parse_dictionary_data(dict_data)
        strings = list(map(str, self.strings))
        string_hits = {
            field: [index for index, value in enumerate(strings) if value == field]
            for field in TARGET_FIELDS
        }
        events = self.key_def_events[before:]
        target_events = [event for event in events if event.get("target_definitions")]
        self.dictionary_events.append({
            "payload_bytes": len(dict_data),
            "string_pool_size": len(strings),
            "string_pool_target_indices": string_hits,
            "key_definition_sets_seen": len(events),
            "target_key_definition_sets": target_events,
            "parsed_top_level_records": len(result) if isinstance(result, dict) else 0,
        })
        return result


def run_weapon_prototype_bindict_audit(
    base: Path,
    current: Path,
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    target = _find_target(base, current)
    report: dict[str, Any] = {
        "schema": "dead-signal-weapon-prototype-bindict-schema-audit",
        "schema_version": 1,
        "mode": "offline-read-only-bindict-parser-audit",
        "target": None,
        "record_counts": {},
        "dictionary_events": [],
        "field_presence": {},
        "raw_token_offsets": {},
        "unknown_value_samples": [],
        "interpretation": {},
        "safety": {
            "bytecode_execution": "None. The PYC is read as bytes and passed to the existing bindict parser only.",
            "game_process": "No process handle, memory read, debugger, hook, or injection is used.",
            "filesystem": "Read-only access to the already-extracted snapshot source_root; only the audit JSON is written.",
        },
    }
    if target is None:
        report["interpretation"] = {
            "status": "target-pyc-missing",
            "next_step": "A fresh Complete Database harvest is required before auditing the raw bindict payload.",
        }
        _write_json(reports_dir / "weapon-prototype-bindict-schema-audit.json", report)
        return report

    path: Path = target["path"]
    activity(f"Bindict Schema Audit: reading {target['relative_path']}")
    raw = path.read_bytes()
    parser = AuditedBindictParser()
    parsed = parser.extract_from_pyc(raw)
    field_counts = _record_field_counts(parsed)

    raw_offsets: dict[str, list[int]] = {}
    for field in TARGET_FIELDS:
        token = field.encode("utf-8")
        offsets: list[int] = []
        start = 0
        while len(offsets) < 32:
            found = raw.find(token, start)
            if found < 0:
                break
            offsets.append(found)
            start = found + 1
        raw_offsets[field] = offsets

    unknown_samples: list[str] = []
    if parsed is not None:
        for value in _walk(parsed):
            if isinstance(value, str) and (value.startswith("<unknown_") or value.startswith("<string_ref:")):
                if value not in unknown_samples:
                    unknown_samples.append(value)
                if len(unknown_samples) >= 80:
                    break

    target_key_defs = []
    for event in parser.key_def_events:
        if event.get("target_definitions"):
            target_key_defs.append(event)

    report.update({
        "target": {
            "layer": target["layer"],
            "relative_path": target["relative_path"],
            "bytes": len(raw),
        },
        "record_counts": {
            "parsed_dictionary_names": len(parsed) if isinstance(parsed, dict) else 0,
            "parsed_data_records": len((parsed or {}).get("data", {})) if isinstance((parsed or {}).get("data"), dict) else 0,
            "key_definition_sets_seen": len(parser.key_def_events),
            "target_key_definition_sets": len(target_key_defs),
            "unknown_value_samples": len(unknown_samples),
        },
        "dictionary_events": parser.dictionary_events,
        "target_key_definition_sets": target_key_defs,
        "field_presence": {
            field: {
                "parsed_record_count": int(field_counts.get(field, 0)),
                "raw_token_occurrences": len(raw_offsets.get(field) or []),
                "appears_in_key_definitions": any(
                    any(str(row.get("name")) == field for row in event.get("target_definitions") or [])
                    for event in target_key_defs
                ),
            }
            for field in TARGET_FIELDS
        },
        "raw_token_offsets": raw_offsets,
        "unknown_value_samples": unknown_samples,
    })

    desc = report["field_presence"]["prototype_desc"]
    if desc["parsed_record_count"]:
        status = "parser-exposes-prototype-desc"
        next_step = "Project exact prototype_desc values through the weapon prototype join and verify localization/identity before publication."
    elif desc["appears_in_key_definitions"]:
        status = "prototype-desc-defined-but-dropped-during-record-decode"
        next_step = "Inspect the matching bitmap/mapnode decode path; do not alter publication until exact record/value alignment is proven."
    elif desc["raw_token_occurrences"]:
        status = "prototype-desc-in-raw-payload-but-not-key-definitions"
        next_step = "Trace the raw string-pool/key-definition encoding before changing the parser."
    else:
        status = "prototype-desc-not-found-in-target-pyc"
        next_step = "Re-check target layer/version and runtime table source."
    report["interpretation"] = {"status": status, "next_step": next_step}

    output = reports_dir / "weapon-prototype-bindict-schema-audit.json"
    _write_json(output, report)
    activity(f"Bindict Schema Audit complete: {status}")
    return report
