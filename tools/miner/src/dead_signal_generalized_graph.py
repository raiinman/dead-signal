"""Phase-1 generalized Evidence Graph entry points.

This facade keeps the protected ``DeadSignalEvidenceGraph.weapon_graph`` API
unchanged while exposing a versioned generalized contract for migration and
future domain adapters.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from dead_signal_evidence_contracts import project_legacy_weapon_graph
from dead_signal_evidence_graph import DeadSignalEvidenceGraph


class DeadSignalGeneralizedGraph:
    """Generalized graph facade introduced after the Weapons v1 freeze."""

    def __init__(self, output: Path | str):
        self.legacy = DeadSignalEvidenceGraph(output)

    def weapon_entity_graph(
        self,
        identity: object,
        *,
        max_occurrences_per_id: int = 80,
    ) -> dict[str, Any]:
        """Return a strict Phase-1 graph without mutating the legacy payload."""
        legacy = self.legacy.weapon_graph(
            identity,
            max_occurrences_per_id=max_occurrences_per_id,
        )
        return project_legacy_weapon_graph(legacy)
