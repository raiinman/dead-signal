"""Exhaustive-but-bounded static weapon-description presentation trace.

This pass exists for one purpose: stop guessing where player-facing weapon text
lives.  It starts from known weapon UI/presentation vocabulary and exact AA12
identities, scans the already-extracted client read-only, and records only exact
static evidence.  It never imports or executes game modules.
"""
from __future__ import annotations

import json
import marshal
import re
import types
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable

from neoxtractor.core.bindict.parser import BindictParser

ActivityCallback = Callable[[str], None]
SCHEMA_VERSION = 1
MAX_CODE_OBJECTS = 4000
MAX_STRUCTURED_ROWS = 1000
MAX_FILES = 1200

AA12_TOKENS: tuple[bytes, ...] = (
    b"13231101",  # blueprint
    b"10231101",  # item
    b"10230011",  # gun
    b"aa12",
    b"AA12",
    b"sg_aa12_sk_a_01",
)
DESCRIPTION_TOKENS: tuple[bytes, ...] = (
    b"prototype_desc",
    b"short_desc",
    b"description",
    b"discription",
    b"copywriting",
    b"item_desc",
    b"skill_desc",
    b"label_desc",
    b"label_skill_desc",
    b"rich_text",
    b"tooltip",
    b"tips",
)
PRESENTATION_TOKENS: tuple[bytes, ...] = (
    b"get_item_desc_text",
    b"get_weapon_item_data",
    b"get_gun_item_data",
    b"get_gun_info",
    b"get_weapon_prototype_data",
    b"get_weapon_prototype_data_val_by_key",
    b"weapon_prototype_data",
    b"PassiveSkillHelper",
    b"get_passive_skill_name",
)

KNOWN_PRESENTATION_BASENAMES = {
    "itemdatatools.pyc",
    "blueprinthelper.pyc",
    "scrollviewitems.pyc",
    "weaponcraftpanel.pyc",
    "uiguntipitem.pyc",
    "passiveskillhelper.pyc",
}
UI_NAME_RE = re.compile(
    r"(?:weapon|gun|equip|item).*(?:tip|detail|info|craft|view)|(?:tip|detail|info|craft|view).*(?:weapon|gun|equip|item)",
    re.IGNORECASE,
)
DESC_KEY_RE = re.compile(r"(?:^|_)(?:desc|description|discription|copywriting|tips?|text|detail|tooltip)(?:$|_)", re.IGNORECASE)


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


def _snapshot_source_root(snapshot: Path) -> Path | None:
    payload = _read_json(snapshot, {}) or {}
    raw = payload.get("source_root") if isinstance(payload, dict) else None
    if not raw:
        return None
    root = Path(str(raw)).expanduser()
    return root.resolve() if root.exists() else None


def _roots(base: Path, current: Path) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for layer, snapshot in (("current", current / "snapshot.json"), ("base", base / "snapshot.json")):
        root = _snapshot_source_root(snapshot)
        if root is None:
            continue
        key = str(root).casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append((layer, root))
    return out


def _walk_code(code: types.CodeType, prefix: str = "") -> Iterable[tuple[str, types.CodeType]]:
    qual = f"{prefix}.{code.co_name}" if prefix else code.co_name
    yield qual, code
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            yield from _walk_code(const, qual)


def _load_code(raw: bytes) -> tuple[types.CodeType | None, str | None]:
    if len(raw) < 17:
        return None, "pyc-too-small"
    try:
        value = marshal.loads(raw[16:])
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    return (value, None) if isinstance(value, types.CodeType) else (None, "marshal-not-code")


def _literal_hits(raw: bytes, tokens: tuple[bytes, ...]) -> list[str]:
    return [token.decode("utf-8", errors="replace") for token in tokens if token in raw]


def _is_ui_candidate(path: Path) -> bool:
    name = path.name.casefold()
    if name in KNOWN_PRESENTATION_BASENAMES:
        return True
    rel = path.as_posix().casefold()
    return "/ui/" in f"/{rel}" and bool(UI_NAME_RE.search(path.stem))


