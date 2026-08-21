"""Generalized Dead Signal Evidence Graph entry points.

The facade preserves the protected ``DeadSignalEvidenceGraph.weapon_graph`` API
while routing generalized entity traces through registered typed domain adapters.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from dead_signal_armor_adapters import ArmorAdapter
from dead_signal_armor_set_adapter import ArmorSetAdapter
from dead_signal_attachment_adapter import AttachmentAdapter
from dead_signal_calibration_adapter import CalibrationAdapter
from dead_signal_domain_adapters import EvidenceAdapterRegistry, EvidenceDomainAdapter
from dead_signal_entity_registry import DeadSignalEntityRegistry
from dead_signal_mod_adapter import ModAdapter
from dead_signal_weapon_adapter import WeaponAdapter


class DeadSignalGeneralizedGraph:
    """Adapter-routed generalized Evidence Graph engine."""

    def __init__(self, output: Path | str):
        self.output = Path(output)
        self.registry = EvidenceAdapterRegistry((
            WeaponAdapter(output),
            AttachmentAdapter(output),
            CalibrationAdapter(output),
            ArmorAdapter(output),
            ArmorSetAdapter(output),
            ModAdapter(output),
        ))
        self.entities = DeadSignalEntityRegistry(output, self.registry)

    def register_adapter(self, adapter: EvidenceDomainAdapter) -> None:
        """Register a new typed domain without changing core routing code."""
        self.registry.register(adapter)

    def entity_graph(self, entity_type: str, identity: object, **kwargs: Any) -> dict[str, Any]:
        """Route a generalized trace to the exact registered domain adapter."""
        return self.registry.graph(entity_type, identity, **kwargs)

    def rebuild_entity_registry(self) -> dict[str, Any]:
        """Reindex source-derived entities for all currently registered adapters."""
        return self.entities.rebuild()

    def search_entities(
        self,
        query: object,
        *,
        entity_type: str | None = None,
        unresolved_only: bool = False,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search exact IDs and source-proven names without creating evidence edges."""
        return self.entities.search(
            query,
            entity_type=entity_type,
            unresolved_only=unresolved_only,
            limit=limit,
        )

    def registered_entity(self, entity_type: str, canonical_id: object) -> dict[str, Any]:
        """Return one registry entity and record it in the recent-trace list."""
        return self.entities.get(entity_type, canonical_id)

    def recent_entities(self) -> list[dict[str, Any]]:
        return self.entities.recent()

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

    def attachment_entity_graph(self, identity: object) -> dict[str, Any]:
        """Phase-4 typed Attachment graph entry point."""
        return self.entity_graph("attachment", identity)

    def calibration_entity_graph(self, identity: object) -> dict[str, Any]:
        """Phase-5 typed Calibration Blueprint graph entry point."""
        return self.entity_graph("calibration", identity)

    def armor_entity_graph(self, identity: object) -> dict[str, Any]:
        """Phase-6 typed Armor Piece graph entry point."""
        return self.entity_graph("armor", identity)

    def armor_set_entity_graph(self, identity: object) -> dict[str, Any]:
        """Phase-6 typed Armor Set graph entry point."""
        return self.entity_graph("armor_set", identity)

    def mod_entity_graph(self, identity: object) -> dict[str, Any]:
        """Phase-7 typed current Mod 2.0 graph entry point."""
        return self.entity_graph("mod", identity)
