"""Generalized Dead Signal Evidence Graph entry points.

The facade preserves the protected ``DeadSignalEvidenceGraph.weapon_graph`` API
while routing generalized entity traces through registered typed domain adapters.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from dead_signal_domain_adapters import EvidenceAdapterRegistry, EvidenceDomainAdapter
from dead_signal_weapon_adapter import WeaponAdapter


class DeadSignalGeneralizedGraph:
    """Adapter-routed generalized Evidence Graph engine."""

    def __init__(self, output: Path | str):
        self.output = Path(output)
        self.registry = EvidenceAdapterRegistry((WeaponAdapter(output),))

    def register_adapter(self, adapter: EvidenceDomainAdapter) -> None:
        """Register a new typed domain without changing core routing code."""
        self.registry.register(adapter)

    def entity_graph(self, entity_type: str, identity: object, **kwargs: Any) -> dict[str, Any]:
        """Route a generalized trace to the exact registered domain adapter."""
        return self.registry.graph(entity_type, identity, **kwargs)

    def weapon_entity_graph(
        self,
        identity: object,
        *,
        max_occurrences_per_id: int = 80,
    ) -> dict[str, Any]:
        """Backward-compatible Phase-1 weapon generalized entry point."""
        return self.entity_graph(
            "weapon",
            identity,
            max_occurrences_per_id=max_occurrences_per_id,
        )
