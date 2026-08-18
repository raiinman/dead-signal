"""Focused read-only trace for the last high-value Weapons launch gaps.

This pass is intentionally narrow.  It statically inspects retained snapshot
sources for the ShootMode enum, follows Tier-I gun -> bullet_scatter_no into the
exact bullet_scatter_data record, and inventories Cradle-related structured
tables.  It never executes game bytecode and never promotes a human-facing label
from a guess.
"""
from __future__ import annotations

import dis
import json
import marshal
import types
from collections import Counter
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 1
ActivityCallback = Callable[[str], None]
SHOOT_CONST_PYC = "dcs_extend/const/shoot_const.pyc"
GUN_BASE_TABLE = "game_common/data/gun_base_params_data.json"
BULLET_SCATTER_TABLE = "game_common/data/bullet_scatter_data.json"
TARGET_SHOOT_NAMES = {"SINGLE", "BURST", "AUTO"}


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


def _roots(base: Path, current: Path) -> list[tuple[str, Path]]:
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


def _load_code(path: Path) -> types.CodeType | None:
    try:
        raw = path.read_bytes()
        value = marshal.loads(raw[16:]) if len(raw) >= 17 else None
    except Exception:
        return None
    finally:
        try:
            del raw
        except UnboundLocalError:
            pass
    return value if isinstance(value, types.CodeType) else None


def _walk(code: types.CodeType):
    yield code
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            yield from _walk(value)


def _shoot_mode_enum(roots: list[tuple[str, Path]]) -> dict[str, Any]:
    for layer, root in roots:
        path = root / SHOOT_CONST_PYC
        if not path.is_file():
            continue
        code = _load_code(path)
        if code is None:
            continue
        for child in _walk(code):
            if child.co_name != "ShootMode":
                continue
            instructions = list(dis.get_instructions(child))
            mapping: dict[str, int] = {}
            evidence: list[dict[str, Any]] = []
            for index, instruction in enumerate(instructions):
                if instruction.opname != "STORE_NAME" or str(instruction.argval) not in TARGET_SHOOT_NAMES:
                    continue
                name = str(instruction.argval)
                value = None
                for previous in reversed(instructions[max(0, index - 6):index]):
                    if previous.opname == "LOAD_CONST" and isinstance(previous.argval, int) and not isinstance(previous.argval, bool):
                        value = int(previous.argval)
                        break
                evidence.append({
                    "name": name,
                    "value": value,
                    "store_offset": instruction.offset,
                })
                if value is not None:
                    mapping[name] = value
            return {
                "state": "resolved-static-enum" if TARGET_SHOOT_NAMES.issubset(mapping) else "partial-static-enum",
                "layer": layer,
                "relative_path": SHOOT_CONST_PYC,
                "mapping": mapping,
                "evidence": evidence,
                "policy": "Numeric enum values come from static class-body bytecode only; game bytecode is never executed.",
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


def _projectile_trace(roots: list[tuple[str, Path]], weapons: list[dict[str, Any]]) -> dict[str, Any]:
    gun_layer, gun_table = _active_table(roots, GUN_BASE_TABLE)
    scatter_layer, scatter_table = _active_table(roots, BULLET_SCATTER_TABLE)
    rows = []
    resolved = 0
    for weapon in weapons:
        gun_no = _first_tier_gun(weapon)
        gun_record = gun_table.get(str(gun_no)) if gun_no not in (None, "") else None
        scatter_no = gun_record.get("bullet_scatter_no") if isinstance(gun_record, dict) else None
        scatter_record = scatter_table.get(str(scatter_no)) if scatter_no not in (None, "") else None
        exact_count = None
        exact_field = None
        if isinstance(scatter_record, dict):
            for field in ("bullet_num", "projectile_count"):
                value = scatter_record.get(field)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    exact_count = value
                    exact_field = field
                    break
        state = "resolved-exact-scatter-record" if exact_count is not None else (
            "scatter-record-located" if isinstance(scatter_record, dict) else "scatter-record-unresolved"
        )
        if exact_count is not None:
            resolved += 1
        rows.append({
            "blueprint_id": weapon.get("blueprint_id"),
            "name": weapon.get("name"),
            "tier_one_gun_no": gun_no,
            "bullet_scatter_no": scatter_no,
            "state": state,
            "projectile_count": exact_count,
            "projectile_count_field": exact_field,
            "source": {
                "gun_layer": gun_layer,
                "gun_table": GUN_BASE_TABLE,
                "scatter_layer": scatter_layer,
                "scatter_table": BULLET_SCATTER_TABLE,
            },
        })
    return {
        "record_counts": {
            "weapons": len(rows),
            "gun_records": sum(row.get("bullet_scatter_no") not in (None, "") for row in rows),
            "scatter_records": sum(row.get("state") in {"scatter-record-located", "resolved-exact-scatter-record"} for row in rows),
            "projectile_counts_resolved": resolved,
        },
        "weapons": rows,
    }


def _cradle_inventory(roots: list[tuple[str, Path]]) -> dict[str, Any]:
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
    return {
        "record_counts": {"tables": len(rows), "records": sum(int(row.get("records") or 0) for row in rows)},
        "tables": rows,
        "state": "tables-located-needs-typed-relationship-proof" if rows else "unresolved",
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
    roots = _roots(base, current)
    activity("Launch Gap Trace: resolving static ShootMode enum")
    firing_mode = _shoot_mode_enum(roots)
    activity("Launch Gap Trace: following Tier-I gun -> bullet_scatter_data")
    projectiles = _projectile_trace(roots, weapons)
    activity("Launch Gap Trace: inventorying Cradle structured tables")
    cradle = _cradle_inventory(roots)
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
        },
        "firing_mode": firing_mode,
        "projectiles": projectiles,
        "cradle": cradle,
        "policy": {
            "authority": "Installed-game snapshot only.",
            "publication": "Only exact numeric enum assignments and exact typed table relationships may be promoted; table-name or token matches remain locators.",
            "bytecode": "Static marshal/disassembly only; game bytecode is never imported or executed.",
        },
    }
    destination = reports_dir / "weapon-launch-gap-trace.json"
    _write_json(destination, report)
    activity(
        "Launch Gap Trace complete: "
        f"shoot modes {report['record_counts']['shoot_mode_values']}; "
        f"projectiles {report['record_counts']['projectile_counts_resolved']}; "
        f"Cradle tables {report['record_counts']['cradle_tables']}"
    )
    return report
