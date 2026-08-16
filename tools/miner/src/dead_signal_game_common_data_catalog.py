"""Offline static catalog of Once Human game_common/data producer modules.

This audit deliberately focuses on the producer layer under game_common/data. It
first inventories every PYC in that subtree using filenames and bounded raw-byte
token scans, then deep-inspects only weapon/skill/buff/blueprint/item/mod related
shortlist modules one at a time. It never imports or executes game bytecode and
never touches the live game process.
"""
from __future__ import annotations

import hashlib
import json
import marshal
import re
import types
from collections import Counter
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 1
ActivityCallback = Callable[[str], None]
SUBTREE = Path("game_common/data")
BLOCK = 1024 * 1024
OVERLAP = 128
MAX_DEEP_FILE_BYTES = 32 * 1024 * 1024
MAX_DEEP_MODULES = 256
MAX_NAMES = 512
MAX_STRINGS = 512
MAX_STRING_LEN = 1024

TARGET_TERMS = (
    "weapon", "gun", "blueprint", "skill", "passive", "active", "buff",
    "item", "equip", "mod", "calibration", "prototype", "bullet", "ammo",
    "attachment", "accessory", "craft", "recipe", "formula",
)
RAW_TOKENS = (
    b"fixed_skill", b"buff_id", b"discription", b"description", b"prototype_desc",
    b"prototype_name", b"weapon", b"gun", b"blueprint", b"passive", b"active",
    b"buff", b"skill", b"translation", b"desc", b"name",
)
TABLE_RE = re.compile(rb"[A-Z][A-Z0-9_]{2,63}_TABLE")
FIELD_RE = re.compile(rb"(?:fixed_skill|buff_id|discription|description|prototype_desc|prototype_name|skill_id|passive_id|active_id|weapon_id|gun_id|blueprint_id|item_id)")


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
    raw = payload.get("source_root") if isinstance(payload, dict) else None
    if not raw:
        return None
    root = Path(str(raw)).expanduser()
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


def _iter_data_pyc(root: Path):
    subtree = root / SUBTREE
    if not subtree.is_dir():
        return
    for path in subtree.rglob("*.pyc"):
        if path.is_file():
            yield path


