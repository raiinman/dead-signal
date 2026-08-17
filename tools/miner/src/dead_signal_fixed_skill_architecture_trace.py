"""Static architecture trace for unresolved weapon fixed-skill resolution.

This pass is deliberately narrow. It inspects only the exact PYC modules/functions
already implicated by fixed_skill_code forensics and groups their static metadata
into four research branches:

1. damage/passive mapping,
2. GunCore fixed-skill normalization,
3. star-skill/stardust resolution,
4. player-facing weapon-craft UI confirmation.

No Once Human module is imported or executed. PYC payloads are unmarshaled only.
"""
from __future__ import annotations

import marshal
import types
from collections import Counter
from pathlib import Path
from typing import Any, Callable

ActivityCallback = Callable[[str], None]
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_SCALAR_CONSTANTS = 96
MAX_SYMBOLS = 192

BRANCHES: dict[str, tuple[dict[str, Any], ...]] = {
    "damage_passive_mapping": (
        {
            "path": "dcs_extend/component/shoot_new/keyword/CompShootDamageSimulateClient.pyc",
            "functions": ("get_weapon_passive_skill_config",),
            "symbols": (
                "fixed_skill_code",
                "WEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG",
                "WEAPON_TO_PASSIVE",
                "gun_blueprint_attr_data",
                "passive_skill_damage_simulate_data",
            ),
        },
        {
            "path": "dcs_extend/component_server/CompSkillMgr.pyc",
            "functions": ("CompSkillMgrNpc._get_gun_ps_buff_id", "_get_gun_ps_buff_id"),
            "symbols": ("fixed_skill_code", "gun_blueprint_attr_data", "passive_skill_data", "buff"),
        },
    ),
    "guncore_normalization": (
        {
            "path": "game_common/guncore/GunCoreHelper.pyc",
            "functions": (
                "get_blueprint_fixed_skill",
                "init_fixed_skill",
                "climp_skill_code",
                "convert_data_skill_slots",
                "get_decompose_skill",
            ),
            "symbols": (
                "fixed_skill_code",
                "SKILL_CODE_LEN",
                "MAX_SKILL_LEVEL",
                "init_fixed_skill",
                "climp_skill_code",
                "convert_data_skill_slots",
                "get_decompose_skill",
            ),
        },
        {
            "path": "game_common/guncore/BluePrintHelper.pyc",
            "functions": (
                "get_blueprint_fixed_skill",
                "get_equip_blueprint_fixed_skill",
                "get_fixed_skill_default_data",
                "get_blueprint_fixed_skill_lv",
                "get_equip_blueprint_fixed_skill_lv",
            ),
            "symbols": (
                "fixed_skill_code",
                "gun_blueprint_attr_data",
                "equip_blueprint_attr_data",
                "package_fixed_skill_data",
                "equip_package_fixed_skill_data",
                "get_skill_data",
            ),
        },
    ),
    "star_stardust_resolution": (
        {
            "path": "dcs_extend/component/CompCamera.pyc",
            "functions": ("CompCameraOtherPlayer._get_gun_sp_track_time", "_get_gun_sp_track_time"),
            "symbols": (
                "fixed_skill_code",
                "skill_code",
                "star_skill_no",
                "stardust_gun_skill_data",
                "passive_skill_data",
                "skill_cast_time",
            ),
        },
        {
            "path": "dcs_extend/common/shoot_utility.pyc",
            "functions": ("get_star_cast_skill_behavior_name",),
            "symbols": (
                "fixed_skill",
                "skill_code",
                "star_skill_no",
                "stardust_gun_skill_data",
                "passive_skill_data",
                "skill_cast_time",
            ),
        },
    ),
    "player_facing_ui": (
        {
            "path": "ui/weapon_craft_part/ScrollViewItems.pyc",
            "functions": ("WRGunInfoPart.update_fixed_skills", "update_fixed_skills"),
            "symbols": (
                "PassiveSkillHelper",
                "get_passive_skill_name",
                "fixed_passive_skill",
                "skill_code",
                "skill_data",
                "fixed_skill",
            ),
        },
    ),
}


def _load_marshaled_root(raw: bytes) -> tuple[types.CodeType | None, str | None]:
    if len(raw) < 17:
        return None, "PYC file is too small"
    try:
        root = marshal.loads(raw[16:])
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(root, types.CodeType):
        return None, "marshal payload was not CodeType"
    return root, None


def _walk_code(code: types.CodeType, qualname: str = "<module>"):
    yield qualname, code
    occurrence: Counter[str] = Counter()
    for value in code.co_consts:
        if not isinstance(value, types.CodeType):
            continue
        occurrence[value.co_name] += 1
        suffix = f"#{occurrence[value.co_name]}" if occurrence[value.co_name] > 1 else ""
        child = value.co_name + suffix
        child_name = child if qualname == "<module>" else f"{qualname}.{child}"
        yield from _walk_code(value, child_name)


def _safe_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, tuple) and len(value) <= 12 and all(
        item is None or isinstance(item, (str, int, float, bool)) for item in value
    ):
        return list(value)
    return None


def _function_selected(qualname: str, co_name: str, requested: tuple[str, ...]) -> bool:
    q = qualname.casefold()
    n = co_name.casefold()
    for target in requested:
        t = target.casefold()
        if q == t or q.endswith("." + t) or n == t or q.endswith(t):
            return True
    return False