def _code_metadata(relative_path: str, layer: str, code: types.CodeType) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for qualname, obj in _walk_code(code):
        names = [str(v) for v in obj.co_names]
        constants = [v for v in obj.co_consts if isinstance(v, str)]
        combined = set(names) | set(constants) | {obj.co_name}
        desc_hits = sorted({v for v in combined if DESC_KEY_RE.search(v)})
        presentation_hits = sorted({token.decode() for token in PRESENTATION_TOKENS if token.decode() in combined})
        aa12_hits = sorted({token.decode(errors="replace") for token in AA12_TOKENS if token.decode(errors="replace") in combined})
        if not (desc_hits or presentation_hits or aa12_hits):
            continue
        rows.append({
            "layer": layer,
            "pyc": relative_path,
            "qualname": qualname,
            "function": obj.co_name,
            "firstlineno": obj.co_firstlineno,
            "description_symbols": desc_hits,
            "presentation_symbols": presentation_hits,
            "aa12_symbols": aa12_hits,
            "relevant_names": [v for v in names if DESC_KEY_RE.search(v) or v in presentation_hits],
            "relevant_string_constants": [v for v in constants if DESC_KEY_RE.search(v) or v in presentation_hits or v in aa12_hits],
        })
        if len(rows) >= MAX_CODE_OBJECTS:
            break
    return rows


def _contains_exact_identity(value: Any) -> bool:
    targets = {13231101, 10231101, 10230011, "13231101", "10231101", "10230011", "aa12", "AA12", "sg_aa12_sk_a_01"}
    if value in targets:
        return True
    if isinstance(value, str):
        return any(str(target) in value for target in targets)
    return False


def _structured_hits(value: Any, path: str = "", *, out: list[dict[str, Any]], context_has_identity: bool = False) -> None:
    if len(out) >= MAX_STRUCTURED_ROWS:
        return
    if isinstance(value, dict):
        local_identity = context_has_identity or any(_contains_exact_identity(k) or _contains_exact_identity(v) for k, v in value.items() if not isinstance(v, (dict, list, tuple)))
        desc_fields = {
            str(k): v for k, v in value.items()
            if isinstance(k, str) and DESC_KEY_RE.search(k) and not isinstance(v, (dict, list, tuple))
        }
        if local_identity and desc_fields:
            out.append({"json_pointer": path or "/", "description_fields": desc_fields})
        for key, child in value.items():
            _structured_hits(child, f"{path}/{key}", out=out, context_has_identity=local_identity)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _structured_hits(child, f"{path}/{index}", out=out, context_has_identity=context_has_identity)


