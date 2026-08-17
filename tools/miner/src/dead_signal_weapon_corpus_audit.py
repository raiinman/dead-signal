"""Read-only full-corpus Weapons completeness audit for Dead Signal.

Weapon evidence is modeled at two explicit scopes:

* variant-local: blueprint/item/prototype/gun identities that own one weapon
  variant and may answer any weapon-local player-facing field.
* family-shared: proven shared relationship identities (currently bullet pattern)
  that may answer only the ballistic/projectile fields owned by that relation.

Variant-local evidence has precedence over inherited family evidence. Shared
relationship IDs never establish weapon ownership and can never answer local
handling, firing-mode, reload, mechanic, acquisition, or similar fields.

Retained PYC files are inspected only as static CodeType metadata. Nothing from
this report is promoted into player-facing data automatically.
"""
from __future__ import annotations

import json
import marshal
import types
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 4
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
    "projectiles": ("projectile_count", "bullet_num", "pellet", "scatter_num", "scatter"),
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

OWNER_IDENTITY_FIELDS = {
    "blueprint_id", "blueprint_no", "gun_blueprint_no", "gun_blueprint_id",
    "item_id", "item_no", "equip_no", "weapon_no", "gun_no", "gun_id",
    "prototype_id", "prototype_no", "weapon_prototype_no", "fragment_id", "fragment_no",
}
# Compatibility alias used by callers/tests written before evidence scopes existed.
IDENTITY_FIELDS = OWNER_IDENTITY_FIELDS

FAMILY_RELATION_FIELDS = {
    "bullet_pattern_id": "bullet-pattern",
    "bullet_pattern_no": "bullet-pattern",
}
FAMILY_SHARED_GROUPS = frozenset({"projectiles", "bullet_speed", "falloff"})

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
    return [group for group, aliases in FIELD_GROUPS.items() if any(_normalized_name(alias) in name for alias in aliases)]


