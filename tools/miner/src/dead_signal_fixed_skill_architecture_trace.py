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
    "damage_passive_mapping": ({
        "path": "dcs_extend/component/shoot_new/keyword/CompShootDamageSimulateClient.pyc",
        "functions": ("<module>", "get_weapon_passive_skill_config"),
        "symbols": ("fixed_skill_code", "WEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG", "WEAPON_TO_PASSIVE", "gun_blueprint_attr_data", "passive_skill_damage_simulate_data", "skill_code", "weapon_no", "blueprint_no"),
    },),
    "guncore_normalization": ({
        "path": "game_common/guncore/GunCoreHelper.pyc",
        "functions": ("<module>", "get_blueprint_fixed_skill", "init_fixed_skill", "climp_skill_code", "convert_data_skill_slots", "get_decompose_skill"),
        "symbols": ("fixed_skill_code", "SKILL_CODE_LEN", "MAX_SKILL_LEVEL", "init_fixed_skill", "climp_skill_code", "convert_data_skill_slots", "get_decompose_skill", "skill_code"),
    }, {
        "path": "game_common/guncore/BluePrintHelper.pyc",
        "functions": ("<module>", "get_blueprint_fixed_skill", "get_equip_blueprint_fixed_skill", "get_fixed_skill_default_data", "get_blueprint_fixed_skill_lv", "get_equip_blueprint_fixed_skill_lv", "get_skill_data"),
        "symbols": ("fixed_skill_code", "fixed_skill_lv", "gun_blueprint_attr_data", "equip_blueprint_attr_data", "package_fixed_skill_data", "equip_package_fixed_skill_data", "get_skill_data", "passive_skill_data", "common_skill_data", "skill_data", "blueprint_no"),
    }, {
        "path": "game_common/guncore/SkillConst.pyc",
        "functions": ("<module>",),
        "symbols": ("SKILL_CODE_LEN", "MAX_SKILL_LEVEL", "ACTIVE_TABLE", "PASSIVE_TABLE", "active_skill_data", "passive_skill_data", "AS", "PS", "WS", "YC"),
    }),
    "helper_fallback_resolution": ({
        "path": "game_common/guncore/PassiveSkillHelper.pyc",
        "functions": ("<module>", "is_fixed_skill", "check_is_passive_skill", "is_skill_exist", "get_passive_skill_name", "get_skill_name", "get_skill_description", "get_passive_skill_desc", "get_passive_skill_data"),
        "symbols": ("fixed_skill", "fixed_passive_skill", "passive_skill_data", "common_skill_data", "skill_data", "skill_code", "name", "description", "discription", "copywriting", "get_passive_skill_name", "DataMgr"),
    }, {
        "path": "game_common/guncore/SkillDataHelper.pyc",
        "functions": ("<module>", "is_fixed_skill", "is_passive", "check_is_passive_skill", "is_skill_exist", "get_table_name", "get_skill_data", "get_skill_name", "get_skill_description", "get_skill_desc"),
        "symbols": ("fixed_skill", "passive_skill_data", "common_skill_data", "skill_data", "skill_code", "table_name", "get_table_name", "is_passive", "ACTIVE_TABLE", "PASSIVE_TABLE", "DataMgr", "name", "description", "discription", "copywriting"),
    }),
    "star_stardust_resolution": ({
        "path": "dcs_extend/component/CompCamera.pyc",
        "functions": ("CompCameraOtherPlayer._get_gun_sp_track_time", "_get_gun_sp_track_time"),
        "symbols": ("fixed_skill_code", "skill_code", "star_skill_no", "stardust_gun_skill_data", "passive_skill_data", "skill_cast_time"),
    }, {
        "path": "dcs_extend/common/shoot_utility.pyc",
        "functions": ("get_star_cast_skill_behavior_name",),
        "symbols": ("fixed_skill", "skill_code", "star_skill_no", "stardust_gun_skill_data", "passive_skill_data", "skill_cast_time"),
    }),
    "server_buff_resolution": ({
        "path": "dcs_extend/component_server/CompSkillMgr.pyc",
        "functions": ("<module>", "CompSkillMgrNpc._get_gun_ps_buff_id", "_get_gun_ps_buff_id", "_get_ps_buff_id", "_check_buff_need_pause"),
        "symbols": ("fixed_skill_code", "gun_blueprint_attr_data", "passive_skill_data", "skill_code", "buff_id", "buff", "init", "equip"),
    },),
    "player_facing_ui": ({
        "path": "ui/weapon_craft_part/ScrollViewItems.pyc",
        "functions": ("WRGunInfoPart.update_fixed_skills", "update_fixed_skills"),
        "symbols": ("PassiveSkillHelper", "get_passive_skill_name", "fixed_passive_skill", "skill_code", "skill_data", "fixed_skill", "label_skill_desc", "label_skill_passivename", "discription", "copywriting"),
    },),
}

