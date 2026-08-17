"""Static ownerless fixed-skill resolution trace.

This pass deliberately inspects every high-value consumer/helper branch implicated
by the 14 player-facing weapons whose fixed_skill_code has no exact
passive_skill_data owner. It is research-only and never imports or executes Once
Human modules.

The trace covers:
- BluePrintHelper fixed-skill/default/get_skill_data path;
- GunCoreHelper normalization / climp_skill_code / slot conversion;
- PassiveSkillHelper and SkillDataHelper existence/name/description fallbacks;
- weapon-craft UI update_fixed_skills consumer;
- damage/passive mapping;
- camera/star/stardust resolution;
- server CompSkillMgr fixed-skill buff resolution.

Only static CodeType metadata, exact raw symbols, safe scalar constants and raw
wordcode capsules are retained. Because Once Human remaps bytecode opcodes, stock
Python opnames are never treated as semantic proof.
"""
from __future__ import annotations

import marshal
import types
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from weapon_progression import _code_capsule, _raw_wordcode

ActivityCallback = Callable[[str], None]
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_SYMBOLS = 256
MAX_CONSTANTS = 128

OWNERLESS_CODES = (
    "WS1001", "WS1101", "WS1301", "WS1402", "WS14503", "WS1501",
    "WS15203", "WS15304", "WS15502", "WS1601", "WS2001",
)

TARGETS: tuple[dict[str, Any], ...] = (
    {
        "branch": "blueprint_default_resolution",
        "basename": "BluePrintHelper.pyc",
        "functions": (
            "get_blueprint_fixed_skill", "get_blueprint_fixed_skill_lv",
            "get_equip_blueprint_fixed_skill", "get_equip_blueprint_fixed_skill_lv",
            "get_fixed_skill_default_data", "get_skill_data",
        ),
        "symbols": (
            "fixed_skill_code", "fixed_skill_lv", "get_skill_data",
            "gun_blueprint_attr_data", "equip_blueprint_attr_data",
            "package_fixed_skill_data", "equip_package_fixed_skill_data",
            "passive_skill_data", "common_skill_data", "skill_data",
        ),
    },
    {
        "branch": "guncore_normalization",
        "basename": "GunCoreHelper.pyc",
        "functions": (
            "get_blueprint_fixed_skill", "init_fixed_skill", "climp_skill_code",
            "convert_data_skill_slots", "get_decompose_skill",
        ),
        "symbols": (
            "fixed_skill_code", "SKILL_CODE_LEN", "MAX_SKILL_LEVEL",
            "climp_skill_code", "init_fixed_skill", "convert_data_skill_slots",
            "get_decompose_skill", "skill_code",
        ),
    },
    {
        "branch": "passive_skill_helper",
        "basename": "PassiveSkillHelper.pyc",
        "functions": (
            "is_fixed_skill", "check_is_passive_skill", "is_skill_exist",
            "get_passive_skill_name", "get_skill_name", "get_skill_description",
            "get_passive_skill_desc", "get_passive_skill_data",
        ),
        "symbols": (
            "fixed_skill", "fixed_passive_skill", "passive_skill_data",
            "skill_code", "skill_data", "name", "description", "discription",
            "copywriting", "get_passive_skill_name",
        ),
    },
    {
        "branch": "skill_data_helper",
        "basename": "SkillDataHelper.pyc",
        "functions": (
            "is_fixed_skill", "check_is_passive_skill", "is_skill_exist",
            "get_skill_data", "get_skill_name", "get_skill_description",
            "get_skill_desc",
        ),
        "symbols": (
            "fixed_skill", "passive_skill_data", "common_skill_data",
            "skill_data", "skill_code", "description", "discription",
            "copywriting", "name",
        ),
    },
    {
        "branch": "player_facing_ui",
        "basename": "ScrollViewItems.pyc",
        "functions": ("WRGunInfoPart.update_fixed_skills", "update_fixed_skills"),
        "symbols": (
            "PassiveSkillHelper", "fixed_passive_skill", "fixed_skill",
            "get_passive_skill_name", "skill_code", "skill_data",
            "label_skill_desc", "label_skill_passivename", "discription",
        ),
    },
    {
        "branch": "damage_passive_mapping",
        "basename": "CompShootDamageSimulateClient.pyc",
        "functions": ("get_weapon_passive_skill_config",),
        "symbols": (
            "fixed_skill_code", "WEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG",
            "WEAPON_TO_PASSIVE", "gun_blueprint_attr_data",
            "passive_skill_damage_simulate_data", "skill_code",
        ),
    },
    {
        "branch": "server_buff_resolution",
        "basename": "CompSkillMgr.pyc",
        "functions": (
            "_get_ps_buff_id", "CompSkillMgrNpc._get_gun_ps_buff_id",
            "_get_gun_ps_buff_id", "_check_buff_need_pause",
        ),
        "symbols": (
            "fixed_skill_code", "gun_blueprint_attr_data", "passive_skill_data",
            "skill_code", "buff_id", "buff",
        ),
    },
    {
        "branch": "star_stardust_camera",
        "basename": "CompCamera.pyc",
        "functions": ("CompCameraOtherPlayer._get_gun_sp_track_time", "_get_gun_sp_track_time"),
        "symbols": (
            "fixed_skill_code", "skill_code", "star_skill_no",
            "stardust_gun_skill_data", "passive_skill_data", "skill_cast_time",
        ),
    },
    {
        "branch": "star_stardust_shoot_utility",
        "basename": "shoot_utility.pyc",
        "functions": ("get_star_cast_skill_behavior_name",),
        "symbols": (
            "fixed_skill", "skill_code", "star_skill_no",
            "stardust_gun_skill_data", "passive_skill_data", "skill_cast_time",
        ),
    },
)