def _inspect_function(qualname: str, code: types.CodeType, symbols: tuple[str, ...]) -> dict[str, Any]:
    names = set(map(str, code.co_names))
    varnames = set(map(str, code.co_varnames))
    strings = {value for value in code.co_consts if isinstance(value, str)}
    universe = names | varnames | strings
    symbol_set = set(symbols)
    constants: list[Any] = []
    for value in code.co_consts:
        safe = _safe_scalar(value)
        if safe is not None and safe not in constants:
            constants.append(safe)
        if len(constants) >= MAX_SCALAR_CONSTANTS:
            break
    children = [value.co_name for value in code.co_consts if isinstance(value, types.CodeType)]
    return {
        "qualname": qualname,
        "co_name": code.co_name,
        "co_filename": code.co_filename,
        "co_firstlineno": code.co_firstlineno,
        "matched_target_symbols": sorted(symbol_set.intersection(universe)),
        "co_names": sorted(names)[:MAX_SYMBOLS],
        "co_varnames": sorted(varnames)[:MAX_SYMBOLS],
        "string_constants": sorted(strings)[:MAX_SYMBOLS],
        "safe_scalar_constants": constants,
        "nested_code_names": children[:MAX_SYMBOLS],
    }


def _find_source(roots: list[tuple[str, Path]], relative: str) -> tuple[str, Path] | None:
    # Prefer current, then base, matching the rest of Miner snapshot precedence.
    for layer, root in roots:
        path = root / Path(relative)
        if path.is_file():
            return layer, path
    return None


def trace_fixed_skill_architecture(
    roots: list[tuple[str, Path]],
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    branches: dict[str, Any] = {}
    files_found = 0
    functions_found = 0
    exact_symbol_matches = 0
    errors: list[dict[str, str]] = []

    for branch_name, targets in BRANCHES.items():
        activity(f"Missing Skill Forensics: architecture branch {branch_name}")
        branch_rows: list[dict[str, Any]] = []
        for target in targets:
            relative = str(target["path"])
            located = _find_source(roots, relative)
            if located is None:
                branch_rows.append({"relative_path": relative, "status": "file-not-found", "functions": []})
                continue
            layer, path = located
            try:
                size = path.stat().st_size
                if size > MAX_FILE_BYTES:
                    branch_rows.append({
                        "layer": layer,
                        "relative_path": relative,
                        "status": "file-too-large",
                        "file_size": size,
                        "functions": [],
                    })
                    continue
                raw = path.read_bytes()
            except OSError as exc:
                errors.append({"relative_path": relative, "error": f"{type(exc).__name__}: {exc}"})
                branch_rows.append({"layer": layer, "relative_path": relative, "status": "read-error", "functions": []})
                continue

            files_found += 1
            root, error = _load_marshaled_root(raw)
            if root is None:
                errors.append({"relative_path": relative, "error": error or "marshal decode failed"})
                branch_rows.append({
                    "layer": layer,
                    "relative_path": relative,
                    "status": "marshal-error",
                    "file_size": size,
                    "functions": [],
                })
                continue

            requested_functions = tuple(target["functions"])
            symbols = tuple(target["symbols"])
            exact_raw_symbols = sorted(symbol for symbol in symbols if symbol.encode("utf-8") in raw)
            exact_symbol_matches += len(exact_raw_symbols)
            functions = []
            for qualname, code in _walk_code(root):
                if not _function_selected(qualname, code.co_name, requested_functions):
                    continue
                functions.append(_inspect_function(qualname, code, symbols))
            functions_found += len(functions)
            branch_rows.append({
                "layer": layer,
                "relative_path": relative,
                "status": "complete",
                "file_size": size,
                "requested_functions": list(requested_functions),
                "target_symbols": list(symbols),
                "exact_raw_symbols": exact_raw_symbols,
                "functions": functions,
            })
        branches[branch_name] = {
            "targets": branch_rows,
            "files_found": sum(1 for row in branch_rows if row.get("status") == "complete"),
            "functions_found": sum(len(row.get("functions") or []) for row in branch_rows),
        }

    status = "raw-source-roots-unavailable" if not roots else ("complete-with-errors" if errors else "complete")
    return {
        "status": status,
        "record_counts": {
            "branches": len(BRANCHES),
            "target_files": sum(len(rows) for rows in BRANCHES.values()),
            "files_found": files_found,
            "functions_found": functions_found,
            "exact_raw_symbol_matches": exact_symbol_matches,
            "errors": len(errors),
        },
        "branches": branches,
        "errors": errors,
        "policy": {
            "scope": "Only exact, preselected fixed-skill resolution modules/functions are inspected; there is no broad corpus traversal.",
            "matching": "Function selection and reported relationship symbols are exact static CodeType/raw-byte evidence.",
            "execution": "PYC payloads are unmarshaled only; Once Human modules and game bytecode are never executed.",
            "interpretation": "Names/constants establish static adjacency only; they do not by themselves prove runtime mapping values or player-facing mechanic semantics.",
        },
        "next_step": (
            "Use damage_passive_mapping to identify mapping/config relationships; guncore_normalization to determine whether skill codes are transformed; "
            "star_stardust_resolution to test star_skill_no/stardust handoff; and player_facing_ui to confirm the final displayed passive-skill identity."
        ),
    }
