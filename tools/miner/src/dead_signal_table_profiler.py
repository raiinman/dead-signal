"""Dead Signal NeoX Table Profiler.

Read-only structural profiling for extracted Once Human NeoX tables.  This is a
research aid, not a publisher: it measures field coverage, record shapes,
identity-bearing fields, description-like fields, and repeated scalar values so
Research Console can surface promising data paths without treating similarity as
proof.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
MAX_UNIQUE_TRACK = 50000
MAX_SHARED_VALUES = 100

IDENTITY_TOKENS = (
    "item_id", "blueprint_id", "prototype_id", "gun_no", "weapon_id",
    "skill_id", "fixed_skill_code", "buff_id", "recipe_id", "forge_id",
)
DESCRIPTION_TOKENS = (
    "description", "short_desc", "shortdesc", "desc_id", "descid", "tooltip",
    "copywriting", "display_text", "displaytext", "flavor", "lore",
)


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _records(path: Path) -> dict[str, Any]:
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


def _scalar(value: Any) -> str:
    if value is None or isinstance(value, (dict, list)):
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value).strip()
    return text if text else ""


def _normalized_field(field: str) -> str:
    return field.casefold().replace("-", "_").replace(" ", "_")


def _matches(field: str, tokens: tuple[str, ...]) -> bool:
    normalized = _normalized_field(field)
    return any(token in normalized for token in tokens)


def profile_table(path: Path, *, layer: str = "unknown", table: str | None = None) -> dict[str, Any]:
    rows = _records(path)
    total = len(rows)
    field_presence: Counter[str] = Counter()
    field_types: dict[str, Counter[str]] = defaultdict(Counter)
    field_values: dict[str, Counter[str]] = defaultdict(Counter)
    field_pointers: dict[str, Counter[str]] = defaultdict(Counter)
    record_shapes: Counter[tuple[str, ...]] = Counter()

    for record in rows.values():
        fields_for_record: set[str] = set()
        for pointer, field, raw in _walk(record):
            normalized = _normalized_field(field)
            fields_for_record.add(normalized)
            field_types[normalized][type(raw).__name__] += 1
            field_pointers[normalized][pointer] += 1
            value = _scalar(raw)
            if value and len(field_values[normalized]) < MAX_UNIQUE_TRACK:
                field_values[normalized][value] += 1
        for field in fields_for_record:
            field_presence[field] += 1
        record_shapes[tuple(sorted(fields_for_record))] += 1

    profiles = []
    for field in sorted(field_presence):
        present = field_presence[field]
        values = field_values[field]
        unique = len(values)
        repeated = sum(1 for count in values.values() if count > 1)
        profiles.append({
            "field": field,
            "present_records": present,
            "coverage": round((present / total) if total else 0.0, 6),
            "missing_records": max(0, total - present),
            "value_types": dict(sorted(field_types[field].items())),
            "unique_scalar_values": unique,
            "repeated_scalar_values": repeated,
            "identity_like": _matches(field, IDENTITY_TOKENS),
            "description_like": _matches(field, DESCRIPTION_TOKENS),
            "top_json_pointers": [
                {"json_pointer": pointer, "occurrences": count}
                for pointer, count in field_pointers[field].most_common(8)
            ],
        })

    shared_values = []
    for field, values in field_values.items():
        for value, count in values.most_common():
            if count <= 1:
                continue
            shared_values.append({
                "field": field,
                "value": value[:500],
                "occurrences": count,
                "description_like": _matches(field, DESCRIPTION_TOKENS),
                "identity_like": _matches(field, IDENTITY_TOKENS),
            })
    shared_values.sort(key=lambda row: (-int(row["description_like"]), -row["occurrences"], row["field"], row["value"]))

    shapes = [
        {
            "fields": list(shape),
            "field_count": len(shape),
            "records": count,
            "coverage": round((count / total) if total else 0.0, 6),
        }
        for shape, count in record_shapes.most_common()
    ]

    description_fields = [row for row in profiles if row["description_like"]]
    identity_fields = [row for row in profiles if row["identity_like"]]
    rare_fields = [row for row in profiles if total and row["coverage"] <= 0.05]

    return {
        "schema": "dead-signal-neox-table-profile",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "table": table or path.name,
        "layer": layer,
        "record_count": total,
        "field_count": len(profiles),
        "record_shape_count": len(shapes),
        "fields": profiles,
        "description_like_fields": description_fields,
        "identity_like_fields": identity_fields,
        "rare_fields": rare_fields,
        "record_shapes": shapes[:100],
        "shared_scalar_values": shared_values[:MAX_SHARED_VALUES],
        "warnings": {
            "description_like_shared_values": sum(1 for row in shared_values if row["description_like"]),
            "rare_field_count": len(rare_fields),
            "multiple_record_shapes": len(shapes) > 1,
        },
        "evidence_policy": {
            "authority": "Structural profiling is discovery-only.",
            "identity": "Field names, repetition, clustering, and similarity never establish identity.",
            "publication": "Profiler output cannot automatically promote a value into public Dead Signal data.",
        },
    }


def compare_profiles(base: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    base_fields = {row["field"]: row for row in base.get("fields") or []}
    current_fields = {row["field"]: row for row in current.get("fields") or []}
    names = sorted(set(base_fields) | set(current_fields))
    deltas = []
    for field in names:
        before = base_fields.get(field)
        after = current_fields.get(field)
        before_coverage = float((before or {}).get("coverage") or 0.0)
        after_coverage = float((after or {}).get("coverage") or 0.0)
        deltas.append({
            "field": field,
            "base_present": before is not None,
            "current_present": after is not None,
            "base_coverage": before_coverage,
            "current_coverage": after_coverage,
            "coverage_delta": round(after_coverage - before_coverage, 6),
            "description_like": bool((after or before or {}).get("description_like")),
            "identity_like": bool((after or before or {}).get("identity_like")),
        })
    return {
        "schema": "dead-signal-neox-table-profile-diff",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "table": current.get("table") or base.get("table"),
        "base_records": base.get("record_count", 0),
        "current_records": current.get("record_count", 0),
        "field_deltas": deltas,
        "new_fields": [row for row in deltas if not row["base_present"] and row["current_present"]],
        "removed_fields": [row for row in deltas if row["base_present"] and not row["current_present"]],
        "description_field_changes": [row for row in deltas if row["description_like"] and row["coverage_delta"] != 0],
        "policy": "Schema/coverage changes are research leads, not identity evidence.",
    }
