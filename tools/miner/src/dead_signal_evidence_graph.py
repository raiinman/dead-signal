"""Dead Signal Evidence Graph and Identity Map backend.

Builds bounded exact-reference graphs from a completed Miner snapshot.  Discovery
metadata may decorate nodes, but graph edges are created only from extracted exact
identifiers and exact reference-tracer occurrences.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from research_console import ResearchConsole


SCHEMA_VERSION = 1
NODE_ORDER = {
    "weapon": 0, "blueprint_id": 1, "item_id": 2, "prototype_id": 3,
    "gun_no": 4, "fixed_skill_code": 5, "buff_id": 6, "forge_id": 7,
    "raw_handle": 8, "translation_handle": 9, "record": 10,
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


class DeadSignalEvidenceGraph:
    def __init__(self, output: Path | str):
        self.console = ResearchConsole(output)

    def weapon_graph(self, identity: object, *, max_occurrences_per_id: int = 80) -> dict[str, Any]:
        weapon = self.console.find_weapon(identity)
        known = self.console._known_ids(weapon)  # exact extracted values only
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
                nodes[identity_id] = {
                    "id": identity_id,
                    "kind": kind,
                    "label": str(value),
                    "state": "VERIFIED" if refs else "UNRESOLVED",
                    "exact_reference_count": len(refs),
                }
                edges.append({
                    "from": root_id,
                    "to": identity_id,
                    "kind": "exact-identity",
                    "field": kind,
                    "state": "VERIFIED",
                    "authoritative": True,
                })
                for reference in refs:
                    ref_node = _reference_node(reference)
                    nodes.setdefault(ref_node["id"], ref_node)
                    edges.append({
                        "from": identity_id,
                        "to": ref_node["id"],
                        "kind": "exact-occurrence",
                        "field": reference.get("field"),
                        "json_pointer": reference.get("json_pointer"),
                        "state": "VERIFIED",
                        "authoritative": True,
                    })
                    reference_count += 1

        graph_nodes = sorted(nodes.values(), key=lambda row: (NODE_ORDER.get(str(row.get("kind")), 99), str(row.get("label"))))
        return {
            "schema": "dead-signal-evidence-graph",
            "schema_version": SCHEMA_VERSION,
            "brand": "Dead Signal",
            "subject": {"type": "weapon", "identity": identity, "name": weapon.get("name")},
            "record_counts": {"nodes": len(graph_nodes), "edges": len(edges), "exact_occurrences": reference_count},
            "nodes": graph_nodes,
            "edges": edges,
            "policy": {
                "edges": "Only exact extracted identity values and exact reference-tracer occurrences create graph edges.",
                "discovery": "Similarity and analytics may suggest what to inspect but never create an edge.",
                "publication": "Graph presence is evidence provenance, not automatic publication permission.",
            },
        }

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
                items.append({
                    "value": value,
                    "state": "VERIFIED" if refs else "UNRESOLVED",
                    "exact_reference_count": len(refs),
                    "tables": [
                        {"table": table, "occurrences": count}
                        for table, count in sorted(by_table.items(), key=lambda row: (-row[1], row[0]))
                    ],
                })
            families.append({"kind": kind, "values": items})
        families.sort(key=lambda row: (NODE_ORDER.get(row["kind"], 99), row["kind"]))
        return {
            "schema": "dead-signal-identity-map",
            "schema_version": SCHEMA_VERSION,
            "brand": "Dead Signal",
            "weapon": {
                "canonical_id": weapon.get("canonical_id"),
                "name": weapon.get("name"),
                "blueprint_id": weapon.get("blueprint_id"),
                "item_id": weapon.get("item_id"),
                "category": weapon.get("category"),
                "rarity": weapon.get("rarity"),
            },
            "families": families,
            "policy": "Every mapped relationship is backed by an exact extracted identifier; missing paths remain unresolved.",
        }
