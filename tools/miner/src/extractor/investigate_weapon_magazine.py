"""Exact, read-only Weapon Magazine evidence probe for Dead Signal.

This tool scans an extracted Miner snapshot for exact item/blueprint/gun IDs and
Q1100/Q1101 references. It may inspect Python code-object metadata from .pyc
files via marshal, but it never imports or executes game bytecode.

It deliberately does not calculate a final Magazine value. Its output is an
evidence bundle for manual proof of the Q1100/Q1101 aggregation path.
"""
from __future__ import annotations

import argparse
import json
import marshal
import types
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

FOCUS_FUNCTIONS = {
    "get_gun_magazine_size",
    "get_gun_magazine_affix_add",
    "get_gun_affix_add",
    "get_gun_calc_affix_add",
    "get_gun_base_affix_add",
    "get_all_guncore_affix_add",
    "get_gun_accessory_affix_add",
    "get_gun_calc_accessory_affix_add",
    "get_gun_rand_attr_affix_add",
    "get_gun_no_rand_affix_add",
    "get_gun_affix_option_add",
    "get_gun_correct_affix_add",
    "_add_weapon_magazine_size_affix_and_value",
}

SOURCE_LOCALS = {
    "base_affix_add",
    "accessory_affix_add",
    "rand_affix_add",
    "affix_option_add",
    "cal_affix",
    "correct_affix_add",
    "all_affix_add",
    "affix_add_dict",
    "magazine",
}


@dataclass(frozen=True)
class JsonHit:
    source_file: str
    json_path: str
    matched: str
    field: str | None
    value: Any
    record_preview: Any


@dataclass(frozen=True)
class PycHit:
    source_file: str
    qualname: str
    function: str
    co_names: list[str]
    co_varnames: list[str]
    string_constants: list[str]
    numeric_constants: list[float | int]
    exact_affix_constants: list[str]
    source_locals_present: list[str]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def compact_record(value: Any, limit: int = 1200) -> Any:
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return repr(value)[:limit]
    if len(encoded) <= limit:
        return value
    return encoded[: limit - 3] + "..."


def walk_json(value: Any, path: str = "$") -> Iterable[tuple[str, str | None, Any, Any]]:
    """Yield scalar nodes with their containing record for exact reverse-reference work."""
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if str(key).isidentifier() else f"{path}[{json.dumps(str(key))}]"
            if isinstance(child, (dict, list)):
                yield from walk_json(child, child_path)
            else:
                yield child_path, str(key), child, value
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            if isinstance(child, (dict, list)):
                yield from walk_json(child, child_path)
            else:
                yield child_path, None, child, value


def scalar_matches(value: Any, exact_values: dict[str, Any]) -> list[str]:
    matches: list[str] = []
    for label, expected in exact_values.items():
        if value == expected:
            matches.append(label)
        elif isinstance(expected, int) and isinstance(value, str) and value.isdigit() and int(value) == expected:
            matches.append(label)
    return matches


def scan_json(root: Path, exact_values: dict[str, Any]) -> list[JsonHit]:
    hits: list[JsonHit] = []
    for path in sorted(root.rglob("*.json")):
        if not path.is_file():
            continue
        try:
            payload = read_json(path)
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        for json_path, field, value, record in walk_json(payload):
            for matched in scalar_matches(value, exact_values):
                hits.append(JsonHit(rel, json_path, matched, field, value, compact_record(record)))
    return hits


def walk_code_objects(code: types.CodeType, prefix: str = "") -> Iterable[tuple[str, types.CodeType]]:
    qualname = f"{prefix}.{code.co_name}" if prefix else code.co_name
    yield qualname, code
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            yield from walk_code_objects(const, qualname)


def load_pyc_code(path: Path) -> types.CodeType | None:
    try:
        raw = path.read_bytes()
        if len(raw) < 17:
            return None
        code = marshal.loads(raw[16:])
    except Exception:
        return None
    return code if isinstance(code, types.CodeType) else None


def scan_pyc(root: Path, affixes: set[str]) -> list[PycHit]:
    hits: list[PycHit] = []
    for path in sorted(root.rglob("*.pyc")):
        if not path.is_file():
            continue
        code = load_pyc_code(path)
        if code is None:
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        for qualname, obj in walk_code_objects(code):
            names = sorted(set(map(str, obj.co_names)))
            varnames = list(map(str, obj.co_varnames))
            string_constants = sorted({value for value in obj.co_consts if isinstance(value, str)})
            exact_affix_constants = sorted(affixes & set(string_constants))
            focus = obj.co_name in FOCUS_FUNCTIONS
            mentions_focus = bool(FOCUS_FUNCTIONS & set(names))
            mentions_affix = bool(exact_affix_constants)
            if not (focus or mentions_focus or mentions_affix):
                continue
            numeric_constants = sorted({
                value for value in obj.co_consts
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            })
            hits.append(PycHit(
                source_file=rel,
                qualname=qualname,
                function=obj.co_name,
                co_names=names,
                co_varnames=varnames,
                string_constants=string_constants,
                numeric_constants=numeric_constants,
                exact_affix_constants=exact_affix_constants,
                source_locals_present=sorted(SOURCE_LOCALS & set(varnames)),
            ))
    return hits


def build_report(root: Path, item_id: int, blueprint_id: int, gun_no: int, abs_affix: str, rate_affix: str) -> dict[str, Any]:
    exact_values = {
        "item_id": item_id,
        "blueprint_id": blueprint_id,
        "gun_no": gun_no,
        "absolute_affix": abs_affix,
        "rate_affix": rate_affix,
    }
    json_hits = scan_json(root, exact_values)
    pyc_hits = scan_pyc(root, {abs_affix, rate_affix})
    return {
        "schema_version": 1,
        "scope": "Exact Weapon Magazine evidence only; no final Magazine calculation",
        "safety": {
            "game_bytecode_executed": False,
            "pyc_handling": "marshal/code-object metadata inspection only; no import/eval/exec",
            "matching": "exact IDs and exact Q1100/Q1101 strings only",
        },
        "target": exact_values,
        "json_hits": [asdict(hit) for hit in json_hits],
        "pyc_hits": [asdict(hit) for hit in pyc_hits],
        "summary": {
            "json_hit_count": len(json_hits),
            "pyc_hit_count": len(pyc_hits),
            "focus_functions_found": sorted({hit.function for hit in pyc_hits if hit.function in FOCUS_FUNCTIONS}),
            "q1100_pyc_functions": sorted({hit.qualname for hit in pyc_hits if abs_affix in hit.exact_affix_constants}),
            "q1101_pyc_functions": sorted({hit.qualname for hit in pyc_hits if rate_affix in hit.exact_affix_constants}),
        },
        "resolution": {
            "status": "evidence-only-unresolved",
            "final_magazine": None,
            "reason": "This probe intentionally records exact sources and consumer metadata without inferring aggregation ordering, hidden baselines, or rounding.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Exact read-only Weapon Magazine evidence probe")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--item-id", type=int, required=True)
    parser.add_argument("--blueprint-id", type=int, required=True)
    parser.add_argument("--gun-no", type=int, required=True)
    parser.add_argument("--abs-affix", default="Q1100")
    parser.add_argument("--rate-affix", default="Q1101")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.snapshot, args.item_id, args.blueprint_id, args.gun_no, args.abs_affix, args.rate_affix)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
