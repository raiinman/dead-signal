"""Targeted offline forensics for unresolved Once Human weapon fixed-skill codes.

This stage receives exact unresolved WS... codes left by Schema Trace, searches
likely skill/gun/weapon/buff PYC modules for exact code bytes, then separately
searches the retained raw PYC corpus for exact fixed-skill consumer symbols.

No game module is imported or executed.

Static inspection methods:
- canonical BindictParser for exact-hit data-table payloads;
- marshal CodeType metadata for ordinary Python bytecode containers.

The report is research evidence only and never modifies published weapon data.
"""
from __future__ import annotations

import json
import marshal
import types
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable

from dead_signal_fixed_skill_flow_trace import trace_fixed_skill_flows
from neoxtractor.core.bindict.parser import BindictParser

SCHEMA_VERSION = 4
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_CANDIDATE_FILES = 5000
MAX_CONSUMER_FILES_PER_ROOT = 100000
NAME_TOKENS = ("skill", "weapon", "gun", "buff", "passive", "stardust")
DIRECT_CONSUMER_SYMBOLS = ("fixed_skill_code",)
CONTEXT_SYMBOLS = (
    "gun_blueprint_attr_data",
    "passive_skill_data",
    "skill_data",
)
CONSUMER_SYMBOLS = DIRECT_CONSUMER_SYMBOLS + CONTEXT_SYMBOLS
SOURCE_TABLE_SUFFIX = "game_common/data/gun_blueprint_attr_data.pyc"
ActivityCallback = Callable[[str], None]


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _source_root(snapshot: Path) -> Path | None:
    payload = _read_json(snapshot / "snapshot.json", {}) or {}
    value = str(payload.get("source_root") or "").strip() if isinstance(payload, dict) else ""
    if not value:
        return None
    root = Path(value).expanduser()
    root = (snapshot / root).resolve() if not root.is_absolute() else root.resolve()
    return root if root.is_dir() else None


def _roots(base: Path, current: Path) -> list[tuple[str, Path]]:
    rows: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for layer, snapshot in (("current", current), ("base", base)):
        root = _source_root(snapshot)
        if root is None:
            continue
        key = str(root).casefold()
        if key in seen:
            continue
        seen.add(key)
        rows.append((layer, root))
    return rows


def _candidate_paths(root: Path) -> Iterable[Path]:
    count = 0
    for path in root.rglob("*.pyc"):
        name = path.name.casefold()
        if not any(token in name for token in NAME_TOKENS):
            continue
        yield path
        count += 1
        if count >= MAX_CANDIDATE_FILES:
            break