CLOSEOUT_SYMBOLS = (
    "SKILL_CODE_LEN", "MAX_SKILL_LEVEL", "climp_skill_code", "fixed_skill_code", "fixed_passive_skill",
    "package_fixed_skill_data", "equip_package_fixed_skill_data", "passive_skill_data", "passive_skill_damage_simulate_data",
    "common_data", "ACTIVE_TABLE", "PASSIVE_TABLE", "DataMgr", "WEAPON_TO_PASSIVE", "WEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG",
    "gun_blueprint_attr_data", "blueprint_no", "prototype_no", "weapon_no", "gun_no", "gun_id", "item_id", "buff_id", "skill_code",
)
COMPATIBILITY_TOKENS = ("legacy", "compat", "deprecated", "migration", "override", "replace", "replacement", "remap", "mapping", "convert", "old_skill", "skill_patch", "season_skill", "weapon_skill", "fixed_skill")
CLOSEOUT_CATEGORIES = ("skill_constants", "climp_callers", "passive_table_assembly", "package_fixed_skill", "damage_sim_indirection", "server_weapon_initializers", "blueprint_identity_fallbacks", "compatibility_overrides")


def _load_marshaled_root(raw: bytes):
    if len(raw) < 17:
        return None, "PYC file is too small"
    try:
        root = marshal.loads(raw[16:])
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    return (root, None) if isinstance(root, types.CodeType) else (None, "marshal payload was not CodeType")


def _walk_code(code: types.CodeType, qualname: str = "<module>"):
    yield qualname, code
    occurrence: Counter[str] = Counter()
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            occurrence[value.co_name] += 1
            suffix = f"#{occurrence[value.co_name]}" if occurrence[value.co_name] > 1 else ""
            child = value.co_name + suffix
            child_name = child if qualname == "<module>" else f"{qualname}.{child}"
            yield from _walk_code(value, child_name)


def _safe_scalar(value: Any):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, tuple) and len(value) <= 24 and all(item is None or isinstance(item, (str, int, float, bool)) for item in value):
        return list(value)
    return None


def _indexed_values(values: tuple[Any, ...], *, scalars_only: bool = False):
    rows = []
    for index, value in enumerate(values):
        rendered = _safe_scalar(value) if scalars_only else str(value)
        if scalars_only and rendered is None:
            continue
        rows.append({"index": index, "value": rendered})
        if len(rows) >= MAX_SYMBOLS:
            break
    return rows


def _raw_wordcode(code: types.CodeType):
    raw = bytes(code.co_code)
    rows = []
    for offset in range(0, len(raw) - 1, 2):
        rows.append({"offset": offset, "opcode": raw[offset], "arg": raw[offset + 1]})
        if len(rows) >= MAX_RAW_WORDCODE_ROWS:
            return rows, offset + 2 < len(raw)
    if len(raw) % 2:
        rows.append({"offset": len(raw) - 1, "opcode": raw[-1], "arg": -1})
    return rows, False


def _function_selected(qualname: str, co_name: str, requested: tuple[str, ...]) -> bool:
    q, n = qualname.casefold(), co_name.casefold()
    for target in requested:
        t = target.casefold()
        if q == t or q.endswith("." + t) or n == t or n == t.split(".")[-1] or q.endswith(t):
            return True
    return False


def _universe(code: types.CodeType) -> set[str]:
    out = set(map(str, code.co_names)) | set(map(str, code.co_varnames))
    out.update(v for v in code.co_consts if isinstance(v, str))
    return out


def _inspect_function(qualname: str, code: types.CodeType, symbols: tuple[str, ...]):
    names, varnames = set(map(str, code.co_names)), set(map(str, code.co_varnames))
    strings = {v for v in code.co_consts if isinstance(v, str)}
    universe = names | varnames | strings
    constants = []
    for value in code.co_consts:
        safe = _safe_scalar(value)
        if safe is not None and safe not in constants:
            constants.append(safe)
        if len(constants) >= MAX_SCALAR_CONSTANTS:
            break
    wordcode, truncated = _raw_wordcode(code)
    return {
        "qualname": qualname, "co_name": code.co_name, "co_filename": code.co_filename, "co_firstlineno": code.co_firstlineno,
        "code_length": len(code.co_code), "matched_target_symbols": sorted(set(symbols).intersection(universe)),
        "co_names": sorted(names)[:MAX_SYMBOLS], "co_names_indexed": _indexed_values(tuple(code.co_names)),
        "co_varnames": sorted(varnames)[:MAX_SYMBOLS], "co_varnames_indexed": _indexed_values(tuple(code.co_varnames)),
        "string_constants": sorted(strings)[:MAX_SYMBOLS], "safe_scalar_constants": constants,
        "co_consts_indexed": _indexed_values(tuple(code.co_consts), scalars_only=True), "raw_wordcode": wordcode,
        "raw_wordcode_truncated": truncated, "nested_code_names": [v.co_name for v in code.co_consts if isinstance(v, types.CodeType)][:MAX_SYMBOLS],
    }


