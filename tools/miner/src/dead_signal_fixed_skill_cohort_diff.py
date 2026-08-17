"""Exact structural cohort diff for fixed-skill weapon blueprints.

Compares the unresolved fixed-skill blueprint class with a same-endow control
cohort that has exact passive_skill_data ownership. This is a read-only research
pass. It parses installed Bindict tables only and never executes game bytecode.

Important schema rule: gun_blueprint_attr_data is keyed by (blueprint_id, star)
and does not carry blueprint identity fields such as blueprint_template_no,
endow, or plaques inline. Those fields are joined exactly from
gun_blueprint_data. correct_skill/correct_term_id are joined exactly from
gun_blueprint_terms_map_data. No fuzzy or similar-ID matching is used.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable

from neoxtractor.core.bindict.parser import BindictParser

ActivityCallback = Callable[[str], None]
MAX_ROWS = 512
MAX_DIFF_PATHS = 256

GUN_BLUEPRINT_ATTR_PATH = "game_common/data/gun_blueprint_attr_data.pyc"
GUN_BLUEPRINT_DATA_PATH = "game_common/data/gun_blueprint_data.pyc"
GUN_BLUEPRINT_TERMS_PATH = "game_common/data/gun_blueprint_terms_map_data.pyc"
PASSIVE_SKILL_PATH = "game_common/data/passive_skill_data.pyc"


def _find_source(roots: list[tuple[str, Path]], relative: str) -> tuple[str, Path] | None:
    for layer, root in roots:
        path = root / relative
        if path.is_file():
            return layer, path
    return None


def _parse_bindict(path: Path) -> Any:
    return BindictParser(debug=False).extract_from_pyc(path.read_bytes())


def _iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _iter_dicts(child)


def _data_mapping(parsed: Any) -> dict[Any, Any]:
    """Return the decoded table's canonical data mapping without losing tuple keys."""
    if isinstance(parsed, dict):
        data = parsed.get("data")
        if isinstance(data, dict):
            return data
        # Tests and some parser versions may already return the table mapping.
        return parsed
    return {}