def _raw_scan(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    token_hits: set[str] = set()
    table_symbols: set[str] = set()
    field_hits: set[str] = set()
    carry = b""
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(BLOCK)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
            data = carry + chunk
            lower = data.lower()
            for token in RAW_TOKENS:
                if token.lower() in lower:
                    token_hits.add(token.decode("ascii"))
            table_symbols.update(m.group(0).decode("ascii", "ignore") for m in TABLE_RE.finditer(data))
            field_hits.update(m.group(0).decode("ascii", "ignore") for m in FIELD_RE.finditer(lower))
            carry = data[-OVERLAP:]
    return {
        "file_size": size,
        "file_sha256": digest.hexdigest(),
        "raw_token_hits": sorted(token_hits),
        "raw_table_symbols": sorted(table_symbols)[:256],
        "raw_field_hits": sorted(field_hits),
    }


def _is_shortlist(relative_path: str, scan: dict[str, Any]) -> bool:
    lowered = relative_path.casefold()
    if any(term in lowered for term in TARGET_TERMS):
        return True
    hits = {str(value).casefold() for value in scan.get("raw_token_hits") or []}
    fields = {str(value).casefold() for value in scan.get("raw_field_hits") or []}
    return bool(hits.intersection(TARGET_TERMS) or fields)


def _load_code(path: Path) -> tuple[types.CodeType | None, str | None]:
    try:
        size = path.stat().st_size
        if size > MAX_DEEP_FILE_BYTES:
            return None, f"skipped: exceeds {MAX_DEEP_FILE_BYTES} byte guard"
        raw = path.read_bytes()
        if len(raw) < 17:
            return None, "PYC file is too small"
        value = marshal.loads(raw[16:])
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(value, types.CodeType):
        return None, "marshal payload was not a CodeType"
    return value, None


def _walk(code: types.CodeType, qualname: str = "<module>"):
    yield qualname, code
    counts: Counter[str] = Counter()
    for value in code.co_consts:
        if not isinstance(value, types.CodeType):
            continue
        counts[value.co_name] += 1
        suffix = f"#{counts[value.co_name]}" if counts[value.co_name] > 1 else ""
        child = value.co_name + suffix
        qn = child if qualname == "<module>" else f"{qualname}.{child}"
        yield from _walk(value, qn)


def _strings(code: types.CodeType) -> list[str]:
    out: list[str] = []
    for value in code.co_consts:
        if isinstance(value, str):
            out.append(value[:MAX_STRING_LEN])
        elif isinstance(value, (tuple, frozenset, list)):
            for item in value:
                if isinstance(item, str):
                    out.append(item[:MAX_STRING_LEN])
                    if len(out) >= MAX_STRINGS:
                        return out
        if len(out) >= MAX_STRINGS:
            break
    return out


def _deep_summary(path: Path) -> dict[str, Any]:
    code, error = _load_code(path)
    if code is None:
        return {"marshal_compatible": False, "error": error, "code_objects": []}
    rows: list[dict[str, Any]] = []
    for qualname, obj in _walk(code):
        names = list(map(str, obj.co_names))[:MAX_NAMES]
        strings = _strings(obj)
        combined = set(names) | set(strings)
        signals = sorted(value for value in combined if any(term in value.casefold() for term in TARGET_TERMS))[:256]
        fields = sorted(value for value in combined if value.casefold() in {
            "fixed_skill", "buff_id", "discription", "description", "prototype_desc",
            "prototype_name", "skill_id", "passive_id", "active_id", "weapon_id",
            "gun_id", "blueprint_id", "item_id",
        })
        tables = sorted(value for value in combined if re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}_TABLE", value))[:256]
        if qualname != "<module>" and not signals and not fields and not tables:
            continue
        rows.append({
            "qualname": qualname,
            "co_name": obj.co_name,
            "co_firstlineno": obj.co_firstlineno,
            "co_names": names,
            "string_constants": strings,
            "target_signals": signals,
            "field_signals": fields,
            "table_symbols": tables,
            "co_code_length": len(obj.co_code),
            "co_code_sha256": hashlib.sha256(obj.co_code).hexdigest(),
        })
    return {"marshal_compatible": True, "error": None, "code_objects": rows}


def run_game_common_data_catalog(
    base: Path,
    current: Path,
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    progress_path = reports_dir / "game-common-data-catalog-progress.json"
    _write_json(progress_path, {"stage": "starting", "schema_version": SCHEMA_VERSION})

    inventory: list[dict[str, Any]] = []
    shortlist: list[dict[str, Any]] = []
    for layer, root in _roots(base, current):
        paths = list(_iter_data_pyc(root) or [])
        for index, path in enumerate(paths, start=1):
            if index == 1 or index % 100 == 0:
                _write_json(progress_path, {"stage": "raw-catalog", "layer": layer, "scanned": index, "total": len(paths)})
                activity(f"Game Common Data Catalog: {layer} {index}/{len(paths)}")
            rel = path.resolve().relative_to(root).as_posix()
            try:
                scan = _raw_scan(path)
            except OSError as exc:
                scan = {"file_size": 0, "file_sha256": None, "raw_token_hits": [], "raw_table_symbols": [], "raw_field_hits": [], "error": f"{type(exc).__name__}: {exc}"}
            row = {"layer": layer, "relative_path": rel, **scan}
            row["shortlisted"] = _is_shortlist(rel, scan)
            inventory.append(row)
            if row["shortlisted"]:
                shortlist.append(row)

    shortlist.sort(key=lambda row: (0 if row["layer"] == "current" else 1, row["relative_path"].casefold()))
    deep_rows: list[dict[str, Any]] = []
    for index, row in enumerate(shortlist[:MAX_DEEP_MODULES], start=1):
        layer = row["layer"]
        root = next((root for candidate_layer, root in _roots(base, current) if candidate_layer == layer), None)
        if root is None:
            continue
        _write_json(progress_path, {"stage": "deep-shortlist", "index": index, "total": min(len(shortlist), MAX_DEEP_MODULES), "layer": layer, "relative_path": row["relative_path"]})
        activity(f"Game Common Data Catalog deep: {index}/{min(len(shortlist), MAX_DEEP_MODULES)} {row['relative_path']}")
        summary = _deep_summary(root / row["relative_path"])
        deep_rows.append({"layer": layer, "relative_path": row["relative_path"], **summary})

    report = {
        "schema": "dead-signal-game-common-data-catalog",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Once Human game_common/data producer layer",
        "mode": "offline-static-subtree-catalog-plus-bounded-deep-shortlist",
        "record_counts": {
            "modules_cataloged": len(inventory),
            "shortlisted_modules": len(shortlist),
            "deep_modules": len(deep_rows),
            "marshal_compatible_deep_modules": sum(bool(row.get("marshal_compatible")) for row in deep_rows),
        },
        "target_terms": list(TARGET_TERMS),
        "inventory": inventory,
        "shortlist": shortlist[:MAX_DEEP_MODULES],
        "deep_modules": deep_rows,
        "policy": {
            "scope": "Only game_common/data/**/*.pyc is cataloged. All files receive bounded streaming raw scans; only a capped relevant shortlist is unmarshaled one at a time.",
            "authority": "This is the producer/data layer. Raw token/path matches are discovery evidence; CodeType names/constants are stronger static evidence. Neither is automatically player-facing text proof.",
            "execution": "No game module is imported or executed; marshal is used only to deserialize CodeType metadata.",
            "live_game": "No process attachment, debugger, hook, injection, memory access, network interception, client modification, or anti-cheat interaction.",
        },
        "next_step": "Use the producer shortlist to identify exact backing modules for fixed_skill, PASSIVE/ACTIVE/BUFF data, gun/weapon blueprint records, and description/name fields, then trace exact weapon-linked records only.",
    }
    _write_json(reports_dir / "game-common-data-catalog.json", report)
    _write_json(progress_path, {"stage": "complete", **report["record_counts"]})
    return report
