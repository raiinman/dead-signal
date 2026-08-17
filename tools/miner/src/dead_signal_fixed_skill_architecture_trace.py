"""Static architecture trace for unresolved weapon fixed-skill resolution.

This pass inspects every exact PYC module/function currently implicated by
fixed_skill_code forensics and groups static metadata into six research branches:

1. damage/passive mapping,
2. GunCore / BluePrint fixed-skill normalization,
3. PassiveSkillHelper / SkillDataHelper fallback resolution,
4. star-skill/stardust resolution,
5. server-side buff resolution,
6. player-facing weapon-craft UI confirmation.

A corpus-wide closeout discovery layer also enumerates exact static candidates
for the remaining ownerless-skill hypotheses: skill constants, climp callers,
passive-table assembly, packaged fixed skills, damage-simulation indirection,
server initialization, blueprint-identity fallbacks, and compatibility/override
logic. No Once Human module is imported or executed. PYC payloads are unmarshaled
only.
"""
from __future__ import annotations

import marshal
import types
from collections import Counter
from pathlib import Path
from typing import Any, Callable

ActivityCallback = Callable[[str], None]
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_SCALAR_CONSTANTS = 192
MAX_SYMBOLS = 256
MAX_RAW_WORDCODE_ROWS = 768
MAX_CLOSEOUT_FILES_PER_ROOT = 100000
MAX_CLOSEOUT_CANDIDATES_PER_CATEGORY = 256

