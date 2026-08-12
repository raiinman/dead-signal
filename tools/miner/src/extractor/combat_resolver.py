"""Depth-oriented combat resolution for the existing Dead Signal snapshots.

This module does not extract game archives.  It operates exclusively on the
base/current JSON table corpus already produced by Dead Signal Miner and extends
the existing published datasets with calculator-ready mechanics, provenance,
relationships, reference tracing, and explicit unresolved reports.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from normalize_armor import Translator, player_facing_effect, translation_entries
from weapon_progression import run_weapon_progression_investigation


GAME_DATA = "game_common/data"
ID_FIELD = re.compile(
    r"(?:^|_)(?:id|ids|no|code|ref|buff|skill|status|keyword|stat|ammo|mod|"
    r"calibration|affix)(?:$|_)", re.IGNORECASE
)
# Once Human uses canonical 3-character stat IDs (e.g. D01/Q03) plus
# 5-character affix IDs whose final two digits may be non-zero (e.g. D0101/D0102).
# Do not restrict the extended form to a 00 suffix or proven Attack-ratio affixes
# will be silently skipped during normalized-stat export.
STAT_CODE = re.compile(r"^[A-Z][0-9]{2}(?:[0-9]{2})?$")
TUPLE_KEY = re.compile(r"-?\d+")
WEAPON_CLASSES = {
    1: "Pistol", 2: "Shotgun", 3: "Submachine Gun", 4: "Assault Rifle",
    5: "Sniper Rifle", 6: "Light Machine Gun", 7: "Bow / Crossbow",
    8: "Heavy Weapon", 9: "Melee", 10: "Melee",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {} if default is None else default


def _json_cycle_safe_copy(value, *, active=None, path="$", diagnostics=None):
    """Copy a JSON-like graph while cutting only true ancestor back-references.

    json.dumps() allows the same dict/list to appear in separate branches, but it
    rejects a container that points back to one of its active ancestors.  Preserve
    normal shared references; replace only the actual cycle with a small marker and
    record both JSON paths for a later source-level fix.
    """
    if active is None:
        active = {}
    if diagnostics is None:
        diagnostics = []

    if isinstance(value, dict):
        object_id = id(value)
        if object_id in active:
            diagnostics.append({
                "cycle_path": path,
                "ancestor_path": active[object_id],
                "container_type": "dict",
            })
            return {"_dead_signal_circular_reference": active[object_id]}
        active[object_id] = path
        copied = {}
        for key, child in value.items():
            child_path = f"{path}/{str(key).replace('~', '~0').replace('/', '~1')}"
            copied[key] = _json_cycle_safe_copy(
                child, active=active, path=child_path, diagnostics=diagnostics
            )
        active.pop(object_id, None)
        return copied

    if isinstance(value, (list, tuple)):
        object_id = id(value)
        if object_id in active:
            diagnostics.append({
                "cycle_path": path,
                "ancestor_path": active[object_id],
                "container_type": type(value).__name__,
            })
            return {"_dead_signal_circular_reference": active[object_id]}
        active[object_id] = path
        copied = [
            _json_cycle_safe_copy(
                child, active=active, path=f"{path}/{index}", diagnostics=diagnostics
            )
            for index, child in enumerate(value)
        ]
        active.pop(object_id, None)
        return copied

    return value


def _write_cycle_diagnostic(path: Path, diagnostics: list[dict]) -> None:
    if not diagnostics:
        return
    reports_dir = path.parent.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "serialization-circular-references.json"
    existing = read_json(report_path, {"schema_version": 1, "events": []})
    events = existing.get("events") if isinstance(existing, dict) else None
    if not isinstance(events, list):
        events = []
    events.append({
        "generated_utc": utc_now(),
        "output_file": str(path),
        "cycles": diagnostics,
        "status": "cycle-cut-for-json-export-source-fix-required",
    })
    report_path.write_text(
        json.dumps({"schema_version": 1, "events": events}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        encoded = json.dumps(payload, ensure_ascii=False, indent=2)
    except ValueError as exc:
        if "Circular reference detected" not in str(exc):
            raise
        diagnostics = []
        safe_payload = _json_cycle_safe_copy(payload, diagnostics=diagnostics)
        _write_cycle_diagnostic(path, diagnostics)
        encoded = json.dumps(safe_payload, ensure_ascii=False, indent=2)
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(path)


def rows(payload) -> dict:
    if isinstance(payload, dict):
        value = payload.get("data", payload)
        return value if isinstance(value, dict) else {}
    return {}


def ints(value: object) -> list[int]:
    return [int(item) for item in TUPLE_KEY.findall(str(value))]


def as_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def number(value):
    try:
        parsed = float(value)
        return int(parsed) if parsed.is_integer() else parsed
    except (TypeError, ValueError):
        return value


def slug(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.casefold())).strip("_")


def walk_scalars(value, pointer="", field_hint=""):
    if isinstance(value, dict):
        for key, child in value.items():
            child_pointer = f"{pointer}/{str(key).replace('~', '~0').replace('/', '~1')}"
            if isinstance(child, (dict, list)):
                yield from walk_scalars(child, child_pointer, str(key))
            else:
                yield child_pointer, str(key), child
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_pointer = f"{pointer}/{index}"
            if isinstance(child, (dict, list)):
                yield from walk_scalars(child, child_pointer, field_hint)
            else:
                yield child_pointer, field_hint or str(index), child


def translated(translate: Translator, value, replacements=None) -> str:
    text = translate(value)
    return player_facing_effect(text, replacements or []) if text else ""


class TableCorpus:
    """Patch-aware access to the already-extracted JSON table corpus."""

    def __init__(self, base: Path, current: Path):
        self.base = base
        self.current = current
        self._cache: dict[str, dict] = {}
        self._logic_index: dict[str, tuple[Path, str]] | None = None

    def merged(self, relative: str) -> dict:
        relative = relative.replace("\\", "/")
        if relative not in self._cache:
            result = dict(rows(read_json(self.base / relative)))
            result.update(rows(read_json(self.current / relative)))
            self._cache[relative] = result
        return self._cache[relative]

    def merged_glob(self, relative_pattern: str) -> tuple[dict, dict]:
        merged: dict = {}
        provenance: dict = {}
        for layer, root in (("base", self.base), ("current", self.current)):
            for path in sorted(root.glob(relative_pattern)):
                relative = path.relative_to(root).as_posix()
                if "/logic_tree/" in f"/{relative}" and not path.name.startswith("buff_"):
                    continue
                for key, record in rows(read_json(path)).items():
                    merged[str(key)] = record
                    provenance[str(key)] = {"layer": layer, "table": relative, "record_id": str(key)}
        return merged, provenance

    def logic_index(self) -> dict[str, tuple[Path, str]]:
        if self._logic_index is None:
            result: dict[str, tuple[Path, str]] = {}
            for layer, root in (("base", self.base), ("current", self.current)):
                directory = root / GAME_DATA / "logic_tree"
                if not directory.exists():
                    continue
                for path in directory.glob("*.json"):
                    result[path.stem.casefold()] = (path, layer)
            self._logic_index = result
        return self._logic_index

    def logic_tree(self, reference: str) -> tuple[dict | None, dict]:
        found = self.logic_index().get(str(reference).casefold())
        if not found:
            return None, {"logic_tree_ref": reference, "status": "missing"}
        path, layer = found
        root = self.current if layer == "current" else self.base
        return rows(read_json(path)), {
            "layer": layer,
            "table": path.relative_to(root).as_posix(),
            "logic_tree_ref": reference,
        }

    def snapshot_fingerprint(self) -> str:
        digest = hashlib.sha256()
        for root in (self.base, self.current):
            snapshot = read_json(root / "snapshot.json", {})
            digest.update(str(snapshot.get("archive_sha256") or root).encode("utf-8"))
        return digest.hexdigest()


class ReferenceTracer:
    """Reusable SQLite occurrence index for meaningful IDs in the raw corpus."""

    RELEVANT_TABLE = re.compile(
        r"(?:buff|skill|status|keyword|mod_|gun_|weapon|ammo|bullet|correct|"
        r"calibration|cradle|deviation|consum|food|item_data|char_property|"
        r"equip|suit|forge|blueprint|progress|level_data)", re.IGNORECASE
    )

    def __init__(self, corpus: TableCorpus, database: Path):
        self.corpus = corpus
        self.database = database

    @staticmethod
    def _indexable(field: str, value) -> bool:
        if value is None or isinstance(value, bool):
            return False
        text = str(value).strip()
        if not text or len(text) > 160:
            return False
        return bool(ID_FIELD.search(field) or STAT_CODE.fullmatch(text))

    def build(self) -> dict:
        fingerprint = self.corpus.snapshot_fingerprint()
        if self.database.exists():
            try:
                connection = sqlite3.connect(self.database)
                previous = connection.execute(
                    "SELECT value FROM metadata WHERE key='snapshot_fingerprint'"
                ).fetchone()
                count = connection.execute("SELECT COUNT(*) FROM occurrences").fetchone()[0]
                connection.close()
                if previous and previous[0] == fingerprint and count:
                    return {"database": str(self.database), "occurrences": count, "reused": True}
            except sqlite3.Error:
                pass

        self.database.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.database.with_suffix(".tmp.sqlite")
        if temporary.exists():
            temporary.unlink()
        connection = sqlite3.connect(temporary)
        connection.executescript(
            """
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE occurrences (
                value TEXT NOT NULL, layer TEXT NOT NULL, table_name TEXT NOT NULL,
                record_id TEXT NOT NULL, field TEXT NOT NULL, json_pointer TEXT NOT NULL
            );
            CREATE INDEX occurrence_value_idx ON occurrences(value);
            CREATE INDEX occurrence_table_idx ON occurrences(table_name);
            """
        )
        pending = []
        table_count = 0
        for layer, root in (("base", self.corpus.base), ("current", self.corpus.current)):
            for path in root.rglob("*.json"):
                if path.name == "snapshot.json":
                    continue
                relative = path.relative_to(root).as_posix()
                # The tracer indexes every table that can participate in the
                # supported combat/build domains.  Unrelated AI behavior,
                # cinematics, maps, and UI layouts are intentionally excluded.
                if not self.RELEVANT_TABLE.search(relative):
                    continue
                payload_rows = rows(read_json(path))
                if not payload_rows:
                    continue
                table_count += 1
                for record_id, record in payload_rows.items():
                    pending.append((str(record_id), layer, relative, str(record_id), "record_id", "/data"))
                    for pointer, field, value in walk_scalars(record):
                        if self._indexable(field, value):
                            pending.append((str(value), layer, relative, str(record_id), field, f"/data/{record_id}{pointer}"))
                    if len(pending) >= 10000:
                        connection.executemany("INSERT INTO occurrences VALUES (?,?,?,?,?,?)", pending)
                        pending.clear()
        if pending:
            connection.executemany("INSERT INTO occurrences VALUES (?,?,?,?,?,?)", pending)
        connection.execute("INSERT INTO metadata VALUES (?,?)", ("snapshot_fingerprint", fingerprint))
        connection.execute("INSERT INTO metadata VALUES (?,?)", ("created_utc", utc_now()))
        connection.commit()
        occurrence_count = connection.execute("SELECT COUNT(*) FROM occurrences").fetchone()[0]
        connection.close()
        temporary.replace(self.database)
        return {
            "database": str(self.database), "occurrences": occurrence_count,
            "tables": table_count, "reused": False,
        }

    def trace(self, query: object, limit=1000) -> dict:
        connection = sqlite3.connect(self.database)
        try:
            matches = [
                {
                    "source": layer, "table": table_name, "record_id": record_id,
                    "field": field, "json_pointer": pointer,
                }
                for layer, table_name, record_id, field, pointer in connection.execute(
                    "SELECT layer,table_name,record_id,field,json_pointer FROM occurrences WHERE value=? ORDER BY table_name,record_id LIMIT ?",
                    (str(query), int(limit)),
                )
            ]
        finally:
            connection.close()
        return {"query": str(query), "match_count": len(matches), "matches": matches}


class StatResolver:
    """Canonical stat dictionary with a validated calibration-code convention."""

    CANONICAL_OVERRIDES = {
        "crit_rate": "critical_hit_rate",
        "crit_dam_rate": "critical_hit_damage",
        "weak_dam_rate": "weakspot_damage",
        "weapon_rpm_add_rate": "rate_of_fire",
        "attack_type_dam_add_rate_remote": "weapon_damage",
    }

    def __init__(self, corpus: TableCorpus, translate: Translator):
        self.translate = translate
        self.by_id = {}
        self.by_internal = {}
        self.unresolved = Counter()
        # Raw affix variants (e.g. Q1101) declare their canonical attr_id and
        # flat/rate type in affix_prototype_data. Preserve that relation so
        # non-zero suffix variants are resolved from mined metadata rather than
        # guessed from the identifier.
        self.affix_prototypes = corpus.merged(f"{GAME_DATA}/affix_prototype_data.json")
        source = corpus.merged(f"{GAME_DATA}/char_property_data.json")
        for internal_name, record in source.items():
            stat_id = str(record.get("attr_id") or "")
            if not stat_id:
                continue
            normalized = {
                "stat_id": stat_id,
                "internal_name": str(internal_name),
                "display_name": translated(translate, record.get("attr_chs_name")) or str(internal_name),
                "canonical_name": self.CANONICAL_OVERRIDES.get(str(internal_name), slug(str(internal_name))),
                "unit": "percent" if "rate" in str(internal_name).casefold() else "flat",
                "value_type": record.get("val_type"),
                "source": {"table": f"{GAME_DATA}/char_property_data.json", "record_id": str(internal_name)},
            }
            self.by_id[stat_id] = normalized
            self.by_internal[str(internal_name)] = normalized

    def resolve(self, raw_stat_id: object, context="") -> dict:
        raw = str(raw_stat_id or "")
        found = self.by_id.get(raw) or self.by_internal.get(raw)
        rule = "exact"
        canonical_id = found.get("stat_id") if found else ""

        # D0101 and D0102 are not standalone char_property_data IDs. Static
        # client consumers prove that both are percentage contributions to the
        # D01 (Damage/Attack) ratio accumulator. Preserve them as resolved
        # modifiers instead of silently dropping them from normalized
        # attachment/calibration stats.
        if not found and raw in {"D0101", "D0102"} and "D01" in self.by_id:
            found = dict(self.by_id["D01"])
            found["unit"] = "percent"
            found["canonical_name"] = "attack"
            found["display_name"] = "Weapon DMG"
            canonical_id = "D01"
            rule = "proven_weapon_attack_ratio_affix"

        if not found:
            prototype = self.affix_prototypes.get(raw) if isinstance(self.affix_prototypes, dict) else None
            if isinstance(prototype, dict):
                proto_attr_id = str(prototype.get("attr_id") or "")
                if proto_attr_id in self.by_id:
                    found = dict(self.by_id[proto_attr_id])
                    proto_type = prototype.get("type")
                    if proto_type == 2:
                        found["unit"] = "percent"
                    elif proto_type == 1:
                        found["unit"] = "flat"
                    proto_name = translated(self.translate, prototype.get("affix_name"))
                    if proto_name:
                        found["display_name"] = proto_name
                    canonical_id = proto_attr_id
                    rule = "affix_prototype_attr_id"

        if not found:
            match = re.fullmatch(r"([A-Z][0-9]{2})00", raw)
            # This convention is accepted only if the exact canonical prefix is
            # present in char_property_data.  It is not blind truncation.
            if match and match.group(1) in self.by_id:
                canonical_id = match.group(1)
                found = self.by_id[canonical_id]
                rule = "validated_affix_zero_suffix"
        if not found:
            self.unresolved[(raw, context)] += 1
            return {
                "raw_stat_id": raw, "stat_id": None, "resolution_status": "unresolved",
                "context": context,
            }
        return {
            "raw_stat_id": raw, **found, "stat_id": canonical_id,
            "encoding_rule": rule, "resolution_status": "resolved",
        }

    def modifier(self, raw_stat_id, raw_value, value_type=None, context="") -> dict:
        stat = self.resolve(raw_stat_id, context)
        numeric = number(raw_value)
        is_percent = stat.get("unit") == "percent"
        return {
            "type": "stat_modifier",
            **stat,
            "operation": "add_percent" if is_percent else "add_flat",
            "value": numeric * 100 if is_percent and isinstance(numeric, (int, float)) else numeric,
            "raw_value": numeric,
            "value_type": value_type,
        }


class ModApplicabilityResolver:
    """Resolve mod compatibility from mod_apply_range_data itself."""

    def __init__(self, corpus: TableCorpus, translate: Translator):
        self.rows = corpus.merged(f"{GAME_DATA}/mod_apply_range_data.json")
        self.translate = translate
        self.unresolved = Counter()
        self.weapon_names = {}
        self.armor_names = {}
        for code, row in self.rows.items():
            values = [as_int(value) for value in row.get("apply_list", [])]
            if len(values) != 1:
                continue
            label = translated(translate, row.get("desc"))
            if as_int(row.get("apply_type")) == 1:
                self.weapon_names[values[0]] = label
            elif as_int(row.get("apply_type")) == 2:
                self.armor_names[values[0]] = label

    def resolve(self, code: object) -> dict:
        text = str(code)
        row = self.rows.get(text)
        if not row:
            self.unresolved[text] += 1
            return {
                "apply_range_code": as_int(code), "resolution_status": "unresolved",
                "category": None, "weapon_classes": [], "armor_slots": [],
                "compatibility_rules": [],
            }
        apply_type = as_int(row.get("apply_type"))
        values = [as_int(value) for value in row.get("apply_list", [])]
        category = {1: "weapon", 2: "armor", 3: "specific_equipment"}.get(apply_type, "unknown")
        weapon_classes = [
            {"class_code": value, "name": self.weapon_names.get(value) or WEAPON_CLASSES.get(value, "")}
            for value in values if apply_type == 1
        ]
        armor_slots = [
            {"slot_code": value, "name": self.armor_names.get(value, "")}
            for value in values if apply_type == 2
        ]
        return {
            "apply_range_code": as_int(code), "resolution_status": "resolved",
            "category": category,
            "equipment_slot": armor_slots[0]["name"] if len(armor_slots) == 1 else None,
            "weapon_classes": weapon_classes, "armor_slots": armor_slots,
            "compatibility_rules": [{
                "apply_type": apply_type, "mod_type": as_int(row.get("mod_type")),
                "allowed_codes": values, "description": translated(self.translate, row.get("desc")),
                "unfit_message": translated(self.translate, row.get("unfit_tips")),
            }],
            "source": {"table": f"{GAME_DATA}/mod_apply_range_data.json", "record_id": text},
        }


class BuffLogicResolver:
    """Resolve buff metadata, dynamic tree parameters, nodes, and conditions."""

    PASSTHROUGH = {
        "NodeBuffNone", "NodeGetHolderUid", "NodeGetCasterID", "NodeGetCasterPos",
        "NodeGetTargetPos", "NodeGetTargetInfo", "NodeGetTargetFloatAttr", "NodeGetFloatAttr",
        "NodeGetIntAttr", "NodeConstFloat", "NodeConstInt", "NodeConstVector",
        "NodeBBFloatCalculation", "NodeBBVectorCalculation", "NodeBBSaveIntData",
        "NodeBBSaveFloatData", "NodeBBSaveVectorData", "NodeBBLoadIntData",
        "NodeBBLoadFloatData", "NodeBBLoadVectorData", "NodeBBChangeIntData",
        "NodeCompareInt", "NodeCompareFloat", "NodeIntToFloat", "NodeBreakHitInfo",
        "NodeUnpackParams", "NodeSaveTargetSnapshot", "NodeGetTargetSnapshot",
        "NodeGetSnapshotProperty", "NodeBuffIfTask", "NodeBuffRandomTask",
        "NodeForeachIdList", "NodeTagEventListener", "NodeAttackEvent", "NodeBeHitEvent",
        "NodeKillEvent", "NodeMaterial", "NodeGetAoiEntity", "NodeCalculateOffsetPos",
        "NodeCreateSfx", "NodePlaySoundEvent", "NodeShowMechanismTip", "NodeCastBehavior",
    }

    def __init__(self, corpus: TableCorpus, stat_resolver: StatResolver):
        self.corpus = corpus
        self.stats = stat_resolver
        self.level_index = {}
        for key, row in corpus.merged(f"{GAME_DATA}/buff_level_data.json").items():
            key_values = ints(key)
            buff_id = as_int(row.get("buff_template_id") or row.get("buff_id"), key_values[0] if key_values else 0)
            level = as_int(row.get("buff_lv") or row.get("level"), key_values[1] if len(key_values) > 1 else 1)
            self.level_index[(buff_id, level)] = row
        self.definitions, self.definition_sources = corpus.merged_glob(f"{GAME_DATA}/buff/buff_data*.json")
        self.definition_index = {}
        for key, row in self.definitions.items():
            key_values = ints(key)
            params = row.get("buff_params", {})
            buff_id = as_int(params.get("buff_id"), key_values[0] if key_values else 0)
            level = as_int(params.get("buff_level"), key_values[1] if len(key_values) > 1 else 1)
            self.definition_index[(buff_id, level)] = (row, self.definition_sources.get(key, {}))
        self.unknown_nodes = Counter()
        self.unknown_examples = defaultdict(list)
        self.missing_buff_references = Counter()
        self.missing_logic_references = Counter()

    @staticmethod
    def _set_path(root: dict, path: list, value) -> bool:
        current = root
        try:
            for component in path[:-1]:
                current = current[int(component)] if isinstance(current, list) else current[str(component)]
            last = path[-1]
            if isinstance(current, list):
                current[int(last)] = value
            else:
                current[str(last)] = value
            return True
        except (KeyError, IndexError, TypeError, ValueError):
            return False

    def _apply_dynamic_params(self, tree: dict, level_record: dict) -> list:
        applied = []
        parameters = level_record.get("params", {})
        dynamic = tree.get("tree_info", {}).get("dynamic_params", {})
        for node_id, bindings in dynamic.items():
            node = tree.get("node_list", {}).get(str(node_id))
            if not node:
                continue
            for binding in bindings:
                if not isinstance(binding, list) or len(binding) != 2:
                    continue
                path, parameter_index = binding
                raw = parameters.get(str(as_int(parameter_index) + 1))
                if raw is None:
                    continue
                parsed = number(raw)
                if self._set_path(node, path, parsed):
                    applied.append({"node_id": str(node_id), "path": path, "parameter": as_int(parameter_index) + 1, "value": parsed})
        return applied

    @staticmethod
    def _operator(value) -> str:
        return {0: "equal", 1: "below_or_equal", 2: "above", 3: "not_equal", 4: "at_least"}.get(as_int(value), f"op_{value}")

    def _checker(self, checker: dict) -> dict:
        checker_type = str(checker.get("type") or "unknown_checker")
        params = checker.get("params", {})
        if checker_type == "bb_data_checker":
            key = str(params.get("key") or params.get("attribute") or "")
            return {
                "type": "magazine_fraction" if key == "bullet_rate" else "blackboard_threshold",
                "attribute": params.get("attribute"), "key": key,
                "operator": self._operator(params.get("op")), "value": params.get("value"),
                "scope": params.get("scope"), "raw_checker": checker,
            }
        if checker_type == "define_property_value_checker":
            return {
                "type": "property_threshold", "property": params.get("check_property"),
                "operator": self._operator(params.get("op")), "value": params.get("value"),
                "raw_checker": checker,
            }
        if checker_type == "enter_state_checker":
            return {
                "type": "state_transition", "state_id": params.get("state"),
                "entering": params.get("enter_state"), "role": params.get("role"),
                "raw_checker": checker,
            }
        if checker_type == "state_checker":
            return {
                "type": "state_check", "state_id": params.get("state"),
                "in_state": params.get("in_state"), "role": params.get("role"),
                "raw_checker": checker,
            }
        if checker_type == "change_buff_checker":
            return {
                "type": "buff_change", "buff_id": params.get("buff_id"),
                "buff_level": params.get("buff_lv"), "added": params.get("add_buff"),
                "raw_checker": checker,
            }
        normalized = {"type": checker_type, "raw_checker": checker, "resolution_status": "unresolved"}
        for key in ("buff_id", "tag", "keyword", "hp", "crit", "weak", "stack", "value", "op"):
            if key in params:
                normalized[key] = params[key]
        return normalized

    def _source_node(self, node_id: str, node_type: str, node: dict) -> dict:
        return {
            "node_id": str(node_id), "node_type": node_type,
            "raw_node_type": node.get("NodeType"),
            "raw_params": node.get("effect_params", {}).get("params", {}),
            "event_action": node.get("event_action", {}),
            "in_data_pin": node.get("in_data_pin", {}),
            "out_data_pin": node.get("out_data_pin", {}),
        }

    def _decode_node(self, node_id: str, node: dict, lifetime) -> tuple[list, list, list[int]]:
        block = node.get("effect_params", {})
        node_type = str(block.get("type") or f"NodeType:{node.get('NodeType')}")
        params = block.get("params", {})
        source_node = self._source_node(node_id, node_type, node)
        effects, conditions, buff_refs = [], [], []
        if node_type == "NodeChangeAttr":
            for change in params.get("change_attr", []):
                if not isinstance(change, dict):
                    effects.append({
                        "type": "unresolved_stat_modifier",
                        "resolution_status": "unresolved",
                        "raw_change": copy.deepcopy(change),
                        "source_node": source_node,
                    })
                    continue
                effect = self.stats.modifier(change.get("attribute"), change.get("value"), change.get("value_type"), f"logic:{node_id}")
                effect.update({"duration": lifetime, "extra_value": change.get("extra_value"), "source_node": source_node})
                effects.append(effect)
        elif node_type == "NodeChangeAttrInputValue":
            effect = self.stats.modifier(params.get("attribute"), None, params.get("value_type"), f"logic:{node_id}")
            effect.update({"value_expression": node.get("in_data_pin", {}).get("value"), "duration": lifetime, "source_node": source_node})
            effects.append(effect)
        elif node_type == "NodeChecker":
            trigger = [self._checker(item) for item in params.get("trigger_checker", [])]
            reset = [self._checker(item) for item in params.get("reset_checker", [])]
            conditions.append({
                "type": "checker_group", "operator": "all" if as_int(params.get("trigger_op")) == 0 else "any",
                "conditions": trigger, "reset_conditions": reset, "cooldown": params.get("cd"),
                "trigger_once": params.get("trigger_once"), "source_node": source_node,
            })
        elif node_type == "NodeCastBuffToTarget":
            target = as_int(params.get("buff_id"))
            buff_refs.append(target)
            effects.append({
                "type": "buff_application", "buff_id": target, "buff_level": as_int(params.get("buff_lv"), 1),
                "target_rule": node.get("in_data_pin", {}).get("target_id"), "reset": params.get("reset"),
                "source_node": source_node,
            })
        elif node_type == "NodeDispelBuff":
            ids = [as_int(value) for value in params.get("dispel_id_list", [])]
            effects.append({
                "type": "buff_removal", "buff_ids": ids,
                "buff_tags": params.get("dispel_buff_tag_list", []),
                "debuff_count": params.get("dispel_debuff_num"), "source_node": source_node,
            })
        elif node_type in {"NodeAttack", "NodeAttackBox"}:
            effects.append({
                "type": "damage_event", "element_type": params.get("element_type"),
                "formula_attack_type": params.get("formula_attack_type"),
                "is_buff_damage": params.get("is_buff_damage"), "keyword_id": params.get("keyword"),
                "keyword_tag": params.get("keyword_tag"), "source_node": source_node,
            })
        elif node_type == "NodeHeal":
            effects.append({"type": "healing_event", "healing_rate": params.get("cure_add_rate"), "source_node": source_node})
        elif node_type == "NodeCostAttr":
            for cost in params.get("cost_attr", []):
                effects.append({
                    "type": "resource_change", "resource": cost.get("attribute"),
                    "operation": "subtract", "value": cost.get("value"),
                    "value_type": cost.get("value_type"), "source_node": source_node,
                })
        elif node_type in {"NodeChangeBuffStack", "NodeSetBuffStack"}:
            effects.append({
                "type": "stack_change", "operation_code": params.get("operation"),
                "value_expression": node.get("in_data_pin", {}).get("value"), "source_node": source_node,
            })
        elif node_type == "NodeBuffProbabilityTask":
            conditions.append({
                "type": "proc_chance", "value": params.get("probability"),
                "uses_input": params.get("use_input"), "input_factor": params.get("input_factor"),
                "source_node": source_node,
            })
        elif node_type == "NodeBuffDelayTask":
            conditions.append({"type": "delay", "seconds": params.get("delay_time"), "source_node": source_node})
        elif node_type == "NodeBuffLoopTask":
            conditions.append({
                "type": "timing", "tick_interval": params.get("loop_time"),
                "maximum_ticks": params.get("loop_max_times"), "source_node": source_node,
            })
        elif node_type == "NodeBuffCheckerTask":
            conditions.append({
                "type": "checker_group",
                "operator": "all" if as_int(params.get("condition_op")) == 0 else "any",
                "conditions": [self._checker(item) for item in params.get("condition", [])],
                "target_rule": node.get("in_data_pin", {}).get("target_id"),
                "source_node": source_node,
            })
        elif node_type in {"NodeGetBuffStack", "NodeGetBuffRate", "NodeGetTargetBuffStack"}:
            referenced = as_int(params.get("buff_id"))
            if referenced:
                buff_refs.append(referenced)
            effects.append({
                "type": "logic_value_read",
                "operation": {
                    "NodeGetBuffStack": "read_buff_stack",
                    "NodeGetBuffRate": "read_buff_rate",
                    "NodeGetTargetBuffStack": "read_target_buff_stack",
                }[node_type],
                "buff_id": referenced or None,
                "buff_level": params.get("buff_lv"),
                "buff_owner": params.get("buff_owner"),
                "target_rule": node.get("in_data_pin", {}).get("target_id"),
                "output": node.get("out_data_pin", {}),
                "source_node": source_node,
            })
        elif node_type == "NodeRelateAttrChange":
            target = self.stats.modifier(
                params.get("tar_attr"), params.get("tar_standard_value"),
                params.get("tar_check_type"), f"logic:{node_id}",
            )
            target.update({
                "type": "related_stat_modifier",
                "operation": "scale_from_source_stat",
                "source_stat": self.stats.resolve(params.get("src_attr"), f"logic:{node_id}:source"),
                "source_standard_value": params.get("src_standard_value"),
                "source_check_type": params.get("src_check_type"),
                "source_type_code": params.get("src_type"),
                "maximum_value": (
                    number(params.get("tar_value_restriction")) * 100
                    if target.get("unit") == "percent" and isinstance(number(params.get("tar_value_restriction")), (int, float))
                    else number(params.get("tar_value_restriction"))
                ),
                "raw_maximum_value": number(params.get("tar_value_restriction")),
                "target_check_type": params.get("tar_check_type"),
                "source_node": source_node,
            })
            effects.append(target)
        elif node_type == "NodeLoopCheckerCostAttrInputValue":
            effects.append({
                "type": "resource_change", "resource": params.get("attribute"),
                "operation": "subtract", "value_expression": node.get("in_data_pin", {}).get("value"),
                "value_type": params.get("value_type"), "source_node": source_node,
            })
            conditions.extend([
                {
                    "type": "checker_group",
                    "operator": "all" if as_int(params.get("condition_op")) == 0 else "any",
                    "conditions": [self._checker(item) for item in params.get("condition", [])],
                    "source_node": source_node,
                },
                {
                    "type": "timing", "tick_interval": params.get("loop_time"),
                    "maximum_ticks": params.get("loop_max_times"), "source_node": source_node,
                },
            ])
        elif node_type == "NodeAddAmmunition":
            effects.append({
                "type": "resource_change", "resource": "ammunition",
                "operation": "add", "value": params.get("value"),
                "value_type": params.get("value_type"),
                "value_expression": node.get("in_data_pin", {}).get("value"),
                "weapon_rule": node.get("in_data_pin", {}).get("gun_id"),
                "ignore_magazine_limit": params.get("ignore_magazine_limit"),
                "source_node": source_node,
            })
        elif node_type == "NodeDistanceDamage":
            effect = self.stats.modifier(
                params.get("attribute"), params.get("value"),
                params.get("value_type"), f"logic:{node_id}",
            )
            raw_increase = number(params.get("increase"))
            effect.update({
                "type": "distance_scaled_stat_modifier",
                "per_interval_value": (
                    raw_increase * 100
                    if effect.get("unit") == "percent" and isinstance(raw_increase, (int, float))
                    else raw_increase
                ),
                "raw_per_interval_value": raw_increase,
                "distance_start": params.get("distance"), "distance_maximum": params.get("max_distance"),
                "distance_interval": params.get("interval"), "maximum_steps": params.get("max_times"),
                "operation_code": params.get("op"), "times_type_code": params.get("times_type"),
                "source_node": source_node,
            })
            effects.append(effect)
            if params.get("trigger_checker"):
                conditions.append({
                    "type": "checker_group",
                    "operator": "all" if as_int(params.get("trigger_op")) == 0 else "any",
                    "conditions": [self._checker(item) for item in params.get("trigger_checker", [])],
                    "source_node": source_node,
                })
        elif node_type == "NodeSetBuffMaxStack":
            effects.append({
                "type": "stack_rule", "operation": "set_maximum_stacks",
                "value_expression": node.get("in_data_pin", {}).get("data"),
                "source_node": source_node,
            })
        elif node_type == "NodeCostAttrInputValue":
            effects.append({
                "type": "resource_change", "resource": params.get("attribute"),
                "operation": "subtract", "value_expression": node.get("in_data_pin", {}).get("value"),
                "value_type": params.get("value_type"), "percent_base_code": params.get("percent_base"),
                "source_node": source_node,
            })
        elif node_type == "NodeReduceBehaviorCD":
            effects.append({
                "type": "cooldown_change",
                "operation": "set" if params.get("set_to") else "reduce",
                "behavior_name": params.get("behavior_name"), "value": params.get("reduce_value"),
                "value_type_code": params.get("reduce_type"), "target_range_code": params.get("reduce_range"),
                "source_node": source_node,
            })
        elif node_type == "NodeChangeDeviationMonsterCaptureRate":
            effects.append({
                "type": "capture_rate_modifier", "deviation_item_id": params.get("deviation_item_no"),
                "value": params.get("extra_value"), "skin_deviation": params.get("skin_deviation"),
                "level_expression": node.get("in_data_pin", {}).get("extra_level"),
                "source_node": source_node,
            })
        elif node_type in {"NodeGetFoodHunterEffect", "NodeSetFoodHunterEffect"}:
            effects.append({
                "type": "logic_value_read" if node_type == "NodeGetFoodHunterEffect" else "food_effect_change",
                "operation": "read_food_effect" if node_type == "NodeGetFoodHunterEffect" else "set_food_effect",
                "food_effect_attribute": params.get("attribute"),
                "value_expression": node.get("in_data_pin", {}).get("value"),
                "output": node.get("out_data_pin", {}), "source_node": source_node,
            })
        elif node_type == "NodeCommonAddItem":
            effects.append({
                "type": "item_grant", "item_id": params.get("item_no"),
                "quantity": params.get("item_num"), "quantity_expression": node.get("in_data_pin", {}).get("item_num"),
                "is_currency": params.get("is_money_type"), "show_notification": params.get("show_toast"),
                "source_node": source_node,
            })
        elif node_type in {"NodeChangeItemDurInc", "NodeChangeItemWeight"}:
            effects.append({
                "type": "item_durability_modifier" if node_type == "NodeChangeItemDurInc" else "item_weight_modifier",
                "item_id": params.get("item_no"), "operation": "add_rate",
                "value": params.get("change_rate"), "source_node": source_node,
            })
        elif node_type in {"NodeLimitAttr", "NodeChangeHitBoxDamRate"}:
            effects.append({"type": "attribute_rule", "parameters": copy.deepcopy(params), "source_node": source_node})
        elif node_type not in self.PASSTHROUGH:
            self.unknown_nodes[node_type] += 1
        return effects, conditions, buff_refs

    @staticmethod
    def _event_targets(node: dict) -> set[str]:
        result = set()
        for value in node.get("event_action", {}).values():
            if isinstance(value, list):
                for target in value:
                    if isinstance(target, (int, str)):
                        result.add(str(target))
        return result

    def resolve(self, buff_id: int, level: int, level_record: dict, depth=0) -> dict:
        definition_pair = self.definition_index.get((buff_id, level)) or self.definition_index.get((buff_id, 1))
        if not definition_pair:
            self.missing_buff_references[(buff_id, level)] += 1
            return {
                "buff_id": buff_id, "buff_level": level, "resolution_status": "unresolved",
                "logic_tree_ref": None, "resolved_effects": [], "resolved_conditions": [],
                "unresolved_nodes": [], "definition_source": None,
            }
        definition, definition_source = definition_pair
        # Presentation-first normalized rows do not carry the raw per-level
        # parameter map. Resolve it from the existing table corpus so dynamic
        # logic-tree bindings use the real value for each buff level.
        raw_level_record = self.level_index.get((buff_id, level))
        if raw_level_record is None and level != 1:
            raw_level_record = self.level_index.get((buff_id, 1))
        if raw_level_record is None:
            # Last-resort compatibility fallback: never attach the mutable
            # normalized parent row itself as raw_level_definition.  The
            # resolver enriches that row in-place later, which would create
            # row["raw_level_definition"] is row and break JSON serialization.
            raw_level_record = copy.deepcopy(level_record)
        metadata = definition.get("buff_params", {})
        references = [str(value) for value in definition.get("logic_tree_data", []) if value]
        all_effects, all_conditions, unresolved, referenced_buffs, trees = [], [], [], set(), []
        lifetime = metadata.get("life_time")
        for reference in references:
            raw_tree, source = self.corpus.logic_tree(reference)
            if not raw_tree:
                self.missing_logic_references[(buff_id, level, reference)] += 1
                unresolved.append({"node_type": "missing_logic_tree", "logic_tree_ref": reference, "source": source})
                continue
            tree = copy.deepcopy(raw_tree)
            applied = self._apply_dynamic_params(tree, raw_level_record)
            node_conditions = {}
            node_effects = {}
            before_unknown = self.unknown_nodes.copy()
            for node_id, node in tree.get("node_list", {}).items():
                effects, conditions, buff_refs = self._decode_node(str(node_id), node, lifetime)
                if effects:
                    node_effects[str(node_id)] = effects
                if conditions:
                    node_conditions[str(node_id)] = conditions
                referenced_buffs.update(value for value in buff_refs if value)
                node_type = str(node.get("effect_params", {}).get("type") or f"NodeType:{node.get('NodeType')}")
                if node_type not in self.PASSTHROUGH and not effects and not conditions:
                    if self.unknown_nodes[node_type] > before_unknown[node_type]:
                        raw_unknown = {
                            "node_type": node_type, "node_id": str(node_id),
                            "raw_node": copy.deepcopy(node), "source": source,
                        }
                        unresolved.append(raw_unknown)
                        if len(self.unknown_examples[node_type]) < 5:
                            self.unknown_examples[node_type].append({
                                "buff_id": buff_id, "buff_level": level,
                                "logic_tree_ref": reference, "node_id": str(node_id),
                                "source": source, "raw_node": copy.deepcopy(node),
                            })
            for condition_node, condition_values in node_conditions.items():
                targets = self._event_targets(tree.get("node_list", {}).get(condition_node, {}))
                attached = False
                for target in targets:
                    for effect in node_effects.get(target, []):
                        effect.setdefault("conditions", []).extend(copy.deepcopy(condition_values))
                        attached = True
                if not attached:
                    all_conditions.extend(condition_values)
            for effects in node_effects.values():
                all_effects.extend(effects)
            trees.append({
                "reference": reference, "source": source,
                "entry_node": tree.get("tree_info", {}).get("entry_node"),
                "dynamic_parameters_applied": applied,
                "node_count": len(tree.get("node_list", {})),
            })
        if all_effects and not unresolved:
            status = "resolved"
        elif all_effects or all_conditions or trees:
            status = "partial"
        else:
            status = "unresolved"
        nested = []
        if depth < 1:
            for target_id in sorted(referenced_buffs)[:25]:
                target_pair = self.definition_index.get((target_id, 1))
                nested.append({
                    "buff_id": target_id,
                    "definition_found": bool(target_pair),
                    "logic_tree_refs": target_pair[0].get("logic_tree_data", []) if target_pair else [],
                })
        return {
            "buff_id": buff_id, "buff_level": level,
            "lifetime": lifetime, "maximum_stacks": metadata.get("buff_max_stack"),
            "tags": metadata.get("buff_tag", []), "sub_tags": metadata.get("buff_sub_tags", []),
            "valid_targets": metadata.get("effect_unit_type", []), "priority": metadata.get("priority"),
            "unique_tag": metadata.get("unique_tag"), "refresh_rule": metadata.get("refresh_rule"),
            "refresh_buff_stack": metadata.get("refresh_buff_stack"), "degrade_time": metadata.get("degrade_time"),
            "degrade_stack": metadata.get("degrade_stack"), "logic_tree_ref": references[0] if len(references) == 1 else references,
            "logic_tree": trees, "resolved_effects": all_effects,
            "resolved_conditions": all_conditions, "referenced_buffs": nested,
            "unresolved_nodes": unresolved, "resolution_status": status,
            "definition_source": definition_source,
            "raw_definition": definition,
            "raw_level_definition": raw_level_record,
        }


class RelationshipBuilder:
    def __init__(self):
        self._records = {}

    def add(self, source_type, source_id, relation, target_type, target_id, source=None, unresolved=False):
        if target_id in (None, "", 0, "0"):
            return
        key = (str(source_type), str(source_id), str(relation), str(target_type), str(target_id))
        self._records[key] = {
            "source_type": key[0], "source_id": key[1], "relation": key[2],
            "target_type": key[3], "target_id": key[4],
            "resolution_status": "unresolved" if unresolved else "resolved",
            "source": source,
        }

    def records(self) -> list:
        return [self._records[key] for key in sorted(self._records)]


class CombatPipeline:
    def __init__(self, base: Path, current: Path, published: Path):
        self.corpus = TableCorpus(base, current)
        self.published = published
        self.data_dir = published / "data"
        self.reports = published / "reports"
        translations = {}
        base_translation = base / "translate/translate_data_en.json"
        if base_translation.exists():
            translations.update(translation_entries(base_translation))
        for path in sorted((current / "translate").glob("translate_data_en*.json")):
            translations.update(translation_entries(path))
        self.translate = Translator(translations)
        self.stats = StatResolver(self.corpus, self.translate)
        self.applicability = ModApplicabilityResolver(self.corpus, self.translate)
        self.buffs = BuffLogicResolver(self.corpus, self.stats)
        self.relationships = RelationshipBuilder()

    def _payload(self, name: str) -> dict:
        return read_json(self.data_dir / name, {})

    def resolve_stats_file(self) -> None:
        payload = self._payload("stat-definitions.json")
        for row in payload.get("stat_definitions", []):
            resolved = self.stats.resolve(row.get("id") or row.get("key"), "stat-definition")
            row.update({
                "canonical_name": resolved.get("canonical_name"),
                "unit": resolved.get("unit"),
                "resolution_status": resolved.get("resolution_status"),
            })
        payload["encoding_rules"] = [{
            "name": "calibration_affix_zero_suffix",
            "pattern": "<canonical stat id> + 00",
            "validation": "Applied only when the unmodified prefix exists in char_property_data",
            "examples": ["E0300 -> E03", "E3200 -> E32", "E3300 -> E33", "E3400 -> E34", "E3800 -> E38"],
        }]
        write_json(self.data_dir / "stat-definitions.json", payload)

    def resolve_buff_file(self) -> dict:
        payload = self._payload("buffs.json")
        status_counts = Counter()
        definition_records = []
        for (buff_id, level), (definition, source) in sorted(self.buffs.definition_index.items()):
            params = definition.get("buff_params", {})
            definition_records.append({
                "id": f"{buff_id}:{level}", "buff_id": buff_id, "buff_level": level,
                "lifetime": params.get("life_time"), "maximum_stacks": params.get("buff_max_stack"),
                "tags": params.get("buff_tag", []), "sub_tags": params.get("buff_sub_tags", []),
                "valid_targets": params.get("effect_unit_type", []), "priority": params.get("priority"),
                "unique_tag": params.get("unique_tag"), "refresh_rule": params.get("refresh_rule"),
                "degrade_time": params.get("degrade_time"), "logic_tree_ref": definition.get("logic_tree_data", []),
                "source": source, "raw_definition": definition,
            })
        for row in payload.get("buffs", []):
            resolved = self.buffs.resolve(as_int(row.get("buff_id")), as_int(row.get("level"), 1), row)
            for field in (
                "lifetime", "maximum_stacks", "tags", "sub_tags", "valid_targets", "priority",
                "unique_tag", "refresh_rule", "refresh_buff_stack", "degrade_time", "degrade_stack",
                "logic_tree_ref", "logic_tree", "resolved_effects", "resolved_conditions",
                "referenced_buffs", "unresolved_nodes", "resolution_status", "definition_source",
            ):
                row[field] = resolved.get(field)
            row["raw_game_definition"] = resolved.get("raw_definition")
            row["raw_level_definition"] = resolved.get("raw_level_definition")
            status_counts[row["resolution_status"]] += 1
            source_id = f"{row.get('buff_id')}:{row.get('level')}"
            for effect in row.get("resolved_effects", []):
                if effect.get("type") == "stat_modifier" and effect.get("stat_id"):
                    self.relationships.add("buff", source_id, "modifies_stat", "stat", effect["stat_id"], effect.get("source_node"))
                elif effect.get("type") == "buff_application":
                    self.relationships.add("buff", source_id, "applies_buff", "buff", effect.get("buff_id"), effect.get("source_node"))
            for status_id in [*(row.get("tags") or []), *(row.get("sub_tags") or [])]:
                self.relationships.add("buff", source_id, "applies_status", "status", status_id, row.get("definition_source"))
        payload["buff_definitions"] = definition_records
        payload["record_counts"]["buff_definitions"] = len(definition_records)
        payload["record_counts"]["resolution_status"] = dict(status_counts)
        write_json(self.data_dir / "buffs.json", payload)
        return dict(status_counts)

    def resolve_mods(self) -> dict:
        payload = self._payload("mods.json")
        buff_payload = self._payload("buffs.json")
        buff_levels_by_id = defaultdict(list)
        for buff_row in buff_payload.get("buffs", []):
            buff_levels_by_id[as_int(buff_row.get("buff_id"))].append(buff_row)
        entries = self.corpus.merged(f"{GAME_DATA}/mod_entry_data.json")
        grouped = defaultdict(list)
        for key, row in entries.items():
            parts = ints(key)
            if parts:
                grouped[parts[0]].append((parts[1] if len(parts) > 1 else 0, row, str(key)))
        resolved_mods = 0
        applicability_codes = set()
        for mod in payload.get("mods", []):
            applicability = self.applicability.resolve(mod.get("apply_range_code"))
            mod["resolved_applicability"] = applicability
            if applicability.get("resolution_status") == "resolved":
                applicability_codes.add(as_int(mod.get("apply_range_code")))
            resolved_effects = []
            secondary_entries = []
            for level, entry, record_id in sorted(grouped.get(as_int(mod.get("main_entry_code")), [])):
                entry_effects = []
                for stat_id, value in zip(entry.get("attr_no_list", []), entry.get("attr_value_list", [])):
                    entry_effects.append(self.stats.modifier(stat_id, value, context=f"mod:{mod.get('mod_code')}:{level}"))
                buff_id = as_int(entry.get("buff_id"))
                if buff_id:
                    buff_levels = buff_levels_by_id.get(buff_id, [])
                    matching_levels = [row for row in buff_levels if as_int(row.get("level")) == level]
                    selected_levels = matching_levels or (buff_levels[:1] if len(buff_levels) == 1 else [])
                    entry_effects.append({
                        "type": "buff_application", "buff_id": buff_id, "entry_level": level,
                        "available_buff_levels": sorted(as_int(row.get("level")) for row in buff_levels),
                        "buff_resolution": [
                            {"level": row.get("level"), "resolution_status": row.get("resolution_status"),
                             "logic_tree_ref": row.get("logic_tree_ref"), "resolved_effects": row.get("resolved_effects", [])}
                            for row in selected_levels
                        ],
                    })
                    self.relationships.add("mod", mod.get("mod_code"), "applies_buff", "buff", buff_id, {"table": f"{GAME_DATA}/mod_entry_data.json", "record_id": record_id})
                    for buff_row in buff_levels:
                        for status_id in [*(buff_row.get("tags") or []), *(buff_row.get("sub_tags") or [])]:
                            self.relationships.add("mod", mod.get("mod_code"), "interacts_with_status", "status", status_id, {"table": f"{GAME_DATA}/mod_entry_data.json", "record_id": record_id})
                for effect in entry_effects:
                    if effect.get("type") == "stat_modifier" and effect.get("stat_id"):
                        self.relationships.add("mod", mod.get("mod_code"), "modifies_stat", "stat", effect["stat_id"], {"table": f"{GAME_DATA}/mod_entry_data.json", "record_id": record_id})
                resolved_effects.append({
                    "entry_code": as_int(mod.get("main_entry_code")), "entry_level": level,
                    "effects": entry_effects, "description": translated(self.translate, entry.get("desc"), entry.get("desc_replace")),
                    "source": {"table": f"{GAME_DATA}/mod_entry_data.json", "record_id": record_id},
                })
            mod["secondary_entries"] = secondary_entries
            mod["resolved_effects"] = resolved_effects
            mod["resolution_status"] = "resolved" if resolved_effects and all(item["effects"] for item in resolved_effects) else ("partial" if resolved_effects else "unresolved")
            if any(item["effects"] for item in resolved_effects):
                resolved_mods += 1
        payload["record_counts"]["mods_with_resolved_effects"] = resolved_mods
        payload["record_counts"]["resolved_applicability_codes"] = len(applicability_codes)
        write_json(self.data_dir / "mods.json", payload)
        return {"mods_with_resolved_effects": resolved_mods, "applicability_codes": len(applicability_codes)}

    def resolve_calibrations(self) -> dict:
        payload = self._payload("calibrations.json")
        resolved_stat_references = 0
        resolved_affix_records = 0
        class_names = self._weapon_class_names()
        buff_rows = self._payload("buffs.json").get("buffs", [])
        calibration_affix_option_data = self.corpus.merged(f"{GAME_DATA}/gun_calibration_affix_option_data.json")
        gun_blueprint_terms_pool = self.corpus.merged(f"{GAME_DATA}/gun_blueprint_terms_pool.json")

        # Preserve the raw calibration global parameters when present. The client
        # helper get_gun_calibration_affix_option_size() reads calibration_option_gun
        # from DataMgr.common_data/global_params_data, but older published datasets
        # did not retain that table.
        global_calibration_params = {}
        wanted_global_keys = {"calibration_option_gun", "calibration_style_gun"}

        def collect_named_keys(value, provenance, path=""):
            if isinstance(value, dict):
                for key, child in value.items():
                    child_path = f"{path}/{key}" if path else str(key)
                    if key in wanted_global_keys:
                        global_calibration_params[key] = {
                            "value": child,
                            "source": provenance,
                            "json_path": child_path,
                        }
                    collect_named_keys(child, provenance, child_path)
            elif isinstance(value, list):
                for idx, child in enumerate(value):
                    collect_named_keys(child, provenance, f"{path}/{idx}")

        for layer, root in (("base", self.corpus.base), ("current", self.corpus.current)):
            seen = set()
            for pattern in ("**/*global*param*.json", "**/global_params_data.json"):
                for path in root.glob(pattern):
                    if path in seen or not path.is_file():
                        continue
                    seen.add(path)
                    raw_global = read_json(path, {})
                    collect_named_keys(
                        raw_global,
                        {"layer": layer, "table": path.relative_to(root).as_posix()},
                    )

        calibration_attack_term_rows = []
        for term_no, term in sorted(gun_blueprint_terms_pool.items(), key=lambda row: str(row[0])):
            if str(term.get("affix_id") or "") != "D0102":
                continue
            calibration_attack_term_rows.append({
                "term_no": str(term_no),
                "affix_id": "D0102",
                "affix_step": term.get("affix_step", []),
            })

        buff_index = {
            (as_int(row.get("buff_id")), as_int(row.get("level"), 1)): row
            for row in buff_rows
        }
        range_distribution = Counter()
        current_range_rows = []
        current_style_rows = []
        for calibration in payload.get("calibrations", []):
            calibration["status"] = "current" if calibration.get("is_valid") else "legacy"
            calibration["calibration_family"] = {
                "style_code": calibration.get("calibration_style_code"),
                "group_id": calibration.get("group_id"),
            }
            raw_range = calibration.get("affix_val_range") or []
            if len(raw_range) >= 2:
                low, high = number(raw_range[0]), number(raw_range[1])
                if isinstance(low, (int, float)) and isinstance(high, (int, float)):
                    calibration["calibration_roll_range"] = {
                        "raw_minimum": low, "raw_maximum": high,
                        "minimum_percent": low * 100, "maximum_percent": high * 100,
                        "source_table": f"{GAME_DATA}/gun_correct_print_data.json",
                        "source_field": "affix_val_range",
                        "semantics_status": "range-and-drop-generation-proven-attack-ratio-application-traced",
                    }
                    if calibration.get("status") == "current":
                        range_distribution[(calibration.get("quality"), low, high)] += 1
                        current_range_rows.append({
                            "calibration_id": calibration.get("id"),
                            "name": calibration.get("name"),
                            "rarity": calibration.get("quality"),
                            "raw_range": [low, high],
                            "percent_range": [low * 100, high * 100],
                            "affix_ids": calibration.get("affix_ids", []),
                            "affix_ids_weight": calibration.get("affix_ids_weight", []),
                            "buff_id": calibration.get("buff_id"),
                        })
            buff_ref = calibration.get("buff_id") or []
            if isinstance(buff_ref, (list, tuple)) and len(buff_ref) >= 2:
                style_buff = buff_index.get((as_int(buff_ref[0]), as_int(buff_ref[1], 1)))
                if style_buff:
                    raw_level = style_buff.get("raw_level_definition") or {}
                    style_name = style_buff.get("name") or translated(
                        self.translate,
                        raw_level.get("name") or raw_level.get("buff_name"),
                        raw_level.get("name_replace") or raw_level.get("name_value"),
                    )
                    style_description = style_buff.get("description") or translated(
                        self.translate,
                        raw_level.get("desc") or raw_level.get("description") or raw_level.get("buff_desc"),
                        raw_level.get("desc_replace") or raw_level.get("desc_value"),
                    )
                    raw_name = Translator.raw(raw_level.get("name") or raw_level.get("buff_name"))
                    raw_description = Translator.raw(raw_level.get("desc") or raw_level.get("description") or raw_level.get("buff_desc"))
                    calibration["style_buff"] = {
                        "buff_id": as_int(buff_ref[0]),
                        "level": as_int(buff_ref[1], 1),
                        "name": style_name,
                        "description": style_description,
                        "raw_name": raw_name,
                        "raw_description": raw_description,
                        "resolved_effects": style_buff.get("resolved_effects", []),
                        "unresolved_nodes": style_buff.get("unresolved_nodes", []),
                        "resolution_status": style_buff.get("resolution_status"),
                        "display_text_status": (
                            "localized-description-resolved" if style_description and style_description != raw_description
                            else "source-description-preserved" if style_description
                            else "description-missing"
                        ),
                        "semantics_note": "Fixed Calibration Style buff. Player-facing text is sourced from buff_level_data and current English localization when available; resolved mechanics remain separate structured evidence.",
                    }
                    if calibration.get("status") == "current":
                        current_style_rows.append({
                            "calibration_id": calibration.get("id"),
                            "name": calibration.get("name"),
                            "rarity": calibration.get("quality"),
                            "buff_id": as_int(buff_ref[0]),
                            "buff_level": as_int(buff_ref[1], 1),
                            "style_name": style_name,
                            "style_description": style_description,
                            "raw_style_name": raw_name,
                            "raw_style_description": raw_description,
                            "display_text_status": calibration["style_buff"]["display_text_status"],
                            "mechanics_resolution_status": style_buff.get("resolution_status"),
                        })
                else:
                    calibration["style_buff"] = None
            else:
                calibration["style_buff"] = None
            calibration["compatible_weapon_classes"] = [
                {"class_code": as_int(code), "name": class_names.get(as_int(code), WEAPON_CLASSES.get(as_int(code), ""))}
                for code in calibration.get("weapon_type_codes", [])
            ]
            normalized_affixes = []
            for affix in calibration.get("affixes", []):
                terms = []
                for term_index, term in enumerate(affix.get("terms", []), start=1):
                    stats = [self.stats.resolve(raw_id, f"calibration:{calibration.get('id')}") for raw_id in term.get("affix_ids", [])]
                    resolved_stat_references += sum(stat.get("resolution_status") == "resolved" for stat in stats)
                    raw_minimum = number(term.get("min_val"))
                    raw_maximum = number(term.get("max_val"))
                    is_percent = bool(stats) and all(stat.get("unit") == "percent" for stat in stats)
                    terms.append({
                        "term_index": term_index, "stats": stats,
                        "minimum_value": raw_minimum * 100 if is_percent and isinstance(raw_minimum, (int, float)) else raw_minimum,
                        "maximum_value": raw_maximum * 100 if is_percent and isinstance(raw_maximum, (int, float)) else raw_maximum,
                        "raw_minimum_value": raw_minimum, "raw_maximum_value": raw_maximum,
                        "unit": "percent" if is_percent else (stats[0].get("unit") if stats else None),
                        "description": translated(self.translate, term.get("affix_desc")),
                        "raw_term": term,
                    })
                    for stat in stats:
                        if stat.get("stat_id"):
                            self.relationships.add("calibration", calibration.get("id"), "modifies_stat", "stat", stat["stat_id"], {"table": f"{GAME_DATA}/gun_correct_common_terms_data.json", "record_id": str(affix.get('affix_id'))})
                affix_status = "resolved" if terms and all(stat.get("resolution_status") == "resolved" for term in terms for stat in term["stats"]) else "partial"
                normalized_affixes.append({
                    "affix_id": affix.get("affix_id"), "terms": terms,
                    "rarity": calibration.get("quality"), "rarity_code": calibration.get("quality_code"),
                    "resolution_status": affix_status,
                })
                resolved_affix_records += affix_status == "resolved"
            calibration["resolved_affixes"] = normalized_affixes
            # Preserve the old first/rest views for compatibility, but expose the
            # actual source structure as a weighted option pool. Current records
            # carry parallel affix_ids + affix_ids_weight arrays; the exact number
            # of selected options is traced through gun_calibration_affix_option_data
            # and client helper functions in this pass.
            calibration["affix_option_pool"] = [
                {
                    **affix_row,
                    "weight": (calibration.get("affix_ids_weight") or [])[idx]
                    if idx < len(calibration.get("affix_ids_weight") or []) else None,
                }
                for idx, affix_row in enumerate(normalized_affixes)
            ]
            calibration["affix_option_pool_status"] = "weighted-drop-term-pool-client-selects-one-term"
            calibration["primary_effect"] = normalized_affixes[0] if normalized_affixes else None
            calibration["secondary_effects"] = normalized_affixes[1:]
            calibration["legacy_effect_view_note"] = "primary_effect/secondary_effects are compatibility views; do not infer that every listed affix is simultaneously active."
            calibration["resolution_status"] = "resolved" if normalized_affixes else "unresolved"
        payload["record_counts"]["resolved_affixes"] = resolved_affix_records
        payload["record_counts"]["resolved_affix_stat_references"] = resolved_stat_references
        payload["record_counts"]["current"] = sum(row.get("status") == "current" for row in payload.get("calibrations", []))
        payload["record_counts"]["legacy"] = sum(row.get("status") == "legacy" for row in payload.get("calibrations", []))
        write_json(self.data_dir / "calibrations.json", payload)
        calibration_option_level_gates = []
        option_param = global_calibration_params.get("calibration_option_gun", {}).get("value")
        if isinstance(option_param, dict):
            option_param = option_param.get("value")
        if isinstance(option_param, list):
            calibration_option_level_gates = [as_int(value) for value in option_param if as_int(value)]

        investigation = {
            "schema_version": 2,
            "generated_utc": utc_now(),
            "source_table": f"{GAME_DATA}/gun_correct_print_data.json",
            "source_field": "affix_val_range",
            "status": "calibration-rng-layers-separated-attack-ratio-consumer-traced",
            "finding": "Current Calibration Blueprint drops contain a rarity-wide gun_correct_affix_val roll from affix_val_range plus one weighted random term selected from affix_ids. Static client tracing separately shows D0102 as an Attack-ratio affix and keeps weapon calibration-level affix_options as a distinct +level system.",
            "current_records_with_range": len(current_range_rows),
            "range_distribution": [
                {
                    "rarity": rarity,
                    "raw_minimum": low,
                    "raw_maximum": high,
                    "minimum_percent": low * 100,
                    "maximum_percent": high * 100,
                    "records": count,
                }
                for (rarity, low, high), count in sorted(range_distribution.items(), key=lambda row: (str(row[0][0]), row[0][1], row[0][2]))
            ],
            "records": current_range_rows,
            "style_localization": {
                "current_records": len(current_style_rows),
                "localized_descriptions": sum(row.get("display_text_status") == "localized-description-resolved" for row in current_style_rows),
                "source_descriptions_preserved": sum(row.get("display_text_status") == "source-description-preserved" for row in current_style_rows),
                "missing_descriptions": sum(row.get("display_text_status") == "description-missing" for row in current_style_rows),
                "named_styles": sum(bool(row.get("style_name")) for row in current_style_rows),
                "records": current_style_rows,
                "source": "game_common/data/buff_level_data.json -> buff_name/buff_desc -> translate/translate_data_en*.json",
                "status": "calibration-style-display-text-bridge-enabled",
            },
            "raw_calibration_affix_option_data": calibration_affix_option_data,
            "affix_option_data_source": f"{GAME_DATA}/gun_calibration_affix_option_data.json",
            "raw_global_calibration_params": global_calibration_params,
            "weapon_calibration_option_level_gates": {
                "levels": calibration_option_level_gates,
                "source": "global_params_data.calibration_option_gun",
                "consumer": "get_gun_calibration_affix_option_size(lv)",
                "status": "level-gate-source-and-consumer-proven",
                "important_note": "These +level option gates are separate from the Calibration Blueprint drop's weighted gun_correct_affix_list term.",
            },
            "rng_layers": {
                "calibration_attack_roll": {
                    "source": "gun_correct_print_data.affix_val_range",
                    "generation": "round(random.uniform(min, max), 3)",
                    "precision": "0.001 raw fraction = 0.1 percentage point",
                    "stored_field": "gun_correct_affix_val",
                    "application_trace": "convert_gun_correct_affix_val_to_affix_list -> generated gun affix list; D0102 is consumed in the Attack-ratio bucket",
                },
                "weighted_drop_term": {
                    "source": "gun_correct_print_data.affix_ids + affix_ids_weight",
                    "selection": "one term_id by cumulative weighted random selection",
                    "materialization": "generate_correct_term_data(term_id) rolls term min_val/max_val to 0.001 raw precision",
                    "stored_field": "gun_correct_affix_list",
                },
                "weapon_level_affix_options": {
                    "source": "item_detail.affix_options + gun_calibration_affix_option_data",
                    "unlock_level_gates": calibration_option_level_gates,
                    "status": "separate-system",
                },
            },
            "calibration_attack_term_pool": {
                "source_table": f"{GAME_DATA}/gun_blueprint_terms_pool.json",
                "affix_id": "D0102",
                "rows": calibration_attack_term_rows,
                "status": "D0102-term-pool-preserved-consumer-semantics-traced-in-pyc-report",
            },
            "next_static_targets": [
                "get_gun_affix_add", "get_gun_calc_affix_add", "get_gun_attack_guncore",
                "get_gun_base_affix_add", "get_gun_correct_affix_add", "get_gun_affix_option_add",
                "get_gun_base_affix_attack", "calc_gun_attr_data", "cal_gun_attr_data_with_item_no",
                "refresh_base_prop", "VM_GUN_FORMULAS",
            ],
        }
        write_json(self.reports / "calibration-investigation.json", investigation)
        return {
            "resolved_affixes": resolved_affix_records,
            "resolved_affix_stat_references": resolved_stat_references,
            "current_records_with_roll_range": len(current_range_rows),
            "roll_range_variants": len(range_distribution),
        }

    def resolve_stats_across_datasets(self) -> dict:
        """Use the same canonical resolver wherever exported records carry stat codes."""
        totals = Counter()

        def annotate(value, context: str):
            if isinstance(value, list):
                for child in value:
                    annotate(child, context)
                return
            if not isinstance(value, dict):
                return
            raw_code = value.get("raw_stat_id") or value.get("stat_id") or value.get("code")
            if isinstance(raw_code, str) and STAT_CODE.fullmatch(raw_code):
                value["resolved_stat"] = self.stats.resolve(raw_code, context)
                totals["resolved" if value["resolved_stat"].get("resolution_status") == "resolved" else "unresolved"] += 1
            codes = value.get("attribute_codes") or value.get("attr_no_list")
            if isinstance(codes, list):
                values = value.get("attribute_values") or value.get("attr_value_list") or []
                # Some Once Human tables (notably gun_accessory_attr_data) encode
                # modifiers directly as [stat_id, value] pairs instead of parallel
                # code/value arrays. Preserve and resolve both representations.
                pair_rows = [
                    pair for pair in codes
                    if isinstance(pair, (list, tuple)) and len(pair) >= 2 and isinstance(pair[0], str)
                ]
                if pair_rows and len(pair_rows) == len(codes):
                    value["resolved_stats"] = [
                        self.stats.modifier(pair[0], pair[1], context=context)
                        for pair in pair_rows
                        if STAT_CODE.fullmatch(pair[0])
                    ]
                else:
                    value["resolved_stats"] = [
                        self.stats.modifier(code, values[index] if index < len(values) else None, context=context)
                        for index, code in enumerate(codes)
                        if isinstance(code, str)
                    ]
                totals["resolved"] += sum(row.get("resolution_status") == "resolved" for row in value["resolved_stats"])
                totals["unresolved"] += sum(row.get("resolution_status") != "resolved" for row in value["resolved_stats"])
            for key, child in list(value.items()):
                if key in {"resolved_stat", "resolved_stats", "source", "game_definition", "raw_definition", "raw_game_definition"}:
                    continue
                if isinstance(child, (dict, list)):
                    annotate(child, context)

        for filename in (
            "weapons.json", "armor-sets.json", "attachments.json", "consumables.json",
            "cradles.json", "progression.json",
        ):
            payload = self._payload(filename)
            annotate(payload, filename)
            write_json(self.data_dir / filename, payload)
        return dict(totals)

    def _weapon_class_names(self) -> dict:
        return {
            as_int(row.get("weapon_type_code")): row.get("category")
            for row in self._payload("weapons.json").get("weapons", [])
            if row.get("weapon_type_code")
        }

    def classify_loadout_data(self) -> dict:
        weapons = self._payload("weapons.json")
        ammo_to_classes = defaultdict(set)
        for weapon in weapons.get("weapons", []):
            ammo_id = as_int((weapon.get("ranged_stats") or {}).get("ammo_item_id"))
            if ammo_id:
                ammo_to_classes[ammo_id].add(weapon.get("category"))
        items = self.corpus.merged(f"{GAME_DATA}/item_data.json")
        ammo = self._payload("ammo.json")
        for row in ammo.get("ammo", []):
            raw = items.get(str(row.get("item_id")), {})
            subtype = as_int(raw.get("sub_type", raw.get("subtype")))
            page = as_int(raw.get("item_belonge_page"))
            tab = as_int(raw.get("item_belonge_tab"))
            classes = sorted(value for value in ammo_to_classes.get(as_int(row.get("item_id")), set()) if value)
            row["compatible_weapon_classes"] = classes
            if classes or (page == 8 and tab == 6):
                row["player_usable"] = True
                row["ammo_category"] = "energy_ammunition" if subtype == 25 else "firearm_ammunition"
            elif subtype in {9, 25}:
                row["player_usable"] = None
                row["ammo_category"] = "unclassified_ammunition"
            else:
                row["player_usable"] = False
                row["ammo_category"] = "npc_or_system_ammunition"
            row["classification_source"] = {"table": f"{GAME_DATA}/item_data.json", "record_id": str(row.get("item_id")), "page": page, "tab": tab, "sub_type": subtype}
        write_json(self.data_dir / "ammo.json", ammo)

        consumables = self._payload("consumables.json")
        for row in consumables.get("consumables", []):
            item_type = str(row.get("item_type") or "").casefold()
            function = str(row.get("use_function") or "").casefold()
            survival = row.get("survival_values", {})
            if "whim" in item_type:
                category = "whim"
            elif "medicine" in item_type:
                category = "medicine"
            elif any("water" in str(key).casefold() for key in survival) and function == "food":
                category = "drink"
            elif function == "food" or "food" in item_type or "cuisine" in item_type:
                category = "food"
            elif "beverage" in item_type:
                category = "drink"
            elif "crate" in item_type or "chest" in item_type:
                category = "crate"
            elif "reward" in item_type or "gift" in item_type:
                category = "reward"
            elif "currency" in item_type or "package" in item_type:
                category = "currency_package"
            elif row.get("buff_effects"):
                category = "combat_consumable"
            elif "event" in item_type:
                category = "event_item"
            else:
                category = "other"
            row["consumable_category"] = category
        write_json(self.data_dir / "consumables.json", consumables)

        deviations = self._payload("deviations.json")
        for row in deviations.get("deviations", []):
            row["player_visible"] = bool(as_int(row.get("id")) and str(row.get("name") or "").strip())
        deviations["player_deviations"] = [row for row in deviations.get("deviations", []) if row["player_visible"]]
        deviations["record_counts"]["player_deviations"] = len(deviations["player_deviations"])
        write_json(self.data_dir / "deviations.json", deviations)
        return {
            "player_ammo": sum(row.get("player_usable") is True for row in ammo.get("ammo", [])),
            "player_deviations": len(deviations["player_deviations"]),
        }

    @staticmethod
    def _recursive_field_values(value, names: set[str]) -> Iterable[tuple[str, object]]:
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).casefold() in names:
                    if isinstance(child, list):
                        for item in child:
                            yield str(key), item
                    else:
                        yield str(key), child
                if isinstance(child, (dict, list)):
                    yield from CombatPipeline._recursive_field_values(child, names)
        elif isinstance(value, list):
            for child in value:
                yield from CombatPipeline._recursive_field_values(child, names)

    def build_relationships(self) -> dict:
        weapons = self._payload("weapons.json")
        for weapon in weapons.get("weapons", []):
            source_id = weapon.get("blueprint_id") or weapon.get("item_id")
            ammo_id = (weapon.get("ranged_stats") or {}).get("ammo_item_id")
            self.relationships.add("weapon", source_id, "uses_ammo", "ammo", ammo_id, {"dataset": "weapons.json"})
            effect = weapon.get("effect") or {}
            self.relationships.add("weapon", source_id, "uses_skill", "skill", effect.get("skill_code"), {"dataset": "weapons.json"})
            self.relationships.add("weapon", source_id, "applies_buff", "buff", effect.get("buff_id"), {"dataset": "weapons.json"})
            self.relationships.add("weapon", source_id, "uses_keyword", "keyword_buff", effect.get("keyword_buff_id"), {"dataset": "weapons.json"})
            self.relationships.add("weapon", source_id, "applies_status", "status", effect.get("keyword_status_id"), {"dataset": "weapons.json"})

        skills = self._payload("skills.json")
        for skill in skills.get("skills", []):
            source_id = skill.get("game_id")
            self.relationships.add("skill", source_id, "applies_buff", "buff", skill.get("buff_id"), {"dataset": "skills.json"})
            self.relationships.add("skill", source_id, "uses_keyword", "keyword_buff", skill.get("keyword_buff_id"), {"dataset": "skills.json"})
            self.relationships.add("skill", source_id, "applies_status", "status", skill.get("keyword_status_id"), {"dataset": "skills.json"})

        for filename, collection, source_type in (
            ("cradles.json", "cradles", "cradle"),
            ("consumables.json", "consumables", "consumable"),
        ):
            payload = self._payload(filename)
            for row in payload.get(collection, []):
                source_id = row.get("id") or row.get("item_id")
                for field, value in self._recursive_field_values(row, {"buff_id", "buff_ids", "buff_list"}):
                    if isinstance(value, (int, str)) and str(value).lstrip("-").isdigit():
                        self.relationships.add(source_type, source_id, "applies_buff", "buff", value, {"dataset": filename, "field": field})

        deviations = self._payload("deviations.json")
        for deviation in deviations.get("deviations", []):
            for skill in deviation.get("skill_catalog", []):
                self.relationships.add("deviation", deviation.get("id"), "uses_skill", "skill", skill.get("id"), {"dataset": "deviations.json"})
        deviation_skill_map = self.corpus.merged(f"{GAME_DATA}/deviation_skill_map_data.json")
        for skill_id, mapping in deviation_skill_map.items():
            for deviation_id in mapping.get("deviation_lst", []):
                self.relationships.add(
                    "deviation", deviation_id, "uses_skill", "skill", skill_id,
                    {"table": f"{GAME_DATA}/deviation_skill_map_data.json", "record_id": str(skill_id)},
                )

        records = self.relationships.records()
        target_ids = {
            "weapon": {str(row.get("blueprint_id") or row.get("item_id")) for row in weapons.get("weapons", [])},
            "ammo": {str(row.get("item_id")) for row in self._payload("ammo.json").get("ammo", [])},
            "skill": {
                str(value)
                for row in skills.get("skills", [])
                for value in (row.get("game_id"), row.get("id")) if value not in (None, "")
            },
            "buff": {str(row.get("buff_id")) for row in self._payload("buffs.json").get("buffs", [])},
            "keyword_buff": {str(row.get("buff_id")) for row in self._payload("keywords.json").get("keywords", [])},
            "status": {str(row.get("id")) for row in self._payload("statuses.json").get("statuses", [])},
            "stat": set(self.stats.by_id),
        }
        unresolved_count = 0
        for relationship in records:
            known = target_ids.get(relationship["target_type"])
            if known is not None and relationship["target_id"] not in known:
                relationship["resolution_status"] = "unresolved"
                relationship["unresolved_reason"] = "Target ID is not present in its normalized master dataset"
                unresolved_count += 1
        payload = {
            "schema_version": 1, "generated_utc": utc_now(),
            "uniqueness_key": ["source_type", "source_id", "relation", "target_type", "target_id"],
            "record_counts": {"relationships": len(records), "unresolved_targets": unresolved_count}, "relationships": records,
        }
        write_json(self.data_dir / "relationships.json", payload)
        return payload["record_counts"]

    def improve_progression(self) -> dict:
        progression = self._payload("progression.json")
        weapons = self._payload("weapons.json")
        armor = self._payload("armor-sets.json")
        calibrations = self._payload("calibrations.json")
        weapon_tiers = [
            {
                "blueprint_id": weapon.get("blueprint_id"), "name": weapon.get("name"),
                "tiers": [{key: tier.get(key) for key in ("tier", "item_id", "gun_no", "damage", "durability", "weight")} for tier in weapon.get("tiers", [])],
                "source": {"dataset": "weapons.json", "source_tables": [f"{GAME_DATA}/gun_blueprint_attr_data.json", f"{GAME_DATA}/gun_base_params_data.json"]},
            }
            for weapon in weapons.get("weapons", [])
        ]
        armor_tiers = []
        for armor_set in armor.get("armor_sets", []):
            for piece in armor_set.get("pieces", []):
                armor_tiers.append({
                    "suit_id": armor_set.get("suit_id"), "blueprint_id": piece.get("blueprint_id"),
                    "name": piece.get("name"), "slot": piece.get("slot"), "tiers": piece.get("tiers", []),
                    "source": {"dataset": "armor-sets.json", "source_table": f"{GAME_DATA}/equip_blueprint_attr_data.json"},
                })
        for piece in armor.get("key_armor", []):
            armor_tiers.append({
                "suit_id": None, "blueprint_id": piece.get("blueprint_id"), "name": piece.get("name"),
                "slot": piece.get("slot"), "tiers": piece.get("tiers", []),
                "source": {"dataset": "armor-sets.json", "source_table": f"{GAME_DATA}/equip_blueprint_attr_data.json"},
            })
        progression["calculator_progression"] = {
            "weapon_tier_scaling": weapon_tiers,
            "armor_tier_scaling": armor_tiers,
            "calibration_ranges": [
                {"calibration_id": row.get("id"), "status": row.get("status"), "affixes": row.get("resolved_affixes", [])}
                for row in calibrations.get("calibrations", [])
            ],
            "crafting_material_stat_effects": armor.get("crafting_material_groups", {}),
            "equipment_strength_term_limits": self.corpus.merged(f"{GAME_DATA}/equip_art_lv_2_terms_strength_lv.json"),
            "equipment_strengthen_rules": self.corpus.merged(f"{GAME_DATA}/equip_make_strengthen_rule.json"),
            "blueprint_collection_level_map": self.corpus.merged(f"{GAME_DATA}/blueprint_collection_random_level_map_data.json"),
            "formula_policy": "Exact source rows preserved; no formulas synthesized where per-tier values exist",
        }
        progression["record_counts"]["weapon_tier_profiles"] = len(weapon_tiers)
        progression["record_counts"]["armor_tier_profiles"] = len(armor_tiers)
        write_json(self.data_dir / "progression.json", progression)
        return {"weapon_tier_profiles": len(weapon_tiers), "armor_tier_profiles": len(armor_tiers)}

    def unresolved_reports(self) -> dict:
        node_rows = [
            {"node_type": node_type, "count": count, "example_entities": self.buffs.unknown_examples.get(node_type, [])}
            for node_type, count in self.buffs.unknown_nodes.most_common()
        ]
        write_json(self.reports / "unresolved-logic-nodes.json", {"generated_utc": utc_now(), "node_types": node_rows})
        write_json(self.reports / "unresolved-buff-references.json", {
            "generated_utc": utc_now(),
            "references": [
                {"buff_id": key[0], "buff_level": key[1], "count": count}
                for key, count in self.buffs.missing_buff_references.most_common()
            ],
            "missing_logic_trees": [
                {"buff_id": key[0], "buff_level": key[1], "logic_tree_ref": key[2], "count": count}
                for key, count in self.buffs.missing_logic_references.most_common()
            ],
        })
        write_json(self.reports / "unresolved-stat-ids.json", {
            "generated_utc": utc_now(),
            "stat_ids": [{"raw_stat_id": key[0], "context": key[1], "count": count} for key, count in self.stats.unresolved.most_common()],
        })
        write_json(self.reports / "unresolved-apply-range-codes.json", {
            "generated_utc": utc_now(),
            "apply_range_codes": [{"apply_range_code": key, "count": count} for key, count in self.applicability.unresolved.most_common()],
        })
        write_json(self.reports / "unresolved-localization.json", {
            "generated_utc": utc_now(), "keys": sorted(self.translate.misses), "count": len(self.translate.misses),
        })
        return {
            "unresolved_logic_node_types": len(node_rows),
            "top_unresolved_logic_nodes": [
                {"node_type": row["node_type"], "count": row["count"]}
                for row in node_rows[:20]
            ],
        }

    def validate(self, buff_status: dict) -> dict:
        relationships = self._payload("relationships.json").get("relationships", [])
        keys = [tuple(row.get(field) for field in ("source_type", "source_id", "relation", "target_type", "target_id")) for row in relationships]
        buffs = self._payload("buffs.json").get("buffs", [])
        calibrations = self._payload("calibrations.json").get("calibrations", [])
        mods = self._payload("mods.json").get("mods", [])
        weapons = self._payload("weapons.json").get("weapons", [])
        deviations = self._payload("deviations.json")
        relationship_keys = set(keys)

        momentum = next((row for row in mods if as_int(row.get("mod_code")) == 2400610), None)
        momentum_levels = {}
        for buff_level in buffs:
            if as_int(buff_level.get("buff_id")) != 589117000:
                continue
            values = {
                resolved.get("internal_name"): resolved.get("value")
                for resolved in buff_level.get("resolved_effects", [])
                if resolved.get("type") == "stat_modifier"
            }
            momentum_levels[as_int(buff_level.get("level"))] = values
        expected_momentum = {
            1: {"weapon_rpm_add_rate": 8.0, "attack_type_dam_add_rate_remote": 10.0},
            2: {"weapon_rpm_add_rate": 8.0, "attack_type_dam_add_rate_remote": 15.0},
            3: {"weapon_rpm_add_rate": 8.0, "attack_type_dam_add_rate_remote": 20.0},
            4: {"weapon_rpm_add_rate": 8.0, "attack_type_dam_add_rate_remote": 25.0},
            5: {"weapon_rpm_add_rate": 10.0, "attack_type_dam_add_rate_remote": 30.0},
        }
        momentum_values_match = all(
            momentum_levels.get(level, {}).get(stat) == value
            for level, expected_stats in expected_momentum.items()
            for stat, value in expected_stats.items()
        )

        electron = next((row for row in weapons if row.get("name") == "AUG - Electron Cloud"), None)
        electron_id = str(electron.get("blueprint_id")) if electron else ""
        electron_chain = {
            ("weapon", electron_id, "uses_skill", "skill", "WS15704"),
            ("skill", "WS15704", "applies_buff", "buff", "354509000"),
            ("skill", "WS15704", "uses_keyword", "keyword_buff", "110300000"),
            ("skill", "WS15704", "applies_status", "status", "302"),
        }

        calibration_example = None
        for calibration in calibrations:
            for affix in calibration.get("resolved_affixes", []):
                for term in affix.get("terms", []):
                    if any(stat.get("raw_stat_id") == "E0300" and stat.get("stat_id") == "E03" for stat in term.get("stats", [])):
                        calibration_example = term
                        break
                if calibration_example:
                    break
            if calibration_example:
                break

        apply_range_2201 = self.applicability.resolve(2201)
        dataset_ids = {}
        for filename, collection, id_fields in (
            ("mods.json", "mods", ("mod_code", "id")),
            ("calibrations.json", "calibrations", ("id", "item_id")),
            ("ammo.json", "ammo", ("item_id", "id")),
            ("attachments.json", "attachments", ("id", "item_id")),
            ("cradles.json", "cradles", ("id",)),
            ("skills.json", "skills", ("id",)),
            ("stat-definitions.json", "stat_definitions", ("id",)),
        ):
            records = self._payload(filename).get(collection, [])
            identifiers = [next((row.get(field) for field in id_fields if row.get(field) not in (None, "")), None) for row in records]
            dataset_ids[filename] = len(identifiers) == len(set(identifiers)) and None not in identifiers
        checks = {
            "no_duplicate_relationships": len(keys) == len(set(keys)),
            "relationships_have_explicit_target_status": all(row.get("resolution_status") in {"resolved", "unresolved"} for row in relationships),
            "no_duplicate_buff_ids": len({row.get("id") for row in buffs}) == len(buffs),
            "no_duplicate_normalized_entity_ids": dataset_ids,
            "buff_metadata_copied": all(
                row.get("lifetime") is not None and row.get("maximum_stacks") is not None
                for row in buffs if row.get("definition_source")
            ),
            "calibration_status_preserved": all(row.get("status") in {"current", "legacy"} for row in calibrations),
            "mod_applicability_consistent": all(row.get("resolved_applicability", {}).get("apply_range_code") == row.get("apply_range_code") for row in mods),
            "placeholder_deviations_hidden": all(as_int(row.get("id")) != 0 and row.get("name") for row in deviations.get("player_deviations", [])),
            "raw_logic_preserved_by_provenance": all(row.get("definition_source") is not None for row in buffs if row.get("raw_game_definition")),
            "unresolved_logic_preserves_raw_nodes": all(
                "raw_node" in node
                for row in buffs for node in row.get("unresolved_nodes", [])
                if node.get("node_type") != "missing_logic_tree"
            ),
            "known_entity_chains": {
                "momentum_up_mod_entry_buff_logic": bool(
                    momentum
                    and as_int(momentum.get("main_entry_code")) == 9118
                    and any(
                        as_int(effect.get("buff_id")) == 589117000
                        for entry in momentum.get("resolved_effects", [])
                        for effect in entry.get("effects", [])
                    )
                    and momentum_values_match
                ),
                "electron_cloud_power_surge": bool(electron and electron_chain.issubset(relationship_keys)),
                "calibration_E0300_to_E03_range": bool(
                    calibration_example
                    and calibration_example.get("minimum_value") is not None
                    and calibration_example.get("maximum_value") is not None
                ),
                "apply_range_2201_is_helmet": bool(
                    apply_range_2201.get("resolution_status") == "resolved"
                    and apply_range_2201.get("category") == "armor"
                    and any(as_int(slot.get("slot_code")) == 21 and slot.get("name") == "Helmet" for slot in apply_range_2201.get("armor_slots", []))
                ),
            },
            "resolution_status_counts": buff_status,
        }
        boolean_results = []
        for value in checks.values():
            if isinstance(value, bool):
                boolean_results.append(value)
            elif isinstance(value, dict) and value and all(isinstance(child, bool) for child in value.values()):
                boolean_results.extend(value.values())
        payload = {"generated_utc": utc_now(), "passed": all(boolean_results), "checks": checks}
        write_json(self.reports / "validation.json", payload)
        write_json(self.reports / "relationship-anomalies.json", {
            "generated_utc": utc_now(), "duplicate_count": len(keys) - len(set(keys)),
            "unresolved_relationships": [row for row in relationships if row.get("resolution_status") == "unresolved"],
        })
        return payload

    def known_entity_report(self, tracer: ReferenceTracer) -> None:
        mods = self._payload("mods.json").get("mods", [])
        momentum = next((row for row in mods if as_int(row.get("mod_code")) == 2400610), None)
        momentum_buffs = [
            {
                "level": row.get("level"), "resolution_status": row.get("resolution_status"),
                "logic_tree_ref": row.get("logic_tree_ref"), "logic_tree": row.get("logic_tree"),
                "lifetime": row.get("lifetime"), "maximum_stacks": row.get("maximum_stacks"),
                "resolved_effects": row.get("resolved_effects"),
                "resolved_conditions": row.get("resolved_conditions"),
                "unresolved_node_types": sorted({node.get("node_type") for node in row.get("unresolved_nodes", []) if node.get("node_type")}),
                "definition_source": row.get("definition_source"),
            }
            for row in self._payload("buffs.json").get("buffs", [])
            if as_int(row.get("buff_id")) == 589117000
        ]
        weapons = self._payload("weapons.json").get("weapons", [])
        electron = next((row for row in weapons if row.get("name") == "AUG - Electron Cloud"), None)
        relationships = self._payload("relationships.json").get("relationships", [])
        electron_sources = {"13451401", "WS15704", "354509000:1"}
        electron_relationships = [
            row for row in relationships
            if row.get("source_id") in electron_sources
            and (
                row.get("source_type") in {"weapon", "skill", "buff"}
                or row.get("target_id") in {"WS15704", "354509000", "110300000", "302"}
            )
        ]
        calibrations = self._payload("calibrations.json").get("calibrations", [])
        calibration_example = None
        for calibration in calibrations:
            for affix in calibration.get("resolved_affixes", []):
                for term in affix.get("terms", []):
                    stat = next((item for item in term.get("stats", []) if item.get("raw_stat_id") == "E0300"), None)
                    if stat:
                        calibration_example = {
                            "calibration_id": calibration.get("id"), "status": calibration.get("status"),
                            "affix_id": affix.get("affix_id"), "minimum_value": term.get("minimum_value"),
                            "maximum_value": term.get("maximum_value"), "stat": stat,
                        }
                        break
                if calibration_example:
                    break
            if calibration_example:
                break
        write_json(self.reports / "known-entity-traces.json", {
            "generated_utc": utc_now(),
            "momentum_up": {
                "mod_code": 2400610, "name": momentum.get("name") if momentum else None,
                "main_entry_code": momentum.get("main_entry_code") if momentum else None,
                "buff_id": 589117000, "resolved_applicability": momentum.get("resolved_applicability") if momentum else None,
                "resolved_effects": momentum.get("resolved_effects") if momentum else None,
                "buff_levels": momentum_buffs,
                "reference_trace": tracer.trace(589117000, 25),
            },
            "electron_cloud_power_surge": {
                "weapon": {
                    "name": electron.get("name"), "blueprint_id": electron.get("blueprint_id"),
                    "item_id": electron.get("item_id"), "passive_skills": electron.get("passive_skills"),
                } if electron else None,
                "expected_chain": ["weapon:13451401", "skill:WS15704", "buff:354509000", "keyword_buff:110300000", "status:302"],
                "relationships": electron_relationships,
                "reference_traces": [tracer.trace(value, 25) for value in ("WS15704", 354509000, 110300000, 302)],
            },
            "calibration_affix": calibration_example,
        })

    def run(self) -> dict:
        self.resolve_stats_file()
        buff_status = self.resolve_buff_file()
        mod_counts = self.resolve_mods()
        calibration_counts = self.resolve_calibrations()
        cross_dataset_stats = self.resolve_stats_across_datasets()
        loadout_counts = self.classify_loadout_data()
        relationship_counts = self.build_relationships()
        progression_counts = self.improve_progression()
        unresolved = self.unresolved_reports()
        tracer = ReferenceTracer(self.corpus, self.published / "indexes" / "reference-tracer.sqlite")
        tracer_counts = tracer.build()
        progression_investigation = run_weapon_progression_investigation(
            self.corpus.base, self.corpus.current, self.published
        )
        self.known_entity_report(tracer)
        validation = self.validate(buff_status)
        report = {
            "schema_version": 1, "generated_utc": utc_now(),
            "buff_resolution": buff_status, "mods": mod_counts,
            "calibrations": calibration_counts, "loadout": loadout_counts,
            "cross_dataset_stats": cross_dataset_stats,
            "relationships": relationship_counts, "progression": progression_counts,
            "weapon_progression_investigation": progression_investigation,
            "reference_tracer": tracer_counts, "unresolved": unresolved,
            "validation_passed": validation.get("passed"),
        }
        write_json(self.reports / "combat-resolution-summary.json", report)
        return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--published", type=Path, required=True)
    parser.add_argument("--trace", action="append", default=[])
    parser.add_argument("--trace-output", type=Path)
    args = parser.parse_args()
    if args.trace:
        corpus = TableCorpus(args.base, args.current)
        tracer = ReferenceTracer(corpus, args.published / "indexes" / "reference-tracer.sqlite")
        index = tracer.build()
        result = {"index": index, "traces": [tracer.trace(query) for query in args.trace]}
        if args.trace_output:
            write_json(args.trace_output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    # A prior run may have produced a cycle diagnostic before the v1.5.7.4
    # source fix. Rebuild this report per run so stale failures cannot survive
    # after current output serializes cleanly.
    cycle_report = args.published / "reports" / "serialization-circular-references.json"
    cycle_report.unlink(missing_ok=True)
    report = CombatPipeline(args.base, args.current, args.published).run()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
