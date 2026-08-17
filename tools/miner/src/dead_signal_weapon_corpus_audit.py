"""Read-only full-corpus Weapons completeness audit for Dead Signal.

The audit starts from the canonical published weapon identities, then scans both
retained NeoX JSON layers for exact weapon identity co-occurrence with player-
facing field families. It also scans retained PYC metadata for relevant consumer
symbols without importing or executing game modules.

Outputs are research evidence only. Candidate fields are never promoted into
published weapon data automatically.
"""
from __future__ import annotations

import json
import marshal
import types
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable

SCHEMA_VERSION = 1
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_EVIDENCE_PER_WEAPON = 500
MAX_PYC_ROWS_PER_GROUP = 300
ActivityCallback = Callable[[str], None]

FIELD_GROUPS: dict[str, tuple[str, ...]] = {
    "damage": ("damage", "attack", "atk"),
    "fire_rate": ("fire_rate", "firerate", "fire_interval", "shoot_interval", "rpm"),
    "magazine": ("magazine", "mag_size", "magazine_size", "clip", "ammo_capacity"),
    "range": ("range", "effective_range", "attack_range"),
    "reload": ("reload", "reload_time", "reload_seconds"),
    "mobility": ("mobility", "move_speed", "movement_speed"),
    "ads_time": ("ads_time", "aim_time", "aim_down_sight", "ads", "scope_time"),
    "bullet_speed": ("bullet_speed", "projectile_speed", "muzzle_speed", "bullet_velocity", "velocity"),
    "falloff": ("falloff", "full_damage", "minimum_damage", "min_damage", "damage_distance"),
    "ammo": ("ammo", "ammo_type", "ammo_item", "bullet_type", "cartridge"),
    "firing_mode": ("fire_mode", "firing_mode", "shoot_mode", "auto_fire", "burst"),
    "accuracy": ("accuracy", "spread", "dispersion"),
    "stability": ("stability", "recoil", "shake"),
    "projectiles": ("projectile_count", "bullet_num", "pellet", "scatter_num"),
    "durability": ("durability", "max_durability"),
    "weight": ("weight",),
    "perk_slots": ("perk_slot", "perk_slots", "calibration_slot", "mod_slot"),
    "crafting": ("forge", "recipe", "craft", "material", "workbench"),
    "acquisition": ("gain_path", "acquisition", "drop", "stronghold", "shop", "vendor", "reward"),
    "description": ("description", "discription", "prototype_desc", "desc"),
    "special_skill": ("fixed_skill", "passive_skill", "weapon_skill", "skill_code", "buff_id", "keyword_buff"),
    "attachment_compatibility": ("accessory_slot", "attachment", "accessory", "scope_slot", "muzzle_slot", "mag_slot"),
    "calibration_compatibility": ("calibration", "calibration_blueprint", "calibration_type", "calibration_group"),
    "image": ("icon", "image", "texture", "forge_icon"),
}

COMPETITOR_BASELINE = (
    "damage", "fire_rate", "magazine", "range", "reload", "mobility", "ads_time",
    "bullet_speed", "falloff", "ammo", "firing_mode", "description", "special_skill",
    "crafting", "acquisition",
)
DEAD_SIGNAL_ADVANTAGE = (
    "accuracy", "stability", "projectiles", "durability", "weight", "perk_slots",
    "attachment_compatibility", "calibration_compatibility", "image",
)
PRIORITY = {
    "damage": 100, "fire_rate": 100, "magazine": 100, "range": 100,
    "reload": 96, "mobility": 94, "ads_time": 94, "bullet_speed": 94,
    "falloff": 92, "ammo": 90, "firing_mode": 90, "description": 90,
    "special_skill": 90, "crafting": 88, "acquisition": 88,
    "accuracy": 78, "stability": 78, "projectiles": 78, "perk_slots": 76,
    "attachment_compatibility": 74, "calibration_compatibility": 74,
    "durability": 60, "weight": 55, "image": 50,
}


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, UnicodeError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def _source_root(snapshot: Path) -> Path | None:
    payload = _read_json(snapshot / "snapshot.json", {}) or {}
    text = str(payload.get("source_root") or "").strip() if isinstance(payload, dict) else ""
    if not text:
        return None
    root = Path(text).expanduser()
    root = (snapshot / root).resolve() if not root.is_absolute() else root.resolve()
    return root if root.is_dir() else None