def _walk_leaves(value: Any, pointer: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            kp = str(key).replace("~", "~0").replace("/", "~1")
            yield from _walk_leaves(child, f"{pointer}/{kp}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            yield from _walk_leaves(child, f"{pointer}/{index}")
    else:
        field = pointer.rsplit("/", 1)[-1] if pointer else ""
        yield pointer or "/", field, value


def _iter_records(payload: Any):
    """Yield isolated records, flattening common NeoX data->{id: record} maps."""
    if isinstance(payload, list):
        for index, value in enumerate(payload):
            if isinstance(value, dict):
                yield str(index), value
        return
    if not isinstance(payload, dict):
        return
    if payload and all(not isinstance(value, (dict, list)) for value in payload.values()):
        yield "<root>", payload
        return
    for key, value in payload.items():
        if isinstance(value, list):
            for index, child in enumerate(value):
                if isinstance(child, dict):
                    yield f"{key}[{index}]", child
            continue
        if not isinstance(value, dict):
            continue
        child_dicts = [(child_key, child) for child_key, child in value.items() if isinstance(child, dict)]
        scalar_children = sum(not isinstance(child, (dict, list)) for child in value.values())
        if child_dicts and scalar_children == 0:
            for child_key, child in child_dicts:
                yield str(child_key), child
        else:
            yield str(key), value


def _weapon_seeds(weapon: dict[str, Any]) -> set[str]:
    """Return variant-owner identities only; shared relation IDs are excluded."""
    seeds: set[str] = set()
    for field in ("blueprint_id", "item_id", "prototype_id", "fragment_id"):
        value = weapon.get(field)
        if value not in (None, "", 0):
            seeds.add(str(value))
    for tier in weapon.get("tiers") or []:
        if isinstance(tier, dict):
            for field in ("item_id", "gun_no"):
                value = tier.get(field)
                if value not in (None, "", 0):
                    seeds.add(str(value))
    return seeds


def _family_seeds(weapon: dict[str, Any]) -> dict[str, str]:
    """Return exact shared relationship IDs and their relation kind."""
    result: dict[str, str] = {}
    ranged = weapon.get("ranged_stats") if isinstance(weapon.get("ranged_stats"), dict) else {}
    value = ranged.get("bullet_pattern_id")
    if value not in (None, "", 0):
        result[str(value)] = "bullet-pattern"
    return result


def _published_coverage(weapon: dict[str, Any]) -> dict[str, str]:
    ranged = weapon.get("ranged_stats") if isinstance(weapon.get("ranged_stats"), dict) else None
    melee = weapon.get("melee_stats") if isinstance(weapon.get("melee_stats"), dict) else None
    coverage = {group: "missing" for group in FIELD_GROUPS}

    def known(group: str, value: Any) -> None:
        if value not in (None, "", [], {}):
            coverage[group] = "published"

    tiers = [row for row in (weapon.get("tiers") or []) if isinstance(row, dict)]
    known("damage", next((row.get("damage") for row in tiers if row.get("damage") not in (None, "")), None))
    known("description", weapon.get("short_description"))
    known("acquisition", weapon.get("acquisition_hint") or weapon.get("item_gain_path"))
    known("crafting", next((row.get("recipe") for row in tiers if row.get("recipe")), None))
    known("durability", weapon.get("durability")); known("weight", weapon.get("weight"))
    known("image", weapon.get("image_asset") or weapon.get("image_reference") or weapon.get("icon"))
    known("special_skill", weapon.get("effect"))
    resolution = weapon.get("effect_resolution") if isinstance(weapon.get("effect_resolution"), dict) else {}
    if coverage["special_skill"] == "missing" and resolution and (resolution.get("publication_status") or resolution.get("status")):
        coverage["special_skill"] = "unresolved-evidence-state"
    if ranged is not None:
        for group, field in {
            "fire_rate": "rpm", "magazine": "magazine", "range": "range_meters", "reload": "reload_seconds",
            "mobility": "mobility", "falloff": "full_damage_distance", "ammo": "ammo_item_id",
            "accuracy": "accuracy", "stability": "stability", "projectiles": "projectile_count",
        }.items():
            known(group, ranged.get(field))
        if ranged.get("minimum_damage_distance") not in (None, "") or ranged.get("minimum_damage_multiplier") not in (None, ""):
            coverage["falloff"] = "published"
        ammo_cfg = weapon.get("ammo_configuration") if isinstance(weapon.get("ammo_configuration"), dict) else {}
        if ammo_cfg:
            coverage["ammo"] = "published"; coverage["attachment_compatibility"] = "published-partial"
    else:
        for group in ("fire_rate", "magazine", "reload", "ads_time", "bullet_speed", "falloff", "ammo", "firing_mode", "accuracy", "stability", "projectiles"):
            coverage[group] = "not-applicable"
        if melee:
            known("range", melee.get("range") or melee.get("attack_range"))
    star = weapon.get("blueprint_star_progression") if isinstance(weapon.get("blueprint_star_progression"), dict) else {}
    if star.get("perk_slot_calibration_max") not in (None, ""):
        coverage["perk_slots"] = "published"
    return coverage


def _strong_record_key(record_id: str) -> bool:
    text = str(record_id).strip()
    if not text:
        return False
    if text.isdigit():
        return len(text) >= 6
    return len(text) >= 6


def _typed_identity_matches(record_id: str, leaves: list[tuple[str, str, Any]], seeds: set[str]) -> set[str]:
    """Match exact variant-owner identities only."""
    matched: set[str] = set()
    if _strong_record_key(record_id) and str(record_id) in seeds:
        matched.add(str(record_id))
    for _pointer, field, value in leaves:
        if _normalized_name(field) not in OWNER_IDENTITY_FIELDS:
            continue
        text = str(value)
        if text in seeds:
            matched.add(text)
    return matched


def _family_identity_matches(record_id: str, leaves: list[tuple[str, str, Any]], seeds: dict[str, str]) -> dict[str, str]:
    """Match exact family/shared relationship identities without claiming ownership."""
    matched: dict[str, str] = {}
    if _strong_record_key(record_id) and str(record_id) in seeds:
        matched[str(record_id)] = seeds[str(record_id)]
    for _pointer, field, value in leaves:
        normalized = _normalized_name(field)
        relation_kind = FAMILY_RELATION_FIELDS.get(normalized)
        if not relation_kind:
            continue
        text = str(value)
        if text in seeds and seeds[text] == relation_kind:
            matched[text] = relation_kind
    return matched


def _scan_json_layers(base: Path, current: Path, weapon_rows: list[dict[str, Any]], *, activity: ActivityCallback) -> dict[str, Any]:
    owner_to_weapons: dict[str, set[int]] = defaultdict(set)
    family_to_weapons: dict[str, set[int]] = defaultdict(set)
    for index, row in enumerate(weapon_rows):
        for seed in row["seeds"]:
            owner_to_weapons[seed].add(index)
        for seed in row["family_seeds"]:
            family_to_weapons[seed].add(index)

    evidence: list[list[dict[str, Any]]] = [[] for _ in weapon_rows]
    group_counts: Counter[str] = Counter(); table_counts: Counter[str] = Counter(); scope_counts: Counter[str] = Counter()
    files_scanned = records_scanned = exact_records = errors = 0

    for layer, root in (("base", base), ("current", current)):
        paths = list(root.rglob("*.json")); activity(f"Weapon Corpus Audit: scanning {len(paths)} {layer} NeoX JSON tables")
        for file_index, path in enumerate(paths, start=1):
            if file_index == 1 or file_index % 1000 == 0:
                activity(f"Weapon Corpus Audit JSON {layer}: {file_index}/{len(paths)}")
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
                payload = _read_json(path, None)
            except OSError:
                errors += 1; continue
            if payload is None:
                errors += 1; continue
            files_scanned += 1; relative = path.relative_to(root).as_posix()

            for record_id, record in _iter_records(payload):
                records_scanned += 1
                leaves = list(_walk_leaves(record))
                candidate_owner_values: set[str] = set()
                candidate_family_values: set[str] = set()
                if _strong_record_key(record_id):
                    candidate_owner_values.add(str(record_id)); candidate_family_values.add(str(record_id))
                for _pointer, field, value in leaves:
                    normalized = _normalized_name(field)
                    if normalized in OWNER_IDENTITY_FIELDS:
                        candidate_owner_values.add(str(value))
                    if normalized in FAMILY_RELATION_FIELDS:
                        candidate_family_values.add(str(value))

                candidate_indices: set[int] = set()
                for value in candidate_owner_values:
                    candidate_indices.update(owner_to_weapons.get(value, set()))
                for value in candidate_family_values:
                    candidate_indices.update(family_to_weapons.get(value, set()))
                if not candidate_indices:
                    continue

                grouped_fields = [(group, pointer, field, value) for pointer, field, value in leaves for group in _group_for_field(field)]
                if not grouped_fields:
                    continue

                record_matched = False
                for weapon_index in candidate_indices:
                    row = weapon_rows[weapon_index]
                    owner_matches = _typed_identity_matches(record_id, leaves, row["seeds"])
                    family_matches = _family_identity_matches(record_id, leaves, row["family_seeds"])
                    if not owner_matches and not family_matches:
                        continue

                    if owner_matches:
                        evidence_scope = "variant-local"
                        eligible_fields = grouped_fields
                    else:
                        evidence_scope = "family-shared"
                        eligible_fields = [item for item in grouped_fields if item[0] in FAMILY_SHARED_GROUPS]
                    if not eligible_fields:
                        continue

                    record_matched = True
                    if len(evidence[weapon_index]) >= MAX_EVIDENCE_PER_WEAPON:
                        continue
                    relevant = []
                    for group, pointer, field, value in eligible_fields:
                        relevant.append({"group": group, "field": field, "json_pointer": pointer, "value": value})
                        group_counts[group] += 1
                    relation_kinds = sorted(set(family_matches.values()))
                    evidence[weapon_index].append({
                        "layer": layer,
                        "table": relative,
                        "record_id": record_id,
                        "evidence_scope": evidence_scope,
                        "precedence": 2 if evidence_scope == "variant-local" else 1,
                        "matched_identity_values": sorted(owner_matches or family_matches.keys()),
                        "matched_owner_identity_values": sorted(owner_matches),
                        "matched_family_identity_values": sorted(family_matches.keys()),
                        "family_relation_kinds": relation_kinds,
                        "fields": relevant[:80],
                    })
                    scope_counts[evidence_scope] += 1
                if record_matched:
                    exact_records += 1; table_counts[relative] += 1

    return {
        "files_scanned": files_scanned,
        "records_scanned": records_scanned,
        "exact_identity_records_with_target_fields": exact_records,
        "errors": errors,
        "evidence": evidence,
        "group_counts": dict(group_counts),
        "scope_counts": dict(scope_counts),
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
            name = child.co_name if qualname == "<module>" else f"{qualname}.{child.co_name}"
            yield from _walk_code(child, name)


def _scan_pyc_consumers(base: Path, current: Path, *, activity: ActivityCallback) -> dict[str, Any]:
    roots = []; seen = set()
    for layer, snapshot in (("current", current), ("base", base)):
        root = _source_root(snapshot)
        if root is None or str(root).casefold() in seen:
            continue
        seen.add(str(root).casefold()); roots.append((layer, root))
    rows_by_group = {group: [] for group in FIELD_GROUPS}; files_scanned = files_with_tokens = decoded_files = 0
    tokens = {alias: alias.encode("ascii", errors="ignore") for aliases in FIELD_GROUPS.values() for alias in aliases if len(alias) >= 3}
    for layer, root in roots:
        paths = list(root.rglob("*.pyc")); activity(f"Weapon Corpus Audit: scanning {len(paths)} retained PYC files in {layer}")
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
            if not any(token and token in raw for token in tokens.values()):
                continue
            files_with_tokens += 1; root_code = _load_marshaled_root(raw)
            if root_code is None:
                continue
            decoded_files += 1; relative = path.relative_to(root).as_posix()
            for qualname, code in _walk_code(root_code):
                universe = set(map(str, code.co_names)) | set(map(str, code.co_varnames)) | {value for value in code.co_consts if isinstance(value, str)}
                normalized = {_normalized_name(value): value for value in universe}
                for group, aliases in FIELD_GROUPS.items():
                    if len(rows_by_group[group]) >= MAX_PYC_ROWS_PER_GROUP:
                        continue
                    matched = [str(original) for alias in aliases for norm, original in normalized.items() if _normalized_name(alias) in norm]
                    if matched:
                        rows_by_group[group].append({"layer": layer, "relative_path": relative, "qualname": qualname, "co_name": code.co_name, "matched_symbols": sorted(set(matched))[:50]})
    return {
        "source_roots": len(roots), "files_scanned": files_scanned,
        "files_with_target_token_bytes": files_with_tokens, "marshal_decoded_token_files": decoded_files,
        "groups": rows_by_group, "group_candidate_counts": {group: len(rows) for group, rows in rows_by_group.items()},
    }


def run_weapon_corpus_audit(base: Path, current: Path, weapons_path: Path, reports_dir: Path, *, activity: ActivityCallback | None = None) -> dict[str, Any]:
    activity = activity or (lambda _message: None)
    payload = _read_json(weapons_path, {}) or {}
    weapons = [row for row in (payload.get("weapons") or []) if isinstance(row, dict)]
    rows = [{
        "weapon": weapon,
        "seeds": _weapon_seeds(weapon),
        "family_seeds": _family_seeds(weapon),
        "coverage": _published_coverage(weapon),
    } for weapon in weapons]
    activity(f"Weapon Corpus Audit: {len(rows)} canonical weapon identities loaded")
    json_scan = _scan_json_layers(base, current, rows, activity=activity)
    pyc_scan = _scan_pyc_consumers(base, current, activity=activity)

    weapon_reports = []; gap_queue = []; status_counts: Counter[str] = Counter()
    for index, row in enumerate(rows):
        weapon = row["weapon"]; coverage = dict(row["coverage"]); evidence = json_scan["evidence"][index]
        candidate_groups: Counter[str] = Counter(); local_groups: Counter[str] = Counter(); family_groups: Counter[str] = Counter()
        for record in evidence:
            scope = str(record.get("evidence_scope") or "variant-local")
            for field in record.get("fields") or []:
                group = str(field.get("group")); candidate_groups[group] += 1
                if scope == "family-shared": family_groups[group] += 1
                else: local_groups[group] += 1
        for group, state in list(coverage.items()):
            if state == "missing" and candidate_groups.get(group):
                coverage[group] = "candidate-evidence-found"
        status_counts.update(coverage.values()); missing = []
        for group in COMPETITOR_BASELINE + DEAD_SIGNAL_ADVANTAGE:
            state = coverage.get(group, "missing")
            if state in ("published", "published-partial", "not-applicable"):
                continue
            priority = PRIORITY.get(group, 50) + (8 if state == "candidate-evidence-found" else 0)
            item = {
                "group": group, "state": state, "priority": priority,
                "exact_candidate_records": candidate_groups.get(group, 0),
                "variant_local_candidate_records": local_groups.get(group, 0),
                "family_shared_candidate_records": family_groups.get(group, 0),
            }
            missing.append(item)
            gap_queue.append({
                "priority": priority, "blueprint_id": weapon.get("blueprint_id"), "name": weapon.get("name"),
                "category": weapon.get("category"), "group": group, "state": state,
                "exact_candidate_records": candidate_groups.get(group, 0),
                "variant_local_candidate_records": local_groups.get(group, 0),
                "family_shared_candidate_records": family_groups.get(group, 0),
                "pyc_consumer_candidates": len((pyc_scan.get("groups") or {}).get(group) or []),
            })
        weapon_reports.append({
            "blueprint_id": weapon.get("blueprint_id"), "item_id": weapon.get("item_id"),
            "prototype_id": weapon.get("prototype_id"), "name": weapon.get("name"), "category": weapon.get("category"),
            "identity_seeds": sorted(row["seeds"]),
            "family_inheritance": {
                "shared_relationships": [{"id": value, "kind": kind} for value, kind in sorted(row["family_seeds"].items())],
                "allowed_groups": sorted(FAMILY_SHARED_GROUPS),
                "precedence": ["variant-local", "family-shared"],
                "rule": "Variant-local exact evidence overrides inherited family evidence for the same field; family relationships never establish variant ownership.",
            },
            "coverage": coverage, "coverage_counts": dict(Counter(coverage.values())),
            "gaps": sorted(missing, key=lambda item: (-item["priority"], item["group"])),
            "exact_corpus_evidence": evidence,
        })

    gap_queue.sort(key=lambda item: (-item["priority"], -item["exact_candidate_records"], str(item["name"]), item["group"]))
    group_summary = {}
    for group in COMPETITOR_BASELINE + DEAD_SIGNAL_ADVANTAGE:
        states = Counter(report["coverage"].get(group, "missing") for report in weapon_reports)
        group_summary[group] = {
            "states": dict(states), "exact_json_field_hits": int((json_scan.get("group_counts") or {}).get(group, 0)),
            "pyc_consumer_candidates": int((pyc_scan.get("group_candidate_counts") or {}).get(group, 0)),
            "priority": PRIORITY.get(group, 50), "baseline": "competitor" if group in COMPETITOR_BASELINE else "dead-signal-advantage",
        }

    report = {
        "schema": "dead-signal-weapon-corpus-audit", "schema_version": SCHEMA_VERSION, "brand": "Dead Signal",
        "subject": "Complete player-facing Weapons corpus coverage", "mode": "overnight-read-only-full-corpus-audit",
        "record_counts": {
            "weapons": len(weapon_reports), "json_files_scanned": json_scan["files_scanned"],
            "json_records_scanned": json_scan["records_scanned"],
            "exact_identity_records_with_target_fields": json_scan["exact_identity_records_with_target_fields"],
            "evidence_scope_counts": json_scan.get("scope_counts") or {},
            "pyc_files_scanned": pyc_scan["files_scanned"], "pyc_files_with_target_tokens": pyc_scan["files_with_target_token_bytes"],
            "gaps": len(gap_queue), "coverage_states": dict(status_counts),
        },
        "coverage_contract": {
            "competitor_baseline": list(COMPETITOR_BASELINE), "dead_signal_advantage": list(DEAD_SIGNAL_ADVANTAGE),
            "rule": "Competitor-visible fields are research targets, never source-of-truth. Installed-game exact evidence remains authoritative.",
            "inheritance": "Shared family relationships are retained as scoped evidence. Variant-local values override inherited family values.",
        },
        "group_summary": group_summary, "gap_queue": gap_queue, "weapons": weapon_reports,
        "json_scan": {
            "files_scanned": json_scan["files_scanned"], "records_scanned": json_scan["records_scanned"],
            "exact_identity_records_with_target_fields": json_scan["exact_identity_records_with_target_fields"],
            "evidence_scope_counts": json_scan.get("scope_counts") or {}, "errors": json_scan["errors"], "top_tables": json_scan["top_tables"],
        },
        "pyc_consumer_scan": pyc_scan,
        "policy": {
            "identity": "Variant ownership requires an exact canonical owner seed in a strong isolated record key or typed owner field. Shared relation IDs never establish variant ownership.",
            "family_inheritance": "Exact bullet-pattern relationships may supply only projectile/ballistic evidence groups. Variant-local evidence has higher precedence and acts as an override.",
            "scope": "Both retained NeoX JSON layers are scanned, plus retained PYC source roots available from snapshot metadata.",
            "execution": "PYC files are unmarshaled for static CodeType metadata only; game modules and game bytecode are never executed.",
            "publication": "Candidate evidence is research-only and never auto-promotes values.",
            "absence": "No exact candidate means this audit did not locate one in the current corpus; it does not prove the concept is absent.",
        },
    }
    destination = reports_dir / "weapon-corpus-audit.json"; _write_json(destination, report)
    activity(f"Weapon Corpus Audit complete: {len(weapon_reports)} weapons; {len(gap_queue)} ranked gaps")
    return report
