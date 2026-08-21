"""Generalized Dead Signal Evidence Graph entry points.

The facade preserves the protected ``DeadSignalEvidenceGraph.weapon_graph`` API
while routing generalized entity traces through registered typed domain adapters.
"""
from __future__ import annotations

from pathlib import Path
from threading import Event
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
from dead_signal_evidence_review import ManualReviewStore, assess_claim, build_review_queue, export_evidence_bundle
from dead_signal_graph_runtime import DEFAULT_TIMEOUT_SECONDS, TraceRuntime
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
            CradleAdapter(output),
            RecipeAdapter(output),
            MaterialAdapter(output),
            DeviationAdapter(output),
        ))
        self.entities = DeadSignalEntityRegistry(output, self.registry)
        self.invalidation = DependencyInvalidationStore(output)
        self.manual_reviews = ManualReviewStore(output)
        self.runtime = TraceRuntime(output)
        self.last_trace_meta: dict[str, Any] = {}

    def register_adapter(self, adapter: EvidenceDomainAdapter) -> None:
        """Register a new typed domain without changing core routing code."""
        self.registry.register(adapter)

    def entity_graph(
        self,
        entity_type: str,
        identity: object,
        *,
        use_cache: bool = True,
        cancel_event: Event | None = None,
        progress: Callable[[int, str], None] | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Route one bounded generalized trace to the exact registered adapter."""
        clean_kwargs = dict(kwargs)
        result = self.runtime.run(
            lambda: self.registry.graph(entity_type, identity, **clean_kwargs),
            entity_type=entity_type,
            identity=identity,
            kwargs=clean_kwargs,
            use_cache=use_cache,
            cancel_event=cancel_event,
            progress=progress,
            timeout_seconds=timeout_seconds,
        )
        self.last_trace_meta = {
            "entity_type": str(entity_type),
            "identity": str(identity),
            "cache_status": result.cache_status,
            "elapsed_seconds": result.elapsed_seconds,
        }
        return result.graph

    def clear_trace_cache(self) -> None:
        """Delete research-only cached adapter results."""
        self.runtime.cache.clear()

    def dependency_invalidation_plan(self) -> dict[str, Any]:
        """Return persisted claims whose exact source dependencies changed."""
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
        """Persist recomputed claims and queue stale/removed proof for review."""
        options: dict[str, Any] = {
            "full_snapshot": full_snapshot,
            "removed_claim_keys": removed_claim_keys,
            "persist": persist,
        }
        if page_resolver is not None:
            options["page_resolver"] = page_resolver
        return self.invalidation.evaluate(graphs, **options)

    def assess_claim(self, graph: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
        """Return requirement-by-requirement assessment without changing proof."""
        return assess_claim(graph, claim)

    def evidence_review_queue(
        self,
        graphs: Iterable[dict[str, Any]],
        *,
        invalidation_report: dict[str, Any] | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        """Build a deterministic review queue and shared-missing-owner groups."""
        return build_review_queue(graphs, invalidation_report=invalidation_report, domain=domain)

    def record_manual_review(self, claim_key: object, *, state: str, reviewer: str, note: str,
                             source_ref: str = "") -> dict[str, Any]:
        """Record an attributable review overlay; never changes deterministic proof."""
        return self.manual_reviews.record(claim_key, state=state, reviewer=reviewer, note=note, source_ref=source_ref)

    def remove_manual_review(self, claim_key: object) -> bool:
        """Remove one human review overlay without editing evidence data."""
        return self.manual_reviews.remove(claim_key)

    def export_review_bundle(self, graphs: Iterable[dict[str, Any]], claim_keys: Iterable[str], destination: Path | str) -> dict[str, Any]:
        """Export a bounded research-only evidence bundle."""
        return export_evidence_bundle(graphs, claim_keys, destination)

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
        bounded_limit = max(1, min(int(limit), 1000))
        return self.entities.search(query, entity_type=entity_type, unresolved_only=unresolved_only, limit=bounded_limit)

    def registered_entity(self, entity_type: str, canonical_id: object) -> dict[str, Any]:
        """Return one registry entity and record it in the recent-trace list."""
        return self.entities.get(entity_type, canonical_id)

    def recent_entities(self) -> list[dict[str, Any]]:
        return self.entities.recent()

    def weapon_entity_graph(self, identity: object, *, max_occurrences_per_id: int = 80, **runtime: Any) -> dict[str, Any]:
        return self.entity_graph("weapon", identity, max_occurrences_per_id=max_occurrences_per_id, **runtime)

    def attachment_entity_graph(self, identity: object, **runtime: Any) -> dict[str, Any]:
        return self.entity_graph("attachment", identity, **runtime)

    def calibration_entity_graph(self, identity: object, **runtime: Any) -> dict[str, Any]:
        return self.entity_graph("calibration", identity, **runtime)

    def armor_entity_graph(self, identity: object, **runtime: Any) -> dict[str, Any]:
        return self.entity_graph("armor", identity, **runtime)

    def armor_set_entity_graph(self, identity: object, **runtime: Any) -> dict[str, Any]:
        return self.entity_graph("armor_set", identity, **runtime)

    def mod_entity_graph(self, identity: object, **runtime: Any) -> dict[str, Any]:
        return self.entity_graph("mod", identity, **runtime)

    def cradle_entity_graph(self, identity: object, **runtime: Any) -> dict[str, Any]:
        return self.entity_graph("cradle", identity, **runtime)

    def recipe_entity_graph(self, identity: object, **runtime: Any) -> dict[str, Any]:
        return self.entity_graph("recipe", identity, **runtime)

    def material_entity_graph(self, identity: object, **runtime: Any) -> dict[str, Any]:
        return self.entity_graph("material", identity, **runtime)

    def deviation_entity_graph(self, identity: object, **runtime: Any) -> dict[str, Any]:
        return self.entity_graph("deviation", identity, **runtime)
