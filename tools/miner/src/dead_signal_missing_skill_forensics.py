"""Targeted offline forensics for unresolved Once Human weapon fixed-skill codes.

This stage is intentionally narrow. It receives the exact unresolved WS... codes
left by Schema Trace, searches only likely skill/gun/weapon/buff PYC modules in
the retained snapshot source roots, and inspects exact hits without importing or
executing game modules.

Two static decoders are attempted for each exact-hit PYC:
- canonical BindictParser for data-table payloads;
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

from neoxtractor.core.bindict.parser import BindictParser

SCHEMA_VERSION = 1
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_CANDIDATE_FILES = 5000
NAME_TOKENS = ("skill", "weapon", "gun", "buff", "passive", "stardust")
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


def _marshal_hits(raw: bytes, codes: set[str]) -> tuple[list[dict[str, Any]], str | None]:
    if len(raw) < 17:
        return [], "PYC file is too small"
    try:
        root = marshal.loads(raw[16:])
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"
    if not isinstance(root, types.CodeType):
        return [], "marshal payload was not CodeType"
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
    rows = []
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
        rows.append(row)

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
        },
        "source_roots": [{"layer": layer, "root_present": True} for layer, _root in roots],
        "skills": rows,
        "policy": {
            "scope": "Only retained PYC files with skill/weapon/gun/buff/passive/stardust in the filename are scanned.",
            "matching": "Exact unresolved skill-code bytes only; no fuzzy or substring identity promotion.",
            "parsing": "Exact-hit files are inspected through BindictParser and marshal CodeType metadata where compatible.",
            "execution": "No game module is imported or executed; no game bytecode is executed.",
            "publication": "Research report only. No website/public weapon data is modified or promoted.",
        },
        "next_step": "Inspect exact Bindict/code-metadata hits for a hidden owner table or consumer mapping for each unresolved fixed-skill code.",
    }
    _write_json(destination, report)
    activity(f"Missing Skill Forensics complete: {len(codes)} codes; {exact_files} exact-hit files")
    return report