BRANCHES: dict[str, tuple[dict[str, Any], ...]] = {
    "damage_passive_mapping": (
        {
            "path": "dcs_extend/component/shoot_new/keyword/CompShootDamageSimulateClient.pyc",
            "functions": ("<module>", "get_weapon_passive_skill_config"),
            "symbols": (
                "fixed_skill_code",
                "WEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG",
                "WEAPON_TO_PASSIVE",
                "gun_blueprint_attr_data",
                "passive_skill_damage_simulate_data",
                "skill_code",
                "weapon_no",
                "blueprint_no",
            ),
        },
    ),
    "guncore_normalization": (
        {
            "path": "game_common/guncore/GunCoreHelper.pyc",
            "functions": (
                "<module>",
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
                "skill_code",
            ),
        },
        {
            "path": "game_common/guncore/BluePrintHelper.pyc",
            "functions": (
                "<module>",
                "get_blueprint_fixed_skill",
                "get_equip_blueprint_fixed_skill",
                "get_fixed_skill_default_data",
                "get_blueprint_fixed_skill_lv",
                "get_equip_blueprint_fixed_skill_lv",
                "get_skill_data",
            ),
            "symbols": (
                "fixed_skill_code",
                "fixed_skill_lv",
                "gun_blueprint_attr_data",
                "equip_blueprint_attr_data",
                "package_fixed_skill_data",
                "equip_package_fixed_skill_data",
                "get_skill_data",
                "passive_skill_data",
                "common_skill_data",
                "skill_data",
                "blueprint_no",
            ),
        },
        {
            "path": "game_common/guncore/SkillConst.pyc",
            "functions": ("<module>",),
            "symbols": (
                "SKILL_CODE_LEN",
                "MAX_SKILL_LEVEL",
                "ACTIVE_TABLE",
                "PASSIVE_TABLE",
                "active_skill_data",
                "passive_skill_data",
                "AS",
                "PS",
                "WS",
                "YC",
            ),
        },
    ),
    "helper_fallback_resolution": (
        {
            "path": "game_common/guncore/PassiveSkillHelper.pyc",
            "functions": (
                "<module>",
                "is_fixed_skill",
                "check_is_passive_skill",
                "is_skill_exist",
                "get_passive_skill_name",
                "get_skill_name",
                "get_skill_description",
                "get_passive_skill_desc",
                "get_passive_skill_data",
            ),
            "symbols": (
                "fixed_skill",
                "fixed_passive_skill",
                "passive_skill_data",
                "common_skill_data",
                "skill_data",
                "skill_code",
                "name",
                "description",
                "discription",
                "copywriting",
                "get_passive_skill_name",
                "DataMgr",
            ),
        },
        {
            "path": "game_common/guncore/SkillDataHelper.pyc",
            "functions": (
                "<module>",
                "is_fixed_skill",
                "is_passive",
                "check_is_passive_skill",
                "is_skill_exist",
                "get_table_name",
                "get_skill_data",
                "get_skill_name",
                "get_skill_description",
                "get_skill_desc",
            ),
            "symbols": (
                "fixed_skill",
                "passive_skill_data",
                "common_skill_data",
                "skill_data",
                "skill_code",
                "table_name",
                "get_table_name",
                "is_passive",
                "ACTIVE_TABLE",
                "PASSIVE_TABLE",
                "DataMgr",
                "name",
                "description",
                "discription",
                "copywriting",
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
    "server_buff_resolution": (
        {
            "path": "dcs_extend/component_server/CompSkillMgr.pyc",
            "functions": (
                "<module>",
                "CompSkillMgrNpc._get_gun_ps_buff_id",
                "_get_gun_ps_buff_id",
                "_get_ps_buff_id",
                "_check_buff_need_pause",
            ),
            "symbols": (
                "fixed_skill_code",
                "gun_blueprint_attr_data",
                "passive_skill_data",
                "skill_code",
                "buff_id",
                "buff",
                "init",
                "equip",
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
                "label_skill_desc",
                "label_skill_passivename",
                "discription",
                "copywriting",
            ),
        },
    ),
}

CLOSEOUT_SYMBOLS = (
    "SKILL_CODE_LEN",
    "MAX_SKILL_LEVEL",
    "climp_skill_code",
    "fixed_skill_code",
    "fixed_passive_skill",
    "package_fixed_skill_data",
    "equip_package_fixed_skill_data",
    "passive_skill_data",
    "passive_skill_damage_simulate_data",
    "common_data",
    "ACTIVE_TABLE",
    "PASSIVE_TABLE",
    "DataMgr",
    "WEAPON_TO_PASSIVE",
    "WEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG",
    "gun_blueprint_attr_data",
    "blueprint_no",
    "prototype_no",
    "weapon_no",
    "gun_no",
    "gun_id",
    "item_id",
    "buff_id",
    "skill_code",
)

COMPATIBILITY_TOKENS = (
    "legacy",
    "compat",
    "deprecated",
    "migration",
    "override",
    "replace",
    "replacement",
    "remap",
    "mapping",
    "convert",
    "old_skill",
    "skill_patch",
    "season_skill",
    "weapon_skill",
    "fixed_skill",
)

CLOSEOUT_CATEGORIES = (
    "skill_constants",
    "climp_callers",
    "passive_table_assembly",
    "package_fixed_skill",
    "damage_sim_indirection",
    "server_weapon_initializers",
    "blueprint_identity_fallbacks",
    "compatibility_overrides",
)


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
    if isinstance(value, tuple) and len(value) <= 24 and all(
        item is None or isinstance(item, (str, int, float, bool)) for item in value
    ):
        return list(value)
    return None


def _indexed_values(values: tuple[Any, ...], *, scalars_only: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, value in enumerate(values):
        if scalars_only:
            safe = _safe_scalar(value)
            if safe is None:
                continue
            rendered = safe
        else:
            rendered = str(value)
        rows.append({"index": index, "value": rendered})
        if len(rows) >= MAX_SYMBOLS:
            break
    return rows


def _raw_wordcode(code: types.CodeType) -> tuple[list[dict[str, int]], bool]:
    """Return exact raw CPython-style 2-byte wordcode without interpreting opcodes."""
    raw = bytes(code.co_code)
    rows: list[dict[str, int]] = []
    for offset in range(0, len(raw) - 1, 2):
        rows.append({"offset": offset, "opcode": raw[offset], "arg": raw[offset + 1]})
        if len(rows) >= MAX_RAW_WORDCODE_ROWS:
            return rows, offset + 2 < len(raw)
    if len(raw) % 2:
        rows.append({"offset": len(raw) - 1, "opcode": raw[-1], "arg": -1})
    return rows, False


def _function_selected(qualname: str, co_name: str, requested: tuple[str, ...]) -> bool:
    q = qualname.casefold()
    n = co_name.casefold()
    for target in requested:
        t = target.casefold()
        if q == t or q.endswith("." + t) or n == t or n == t.split(".")[-1] or q.endswith(t):
            return True
    return False


def _function_universe(code: types.CodeType) -> set[str]:
    values = set(map(str, code.co_names)) | set(map(str, code.co_varnames))
    values.update(value for value in code.co_consts if isinstance(value, str))
    return values


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
    wordcode, wordcode_truncated = _raw_wordcode(code)
    return {
        "qualname": qualname,
        "co_name": code.co_name,
        "co_filename": code.co_filename,
        "co_firstlineno": code.co_firstlineno,
        "code_length": len(code.co_code),
        "matched_target_symbols": sorted(symbol_set.intersection(universe)),
        "co_names": sorted(names)[:MAX_SYMBOLS],
        "co_names_indexed": _indexed_values(tuple(code.co_names)),
        "co_varnames": sorted(varnames)[:MAX_SYMBOLS],
        "co_varnames_indexed": _indexed_values(tuple(code.co_varnames)),
        "string_constants": sorted(strings)[:MAX_SYMBOLS],
        "safe_scalar_constants": constants,
        "co_consts_indexed": _indexed_values(tuple(code.co_consts), scalars_only=True),
        "raw_wordcode": wordcode,
        "raw_wordcode_truncated": wordcode_truncated,
        "nested_code_names": children[:MAX_SYMBOLS],
    }


def _find_source(roots: list[tuple[str, Path]], relative: str) -> tuple[str, Path] | None:
    for layer, root in roots:
        path = root / Path(relative)
        if path.is_file():
            return layer, path
    return None


def _category_matches(relative: str, qualname: str, universe: set[str]) -> list[str]:
    lower_path = relative.casefold()
    lower_qual = qualname.casefold()
    lower_values = {value.casefold() for value in universe}
    matches: list[str] = []

    if "skill_code_len" in lower_values or "skillconst" in lower_path:
        matches.append("skill_constants")
    if "climp_skill_code" in lower_values:
        matches.append("climp_callers")
    if (
        "common_data" in lower_values
        and ({"passive_skill_data", "passive_table", "active_table", "datamgr"} & lower_values)
    ):
        matches.append("passive_table_assembly")
    if {"package_fixed_skill_data", "equip_package_fixed_skill_data"} & lower_values:
        matches.append("package_fixed_skill")
    if {
        "passive_skill_damage_simulate_data",
        "weapon_to_passive",
        "weapon_passive_to_skill_damage_config",
    } & lower_values:
        matches.append("damage_sim_indirection")
    if "fixed_skill_code" in lower_values and any(
        token in lower_qual or token in lower_path
        for token in ("init", "create", "equip", "spawn", "skillmgr", "weapon", "gun")
    ):
        matches.append("server_weapon_initializers")
    if "gun_blueprint_attr_data" in lower_values and (
        {"prototype_no", "weapon_no", "gun_no", "gun_id", "item_id", "blueprint_no"} & lower_values
    ) and ({"skill_code", "fixed_skill_code", "buff_id", "passive_skill_data"} & lower_values):
        matches.append("blueprint_identity_fallbacks")
    if any(token in lower_path or token in lower_qual or token in lower_values for token in COMPATIBILITY_TOKENS):
        if {"skill_code", "fixed_skill_code", "passive_skill_data", "climp_skill_code"} & lower_values or "skill" in lower_path:
            matches.append("compatibility_overrides")
    return matches


def _compact_candidate(layer: str, relative: str, qualname: str, code: types.CodeType) -> dict[str, Any]:
    universe = _function_universe(code)
    exact = sorted(set(CLOSEOUT_SYMBOLS).intersection(universe))
    compat = sorted(
        token for token in COMPATIBILITY_TOKENS
        if token in relative.casefold()
        or token in qualname.casefold()
        or any(token == value.casefold() or token in value.casefold() for value in universe)
    )
    safe_constants: list[Any] = []
    for value in code.co_consts:
        safe = _safe_scalar(value)
        if safe is not None and safe not in safe_constants:
            safe_constants.append(safe)
        if len(safe_constants) >= 48:
            break
    return {
        "layer": layer,
        "relative_path": relative,
        "qualname": qualname,
        "co_name": code.co_name,
        "co_firstlineno": code.co_firstlineno,
        "matched_exact_symbols": exact,
        "matched_compatibility_tokens": compat,
        "safe_scalar_constants": safe_constants,
        "co_names": sorted(map(str, code.co_names))[:96],
        "co_varnames": sorted(map(str, code.co_varnames))[:96],
    }


def _discover_closeout_candidates(
    roots: list[tuple[str, Path]],
    *,
    activity: ActivityCallback,
) -> dict[str, Any]:
    categories: dict[str, list[dict[str, Any]]] = {name: [] for name in CLOSEOUT_CATEGORIES}
    seen: dict[str, set[tuple[str, str]]] = {name: set() for name in CLOSEOUT_CATEGORIES}
    files_scanned = 0
    files_with_target_bytes = 0
    marshal_decoded = 0
    roots_truncated: list[str] = []
    exact_tokens = {symbol: symbol.encode("utf-8") for symbol in CLOSEOUT_SYMBOLS}
    compat_bytes = {token: token.encode("utf-8") for token in COMPATIBILITY_TOKENS}

    for layer, root in roots:
        activity(f"Missing Skill Forensics: closeout corpus discovery in {layer}")
        layer_count = 0
        for path in root.rglob("*.pyc"):
            layer_count += 1
            if layer_count > MAX_CLOSEOUT_FILES_PER_ROOT:
                roots_truncated.append(layer)
                break
            files_scanned += 1
            try:
                size = path.stat().st_size
                if size > MAX_FILE_BYTES:
                    continue
                raw = path.read_bytes()
            except OSError:
                continue
            relative = path.resolve().relative_to(root).as_posix()
            lower_relative = relative.casefold()
            has_exact = any(token in raw for token in exact_tokens.values())
            has_compat = any(token in raw or name in lower_relative for name, token in compat_bytes.items())
            if not has_exact and not has_compat and "skillconst" not in lower_relative:
                continue
            files_with_target_bytes += 1
            root_code, error = _load_marshaled_root(raw)
            if root_code is None:
                continue
            marshal_decoded += 1
            for qualname, code in _walk_code(root_code):
                universe = _function_universe(code)
                matched_categories = _category_matches(relative, qualname, universe)
                if not matched_categories:
                    continue
                row = None
                for category in matched_categories:
                    key = (relative, qualname)
                    if key in seen[category] or len(categories[category]) >= MAX_CLOSEOUT_CANDIDATES_PER_CATEGORY:
                        continue
                    seen[category].add(key)
                    if row is None:
                        row = _compact_candidate(layer, relative, qualname, code)
                    categories[category].append(row)

    return {
        "status": "raw-source-roots-unavailable" if not roots else ("partial-limit" if roots_truncated else "complete"),
        "record_counts": {
            "files_scanned": files_scanned,
            "files_with_target_bytes": files_with_target_bytes,
            "marshal_decoded_target_files": marshal_decoded,
            "categories": len(CLOSEOUT_CATEGORIES),
            "candidates": sum(len(rows) for rows in categories.values()),
            "by_category": {name: len(rows) for name, rows in categories.items()},
        },
        "roots_truncated_at_limit": sorted(set(roots_truncated)),
        "categories": categories,
        "policy": {
            "matching": "Exact code/name/string symbols and explicit compatibility tokens only; candidates are static adjacency evidence, not semantic proof.",
            "execution": "PYC payloads are unmarshaled only; Once Human modules and bytecode are never executed.",
            "limits": f"At most {MAX_CLOSEOUT_FILES_PER_ROOT} PYC files per root and {MAX_CLOSEOUT_CANDIDATES_PER_CATEGORY} candidates per category are retained.",
        },
    }


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

    closeout_discovery = _discover_closeout_candidates(roots, activity=activity)
    status = "raw-source-roots-unavailable" if not roots else ("complete-with-errors" if errors else "complete")
    return {
        "status": status,
        "record_counts": {
            "branches": len(BRANCHES),
            "target_files": sum(len(rows) for rows in BRANCHES.values()),
            "files_found": files_found,
            "functions_found": functions_found,
            "exact_raw_symbol_matches": exact_symbol_matches,
            "closeout_files_scanned": closeout_discovery["record_counts"]["files_scanned"],
            "closeout_candidates": closeout_discovery["record_counts"]["candidates"],
            "closeout_candidates_by_category": closeout_discovery["record_counts"]["by_category"],
            "errors": len(errors),
        },
        "branches": branches,
        "closeout_discovery": closeout_discovery,
        "errors": errors,
        "policy": {
            "scope": "All currently known high-value fixed-skill resolution modules/functions are inspected together, plus an exact-symbol corpus closeout scan for remaining routing/assembly/compatibility hypotheses.",
            "matching": "Function selection and reported relationship symbols are exact static CodeType/raw-byte evidence; closeout candidates require exact symbols or explicit compatibility tokens.",
            "execution": "PYC payloads are unmarshaled only; Once Human modules and game bytecode are never executed.",
            "wordcode": "Raw 2-byte instruction words and indexed name/constant pools are preserved without applying the local Python opcode table.",
            "interpretation": "Names/constants establish static adjacency only; raw wordcode preserves exact bytes but requires version-correct interpretation before semantic claims.",
        },
        "next_step": (
            "Resolve the closeout categories in order: skill_constants, climp_callers, passive_table_assembly, package_fixed_skill, damage_sim_indirection, "
            "server_weapon_initializers, blueprint_identity_fallbacks, compatibility_overrides. Follow only exact returned identifiers into NeoX owners. "
            "If every category fails to produce an alternate exact owner for the unresolved WS codes, classify the fixed-skill references internally as exhausted/dangling-current-corpus evidence while keeping player-facing mechanics unresolved."
        ),
    }
