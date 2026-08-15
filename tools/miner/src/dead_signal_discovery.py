"""Dead Signal Discovery Engine.

Lightweight structural discovery over NeoX table profiles.  It intentionally uses
transparent deterministic measures instead of opaque identity prediction: Jaccard
schema similarity, field co-occurrence, shape rarity, and description/identity
hotspots.  Every output is a lead only.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict, deque
from itertools import combinations
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _profiles(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    rows = []
    for wrapper in payload.get("tables") or []:
        if not isinstance(wrapper, dict):
            continue
        profile = wrapper.get("active_profile") if isinstance(wrapper.get("active_profile"), dict) else wrapper
        rows.append((str(wrapper.get("table") or profile.get("table") or ""), profile))
    return rows


def _field_set(profile: dict[str, Any]) -> set[str]:
    return {str(row.get("field")) for row in profile.get("fields") or [] if isinstance(row, dict) and row.get("field")}


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return (len(left & right) / len(union)) if union else 0.0


def schema_clusters(payload: dict[str, Any], *, threshold: float = 0.65, max_tables: int = 600) -> dict[str, Any]:
    if threshold <= 0 or threshold > 1:
        raise ValueError("Schema similarity threshold must be in (0, 1]")
    rows = _profiles(payload)[:max_tables]
    fields = {table: _field_set(profile) for table, profile in rows}
    adjacency: dict[str, set[str]] = defaultdict(set)
    similarities = []
    for left, right in combinations(fields, 2):
        score = _jaccard(fields[left], fields[right])
        if score >= threshold:
            adjacency[left].add(right)
            adjacency[right].add(left)
            similarities.append({"left": left, "right": right, "similarity": round(score, 6)})
    seen = set()
    clusters = []
    for table in sorted(fields):
        if table in seen:
            continue
        queue = deque([table])
        component = []
        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            component.append(current)
            queue.extend(sorted(adjacency.get(current, set()) - seen))
        if len(component) > 1:
            shared = set.intersection(*(fields[name] for name in component)) if component else set()
            clusters.append({"tables": sorted(component), "size": len(component), "shared_fields": sorted(shared)})
    clusters.sort(key=lambda row: (-row["size"], row["tables"][0]))
    similarities.sort(key=lambda row: (-row["similarity"], row["left"], row["right"]))
    return {
        "schema": "dead-signal-schema-clusters",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "threshold": threshold,
        "record_counts": {"tables": len(fields), "clusters": len(clusters), "similar_pairs": len(similarities)},
        "clusters": clusters,
        "top_similar_pairs": similarities[:500],
        "policy": "Schema similarity is discovery-only and never creates an identity relationship.",
    }


def field_associations(payload: dict[str, Any], *, minimum_tables: int = 3) -> dict[str, Any]:
    rows = _profiles(payload)
    field_tables: Counter[str] = Counter()
    pairs: Counter[tuple[str, str]] = Counter()
    for _table, profile in rows:
        fields = sorted(_field_set(profile))
        field_tables.update(fields)
        pairs.update(combinations(fields, 2))
    associations = []
    for (left, right), together in pairs.items():
        if together < minimum_tables:
            continue
        confidence_lr = together / field_tables[left] if field_tables[left] else 0.0
        confidence_rl = together / field_tables[right] if field_tables[right] else 0.0
        associations.append({
            "left": left,
            "right": right,
            "tables_together": together,
            "left_table_count": field_tables[left],
            "right_table_count": field_tables[right],
            "confidence_left_to_right": round(confidence_lr, 6),
            "confidence_right_to_left": round(confidence_rl, 6),
        })
    associations.sort(key=lambda row: (-max(row["confidence_left_to_right"], row["confidence_right_to_left"]), -row["tables_together"], row["left"], row["right"]))
    return {
        "schema": "dead-signal-field-associations",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "record_counts": {"tables": len(rows), "associations": len(associations)},
        "associations": associations[:1000],
        "policy": "Field co-occurrence suggests source families; it does not prove record or item identity.",
    }


def structural_outliers(payload: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for table, profile in _profiles(payload):
        shapes = profile.get("record_shapes") or []
        if not shapes:
            continue
        dominant = float((shapes[0] or {}).get("coverage") or 0.0)
        rare_shape_count = sum(1 for shape in shapes if float((shape or {}).get("coverage") or 0.0) <= 0.05)
        score = round((1.0 - dominant) + min(1.0, rare_shape_count / 10.0), 6)
        rows.append({
            "table": table,
            "record_count": int(profile.get("record_count") or 0),
            "shape_count": len(shapes),
            "dominant_shape_coverage": dominant,
            "rare_shape_count": rare_shape_count,
            "outlier_score": score,
        })
    rows.sort(key=lambda row: (-row["outlier_score"], -row["record_count"], row["table"]))
    return {
        "schema": "dead-signal-structural-outliers",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "record_counts": {"tables": len(rows)},
        "tables": rows,
        "policy": "Outlier scores identify unusual table structures for human inspection only.",
    }


def description_hotspots(payload: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for table, profile in _profiles(payload):
        descriptions = profile.get("description_like_fields") or []
        identities = profile.get("identity_like_fields") or []
        if not descriptions or not identities:
            continue
        desc_coverage = max(float(row.get("coverage") or 0.0) for row in descriptions)
        id_coverage = max(float(row.get("coverage") or 0.0) for row in identities)
        shared_warnings = int((profile.get("warnings") or {}).get("description_like_shared_values") or 0)
        score = round((desc_coverage * id_coverage * 100.0) - min(50.0, shared_warnings * 2.0), 3)
        rows.append({
            "table": table,
            "score": score,
            "record_count": int(profile.get("record_count") or 0),
            "description_fields": [row.get("field") for row in descriptions],
            "identity_fields": [row.get("field") for row in identities],
            "max_description_coverage": desc_coverage,
            "max_identity_coverage": id_coverage,
            "shared_description_warnings": shared_warnings,
        })
    rows.sort(key=lambda row: (-row["score"], -row["record_count"], row["table"]))
    return {
        "schema": "dead-signal-description-hotspots",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "record_counts": {"hotspots": len(rows)},
        "hotspots": rows,
        "policy": "Hotspot ranking is discovery-only; exact IDs and independent evidence are still required for verification.",
    }


class DeadSignalDiscovery:
    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        self.report_path = self.output / "published" / "reports" / "dead-signal-table-profiles.json"

    def _payload(self) -> dict[str, Any]:
        payload = _read_json(self.report_path, {}) or {}
        if not isinstance(payload, dict):
            raise ValueError("Dead Signal Table Profiler report is unavailable")
        return payload

    def run_all(self) -> dict[str, Any]:
        payload = self._payload()
        result = {
            "schema": "dead-signal-discovery-suite",
            "schema_version": SCHEMA_VERSION,
            "brand": "Dead Signal",
            "schema_clusters": schema_clusters(payload),
            "field_associations": field_associations(payload),
            "structural_outliers": structural_outliers(payload),
            "description_hotspots": description_hotspots(payload),
            "policy": "Discovery outputs are leads only and cannot establish identity, verification, or publication eligibility.",
        }
        target = self.output / "published" / "reports" / "dead-signal-discovery.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return result