def _load_code(path: Path) -> tuple[types.CodeType | None, str | None]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if len(raw) < 17:
        return None, "PYC too small"
    try:
        root = marshal.loads(raw[16:])
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    return (root, None) if isinstance(root, types.CodeType) else (None, "marshal payload not CodeType")


def _walk(code: types.CodeType, qualname: str = "<module>"):
    yield qualname, code
    seen: Counter[str] = Counter()
    for child in code.co_consts:
        if not isinstance(child, types.CodeType):
            continue
        seen[child.co_name] += 1
        suffix = f"#{seen[child.co_name]}" if seen[child.co_name] > 1 else ""
        name = child.co_name + suffix
        child_q = name if qualname == "<module>" else f"{qualname}.{name}"
        yield from _walk(child, child_q)


def _matches(qualname: str, code_name: str, requested: tuple[str, ...]) -> bool:
    q = qualname.casefold()
    n = code_name.casefold()
    return any(
        q == target.casefold()
        or q.endswith("." + target.casefold())
        or q.endswith(target.casefold())
        or n == target.split(".")[-1].casefold()
        for target in requested
    )


def _safe_scalars(values: tuple[Any, ...]) -> list[Any]:
    rows: list[Any] = []
    for value in values:
        if value is None or isinstance(value, (str, int, float, bool)):
            rows.append(value)
        elif isinstance(value, tuple) and len(value) <= 16 and all(
            item is None or isinstance(item, (str, int, float, bool)) for item in value
        ):
            rows.append(list(value))
        if len(rows) >= MAX_CONSTANTS:
            break
    return rows


def _find_by_basename(roots: list[tuple[str, Path]], basename: str) -> tuple[str, Path] | None:
    wanted = basename.casefold()
    for layer, root in roots:
        exact = [path for path in root.rglob("*.pyc") if path.name.casefold() == wanted]
        if exact:
            exact.sort(key=lambda path: (len(path.parts), path.as_posix().casefold()))
            return layer, exact[0]
    return None


def _function_row(qualname: str, code: types.CodeType, symbols: tuple[str, ...]) -> dict[str, Any]:
    names = list(map(str, code.co_names))
    varnames = list(map(str, code.co_varnames))
    strings = [value for value in code.co_consts if isinstance(value, str)]
    universe = set(names) | set(varnames) | set(strings)
    matched = sorted(set(symbols).intersection(universe))
    ownerless_literal_hits = sorted(set(OWNERLESS_CODES).intersection(universe))
    return {
        "qualname": qualname,
        "function": code.co_name,
        "co_filename": code.co_filename,
        "firstlineno": code.co_firstlineno,
        "matched_symbols": matched,
        "ownerless_code_literals": ownerless_literal_hits,
        "co_names": sorted(set(names))[:MAX_SYMBOLS],
        "co_varnames": sorted(set(varnames))[:MAX_SYMBOLS],
        "string_constants": sorted(set(strings))[:MAX_SYMBOLS],
        "safe_scalar_constants": _safe_scalars(code.co_consts),
        "code_capsule": _code_capsule(code),
        "raw_wordcode": _raw_wordcode(code, limit=16384),
    }


