"""Focused read-only trace for the last high-value Weapons launch gaps.

This pass is intentionally narrow. It statically inspects retained snapshot
sources for the ShootMode enum construction, inventories projectile-related gun
fields and exact pattern/scatter relations, and builds Cradle entry/reference
matrices plus static consumer leads. It never executes game bytecode and never
promotes a human-facing label from a guess.
"""
from __future__ import annotations

import dis
import json
import marshal
import types
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 4
ActivityCallback = Callable[[str], None]
SHOOT_CONST_PYC = "dcs_extend/const/shoot_const.pyc"
GUN_BASE_TABLE = "game_common/data/gun_base_params_data.json"
BULLET_SCATTER_TABLE = "game_common/data/bullet_scatter_data.json"
BULLET_PATTERN_TABLE = "client_data/bullet_pattern_data.json"
CRADLE_ENTRY_TABLE = "game_common/data/cradle_override_entry_data.json"
CRADLE_CONFIG_TABLE = "game_common/data/cradle_override_config_new_data.json"
SHOOT_NAME_ORDER = ("NONE", "SINGLE", "BURST", "AUTO")
TARGET_SHOOT_NAMES = set(SHOOT_NAME_ORDER)
RELATION_TOKENS = ("bullet", "projectile", "pattern", "scatter", "pellet")
CRADLE_CONSUMER_TOKENS = (
    b"cradle_override_entry", b"cradle_override", b"weapon_type", b"gun_type",
    b"weapon_category", b"key_word_no", b"key_word_lst",
)


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, UnicodeError):
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


def _source_roots(base: Path, current: Path) -> list[tuple[str, Path]]:
    result: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for layer, snapshot in (("current", current), ("base", base)):
        root = _source_root(snapshot)
        if root is None:
            continue
        key = str(root).casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append((layer, root))
    return result


def _table_roots(base: Path, current: Path) -> list[tuple[str, Path]]:
    result: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for layer, snapshot in (("current", current), ("base", base)):
        root = snapshot.resolve()
        if not root.is_dir():
            continue
        key = str(root).casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append((layer, root))
    return result


def _load_code(path: Path) -> types.CodeType | None:
    raw: bytes | None = None
    try:
        raw = path.read_bytes()
        value = marshal.loads(raw[16:]) if len(raw) >= 17 else None
    except Exception:
        return None
    finally:
        raw = None
    return value if isinstance(value, types.CodeType) else None


def _walk(code: types.CodeType, qualname: str = "<module>"):
    yield qualname, code
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            child = value.co_name if qualname == "<module>" else f"{qualname}.{value.co_name}"
            yield from _walk(value, child)


def _instruction_row(instruction: dis.Instruction) -> dict[str, Any]:
    argval = instruction.argval
    if not isinstance(argval, (str, int, float, bool, type(None))):
        argval = repr(argval)[:240]
    return {
        "offset": instruction.offset,
        "opname": instruction.opname,
        "arg": instruction.arg,
        "argval": argval,
        "argrepr": instruction.argrepr,
    }


