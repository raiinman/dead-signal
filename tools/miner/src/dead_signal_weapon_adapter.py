"""Weapons v1 adapter for the generalized Evidence Graph.

This is the Phase-2 reference adapter. It consumes the protected legacy weapon
trace and Phase-1 projection without changing either contract.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from dead_signal_domain_adapters import AdapterContract, EvidenceDomainAdapter
from dead_signal_evidence_contracts import project_legacy_weapon_graph, validate_generalized_graph
from dead_signal_evidence_graph import DeadSignalEvidenceGraph


WEAPON_CONTRACT = AdapterContract(
    entity_type="weapon",
    identity_seeds=(
        "blueprint_id",
        "item_id",
        "prototype_id",
        "fragment_id",
        "bullet_pattern_id",
        "tier_item_id",
        "gun_no",
        "fixed_skill_code",
    ),
    canonical_owner_tables=(
        "published/web/weapons.json",
        "game_common/data/gun_blueprint_data.json",
        "game_common/data/item_data.json",
        "game_common/data/weapon_prototype_data.json",
    ),
    allowed_outbound_fields=(
        "blueprint_id",
        "item_id",
        "prototype_id",
        "fragment_id",
        "bullet_pattern_id",
        "tier_item_id",
        "gun_no",
        "fixed_skill_code",
        "buff_id",
        "forge_id",
        "recipe_id",
        "material_id",
        "attachment_id",
        "accessory_id",
        "translation_handle",
        "raw_handle",
    ),
    typed_destination_tables=(
        ("prototype_id", ("game_common/data/weapon_prototype_data.json",)),
        ("gun_no", ("game_common/data/equip_data.json",)),
        ("fixed_skill_code", ("game_common/data/passive_skill_data.json", "game_common/data/gun_blueprint_attr_data.json")),
    ),
    collision_prone_fields=("prototype_id", "gun_no", "fixed_skill_code"),
    blocked_generic_fields=("id", "no", "code", "record_id"),
    terminal_presentation_fields=("name", "category", "rarity", "prototype_desc"),
    supported_claims=("weapon.exact_identity", "weapon.exact_occurrence"),
    applicability_rules=(
        "weapon identity must resolve through the protected Weapons v1 corpus",
        "missing evidence remains unresolved",
        "not-applicable is explicit and never inferred from absence",
    ),
)


class WeaponAdapter(EvidenceDomainAdapter):
    contract = WEAPON_CONTRACT

    def __init__(self, output: Path | str):
        self.output = Path(output)
        self._legacy: DeadSignalEvidenceGraph | None = None
        super().__init__()

    @property
    def legacy(self) -> DeadSignalEvidenceGraph:
        """Initialize the heavyweight Weapons v1 research graph only on demand.

        Registry construction and non-weapon domain work must not require a
        complete Base/Current research snapshot merely because the Weapon adapter
        is registered beside another adapter.
        """
        if self._legacy is None:
            self._legacy = DeadSignalEvidenceGraph(self.output)
        return self._legacy

    def graph(
        self,
        identity: object,
        *,
        max_occurrences_per_id: int = 80,
        **_: Any,
    ) -> dict[str, Any]:
        legacy = self.legacy.weapon_graph(
            identity,
            max_occurrences_per_id=max_occurrences_per_id,
        )
        payload = project_legacy_weapon_graph(legacy)
        errors = validate_generalized_graph(payload)
        if errors:
            raise ValueError(f"Weapon adapter produced invalid graph: {errors}")
        return payload

    def identify(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        return self.graph(identity, **kwargs)["entity"]

    def claims(self, identity: object, **kwargs: Any) -> list[dict[str, Any]]:
        return self.graph(identity, **kwargs)["claims"]

    def resolve_claim(self, identity: object, claim_type: str, **kwargs: Any) -> dict[str, Any]:
        requested = str(claim_type or "").strip()
        if requested not in self.contract.supported_claims:
            raise KeyError(f"Unsupported weapon claim: {claim_type}")
        matches = [claim for claim in self.claims(identity, **kwargs) if claim.get("claim_type") == requested]
        if not matches:
            raise KeyError(f"No weapon claim resolved for: {claim_type}")
        if len(matches) > 1:
            return {
                "claim_type": requested,
                "result": "PROVEN" if all(row.get("result") == "PROVEN" for row in matches) else "PARTIAL",
                "claims": matches,
            }
        return matches[0]

    def dependencies(self, identity: object, **kwargs: Any) -> list[str]:
        values = {
            dependency
            for claim in self.claims(identity, **kwargs)
            for dependency in claim.get("dependencies", [])
            if str(dependency or "").strip()
        }
        return sorted(values)

    def presentation(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        graph = self.graph(identity, **kwargs)
        entity = graph["entity"]
        assessment = graph["assessment"]
        return {
            "entity_type": entity["entity_type"],
            "canonical_id": entity["canonical_id"],
            "name": entity["name"],
            "classification": entity["classification"],
            "identity_state": entity["identity_state"],
            "assessment": assessment["result"],
            "claim_counts": assessment["claim_counts"],
            "publication_authority": False,
        }