def trace_ownerless_skill_resolution(
    roots: list[tuple[str, Path]], *, activity: ActivityCallback | None = None
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    branches: dict[str, Any] = {}
    files_found = 0
    functions_found = 0
    errors: list[dict[str, Any]] = []

    for target in TARGETS:
        branch = str(target["branch"])
        basename = str(target["basename"])
        activity(f"Missing Skill Forensics: ownerless resolver branch {branch}")
        located = _find_by_basename(roots, basename)
        if located is None:
            branches[branch] = {
                "status": "file-not-found", "basename": basename,
                "requested_functions": list(target["functions"]), "functions": [],
            }
            continue
        layer, path = located
        try:
            size = path.stat().st_size
        except OSError as exc:
            errors.append({"branch": branch, "error": f"{type(exc).__name__}: {exc}"})
            branches[branch] = {"status": "stat-error", "basename": basename, "functions": []}
            continue
        if size > MAX_FILE_BYTES:
            branches[branch] = {"status": "file-too-large", "basename": basename, "file_size": size, "functions": []}
            continue
        code, error = _load_code(path)
        if code is None:
            errors.append({"branch": branch, "relative_path": path.name, "error": error})
            branches[branch] = {"status": "marshal-error", "basename": basename, "file_size": size, "functions": []}
            continue

        files_found += 1
        requested = tuple(target["functions"])
        symbols = tuple(target["symbols"])
        functions = [
            _function_row(qualname, obj, symbols)
            for qualname, obj in _walk(code)
            if _matches(qualname, obj.co_name, requested)
        ]
        functions_found += len(functions)
        raw = path.read_bytes()
        branches[branch] = {
            "status": "complete",
            "layer": layer,
            "relative_path": next(
                (path.resolve().relative_to(root).as_posix() for root_layer, root in roots if root_layer == layer and path.is_relative_to(root)),
                path.name,
            ),
            "file_size": size,
            "requested_functions": list(requested),
            "target_symbols": list(symbols),
            "raw_symbol_hits": sorted(symbol for symbol in symbols if symbol.encode("utf-8") in raw),
            "raw_ownerless_code_hits": sorted(code for code in OWNERLESS_CODES if code.encode("ascii") in raw),
            "functions": functions,
        }

    return {
        "status": "raw-source-roots-unavailable" if not roots else ("complete-with-errors" if errors else "complete"),
        "ownerless_skill_codes": list(OWNERLESS_CODES),
        "record_counts": {
            "branches": len(TARGETS),
            "files_found": files_found,
            "functions_found": functions_found,
            "branches_with_functions": sum(bool(row.get("functions")) for row in branches.values()),
            "errors": len(errors),
        },
        "branches": branches,
        "errors": errors,
        "policy": {
            "scope": "All known high-value fixed-skill helpers/consumers are inspected in one pass.",
            "matching": "Basenames, requested function names, symbols and WS codes use exact static matching only.",
            "execution": "PYC payloads are unmarshaled as CodeType metadata only; game modules and bytecode are never executed.",
            "opcode_warning": "Once Human remaps opcode numbers; raw wordcode is retained and stock Python opnames are not semantic proof.",
            "interpretation": "Static adjacency narrows the alternate resolver path but does not prove runtime return values until identifiers are joined to exact data owners.",
        },
        "next_step": (
            "Compare the ownerless cohort against these branches for transformation/fallback symbols, then follow any exact returned code/numeric IDs into NeoX owners. "
            "Prioritize climp_skill_code, get_fixed_skill_default_data/get_skill_data, PassiveSkillHelper/SkillDataHelper fallbacks, and WRGunInfoPart.update_fixed_skills."
        ),
    }