def _find_source(roots, relative):
    for layer, root in roots:
        path = root / Path(relative)
        if path.is_file():
            return layer, path
    return None


def _category_matches(relative: str, qualname: str, universe: set[str]):
    lp, lq, lv = relative.casefold(), qualname.casefold(), {v.casefold() for v in universe}
    hits = []
    if "skill_code_len" in lv or "skillconst" in lp:
        hits.append("skill_constants")
    if "climp_skill_code" in lv:
        hits.append("climp_callers")
    if "common_data" in lv and ({"passive_skill_data", "passive_table", "active_table", "datamgr"} & lv):
        hits.append("passive_table_assembly")
    if {"package_fixed_skill_data", "equip_package_fixed_skill_data"} & lv:
        hits.append("package_fixed_skill")
    if {"passive_skill_damage_simulate_data", "weapon_to_passive", "weapon_passive_to_skill_damage_config"} & lv:
        hits.append("damage_sim_indirection")
    if "fixed_skill_code" in lv and any(t in lq or t in lp for t in ("init", "create", "equip", "spawn", "skillmgr", "weapon", "gun")):
        hits.append("server_weapon_initializers")
    if "gun_blueprint_attr_data" in lv and ({"prototype_no", "weapon_no", "gun_no", "gun_id", "item_id", "blueprint_no"} & lv) and ({"skill_code", "fixed_skill_code", "buff_id", "passive_skill_data"} & lv):
        hits.append("blueprint_identity_fallbacks")
    if any(t in lp or t in lq or t in lv for t in COMPATIBILITY_TOKENS):
        if {"skill_code", "fixed_skill_code", "passive_skill_data", "climp_skill_code"} & lv or "skill" in lp:
            hits.append("compatibility_overrides")
    return hits


def _compact_candidate(layer, relative, qualname, code):
    universe = _universe(code)
    constants = []
    for value in code.co_consts:
        safe = _safe_scalar(value)
        if safe is not None and safe not in constants:
            constants.append(safe)
        if len(constants) >= 48:
            break
    return {
        "layer": layer, "relative_path": relative, "qualname": qualname, "co_name": code.co_name,
        "co_firstlineno": code.co_firstlineno, "matched_exact_symbols": sorted(set(CLOSEOUT_SYMBOLS).intersection(universe)),
        "matched_compatibility_tokens": sorted(t for t in COMPATIBILITY_TOKENS if t in relative.casefold() or t in qualname.casefold() or any(t == v.casefold() or t in v.casefold() for v in universe)),
        "safe_scalar_constants": constants, "co_names": sorted(map(str, code.co_names))[:96], "co_varnames": sorted(map(str, code.co_varnames))[:96],
    }


def _discover_closeout_candidates(roots, *, activity):
    categories = {name: [] for name in CLOSEOUT_CATEGORIES}
    seen = {name: set() for name in CLOSEOUT_CATEGORIES}
    files_scanned = files_with_target_bytes = marshal_decoded = 0
    roots_truncated = []
    exact_bytes = [s.encode("utf-8") for s in CLOSEOUT_SYMBOLS]
    compat_bytes = [(s, s.encode("utf-8")) for s in COMPATIBILITY_TOKENS]
    for layer, root in roots:
        activity(f"Missing Skill Forensics: closeout corpus discovery in {layer}")
        for idx, path in enumerate(root.rglob("*.pyc"), start=1):
            if idx > MAX_CLOSEOUT_FILES_PER_ROOT:
                roots_truncated.append(layer)
                break
            files_scanned += 1
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
                raw = path.read_bytes()
            except OSError:
                continue
            try:
                relative = path.relative_to(root).as_posix()
            except ValueError:
                relative = path.name
            lr = relative.casefold()
            if not any(t in raw for t in exact_bytes) and not any(b in raw or n in lr for n, b in compat_bytes) and "skillconst" not in lr:
                continue
            files_with_target_bytes += 1
            root_code, _error = _load_marshaled_root(raw)
            if root_code is None:
                continue
            marshal_decoded += 1
            for qualname, code in _walk_code(root_code):
                matched = _category_matches(relative, qualname, _universe(code))
                row = None
                for category in matched:
                    key = (relative, qualname)
                    if key in seen[category] or len(categories[category]) >= MAX_CLOSEOUT_CANDIDATES_PER_CATEGORY:
                        continue
                    seen[category].add(key)
                    row = row or _compact_candidate(layer, relative, qualname, code)
                    categories[category].append(row)
    return {
        "status": "raw-source-roots-unavailable" if not roots else ("partial-limit" if roots_truncated else "complete"),
        "record_counts": {"files_scanned": files_scanned, "files_with_target_bytes": files_with_target_bytes, "marshal_decoded_target_files": marshal_decoded, "categories": len(CLOSEOUT_CATEGORIES), "candidates": sum(map(len, categories.values())), "by_category": {k: len(v) for k, v in categories.items()}},
        "roots_truncated_at_limit": sorted(set(roots_truncated)), "categories": categories,
        "policy": {"matching": "Exact code/name/string symbols and explicit compatibility tokens only; candidates are static adjacency evidence, not semantic proof.", "execution": "PYC payloads are unmarshaled only; Once Human modules and bytecode are never executed.", "limits": f"At most {MAX_CLOSEOUT_FILES_PER_ROOT} PYC files per root and {MAX_CLOSEOUT_CANDIDATES_PER_CATEGORY} candidates per category are retained."},
    }