def _shoot_mode_enum(roots: list[tuple[str, Path]]) -> dict[str, Any]:
    for layer, root in roots:
        path = root / SHOOT_CONST_PYC
        if not path.is_file():
            continue
        code = _load_code(path)
        if code is None:
            continue
        for qualname, child in _walk(code):
            if child.co_name != "ShootMode":
                continue
            names = [name for name in map(str, child.co_names) if name in TARGET_SHOOT_NAMES]
            int_consts = [
                int(value) for value in child.co_consts
                if isinstance(value, int) and not isinstance(value, bool)
            ]
            structural_mapping: dict[str, int] = {}
            structural_ok = (
                names == list(SHOOT_NAME_ORDER)
                and len(int_consts) == len(SHOOT_NAME_ORDER)
                and len(set(int_consts)) == len(int_consts)
            )
            if structural_ok:
                structural_mapping = dict(zip(SHOOT_NAME_ORDER, int_consts))

            try:
                instructions = list(dis.get_instructions(child))
            except Exception:
                instructions = []
            mapping: dict[str, int] = {}
            evidence: list[dict[str, Any]] = []
            for index, instruction in enumerate(instructions):
                if instruction.opname != "STORE_NAME" or str(instruction.argval) not in TARGET_SHOOT_NAMES:
                    continue
                name = str(instruction.argval)
                value = None
                for previous in reversed(instructions[max(0, index - 8):index]):
                    if previous.opname == "LOAD_CONST" and isinstance(previous.argval, int) and not isinstance(previous.argval, bool):
                        value = int(previous.argval)
                        break
                window = [_instruction_row(row) for row in instructions[max(0, index - 8):min(len(instructions), index + 3)]]
                evidence.append({
                    "name": name,
                    "value": value,
                    "store_offset": instruction.offset,
                    "instruction_window": window,
                })
                if value is not None:
                    mapping[name] = value

            if not TARGET_SHOOT_NAMES.issubset(mapping) and structural_mapping:
                mapping = structural_mapping
                state = "resolved-static-class-constant-order"
                proof = {
                    "method": "class-code-object-name-and-integer-constant-order",
                    "name_order": names,
                    "integer_constant_order": int_consts,
                    "mapping": structural_mapping,
                    "constraints": "Exactly four enum names in canonical order and exactly four unique integer constants are required.",
                }
            else:
                state = "resolved-static-enum" if TARGET_SHOOT_NAMES.issubset(mapping) else "partial-static-enum"
                proof = None

            return {
                "state": state,
                "layer": layer,
                "relative_path": SHOOT_CONST_PYC,
                "qualname": qualname,
                "mapping": mapping,
                "evidence": evidence,
                "structural_proof": proof,
                "co_names": list(map(str, child.co_names)),
                "co_consts": [value for value in child.co_consts if isinstance(value, (str, int, float, bool, type(None)))][:100],
                "policy": "Numeric enum values require either direct static assignment evidence or an exact one-to-one class name/constant ordering with no extra integer constants; game bytecode is never executed.",
            }
    return {"state": "unresolved", "mapping": {}, "evidence": []}