def _try_bindict(raw: bytes) -> tuple[Any, str | None]:
    try:
        return BindictParser(debug=False).extract_from_pyc(raw), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def run_weapon_description_full_trace(
    base: Path,
    current: Path,
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    roots = _roots(base, current)
    file_rows: list[dict[str, Any]] = []
    code_rows: list[dict[str, Any]] = []
    structured_rows: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()
    seen: set[str] = set()

    for layer, root in roots:
        activity(f"Weapon Description Full Trace: scanning extracted client ({layer})")
        for path in root.rglob("*.pyc"):
            if len(file_rows) >= MAX_FILES:
                counters["file_limit_reached"] += 1
                break
            key = str(path.resolve()).casefold()
            if key in seen:
                continue
            seen.add(key)
            try:
                raw = path.read_bytes()
            except OSError:
                counters["read_errors"] += 1
                continue
            counters["pyc_files_scanned"] += 1
            aa12_hits = _literal_hits(raw, AA12_TOKENS)
            desc_hits = _literal_hits(raw, DESCRIPTION_TOKENS)
            presentation_hits = _literal_hits(raw, PRESENTATION_TOKENS)
            ui_candidate = _is_ui_candidate(path)
            if not (aa12_hits or desc_hits or presentation_hits or ui_candidate):
                continue

            relative = path.relative_to(root).as_posix()
            row = {
                "layer": layer,
                "relative_path": relative,
                "ui_candidate": ui_candidate,
                "aa12_literal_hits": aa12_hits,
                "description_literal_hits": desc_hits,
                "presentation_literal_hits": presentation_hits,
            }
            code, marshal_error = _load_code(raw)
            row["marshal_compatible"] = code is not None
            row["marshal_error"] = marshal_error
            file_rows.append(row)
            if code is not None:
                code_rows.extend(_code_metadata(relative, layer, code))

            # Parse only high-value candidate data modules. This is still static
            # Bindict decoding, never module execution.
            rel_lower = relative.casefold()
            if "/data/" in f"/{rel_lower}" and (aa12_hits or desc_hits or b"weapon_prototype" in raw.lower()):
                decoded, bindict_error = _try_bindict(raw)
                hits: list[dict[str, Any]] = []
                if decoded is not None:
                    _structured_hits(decoded, out=hits)
                if hits or aa12_hits:
                    structured_rows.append({
                        "layer": layer,
                        "relative_path": relative,
                        "aa12_literal_hits": aa12_hits,
                        "bindict_decoded": decoded is not None,
                        "bindict_error": bindict_error,
                        "aa12_description_rows": hits,
                    })

    exact_aa12_files = [row for row in file_rows if row["aa12_literal_hits"]]
    ui_files = [row for row in file_rows if row["ui_candidate"]]
    desc_files = [row for row in file_rows if row["description_literal_hits"]]
    presentation_files = [row for row in file_rows if row["presentation_literal_hits"]]
    exact_text_rows = [
        {"layer": row["layer"], "relative_path": row["relative_path"], "rows": row["aa12_description_rows"]}
        for row in structured_rows if row["aa12_description_rows"]
    ]

    report = {
        "schema": "dead-signal-weapon-description-full-trace",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Weapon Description / AA12 presentation path",
        "mode": "offline-read-only-static-pyc-and-bindict",
        "record_counts": {
            "source_roots": len(roots),
            "pyc_files_scanned": counters["pyc_files_scanned"],
            "candidate_files": len(file_rows),
            "ui_candidate_files": len(ui_files),
            "description_literal_files": len(desc_files),
            "presentation_literal_files": len(presentation_files),
            "aa12_exact_literal_files": len(exact_aa12_files),
            "selected_code_objects": len(code_rows),
            "structured_candidate_tables": len(structured_rows),
            "aa12_structured_description_tables": len(exact_text_rows),
            "read_errors": counters["read_errors"],
            "file_limit_reached": bool(counters["file_limit_reached"]),
        },
        "aa12_identity": {
            "blueprint_id": 13231101,
            "item_id": 10231101,
            "gun_no": 10230011,
            "name_tokens": ["aa12", "AA12"],
            "posture_token": "sg_aa12_sk_a_01",
        },
        "candidate_files": file_rows,
        "ui_presentation_candidates": ui_files,
        "aa12_exact_literal_files": exact_aa12_files,
        "structured_candidates": structured_rows,
        "aa12_structured_description_candidates": exact_text_rows,
        "code_objects": code_rows,
        "policy": {
            "matching": "Only exact AA12 IDs/tokens and exact description/presentation literals are promoted into the report; no fuzzy identity matching.",
            "execution": "Game modules are never imported or executed. PYC files are read, marshalled code objects are inspected as metadata, and Bindict data modules are decoded statically.",
            "publication": "Description candidates remain research-only until an exact UI consumer -> field/table -> localization path is proven.",
        },
        "next_step": (
            "If aa12_structured_description_candidates is non-empty, verify the owning field against a UI code-object consumer. "
            "Otherwise rank ui_presentation_candidates by description/presentation symbol co-occurrence and trace the exact helper/table dependency backward."
        ),
    }
    _write_json(reports_dir / "weapon-description-full-trace.json", report)
    return report
