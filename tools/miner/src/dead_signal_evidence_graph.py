"""Dead Signal Evidence Graph and Identity Map backend.

Builds bounded exact-reference graphs from a completed Miner snapshot. Discovery
metadata may decorate nodes, but graph edges are created only from extracted exact
identifiers and exact reference-tracer occurrences.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import tempfile
import zipfile
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from research_console import ResearchConsole


SCHEMA_VERSION = 5
NODE_ORDER = {
    "weapon": 0, "blueprint_id": 1, "item_id": 2, "prototype_id": 3,
    "gun_no": 4, "fixed_skill_code": 5, "buff_id": 6, "forge_id": 7,
    "raw_handle": 8, "translation_handle": 9, "record": 10,
}

IDENTITY_FIELD_TOKENS = (
    "blueprint", "prototype", "weapon", "gun", "equip", "item", "forge",
    "skill", "buff", "recipe", "formula", "material", "attachment", "accessory",
    "mod", "suit", "cradle", "deviation", "reward", "drop", "loot", "shop",
    "currency", "resource", "origin", "brand", "series", "source", "target",
    "translation", "handle",
)
IDENTITY_EXACT_FIELDS = {
    "blueprint_id", "blueprint_no", "item_id", "item_no", "prototype_id",
    "prototype_no", "gun_no", "weapon_id", "weapon_no", "equip_id", "equip_no",
    "fixed_skill", "fixed_skill_code", "skill_id", "skill_no", "buff_id", "buff_no",
    "forge_id", "forge_no", "recipe_id", "recipe_no", "material_id", "material_no",
    "attachment_id", "attachment_no", "accessory_id", "accessory_no", "mod_id", "mod_no",
    "suit_id", "suit_no", "cradle_id", "cradle_no", "deviation_id", "deviation_no",
    "reward_id", "reward_no", "drop_id", "drop_no", "loot_id", "loot_no",
    "shop_id", "shop_no", "currency_id", "currency_no", "resource_id", "resource_no",
    "origin_id", "origin_no", "brand_id", "brand_no", "series_id", "series_no",
    "translation_handle", "raw_handle", "source_id", "target_id",
}
GENERIC_FIELD_BLOCKLIST = {
    "record_id", "id", "no", "code",
    "level", "star", "tier", "type", "sub_type", "quality", "rarity", "count",
    "amount", "quantity", "weight", "rate", "ratio", "percent", "probability",
    "x", "y", "z", "index", "sort", "order", "status", "enabled", "flag",
    "min", "max", "value", "param", "parameter", "version",
}

# Some short numeric identities are semantically typed but globally collision-prone.
# For those identities, the full crawler follows the canonical destination table
# instead of treating every equal scalar in the corpus as the same relationship.
# Broader exact occurrences remain available through Identity Map / Evidence Graph.
TYPED_IDENTITY_TABLES = {
    "prototype_id": ("game_common/data/weapon_prototype_data.json",),
    "prototype_no": ("game_common/data/weapon_prototype_data.json",),
}


def _node_id(kind: str, value: object) -> str:
    return f"{kind}:{value}"


def _reference_node(reference: dict[str, Any]) -> dict[str, Any]:
    table = str(reference.get("table") or "")
    record = str(reference.get("record_id") or "")
    layer = str(reference.get("source") or "")
    key = f"{layer}|{table}|{record}"
    return {
        "id": _node_id("record", key),
        "kind": "record",
        "label": f"{Path(table).stem} / {record}",
        "layer": layer,
        "table": table,
        "record_id": record,
        "state": "VERIFIED",
    }


def _safe_slug(value: object) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "")).strip(".-")
    return text[:80] or "identity"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")


def _looks_like_identity(field: object, value: object) -> bool:
    """Return True when a scalar is useful as the next exact identity hop."""
    if value in (None, "", 0, "0", False, True):
        return False
    if isinstance(value, (dict, list, tuple, set)):
        return False
    name = str(field or "").strip().casefold()
    if not name or name in GENERIC_FIELD_BLOCKLIST:
        return False
    text = str(value).strip()
    if len(text) > 256:
        return False
    if name in IDENTITY_EXACT_FIELDS:
        return True
    if name.endswith(("_id", "_ids", "_no", "_code", "_handle")):
        return name not in {"record_id", "id", "no", "code"}
    if any(token in name for token in IDENTITY_FIELD_TOKENS):
        if any(token in name for token in ("name", "desc", "description", "text", "label", "title")):
            return "handle" in name or name.endswith("_id")
        return True
    return False


def _typed_occurrence_rows(
    connection: sqlite3.Connection,
    kind: object,
    value: object,
    limit: int,
) -> tuple[list[tuple[Any, ...]], tuple[str, ...]]:
    """Return exact tracer rows, scoped only when an identity has a canonical table type.

    The tracer stores scalar equality, not semantic type. A value such as prototype
    ``204`` can therefore occur in thousands of unrelated systems. For explicitly
    typed identities we resolve through the canonical destination table while
    retaining the same exact value-to-record evidence requirement.
    """
    normalized_kind = str(kind or "").strip().casefold()
    tables = TYPED_IDENTITY_TABLES.get(normalized_kind, ())
    if tables:
        placeholders = ",".join("?" for _ in tables)
        sql = (
            "SELECT layer,table_name,record_id,field,json_pointer FROM occurrences "
            f"WHERE value=? AND table_name IN ({placeholders}) "
            "ORDER BY table_name,record_id LIMIT ?"
        )
        params: tuple[object, ...] = (str(value), *tables, limit)
    else:
        sql = (
            "SELECT layer,table_name,record_id,field,json_pointer FROM occurrences "
            "WHERE value=? ORDER BY table_name,record_id LIMIT ?"
        )
        params = (str(value), limit)
    return connection.execute(sql, params).fetchall(), tables


def _core_weapon_seeds(weapon: dict[str, Any], console: ResearchConsole) -> list[tuple[str, str]]:
    """Return only the weapon's own identity spine, never enrichment provenance.

    The published web record embeds recipes, materials, resolved stat source records,
    currencies, and other already-expanded evidence. Feeding all of those back into
    the crawler made the initial frontier equivalent to many unrelated subjects.
    Start from the weapon itself and let exact tracer edges discover the rest.
    """
    seeds: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, value: object) -> None:
        if value in (None, "", 0, "0", False, True):
            return
        row = (kind, str(value))
        if row not in seen:
            seen.add(row)
            seeds.append(row)

    add("blueprint_id", weapon.get("blueprint_id"))
    add("item_id", weapon.get("item_id"))
    add("prototype_id", weapon.get("prototype_id"))

    acquisition = weapon.get("acquisition") or {}
    add("fragment_id", acquisition.get("fragment_id"))

    ranged = (weapon.get("baseline") or {}).get("ranged") or {}
    add("bullet_pattern_id", ranged.get("bullet_pattern_id"))

    for tier in ((weapon.get("progression") or {}).get("gear_tiers") or []):
        if not isinstance(tier, dict):
            continue
        add("tier_item_id", tier.get("item_id"))
        add("gun_no", tier.get("gun_no"))

    fixed_skill = console._fixed_skill(weapon)
    add("fixed_skill_code", fixed_skill)
    return seeds


class DeadSignalEvidenceGraph:
    def __init__(self, output: Path | str):
        self.console = ResearchConsole(output)
        self.output = self.console.output

    def weapon_graph(self, identity: object, *, max_occurrences_per_id: int = 80) -> dict[str, Any]:
        weapon = self.console.find_weapon(identity)
        known = self.console._known_ids(weapon)
        root_id = _node_id("weapon", weapon.get("canonical_id") or weapon.get("blueprint_id"))
        nodes: dict[str, dict[str, Any]] = {
            root_id: {
                "id": root_id,
                "kind": "weapon",
                "label": str(weapon.get("name") or "Unknown Weapon"),
                "state": "VERIFIED",
                "canonical_id": weapon.get("canonical_id"),
                "blueprint_id": weapon.get("blueprint_id"),
                "item_id": weapon.get("item_id"),
                "category": weapon.get("category"),
                "rarity": weapon.get("rarity"),
            }
        }
        edges: list[dict[str, Any]] = []
        reference_count = 0
        for kind, values in known.items():
            for value in values:
                identity_id = _node_id(kind, value)
                refs = self.console._trace(value, max_occurrences_per_id)
                nodes[identity_id] = {"id": identity_id, "kind": kind, "label": str(value), "state": "VERIFIED" if refs else "UNRESOLVED", "exact_reference_count": len(refs)}
                edges.append({"from": root_id, "to": identity_id, "kind": "exact-identity", "field": kind, "state": "VERIFIED", "authoritative": True})
                for reference in refs:
                    ref_node = _reference_node(reference)
                    nodes.setdefault(ref_node["id"], ref_node)
                    edges.append({"from": identity_id, "to": ref_node["id"], "kind": "exact-occurrence", "field": reference.get("field"), "json_pointer": reference.get("json_pointer"), "state": "VERIFIED", "authoritative": True})
                    reference_count += 1
        graph_nodes = sorted(nodes.values(), key=lambda row: (NODE_ORDER.get(str(row.get("kind")), 99), str(row.get("label"))))
        return {"schema": "dead-signal-evidence-graph", "schema_version": SCHEMA_VERSION, "brand": "Dead Signal", "subject": {"type": "weapon", "identity": identity, "name": weapon.get("name")}, "record_counts": {"nodes": len(graph_nodes), "edges": len(edges), "exact_occurrences": reference_count}, "nodes": graph_nodes, "edges": edges, "policy": {"edges": "Only exact extracted identity values and exact reference-tracer occurrences create graph edges.", "discovery": "Similarity and analytics may suggest what to inspect but never create an edge.", "publication": "Graph presence is evidence provenance, not automatic publication permission."}}

    def identity_map(self, identity: object) -> dict[str, Any]:
        weapon = self.console.find_weapon(identity)
        known = self.console._known_ids(weapon)
        families = []
        for kind, values in known.items():
            items = []
            for value in values:
                refs = self.console._trace(value, 100)
                by_table: dict[str, int] = defaultdict(int)
                for ref in refs:
                    by_table[str(ref.get("table") or "")] += 1
                items.append({"value": value, "state": "VERIFIED" if refs else "UNRESOLVED", "exact_reference_count": len(refs), "tables": [{"table": table, "occurrences": count} for table, count in sorted(by_table.items(), key=lambda row: (-row[1], row[0]))]})
            families.append({"kind": kind, "values": items})
        families.sort(key=lambda row: (NODE_ORDER.get(row["kind"], 99), row["kind"]))
        return {"schema": "dead-signal-identity-map", "schema_version": SCHEMA_VERSION, "brand": "Dead Signal", "weapon": {"canonical_id": weapon.get("canonical_id"), "name": weapon.get("name"), "blueprint_id": weapon.get("blueprint_id"), "item_id": weapon.get("item_id"), "category": weapon.get("category"), "rarity": weapon.get("rarity")}, "families": families, "policy": "Every mapped relationship is backed by an exact extracted identifier; missing paths remain unresolved."}

    def scan_identity_everything(self, identity: object, *, max_depth: int = 12, max_records: int = 100000, max_identity_values: int = 250000, max_occurrences_per_value: int = 20000, activity: Callable[[str], None] | None = None) -> dict[str, Any]:
        """Recursively crawl all exact connected records and export them to ZIP."""
        if max_depth < 1 or max_depth > 32:
            raise ValueError("Identity scan depth must be between 1 and 32")
        if max_records < 1 or max_records > 500000:
            raise ValueError("Identity scan record cap must be between 1 and 500000")
        if max_identity_values < 1 or max_identity_values > 1000000:
            raise ValueError("Identity scan value cap must be between 1 and 1000000")
        if max_occurrences_per_value < 1 or max_occurrences_per_value > 100000:
            raise ValueError("Identity scan occurrence cap must be between 1 and 100000")
        activity = activity or (lambda _message: None)
        weapon = self.console.find_weapon(identity)
        seeds = _core_weapon_seeds(weapon, self.console)
        if not seeds:
            raise ValueError("Selected Weapon has no extracted core identity seeds")

        export_root = self.output / "research" / "identity-map"
        export_root.mkdir(parents=True, exist_ok=True)
        slug = _safe_slug(weapon.get("name") or identity)
        stamp = _utc_stamp()
        archive = export_root / f"Dead-Signal-Identity-Scan-{slug}-{stamp}.zip"
        progress_path = export_root / "identity-scan-progress.json"
        temp_dir = Path(tempfile.mkdtemp(prefix="dead-signal-identity-", dir=export_root))
        records_path = temp_dir / "records.jsonl"
        values_path = temp_dir / "identity-values.jsonl"
        edges_path = temp_dir / "edges.jsonl"
        unresolved_path = temp_dir / "unresolved-values.jsonl"
        tables_path = temp_dir / "tables.json"
        summary_path = temp_dir / "summary.json"
        weapon_path = temp_dir / "seed-weapon.json"
        readme_path = temp_dir / "README.txt"
        tracer_uri = f"file:{self.console.tracer.as_posix()}?mode=ro"
        queue: deque[tuple[str, str, int, str]] = deque()
        queued: set[tuple[str, str]] = set()
        processed_values: set[tuple[str, str]] = set()
        seen_records: set[tuple[str, str, str]] = set()
        table_counts: Counter[str] = Counter()
        layer_counts: Counter[str] = Counter()
        depth_counts: Counter[int] = Counter()
        field_counts: Counter[str] = Counter()
        typed_scope_counts: Counter[str] = Counter()
        unresolved = 0
        exact_edges = 0
        record_scalar_count = 0
        occurrence_cap_hits = 0
        truncated_reasons: list[str] = []
        for kind, value in seeds:
            identity_key = (kind, value)
            if identity_key not in queued:
                queue.append((kind, value, 0, "weapon-core-seed"))
                queued.add(identity_key)

        def write_progress(stage: str) -> None:
            payload = {"schema": "dead-signal-identity-scan-progress", "schema_version": 4, "stage": stage, "weapon": weapon.get("name"), "queued_values": len(queued), "pending_values": len(queue), "processed_values": len(processed_values), "unprocessed_values": max(0, len(queued) - len(processed_values)), "records": len(seen_records), "exact_edges": exact_edges, "depth_counts": dict(sorted(depth_counts.items())), "seed_policy": "weapon-core-identity-spine", "typed_traversal": True, "record_primary_keys_recursive": False, "updated_at": datetime.now(timezone.utc).isoformat()}
            temporary = progress_path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(progress_path)

        try:
            weapon_path.write_text(json.dumps(weapon, ensure_ascii=False, indent=2), encoding="utf-8")
            readme_path.write_text("Dead Signal Identity Map — Full Connected Exact-Reference Export\n\nrecords.jsonl contains every scalar occurrence for each exact connected record.\nidentity-values.jsonl contains recursively traversed semantic identifier values.\nedges.jsonl contains exact value-to-record and record-to-identity relationships.\nunresolved-values.jsonl contains traversed identity values with no exact occurrence.\ntables.json summarizes connected tables. summary.json contains caps/policy/results.\n\nThe scan begins only from the selected weapon's core identity spine. Recipe materials, currencies, stat-source record IDs, and other enrichment embedded in the web record are not initial seeds; they must be discovered through exact connected records. Generic record primary keys (id/no/code/record_id) are exported as provenance but never recurse. Collision-prone typed identities such as prototype_no/prototype_id resolve through their canonical destination table instead of every equal scalar in the corpus.\nNo fuzzy/name matching is used. No game bytecode is executed. No live process is touched.\n", encoding="utf-8")
            write_progress("starting")
            activity(f"Identity Map: scanning exact neighborhood from {len(seeds)} core seeds for {weapon.get('name')}")
            connection = sqlite3.connect(tracer_uri, uri=True)
            try:
                with records_path.open("w", encoding="utf-8") as records_out, values_path.open("w", encoding="utf-8") as values_out, edges_path.open("w", encoding="utf-8") as edges_out, unresolved_path.open("w", encoding="utf-8") as unresolved_out:
                    while queue:
                        if len(processed_values) >= max_identity_values:
                            truncated_reasons.append("max_identity_values"); break
                        if len(seen_records) >= max_records:
                            truncated_reasons.append("max_records"); break
                        kind, value, depth, discovered_from = queue.popleft()
                        identity_key = (kind, value)
                        if identity_key in processed_values:
                            continue
                        processed_values.add(identity_key); depth_counts[depth] += 1
                        occurrence_rows, typed_tables = _typed_occurrence_rows(connection, kind, value, max_occurrences_per_value + 1)
                        if typed_tables:
                            typed_scope_counts[str(kind).casefold()] += 1
                        values_out.write(json.dumps({"value": value, "kind": kind, "depth": depth, "discovered_from": discovered_from, "typed_target_tables": list(typed_tables)}, ensure_ascii=False) + "\n")
                        if len(occurrence_rows) > max_occurrences_per_value:
                            occurrence_cap_hits += 1; occurrence_rows = occurrence_rows[:max_occurrences_per_value]
                        if not occurrence_rows:
                            unresolved += 1
                            unresolved_out.write(json.dumps({"value": value, "kind": kind, "depth": depth, "discovered_from": discovered_from, "typed_target_tables": list(typed_tables)}, ensure_ascii=False) + "\n")
                            continue
                        for layer, table, record_id, field, pointer in occurrence_rows:
                            record_key = (str(layer), str(table), str(record_id))
                            edges_out.write(json.dumps({"from_type": "identity", "from": value, "identity_kind": kind, "to_type": "record", "layer": layer, "table": table, "record_id": record_id, "field": field, "json_pointer": pointer, "depth": depth, "match": "exact", "authoritative": True, "typed_scope": list(typed_tables)}, ensure_ascii=False) + "\n"); exact_edges += 1
                            if record_key in seen_records:
                                continue
                            if len(seen_records) >= max_records:
                                truncated_reasons.append("max_records"); break
                            seen_records.add(record_key); table_counts[str(table)] += 1; layer_counts[str(layer)] += 1
                            scalar_rows = connection.execute("SELECT value,field,json_pointer FROM occurrences WHERE layer=? AND table_name=? AND record_id=? ORDER BY json_pointer", record_key).fetchall()
                            record_scalars = []; next_identities = []
                            for scalar_value, scalar_field, scalar_pointer in scalar_rows:
                                scalar_text = str(scalar_value); scalar_field_text = str(scalar_field or "")
                                record_scalars.append({"value": scalar_text, "field": scalar_field_text, "json_pointer": scalar_pointer}); record_scalar_count += 1; field_counts[scalar_field_text] += 1
                                if depth >= max_depth or not _looks_like_identity(scalar_field_text, scalar_text):
                                    continue
                                next_identities.append({"value": scalar_text, "field": scalar_field_text, "json_pointer": scalar_pointer})
                                edges_out.write(json.dumps({"from_type": "record", "layer": layer, "table": table, "record_id": record_id, "to_type": "identity", "to": scalar_text, "field": scalar_field_text, "json_pointer": scalar_pointer, "depth": depth + 1, "relationship": "semantic-identity-field-candidate", "authoritative": False, "note": "Traversal candidate only; next typed/exact value->record edge must be independently proven in tracer."}, ensure_ascii=False) + "\n")
                            records_out.write(json.dumps({"layer": layer, "table": table, "record_id": record_id, "discovered_by": value, "discovered_by_kind": kind, "depth": depth, "scalar_count": len(record_scalars), "scalars": record_scalars, "next_identity_candidates": next_identities}, ensure_ascii=False) + "\n")
                            if depth < max_depth:
                                for candidate in next_identities:
                                    candidate_value = candidate["value"]
                                    candidate_kind = candidate["field"]
                                    candidate_key = (candidate_kind, candidate_value)
                                    if candidate_key in queued or candidate_key in processed_values:
                                        continue
                                    if len(queued) >= max_identity_values:
                                        continue
                                    queue.append((candidate_kind, candidate_value, depth + 1, f"{layer}|{table}|{record_id}{candidate['json_pointer'] or ''}")); queued.add(candidate_key)
                            if len(seen_records) % 250 == 0:
                                activity(f"Identity Map: {len(seen_records):,} records / {len(processed_values):,} identities / depth {depth}"); write_progress("scanning")
                        if truncated_reasons:
                            break
            finally:
                connection.close()
            tables_payload = {"schema": "dead-signal-identity-scan-tables", "schema_version": 1, "table_count": len(table_counts), "tables": [{"table": table, "records": count} for table, count in sorted(table_counts.items(), key=lambda row: (-row[1], row[0]))], "layers": dict(sorted(layer_counts.items()))}
            tables_path.write_text(json.dumps(tables_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            unprocessed = max(0, len(queued) - len(processed_values))
            summary = {"schema": "dead-signal-identity-everything-export", "schema_version": 4, "brand": "Dead Signal", "generated_at": datetime.now(timezone.utc).isoformat(), "weapon": {"canonical_id": weapon.get("canonical_id"), "name": weapon.get("name"), "blueprint_id": weapon.get("blueprint_id"), "item_id": weapon.get("item_id"), "prototype_id": weapon.get("prototype_id"), "category": weapon.get("category"), "rarity": weapon.get("rarity")}, "seed_policy": "weapon-core-identity-spine", "seed_identities": [{"kind": kind, "value": value} for kind, value in seeds], "record_counts": {"identity_values_discovered": len(queued), "identity_values_processed": len(processed_values), "identity_values_unprocessed": unprocessed, "connected_records": len(seen_records), "connected_tables": len(table_counts), "record_scalars_exported": record_scalar_count, "exact_value_to_record_edges": exact_edges, "unresolved_processed_identity_values": unresolved, "occurrence_cap_hits": occurrence_cap_hits}, "typed_scope_counts": dict(sorted(typed_scope_counts.items())), "depth_counts": {str(key): value for key, value in sorted(depth_counts.items())}, "limits": {"max_depth": max_depth, "max_records": max_records, "max_identity_values": max_identity_values, "max_occurrences_per_value": max_occurrences_per_value}, "truncated": bool(truncated_reasons or occurrence_cap_hits), "truncated_reasons": sorted(set(truncated_reasons)), "most_common_fields": [{"field": field, "occurrences": count} for field, count in field_counts.most_common(100)], "policy": {"seed_scope": "Only the selected weapon's own identity spine seeds the scan. Embedded enrichment/provenance must be discovered through exact tracer edges.", "record_capture": "Every scalar occurrence from every discovered exact record is exported.", "recursive_traversal": "Only semantic relationship fields recurse. Generic table primary keys id/no/code/record_id are exported but blocked from recursion. Collision-prone semantic types can additionally constrain traversal to canonical destination tables.", "typed_resolution": "prototype_id/prototype_no resolve through game_common/data/weapon_prototype_data.json; equal scalar values in unrelated systems do not become prototype traversal edges.", "edge_authority": "Only value->record edges returned by reference-tracer.sqlite are authoritative exact joins. Record->candidate identity edges are traversal leads until the next typed/exact tracer hop proves them.", "matching": "No fuzzy, substring, or name-based relationship is used.", "execution": "Read-only completed snapshot and reference tracer only; no game bytecode execution and no live process access.", "publication": "This ZIP is research evidence and does not automatically authorize player-facing publication."}}
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            write_progress("packaging"); activity(f"Identity Map: packaging {len(seen_records):,} connected records")
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as destination:
                for path in (summary_path, weapon_path, tables_path, records_path, values_path, edges_path, unresolved_path, readme_path):
                    destination.write(path, path.name)
            write_progress("complete"); activity(f"Identity Map export ready: {archive.name}")
            return {**summary, "archive": str(archive), "archive_size": archive.stat().st_size}
        except Exception:
            write_progress("failed"); raise
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
