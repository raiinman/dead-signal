"""Dead Signal Workflow Lab.

A constrained visual-workflow backend inspired by data-mining workbenches but
purpose-built for Once Human evidence research.  Nodes are deterministic,
read-only operations over completed Miner snapshots.  Workflows may produce
leads and candidates; they cannot assign VERIFIED or write public datasets.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from dead_signal_analytics import DeadSignalAnalytics
from dead_signal_evidence_graph import DeadSignalEvidenceGraph
from neox_data_explorer import NeoXDataExplorer
from research_console import ResearchConsole


SCHEMA_VERSION = 1
ALLOWED_NODES = (
    "weapon_input",
    "extract_exact_ids",
    "find_exact_references",
    "table_filter",
    "field_filter",
    "resolve_translation",
    "shared_value_check",
    "identity_map",
    "analytics_description_leads",
    "evidence_result",
)


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def default_description_workflow() -> dict[str, Any]:
    return {
        "schema": "dead-signal-workflow",
        "schema_version": SCHEMA_VERSION,
        "name": "Weapon Description Trace",
        "nodes": [
            {"id": "weapon", "type": "weapon_input", "config": {}},
            {"id": "ids", "type": "extract_exact_ids", "inputs": ["weapon"], "config": {}},
            {"id": "refs", "type": "find_exact_references", "inputs": ["ids"], "config": {"limit_per_id": 120}},
            {"id": "fields", "type": "field_filter", "inputs": ["refs"], "config": {"contains": ["desc", "tooltip", "display", "copy", "text"]}},
            {"id": "result", "type": "evidence_result", "inputs": ["fields"], "config": {}},
        ],
    }


class DeadSignalWorkflowLab:
    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        self.console = ResearchConsole(self.output)
        self.explorer = NeoXDataExplorer(self.output)
        self.graph = DeadSignalEvidenceGraph(self.output)
        self.analytics = DeadSignalAnalytics(self.output)
        self.handlers: dict[str, Callable[[dict[str, Any], list[Any], dict[str, Any]], Any]] = {
            "weapon_input": self._weapon_input,
            "extract_exact_ids": self._extract_exact_ids,
            "find_exact_references": self._find_exact_references,
            "table_filter": self._table_filter,
            "field_filter": self._field_filter,
            "resolve_translation": self._resolve_translation,
            "shared_value_check": self._shared_value_check,
            "identity_map": self._identity_map,
            "analytics_description_leads": self._analytics_description_leads,
            "evidence_result": self._evidence_result,
        }

    def _weapon_input(self, context: dict[str, Any], _inputs: list[Any], _config: dict[str, Any]) -> Any:
        identity = context.get("weapon_identity")
        if not identity:
            raise ValueError("Workflow requires weapon_identity in context")
        return self.console.find_weapon(identity)

    def _extract_exact_ids(self, _context: dict[str, Any], inputs: list[Any], _config: dict[str, Any]) -> Any:
        if not inputs or not isinstance(inputs[0], dict):
            raise ValueError("extract_exact_ids requires one Weapon input")
        return self.console._known_ids(inputs[0])

    def _find_exact_references(self, _context: dict[str, Any], inputs: list[Any], config: dict[str, Any]) -> Any:
        if not inputs or not isinstance(inputs[0], dict):
            raise ValueError("find_exact_references requires exact ID families")
        limit = min(1000, max(1, int(config.get("limit_per_id") or 120)))
        rows = []
        for kind, values in inputs[0].items():
            for value in values:
                for reference in self.console._trace(value, limit):
                    rows.append({"identity_kind": kind, "identity_value": value, **reference})
        return rows

    @staticmethod
    def _table_filter(_context: dict[str, Any], inputs: list[Any], config: dict[str, Any]) -> Any:
        rows = list(inputs[0] if inputs else [])
        contains = [str(value).casefold() for value in config.get("contains") or []]
        if not contains:
            return rows
        return [row for row in rows if any(token in str(row.get("table") or "").casefold() for token in contains)]

    @staticmethod
    def _field_filter(_context: dict[str, Any], inputs: list[Any], config: dict[str, Any]) -> Any:
        rows = list(inputs[0] if inputs else [])
        contains = [str(value).casefold() for value in config.get("contains") or []]
        if not contains:
            return rows
        return [row for row in rows if any(token in str(row.get("field") or "").casefold() for token in contains)]

    def _resolve_translation(self, _context: dict[str, Any], inputs: list[Any], _config: dict[str, Any]) -> Any:
        rows = list(inputs[0] if inputs else [])
        results = []
        for row in rows:
            value = row.get("value") or row.get("identity_value")
            if not value:
                results.append({**row, "translation": None})
                continue
            forensic = self.console.translation_forensics(value)
            results.append({**row, "translation": forensic})
        return results

    @staticmethod
    def _shared_value_check(_context: dict[str, Any], inputs: list[Any], _config: dict[str, Any]) -> Any:
        rows = list(inputs[0] if inputs else [])
        counts: dict[str, int] = {}
        for row in rows:
            value = str(row.get("value") or row.get("identity_value") or row.get("text") or "")
            if value:
                counts[value] = counts.get(value, 0) + 1
        return [{**row, "workflow_shared_count": counts.get(str(row.get("value") or row.get("identity_value") or row.get("text") or ""), 0)} for row in rows]

    def _identity_map(self, context: dict[str, Any], _inputs: list[Any], _config: dict[str, Any]) -> Any:
        identity = context.get("weapon_identity")
        if not identity:
            raise ValueError("identity_map requires weapon_identity")
        return self.graph.identity_map(identity)

    def _analytics_description_leads(self, _context: dict[str, Any], _inputs: list[Any], config: dict[str, Any]) -> Any:
        return self.analytics.description_leads(limit=min(1000, max(1, int(config.get("limit") or 250))))

    @staticmethod
    def _evidence_result(_context: dict[str, Any], inputs: list[Any], _config: dict[str, Any]) -> Any:
        value = inputs[0] if inputs else None
        return {
            "state": "CANDIDATE" if value else "UNRESOLVED",
            "result": value,
            "verification": "BLOCKED-PENDING-INDEPENDENT-EXACT-VERIFICATION",
            "publication": "BLOCKED",
        }

    def run(self, workflow: dict[str, Any], *, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = dict(context or {})
        nodes = workflow.get("nodes") or []
        if not isinstance(nodes, list) or not nodes:
            raise ValueError("Workflow must contain at least one node")
        outputs: dict[str, Any] = {}
        trace = []
        for node in nodes:
            if not isinstance(node, dict):
                raise ValueError("Workflow nodes must be objects")
            node_id = str(node.get("id") or "").strip()
            node_type = str(node.get("type") or "").strip()
            if not node_id or node_type not in self.handlers:
                raise ValueError(f"Unsupported Workflow Lab node: {node_type or node_id}")
            input_ids = [str(value) for value in node.get("inputs") or []]
            missing = [value for value in input_ids if value not in outputs]
            if missing:
                raise ValueError(f"Workflow node {node_id} references unavailable inputs: {missing}")
            input_values = [outputs[value] for value in input_ids]
            result = self.handlers[node_type](context, input_values, dict(node.get("config") or {}))
            outputs[node_id] = result
            trace.append({"id": node_id, "type": node_type, "inputs": input_ids, "status": "complete"})
        final_id = str(nodes[-1].get("id"))
        return {
            "schema": "dead-signal-workflow-run",
            "schema_version": SCHEMA_VERSION,
            "brand": "Dead Signal",
            "workflow": str(workflow.get("name") or "Unnamed Workflow"),
            "allowed_nodes": list(ALLOWED_NODES),
            "trace": trace,
            "final_node": final_id,
            "result": outputs.get(final_id),
            "policy": {
                "execution": "Read-only operations over completed Miner snapshots.",
                "verification": "Workflow Lab cannot assign VERIFIED.",
                "publication": "Workflow Lab has no public-data write path.",
            },
        }

    def save_workflow(self, workflow: dict[str, Any], name: str) -> Path:
        safe = "".join(ch for ch in str(name) if ch.isalnum() or ch in "-_ ").strip().replace(" ", "-")
        if not safe:
            raise ValueError("Workflow name must contain letters or numbers")
        folder = self.output / "research" / "workflows"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{safe}.json"
        path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path