def _normalized_name(value: object) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _group_for_field(field: object) -> list[str]:
    name = _normalized_name(field)
    groups = []
    for group, aliases in FIELD_GROUPS.items():
        if any(_normalized_name(alias) in name for alias in aliases):
            groups.append(group)
    return groups


def _walk_scalars(value: Any, pointer: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            kp = str(key).replace("~", "~0").replace("/", "~1")
            child_pointer = f"{pointer}/{kp}"
            yield child_pointer + "/@key", str(key), key
            yield from _walk_scalars(child, child_pointer)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            yield from _walk_scalars(child, f"{pointer}/{index}")
    else:
        field = pointer.rsplit("/", 1)[-1] if pointer else ""
        yield pointer or "/", field, value


def _iter_records(payload: Any):
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(value, dict):
                yield str(key), value
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    if isinstance(child, dict):
                        yield f"{key}[{index}]", child
        if payload and all(not isinstance(value, (dict, list)) for value in payload.values()):
            yield "<root>", payload
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            if isinstance(value, dict):
                yield str(index), value


def _weapon_seeds(weapon: dict[str, Any]) -> set[str]:
    seeds: set[str] = set()
    for field in ("blueprint_id", "item_id", "prototype_id", "fragment_id"):
        value = weapon.get(field)
        if value not in (None, "", 0):
            seeds.add(str(value))
    ranged = weapon.get("ranged_stats") if isinstance(weapon.get("ranged_stats"), dict) else {}
    for field in ("ammo_item_id", "bullet_pattern_id"):
        value = ranged.get(field)
        if value not in (None, "", 0):
            seeds.add(str(value))
    ammo = weapon.get("ammo_configuration") if isinstance(weapon.get("ammo_configuration"), dict) else {}
    for value in ammo.get("selectable_ammo_item_ids") or []:
        if value not in (None, "", 0):
            seeds.add(str(value))
    for tier in weapon.get("tiers") or []:
        if not isinstance(tier, dict):
            continue
        for field in ("item_id", "gun_no"):
            value = tier.get(field)
            if value not in (None, "", 0):
                seeds.add(str(value))
    return seeds


def _published_coverage(weapon: dict[str, Any]) -> dict[str, str]:
    ranged = weapon.get("ranged_stats") if isinstance(weapon.get("ranged_stats"), dict) else None
    melee = weapon.get("melee_stats") if isinstance(weapon.get("melee_stats"), dict) else None
    is_ranged = ranged is not None
    coverage = {group: "missing" for group in FIELD_GROUPS}

    def known(group: str, value: Any) -> None:
        if value not in (None, "", [], {}):
            coverage[group] = "published"

    tiers = [row for row in (weapon.get("tiers") or []) if isinstance(row, dict)]
    known("damage", next((row.get("damage") for row in tiers if row.get("damage") not in (None, "")), None))
    known("description", weapon.get("short_description"))
    known("acquisition", weapon.get("acquisition_hint") or weapon.get("item_gain_path"))
    known("crafting", next((row.get("recipe") for row in tiers if row.get("recipe")), None))
    known("durability", weapon.get("durability"))
    known("weight", weapon.get("weight"))
    known("image", weapon.get("image_asset") or weapon.get("image_reference") or weapon.get("icon"))
    known("special_skill", weapon.get("effect"))
    resolution = weapon.get("effect_resolution") if isinstance(weapon.get("effect_resolution"), dict) else {}
    if coverage["special_skill"] == "missing" and resolution:
        if resolution.get("publication_status") or resolution.get("status"):
            coverage["special_skill"] = "unresolved-evidence-state"

    if is_ranged:
        direct = {
            "fire_rate": "rpm", "magazine": "magazine", "range": "range_meters",
            "reload": "reload_seconds", "mobility": "mobility", "falloff": "full_damage_distance",
            "ammo": "ammo_item_id", "accuracy": "accuracy", "stability": "stability",
            "projectiles": "projectile_count",
        }
        for group, field in direct.items():
            known(group, ranged.get(field))
        if ranged.get("minimum_damage_distance") not in (None, "") or ranged.get("minimum_damage_multiplier") not in (None, ""):
            coverage["falloff"] = "published"
        ammo_cfg = weapon.get("ammo_configuration") if isinstance(weapon.get("ammo_configuration"), dict) else {}
        if ammo_cfg:
            coverage["ammo"] = "published"
            coverage["attachment_compatibility"] = "published-partial"
    else:
        for group in ("fire_rate", "magazine", "reload", "ads_time", "bullet_speed", "falloff", "ammo", "firing_mode", "accuracy", "stability", "projectiles"):
            coverage[group] = "not-applicable"
        if melee:
            known("range", melee.get("range") or melee.get("attack_range"))

    star = weapon.get("blueprint_star_progression") if isinstance(weapon.get("blueprint_star_progression"), dict) else {}
    if star.get("perk_slot_calibration_max") not in (None, ""):
        coverage["perk_slots"] = "published"
    return coverage


def _scan_json_layers(base: Path, current: Path, weapon_rows: list[dict[str, Any]], *, activity: ActivityCallback) -> dict[str, Any]:
    seed_to_weapons: dict[str, set[int]] = defaultdict(set)
    for index, row in enumerate(weapon_rows):
        for seed in row["seeds"]:
            seed_to_weapons[seed].add(index)
    evidence: list[list[dict[str, Any]]] = [[] for _ in weapon_rows]
    group_counts: Counter[str] = Counter()
    table_counts: Counter[str] = Counter()
    files_scanned = records_scanned = exact_records = 0
    errors = 0

    for layer, root in (("base", base), ("current", current)):
        paths = list(root.rglob("*.json"))
        activity(f"Weapon Corpus Audit: scanning {len(paths)} {layer} NeoX JSON tables")
        for file_index, path in enumerate(paths, start=1):
            if file_index == 1 or file_index % 1000 == 0:
                activity(f"Weapon Corpus Audit JSON {layer}: {file_index}/{len(paths)}")
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
                payload = _read_json(path, None)
            except OSError:
                errors += 1
                continue
            if payload is None:
                errors += 1
                continue
            files_scanned += 1
            relative = path.relative_to(root).as_posix()
            for record_id, record in _iter_records(payload):
                records_scanned += 1
                scalars = list(_walk_scalars(record))
                matched_indices: set[int] = set()
                matched_seeds: set[str] = set()
                for _pointer, _field, value in scalars:
                    key = str(value)
                    indices = seed_to_weapons.get(key)
                    if indices:
                        matched_indices.update(indices)
                        matched_seeds.add(key)
                if not matched_indices:
                    continue
                grouped_fields: list[tuple[str, str, str, Any]] = []
                for pointer, field, value in scalars:
                    groups = _group_for_field(field)
                    for group in groups:
                        grouped_fields.append((group, pointer, field, value))
                if not grouped_fields:
                    continue
                exact_records += 1
                table_counts[relative] += 1
                for weapon_index in matched_indices:
                    if len(evidence[weapon_index]) >= MAX_EVIDENCE_PER_WEAPON:
                        continue
                    relevant = []
                    for group, pointer, field, value in grouped_fields:
                        relevant.append({"group": group, "field": field, "json_pointer": pointer, "value": value})
                        group_counts[group] += 1
                    evidence[weapon_index].append({
                        "layer": layer,
                        "table": relative,
                        "record_id": record_id,
                        "matched_identity_values": sorted(matched_seeds.intersection(weapon_rows[weapon_index]["seeds"])),
                        "fields": relevant[:80],
                    })
    return {
        "files_scanned": files_scanned,
        "records_scanned": records_scanned,
        "exact_identity_records_with_target_fields": exact_records,
        "errors": errors,
        "evidence": evidence,
        "group_counts": dict(group_counts),
        "top_tables": [{"table": table, "matched_records": count} for table, count in table_counts.most_common(100)],
    }


def _load_marshaled_root(raw: bytes) -> types.CodeType | None:
    if len(raw) < 17:
        return None
    try:
        root = marshal.loads(raw[16:])
    except Exception:
        return None
    return root if isinstance(root, types.CodeType) else None


def _walk_code(code: types.CodeType, qualname: str = "<module>"):
    yield qualname, code
    for child in code.co_consts:
        if isinstance(child, types.CodeType):
            child_name = child.co_name if qualname == "<module>" else f"{qualname}.{child.co_name}"
            yield from _walk_code(child, child_name)


def _scan_pyc_consumers(base: Path, current: Path, *, activity: ActivityCallback) -> dict[str, Any]:
    roots = []
    seen = set()
    for layer, snapshot in (("current", current), ("base", base)):
        root = _source_root(snapshot)
        if root is None:
            continue
        key = str(root).casefold()
        if key in seen:
            continue
        seen.add(key)
        roots.append((layer, root))
    target_symbols = {alias for aliases in FIELD_GROUPS.values() for alias in aliases if len(alias) >= 3}
    token_bytes = {symbol: symbol.encode("ascii", errors="ignore") for symbol in target_symbols}
    rows_by_group: dict[str, list[dict[str, Any]]] = {group: [] for group in FIELD_GROUPS}
    files_scanned = files_with_tokens = decoded_files = 0
    for layer, root in roots:
        paths = list(root.rglob("*.pyc"))
        activity(f"Weapon Corpus Audit: scanning {len(paths)} retained PYC files in {layer}")
        for index, path in enumerate(paths, start=1):
            if index == 1 or index % 5000 == 0:
                activity(f"Weapon Corpus Audit PYC {layer}: {index}/{len(paths)}")
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
                raw = path.read_bytes()
            except OSError:
                continue
            files_scanned += 1
            present = {symbol for symbol, token in token_bytes.items() if token and token in raw}
            if not present:
                continue
            files_with_tokens += 1
            root_code = _load_marshaled_root(raw)
            if root_code is None:
                continue
            decoded_files += 1
            relative = path.relative_to(root).as_posix()
            for qualname, code in _walk_code(root_code):
                universe = set(map(str, code.co_names)) | set(map(str, code.co_varnames)) | {value for value in code.co_consts if isinstance(value, str)}
                normalized = {_normalized_name(value): value for value in universe}
                for group, aliases in FIELD_GROUPS.items():
                    if len(rows_by_group[group]) >= MAX_PYC_ROWS_PER_GROUP:
                        continue
                    matched = []
                    for alias in aliases:
                        a = _normalized_name(alias)
                        matched.extend(str(original) for norm, original in normalized.items() if a in norm)
                    if not matched:
                        continue
                    rows_by_group[group].append({
                        "layer": layer,
                        "relative_path": relative,
                        "qualname": qualname,
                        "co_name": code.co_name,
                        "matched_symbols": sorted(set(matched))[:50],
                    })
    return {
        "source_roots": len(roots),
        "files_scanned": files_scanned,
        "files_with_target_token_bytes": files_with_tokens,
        "marshal_decoded_token_files": decoded_files,
        "groups": rows_by_group,
        "group_candidate_counts": {group: len(rows) for group, rows in rows_by_group.items()},
    }


def run_weapon_corpus_audit(
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
    rows = []
    for weapon in weapons:
        rows.append({
            "weapon": weapon,
            "seeds": _weapon_seeds(weapon),
            "coverage": _published_coverage(weapon),
        })
    activity(f"Weapon Corpus Audit: {len(rows)} canonical weapon identities loaded")
    json_scan = _scan_json_layers(base, current, rows, activity=activity)
    pyc_scan = _scan_pyc_consumers(base, current, activity=activity)

    weapon_reports = []
    gap_queue = []
    status_counts: Counter[str] = Counter()
    for index, row in enumerate(rows):
        weapon = row["weapon"]
        coverage = dict(row["coverage"])
        evidence = json_scan["evidence"][index]
        candidate_groups = Counter()
        for record in evidence:
            for field in record.get("fields") or []:
                candidate_groups[str(field.get("group"))] += 1
        for group, state in list(coverage.items()):
            if state == "missing" and candidate_groups.get(group):
                coverage[group] = "candidate-evidence-found"
        for state in coverage.values():
            status_counts[state] += 1
        missing = []
        for group in COMPETITOR_BASELINE + DEAD_SIGNAL_ADVANTAGE:
            state = coverage.get(group, "missing")
            if state in ("published", "published-partial", "not-applicable"):
                continue
            priority = PRIORITY.get(group, 50)
            if state == "candidate-evidence-found":
                priority += 8
            missing.append({"group": group, "state": state, "priority": priority, "exact_candidate_records": candidate_groups.get(group, 0)})
            gap_queue.append({
                "priority": priority,
                "blueprint_id": weapon.get("blueprint_id"),
                "name": weapon.get("name"),
                "category": weapon.get("category"),
                "group": group,
                "state": state,
                "exact_candidate_records": candidate_groups.get(group, 0),
                "pyc_consumer_candidates": len((pyc_scan.get("groups") or {}).get(group) or []),
            })
        weapon_reports.append({
            "blueprint_id": weapon.get("blueprint_id"),
            "item_id": weapon.get("item_id"),
            "prototype_id": weapon.get("prototype_id"),
            "name": weapon.get("name"),
            "category": weapon.get("category"),
            "identity_seeds": sorted(row["seeds"]),
            "coverage": coverage,
            "coverage_counts": dict(Counter(coverage.values())),
            "gaps": sorted(missing, key=lambda item: (-item["priority"], item["group"])),
            "exact_corpus_evidence": evidence,
        })

    gap_queue.sort(key=lambda item: (-item["priority"], -item["exact_candidate_records"], str(item["name"]), item["group"]))
    group_summary = {}
    for group in COMPETITOR_BASELINE + DEAD_SIGNAL_ADVANTAGE:
        states = Counter(report["coverage"].get(group, "missing") for report in weapon_reports)
        group_summary[group] = {
            "states": dict(states),
            "exact_json_field_hits": int((json_scan.get("group_counts") or {}).get(group, 0)),
            "pyc_consumer_candidates": int((pyc_scan.get("group_candidate_counts") or {}).get(group, 0)),
            "priority": PRIORITY.get(group, 50),
            "baseline": "competitor" if group in COMPETITOR_BASELINE else "dead-signal-advantage",
        }

    report = {
        "schema": "dead-signal-weapon-corpus-audit",
        "schema_version": SCHEMA_VERSION,
        "brand": "Dead Signal",
        "subject": "Complete player-facing Weapons corpus coverage",
        "mode": "overnight-read-only-full-corpus-audit",
        "record_counts": {
            "weapons": len(weapon_reports),
            "json_files_scanned": json_scan["files_scanned"],
            "json_records_scanned": json_scan["records_scanned"],
            "exact_identity_records_with_target_fields": json_scan["exact_identity_records_with_target_fields"],
            "pyc_files_scanned": pyc_scan["files_scanned"],
            "pyc_files_with_target_tokens": pyc_scan["files_with_target_token_bytes"],
            "gaps": len(gap_queue),
            "coverage_states": dict(status_counts),
        },
        "coverage_contract": {
            "competitor_baseline": list(COMPETITOR_BASELINE),
            "dead_signal_advantage": list(DEAD_SIGNAL_ADVANTAGE),
            "rule": "Competitor-visible fields are research targets, never source-of-truth. Installed-game exact evidence remains authoritative.",
        },
        "group_summary": group_summary,
        "gap_queue": gap_queue,
        "weapons": weapon_reports,
        "json_scan": {
            "files_scanned": json_scan["files_scanned"],
            "records_scanned": json_scan["records_scanned"],
            "exact_identity_records_with_target_fields": json_scan["exact_identity_records_with_target_fields"],
            "errors": json_scan["errors"],
            "top_tables": json_scan["top_tables"],
        },
        "pyc_consumer_scan": pyc_scan,
        "policy": {
            "identity": "Only exact canonical blueprint/item/prototype/tier-gun/tier-item/ammo identities seed record association; no fuzzy name or similar-ID matching.",
            "scope": "Both retained NeoX JSON layers are scanned, plus all retained PYC source roots available from snapshot metadata.",
            "execution": "PYC files are unmarshaled for static CodeType metadata only. Game modules and game bytecode are never executed.",
            "publication": "Candidate evidence is research-only. Missing and candidate states never auto-promote values into published weapon data.",
            "absence": "No exact candidate found means this audit did not locate one in the current corpus; it does not prove the game lacks the concept.",
        },
    }
    destination = reports_dir / "weapon-corpus-audit.json"
    _write_json(destination, report)
    activity(f"Weapon Corpus Audit complete: {len(weapon_reports)} weapons; {len(gap_queue)} ranked gaps")
    return report