def _normalize_table(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        return {}
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def _active_table(roots: list[tuple[str, Path]], relative: str) -> tuple[str | None, dict[str, dict[str, Any]]]:
    for layer, root in roots:
        path = root / relative
        payload = _read_json(path, None) if path.is_file() else None
        table = _normalize_table(payload)
        if table:
            return layer, table
    return None, {}


def _first_tier_gun(weapon: dict[str, Any]) -> Any:
    rows = [row for row in (weapon.get("tiers") or []) if isinstance(row, dict)]
    row = min(rows, key=lambda value: int(value.get("tier") or 999), default={})
    return row.get("gun_no")


def _relation_fields(record: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {}
    return {
        str(field): value
        for field, value in record.items()
        if any(token in str(field).casefold() for token in RELATION_TOKENS)
    }


def _projectile_trace(roots: list[tuple[str, Path]], weapons: list[dict[str, Any]]) -> dict[str, Any]:
    gun_layer, gun_table = _active_table(roots, GUN_BASE_TABLE)
    scatter_layer, scatter_table = _active_table(roots, BULLET_SCATTER_TABLE)
    pattern_layer, pattern_table = _active_table(roots, BULLET_PATTERN_TABLE)
    rows = []
    relation_field_counts: Counter[str] = Counter()
    pattern_field_counts: Counter[str] = Counter()
    for record in gun_table.values():
        for field in _relation_fields(record):
            relation_field_counts[field] += 1
    for record in pattern_table.values():
        for field in record:
            if any(token in str(field).casefold() for token in ("bullet", "projectile", "pellet", "count", "num")):
                pattern_field_counts[str(field)] += 1

    resolved = 0
    ranged_total = 0
    patternless_ranged = 0
    for weapon in weapons:
        published_ranged = weapon.get("ranged_stats") if isinstance(weapon.get("ranged_stats"), dict) else {}
        if published_ranged:
            ranged_total += 1
        gun_no = _first_tier_gun(weapon)
        gun_record = gun_table.get(str(gun_no)) if gun_no not in (None, "") else None
        relations = _relation_fields(gun_record)
        scatter_no = relations.get("bullet_scatter_no") if relations else None
        scatter_record = scatter_table.get(str(scatter_no)) if scatter_no not in (None, "") else None

        pattern_no = published_ranged.get("bullet_pattern_id")
        if pattern_no in (None, "") and isinstance(gun_record, dict):
            for key in ("bullet_pattern_no", "bullet_pattern_id", "bullet_pattern"):
                if gun_record.get(key) not in (None, ""):
                    pattern_no = gun_record.get(key)
                    break
        if published_ranged and pattern_no in (None, ""):
            patternless_ranged += 1
        pattern_record = pattern_table.get(str(pattern_no)) if pattern_no not in (None, "") else None
        exact_count = None
        exact_field = None
        if isinstance(pattern_record, dict):
            for field in ("bullet_num", "projectile_count", "pellet_num", "pellet_count"):
                value = pattern_record.get(field)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    exact_count = value
                    exact_field = field
                    break
        if exact_count is not None:
            resolved += 1
        state = "resolved-exact-pattern-record" if exact_count is not None else (
            "pattern-record-located" if isinstance(pattern_record, dict) else (
                "gun-projectile-relations-located" if relations else "projectile-relation-unresolved"
            )
        )
        rows.append({
            "blueprint_id": weapon.get("blueprint_id"),
            "name": weapon.get("name"),
            "tier_one_gun_no": gun_no,
            "gun_relation_fields": relations,
            "bullet_scatter_no": scatter_no,
            "scatter_record_found": isinstance(scatter_record, dict),
            "bullet_pattern_no": pattern_no,
            "pattern_record_found": isinstance(pattern_record, dict),
            "state": state,
            "projectile_count": exact_count,
            "projectile_count_field": exact_field,
            "source": {
                "gun_layer": gun_layer,
                "gun_table": GUN_BASE_TABLE,
                "scatter_layer": scatter_layer,
                "scatter_table": BULLET_SCATTER_TABLE,
                "pattern_layer": pattern_layer,
                "pattern_table": BULLET_PATTERN_TABLE,
            },
        })
    return {
        "record_counts": {
            "weapons": len(rows),
            "ranged_weapons": ranged_total,
            "gun_records": sum(bool(row.get("gun_relation_fields")) for row in rows),
            "scatter_records": sum(bool(row.get("scatter_record_found")) for row in rows),
            "pattern_records": sum(bool(row.get("pattern_record_found")) for row in rows),
            "projectile_counts_resolved": resolved,
            "patternless_ranged_weapons": patternless_ranged,
        },
        "gun_relation_field_inventory": dict(sorted(relation_field_counts.items())),
        "pattern_projectile_field_inventory": dict(sorted(pattern_field_counts.items())),
        "weapons": rows,
    }


def _walk_values(value: Any):
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_values(child)
    else:
        yield value


def _cradle_reference_matrix(roots: list[tuple[str, Path]]) -> dict[str, Any]:
    entry_layer, entries = _active_table(roots, CRADLE_ENTRY_TABLE)
    config_layer, configs = _active_table(roots, CRADLE_CONFIG_TABLE)
    entry_ids = set(entries)
    referenced_by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for config_id, record in configs.items():
        for field, value in record.items():
            hits = sorted({str(item) for item in _walk_values(value) if str(item) in entry_ids})
            for entry_id in hits:
                referenced_by[entry_id].append({"config_id": config_id, "field": str(field)})
    rows = []
    for entry_id, record in entries.items():
        rows.append({
            "entry_id": entry_id,
            "style_no": record.get("style_no"),
            "key_word_no": record.get("key_word_no"),
            "buff_id": record.get("buff_id"),
            "name": record.get("name"),
            "desc": record.get("desc"),
            "referenced_by": referenced_by.get(entry_id, []),
        })
    return {
        "state": "exact-entry-config-reference-matrix",
        "entry_layer": entry_layer,
        "config_layer": config_layer,
        "record_counts": {
            "entries": len(rows),
            "config_records": len(configs),
            "entries_referenced_by_config": sum(bool(row["referenced_by"]) for row in rows),
        },
        "entries": rows,
    }


def _cradle_consumer_leads(source_roots: list[tuple[str, Path]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for layer, root in source_roots:
        for path in root.rglob("*.pyc"):
            key = str(path.resolve()).casefold()
            if key in seen:
                continue
            seen.add(key)
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            matched = [token.decode("ascii") for token in CRADLE_CONSUMER_TOKENS if token in raw]
            if not matched or not any("cradle" in token for token in matched):
                continue
            rows.append({
                "layer": layer,
                "relative_path": path.relative_to(root).as_posix(),
                "matched_tokens": matched,
            })
            if len(rows) >= 250:
                break
        if len(rows) >= 250:
            break
    rows.sort(key=lambda row: (-len(row["matched_tokens"]), row["relative_path"]))
    return {
        "state": "static-consumer-leads" if rows else "unresolved",
        "record_counts": {"pyc_leads": len(rows)},
        "leads": rows,
    }


def _cradle_inventory(roots: list[tuple[str, Path]], source_roots: list[tuple[str, Path]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for layer, root in roots:
        for path in root.rglob("*.json"):
            relative = path.relative_to(root).as_posix()
            if "cradle" not in relative.casefold():
                continue
            key = relative.casefold()
            if key in seen:
                continue
            seen.add(key)
            payload = _read_json(path, None)
            table = _normalize_table(payload)
            field_counts: Counter[str] = Counter()
            samples: list[dict[str, Any]] = []
            for record_id, record in list(table.items())[:200]:
                for field in record.keys():
                    field_counts[str(field)] += 1
                if len(samples) < 5:
                    samples.append({"record_id": record_id, "record": record})
            rows.append({
                "layer": layer,
                "relative_path": relative,
                "records": len(table),
                "fields": [name for name, _count in field_counts.most_common(80)],
                "samples": samples,
            })
    rows.sort(key=lambda row: (-int(row.get("records") or 0), str(row.get("relative_path"))))
    matrix = _cradle_reference_matrix(roots)
    consumers = _cradle_consumer_leads(source_roots)
    return {
        "record_counts": {
            "tables": len(rows),
            "records": sum(int(row.get("records") or 0) for row in rows),
            "override_entries": (matrix.get("record_counts") or {}).get("entries", 0),
            "entries_referenced_by_config": (matrix.get("record_counts") or {}).get("entries_referenced_by_config", 0),
            "consumer_pyc_leads": (consumers.get("record_counts") or {}).get("pyc_leads", 0),
        },
        "tables": rows,
        "entry_reference_matrix": matrix,
        "consumer_leads": consumers,
        "state": "typed-consumer-proof-needed" if rows else "unresolved",
    }


def run_weapon_launch_gap_trace(
    base: Path,
    current: Path,
    weapons_path: Path,
    reports_dir: Path,
    *,
    activity: ActivityCallback | None = None,
) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    payload = _read_json(weapons_path, {}) or {}
    weapons = [row for row in (payload.get("weapons") or []) if isinstance(row, dict)]
    source_roots = _source_roots(base, current)
    table_roots = _table_roots(base, current)
    activity("Launch Gap Trace: resolving static ShootMode construction")
    firing_mode = _shoot_mode_enum(source_roots)
    activity("Launch Gap Trace: inventorying gun projectile/pattern relations")
    projectiles = _projectile_trace(table_roots, weapons)
    activity("Launch Gap Trace: building Cradle entry/reference and consumer matrices")
    cradle = _cradle_inventory(table_roots, source_roots)
    report = {
        "schema": "dead-signal-weapon-launch-gap-trace",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Weapons launch gaps",
        "mode": "offline-read-only-focused-semantic-trace",
        "record_counts": {
            "weapons": len(weapons),
            "shoot_mode_values": len(firing_mode.get("mapping") or {}),
            "projectile_counts_resolved": (projectiles.get("record_counts") or {}).get("projectile_counts_resolved", 0),
            "cradle_tables": (cradle.get("record_counts") or {}).get("tables", 0),
            "cradle_entries": (cradle.get("record_counts") or {}).get("override_entries", 0),
            "cradle_consumer_leads": (cradle.get("record_counts") or {}).get("consumer_pyc_leads", 0),
        },
        "firing_mode": firing_mode,
        "projectiles": projectiles,
        "cradle": cradle,
        "policy": {
            "authority": "Installed-game snapshot only.",
            "publication": "Only exact numeric enum assignments and exact typed table relationships may be promoted; table-name, text, or token matches remain locators.",
            "bytecode": "Static marshal/disassembly and code-object structure only; game bytecode is never imported or executed.",
        },
    }
    destination = reports_dir / "weapon-launch-gap-trace.json"
    _write_json(destination, report)
    activity(
        "Launch Gap Trace complete: "
        f"shoot modes {report['record_counts']['shoot_mode_values']}; "
        f"projectiles {report['record_counts']['projectile_counts_resolved']}; "
        f"Cradle entries {report['record_counts']['cradle_entries']}"
    )
    return report
