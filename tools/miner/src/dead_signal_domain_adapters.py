"""Typed domain-adapter framework for the generalized Dead Signal Evidence Graph.

Adapters declare the exact evidence surface they are allowed to traverse. The
registry routes entities to adapters, but adapters cannot publish website data or
promote discovery/name similarity into proof.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterable

from dead_signal_evidence_contracts import validate_generalized_graph


GENERIC_IDENTITY_FIELDS = frozenset({"id", "no", "code"})


@dataclass(frozen=True)
class AdapterContract:
    entity_type: str
    identity_seeds: tuple[str, ...]
    canonical_owner_tables: tuple[str, ...]
    allowed_outbound_fields: tuple[str, ...]
    typed_destination_tables: tuple[tuple[str, tuple[str, ...]], ...]
    collision_prone_fields: tuple[str, ...]
    blocked_generic_fields: tuple[str, ...]
    terminal_presentation_fields: tuple[str, ...]
    supported_claims: tuple[str, ...]
    applicability_rules: tuple[str, ...]

    def destinations(self) -> dict[str, tuple[str, ...]]:
        return dict(self.typed_destination_tables)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.entity_type.strip():
            errors.append("adapter entity_type must be non-empty")
        if not self.identity_seeds:
            errors.append("adapter must declare identity seeds")
        if not self.canonical_owner_tables:
            errors.append("adapter must declare canonical owner tables")
        if not self.supported_claims:
            errors.append("adapter must declare supported claims")

        blocked = set(self.blocked_generic_fields) | set(GENERIC_IDENTITY_FIELDS)
        for seed in self.identity_seeds:
            if seed.casefold() in blocked:
                errors.append(f"generic identity seed is forbidden: {seed}")

        destinations = self.destinations()
        for field in self.collision_prone_fields:
            if not destinations.get(field):
                errors.append(f"collision-prone field requires explicit destination tables: {field}")

        for field in self.allowed_outbound_fields:
            if field.casefold() in GENERIC_IDENTITY_FIELDS:
                errors.append(f"bare generic outbound field is forbidden: {field}")

        if len(destinations) != len(self.typed_destination_tables):
            errors.append("typed destination field declared more than once")
        for field, tables in self.typed_destination_tables:
            if not field.strip() or not tables or any(not table.strip() for table in tables):
                errors.append(f"typed destination declaration is incomplete: {field}")
        return errors


class EvidenceDomainAdapter(ABC):
    """Base interface for one exact evidence domain.

    Adapters resolve evidence and presentation only. They intentionally expose no
    publish method; publication remains a separate reviewed projection boundary.
    """

    contract: AdapterContract

    def __init__(self) -> None:
        errors = self.contract.validate()
        if errors:
            raise ValueError(f"Invalid {self.__class__.__name__} contract: {errors}")

    @property
    def entity_type(self) -> str:
        return self.contract.entity_type

    @abstractmethod
    def identify(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        """Return the validated generalized entity contract."""

    @abstractmethod
    def claims(self, identity: object, **kwargs: Any) -> list[dict[str, Any]]:
        """Return deterministic claims supported by this adapter."""

    @abstractmethod
    def resolve_claim(self, identity: object, claim_type: str, **kwargs: Any) -> dict[str, Any]:
        """Resolve exactly one declared claim type or fail closed."""

    @abstractmethod
    def dependencies(self, identity: object, **kwargs: Any) -> list[str]:
        """Return dependency fingerprints used by the entity's claims."""

    @abstractmethod
    def presentation(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        """Return non-publishing presentation data from validated evidence."""

    @abstractmethod
    def graph(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        """Return the complete validated generalized graph."""


class EvidenceAdapterRegistry:
    """Small typed registry; registering a new domain does not modify core routing."""

    def __init__(self, adapters: Iterable[EvidenceDomainAdapter] = ()) -> None:
        self._adapters: dict[str, EvidenceDomainAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: EvidenceDomainAdapter) -> None:
        entity_type = adapter.entity_type.strip().casefold()
        if not entity_type:
            raise ValueError("Cannot register adapter without entity_type")
        if entity_type in self._adapters:
            raise ValueError(f"Adapter already registered for entity type: {entity_type}")
        self._adapters[entity_type] = adapter

    def get(self, entity_type: str) -> EvidenceDomainAdapter:
        key = str(entity_type or "").strip().casefold()
        adapter = self._adapters.get(key)
        if adapter is None:
            raise KeyError(f"No evidence adapter registered for entity type: {entity_type}")
        return adapter

    def entity_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def graph(self, entity_type: str, identity: object, **kwargs: Any) -> dict[str, Any]:
        payload = self.get(entity_type).graph(identity, **kwargs)
        errors = validate_generalized_graph(payload)
        if errors:
            raise ValueError(f"Adapter returned invalid generalized graph: {errors}")
        return payload
