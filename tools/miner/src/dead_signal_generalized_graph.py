"""Generalized Dead Signal Evidence Graph entry points.

The facade preserves the protected ``DeadSignalEvidenceGraph.weapon_graph`` API
while routing generalized entity traces through registered typed domain adapters.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable

from dead_signal_armor_adapters import ArmorAdapter
from dead_signal_armor_set_adapter import ArmorSetAdapter
from dead_signal_attachment_adapter import AttachmentAdapter
from dead_signal_calibration_adapter import CalibrationAdapter
from dead_signal_crafting_adapters import MaterialAdapter, RecipeAdapter
from dead_signal_cradle_adapter import CradleAdapter
from dead_signal_dependency_invalidation import DependencyInvalidationStore
from dead_signal_deviation_adapter import DeviationAdapter
from dead_signal_domain_adapters import EvidenceAdapterRegistry, EvidenceDomainAdapter
from dead_signal_entity_registry import DeadSignalEntityRegistry
from dead_signal_mod_adapter import ModAdapter
from dead_signal_weapon_adapter import WeaponAdapter


class DeadSignalGeneralizedGraph:
    """Adapter-routed generalized Evidence Graph engine."""

    def __init__(self, output: Path | str):
        self.output = Path(output)
        self.registry = EvidenceAdapterRegistry((
            WeaponAdapter(output), AttachmentAdapter(output), CalibrationAdapter(output),
            ArmorAdapter(output), ArmorSetAdapter(output), ModAdapter(output),
            CradleAdapter(output), RecipeAdapter(output), MaterialAdapter(output),
            DeviationAdapter(output),
        ))
        self.entities = DeadSignalEntityRegistry(output, self.registry)
        self.invalidation = DependencyInvalidationStore(output)

    def register_adapter(self, adapter: EvidenceDomainAdapter) -> None:
        self.registry.register(adapter)

    def entity_graph(self, entity_type: str, identity: object, **kwargs: Any) -> dict[str, Any]:
        return self.registry.graph(entity_type, identity, **kwargs)

    def dependency_invalidation_plan(self) -> dict[str, Any]:
        return self.invalidation.invalidation_plan()

    def evaluate_dependency_invalidation(
        self,
        graphs: Iterable[dict[str, Any]],
        *,
        page_resolver: Callable[[str, str, str], Iterable[str]] | None = None,
        full_snapshot: bool = True,
        removed_claim_keys: Iterable[str] = (),
        persist: bool = True,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "full_snapshot": full_snapshot,
            "removed_claim_keys": removed_claim_keys,
            "persist": persist,
        }
        if page_resolver is not None:
            kwargs["page_resolver"] = page_resolver
        return self.invalidation.evaluate(graphs, **kwargs)

    def rebuild_entity_registry(self) -> dict[str, Any]:
        return self.entities.rebuild()

    def search_entities(self, query: object, *, entity_type: str | None = None, unresolved_only: bool = False, limit: int = 100) -> list[dict[str, Any]]:
        return self.entities.search(query, entity_type=entity_type, unresolved_only=unresolved_only, limit=limit)

    def registered_entity(self, entity_type: str, canonical_id: object) -> dict[str, Any]:
        return self.entities.get(entity_type, canonical_id)

    def recent_entities(self) -> list[dict[str, Any]]:
        return self.entities.recent()

    def weapon_entity_graph(self, identity: object, *, max_occurrences_per_id: int = 80) -> dict[str, Any]:
        return self.entity_graph("weapon", identity, max_occurrences_per_id=max_occurrences_per_id)

    def attachment_entity_graph(self, identity: object) -> dict[str, Any]: return self.entity_graph("attachment", identity)
    def calibration_entity_graph(self, identity: object) -> dict[str, Any]: return self.entity_graph("calibration", identity)
    def armor_entity_graph(self, identity: object) -> dict[str, Any]: return self.entity_graph("armor", identity)
    def armor_set_entity_graph(self, identity: object) -> dict[str, Any]: return self.entity_graph("armor_set", identity)
    def mod_entity_graph(self, identity: object) -> dict[str, Any]: return self.entity_graph("mod", identity)
    def cradle_entity_graph(self, identity: object) -> dict[str, Any]: return self.entity_graph("cradle", identity)
    def recipe_entity_graph(self, identity: object) -> dict[str, Any]: return self.entity_graph("recipe", identity)
    def material_entity_graph(self, identity: object) -> dict[str, Any]: return self.entity_graph("material", identity)
    def deviation_entity_graph(self, identity: object) -> dict[str, Any]: return self.entity_graph("deviation", identity)
