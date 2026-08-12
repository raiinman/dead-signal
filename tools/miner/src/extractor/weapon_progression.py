"""Evidence-first investigation of Once Human weapon Blueprint Star x Tier scaling.

This module operates only on JSON tables already extracted by Dead Signal Miner.
It does not import or execute game bytecode.

The objective is intentionally narrow: determine how blueprint progression levels
and crafted Gear Tier I-V combine to produce displayed weapon stats.  The module
preserves source evidence, computes falsifiable candidate models, and refuses to
promote a formula when the mined rows do not prove one.
"""
from __future__ import annotations

import argparse
import dis
import json
import marshal
import math
import re
import sqlite3
import sys
import statistics
import types
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

GAME_DATA = "game_common/data"
TABLE_HINT = re.compile(
    r"(?:gun|weapon|blueprint|equip|forge|strength|enhanc|progress|level|quality|grade|art_lv|attr)",
    re.IGNORECASE,
)
STAR_HINT = re.compile(r"(?:blueprint.?star|star.?level|star.?rank|\bstar\b)", re.IGNORECASE)
TIER_HINT = re.compile(r"(?:weapon.?tier|gear.?tier|craft.?tier|equip.?tier|art_lv|tier.?level|\btier\b)", re.IGNORECASE)
ATTACK_HINT = re.compile(r"(?:attack|damage|dmg|firepower)", re.IGNORECASE)
SCALE_HINT = re.compile(r"(?:mult|factor|coeff|scale|ratio|radio|rate|percent|pct)", re.IGNORECASE)
ENHANCE_HINT = re.compile(r"(?:enhanc|strength|quality|grade|level|\blv\b)", re.IGNORECASE)
BLUEPRINT_HINT = re.compile(r"blueprint", re.IGNORECASE)
TUPLE_KEY = re.compile(r"-?\d+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {} if default is None else default


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def rows(payload) -> dict:
    if isinstance(payload, dict):
        value = payload.get("data", payload)
        return value if isinstance(value, dict) else {}
    return {}


def finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", text):
            try:
                parsed = float(text)
                return parsed if math.isfinite(parsed) else None
            except ValueError:
                return None
    return None


def compact(value: Any, limit: int = 900) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        text = repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def walk(value: Any, pointer: str = "") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            child_pointer = f"{pointer}/{escaped}"
            if isinstance(child, (dict, list)):
                yield from walk(child, child_pointer)
            else:
                yield child_pointer, str(key), child
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_pointer = f"{pointer}/{index}"
            if isinstance(child, (dict, list)):
                yield from walk(child, child_pointer)
            else:
                yield child_pointer, str(index), child


def approximate_fraction(value: float, denominator: int = 10000) -> str:
    if not math.isfinite(value):
        return ""
    fraction = Fraction(value).limit_denominator(denominator)
    return f"{fraction.numerator}/{fraction.denominator}"


def distribution(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    median = statistics.median(values)
    mad = statistics.median(abs(value - median) for value in values) if len(values) > 1 else 0.0
    return {
        "n": len(values),
        "median": median,
        "mean": statistics.fmean(values),
        "mad": mad,
        "minimum": min(values),
        "maximum": max(values),
        "median_fraction": approximate_fraction(median),
    }


def factor_interval(base: float, observed: float, mode: str) -> tuple[float, float, bool, bool] | None:
    """Return factor interval compatible with positive integer display rounding.

    Tuple is (lower, upper, lower_inclusive, upper_inclusive).  Values are used
    as evidence ranges; boundary inclusivity is preserved in output but the
    intersection check treats zero-width boundaries conservatively.
    """
    if base <= 0:
        return None
    if mode == "nearest":
        return ((observed - 0.5) / base, (observed + 0.5) / base, True, False)
    if mode in {"floor", "truncate"}:
        return (observed / base, (observed + 1.0) / base, True, False)
    if mode == "ceil":
        return ((observed - 1.0) / base, observed / base, False, True)
    return None


def intersect_factor_intervals(pairs: list[tuple[float, float]], mode: str) -> dict:
    intervals = [factor_interval(base, observed, mode) for base, observed in pairs]
    intervals = [row for row in intervals if row is not None]
    if not intervals:
        return {"mode": mode, "compatible": False, "n": 0}
    lower = max(row[0] for row in intervals)
    upper = min(row[1] for row in intervals)
    compatible = lower < upper or math.isclose(lower, upper, rel_tol=0.0, abs_tol=1e-12)
    midpoint = (lower + upper) / 2.0 if compatible else None
    return {
        "mode": mode,
        "compatible": compatible,
        "n": len(intervals),
        "factor_min": lower,
        "factor_max": upper,
        "interval_width": max(0.0, upper - lower),
        "midpoint": midpoint,
        "midpoint_fraction": approximate_fraction(midpoint) if midpoint is not None else "",
    }


def tier_analysis(weapons: list[dict]) -> dict:
    ratio_samples: dict[int, list[float]] = defaultdict(list)
    pair_samples: dict[int, list[tuple[float, float]]] = defaultdict(list)
    per_weapon = []
    complete = 0
    for weapon in weapons:
        tier_rows = {
            int(row.get("tier")): finite_number(row.get("damage"))
            for row in weapon.get("tiers", [])
            if finite_number(row.get("tier")) is not None
        }
        tier_rows = {tier: damage for tier, damage in tier_rows.items() if damage is not None and damage > 0}
        if not tier_rows:
            continue
        base = tier_rows.get(1)
        ratios = {}
        adjacent = {}
        if base:
            for tier, damage in sorted(tier_rows.items()):
                ratio = damage / base
                ratios[str(tier)] = ratio
                ratio_samples[tier].append(ratio)
                pair_samples[tier].append((base, damage))
        for tier in range(2, 6):
            if tier in tier_rows and tier - 1 in tier_rows and tier_rows[tier - 1]:
                adjacent[str(tier)] = tier_rows[tier] / tier_rows[tier - 1]
        if all(tier in tier_rows for tier in range(1, 6)):
            complete += 1
        per_weapon.append({
            "blueprint_id": weapon.get("blueprint_id"),
            "name": weapon.get("name"),
            "quality": weapon.get("quality"),
            "tier_damage": {str(k): v for k, v in sorted(tier_rows.items())},
            "ratios_to_tier_1": ratios,
            "adjacent_ratios": adjacent,
        })

    aggregate = {}
    for tier in range(1, 6):
        values = ratio_samples.get(tier, [])
        if not values:
            continue
        entry = distribution(values)
        entry["rounding_factor_intersections"] = [
            intersect_factor_intervals(pair_samples[tier], mode)
            for mode in ("nearest", "floor", "ceil")
        ]
        aggregate[str(tier)] = entry

    compatible_modes = {}
    for tier, entry in aggregate.items():
        compatible_modes[tier] = [
            row for row in entry.get("rounding_factor_intersections", []) if row.get("compatible")
        ]

    return {
        "weapons_with_tier_damage": len(per_weapon),
        "weapons_with_complete_tiers": complete,
        "aggregate_ratios_to_tier_1": aggregate,
        "universal_factor_candidates": compatible_modes,
        "weapons": per_weapon,
    }


def blueprint_level_analysis(weapons: list[dict]) -> dict:
    """Analyze raw gun_blueprint_attr_data progression without renaming evidence prematurely.

    Two source fields are especially important:
      * strength_lv -- compared against the table tuple's second integer.
      * preset_attack_radio -- preserved verbatim (the game field is spelled "radio")
        and normalized in our output as preset_attack_ratio because its values are
        already multiplicative factors such as 1.05, not additive +5% bonuses.
    """
    quality_level_counts: dict[str, list[int]] = defaultdict(list)
    quality_max_levels: dict[str, list[int]] = defaultdict(list)
    attribute_ratios: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    attribute_values: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    attribute_labels: dict[str, Counter] = defaultdict(Counter)
    field_ratios: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    quality_ratio_curves: dict[str, Counter] = defaultdict(Counter)
    ratio_curve_examples: dict[tuple[str, tuple], list[str]] = defaultdict(list)
    strength_rows_total = 0
    strength_rows_matching_tuple_level = 0
    preset_ratio_rows = 0
    progression_modes = Counter()
    per_weapon = []

    for weapon in weapons:
        progression = weapon.get("blueprint_attribute_progression") or {}
        levels = [row for row in progression.get("levels", []) if isinstance(row, dict)]
        levels = sorted(levels, key=lambda row: int(row.get("level") or 0))
        quality = str(weapon.get("quality") or "Unknown")
        level_numbers = [int(row.get("level") or 0) for row in levels if int(row.get("level") or 0) > 0]
        if level_numbers:
            quality_level_counts[quality].append(len(level_numbers))
            quality_max_levels[quality].append(max(level_numbers))

        attr_by_level: dict[int, dict[str, float]] = defaultdict(dict)
        label_by_code: dict[str, str] = {}
        raw_numeric_by_level: dict[int, dict[str, float]] = defaultdict(dict)
        strength_by_level: dict[int, int] = {}
        preset_ratio_by_level: dict[int, float] = {}
        fixed_skill_level_by_level: dict[int, int] = {}

        for row in levels:
            level = int(row.get("level") or 0)
            if level <= 0:
                continue
            for attr in row.get("base_attributes", []) or []:
                if not isinstance(attr, dict):
                    continue
                code = str(attr.get("code") or "")
                value = finite_number(attr.get("value"))
                if code and value is not None:
                    attr_by_level[level][code] = value
                    label = str(attr.get("label") or code)
                    label_by_code[code] = label
                    attribute_labels[code][label] += 1
                    attribute_values[code][level].append(value)

            raw_fields = row.get("raw_fields") or {}
            raw_strength = finite_number(raw_fields.get("strength_lv"))
            if raw_strength is not None and float(raw_strength).is_integer():
                raw_strength_int = int(raw_strength)
                strength_by_level[level] = raw_strength_int
                strength_rows_total += 1
                if raw_strength_int == level:
                    strength_rows_matching_tuple_level += 1

            raw_ratio = finite_number(raw_fields.get("preset_attack_radio"))
            if raw_ratio is not None and raw_ratio > 0:
                preset_ratio_by_level[level] = raw_ratio
                preset_ratio_rows += 1

            raw_skill_level = finite_number(raw_fields.get("fixed_skill_lv"))
            if raw_skill_level is not None and float(raw_skill_level).is_integer():
                fixed_skill_level_by_level[level] = int(raw_skill_level)

            for pointer, field, value in walk(raw_fields):
                parsed = finite_number(value)
                if parsed is None:
                    continue
                # Exclude identity/skill fields from generic factor inference.
                if re.search(r"(?:skill|code|_id$|_no$|^id$)", field, re.IGNORECASE):
                    continue
                raw_numeric_by_level[level][pointer] = parsed

        level1_attrs = attr_by_level.get(1, {})
        for level, attrs in attr_by_level.items():
            for code, value in attrs.items():
                base = level1_attrs.get(code)
                if base not in (None, 0):
                    attribute_ratios[code][level].append(value / base)

        if 1 in raw_numeric_by_level:
            base_fields = raw_numeric_by_level[1]
            for level, fields in raw_numeric_by_level.items():
                for pointer, value in fields.items():
                    base = base_fields.get(pointer)
                    if base not in (None, 0):
                        field_ratios[pointer][level].append(value / base)

        attack_candidates = []
        for code, label in label_by_code.items():
            if ATTACK_HINT.search(label) or ATTACK_HINT.search(code):
                attack_candidates.append({
                    "code": code,
                    "label": label,
                    "values_by_level": {
                        str(level): attr_by_level[level].get(code)
                        for level in sorted(attr_by_level)
                        if code in attr_by_level[level]
                    },
                })

        ratio_curve = tuple(preset_ratio_by_level.get(level) for level in sorted(preset_ratio_by_level))
        if ratio_curve:
            quality_ratio_curves[quality][ratio_curve] += 1
            key = (quality, ratio_curve)
            if len(ratio_curve_examples[key]) < 8:
                ratio_curve_examples[key].append(str(weapon.get("name") or weapon.get("blueprint_id")))

        ratio_values = [preset_ratio_by_level[level] for level in sorted(preset_ratio_by_level)]
        skill_values = [fixed_skill_level_by_level.get(level, 0) for level in sorted(level_numbers)]
        ratio_changes = len(set(ratio_values)) > 1
        skill_changes = len(set(skill_values)) > 1
        if ratio_changes and skill_changes:
            progression_mode = "attack-ratio-and-skill-level"
        elif ratio_changes:
            progression_mode = "attack-ratio"
        elif skill_changes:
            progression_mode = "skill-level"
        else:
            progression_mode = "no-changing-attack-ratio-or-skill-level"
        progression_modes[progression_mode] += 1

        per_weapon.append({
            "blueprint_id": weapon.get("blueprint_id"),
            "name": weapon.get("name"),
            "quality": quality,
            "levels": level_numbers,
            "progression_effect_mode": progression_mode,
            "strength_lv_by_raw_level": {str(k): v for k, v in sorted(strength_by_level.items())},
            "tuple_level_equals_strength_lv": bool(level_numbers) and all(strength_by_level.get(level) == level for level in level_numbers),
            "preset_attack_ratio_source_field": "preset_attack_radio",
            "preset_attack_ratio_by_level": {str(k): v for k, v in sorted(preset_ratio_by_level.items())},
            "fixed_skill_level_by_level": {str(k): v for k, v in sorted(fixed_skill_level_by_level.items())},
            "attack_or_damage_attribute_candidates": attack_candidates,
        })

    quality_summary = {}
    for quality in sorted(set(quality_level_counts) | set(quality_max_levels)):
        counts = quality_level_counts.get(quality, [])
        maxima = quality_max_levels.get(quality, [])
        quality_summary[quality] = {
            "weapons": len(maxima),
            "level_count_distribution": dict(sorted(Counter(counts).items())),
            "max_level_distribution": dict(sorted(Counter(maxima).items())),
            "common_max_level": Counter(maxima).most_common(1)[0][0] if maxima else None,
        }

    attr_summary = {}
    for code in sorted(set(attribute_values) | set(attribute_ratios)):
        levels = attribute_ratios.get(code, {})
        label = attribute_labels[code].most_common(1)[0][0] if attribute_labels[code] else code
        attr_summary[code] = {
            "label": label,
            "attack_or_damage_candidate": bool(ATTACK_HINT.search(label) or ATTACK_HINT.search(code)),
            "values": {str(level): distribution(values) for level, values in sorted(attribute_values[code].items())},
            "ratios_to_level_1": {str(level): distribution(values) for level, values in sorted(levels.items())},
            "ratio_note": (
                "Ratios are omitted where the level-1 value is zero; use raw values/deltas for additive percentage progressions."
                if any(finite_number(value) == 0 for value in attribute_values[code].get(1, []))
                else "Ratios are normalized to level 1 where a non-zero baseline exists."
            ),
        }

    raw_field_summary = []
    for pointer, levels in field_ratios.items():
        coverage = sum(len(values) for values in levels.values())
        if coverage < 3 or len(levels) < 2:
            continue
        raw_field_summary.append({
            "field": pointer,
            "coverage": coverage,
            "ratios_to_level_1": {str(level): distribution(values) for level, values in sorted(levels.items())},
        })
    raw_field_summary.sort(key=lambda row: (-row["coverage"], row["field"]))

    curves = []
    for quality in sorted(quality_ratio_curves):
        for curve, count in quality_ratio_curves[quality].most_common():
            curves.append({
                "quality": quality,
                "weapons": count,
                "levels": list(range(1, len(curve) + 1)),
                "preset_attack_ratio": list(curve),
                "examples": ratio_curve_examples.get((quality, curve), []),
            })

    all_sequences_start_at_one = all(not row["levels"] or min(row["levels"]) == 1 for row in per_weapon)
    strength_match_rate = (
        strength_rows_matching_tuple_level / strength_rows_total if strength_rows_total else 0.0
    )
    direct_ratio_coverage = preset_ratio_rows / strength_rows_total if strength_rows_total else 0.0

    return {
        "interpretation_status": (
            "direct-source-star-attack-factor-found"
            if strength_rows_total and strength_rows_matching_tuple_level == strength_rows_total and preset_ratio_rows == strength_rows_total
            else "raw-levels-under-test"
        ),
        "raw_level_star_hypothesis": {
            "all_nonempty_sequences_start_at_1": all_sequences_start_at_one,
            "strength_lv_rows": strength_rows_total,
            "tuple_level_matches_strength_lv_rows": strength_rows_matching_tuple_level,
            "tuple_level_matches_strength_lv_rate": strength_match_rate,
            "observed_common_max_levels_by_quality": {
                quality: row["common_max_level"] for quality, row in quality_summary.items()
            },
            "note": (
                "The tuple level and source field strength_lv are identical across all captured rows when the match rate is 1.0. "
                "Rarity-dependent level caps and the separate five-value corr_forge_lv Tier system make Blueprint Stars the leading semantic interpretation."
            ),
        },
        "preset_attack_ratio_evidence": {
            "source_table": "game_common/data/gun_blueprint_attr_data.json",
            "source_field": "preset_attack_radio",
            "normalized_alias": "preset_attack_ratio",
            "rows": preset_ratio_rows,
            "coverage_of_strength_rows": direct_ratio_coverage,
            "value_semantics": "direct multiplier (1.05 means x1.05), not additive bonus",
            "curves_by_quality": curves,
        },
        "progression_effect_modes": dict(sorted(progression_modes.items())),
        "quality_level_summary": quality_summary,
        "attribute_progression": attr_summary,
        "raw_numeric_field_progression": raw_field_summary[:120],
        "weapons": per_weapon,
    }

def table_candidate_score(relative: str, record_id: str, record: dict, blueprint_ids: set[str]) -> tuple[int, list[str], list[dict]]:
    score = 0
    reasons = []
    numeric_sequences = []
    table_text = relative.replace("_", " ")
    if BLUEPRINT_HINT.search(table_text):
        score += 3
        reasons.append("blueprint-table")
    if TIER_HINT.search(table_text):
        score += 4
        reasons.append("tier-table-name")
    if ENHANCE_HINT.search(table_text):
        score += 2
        reasons.append("progression-table-name")
    if str(record_id) in blueprint_ids or any(part in blueprint_ids for part in TUPLE_KEY.findall(str(record_id))):
        score += 5
        reasons.append("weapon-blueprint-id")

    flattened = list(walk(record))
    fields = " ".join(field for _, field, _ in flattened)
    if STAR_HINT.search(fields):
        score += 10
        reasons.append("star-field")
    if TIER_HINT.search(fields):
        score += 7
        reasons.append("tier-field")
    if ATTACK_HINT.search(fields):
        score += 5
        reasons.append("attack-damage-field")
    if SCALE_HINT.search(fields):
        score += 5
        reasons.append("scale-field")
    if BLUEPRINT_HINT.search(fields):
        score += 3
        reasons.append("blueprint-field")
    if ENHANCE_HINT.search(fields):
        score += 2
        reasons.append("enhancement-field")

    for key, value in record.items():
        if not isinstance(value, list) or not 3 <= len(value) <= 8:
            continue
        nums = [finite_number(item) for item in value]
        if all(item is not None for item in nums):
            key_text = str(key)
            if STAR_HINT.search(key_text) or TIER_HINT.search(key_text) or SCALE_HINT.search(key_text) or ENHANCE_HINT.search(key_text):
                score += 8
                reasons.append("numeric-progression-array")
                numeric_sequences.append({"field": key_text, "values": nums})

    if ("star-field" in reasons and "attack-damage-field" in reasons) or (
        "tier-field" in reasons and "scale-field" in reasons
    ):
        score += 8
        reasons.append("high-value-combination")
    return score, sorted(set(reasons)), numeric_sequences


def scan_candidate_tables(base: Path, current: Path, blueprint_ids: set[str], limit: int = 900) -> dict:
    candidates = []
    table_counts = Counter()
    scanned_tables = 0
    scanned_rows = 0
    seen = set()
    for layer, root in (("base", base), ("current", current)):
        data_root = root / GAME_DATA
        if not data_root.exists():
            continue
        for path in data_root.rglob("*.json"):
            relative = path.relative_to(root).as_posix()
            if not TABLE_HINT.search(relative):
                continue
            payload_rows = rows(read_json(path))
            if not payload_rows:
                continue
            scanned_tables += 1
            for record_id, record in payload_rows.items():
                if not isinstance(record, dict):
                    continue
                scanned_rows += 1
                score, reasons, numeric_sequences = table_candidate_score(relative, str(record_id), record, blueprint_ids)
                if score < 8:
                    continue
                key = (relative, str(record_id), compact(record, 500))
                # Current layer supersedes identical base content.
                if key in seen:
                    continue
                seen.add(key)
                table_counts[relative] += 1
                candidates.append({
                    "score": score,
                    "layer": layer,
                    "table": relative,
                    "record_id": str(record_id),
                    "reasons": reasons,
                    "numeric_sequences": numeric_sequences,
                    "record_preview": record if len(compact(record, 5000)) < 5000 else compact(record, 5000),
                })
    candidates.sort(key=lambda row: (-row["score"], row["table"], row["record_id"]))
    return {
        "scanned_tables": scanned_tables,
        "scanned_rows": scanned_rows,
        "candidate_count": len(candidates),
        "candidate_tables": [{"table": table, "rows": count} for table, count in table_counts.most_common()],
        "top_candidates": candidates[:limit],
    }


def tracer_weapon_references(database: Path, weapons: list[dict], per_weapon_limit: int = 60) -> dict:
    result = {"database": str(database), "available": database.exists(), "weapons": []}
    if not database.exists():
        return result
    connection = sqlite3.connect(database)
    try:
        for weapon in weapons:
            identifiers = []
            for value in (weapon.get("blueprint_id"), weapon.get("item_id")):
                if value not in (None, "", 0):
                    identifiers.append(str(value))
            for tier in weapon.get("tiers", []) or []:
                for value in (tier.get("item_id"), tier.get("gun_no")):
                    if value not in (None, "", 0):
                        identifiers.append(str(value))
            identifiers = list(dict.fromkeys(identifiers))
            matches = []
            for identifier in identifiers:
                rows_found = connection.execute(
                    """
                    SELECT value,layer,table_name,record_id,field,json_pointer
                    FROM occurrences
                    WHERE value=? AND (
                        table_name LIKE '%blueprint%' OR table_name LIKE '%gun_%' OR
                        table_name LIKE '%weapon%' OR table_name LIKE '%equip%' OR
                        table_name LIKE '%forge%' OR table_name LIKE '%progress%' OR
                        table_name LIKE '%level%' OR table_name LIKE '%strength%'
                    )
                    ORDER BY table_name,record_id
                    LIMIT ?
                    """,
                    (identifier, per_weapon_limit),
                ).fetchall()
                for value, layer, table_name, record_id, field, pointer in rows_found:
                    matches.append({
                        "query": value,
                        "layer": layer,
                        "table": table_name,
                        "record_id": record_id,
                        "field": field,
                        "json_pointer": pointer,
                    })
            unique = []
            seen = set()
            for row in matches:
                key = tuple(row.values())
                if key in seen:
                    continue
                seen.add(key)
                unique.append(row)
            result["weapons"].append({
                "blueprint_id": weapon.get("blueprint_id"),
                "name": weapon.get("name"),
                "identifiers": identifiers,
                "match_count": len(unique),
                "matches": unique[:per_weapon_limit],
            })
    except sqlite3.Error as exc:
        result["error"] = str(exc)
    finally:
        connection.close()
    result["weapons_with_matches"] = sum(bool(row["match_count"]) for row in result["weapons"])
    result["total_matches_retained"] = sum(row["match_count"] for row in result["weapons"])
    return result


def attack_star_candidates(blueprint_analysis: dict) -> list[dict]:
    candidates = []
    for code, row in blueprint_analysis.get("attribute_progression", {}).items():
        if not row.get("attack_or_damage_candidate"):
            continue
        levels = row.get("values", {})
        candidate = {
            "code": code,
            "label": row.get("label"),
            "raw_values_by_level": levels,
            "ratios_to_level_1": row.get("ratios_to_level_1", {}),
            "candidate_multiplier_if_value_is_fractional_bonus": {},
        }
        for level, stats in levels.items():
            median = stats.get("median")
            if isinstance(median, (int, float)) and -1.0 <= median <= 5.0:
                candidate["candidate_multiplier_if_value_is_fractional_bonus"][level] = 1.0 + median
        candidates.append(candidate)
    return candidates


def combined_star_tier_candidates(tier_analysis_payload: dict, blueprint_analysis_payload: dict) -> list[dict]:
    """Build Star x Tier matrices using the game's explicit preset_attack_radio field.

    IMPORTANT: preset_attack_radio is already a multiplier. A value of 1.05 is
    x1.05, not a +1.05 fractional bonus and must never be converted to 2.05.
    """
    tiers_by_blueprint = {
        str(row.get("blueprint_id")): row
        for row in tier_analysis_payload.get("weapons", [])
        if row.get("blueprint_id") is not None
    }
    blue_by_blueprint = {
        str(row.get("blueprint_id")): row
        for row in blueprint_analysis_payload.get("weapons", [])
        if row.get("blueprint_id") is not None
    }
    results = []
    for blueprint_id, tier_row in tiers_by_blueprint.items():
        blue_row = blue_by_blueprint.get(blueprint_id)
        if not blue_row:
            continue
        tier_damage = {int(k): finite_number(v) for k, v in (tier_row.get("tier_damage") or {}).items()}
        tier_damage = {k: v for k, v in tier_damage.items() if v is not None}
        factors = {int(k): finite_number(v) for k, v in (blue_row.get("preset_attack_ratio_by_level") or {}).items()}
        factors = {k: v for k, v in factors.items() if v is not None and v > 0}
        if not factors or not tier_damage:
            continue
        matrix = {}
        for level, multiplier in sorted(factors.items()):
            matrix[str(level)] = {}
            for tier_no, base_damage in sorted(tier_damage.items()):
                raw = base_damage * multiplier
                matrix[str(level)][str(tier_no)] = {
                    "tier_base_damage": base_damage,
                    "source_preset_attack_radio": multiplier,
                    "unrounded": raw,
                    "nearest_half_up": math.floor(raw + 0.5),
                    "python_bankers_round": round(raw),
                    "floor": math.floor(raw),
                    "truncate_toward_zero": int(raw),
                    "ceil": math.ceil(raw),
                }
        results.append({
            "blueprint_id": tier_row.get("blueprint_id"),
            "name": tier_row.get("name"),
            "quality": tier_row.get("quality"),
            "source_factor_table": "game_common/data/gun_blueprint_attr_data.json",
            "source_factor_field": "preset_attack_radio",
            "strength_level_mapping": blue_row.get("strength_lv_by_raw_level", {}),
            "hypothesis": "DisplayedAttack = UI_IntegerConversion(Tier gun_preset_attack * preset_attack_radio[strength_lv])",
            "status": "source-factor-proven-rounding-unresolved",
            "matrix_by_strength_level_and_tier": matrix,
        })
    return results

PYC_TARGETS = (
    "preset_attack_radio",
    "preset_attack_ratio",
    "strength_lv",
    "gun_preset_attack",
    "corr_forge_lv",
    "gun_blueprint_attr_data",
)
PYC_DISPLAY_TARGETS = ("D0100",)
# v1.4.7 calibration trace: gun_correct_print_data.affix_val_range is the
# mined rarity-wide RNG range. Scan both its data fields and the client helpers
# that generate, serialize, read and apply calibration affix values.
PYC_CALIBRATION_TARGETS = (
    "affix_val_range",
    "affix_ids_weight",
    "gun_correct_affix_val",
    "gun_correct_affix_list",
    "gun_correct_affix_skill",
    "gun_correct_print_data",
    "gun_correct_common_terms_data",
    "gun_calibration_affix_option_data",
    "gun_blueprint_terms_pool",
    "GUN_BLUEPRINT_TERMS_POOL",
    "D0101",
    "D0102",
    "correct_style",
    "calibration_style_gun",
    "calibration_option_gun",
    "gun_correct_item_no",
    "gun_calibration_attr",
    "correct_affix_add",
    "affix_options",
    "affix_option_libs",
    "VM_GUN_FORMULAS",
    "all_affix_adds",
    "all_calc_affix_add",
)
# v1.5.1 generic weapon-card stat aggregator + resolved Attack-ratio trace. These symbols survive
# client opcode remapping and expose the static weapon-card input pipeline:
# base weapon data, equipped accessories, random affixes, +7/+10 affix options,
# calibration-level additions, and Calibration Blueprint (correct) affixes.
PYC_WEAPON_AGGREGATOR_TARGETS = (
    "base_affix_add",
    "accessory_affix_add",
    "rand_affix_add",
    "affix_option_add",
    "cal_affix",
    "correct_affix_add",
    "all_affix_adds",
    "all_guncore_affix_add",
    "all_guncore_affix_primitive",
    "all_calc_affix_add",
    "accessory_affix_primitive",
    "accessory_calc_affix_add",
    "gun_slot_accessory_data_list",
    "VM_GUN_FORMULAS",
    "item_attack_base",
    "item_attack_guncore",
    "item_attack",
    "attack_radio",
    "delta_attack",
    "attr_radio_affix_ids",
    "D0100",
    "D0101",
    "D0102",
    # v1.5.3: final weapon-card display branch probe. These survive the
    # remapped bytecode and let us bind D0100 to the formatter's absolute
    # versus rate path without trusting stock disassembly.
    "affix_prototype_data",
    "AP_CALC_TYPE_ABS",
    "AP_CALC_TYPE_RATE",
    "ATTR_VAL_ABS",
    "ATTR_VAL_RATE",
    "effect_range",
    "val_type",
    "format_val_str",
    "Q0100",
    "Q0300",
    "Q0500",
    "Q0800",
    "Q0900",
    "Q1100",
    "Q1101",
    "Q1600",
    "Q2000",
    "Q2400",
    "Q2600",
)

PYC_ROUNDING_NAMES = {
    "round", "int", "floor", "ceil", "trunc", "format", "str", "float",
    "Decimal", "sprintf", "format_float", "format_value",
}
PYC_PROGRESSION_FUNCTIONS = {
    "get_gun_preset_attack_radio",
    "get_gun_omg_value",
    "get_gun_attack_base",
    "get_gun_attack",
    "get_gun_attack_guncore",
}
# v1.4.5 follows the already-proven raw Attack float into the generic stat/UI
# layer. D0100 is the Attack stat key used by get_weapon_base_attr_dict() and
# read by ItemDataTools.get_gun_attack(). These functions are deliberately
# focus-scanned even when they do not mention the original progression fields.
PYC_DISPLAY_FUNCTIONS = {
    "get_weapon_base_attr_dict",
    "get_weapon_base_attr_list",
    "get_weapon_base_attr_new",
    "convert_data_show_attr",
    "convert_data_adjust_show_attr",
    "get_affix_name_and_val",
    # v1.5.2: calc_gun_attr_data formats D0100 through AffixUtils.get_affix_name_and_val2,
    # not only get_affix_name_and_val. Capture the formatter family directly so the
    # fully aggregated weapon-card integer/decimal conversion can be proven.
    "get_affix_name_and_val2",
    "get_affix_format_name_and_val",
    "convert_affix_format_str",
    "get_format_attr_val",
    "adjust_affix_val",
    "get_affix_desc_format",
    "get_gun_attack",
}
PYC_CALIBRATION_FUNCTIONS = {
    "gen_rand_correct_affixs",
    "gen_rand_gun_affixs",
    "_rand_term_no_lst",
    "rand_term_affix_data",
    "generate_correct_print_term_id",
    "generate_correct_term_data",
    "generate_gun_correct_print_detail",
    "generate_gun_correct_print_info",
    "init_gun_correct_print_info",
    "get_gun_calibration_affix_option_libs",
    "get_gun_calibration_affix_option_size",
    "get_gun_correct_affix_desc",
    "construct_correct_blueprint_term_info_by_affix_list",
    "get_item_calibration_attr",
    "get_gun_calibration_attr",
    "convert_gun_correct_affix_val_to_affix_list",
    "get_gun_correct_affix_add",
    "get_gun_correct_item_no",
    "get_max_term_affix_value",
    "get_gun_base_affix_add",
    "get_gun_attack_guncore",
    "get_gun_average_tire",
    "get_gun_info",
    "calc_gun_attr_data",
    "refresh_base_prop",
    "get_gun_affix_add",
    "get_gun_calc_affix_add",
    "get_gun_affix_option_add",
    "get_gun_base_affix_attack",
    "cal_gun_attr_data_with_item_no",
    "get_gun_base_random_attr_data",
}
PYC_WEAPON_AGGREGATOR_FUNCTIONS = {
    "get_gun_affix_add",
    "get_gun_calc_affix_add",
    "get_all_guncore_affix_add",
    "get_gun_accessory_affix_add",
    "get_gun_calc_accessory_affix_add",
    "get_gun_rand_attr_affix_add",
    "get_gun_no_rand_affix_add",
    "get_gun_magazine_affix_add",
    "get_blueprint_affix_add",
    "get_equipped_accessorys",
    "get_gun_accessory_list",
    "get_gun_accessory_all_show_list_data",
    "get_gun_accessory_all_show_slot_pos",
    "get_gun_slot_accessory_data_list",
    "get_gun_base_random_attr",
    "get_gun_base_random_attr_list",
    "get_gun_rand_attr",
    "get_gun_rand_attr_affix_add",
    "_calc_gun_attr_list",
    "get_gun_rpm_val",
    "get_gun_magazine_size",
    "get_gun_mobility",
    # v1.5.6: deeper static-card mechanics behind the UI-level readers.
    "get_gun_shoot_attr_weapon_rpm",
    "get_gun_shoot_interval",
    "get_weapon_accuracy_rate",
    "get_weapoon_range_value",
    "get_reload_add_bullet_time_value",
    "get_init_weapon_stability",
    "get_weapon_stability_affix",
    # v1.5.2 final weapon-card display bridge.
    "calc_gun_attr_data",
    "cal_gun_attr_data_with_item_no",
    "refresh_base_prop",
    "refresh_item_lst",
    "get_affix_name_and_val2",
    "get_affix_format_name_and_val",
    "get_format_attr_val",
}
PYC_FOCUS_FUNCTIONS = (
    PYC_PROGRESSION_FUNCTIONS
    | PYC_DISPLAY_FUNCTIONS
    | PYC_CALIBRATION_FUNCTIONS
    | PYC_WEAPON_AGGREGATOR_FUNCTIONS
)
# Follow source factors, D0100 display/stat chain, and the calibration RNG/apply
# chain. co_names/co_consts remain useful even when opcode numbers are remapped.
PYC_FOCUS_SYMBOLS = tuple(sorted(PYC_FOCUS_FUNCTIONS))
PYC_CHAIN_SYMBOLS = tuple(sorted(PYC_FOCUS_FUNCTIONS))
PYC_SCAN_SYMBOLS = tuple(dict.fromkeys(
    PYC_TARGETS
    + PYC_DISPLAY_TARGETS
    + PYC_CALIBRATION_TARGETS
    + PYC_WEAPON_AGGREGATOR_TARGETS
    + PYC_CHAIN_SYMBOLS
))


def _snapshot_source_root(snapshot_path: Path) -> Path | None:
    payload = read_json(snapshot_path, {})
    raw = payload.get("source_root") if isinstance(payload, dict) else None
    if not raw:
        return None
    path = Path(str(raw))
    return path if path.exists() else None


def _ascii_context(raw: bytes, offset: int, radius: int = 1800) -> list[str]:
    start = max(0, offset - radius)
    end = min(len(raw), offset + radius)
    chunk = raw[start:end]
    strings = re.findall(rb"[A-Za-z_][A-Za-z0-9_./:-]{2,}", chunk)
    decoded = []
    seen = set()
    for value in strings:
        text = value.decode("ascii", errors="ignore")
        if text in seen:
            continue
        seen.add(text)
        decoded.append(text)
        if len(decoded) >= 120:
            break
    return decoded


def _walk_code_objects(code: types.CodeType, qualname: str = "<module>"):
    yield qualname, code
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            child = f"{qualname}.{const.co_name}"
            yield from _walk_code_objects(const, child)


def _instruction_window(instructions: list, center: int, radius: int = 20) -> list[dict]:
    out = []
    for ins in instructions[max(0, center - radius): min(len(instructions), center + radius + 1)]:
        argval = ins.argval
        if not isinstance(argval, (str, int, float, bool, type(None))):
            argval = repr(argval)
        out.append({
            "offset": ins.offset,
            "opname": ins.opname,
            "argrepr": ins.argrepr,
            "argval": argval,
        })
    return out


def _safe_const(value: Any, depth: int = 0):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return {"bytes_hex": value[:256].hex(), "bytes_len": len(value)}
    if isinstance(value, tuple) and depth < 2:
        return [_safe_const(item, depth + 1) for item in value[:64]]
    if isinstance(value, frozenset) and depth < 2:
        return [_safe_const(item, depth + 1) for item in list(value)[:64]]
    if isinstance(value, types.CodeType):
        return {"code_object": value.co_name, "firstlineno": value.co_firstlineno}
    text = repr(value)
    return {"python_type": type(value).__name__, "repr": text[:500]}


def _code_capsule(code_obj: types.CodeType) -> dict:
    """Persist enough static code-object state to decode a failed disassembly later.

    Some Once Human PYC code objects marshal successfully under the bundled
    runtime but use an opcode/name layout that makes stdlib `dis` raise an
    IndexError.  Never discard those functions: preserve the raw wordcode,
    names, constants and locals so the consumer path can be reconstructed
    offline without executing the bytecode.
    """
    capsule = {
        "co_name": code_obj.co_name,
        "co_qualname": getattr(code_obj, "co_qualname", code_obj.co_name),
        "co_filename": code_obj.co_filename,
        "co_firstlineno": code_obj.co_firstlineno,
        "co_argcount": code_obj.co_argcount,
        "co_posonlyargcount": getattr(code_obj, "co_posonlyargcount", 0),
        "co_kwonlyargcount": code_obj.co_kwonlyargcount,
        "co_nlocals": code_obj.co_nlocals,
        "co_stacksize": code_obj.co_stacksize,
        "co_flags": code_obj.co_flags,
        "co_names": list(map(str, code_obj.co_names)),
        "co_varnames": list(map(str, code_obj.co_varnames)),
        "co_freevars": list(map(str, code_obj.co_freevars)),
        "co_cellvars": list(map(str, code_obj.co_cellvars)),
        "co_consts": [_safe_const(value) for value in code_obj.co_consts],
        "co_code_hex": code_obj.co_code.hex(),
        "co_code_len": len(code_obj.co_code),
    }
    exception_table = getattr(code_obj, "co_exceptiontable", b"")
    line_table = getattr(code_obj, "co_linetable", b"")
    if exception_table:
        capsule["co_exceptiontable_hex"] = exception_table.hex()
    if line_table:
        capsule["co_linetable_hex"] = line_table.hex()
    return capsule


def _raw_wordcode(code_obj: types.CodeType, limit: int = 4096) -> list[dict]:
    """Version-agnostic two-byte wordcode dump.

    `opname_runtime` is only a hint when the game bytecode version differs from
    the miner runtime.  Opcode number + raw argument are authoritative.
    """
    raw = code_obj.co_code
    rows = []
    for offset in range(0, min(len(raw), limit), 2):
        opcode_num = raw[offset]
        arg = raw[offset + 1] if offset + 1 < len(raw) else None
        opname = dis.opname[opcode_num] if 0 <= opcode_num < len(dis.opname) else f"<opcode-{opcode_num}>"
        rows.append({
            "offset": offset,
            "opcode": opcode_num,
            "oparg_byte": arg,
            "opname_runtime": opname,
        })
    return rows


def _known_obfuscated_tail(code_obj: types.CodeType) -> dict | None:
    """Recognize the stable remapped tail used by the Once Human 3.11 client.

    The game keeps standard BINARY_OP arguments but remaps several opcode
    numbers.  The progression consumers captured in the current snapshot share
    an unambiguous tail mapping:

      100 -> STORE_FAST
       94 -> LOAD_FAST
      125 -> BINARY_OP
      122 -> RETURN_VALUE

    BINARY_OP argument 5 is CPython's NB_MULTIPLY.  We only decode exact tail
    shapes whose local indexes are valid; this is evidence extraction, not a
    general deobfuscator.
    """
    raw = code_obj.co_code
    if len(raw) < 6 or len(raw) % 2:
        return None
    words = [(i, raw[i], raw[i + 1]) for i in range(0, len(raw), 2)]
    locals_ = list(map(str, code_obj.co_varnames))

    def local_name(index: int) -> str | None:
        return locals_[index] if 0 <= index < len(locals_) else None

    # STORE_FAST r; LOAD_FAST x; LOAD_FAST r; BINARY_OP NB_MULTIPLY; CACHE; RETURN
    if len(words) >= 6:
        tail = words[-6:]
        if (tail[0][1] == 100 and tail[1][1] == 94 and tail[2][1] == 94
                and tail[3][1] == 125 and tail[3][2] == 5
                and tail[4][1] == 0 and tail[5][1] == 122):
            stored = local_name(tail[0][2])
            left = local_name(tail[1][2])
            right = local_name(tail[2][2])
            if stored and left and right and right == stored:
                return {
                    "status": "recognized-exact-tail",
                    "operation": "multiply-return",
                    "expression": f"{left} * {right}",
                    "stored_local": stored,
                    "binary_oparg": 5,
                    "binary_operation": "NB_MULTIPLY (*)",
                    "raw_words": [
                        {"offset": off, "opcode": op, "arg": arg}
                        for off, op, arg in tail
                    ],
                    "opcode_mapping_evidence": {
                        "100": "STORE_FAST",
                        "94": "LOAD_FAST",
                        "125": "BINARY_OP",
                        "122": "RETURN_VALUE",
                    },
                }

    # STORE_FAST r; LOAD_FAST r; RETURN
    if len(words) >= 3:
        tail = words[-3:]
        if tail[0][1] == 100 and tail[1][1] == 94 and tail[2][1] == 122:
            stored = local_name(tail[0][2])
            loaded = local_name(tail[1][2])
            if stored and loaded and stored == loaded:
                return {
                    "status": "recognized-exact-tail",
                    "operation": "direct-return",
                    "expression": loaded,
                    "stored_local": stored,
                    "raw_words": [
                        {"offset": off, "opcode": op, "arg": arg}
                        for off, op, arg in tail
                    ],
                    "opcode_mapping_evidence": {
                        "100": "STORE_FAST",
                        "94": "LOAD_FAST",
                        "122": "RETURN_VALUE",
                    },
                }
    return None


def _wordcode_words(code_obj: types.CodeType) -> list[tuple[int, int, int]]:
    raw = code_obj.co_code
    return [(i, raw[i], raw[i + 1]) for i in range(0, len(raw) - 1, 2)]


def _recognize_weapon_omg_property_dispatch(code_obj: types.CodeType) -> dict | None:
    """Recognize the exact property branch that forwards weapon OMG to get_gun_omg_value.

    In the current Once Human client the remapped opcodes preserve operands.  The
    `get_gun_attr_property_value` branch for the literal
    `weapon_omg_affix_value` contains a stable sequence:

      LOAD_GLOBAL get_gun_omg_value
      LOAD_FAST gun_no
      LOAD_FAST star
      CALL 2
      ... caches ...
      RETURN_VALUE

    This proves the property getter does not apply an extra numeric conversion
    before returning the already-proven `preset_attack * attack_radio` value.
    """
    if code_obj.co_name != "get_gun_attr_property_value":
        return None
    names = list(map(str, code_obj.co_names))
    consts = [value for value in code_obj.co_consts if isinstance(value, str)]
    locals_ = list(map(str, code_obj.co_varnames))
    if "get_gun_omg_value" not in names or "weapon_omg_affix_value" not in consts:
        return None
    try:
        global_arg = (names.index("get_gun_omg_value") * 2) | 1
        gun_no_idx = locals_.index("gun_no")
        star_idx = locals_.index("star")
    except ValueError:
        return None
    words = _wordcode_words(code_obj)
    for i, word in enumerate(words):
        if word[1:] != (108, global_arg):
            continue
        j = i + 1
        found_gun = found_star = found_call = found_return = None
        while j < min(len(words), i + 24):
            off, op, arg = words[j]
            if op == 94 and arg == gun_no_idx and found_gun is None:
                found_gun = (off, op, arg)
            elif op == 94 and arg == star_idx and found_gun is not None and found_star is None:
                found_star = (off, op, arg)
            elif op == 172 and arg == 2 and found_star is not None and found_call is None:
                found_call = (off, op, arg)
            elif op == 122 and found_call is not None:
                found_return = (off, op, arg)
                break
            j += 1
        if found_gun and found_star and found_call and found_return:
            return {
                "status": "recognized-exact-dispatch",
                "operation": "weapon-omg-property-direct-return",
                "property_key": "weapon_omg_affix_value",
                "expression": "get_gun_omg_value(gun_no, star)",
                "raw_words": [
                    {"offset": off, "opcode": op, "arg": arg}
                    for off, op, arg in [word, found_gun, found_star, found_call, found_return]
                ],
                "opcode_mapping_evidence": {
                    "108": "LOAD_GLOBAL",
                    "94": "LOAD_FAST",
                    "172": "CALL",
                    "122": "RETURN_VALUE",
                },
            }
    return None


def _recognize_display_attack_int_conversion(code_obj: types.CodeType) -> dict | None:
    """Recognize get_weapon_base_attr_new's integer conversion of weapon OMG.

    The exact raw sequence loads built-in `int`, calls
    `shoot_utility.get_gun_attr_property_value(item_no,
    "weapon_omg_affix_value", star=star)`, then immediately CALLs `int` and
    stores the result in local `weapon_omg`.  Because the property dispatcher is
    independently recognized as a direct return of `get_gun_omg_value`, this is
    the downstream positive-Attack display conversion:

        int(get_gun_omg_value(item_no, star))

    Python `int()` truncates toward zero; for positive weapon Attack this equals
    floor.  The recognizer relies on exact metadata + raw-call ordering and does
    not use stock `dis` operation names.
    """
    if code_obj.co_name != "get_weapon_base_attr_new":
        return None
    names = list(map(str, code_obj.co_names))
    consts = list(code_obj.co_consts)
    locals_ = list(map(str, code_obj.co_varnames))
    required_names = {"int", "shoot_utility", "get_gun_attr_property_value"}
    if not required_names.issubset(set(names)) or "weapon_omg_affix_value" not in consts:
        return None
    try:
        int_global_arg = (names.index("int") * 2) | 1
        shoot_global_arg = (names.index("shoot_utility") * 2) | 1
        item_idx = locals_.index("item_no")
        star_idx = locals_.index("star")
        omg_idx = locals_.index("weapon_omg")
    except ValueError:
        return None
    words = _wordcode_words(code_obj)
    for i, first in enumerate(words):
        if first[1:] != (108, int_global_arg):
            continue
        positions = {}
        for j in range(i + 1, min(len(words), i + 48)):
            off, op, arg = words[j]
            if op == 108 and arg == shoot_global_arg and "shoot" not in positions:
                positions["shoot"] = words[j]
            elif op == 94 and arg == item_idx and "shoot" in positions and "item" not in positions:
                positions["item"] = words[j]
            elif op == 94 and arg == star_idx and "item" in positions and "star" not in positions:
                positions["star"] = words[j]
            elif op == 172 and arg == 3 and "star" in positions and "inner_call" not in positions:
                positions["inner_call"] = words[j]
            elif op == 172 and arg == 1 and "inner_call" in positions and "int_call" not in positions:
                positions["int_call"] = words[j]
            elif op == 100 and arg == omg_idx and "int_call" in positions:
                positions["store"] = words[j]
                break
        if all(k in positions for k in ("shoot", "item", "star", "inner_call", "int_call", "store")):
            return {
                "status": "recognized-exact-display-conversion",
                "operation": "int-conversion-after-weapon-omg-property",
                "expression": 'int(shoot_utility.get_gun_attr_property_value(item_no, "weapon_omg_affix_value", star=star))',
                "effective_positive_attack_rounding": "floor/truncate-toward-zero",
                "raw_words": [
                    {"offset": off, "opcode": op, "arg": arg}
                    for off, op, arg in [first] + [positions[k] for k in ("shoot", "item", "star", "inner_call", "int_call", "store")]
                ],
                "opcode_mapping_evidence": {
                    "108": "LOAD_GLOBAL",
                    "94": "LOAD_FAST",
                    "172": "CALL",
                    "100": "STORE_FAST",
                },
            }
    return None


def _recognize_rate_formatter_fraction_probe(code_obj: types.CodeType) -> dict | None:
    """Recognize the percent-only int() role inside get_affix_name_and_val2.

    v1.5.5 distinction: the final weapon-card formatter contains ``int`` but the
    stable remapped wordcode shows that call is used after multiplying the
    adjusted RATE value by 100, then subtracting the integer portion and testing
    the tiny remainder.  That branch chooses between the ``{:.0%}`` and
    ``{:.1%}`` display forms.  It is therefore *not* evidence that D0100 is
    truncated with int() at the final card-display stage.

    This recognizer is intentionally narrow and only accepts the exact metadata
    and raw-call ordering observed in the current Once Human client.  It does not
    execute game bytecode and does not trust stock Python opnames for remapped
    instructions.
    """
    if code_obj.co_name != "get_affix_name_and_val2":
        return None
    names = list(map(str, code_obj.co_names))
    locals_ = list(map(str, code_obj.co_varnames))
    consts = list(code_obj.co_consts)
    required_names = {
        "attr_const", "AP_CALC_TYPE_RATE", "adjust_affix_val", "int", "abs",
    }
    required_locals = {
        "affix_id", "raw_val", "calc_type", "affix_val", "dot3", "has_zero",
    }
    if not required_names.issubset(set(names)) or not required_locals.issubset(set(locals_)):
        return None
    if 100 not in consts or 1e-10 not in consts:
        return None
    if not {"{:.0%}", "{:.1%}"}.issubset({v for v in consts if isinstance(v, str)}):
        return None

    try:
        adjust_arg = (names.index("adjust_affix_val") * 2) | 1
        int_arg = (names.index("int") * 2) | 1
        abs_arg = (names.index("abs") * 2) | 1
        attr_const_arg = names.index("attr_const") * 2
        rate_attr_arg = names.index("AP_CALC_TYPE_RATE") * 2
        affix_id_idx = locals_.index("affix_id")
        raw_val_idx = locals_.index("raw_val")
        calc_type_idx = locals_.index("calc_type")
        affix_val_idx = locals_.index("affix_val")
        dot3_idx = locals_.index("dot3")
        has_zero_idx = locals_.index("has_zero")
        hundred_const_idxs = {i for i, v in enumerate(consts) if v == 100 and not isinstance(v, bool)}
        epsilon_const_idxs = {i for i, v in enumerate(consts) if v == 1e-10}
    except ValueError:
        return None

    words = _wordcode_words(code_obj)

    def seek(start: int, predicate, stop: int) -> int | None:
        for pos in range(start, min(len(words), stop)):
            if predicate(words[pos]):
                return pos
        return None

    for i, word in enumerate(words):
        if word[1:] != (108, adjust_arg):
            continue

        # Prove this exact block is guarded by the RATE formatter branch.
        pre = words[max(0, i - 40):i]
        has_calc_type = any(op == 94 and arg == calc_type_idx for _, op, arg in pre)
        has_attr_const = any(op == 108 and arg == attr_const_arg for _, op, arg in pre)
        has_rate_symbol_operand = any(arg == rate_attr_arg for _, _, arg in pre)
        if not (has_calc_type and has_attr_const and has_rate_symbol_operand):
            continue

        p = i + 1
        matched = []
        specs = [
            (lambda w: w[1] == 94 and w[2] == affix_id_idx, "LOAD_FAST affix_id"),
            (lambda w: w[1] == 94 and w[2] == raw_val_idx, "LOAD_FAST raw_val"),
            (lambda w: w[1] == 172 and w[2] == 2, "CALL adjust_affix_val/2"),
            (lambda w: w[1] == 100 and w[2] == raw_val_idx, "STORE_FAST raw_val"),
            (lambda w: w[1] == 94 and w[2] == raw_val_idx, "LOAD_FAST raw_val"),
            (lambda w: w[2] in hundred_const_idxs, "literal 100 operand"),
            (lambda w: w[1] == 125 and w[2] == 5, "BINARY_OP multiply"),
            (lambda w: w[1] == 100 and w[2] == affix_val_idx, "STORE_FAST affix_val"),
            (lambda w: w[1] == 108 and w[2] == int_arg, "LOAD_GLOBAL int"),
            (lambda w: w[1] == 94 and w[2] == affix_val_idx, "LOAD_FAST affix_val"),
            (lambda w: w[1] == 172 and w[2] == 1, "CALL int/1"),
            (lambda w: w[1] == 125 and w[2] == 10, "BINARY_OP subtract"),
            (lambda w: w[1] == 100 and w[2] == dot3_idx, "STORE_FAST dot3"),
            (lambda w: w[1] == 108 and w[2] == abs_arg, "LOAD_GLOBAL abs"),
            (lambda w: w[1] == 94 and w[2] == dot3_idx, "LOAD_FAST dot3"),
            (lambda w: w[1] == 172 and w[2] == 1, "CALL abs/1"),
            (lambda w: w[2] in epsilon_const_idxs, "literal epsilon operand"),
            (lambda w: w[1] == 100 and w[2] == has_zero_idx, "STORE_FAST has_zero"),
        ]
        ok = True
        for predicate, label in specs:
            found = seek(p, predicate, i + 110)
            if found is None:
                ok = False
                break
            matched.append((label, words[found]))
            p = found + 1
        if not ok:
            continue

        return {
            "status": "recognized-rate-percent-fraction-probe",
            "branch": "AP_CALC_TYPE_RATE",
            "int_role": "detect fractional percent display precision; not final D0100 truncation",
            "reconstructed_numeric_probe": (
                "adjusted_rate_percent = adjust_affix_val(affix_id, raw_val) * 100; "
                "dot3 = adjusted_rate_percent - int(adjusted_rate_percent); "
                "has_zero = abs(dot3) < 1e-10"
            ),
            "display_choice_literals": ["{:.0%}", "{:.1%}"],
            "binary_oparg_evidence": {"5": "NB_MULTIPLY (*)", "10": "NB_SUBTRACT (-)"},
            "raw_words": [
                {"label": label, "offset": off, "opcode": op, "arg": arg}
                for label, (off, op, arg) in matched
            ],
        }
    return None


def _recognize_final_affix_formatter(code_obj: types.CodeType) -> dict | None:
    """Capture formatter branch metadata without trusting remapped opnames.

    v1.5.3 intentionally stops short of assigning D0100 to a branch until the
    affix prototype / attr-constant evidence is captured. The function identity,
    co_names, co_varnames and literal format strings are stable evidence even when
    the opcode stream is remapped.
    """
    name = code_obj.co_name
    names = set(map(str, code_obj.co_names))
    vars_ = set(map(str, code_obj.co_varnames))
    const_strings = {value for value in code_obj.co_consts if isinstance(value, str)}
    const_numbers = {
        value for value in code_obj.co_consts
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }

    if name == "get_affix_name_and_val2":
        required = {
            "affix_prototype_data", "AP_CALC_TYPE_ABS", "AP_CALC_TYPE_RATE",
            "adjust_affix_val", "int", "abs", "str",
            "convert_affix_format_str", "format",
        }
        if required <= names:
            return {
                "status": "final-affix-formatter-branch-signature",
                "finding": (
                    "The weapon-card formatter reads affix_prototype_data, distinguishes "
                    "AP_CALC_TYPE_ABS from AP_CALC_TYPE_RATE, contains an int conversion, "
                    "and separately contains percent-format branches. D0100 must be bound "
                    "to its prototype calc type before promoting the final card conversion."
                ),
                "branch_symbols": ["AP_CALC_TYPE_ABS", "AP_CALC_TYPE_RATE"],
                "conversion_symbols": sorted({"int", "abs", "str", "format"} & names),
                "percentage_format_literals": sorted(
                    value for value in const_strings if value in {"{:.1%}", "{:.0%}"}
                ),
                "numeric_literals": sorted(const_numbers),
                "locals": sorted(vars_),
                "rate_fraction_probe": _recognize_rate_formatter_fraction_probe(code_obj),
            }

    if name == "get_format_attr_val":
        required = {
            "affix_prototype_data", "ATTR_VAL_ABS", "ATTR_VAL_RATE",
            "char_property_data", "int", "round",
        }
        if required <= names:
            return {
                "status": "attribute-value-type-formatter-signature",
                "finding": (
                    "The generic attribute formatter distinguishes ATTR_VAL_ABS and "
                    "ATTR_VAL_RATE and contains separate int/round conversion tools. "
                    "This is supporting evidence for value-type-dependent formatting, "
                    "not by itself proof of the D0100 branch."
                ),
                "branch_symbols": ["ATTR_VAL_ABS", "ATTR_VAL_RATE"],
                "conversion_symbols": sorted({"int", "round"} & names),
                "numeric_literals": sorted(const_numbers),
                "locals": sorted(vars_),
            }

    filename = str(code_obj.co_filename).replace("\\", "/").lower()
    if filename.endswith("attr_const.py") and (
        {"AP_CALC_TYPE_ABS", "AP_CALC_TYPE_RATE"} <= names
        or {"ATTR_VAL_ABS", "ATTR_VAL_RATE"} <= names
    ):
        return {
            "status": "attr-constant-definition-module-target",
            "finding": (
                "This module defines the formatter branch constants. Preserve its code "
                "capsule so the numeric ABS/RATE constant mapping can be recovered statically."
            ),
            "symbols": sorted(
                {"AP_CALC_TYPE_ABS", "AP_CALC_TYPE_RATE", "ATTR_VAL_ABS", "ATTR_VAL_RATE"} & names
            ),
            "numeric_literals": sorted(const_numbers),
        }

    return None


def _known_display_semantics(code_obj: types.CodeType) -> dict:
    return {
        "weapon_omg_property_dispatch": _recognize_weapon_omg_property_dispatch(code_obj),
        "display_attack_int_conversion": _recognize_display_attack_int_conversion(code_obj),
        "final_affix_formatter": _recognize_final_affix_formatter(code_obj),
    }




def _known_calibration_semantics(code_obj: types.CodeType) -> dict | None:
    """Recognize calibration RNG / Attack-ratio signatures that survive opcode remapping.

    This is intentionally narrow. It uses function identity plus co_names/co_varnames/
    constants and, where useful, preserved BINARY_OP arguments. It never executes
    game bytecode and does not treat stock disassembly opnames as authoritative.
    """
    name = code_obj.co_name
    names = set(map(str, code_obj.co_names))
    vars_ = set(map(str, code_obj.co_varnames))
    const_strings = {value for value in code_obj.co_consts if isinstance(value, str)}
    const_numbers = {value for value in code_obj.co_consts if isinstance(value, (int, float)) and not isinstance(value, bool)}
    words = _wordcode_words(code_obj)

    if name == "generate_correct_print_term_id":
        required_names = {"sum", "random", "uniform", "range", "len"}
        required_vars = {"term_ids", "affix_ids_weight", "total_weight", "rand_num", "weight_sum", "i"}
        if required_names <= names and required_vars <= vars_ and {"affix_ids", "affix_ids_weight"} <= const_strings:
            return {
                "status": "weighted-single-term-selection-signature",
                "finding": "A single term_id is selected from affix_ids using affix_ids_weight and cumulative random weighting.",
                "algorithm": [
                    "total_weight = sum(affix_ids_weight)",
                    "rand_num = random.uniform(0, total_weight)",
                    "iterate term_ids while accumulating affix_ids_weight",
                    "select one term_id when cumulative weight reaches the roll",
                ],
                "evidence": {
                    "co_names": sorted(required_names),
                    "co_varnames": sorted(required_vars),
                    "source_fields": ["affix_ids", "affix_ids_weight"],
                },
            }

    if name == "generate_gun_correct_print_info":
        required_names = {"generate_correct_print_term_id", "generate_correct_term_data", "round", "random", "uniform", "len"}
        required_vars = {"term_id", "affix_val_range", "affix_val", "info"}
        if required_names <= names and required_vars <= vars_ and {"affix_val_range", "gun_correct_affix_val"} <= const_strings and {2, 3} <= const_numbers:
            return {
                "status": "calibration-roll-generation-signature",
                "finding": "The dropped calibration generates one weighted term and one numeric gun_correct_affix_val from affix_val_range.",
                "roll_expression": "round(random.uniform(affix_val_range[0], affix_val_range[1]), 3)",
                "ui_precision_implication": "raw fraction precision 0.001 = 0.1 percentage-point increments",
                "term_selection_call": "generate_correct_print_term_id(print_id)",
                "term_materialization_call": "generate_correct_term_data(term_id)",
            }

    if name == "convert_gun_correct_affix_val_to_affix_list":
        if "gen_rand_gun_affixs" in names and {"gun_correct_affix_val", "gun_affix_list", "affix"} <= vars_ and "affix_val" in const_strings:
            return {
                "status": "calibration-roll-injection-signature",
                "finding": "The calibration roll is injected into the generated gun affix list under affix_val.",
                "source_value": "gun_correct_affix_val",
                "target_field": "affix_val",
                "generated_affix_source": "gen_rand_gun_affixs(item_no, star)",
            }

    if name == "get_gun_attack_guncore":
        if {"attack_radio", "attr_radio_affix_ids", "affix_id", "affix_val"} <= vars_ and {"D0100", "D0101", "D0102"} <= const_strings:
            binary_args = [arg for _, op, arg in words if op == 125]
            formula_signature = "delta_attack" in vars_ and all(op in binary_args for op in (13, 10, 5, 0))
            return {
                "status": (
                    "guncore-static-attack-formula-signature"
                    if formula_signature
                    else "attack-ratio-bucket-signature"
                ),
                "finding": (
                    "D0101 and D0102 are handled as additive Attack-ratio affixes. "
                    "When the delta_attack path is present, the preserved operator sequence "
                    "matches base D0100 * attack_radio + delta_attack."
                ),
                "base_attack_affix_id": "D0100",
                "attack_ratio_affix_ids": ["D0101", "D0102"],
                "binary_opargs_seen": binary_args,
                "formula_signature": {
                    "attack_radio": "1.0 + sum(active D0101/D0102 values)",
                    "combined_attack": "base D0100 * attack_radio + delta_attack",
                } if formula_signature else None,
                "binary_oparg_semantics": {
                    "13": "in-place add (+=) in the captured ratio accumulator",
                    "10": "subtract (-) used to isolate delta_attack",
                    "5": "multiply (*) in the captured base-Attack scaling path",
                    "0": "add (+) used after ratio scaling",
                },
            }

    if name == "get_gun_base_affix_add":
        if {"attack_radio", "attr_radio_affix_ids", "item_attack_base", "affix_val"} <= vars_ and {"D0100", "D0101", "D0102"} <= const_strings:
            binary_args = [arg for _, op, arg in words if op == 125]
            base_formula_signature = 5 in binary_args and 13 in binary_args
            return {
                "status": (
                    "base-affix-item-attack-scaling-signature"
                    if base_formula_signature
                    else "base-affix-attack-ratio-signature"
                ),
                "finding": (
                    "The base weapon affix builder recognizes D0101/D0102 as Attack-ratio IDs "
                    "and its preserved multiply/accumulate sequence scales item_attack_base by attack_radio "
                    "before contributing the result to D0100."
                ),
                "base_attack_affix_id": "D0100",
                "attack_ratio_affix_ids": ["D0101", "D0102"],
                "binary_opargs_seen": binary_args,
                "formula_signature": (
                    "D0100 contribution += item_attack_base * attack_radio"
                    if base_formula_signature else None
                ),
            }

    if name == "generate_correct_term_data":
        required_names = {"round", "random", "uniform", "enumerate"}
        required_vars = {"term_id", "terms", "term_data", "affix_val", "affix_id", "term_affix_list_value", "ret"}
        if required_names <= names and required_vars <= vars_ and {"min_val", "max_val", "affix_ids", "affix_val"} <= const_strings and 3 in const_numbers:
            return {
                "status": "selected-calibration-term-roll-signature",
                "finding": "After one weighted calibration term is selected, the client materializes its term data and rolls each non-empty term value from that term's min_val/max_val with 0.001 raw precision.",
                "roll_expression": "round(random.uniform(min_val, max_val), 3)",
                "output_semantics": "selected term -> generated affix entry/list; this is separate from gun_correct_affix_val",
            }

    if name == "get_gun_calibration_affix_option_size":
        required_names = {"enumerate", "reversed", "len"}
        required_vars = {"lv", "calibration_option_gun", "option_size", "i", "level_limit"}
        if required_names <= names and required_vars <= vars_ and "calibration_option_gun" in const_strings:
            return {
                "status": "weapon-calibration-option-level-gates-signature",
                "finding": "calibration_option_gun is consumed as level_limit thresholds to compute option_size from weapon calibration level lv. This is a separate system from the dropped blueprint's gun_correct_affix_list.",
                "current_global_value_reported_elsewhere": "see calibration-investigation.raw_global_calibration_params.calibration_option_gun",
            }

    if name == "get_gun_affix_option_add":
        if {"affix_options", "affix_option_libs", "affix_option", "affixes", "affix_value"} <= vars_ and "gun_calibration_affix_option_data" in const_strings:
            return {
                "status": "weapon-calibration-option-stat-source-signature",
                "finding": "Weapon affix_options are resolved through gun_calibration_affix_option_data into stat additions. This path is distinct from gun_correct_affix_list / Calibration Blueprint drop-term data.",
                "source_field": "item_detail.affix_options",
                "source_table": "gun_calibration_affix_option_data",
            }

    if name == "get_gun_correct_affix_add":
        if {"gun_correct_affix_list", "affix_add", "gun_affix", "affix_id", "affix_val"} <= vars_ and "gun_correct_affix_list" in const_strings:
            return {
                "status": "calibration-blueprint-random-term-stat-source-signature",
                "finding": "The Calibration Blueprint's stored gun_correct_affix_list is converted into an affix_add dictionary from affix_id/affix_val pairs.",
                "source_field": "gun_correct_affix_list",
                "output": "affix_add",
            }

    if name in {"get_gun_affix_add", "get_gun_calc_affix_add"}:
        source_vars = [
            key for key in (
                "base_affix_add", "accessory_affix_add", "rand_affix_add",
                "affix_option_add", "cal_affix", "correct_affix_add"
            )
            if key in vars_
        ]
        if {"affix_add_dict", "attack_radio", "attr_radio_affix_ids", "affix_id", "affix_val", "delta_attack"} <= vars_ and {"D0100", "D0101", "D0102"} <= const_strings:
            binary_args = [arg for _, op, arg in words if op == 125]
            formula_signature = all(op in binary_args for op in (10, 5, 0))
            return {
                "status": (
                    "combined-weapon-attack-formula-signature"
                    if formula_signature
                    else "combined-weapon-attack-affix-bucket-signature"
                ),
                "finding": (
                    "The final weapon-affix aggregation path combines multiple affix sources. "
                    "D0101/D0102 feed one additive Attack-ratio accumulator around D0100. "
                    "The preserved raw operator sequence then isolates delta_attack with subtraction "
                    "and applies multiply followed by add, matching base_attack * attack_radio + delta_attack."
                ),
                "affix_sources_present": source_vars,
                "base_attack_affix_id": "D0100",
                "attack_ratio_affix_ids": ["D0101", "D0102"],
                "binary_opargs_seen": binary_args,
                "formula_signature": {
                    "attack_radio": "1.0 + sum(active D0101/D0102 values)",
                    "delta_attack": "combined D0100 contribution minus base D0100 contribution",
                    "combined_attack": "base D0100 * attack_radio + delta_attack",
                    "operator_evidence": {
                        "13": "+= ratio accumulation",
                        "10": "subtract to isolate delta_attack",
                        "5": "multiply base Attack by attack_radio",
                        "0": "add delta_attack after ratio scaling",
                    },
                } if formula_signature else None,
                "important_implication": "Calibration D0102 is one additive member of a shared Attack-ratio bucket; D0101/D0102 sources combine before multiplying base Attack, while flat D0100 delta is added afterward.",
            }

    return None


def _known_weapon_aggregator_semantics(code_obj: types.CodeType) -> dict | None:
    """Recognize the static weapon-card aggregation architecture.

    This deliberately uses function identity, argument/local names and constants
    that survive Once Human's opcode remapping. It does not execute game code.
    """
    name = code_obj.co_name
    names = set(map(str, code_obj.co_names))
    vars_ = set(map(str, code_obj.co_varnames))
    const_strings = {value for value in code_obj.co_consts if isinstance(value, str)}
    words = _wordcode_words(code_obj)

    if name == "get_gun_affix_add":
        source_args = [
            key for key in (
                "base_affix_add", "accessory_affix_add", "rand_affix_add",
                "affix_option_add", "cal_affix", "correct_affix_add",
            ) if key in vars_
        ]
        if len(source_args) >= 6 and {"affix_add_dict", "attack_radio", "delta_attack"} <= vars_:
            return {
                "status": "six-source-static-weapon-affix-aggregator-signature",
                "finding": "The normal weapon-card aggregator accepts six distinct stat-input dictionaries before producing the combined weapon affix dictionary.",
                "input_sources": source_args,
                "source_roles": {
                    "base_affix_add": "intrinsic/base weapon affixes",
                    "accessory_affix_add": "equipped weapon accessories/attachments",
                    "rand_affix_add": "random weapon affix contribution",
                    "affix_option_add": "weapon calibration +7/+10 option contribution",
                    "cal_affix": "weapon calibration-level contribution",
                    "correct_affix_add": "Calibration Blueprint / gun_correct contribution",
                },
                "attack_bucket": {
                    "base_flat_id": "D0100",
                    "ratio_ids": ["D0101", "D0102"],
                    "delta_local": "delta_attack",
                    "ratio_expression": "1.0 + sum(active D0101/D0102 values)",
                    "final_static_expression": "base D0100 * attack_radio + delta_attack",
                    "flat_delta_semantics": "non-base/extra D0100 contribution is added after ratio scaling",
                },
                "special_stat_ids_present": sorted({"Q0800", "Q0900"} & const_strings),
                "binary_opargs_seen": [arg for _, op, arg in words if op == 125],
            }

    if name == "get_gun_calc_affix_add":
        source_args = [
            key for key in (
                "base_affix_add", "accessory_affix_add", "rand_affix_add",
                "affix_option_add", "correct_affix_add",
            ) if key in vars_
        ]
        if len(source_args) >= 5 and {"affix_add_dict", "attack_radio", "delta_attack"} <= vars_:
            return {
                "status": "calculation-affix-aggregator-signature",
                "finding": "A calculation-oriented weapon aggregator combines base, accessory, random, +7/+10 option, and Calibration Blueprint affix dictionaries; it is separate from the normal path that also accepts cal_affix.",
                "input_sources": source_args,
                "attack_bucket": {
                    "base_flat_id": "D0100",
                    "ratio_ids": ["D0101", "D0102"],
                    "ratio_expression": "1.0 + sum(active D0101/D0102 values)",
                    "final_static_expression": "base D0100 * attack_radio + delta_attack",
                },
            }

    if name in {"get_gun_accessory_affix_add", "get_gun_calc_accessory_affix_add"}:
        return {
            "status": "weapon-accessory-stat-producer-target",
            "finding": "This helper is a direct producer for the accessory_affix_add input consumed by the weapon-card aggregator.",
            "co_names": sorted(names),
            "co_varnames": list(code_obj.co_varnames),
        }

    if name in {"get_gun_rand_attr_affix_add", "get_gun_no_rand_affix_add", "get_gun_rand_attr"}:
        return {
            "status": "weapon-random-affix-producer-target",
            "finding": "This helper participates in producing or reading the rand_affix_add input consumed by the weapon-card aggregator.",
            "co_names": sorted(names),
            "co_varnames": list(code_obj.co_varnames),
        }

    if name == "get_all_guncore_affix_add":
        return {
            "status": "guncore-affix-source-collector-target",
            "finding": "This helper is a high-value collector immediately upstream of the combined weapon-card affix pipeline.",
            "co_names": sorted(names),
            "co_varnames": list(code_obj.co_varnames),
        }

    if name in {"get_equipped_accessorys", "get_gun_accessory_list", "get_gun_slot_accessory_data_list"}:
        return {
            "status": "equipped-accessory-selection-target",
            "finding": "This helper participates in resolving which accessory records are equipped before accessory stat aggregation.",
            "co_names": sorted(names),
            "co_varnames": list(code_obj.co_varnames),
        }

    return None


def _metadata_semantics(code_obj: types.CodeType) -> dict:
    """Extract semantics that survive the client's opcode remapping."""
    names = set(map(str, code_obj.co_names))
    const_strings = {value for value in code_obj.co_consts if isinstance(value, str)}
    chain_calls = sorted(set(PYC_CHAIN_SYMBOLS) & names)
    rounding_names = sorted(PYC_ROUNDING_NAMES & names)
    progression_names = sorted(set(PYC_TARGETS) & (names | const_strings))
    display_targets = sorted(set(PYC_DISPLAY_TARGETS) & (names | const_strings))
    calibration_targets = sorted(set(PYC_CALIBRATION_TARGETS) & (names | const_strings))
    weapon_aggregator_targets = sorted(set(PYC_WEAPON_AGGREGATOR_TARGETS) & (names | const_strings))
    format_strings = sorted({
        value for value in const_strings
        if any(marker in value for marker in ("%.0f", "%d", "%i", ":.0f", ":d", "{:.0f}", "{:d}"))
    })
    return {
        "chain_symbols_in_co_names": chain_calls,
        "rounding_or_format_names_in_co_names": rounding_names,
        "progression_symbols_in_metadata": progression_names,
        "display_stat_ids_in_metadata": display_targets,
        "calibration_symbols_in_metadata": calibration_targets,
        "weapon_aggregator_symbols_in_metadata": weapon_aggregator_targets,
        "integer_format_strings_in_metadata": format_strings[:80],
        "known_obfuscated_tail": _known_obfuscated_tail(code_obj),
        "known_display_semantics": _known_display_semantics(code_obj),
        "known_calibration_semantics": _known_calibration_semantics(code_obj),
        "known_weapon_aggregator_semantics": _known_weapon_aggregator_semantics(code_obj),
    }


def _serialise_instructions(instructions: list, limit: int = 2000) -> list[dict]:
    rows = []
    for ins in instructions[:limit]:
        argval = ins.argval
        if not isinstance(argval, (str, int, float, bool, type(None))):
            argval = repr(argval)
        rows.append({
            "offset": ins.offset,
            "opcode": ins.opcode,
            "opname": ins.opname,
            "arg": ins.arg,
            "argrepr": ins.argrepr,
            "argval": argval,
        })
    return rows


def _padded_disassembly(code_obj: types.CodeType) -> tuple[list | None, str | None]:
    """Best-effort disassembly for malformed/cross-version name indexes.

    Padding co_names/co_consts prevents stdlib `dis` from aborting solely on an
    out-of-range metadata lookup.  This output is diagnostic only and is always
    paired with raw opcode numbers; it is never treated as proof by itself.
    """
    try:
        padded_names = tuple(code_obj.co_names) + tuple(f"<pad_name_{i}>" for i in range(4096))
        padded_consts = tuple(code_obj.co_consts) + (None,) * 4096
        clone = code_obj.replace(co_names=padded_names, co_consts=padded_consts)
        return list(dis.get_instructions(clone, show_caches=True)), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _inspect_compatible_code(raw: bytes) -> dict:
    result = {
        "marshal_compatible": False,
        "code_hits": [],
        "error": None,
        "pyc_magic_hex": raw[:4].hex() if len(raw) >= 4 else "",
        "pyc_header_hex": raw[:16].hex() if len(raw) >= 16 else raw.hex(),
        "miner_runtime": sys.version,
    }
    try:
        code = marshal.loads(raw[16:])
        if not isinstance(code, types.CodeType):
            result["error"] = "marshal payload was not a CodeType"
            return result
        result["marshal_compatible"] = True
        code_objects = list(_walk_code_objects(code))
        # Once Human preserves marshal/code-object metadata but remaps bytecode
        # opcode numbers. A stdlib disassembly can therefore *appear* valid while
        # assigning the wrong operation names (for example opcode 122 is proven
        # RETURN_VALUE in this client although stock 3.11 labels it BINARY_OP).
        # Detect the profile from any exact known progression tail in the PYC and
        # never promote stock-disassembly arithmetic to evidence when present.
        opcode_remapping_detected = any(_known_obfuscated_tail(obj) for _, obj in code_objects)
        result["opcode_remapping_detected"] = opcode_remapping_detected
        for qualname, code_obj in code_objects:
            names = set(map(str, code_obj.co_names))
            constants = {value for value in code_obj.co_consts if isinstance(value, str)}
            hits = sorted({target for target in PYC_TARGETS if target in names or target in constants})
            display_hits = sorted({target for target in PYC_DISPLAY_TARGETS if target in names or target in constants})
            calibration_hits = sorted({target for target in PYC_CALIBRATION_TARGETS if target in names or target in constants})
            aggregator_hits = sorted({target for target in PYC_WEAPON_AGGREGATOR_TARGETS if target in names or target in constants})
            chain_hits = sorted({target for target in PYC_CHAIN_SYMBOLS if target in names or target in constants})
            filename_norm = str(code_obj.co_filename).replace("\\", "/").lower()
            attr_const_focus = (
                filename_norm.endswith("attr_const.py")
                and bool({"AP_CALC_TYPE_ABS", "AP_CALC_TYPE_RATE", "ATTR_VAL_ABS", "ATTR_VAL_RATE"} & (names | constants))
            )
            focus = code_obj.co_name in PYC_FOCUS_FUNCTIONS or attr_const_focus
            caller = bool(chain_hits)
            if not hits and not display_hits and not calibration_hits and not aggregator_hits and not focus and not caller:
                continue

            metadata_semantics = _metadata_semantics(code_obj)
            base_row = {
                "qualname": qualname,
                "filename": code_obj.co_filename,
                "targets": hits,
                "display_targets": display_hits,
                "calibration_targets": calibration_hits,
                "weapon_aggregator_targets": aggregator_hits,
                "chain_targets": chain_hits,
                "focus_function": focus,
                "focus_layer": (
                    "progression" if code_obj.co_name in PYC_PROGRESSION_FUNCTIONS
                    else "display" if code_obj.co_name in PYC_DISPLAY_FUNCTIONS
                    else "calibration" if code_obj.co_name in PYC_CALIBRATION_FUNCTIONS
                    else "weapon_aggregator" if code_obj.co_name in PYC_WEAPON_AGGREGATOR_FUNCTIONS
                    else "display_constants" if attr_const_focus
                    else None
                ),
                "caller_of_progression_chain": caller,
                "co_names": sorted(names)[:600],
                "metadata_semantics": metadata_semantics,
            }
            try:
                instructions = list(dis.get_instructions(code_obj, show_caches=True))
            except Exception as exc:
                padded, padded_error = _padded_disassembly(code_obj)
                row = dict(base_row)
                row.update({
                    "score": (len(hits) * 20) + (len(display_hits) * 25) + (len(calibration_hits) * 25) + (len(aggregator_hits) * 25) + (len(chain_hits) * 30) + (80 if focus else 0)
                             + (25 if metadata_semantics.get("rounding_or_format_names_in_co_names") else 0),
                    "disassembly_error": f"{type(exc).__name__}: {exc}",
                    "code_capsule": _code_capsule(code_obj),
                    "raw_wordcode": _raw_wordcode(code_obj),
                    "padded_disassembly_warning": "Diagnostic only: metadata was padded after stdlib disassembly failed; raw opcode numbers remain authoritative.",
                    "padded_disassembly_error": padded_error,
                    "padded_disassembly": _serialise_instructions(padded, 2000) if padded else [],
                })
                result["code_hits"].append(row)
                continue

            windows = []
            arithmetic_ops = set()
            # co_names metadata remains trustworthy under opcode remapping.
            rounding_names = set(metadata_semantics.get("rounding_or_format_names_in_co_names", []))
            window_symbols = tuple(dict.fromkeys(hits + display_hits + calibration_hits + chain_hits))
            for index, ins in enumerate(instructions):
                text = str(ins.argval)
                target = next((target for target in window_symbols if target == text), None)
                if target is not None:
                    window = _instruction_window(instructions, index, radius=32 if focus else 20)
                    # Instruction windows are preserved diagnostically. Arithmetic
                    # names are used only for non-remapped bytecode.
                    if not opcode_remapping_detected:
                        for winrow in window:
                            if winrow["opname"] in {
                                "BINARY_OP", "BINARY_MULTIPLY", "BINARY_ADD", "BINARY_SUBTRACT",
                                "CALL", "CALL_FUNCTION", "CALL_METHOD", "PRECALL",
                            }:
                                arithmetic_ops.add(f"{winrow['opname']} {winrow['argrepr']}".strip())
                    windows.append({"target": target, "instruction_index": index, "instructions": window})
            if focus and not opcode_remapping_detected:
                for ins in instructions:
                    if ins.opname in {
                        "BINARY_OP", "BINARY_MULTIPLY", "BINARY_ADD", "BINARY_SUBTRACT",
                        "CALL", "CALL_FUNCTION", "CALL_METHOD", "PRECALL",
                    }:
                        arithmetic_ops.add(f"{ins.opname} {ins.argrepr}".strip())
            score = (len(hits) * 20 + len(display_hits) * 25 + len(calibration_hits) * 25 + len(chain_hits) * 30 + len(windows) * 5
                     + len(arithmetic_ops) * 8 + len(rounding_names) * 12 + (80 if focus else 0)
                     + (25 if metadata_semantics.get("rounding_or_format_names_in_co_names") else 0))
            row = dict(base_row)
            row.update({
                "score": score,
                "arithmetic_ops_near_target": sorted(arithmetic_ops),
                "rounding_names_near_target": sorted(rounding_names),
                "windows": windows[:20],
                "stock_disassembly_authoritative": not opcode_remapping_detected,
                "stock_disassembly_warning": (
                    "Diagnostic only: this PYC contains the proven Once Human opcode-remapping profile; operation names from stock dis are not evidence."
                    if opcode_remapping_detected else None
                ),
            })
            if focus or caller:
                row["full_disassembly"] = _serialise_instructions(instructions, 3000)
                row["code_capsule"] = _code_capsule(code_obj)
            result["code_hits"].append(row)
        result["code_hits"].sort(key=lambda row: -int(row.get("score") or 0))
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result

def scan_pyc_consumers(base: Path, current: Path, max_candidates: int = 500) -> dict:
    """Collect persisted and live PYC evidence for progression consumers.

    `export_bindict.py` now writes pyc-progression-symbols.json while extracted
    PYC files are guaranteed to exist. This pass consumes those stable indexes
    and also rescans the live source_root when it is still available.
    """
    persisted_indexes = []
    candidates = []
    candidate_keys = set()

    for layer, root in (("base", base), ("current", current)):
        index_path = root / "pyc-progression-symbols.json"
        payload = read_json(index_path, {})
        if not isinstance(payload, dict) or not payload.get("candidates"):
            continue
        persisted_indexes.append({
            "layer": layer,
            "path": str(index_path),
            "scanned_pyc_files": payload.get("scanned_pyc_files", 0),
            "candidate_files": payload.get("candidate_files", 0),
            "consumer_candidate_files": payload.get("consumer_candidate_files", 0),
            "arithmetic_or_rounding_candidate_files": payload.get("arithmetic_or_rounding_candidate_files", 0),
        })
        for row in payload.get("candidates", []):
            if not isinstance(row, dict):
                continue
            merged = dict(row)
            merged["layer"] = layer
            merged["evidence_source"] = "persisted-export-index"
            key = (layer, str(merged.get("pyc")), tuple(merged.get("targets", [])))
            if key in candidate_keys:
                continue
            candidate_keys.add(key)
            candidates.append(merged)

    roots = []
    for layer, snapshot in (("base", base / "snapshot.json"), ("current", current / "snapshot.json")):
        source_root = _snapshot_source_root(snapshot)
        if source_root is not None:
            roots.append((layer, source_root))

    scanned_files_live = 0
    scanned_bytes_live = 0
    seen_paths = set()
    for layer, root in roots:
        for path in root.rglob("*.pyc"):
            key_path = str(path.resolve()).casefold()
            if key_path in seen_paths:
                continue
            seen_paths.add(key_path)
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            scanned_files_live += 1
            scanned_bytes_live += len(raw)
            hits = []
            offsets = {}
            for target in PYC_SCAN_SYMBOLS:
                token = target.encode("ascii")
                positions = []
                start = 0
                while len(positions) < 8:
                    found = raw.find(token, start)
                    if found < 0:
                        break
                    positions.append(found)
                    start = found + 1
                if positions:
                    hits.append(target)
                    offsets[target] = positions
            if not hits:
                continue

            rel = str(path.relative_to(root)).replace("\\", "/")
            table_definition = bool(re.search(r"(?:gun_blueprint_attr_data|equip_origin_data|gun_blueprint_data)\.pyc$", rel, re.IGNORECASE))
            contexts = {target: _ascii_context(raw, positions[0]) for target, positions in offsets.items()}
            code = _inspect_compatible_code(raw)
            best_code_score = max((int(row.get("score") or 0) for row in code.get("code_hits", [])), default=0)
            score = len(hits) * 15 + best_code_score - (25 if table_definition else 0)
            if "preset_attack_radio" in hits:
                score += 25
            if "gun_preset_attack" in hits:
                score += 20
            if "strength_lv" in hits:
                score += 15
            if "affix_val_range" in hits:
                score += 35
            if any(target in hits for target in ("gun_correct_print_data", "gun_calibration_affix_option_data")):
                score += 20
            merged = {
                "score": score,
                "layer": layer,
                "source_root": str(root),
                "pyc": rel,
                "absolute_path": str(path),
                "targets": hits,
                "target_offsets": offsets,
                "classification": "table-definition" if table_definition else "consumer-candidate",
                "ascii_context": contexts,
                "code_object_inspection": code,
                "evidence_source": "live-source-root-scan",
            }
            key = (layer, rel, tuple(hits))
            if key in candidate_keys:
                # Prefer the live copy because it carries the absolute path.
                for index, existing in enumerate(candidates):
                    if (existing.get("layer"), str(existing.get("pyc")), tuple(existing.get("targets", []))) == key:
                        candidates[index] = merged
                        break
            else:
                candidate_keys.add(key)
                candidates.append(merged)

    candidates.sort(key=lambda row: (-int(row.get("score") or 0), row.get("classification", ""), row.get("pyc", "")))
    consumer_candidates = [row for row in candidates if row.get("classification") == "consumer-candidate"]
    arithmetic_candidates = [
        row for row in consumer_candidates
        if any(
            hit.get("arithmetic_ops_near_target") or hit.get("rounding_names_near_target")
            for hit in row.get("code_object_inspection", {}).get("code_hits", [])
        )
    ]
    caller_functions = []
    for row in consumer_candidates:
        for hit in row.get("code_object_inspection", {}).get("code_hits", []):
            if not hit.get("caller_of_progression_chain"):
                continue
            semantics = hit.get("metadata_semantics", {}) or {}
            caller_functions.append({
                "layer": row.get("layer"),
                "pyc": row.get("pyc"),
                "qualname": hit.get("qualname"),
                "chain_targets": hit.get("chain_targets", []),
                "rounding_or_format_names_in_co_names": semantics.get("rounding_or_format_names_in_co_names", []),
                "known_obfuscated_tail": semantics.get("known_obfuscated_tail"),
                "known_display_semantics": semantics.get("known_display_semantics", {}),
                "disassembly_error": hit.get("disassembly_error"),
                "has_code_capsule": bool(hit.get("code_capsule")),
                "metadata_semantics": hit.get("metadata_semantics", {}),
            })
    caller_functions.sort(key=lambda row: (-len(row.get("rounding_or_format_names_in_co_names", [])), str(row.get("pyc")), str(row.get("qualname"))))

    focus_functions = []
    for row in consumer_candidates:
        for hit in row.get("code_object_inspection", {}).get("code_hits", []):
            if not hit.get("focus_function"):
                continue
            focus_functions.append({
                "layer": row.get("layer"),
                "pyc": row.get("pyc"),
                "qualname": hit.get("qualname"),
                "focus_layer": hit.get("focus_layer"),
                "targets": hit.get("targets", []),
                "display_targets": hit.get("display_targets", []),
                "calibration_targets": hit.get("calibration_targets", []),
                "weapon_aggregator_targets": hit.get("weapon_aggregator_targets", []),
                "chain_targets": hit.get("chain_targets", []),
                "disassembly_error": hit.get("disassembly_error"),
                "rounding_names_near_target": hit.get("rounding_names_near_target", []),
                "arithmetic_ops_near_target": hit.get("arithmetic_ops_near_target", []),
                "stock_disassembly_authoritative": hit.get("stock_disassembly_authoritative"),
                "has_full_disassembly": bool(hit.get("full_disassembly")),
                "has_code_capsule": bool(hit.get("code_capsule")),
                "metadata_semantics": hit.get("metadata_semantics", {}),
            })
    focus_functions.sort(key=lambda row: (str(row.get("pyc")), str(row.get("qualname")), str(row.get("layer"))))

    persisted_scanned = max((int(row.get("scanned_pyc_files") or 0) for row in persisted_indexes), default=0)
    return {
        "persisted_symbol_indexes": persisted_indexes,
        "source_roots": [{"layer": layer, "path": str(root)} for layer, root in roots],
        "source_roots_available": bool(roots),
        "persisted_indexes_available": bool(persisted_indexes),
        "scanned_pyc_files": max(persisted_scanned, scanned_files_live),
        "live_scanned_pyc_files": scanned_files_live,
        "live_scanned_bytes": scanned_bytes_live,
        "candidate_files": len(candidates),
        "consumer_candidate_files": len(consumer_candidates),
        "arithmetic_or_rounding_candidate_files": len(arithmetic_candidates),
        "focus_function_count": len(focus_functions),
        "progression_focus_function_count": sum(row.get("focus_layer") == "progression" for row in focus_functions),
        "display_focus_function_count": sum(row.get("focus_layer") == "display" for row in focus_functions),
        "calibration_focus_function_count": sum(row.get("focus_layer") == "calibration" for row in focus_functions),
        "weapon_aggregator_focus_function_count": sum(row.get("focus_layer") == "weapon_aggregator" for row in focus_functions),
        "display_focus_with_rounding_or_format_names": sum(
            row.get("focus_layer") == "display" and bool((row.get("metadata_semantics") or {}).get("rounding_or_format_names_in_co_names"))
            for row in focus_functions
        ),
        "focus_disassembly_failures": sum(bool(row.get("disassembly_error")) for row in focus_functions),
        "focus_functions": focus_functions,
        "caller_function_count": len(caller_functions),
        "callers_with_rounding_or_format_names": sum(bool(row.get("rounding_or_format_names_in_co_names")) for row in caller_functions),
        "caller_functions": caller_functions[:500],
        "top_candidates": candidates[:max_candidates],
    }


def formula_assessment(tier: dict, blueprint: dict, pyc_scan: dict | None = None) -> dict:
    tier_universal = {}
    for tier_no, modes in tier.get("universal_factor_candidates", {}).items():
        tier_universal[tier_no] = [row for row in modes if row.get("compatible")]
    legacy_attr_candidates = attack_star_candidates(blueprint)
    combined_candidates = combined_star_tier_candidates(tier, blueprint)
    ratio_evidence = blueprint.get("preset_attack_ratio_evidence", {})
    star_structure = blueprint.get("raw_level_star_hypothesis", {})
    direct_ratio = bool(ratio_evidence.get("rows")) and ratio_evidence.get("coverage_of_strength_rows") == 1.0
    strength_exact = star_structure.get("tuple_level_matches_strength_lv_rate") == 1.0
    pyc_scan = pyc_scan or {}
    consumer_count = int(pyc_scan.get("consumer_candidate_files") or 0)
    arithmetic_count = int(pyc_scan.get("arithmetic_or_rounding_candidate_files") or 0)
    focus_functions = pyc_scan.get("focus_functions", []) or []
    multiply_consumers = [
        row for row in focus_functions
        if ((row.get("metadata_semantics") or {}).get("known_obfuscated_tail") or {}).get("operation") == "multiply-return"
    ]
    direct_ratio_returns = [
        row for row in focus_functions
        if ((row.get("metadata_semantics") or {}).get("known_obfuscated_tail") or {}).get("operation") == "direct-return"
    ]
    caller_count = int(pyc_scan.get("caller_function_count") or 0)
    caller_rounding_count = int(pyc_scan.get("callers_with_rounding_or_format_names") or 0)
    display_focus = [row for row in focus_functions if row.get("focus_layer") == "display"]
    display_rounding = [
        row for row in display_focus
        if (row.get("metadata_semantics") or {}).get("rounding_or_format_names_in_co_names")
        or (row.get("metadata_semantics") or {}).get("integer_format_strings_in_metadata")
    ]
    display_int_conversions = []
    weapon_omg_dispatchers = []
    semantic_rows = list(focus_functions) + list(pyc_scan.get("caller_functions", []) or [])
    for row in semantic_rows:
        semantics = row.get("metadata_semantics", {}) or {}
        known_display = semantics.get("known_display_semantics", {}) or {}
        int_conversion = known_display.get("display_attack_int_conversion")
        property_dispatch = known_display.get("weapon_omg_property_dispatch")
        if int_conversion:
            display_int_conversions.append({"row": row, "evidence": int_conversion})
        if property_dispatch:
            weapon_omg_dispatchers.append({"row": row, "evidence": property_dispatch})

    status = "unresolved"
    findings = []
    if tier_universal and all(tier_universal.get(str(tier_no)) for tier_no in range(1, 6)):
        findings.append("A single Tier factor is compatible with all observed weapon Tier damage rows under at least one tested integer-rounding rule.")
    else:
        findings.append("Tier I-V attack is available directly per weapon from gun_preset_attack; a universal Tier formula is therefore optional rather than required for Dead Signal.")

    if strength_exact:
        findings.append("Every captured gun_blueprint_attr_data tuple level exactly matches its source strength_lv field; combined with rarity-dependent caps and the separate five-level forge Tier path, this strongly identifies the progression axis used for Blueprint enhancement/stars.")
    if direct_ratio:
        findings.append("Every captured strength row exposes preset_attack_radio. Its values are direct Attack multipliers (for example 1.05 = x1.05), so the Star-side Attack factor is mined per blueprint instead of inferred from a generic rarity formula.")
        modes = blueprint.get("progression_effect_modes", {})
        findings.append(
            "Blueprint-star effects are not Attack-only: progression modes in this snapshot are "
            + ", ".join(f"{name}={count}" for name, count in sorted(modes.items()))
            + "."
        )
        status = "source-factor-found-rounding-unresolved"
    elif legacy_attr_candidates:
        findings.append("Attack/Damage-like blueprint attributes exist, but no complete direct Star Attack multiplier field was established.")
        status = "candidate-components-found"
    else:
        findings.append("No complete source Star Attack multiplier was established.")

    if combined_candidates:
        findings.append("Star x Tier matrices now multiply Tier gun_preset_attack directly by preset_attack_radio; the previous incorrect 1+ratio interpretation has been removed.")
    if multiply_consumers:
        expressions = sorted({
            ((row.get("metadata_semantics") or {}).get("known_obfuscated_tail") or {}).get("expression")
            for row in multiply_consumers
            if ((row.get("metadata_semantics") or {}).get("known_obfuscated_tail") or {}).get("expression")
        })
        findings.append(
            "The remapped client bytecode tail is now recognized directly: progression consumers return "
            + ", ".join(f"`{expr}`" for expr in expressions)
            + ". BINARY_OP argument 5 is multiply; no rounding call exists inside those recognized return tails."
        )
        if status.startswith("source-factor"):
            status = "intrinsic-star-tier-multiplication-proven-rounding-downstream"
    if direct_ratio_returns:
        findings.append("get_gun_preset_attack_radio returns the mined attack_ratio local directly before the multiplication consumer uses it.")
    if weapon_omg_dispatchers:
        findings.append(
            "The remapped get_gun_attr_property_value branch for `weapon_omg_affix_value` is recognized directly and returns "
            "`get_gun_omg_value(gun_no, star)` with no intermediate numeric conversion."
        )
    if display_int_conversions:
        findings.append(
            "The displayed base-Attack builder get_weapon_base_attr_new is recognized wrapping that weapon-OMG property result in "
            "`int(...)` before storing `weapon_omg`. For positive weapon Attack, Python int() is truncate-toward-zero, which is equivalent to floor."
        )
        if multiply_consumers and weapon_omg_dispatchers and direct_ratio:
            status = "displayed-intrinsic-star-tier-formula-proven-int-truncate"
    if display_focus:
        findings.append(
            f"The downstream D0100 display/stat chain is now focus-scanned in {len(display_focus)} captured function instances; "
            "stock disassembly is treated as diagnostic whenever the proven Once Human opcode-remapping profile is present."
        )
        if display_rounding:
            findings.append(
                f"{len(display_rounding)} D0100/display focus functions contain trustworthy rounding/format metadata and are priority final-display candidates."
            )
    if consumer_count:
        findings.append(f"Static PYC scanning found {consumer_count} non-table modules containing progression operands or chain symbols; {caller_count} caller functions were captured for downstream tracing.")
        if caller_rounding_count:
            findings.append(f"{caller_rounding_count} progression-chain caller functions contain int/round/floor/ceil/trunc/format/str names in co_names and are priority rounding/display candidates.")
        elif status == "source-factor-found-rounding-unresolved" and arithmetic_count:
            status = "source-factor-and-consumer-candidates-found"
    elif pyc_scan.get("source_roots_available") or pyc_scan.get("persisted_indexes_available"):
        findings.append("Static PYC scanning did not find a non-table consumer by literal field name; the client may access generated fields indirectly.")
    else:
        findings.append("Neither a persisted PYC symbol index nor a live extracted PYC source root was available, so consumer/rounding code could not be scanned.")

    findings.append("Calibration Blueprint Attack bonuses remain excluded from intrinsic Blueprint Star x Gear Tier progression.")
    return {
        "status": status,
        "tested_model": (
            "DisplayedIntrinsicAttack = int(Tier gun_preset_attack * preset_attack_radio[strength_lv])"
            if display_int_conversions and weapon_omg_dispatchers and multiply_consumers
            else "DisplayedAttack = UI_IntegerConversion(Tier gun_preset_attack * preset_attack_radio[strength_lv])"
        ),
        "tier_factor_evidence": tier_universal,
        "star_factor_source": ratio_evidence,
        "legacy_attack_attribute_candidates": legacy_attr_candidates,
        "combined_star_tier_prediction_matrices": combined_candidates,
        "pyc_consumer_summary": {
            "source_roots_available": pyc_scan.get("source_roots_available", False),
            "persisted_indexes_available": pyc_scan.get("persisted_indexes_available", False),
            "consumer_candidate_files": consumer_count,
            "arithmetic_or_rounding_candidate_files": arithmetic_count,
            "recognized_multiply_return_functions": len(multiply_consumers),
            "recognized_direct_ratio_return_functions": len(direct_ratio_returns),
            "caller_function_count": caller_count,
            "callers_with_rounding_or_format_names": caller_rounding_count,
            "display_focus_function_count": len(display_focus),
            "display_focus_with_rounding_or_format_metadata": len(display_rounding),
            "recognized_weapon_omg_property_dispatchers": len(weapon_omg_dispatchers),
            "recognized_display_int_conversions": len(display_int_conversions),
        },
        "findings": findings,
        "remaining_unknown": (
            "Intrinsic positive weapon Attack Star × Tier display conversion is resolved; later calibration/affix/mod combat layers remain separate systems."
            if display_int_conversions and weapon_omg_dispatchers and multiply_consumers
            else "Exact UI integer conversion / rounding order unless a PYC consumer or independent displayed-stat observation proves it."
        ),
        "calibration_policy": "Calibration Blueprint Attack bonuses are excluded from intrinsic Blueprint Star x Gear Tier progression analysis.",
    }

def markdown_report(payload: dict) -> str:
    tier = payload["tier_analysis"]
    blue = payload["blueprint_level_analysis"]
    formula = payload["formula_assessment"]
    scan = payload["source_candidate_scan"]
    pyc_scan = payload.get("pyc_consumer_scan", {})
    lines = [
        "# Dead Signal Weapon Progression Investigation",
        "",
        "Target: **Blueprint Stars × Gear Tier I–V → displayed weapon stats**",
        "",
        f"Generated: `{payload['generated_utc']}`",
        "",
        "## Current verdict",
        "",
        f"**{formula['status']}**",
        "",
    ]
    for finding in formula["findings"]:
        lines.append(f"- {finding}")
    lines.extend(["", "## Tier I–V evidence", ""])
    aggregate = tier.get("aggregate_ratios_to_tier_1", {})
    if aggregate:
        lines.extend([
            "| Tier | n | median ratio to T1 | MAD | compatible rounding-factor interval(s) |",
            "|---:|---:|---:|---:|---|",
        ])
        for tier_no in sorted(aggregate, key=int):
            row = aggregate[tier_no]
            intervals = []
            for candidate in row.get("rounding_factor_intersections", []):
                if candidate.get("compatible"):
                    intervals.append(
                        f"{candidate['mode']}: {candidate['factor_min']:.10g}..{candidate['factor_max']:.10g}"
                    )
            lines.append(
                f"| {tier_no} | {row['n']} | {row['median']:.10g} | {row['mad']:.4g} | {'; '.join(intervals) or 'none'} |"
            )
    lines.extend(["", "## Raw blueprint-level evidence", ""])
    for quality, row in blue.get("quality_level_summary", {}).items():
        lines.append(
            f"- **{quality}:** {row['weapons']} weapons; common max raw level `{row['common_max_level']}`; distribution `{row['max_level_distribution']}`"
        )
    ratio = blue.get("preset_attack_ratio_evidence", {})
    lines.extend(["", "## Direct Star Attack factor", ""])
    lines.append(f"- Source field: `{ratio.get('source_field', 'not found')}`")
    lines.append(f"- Rows: **{ratio.get('rows', 0)}**")
    lines.append(f"- Coverage of strength rows: **{ratio.get('coverage_of_strength_rows', 0):.1%}**")
    lines.append(f"- Semantics: {ratio.get('value_semantics', 'unresolved')}")
    lines.append(f"- Progression effect modes: `{blue.get('progression_effect_modes', {})}`")
    lines.extend(["", "Most common curves:"])
    for row in ratio.get("curves_by_quality", [])[:20]:
        lines.append(f"- **{row['quality']}** × {row['weapons']}: `{row['preset_attack_ratio']}`")
    star_candidates = formula.get("legacy_attack_attribute_candidates", [])
    lines.extend(["", "## Other Attack/Damage-like blueprint attributes", ""])
    if star_candidates:
        for row in star_candidates:
            lines.append(f"- `{row['code']}` — {row['label']}")
    else:
        lines.append("- None safely identified yet.")
    lines.extend([
        "",
        "## PYC consumer hunt",
        "",
        f"- Persisted symbol indexes: **{pyc_scan.get('persisted_indexes_available', False)}**",
        f"- Live PYC roots available: **{pyc_scan.get('source_roots_available', False)}**",
        f"- PYC files scanned: **{pyc_scan.get('scanned_pyc_files', 0)}**",
        f"- Non-table consumer candidates: **{pyc_scan.get('consumer_candidate_files', 0)}**",
        f"- Arithmetic/rounding candidates: **{pyc_scan.get('arithmetic_or_rounding_candidate_files', 0)}**",
        f"- Focus functions captured: **{pyc_scan.get('focus_function_count', 0)}**",
        f"- Progression focus functions: **{pyc_scan.get('progression_focus_function_count', 0)}**",
        f"- D0100/display focus functions: **{pyc_scan.get('display_focus_function_count', 0)}**",
        f"- D0100/display focus functions with rounding/format metadata: **{pyc_scan.get('display_focus_with_rounding_or_format_names', 0)}**",
        f"- Focus functions requiring raw-code fallback: **{pyc_scan.get('focus_disassembly_failures', 0)}**",
        f"- Progression-chain caller functions captured: **{pyc_scan.get('caller_function_count', 0)}**",
        f"- Callers with rounding/format names in metadata: **{pyc_scan.get('callers_with_rounding_or_format_names', 0)}**",
        "",
        "Focus consumer functions:",
    ])
    for row in pyc_scan.get("focus_functions", [])[:30]:
        status = "raw-code capsule" if row.get("disassembly_error") else "full disassembly"
        tail = ((row.get("metadata_semantics") or {}).get("known_obfuscated_tail") or {})
        tail_text = f" — decoded tail `{tail.get('expression')}`" if tail.get("expression") else ""
        meta = row.get("metadata_semantics") or {}
        display_semantics = meta.get("known_display_semantics", {}) or {}
        display_conversion = display_semantics.get("display_attack_int_conversion") or {}
        property_dispatch = display_semantics.get("weapon_omg_property_dispatch") or {}
        if display_conversion.get("expression"):
            tail_text += f" — decoded display `{display_conversion.get('expression')}`"
        if property_dispatch.get("expression"):
            tail_text += f" — decoded property `{property_dispatch.get('expression')}`"
        display_text = f" — display IDs {row.get('display_targets', [])}" if row.get("display_targets") else ""
        round_text = f" — round/format names {meta.get('rounding_or_format_names_in_co_names', [])}" if meta.get("rounding_or_format_names_in_co_names") else ""
        fmt_text = f" — integer formats {meta.get('integer_format_strings_in_metadata', [])}" if meta.get("integer_format_strings_in_metadata") else ""
        lines.append(f"- `{row.get('pyc')}` :: `{row.get('qualname')}` — {row.get('focus_layer') or 'focus'} — {status} — targets {row.get('targets', [])}{display_text}{round_text}{fmt_text}{tail_text}")
    lines.extend(["", "Progression-chain callers with rounding/format metadata:"])
    caller_rows = [row for row in pyc_scan.get("caller_functions", []) if row.get("rounding_or_format_names_in_co_names")]
    if caller_rows:
        for row in caller_rows[:60]:
            lines.append(
                f"- `{row.get('pyc')}` :: `{row.get('qualname')}` — calls {row.get('chain_targets', [])} — names {row.get('rounding_or_format_names_in_co_names', [])}"
            )
    else:
        lines.append("- none captured")
    lines.extend([
        "",
        "Top PYC candidates:",
    ])
    for row in pyc_scan.get("top_candidates", [])[:25]:
        lines.append(f"- `{row['pyc']}` — score {row['score']} — {row['classification']} — {row['targets']}")
    lines.extend([
        "",
        "## Source hunt",
        "",
        f"- Relevant raw tables scanned: **{scan['scanned_tables']}**",
        f"- Relevant raw rows scanned: **{scan['scanned_rows']}**",
        f"- Candidate records found: **{scan['candidate_count']}**",
        "",
        "Highest-value tables:",
    ])
    for row in scan.get("candidate_tables", [])[:30]:
        lines.append(f"- `{row['table']}` — {row['rows']} candidate rows")
    lines.extend([
        "",
        "## Rule before shipping calculator math",
        "",
        (
            "The intrinsic positive-Attack display path is proven as int(Tier gun_preset_attack × preset_attack_radio[strength_lv]). "
            "Calibration Blueprint Attack rolls and later affix/mod/combat layers remain separate systems."
            if formula.get("status") == "displayed-intrinsic-star-tier-formula-proven-int-truncate"
            else "A candidate Star/Tier transform must reproduce multiple weapons and multiple progression levels. "
                 "Rounding behavior must explain the remaining integer display differences. Calibration Blueprint Attack rolls remain a separate layer."
        ),
        "",
    ])
    return "\n".join(lines)


def _record_contains_literal(value: Any, targets: set[str]) -> bool:
    if isinstance(value, str):
        return value in targets
    if isinstance(value, dict):
        return any(
            str(key) in targets or _record_contains_literal(item, targets)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_record_contains_literal(item, targets) for item in value)
    return False


def _interesting_formatter_fields(value: Any, prefix: str = "", limit: int = 120) -> list[dict]:
    out: list[dict] = []
    key_hint = re.compile(r"(?:affix|attr|calc|type|format|effect|range|value|val)", re.IGNORECASE)

    def walk(node: Any, path: str) -> None:
        if len(out) >= limit:
            return
        if isinstance(node, dict):
            for key, item in node.items():
                child = f"{path}/{key}" if path else str(key)
                if key_hint.search(str(key)) and isinstance(item, (str, int, float, bool, type(None))):
                    out.append({"path": child, "value": item})
                    if len(out) >= limit:
                        return
                walk(item, child)
        elif isinstance(node, (list, tuple)):
            for index, item in enumerate(node):
                walk(item, f"{path}/{index}")

    walk(value, prefix)
    return out


STATIC_CARD_AFFIX_IDS = {
    "D0100", "D0101", "D0102",
    "Q0100", "Q0300", "Q0500", "Q0800", "Q0900",
    "Q1100", "Q1101", "Q1600", "Q2000", "Q2400", "Q2600",
}


def _scan_affix_prototype_display_records(pyc_scan: dict, base: Path | None = None, current: Path | None = None) -> dict:
    """Find raw formatter prototype rows for the static weapon-card stat family.

    v1.5.4 correction: parsed bindict JSON lives in the exported base/current
    snapshot roots, while pyc_scan.source_roots points back to the temporary/raw
    extracted PYC tree.  Scan the exported roots first, then retain the live-root
    fallback for unusual layouts.
    """
    targets = set(STATIC_CARD_AFFIX_IDS)
    retained = []
    scanned_files = 0
    matched_files = set()
    seen = set()

    roots_to_scan: list[tuple[str | None, Path, str]] = []
    if base is not None:
        roots_to_scan.append(("base", Path(base), "exported-snapshot"))
    if current is not None:
        roots_to_scan.append(("current", Path(current), "exported-snapshot"))
    for source in pyc_scan.get("source_roots", []) or []:
        root = Path(str(source.get("path") or ""))
        roots_to_scan.append((source.get("layer"), root, "live-pyc-root-fallback"))

    scanned_root_keys = set()
    for layer, root, source_kind in roots_to_scan:
        try:
            root_key = str(root.resolve()).casefold()
        except OSError:
            root_key = str(root).casefold()
        if root_key in scanned_root_keys:
            continue
        scanned_root_keys.add(root_key)
        data_root = root / GAME_DATA
        if not data_root.exists():
            continue

        candidate_paths = set(data_root.glob("*affix*.json")) | set(data_root.glob("*prototype*.json"))
        direct = data_root / "affix_prototype_data.json"
        if direct.exists():
            candidate_paths.add(direct)

        for path in sorted(candidate_paths):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if not any(token in text for token in targets):
                continue
            scanned_files += 1
            payload = read_json(path, {})
            table_rows = rows(payload)
            for record_id, record in table_rows.items():
                if not isinstance(record, dict):
                    continue
                matched_targets = sorted(
                    token for token in targets
                    if str(record_id) == token or _record_contains_literal(record, {token})
                )
                if not matched_targets:
                    continue
                key = (str(path), str(record_id), tuple(matched_targets))
                if key in seen:
                    continue
                seen.add(key)
                matched_files.add(str(path))
                retained.append({
                    "layer": layer,
                    "source_kind": source_kind,
                    "table": path.relative_to(root).as_posix(),
                    "record_id": str(record_id),
                    "matched_stat_ids": matched_targets,
                    "interesting_fields": _interesting_formatter_fields(record),
                    "record_preview": record if len(compact(record, 12000)) < 12000 else compact(record, 12000),
                })
                if len(retained) >= 120:
                    break
            if len(retained) >= 120:
                break
        if len(retained) >= 120:
            break

    return {
        "status": "source-prototype-records-found" if retained else "source-prototype-records-not-found",
        "targets": sorted(targets),
        "candidate_files_with_target_literals": scanned_files,
        "matched_files": sorted(matched_files),
        "records": retained,
        "scan_note": "v1.5.4 scans exported base/current bindict JSON before raw PYC roots",
    }


def _infer_d0100_formatter_binding(prototype_scan: dict) -> dict:
    """Compare D0100 with D0101/D0102 prototype display metadata."""
    by_target: dict[str, list[dict]] = {"D0100": [], "D0101": [], "D0102": []}
    for record in prototype_scan.get("records", []) or []:
        for target in record.get("matched_stat_ids", []) or []:
            if target in by_target:
                by_target[target].append(record)

    def field_map(records: list[dict]) -> dict[str, object]:
        out: dict[str, object] = {}
        for record in records:
            for item in record.get("interesting_fields", []) or []:
                path = str(item.get("path") or "")
                leaf = path.rsplit("/", 1)[-1].casefold()
                if any(token in leaf for token in ("type", "calc", "format", "attr", "effect")):
                    out.setdefault(path, item.get("value"))
        return out

    fields = {target: field_map(records) for target, records in by_target.items()}
    common_paths = set(fields["D0100"]) & set(fields["D0101"]) & set(fields["D0102"])
    comparisons = []
    distinct_rate_paths = []
    for path in sorted(common_paths):
        a = fields["D0100"].get(path)
        b = fields["D0101"].get(path)
        c = fields["D0102"].get(path)
        comparisons.append({"path": path, "D0100": a, "D0101": b, "D0102": c})
        leaf = path.rsplit("/", 1)[-1].casefold()
        if b == c and a != b and any(token in leaf for token in ("type", "calc", "format")):
            distinct_rate_paths.append(path)

    if all(by_target[target] for target in by_target) and distinct_rate_paths:
        status = "d0100-display-prototype-distinct-from-d0101-d0102-rate-prototypes"
        inference = (
            "D0101 and D0102 are proven Weapon DMG ratio stats and share the same display metadata, "
            "while D0100 differs on formatter/type metadata. This binds D0100 to the absolute-value "
            "display family and D0101/D0102 to the rate/percent family."
        )
    elif all(by_target[target] for target in by_target):
        status = "prototype-records-found-branch-distinction-not-yet-automatic"
        inference = "Prototype rows were recovered; inspect comparison fields before assigning ABS/RATE."
    else:
        status = "prototype-records-incomplete"
        inference = "D0100/D0101/D0102 prototype rows were not all recovered."

    return {
        "status": status,
        "inference": inference,
        "records_found": {target: len(records) for target, records in by_target.items()},
        "shared_field_comparisons": comparisons[:80],
        "distinct_rate_comparison_paths": distinct_rate_paths[:20],
    }


def _infer_d0100_final_display_rule(prototype_scan: dict, formatter_function_evidence: list[dict], binding: dict) -> dict:
    """Bind D0100 to its final whole-number display rule.

    The D0100 prototype explicitly carries ``{:.0f}``, while D0101/D0102 carry
    percent formats.  Separately, the remapped formatter body proves its int()
    call belongs to the RATE precision probe.  Together this distinguishes the
    earlier intrinsic-star ``int()`` truncation from the final static-card D0100
    display, which uses the prototype's zero-decimal fixed-point format.
    """
    d0100_formats: list[str] = []
    for record in prototype_scan.get("records", []) or []:
        if record.get("record_id") != "D0100":
            continue
        table = str(record.get("table") or "")
        if not table.endswith("affix_prototype_data.json"):
            continue
        preview = record.get("record_preview") or {}
        fmt = preview.get("format") if isinstance(preview, dict) else None
        if isinstance(fmt, dict):
            values = fmt.get("lan_translate") or []
            if isinstance(values, str):
                values = [values]
            for value in values:
                if isinstance(value, str):
                    d0100_formats.append(value)
        elif isinstance(fmt, str):
            d0100_formats.append(fmt)

    rate_probes = []
    for evidence in formatter_function_evidence:
        semantics = evidence.get("semantics") or {}
        probe = semantics.get("rate_fraction_probe") or {}
        if probe.get("status") == "recognized-rate-percent-fraction-probe":
            rate_probes.append({
                "pyc": evidence.get("pyc"),
                "qualname": evidence.get("qualname"),
                "probe": probe,
            })

    has_zero_decimal_format = any("{:.0f}" in value for value in d0100_formats)
    bound_abs = binding.get("status") == "d0100-display-prototype-distinct-from-d0101-d0102-rate-prototypes"
    if bound_abs and has_zero_decimal_format and rate_probes:
        return {
            "status": "d0100-final-zero-decimal-format-proven",
            "D0100_format_strings": d0100_formats,
            "display_rule": 'D0100 static-card value is rendered with the prototype fixed-point format "{:.0f}"',
            "numeric_effect": (
                "zero decimal places using the client Python formatter; this is a formatting-round step, "
                "not the earlier int()/truncate step used when constructing intrinsic star-scaled base Attack"
            ),
            "final_static_card_conversion": 'format(static_attack, ".0f") semantics via D0100 prototype',
            "rate_int_role": "int() belongs to AP_CALC_TYPE_RATE fractional-percent precision detection",
            "rate_probe_evidence": rate_probes,
        }
    return {
        "status": "d0100-final-display-rule-pending",
        "D0100_format_strings": d0100_formats,
        "bound_absolute_family": bound_abs,
        "rate_fraction_probe_found": bool(rate_probes),
        "reason": "Need D0100 {:.0f} prototype + absolute-family binding + recognized RATE int-role in the same run.",
    }



def _static_weapon_card_stat_assessment(published: Path, prototype_scan: dict, attachments: list[dict]) -> dict:
    """Build a planner-facing map for the static weapon-card stat IDs.

    Stat identity comes from normalized char_property_data, while the exact raw
    affix variant (flat vs rate and display format) comes from
    affix_prototype_data when present.  This lets variants such as Q1101
    resolve to Q11 Magazine Capacity without guessing from the suffix alone.
    """
    stat_payload = read_json(published / "data" / "stat-definitions.json", {})
    stat_defs = [row for row in stat_payload.get("stat_definitions", []) if isinstance(row, dict)]
    by_id = {str(row.get("id")): row for row in stat_defs if row.get("id")}

    prototype_by_id: dict[str, dict] = {}
    for record in prototype_scan.get("records", []) or []:
        rid = str(record.get("record_id") or "")
        if rid not in STATIC_CARD_AFFIX_IDS:
            continue
        table = str(record.get("table") or "")
        if not table.endswith("affix_prototype_data.json"):
            continue
        preview = record.get("record_preview")
        if isinstance(preview, dict):
            prototype_by_id.setdefault(rid, preview)

    usage: dict[str, dict] = {}
    planner_slots = {"Sight", "Muzzle", "Tactical", "Magazine"}
    for row in attachments:
        slot = str(row.get("attachment_type") or "")
        if slot not in planner_slots:
            continue
        for pair in row.get("attribute_codes") or []:
            if not (isinstance(pair, (list, tuple)) and len(pair) >= 2 and isinstance(pair[0], str)):
                continue
            code = pair[0]
            if code not in STATIC_CARD_AFFIX_IDS:
                continue
            bucket = usage.setdefault(code, {"attachment_count": 0, "slots": set(), "examples": []})
            bucket["attachment_count"] += 1
            bucket["slots"].add(slot)
            if len(bucket["examples"]) < 5:
                bucket["examples"].append({"name": row.get("name"), "slot": slot, "raw_value": pair[1]})

    helper_bindings = {
        "Q0800": {"reader": "get_gun_rpm_val", "role": "aggregated absolute weapon RPM / Fire Rate value"},
        "Q0900": {"role": "Fire Rate percentage modifier folded into the RPM path"},
        "Q1100": {"reader": "get_gun_magazine_size", "role": "aggregated absolute Magazine Capacity value"},
        "Q1101": {"role": "Magazine Capacity percentage affix variant; prototype metadata decides rate semantics"},
        "Q1600": {"reader": "get_gun_mobility", "role": "weapon Mobility contribution"},
    }

    rows_out = []
    for code in sorted(STATIC_CARD_AFFIX_IDS):
        proto = prototype_by_id.get(code) or {}
        canonical_id = str(proto.get("attr_id") or "")
        if not canonical_id and re.fullmatch(r"[A-Z][0-9]{4}", code):
            prefix = code[:3]
            if prefix in by_id:
                canonical_id = prefix
        stat = by_id.get(canonical_id) or {}
        proto_type = proto.get("type")
        if proto_type == 2:
            operation = "add_percent"
            unit = "percent"
        elif proto_type == 1:
            operation = "add_flat"
            unit = "flat"
        else:
            unit = stat.get("unit")
            operation = "add_percent" if unit == "percent" else "add_flat" if unit else None

        fmt_values = []
        fmt = proto.get("format")
        if isinstance(fmt, dict):
            values = fmt.get("lan_translate") or []
            if isinstance(values, str):
                values = [values]
            fmt_values.extend(value for value in values if isinstance(value, str))
        elif isinstance(fmt, str):
            fmt_values.append(fmt)

        use = usage.get(code) or {}
        rows_out.append({
            "affix_id": code,
            "canonical_stat_id": canonical_id or None,
            "internal_name": stat.get("key"),
            "display_name": stat.get("name"),
            "canonical_name": stat.get("canonical_name"),
            "operation": operation,
            "unit": unit,
            "prototype_type": proto_type,
            "prototype_effect_range": proto.get("effect_range"),
            "prototype_formats": fmt_values,
            "prototype_found": bool(proto),
            "attachment_count": int(use.get("attachment_count") or 0),
            "attachment_slots": sorted(use.get("slots") or []),
            "examples": use.get("examples") or [],
            "helper_binding": helper_bindings.get(code),
        })

    q1101 = next((row for row in rows_out if row["affix_id"] == "Q1101"), None)
    return {
        "status": "static-weapon-card-stat-family-mapped",
        "stat_ids": rows_out,
        "q1101_resolution": {
            "status": (
                "prototype-rate-variant-proven" if q1101 and q1101.get("prototype_type") == 2 and q1101.get("canonical_stat_id") == "Q11"
                else "pending-prototype-evidence"
            ),
            "interpretation": "Q1101 is the percentage/rate variant of Q11 Magazine Capacity when its prototype type is RATE.",
            "record": q1101,
        },
        "deeper_helper_targets": [
            "get_gun_shoot_attr_weapon_rpm", "get_gun_shoot_interval",
            "get_weapon_accuracy_rate", "get_weapoon_range_value",
            "get_reload_add_bullet_time_value", "get_init_weapon_stability",
            "get_weapon_stability_affix",
        ],
    }

def weapon_stat_aggregator_assessment(pyc_scan: dict, published: Path, base: Path | None = None, current: Path | None = None) -> dict:
    """Summarize static weapon-card sources plus mined attachment stat coverage."""
    function_evidence = []
    for row in pyc_scan.get("top_candidates", []):
        for hit in (row.get("code_object_inspection", {}) or {}).get("code_hits", []):
            semantics = (hit.get("metadata_semantics", {}) or {}).get("known_weapon_aggregator_semantics")
            if not semantics:
                continue
            function_evidence.append({
                "pyc": row.get("pyc"),
                "qualname": hit.get("qualname"),
                "semantics": semantics,
            })

    formatter_function_evidence = []
    for row in pyc_scan.get("top_candidates", []):
        for hit in (row.get("code_object_inspection", {}) or {}).get("code_hits", []):
            display_semantics = (hit.get("metadata_semantics", {}) or {}).get("known_display_semantics") or {}
            formatter = display_semantics.get("final_affix_formatter")
            if not formatter:
                continue
            formatter_function_evidence.append({
                "pyc": row.get("pyc"),
                "qualname": hit.get("qualname"),
                "semantics": formatter,
                "code_capsule": hit.get("code_capsule"),
                "raw_wordcode": hit.get("raw_wordcode"),
            })

    affix_prototype_scan = _scan_affix_prototype_display_records(pyc_scan, base=base, current=current)
    d0100_formatter_binding = _infer_d0100_formatter_binding(affix_prototype_scan)
    d0100_final_display_rule = _infer_d0100_final_display_rule(
        affix_prototype_scan, formatter_function_evidence, d0100_formatter_binding
    )

    attachments_payload = read_json(published / "data" / "attachments.json", {})
    attachments = [row for row in attachments_payload.get("attachments", []) if isinstance(row, dict)]
    static_weapon_card_stats = _static_weapon_card_stat_assessment(published, affix_prototype_scan, attachments)
    slot_counts = {}
    stat_counts = {}
    direct_attack_ratio_examples = []
    planner_slot_attack_ratio_examples = []
    planner_slot_stat_counts = {}
    planner_slot_stat_examples = {}
    planner_slots = {"Sight", "Muzzle", "Tactical", "Magazine"}
    attack_ratio_raw_count = 0
    attack_ratio_resolved_count = 0
    attack_ratio_missing_examples = []
    for row in attachments:
        slot = str(row.get("attachment_type") or "Unknown")
        slot_counts[slot] = slot_counts.get(slot, 0) + 1
        pairs = row.get("attribute_codes") or []
        for pair in pairs:
            if isinstance(pair, (list, tuple)) and len(pair) >= 2 and isinstance(pair[0], str):
                code, raw_value = pair[0], pair[1]
            elif isinstance(pair, str):
                code, raw_value = pair, None
            else:
                continue
            stat_counts[code] = stat_counts.get(code, 0) + 1
            if code in {"D0101", "D0102"}:
                attack_ratio_raw_count += 1
                resolved_rows = row.get("resolved_stats") or []
                matching = [
                    resolved for resolved in resolved_rows
                    if isinstance(resolved, dict)
                    and resolved.get("raw_stat_id") == code
                    and resolved.get("resolution_status") == "resolved"
                ]
                if matching:
                    attack_ratio_resolved_count += 1
                elif len(attack_ratio_missing_examples) < 20:
                    attack_ratio_missing_examples.append({
                        "name": row.get("name"),
                        "id": row.get("id"),
                        "attachment_type": slot,
                        "stat_id": code,
                        "raw_value": raw_value,
                    })
            if slot in planner_slots:
                slot_map = planner_slot_stat_counts.setdefault(slot, {})
                slot_map[code] = slot_map.get(code, 0) + 1
                example_key = (slot, code)
                planner_slot_stat_examples.setdefault(example_key, {
                    "name": row.get("name"),
                    "raw_value": raw_value,
                })
            if code in {"D0101", "D0102"} and len(direct_attack_ratio_examples) < 30:
                example = {
                    "name": row.get("name"),
                    "attachment_type": slot,
                    "stat_id": code,
                    "raw_value": raw_value,
                }
                direct_attack_ratio_examples.append(example)
                if slot in planner_slots and len(planner_slot_attack_ratio_examples) < 30:
                    planner_slot_attack_ratio_examples.append(example)

    planner_slot_stat_map = {}
    for slot in sorted(planner_slots):
        entries = []
        for code, count in sorted((planner_slot_stat_counts.get(slot) or {}).items(), key=lambda item: (-item[1], item[0])):
            example = planner_slot_stat_examples.get((slot, code), {})
            semantic = None
            if code in {"D0101", "D0102"}:
                semantic = {
                    "canonical_name": "attack",
                    "display_name": "Weapon DMG",
                    "operation": "add_percent",
                    "encoding_rule": "proven_weapon_attack_ratio_affix",
                }
            entries.append({
                "stat_id": code,
                "attachment_count": count,
                "example_attachment": example.get("name"),
                "example_raw_value": example.get("raw_value"),
                "proven_semantic": semantic,
            })
        planner_slot_stat_map[slot] = entries

    attack_formula_evidence = []
    for row in function_evidence:
        semantics = row.get("semantics") or {}
        attack_bucket = semantics.get("attack_bucket") or {}
        formula = attack_bucket.get("final_static_expression")
        if formula:
            attack_formula_evidence.append({
                "pyc": row.get("pyc"),
                "qualname": row.get("qualname"),
                "formula": formula,
                "ratio_expression": attack_bucket.get("ratio_expression"),
            })

    return {
        "status": "static-weapon-card-aggregator-formula-and-accessory-map-traced",
        "known_normal_aggregator_inputs": [
            "base_affix_add", "accessory_affix_add", "rand_affix_add",
            "affix_option_add", "cal_affix", "correct_affix_add",
        ],
        "planner_interpretation": {
            "static_weapon_card_layer": "weapon foundation + equipped accessories + calibration/affix sources",
            "runtime_combat_layer": "weapon mods, armor/set buffs, cradles, deviations, consumables and conditional buffs should remain a later combat layer unless a direct static-card consumer proves otherwise",
        },
        "attachment_slot_counts": dict(sorted(slot_counts.items())),
        "attachment_stat_code_counts": dict(sorted(stat_counts.items())),
        "attachment_direct_attack_ratio_examples": direct_attack_ratio_examples,
        "planner_accessory_slots": sorted(planner_slots),
        "planner_slot_stat_map": planner_slot_stat_map,
        "static_weapon_card_stat_map": static_weapon_card_stats,
        "planner_slot_direct_attack_ratio_examples": planner_slot_attack_ratio_examples,
        "static_attack_formula": {
            "base_flat_id": "D0100",
            "ratio_ids": ["D0101", "D0102"],
            "attack_radio": "1.0 + sum(active D0101/D0102 values)",
            "combined_attack": "base D0100 * attack_radio + delta_attack",
            "delta_attack": "combined D0100 contribution minus base D0100 contribution",
            "attachment_ratio_modifiers_are_shared": True,
            "evidence": attack_formula_evidence,
        },
        "normalization_rules": {
            "D0101_D0102": "resolve as Weapon DMG percentage modifiers against canonical D01 instead of dropping them",
        },
        "normalization_validation": {
            "raw_D0101_D0102_attachment_modifiers": attack_ratio_raw_count,
            "resolved_D0101_D0102_attachment_modifiers": attack_ratio_resolved_count,
            "status": (
                "all-proven-attack-ratio-affixes-preserved"
                if attack_ratio_raw_count == attack_ratio_resolved_count
                else "ERROR-proven-attack-ratio-affix-missing-from-resolved-stats"
            ),
            "missing_examples": attack_ratio_missing_examples,
        },
        "display_bridge": {
            "D0100_formatter_call": "calc_gun_attr_data -> AffixUtils.get_affix_name_and_val2",
            "calc_gun_attr_data_literals": {
                "D0100_special_case": True,
                "multi_projectile_format": "%sx%d",
            },
            "status": (
                "D0100-final-zero-decimal-format-proven"
                if d0100_final_display_rule.get("status") == "d0100-final-zero-decimal-format-proven"
                else "D0100-final-display-rule-pending"
            ),
            "do_not_assume_final_integer_conversion": (
                d0100_final_display_rule.get("status") != "d0100-final-zero-decimal-format-proven"
            ),
            "reason": (
                "D0100 is bound to the absolute-value family and its prototype explicitly requests {:.0f}. "
                "The formatter's int() call is independently recognized inside the AP_CALC_TYPE_RATE fractional-percent "
                "precision probe, so it is not a D0100 truncation step."
                if d0100_final_display_rule.get("status") == "d0100-final-zero-decimal-format-proven"
                else "The prototype or RATE int-role evidence was incomplete in this run."
            ),
        },
        "formatter_function_evidence": formatter_function_evidence,
        "affix_prototype_display_records": affix_prototype_scan,
        "D0100_formatter_binding": d0100_formatter_binding,
        "D0100_final_display_rule": d0100_final_display_rule,
        "function_evidence": function_evidence,
        "next_static_targets": sorted(PYC_WEAPON_AGGREGATOR_FUNCTIONS),
    }


def run_weapon_progression_investigation(base: Path, current: Path, published: Path) -> dict:
    data_dir = published / "data"
    reports = published / "reports"
    weapons_payload = read_json(data_dir / "weapons.json", {})
    weapons = [row for row in weapons_payload.get("weapons", []) if isinstance(row, dict)]
    blueprint_ids = {str(row.get("blueprint_id")) for row in weapons if row.get("blueprint_id")}

    tier = tier_analysis(weapons)
    blueprint = blueprint_level_analysis(weapons)
    scan = scan_candidate_tables(base, current, blueprint_ids)
    tracer = tracer_weapon_references(published / "indexes" / "reference-tracer.sqlite", weapons)
    pyc_scan = scan_pyc_consumers(base, current)
    formula = formula_assessment(tier, blueprint, pyc_scan)
    aggregator = weapon_stat_aggregator_assessment(pyc_scan, published, base=base, current=current)

    payload = {
        "schema_version": 10,
        "generated_utc": utc_now(),
        "question": "How do Blueprint Stars and crafted Gear Tier I-V produce displayed weapon stats?",
        "method": {
            "execution_policy": "static extracted-table analysis only",
            "separation_policy": "Calibration Blueprint Attack bonuses are excluded from intrinsic weapon progression",
            "formula_policy": "No formula is promoted unless mined evidence and cross-weapon reproduction support it",
        },
        "record_counts": {
            "weapons": len(weapons),
            "weapons_with_complete_tiers": tier.get("weapons_with_complete_tiers", 0),
            "candidate_source_records": scan.get("candidate_count", 0),
            "weapons_with_progression_traces": tracer.get("weapons_with_matches", 0),
        },
        "tier_analysis": tier,
        "blueprint_level_analysis": blueprint,
        "formula_assessment": formula,
        "source_candidate_scan": scan,
        "reference_traces": tracer,
        "pyc_consumer_scan": pyc_scan,
        "weapon_stat_aggregator": aggregator,
    }

    write_json(data_dir / "weapon-progression-investigation.json", payload)
    write_json(reports / "weapon-stat-aggregator-investigation.json", aggregator)
    write_json(reports / "weapon-progression-pyc-consumers.json", pyc_scan)
    write_json(reports / "weapon-progression-candidates.json", {
        "generated_utc": payload["generated_utc"],
        "question": payload["question"],
        "candidate_tables": scan.get("candidate_tables", []),
        "top_candidates": scan.get("top_candidates", []),
    })
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "weapon-progression-report.md").write_text(markdown_report(payload), encoding="utf-8")

    progression_path = data_dir / "progression.json"
    progression = read_json(progression_path, {})
    progression["weapon_blueprint_star_tier_investigation"] = {
        "status": formula.get("status"),
        "dataset": "weapon-progression-investigation.json",
        "report": "../reports/weapon-progression-report.md",
        "candidate_report": "../reports/weapon-progression-candidates.json",
        "pyc_consumer_report": "../reports/weapon-progression-pyc-consumers.json",
        "tier_factor_candidates": formula.get("tier_factor_evidence", {}),
        "star_factor_source": formula.get("star_factor_source", {}),
        "policy": payload["method"],
    }
    counts = progression.setdefault("record_counts", {})
    counts["weapon_progression_candidate_source_records"] = scan.get("candidate_count", 0)
    counts["weapons_with_complete_tier_damage"] = tier.get("weapons_with_complete_tiers", 0)
    write_json(progression_path, progression)

    return {
        "status": formula.get("status"),
        "weapons": len(weapons),
        "weapons_with_complete_tiers": tier.get("weapons_with_complete_tiers", 0),
        "candidate_source_records": scan.get("candidate_count", 0),
        "weapons_with_progression_traces": tracer.get("weapons_with_matches", 0),
        "pyc_consumer_candidates": pyc_scan.get("consumer_candidate_files", 0),
        "pyc_arithmetic_or_rounding_candidates": pyc_scan.get("arithmetic_or_rounding_candidate_files", 0),
        "output": str(data_dir / "weapon-progression-investigation.json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Investigate Once Human Blueprint Star x Gear Tier weapon scaling from an existing Dead Signal snapshot.")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--published", type=Path, required=True)
    args = parser.parse_args()
    result = run_weapon_progression_investigation(args.base, args.current, args.published)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