def _int_id(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _blueprint_id_from_star_key(key: Any) -> int | None:
    if isinstance(key, (tuple, list)) and key:
        return _int_id(key[0])
    if isinstance(key, str):
        text = key.strip().lstrip("(").rstrip(")")
        first = text.split(",", 1)[0].strip()
        return _int_id(first)
    return None


def _star_from_key(key: Any) -> int | None:
    if isinstance(key, (tuple, list)) and len(key) >= 2:
        return _int_id(key[1])
    if isinstance(key, str) and "," in key:
        text = key.strip().lstrip("(").rstrip(")")
        return _int_id(text.split(",", 1)[1].strip())
    return None


def _index_star_rows(parsed: Any) -> dict[int, dict[int, dict[str, Any]]]:
    out: dict[int, dict[int, dict[str, Any]]] = {}
    for key, row in _data_mapping(parsed).items():
        if not isinstance(row, dict):
            continue
        blueprint_id = _blueprint_id_from_star_key(key)
        star = _star_from_key(key)
        if blueprint_id is None or star is None:
            continue
        out.setdefault(blueprint_id, {})[star] = row
    return out


def _index_blueprints(parsed: Any) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for key, row in _data_mapping(parsed).items():
        if not isinstance(row, dict):
            continue
        blueprint_id = _int_id(key)
        if blueprint_id is None:
            blueprint_id = _int_id(row.get("blueprint_id") or row.get("blueprint_no") or row.get("id"))
        if blueprint_id is not None:
            out[blueprint_id] = row
    return out


def _collect_exact_codes(parsed: Any) -> set[str]:
    codes: set[str] = set()
    for row in _iter_dicts(parsed):
        for key in ("skill_code", "passive_skill_code", "code", "id"):
            value = row.get(key)
            if isinstance(value, str) and value.startswith("WS"):
                codes.add(value)
        for key, value in row.items():
            if isinstance(key, str) and key.startswith("WS"):
                codes.add(key)
            if isinstance(value, str) and value.startswith("WS"):
                codes.add(value)
    # passive_skill_data commonly uses WS... as top-level keys.
    for key in _data_mapping(parsed):
        if isinstance(key, str) and key.startswith("WS"):
            codes.add(key)
    return codes


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(child, (dict, list, tuple)):
                out.update(_flatten(child, path))
            else:
                out[path] = child
    elif isinstance(value, (list, tuple)):
        if not value:
            out[prefix] = []
        else:
            for index, child in enumerate(value):
                path = f"{prefix}[{index}]"
                if isinstance(child, (dict, list, tuple)):
                    out.update(_flatten(child, path))
                else:
                    out[path] = child
    return out


def _is_empty(value: Any) -> bool:
    return value in (None, "", [], (), {})


def _base_attrs_zero(row: dict[str, Any]) -> bool:
    flat = _flatten(row)
    found = []
    for suffix in ("E0100", "E0200", "E0300"):
        values = [value for path, value in flat.items() if path.endswith(suffix)]
        if values:
            found.extend(values)
    if not found:
        return False
    return all(value in (0, 0.0, "0", "0.0", None, "") for value in found)


def _joined_row(
    blueprint_id: int,
    blueprint: dict[str, Any],
    attr_star1: dict[str, Any],
    terms_star1: dict[str, Any],
) -> dict[str, Any]:
    """Build one exact blueprint-level comparison row from its owner tables."""
    return {
        "blueprint_id": blueprint_id,
        "item_id": blueprint.get("gun_item_no") or blueprint.get("item_no") or blueprint.get("item_id"),
        "name": blueprint.get("name") or blueprint.get("blueprint_name") or blueprint.get("item_name"),
        "blueprint_template_no": blueprint.get("blueprint_template_no"),
        "endow": blueprint.get("endow"),
        "plaques": blueprint.get("plaques"),
        "brand_no": blueprint.get("brand_no"),
        "prototype_no": blueprint.get("prototype_no"),
        "fixed_skill_code": attr_star1.get("fixed_skill_code"),
        "fixed_skill_lv": attr_star1.get("fixed_skill_lv"),
        "base_attr": {
            key: value
            for key, value in attr_star1.items()
            if key in {"base_attr", "base_attr_val1", "base_attr_val2", "base_attr_val3", "base_attr_val4", "base_attr_name1", "base_attr_name2", "base_attr_name3", "base_attr_name4"}
        },
        "attr_star1": attr_star1,
        "correct_skill": terms_star1.get("correct_skill"),
        "correct_term_id": terms_star1.get("correct_term_id"),
        "terms_star1": terms_star1,
    }


def _weapon_rows(blueprints_parsed: Any, attrs_parsed: Any, terms_parsed: Any) -> list[dict[str, Any]]:
    blueprints = _index_blueprints(blueprints_parsed)
    attrs = _index_star_rows(attrs_parsed)
    terms = _index_star_rows(terms_parsed)
    rows: list[dict[str, Any]] = []
    for blueprint_id in sorted(blueprints):
        blueprint = blueprints[blueprint_id]
        if str(blueprint.get("blueprint_template_no") or "") != "10":
            continue
        star_rows = attrs.get(blueprint_id) or {}
        attr_star1 = star_rows.get(1)
        if not isinstance(attr_star1, dict):
            continue
        rows.append(_joined_row(blueprint_id, blueprint, attr_star1, (terms.get(blueprint_id) or {}).get(1, {})))
        if len(rows) >= MAX_ROWS:
            break
    return rows


def _identity(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "blueprint_id": row.get("blueprint_id"),
        "item_id": row.get("item_id"),
        "name": row.get("name"),
        "fixed_skill_code": row.get("fixed_skill_code"),
    }


def _fingerprint(row: dict[str, Any], passive_codes: set[str]) -> dict[str, Any]:
    skill = str(row.get("fixed_skill_code") or "").strip()
    return {
        "fixed_skill_present": bool(skill),
        "passive_owner_present": skill in passive_codes if skill else False,
        "endow": row.get("endow"),
        "plaques_empty": _is_empty(row.get("plaques")),
        "correct_skill_absent": _is_empty(row.get("correct_skill")),
        "correct_term_id_absent": _is_empty(row.get("correct_term_id")),
        "base_attrs_e0100_e0200_e0300_zero": _base_attrs_zero(row.get("attr_star1") or {}),
    }


def _value_shape(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return f"bool:{str(value).lower()}"
    if isinstance(value, (int, float)):
        return f"number:{value}"
    if isinstance(value, str):
        return "string:empty" if not value else f"string:{value}"
    if isinstance(value, (list, tuple, dict)):
        return f"{type(value).__name__}:len={len(value)}"
    return type(value).__name__


def _cohort_field_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    flat_rows = [_flatten(row) for row in rows]
    paths = sorted({path for row in flat_rows for path in row})
    summary: dict[str, Any] = {}
    total = len(rows)
    for path in paths:
        present = [row[path] for row in flat_rows if path in row]
        shapes = Counter(_value_shape(value) for value in present)
        summary[path] = {
            "present": len(present),
            "missing": total - len(present),
            "shapes": dict(sorted(shapes.items())),
        }
    return summary


def trace_fixed_skill_cohort_diff(
    roots: list[tuple[str, Path]], *, activity: ActivityCallback | None = None
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    required_paths = (
        GUN_BLUEPRINT_ATTR_PATH,
        GUN_BLUEPRINT_DATA_PATH,
        GUN_BLUEPRINT_TERMS_PATH,
        PASSIVE_SKILL_PATH,
    )
    sources = {path: _find_source(roots, path) for path in required_paths}
    missing = [path for path, source in sources.items() if source is None]
    if missing:
        return {
            "status": "required-table-missing",
            "missing": missing,
            "record_counts": {"normal_weapon_blueprints": 0, "unresolved_cohort": 0, "resolved_control_cohort": 0},
        }

    activity("Missing Skill Forensics: comparing unresolved and resolved fixed-skill blueprint cohorts")
    attr_layer, attr_path = sources[GUN_BLUEPRINT_ATTR_PATH]  # type: ignore[misc]
    blueprint_layer, blueprint_path = sources[GUN_BLUEPRINT_DATA_PATH]  # type: ignore[misc]
    terms_layer, terms_path = sources[GUN_BLUEPRINT_TERMS_PATH]  # type: ignore[misc]
    passive_layer, passive_path = sources[PASSIVE_SKILL_PATH]  # type: ignore[misc]

    weapons = _weapon_rows(
        _parse_bindict(blueprint_path),
        _parse_bindict(attr_path),
        _parse_bindict(terms_path),
    )
    passive_codes = _collect_exact_codes(_parse_bindict(passive_path))

    unresolved: list[dict[str, Any]] = []
    controls: list[dict[str, Any]] = []
    for row in weapons:
        fp = _fingerprint(row, passive_codes)
        if not fp["fixed_skill_present"] or fp["endow"] is not False:
            continue
        if fp["passive_owner_present"]:
            controls.append(row)
        elif (
            fp["plaques_empty"]
            and fp["correct_skill_absent"]
            and fp["correct_term_id_absent"]
            and fp["base_attrs_e0100_e0200_e0300_zero"]
        ):
            unresolved.append(row)

    unresolved_summary = _cohort_field_summary(unresolved)
    control_summary = _cohort_field_summary(controls)
    discriminators = []
    for path in sorted(set(unresolved_summary) | set(control_summary)):
        left = unresolved_summary.get(path, {"present": 0, "missing": len(unresolved), "shapes": {}})
        right = control_summary.get(path, {"present": 0, "missing": len(controls), "shapes": {}})
        if left != right:
            discriminators.append({"field_path": path, "unresolved": left, "resolved_control": right})
        if len(discriminators) >= MAX_DIFF_PATHS:
            break

    return {
        "status": "complete",
        "source": {
            "gun_blueprint_attr_data": {"layer": attr_layer, "relative_path": GUN_BLUEPRINT_ATTR_PATH},
            "gun_blueprint_data": {"layer": blueprint_layer, "relative_path": GUN_BLUEPRINT_DATA_PATH},
            "gun_blueprint_terms_map_data": {"layer": terms_layer, "relative_path": GUN_BLUEPRINT_TERMS_PATH},
            "passive_skill_data": {"layer": passive_layer, "relative_path": PASSIVE_SKILL_PATH},
        },
        "record_counts": {
            "normal_weapon_blueprints": len(weapons),
            "passive_skill_codes": len(passive_codes),
            "unresolved_cohort": len(unresolved),
            "resolved_control_cohort": len(controls),
            "discriminating_field_paths": len(discriminators),
        },
        "unresolved_cohort": [
            {"identity": _identity(row), "fingerprint": _fingerprint(row, passive_codes)} for row in unresolved
        ],
        "resolved_control_cohort": [
            {"identity": _identity(row), "fingerprint": _fingerprint(row, passive_codes)} for row in controls
        ],
        "field_diff": discriminators,
        "policy": {
            "matching": "Cohorts use exact blueprint IDs, exact (blueprint_id, star) table keys, and exact passive_skill_data code membership only; no fuzzy or similar-ID matching.",
            "execution": "Installed Bindict tables are parsed read-only; game modules and bytecode are never executed.",
            "interpretation": "Field differences are structural evidence only and do not prove runtime mechanic semantics.",
            "publication": "Research-only; no player-facing weapon data is modified or promoted.",
        },
    }