def _walk_scalars(value: Any, pointer: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            kp = str(key).replace("~", "~0").replace("/", "~1")
            child_pointer = f"{pointer}/{kp}"
            yield child_pointer + "/@key", "dict-key", key
            yield from _walk_scalars(child, child_pointer)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            yield from _walk_scalars(child, f"{pointer}/{index}")
    else:
        yield pointer or "/", "value", value


def _bindict_hits(raw: bytes, codes: set[str]) -> tuple[list[dict[str, Any]], str | None]:
    try:
        parsed = BindictParser(debug=False).extract_from_pyc(raw)
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"
    hits: list[dict[str, Any]] = []
    for pointer, role, value in _walk_scalars(parsed):
        scalar = str(value)
        if scalar in codes:
            hits.append({"code": scalar, "json_pointer": pointer, "role": role})
    return hits, None


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


def _marshal_hits(raw: bytes, codes: set[str]) -> tuple[list[dict[str, Any]], str | None]:
    root, error = _load_marshaled_root(raw)
    if root is None:
        return [], error
    hits: list[dict[str, Any]] = []
    for qualname, code in _walk_code(root):
        strings = {value for value in code.co_consts if isinstance(value, str)}
        names = set(map(str, code.co_names))
        for skill in sorted(codes.intersection(strings | names)):
            hits.append({
                "code": skill,
                "qualname": qualname,
                "co_name": code.co_name,
                "co_filename": code.co_filename,
                "co_firstlineno": code.co_firstlineno,
                "match_in": "co_names" if skill in names else "string_constant",
            })
    return hits, None


def _consumer_code_hits(raw: bytes) -> tuple[list[dict[str, Any]], str | None]:
    root, error = _load_marshaled_root(raw)
    if root is None:
        return [], error
    targets = set(CONSUMER_SYMBOLS)
    direct = set(DIRECT_CONSUMER_SYMBOLS)
    context = set(CONTEXT_SYMBOLS)
    hits: list[dict[str, Any]] = []
    for qualname, code in _walk_code(root):
        strings = {value for value in code.co_consts if isinstance(value, str)}
        names = set(map(str, code.co_names))
        varnames = set(map(str, code.co_varnames))
        universe = strings | names | varnames
        matched = sorted(targets.intersection(universe))
        if not matched:
            continue
        hits.append({
            "qualname": qualname,
            "co_name": code.co_name,
            "co_filename": code.co_filename,
            "co_firstlineno": code.co_firstlineno,
            "matched_symbols": matched,
            "direct_consumer_symbols": sorted(direct.intersection(universe)),
            "context_symbols": sorted(context.intersection(universe)),
            "co_names": sorted(name for name in names if name in targets or "skill" in name.casefold()),
            "co_varnames": sorted(name for name in varnames if name in targets or "skill" in name.casefold()),
            "string_constants": sorted(
                value for value in strings
                if value in targets or "skill" in value.casefold() or "blueprint_attr" in value.casefold()
            )[:64],
        })
    return hits, None


def _scan_consumers(
    roots: list[tuple[str, Path]],
    *,
    activity: ActivityCallback,
    max_files_per_root: int = MAX_CONSUMER_FILES_PER_ROOT,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    files_scanned = 0
    files_with_symbol_bytes = 0
    marshal_decoded = 0
    roots_truncated: list[str] = []
    symbol_bytes = {symbol: symbol.encode("ascii") for symbol in CONSUMER_SYMBOLS}

    for layer, root in roots:
        activity(f"Missing Skill Forensics: tracing fixed_skill_code consumers in {layer}")
        layer_count = 0
        for path in root.rglob("*.pyc"):
            layer_count += 1
            if layer_count > max_files_per_root:
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
            present = sorted(symbol for symbol, token in symbol_bytes.items() if token in raw)
            if not present:
                continue
            files_with_symbol_bytes += 1
            relative = path.resolve().relative_to(root).as_posix()
            code_hits, error = _consumer_code_hits(raw)
            if error is None:
                marshal_decoded += 1
            rows.append({
                "layer": layer,
                "relative_path": relative,
                "file_size": size,
                "source_table": relative.endswith(SOURCE_TABLE_SUFFIX),
                "raw_symbols": present,
                "marshal_decoded": error is None,
                "marshal_error": error,
                "code_hits": code_hits,
            })

    direct_candidates = [
        row for row in rows
        if not row["source_table"]
        and any(hit.get("direct_consumer_symbols") for hit in row.get("code_hits") or [])
    ]
    context_candidates = [
        row for row in rows
        if not row["source_table"]
        and not any(hit.get("direct_consumer_symbols") for hit in row.get("code_hits") or [])
        and any(hit.get("context_symbols") for hit in row.get("code_hits") or [])
    ]
    status = "raw-source-roots-unavailable" if not roots else ("partial-limit" if roots_truncated else "complete")
    return {
        "status": status,
        "record_counts": {
            "files_scanned": files_scanned,
            "files_with_symbol_bytes": files_with_symbol_bytes,
            "marshal_decoded_symbol_files": marshal_decoded,
            "consumer_candidate_files": len(direct_candidates),
            "direct_consumer_candidate_files": len(direct_candidates),
            "context_reference_candidate_files": len(context_candidates),
        },
        "roots_truncated_at_limit": sorted(set(roots_truncated)),
        "symbols": {
            "direct": list(DIRECT_CONSUMER_SYMBOLS),
            "context": list(CONTEXT_SYMBOLS),
        },
        "candidates": direct_candidates,
        "direct_consumer_candidates": direct_candidates,
        "context_reference_candidates": context_candidates,
        "all_symbol_files": rows,
    }


def run_missing_skill_forensics(
    base: Path,
    current: Path,
    skill_codes: Iterable[object],
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    codes = {str(value).strip() for value in skill_codes if str(value).strip()}
    destination = reports_dir / "missing-fixed-skill-forensics.json"
    roots = _roots(base, current)
    by_code: dict[str, dict[str, Any]] = {
        code: {"skill_code": code, "raw_exact_files": [], "bindict_hits": [], "marshal_hits": []}
        for code in sorted(codes)
    }
    files_scanned = 0
    exact_files = 0

    for layer, root in roots:
        activity(f"Missing Skill Forensics: scanning likely PYC modules in {layer}")
        for path in _candidate_paths(root):
            files_scanned += 1
            try:
                size = path.stat().st_size
                if size > MAX_FILE_BYTES:
                    continue
                raw = path.read_bytes()
            except OSError:
                continue
            present = {code for code in codes if code.encode("ascii", errors="ignore") in raw}
            if not present:
                continue
            exact_files += 1
            relative = path.resolve().relative_to(root).as_posix()
            bindict, bindict_error = _bindict_hits(raw, present)
            marshaled, marshal_error = _marshal_hits(raw, present)
            for code in sorted(present):
                by_code[code]["raw_exact_files"].append({
                    "layer": layer,
                    "relative_path": relative,
                    "file_size": size,
                    "bindict_decoded": bindict_error is None,
                    "marshal_decoded": marshal_error is None,
                })
            for row in bindict:
                by_code[row["code"]]["bindict_hits"].append({"layer": layer, "relative_path": relative, **row})
            for row in marshaled:
                by_code[row["code"]]["marshal_hits"].append({"layer": layer, "relative_path": relative, **row})

    status_counts: Counter[str] = Counter()
    skill_rows = []
    for code in sorted(by_code):
        row = by_code[code]
        if row["bindict_hits"]:
            status = "exact-bindict-hit"
        elif row["marshal_hits"]:
            status = "exact-code-metadata-hit"
        elif row["raw_exact_files"]:
            status = "exact-raw-pyc-hit-undecoded"
        else:
            status = "no-exact-raw-hit-in-targeted-modules"
        row["status"] = status
        status_counts[status] += 1
        skill_rows.append(row)

    consumer_trace = _scan_consumers(roots, activity=activity)
    fixed_skill_flow_trace = trace_fixed_skill_flows(roots, consumer_trace, activity=activity)

    report = {
        "schema": "dead-signal-missing-fixed-skill-forensics",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Unresolved weapon fixed-skill codes",
        "mode": "offline-read-only-targeted-pyc-forensics",
        "status": "complete" if roots else "raw-source-roots-unavailable",
        "record_counts": {
            "skill_codes": len(codes),
            "source_roots": len(roots),
            "candidate_files_scanned": files_scanned,
            "files_with_exact_code_bytes": exact_files,
            "statuses": dict(sorted(status_counts.items())),
            "consumer_candidate_files": consumer_trace["record_counts"]["consumer_candidate_files"],
            "fixed_skill_flow_functions": fixed_skill_flow_trace["record_counts"]["consumer_functions"],
            "fixed_skill_instruction_anchors": fixed_skill_flow_trace["record_counts"]["fixed_skill_instruction_anchors"],
        },
        "source_roots": [{"layer": layer, "root_present": True} for layer, _root in roots],
        "skills": skill_rows,
        "consumer_trace": consumer_trace,
        "fixed_skill_flow_trace": fixed_skill_flow_trace,
        "policy": {
            "scope": (
                "Exact unresolved skill-code bytes are searched in likely skill/weapon/gun/buff modules; "
                "a separate bounded corpus pass searches exact fixed-skill consumer symbols, then only those exact "
                "direct consumers receive static instruction-window tracing."
            ),
            "matching": "Exact skill-code or exact consumer-symbol bytes only; no fuzzy or substring identity promotion.",
            "parsing": "Exact-hit files are inspected through BindictParser and/or marshal CodeType metadata where compatible.",
            "consumer_evidence": (
                "Only static CodeType metadata containing the exact field symbol fixed_skill_code is classified as a "
                "direct consumer. References to gun_blueprint_attr_data/passive_skill_data/skill_data are retained as "
                "context references and are not promoted to consumers."
            ),
            "flow_evidence": (
                "Direct consumer functions are disassembled into bounded windows around exact fixed_skill_code "
                "instruction operands. Nearby operations and symbols are static evidence, not claimed runtime semantics."
            ),
            "execution": "No game module is imported or executed; no game bytecode is executed.",
            "publication": "Research report only. No website/public weapon data is modified or promoted.",
        },
        "next_step": (
            "Inspect fixed_skill_flow_trace for the immediate operations after fixed_skill_code in BluePrintHelper, "
            "GunCoreHelper, damage simulation, camera, and skill-manager consumers. Use those exact static flows to "
            "identify the next typed data/helper relationship without inventing a WS alias."
        ),
    }
    _write_json(destination, report)
    activity(
        f"Missing Skill Forensics complete: {len(codes)} codes; {exact_files} exact-hit files; "
        f"{consumer_trace['record_counts']['direct_consumer_candidate_files']} direct consumers; "
        f"{fixed_skill_flow_trace['record_counts']['consumer_functions']} traced consumer functions; "
        f"{consumer_trace['record_counts']['context_reference_candidate_files']} context references"
    )
    return report