def trace_fixed_skill_architecture(roots, *, activity: ActivityCallback | None = None):
    activity = activity or (lambda _message: None)
    branches, errors = {}, []
    files_found = functions_found = exact_symbol_matches = 0
    for branch_name, targets in BRANCHES.items():
        activity(f"Missing Skill Forensics: architecture branch {branch_name}")
        branch_rows = []
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
                    branch_rows.append({"layer": layer, "relative_path": relative, "status": "file-too-large", "file_size": size, "functions": []})
                    continue
                raw = path.read_bytes()
            except OSError as exc:
                errors.append({"relative_path": relative, "error": f"{type(exc).__name__}: {exc}"})
                branch_rows.append({"layer": layer, "relative_path": relative, "status": "read-error", "functions": []})
                continue
            files_found += 1
            root_code, error = _load_marshaled_root(raw)
            if root_code is None:
                errors.append({"relative_path": relative, "error": error or "marshal decode failed"})
                branch_rows.append({"layer": layer, "relative_path": relative, "status": "marshal-error", "file_size": size, "functions": []})
                continue
            requested, symbols = tuple(target["functions"]), tuple(target["symbols"])
            exact_raw_symbols = sorted(s for s in symbols if s.encode("utf-8") in raw)
            exact_symbol_matches += len(exact_raw_symbols)
            functions = [_inspect_function(q, c, symbols) for q, c in _walk_code(root_code) if _function_selected(q, c.co_name, requested)]
            functions_found += len(functions)
            branch_rows.append({"layer": layer, "relative_path": relative, "status": "complete", "file_size": size, "requested_functions": list(requested), "target_symbols": list(symbols), "exact_raw_symbols": exact_raw_symbols, "functions": functions})
        branches[branch_name] = {"targets": branch_rows, "files_found": sum(1 for r in branch_rows if r.get("status") == "complete"), "functions_found": sum(len(r.get("functions") or []) for r in branch_rows)}
    closeout = _discover_closeout_candidates(roots, activity=activity)
    status = "raw-source-roots-unavailable" if not roots else ("complete-with-errors" if errors else "complete")
    return {
        "status": status,
        "record_counts": {"branches": len(BRANCHES), "target_files": sum(len(rows) for rows in BRANCHES.values()), "files_found": files_found, "functions_found": functions_found, "exact_raw_symbol_matches": exact_symbol_matches, "closeout_files_scanned": closeout["record_counts"]["files_scanned"], "closeout_candidates": closeout["record_counts"]["candidates"], "closeout_candidates_by_category": closeout["record_counts"]["by_category"], "errors": len(errors)},
        "branches": branches, "closeout_discovery": closeout, "errors": errors,
        "policy": {"scope": "All currently known high-value fixed-skill resolution modules/functions are inspected together, plus an exact-symbol corpus closeout scan for remaining routing/assembly/compatibility hypotheses.", "matching": "Function selection and reported relationship symbols are exact static CodeType/raw-byte evidence; closeout candidates require exact symbols or explicit compatibility tokens.", "execution": "PYC payloads are unmarshaled only; Once Human modules and game bytecode are never executed.", "wordcode": "Raw 2-byte instruction words and indexed name/constant pools are preserved without applying the local Python opcode table.", "interpretation": "Names/constants establish static adjacency only; raw wordcode preserves exact bytes but requires version-correct interpretation before semantic claims."},
        "next_step": "Resolve closeout categories in order: skill_constants, climp_callers, passive_table_assembly, package_fixed_skill, damage_sim_indirection, server_weapon_initializers, blueprint_identity_fallbacks, compatibility_overrides. Follow only exact returned identifiers into NeoX owners. If every category fails to produce an alternate exact owner, classify the fixed-skill references internally as exhausted/dangling-current-corpus evidence while keeping player-facing mechanics unresolved.",
    }
