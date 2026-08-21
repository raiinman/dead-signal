"""Phase 14 fail-closed publication contracts for generalized Evidence Graph claims.

Publication is a separate decision from deterministic proof.  This module consumes
lean claim results only; it never mines, discovers, mutates graph truth, or publishes
by itself.  Every evidence-backed website field must be explicitly registered.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterable

ALLOWED_STATES = {"PROVEN", "PARTIAL", "UNRESOLVED", "NOT APPLICABLE", "CONFLICT"}
BLOCKED_STATES = {"PARTIAL", "UNRESOLVED", "CONFLICT"}


@dataclass(frozen=True)
class PublicationFieldContract:
    field: str
    claim_type: str
    minimum_state: str = "PROVEN"
    required_evidence: tuple[str, ...] = ()
    conflict_policy: str = "block"
    absence_policy: str = "omit"
    not_applicable_policy: str = "explicit"
    projection: str = "claim-evidence"

    def validate(self) -> "PublicationFieldContract":
        if not self.field or not self.claim_type:
            raise ValueError("Publication field contracts require field and claim_type")
        if self.minimum_state not in {"PROVEN", "NOT APPLICABLE"}:
            raise ValueError("Publication minimum_state must be PROVEN or NOT APPLICABLE")
        if self.conflict_policy != "block":
            raise ValueError("Phase 14 conflict policy is fail-closed: block")
        if self.absence_policy not in {"omit", "block"}:
            raise ValueError("Unknown publication absence policy")
        if self.not_applicable_policy not in {"explicit", "omit", "block"}:
            raise ValueError("Unknown NOT APPLICABLE publication policy")
        return self


# These are evidence-backed website fields. Presentation-only family labels and
# canonical IDs remain source projections, but any field claiming game semantics
# must pass one of these contracts before a claim-backed projector may emit it.
FIELD_CONTRACTS = tuple(contract.validate() for contract in (
    PublicationFieldContract("weapon.description", "weapon.description", required_evidence=("exact player-facing description owner",)),
    PublicationFieldContract("weapon.special_skill", "weapon.effect_resolution", required_evidence=("exact fixed skill/effect owner",)),
    PublicationFieldContract("attachment.slot_type", "attachment.slot_type", required_evidence=("player attachment subtype maps to a supported slot",)),
    PublicationFieldContract("attachment.weapon_relationship", "attachment.weapon_relationship", required_evidence=("shared four-state policy", "weapon-side reverse state agrees"), not_applicable_policy="explicit"),
    PublicationFieldContract("attachment.stat_modifiers", "attachment.stat_modifiers", required_evidence=("exact attribute or buff owner",)),
    PublicationFieldContract("attachment.acquisition", "attachment.acquisition", required_evidence=("exact acquisition owner",)),
    PublicationFieldContract("attachment.artwork", "attachment.artwork", required_evidence=("exact artwork reference",)),
    PublicationFieldContract("calibration.style_owner", "calibration.style_owner", required_evidence=("exact current Calibration Blueprint owner",)),
    PublicationFieldContract("calibration.weapon_relationship", "calibration.weapon_relationship", required_evidence=("typed weapon selector", "weapon-side reverse state agrees"), not_applicable_policy="explicit"),
    PublicationFieldContract("calibration.rarity", "calibration.rarity", required_evidence=("exact item quality owner",)),
    PublicationFieldContract("calibration.attack_range", "calibration.attack_range", required_evidence=("exact affix_val_range owner",)),
    PublicationFieldContract("calibration.secondary_attributes", "calibration.secondary_attributes", required_evidence=("exact affix pool owner",)),
    PublicationFieldContract("armor.slot", "armor.slot", required_evidence=("exact equipment owner",)),
    PublicationFieldContract("armor.rarity", "armor.rarity", required_evidence=("exact item/equipment quality owner",)),
    PublicationFieldContract("armor.base_attributes", "armor.base_attributes", required_evidence=("exact tier attribute owner",)),
    PublicationFieldContract("armor.set_membership", "armor.set_membership", required_evidence=("exact suit and equipment owner",), not_applicable_policy="explicit"),
    PublicationFieldContract("armor.crafting", "armor.crafting", required_evidence=("exact forge owner",)),
    PublicationFieldContract("armor.acquisition", "armor.acquisition", required_evidence=("exact acquisition owner",)),
    PublicationFieldContract("armor.artwork", "armor.artwork", required_evidence=("exact artwork reference",)),
    PublicationFieldContract("armor_set.pieces", "armor_set.pieces", required_evidence=("exact equipment membership owners",)),
    PublicationFieldContract("armor_set.activation_thresholds", "armor_set.activation_thresholds", required_evidence=("exact activation threshold owner",)),
    PublicationFieldContract("armor_set.bonuses", "armor_set.bonuses", required_evidence=("exact attribute or buff owner",)),
    PublicationFieldContract("mod.slot_compatibility", "mod.slot_compatibility", required_evidence=("exact apply_range owner",)),
    PublicationFieldContract("mod.main_attribute", "mod.main_attribute", required_evidence=("exact main-entry owner",)),
    PublicationFieldContract("mod.fixed_sub_attributes", "mod.fixed_sub_attributes", required_evidence=("exact frame/sub-entry owner",)),
    PublicationFieldContract("mod.levels", "mod.levels", required_evidence=("exact level entry rows",)),
    PublicationFieldContract("mod.shiny", "mod.shiny", required_evidence=("exact Shiny buff/replacement owner",), not_applicable_policy="explicit"),
    PublicationFieldContract("mod.frame_family", "mod.frame_family", required_evidence=("exact frame owner",)),
    PublicationFieldContract("mod.acquisition", "mod.acquisition", required_evidence=("exact acquisition owner",)),
    PublicationFieldContract("mod.effect", "mod.effect", required_evidence=("exact attribute or buff owner",)),
    PublicationFieldContract("cradle.effect", "cradle.effect", required_evidence=("exact effect owner",)),
    PublicationFieldContract("cradle.weapon_relationship", "cradle.weapon_relationship", required_evidence=("exact applicability selector", "weapon-side reverse state agrees"), not_applicable_policy="explicit"),
    PublicationFieldContract("cradle.scenario_availability", "cradle.scenario_availability", required_evidence=("exact scenario activation owner",)),
    PublicationFieldContract("cradle.artwork", "cradle.artwork", required_evidence=("exact artwork reference",)),
    PublicationFieldContract("recipe.output", "recipe.output", required_evidence=("exact forge output owner",)),
    PublicationFieldContract("recipe.materials", "recipe.materials", required_evidence=("typed fixed/choice material owners",)),
    PublicationFieldContract("recipe.currency", "recipe.currency", required_evidence=("exact currency owner",)),
    PublicationFieldContract("recipe.station", "recipe.station", required_evidence=("exact station owner",)),
    PublicationFieldContract("material.used_by", "material.used_by", required_evidence=("exact reverse recipe usage",)),
    PublicationFieldContract("material.acquisition", "material.acquisition", required_evidence=("exact acquisition owner",)),
    PublicationFieldContract("deviation.skills", "deviation.skills", required_evidence=("exact deviation skill owner",)),
    PublicationFieldContract("deviation.power_mood", "deviation.power_mood", required_evidence=("exact power/mood source owner",)),
    PublicationFieldContract("deviation.acquisition", "deviation.acquisition", required_evidence=("exact acquisition owner",)),
    PublicationFieldContract("deviation.scenario_availability", "deviation.scenario_availability", required_evidence=("exact scenario activation owner",)),
    PublicationFieldContract("deviation.artwork", "deviation.artwork", required_evidence=("exact artwork reference",)),
))

CONTRACT_BY_FIELD = {contract.field: contract for contract in FIELD_CONTRACTS}
if len(CONTRACT_BY_FIELD) != len(FIELD_CONTRACTS):
    raise ValueError("Duplicate publication field contract")


def lean_claim(claim: dict[str, Any]) -> dict[str, Any]:
    """Strip research graph bulk before a publication decision is made."""
    return {
        "claim_type": str(claim.get("claim_type") or ""),
        "result": str(claim.get("result") or "UNRESOLVED").upper(),
        "requirements": [str(v) for v in claim.get("requirements", []) if str(v or "").strip()],
        "evidence": list(claim.get("evidence", []) or []),
        "missing": [str(v) for v in claim.get("missing", []) if str(v or "").strip()],
        "conflicts": list(claim.get("conflicts", []) or []),
        "dependencies": [str(v) for v in claim.get("dependencies", []) if str(v or "").strip()],
    }


def _requirements_satisfied(contract: PublicationFieldContract, claim: dict[str, Any]) -> tuple[bool, list[str]]:
    declared = set(str(v) for v in claim.get("requirements", []) or [])
    missing = [value for value in contract.required_evidence if value not in declared]
    return not missing, missing


def publication_decision(field: str, claim: dict[str, Any] | None) -> dict[str, Any]:
    """Return an explicit fail-closed field decision. Never assigns proof."""
    contract = CONTRACT_BY_FIELD.get(str(field))
    if contract is None:
        return {"field": str(field), "decision": "BLOCKED", "publishable": False, "blockers": ["unregistered-publication-field"], "contract": None}
    if claim is None:
        return {"field": field, "decision": "OMIT" if contract.absence_policy == "omit" else "BLOCKED", "publishable": False, "blockers": ["claim-absent"], "contract": asdict(contract)}
    lean = lean_claim(claim)
    state = lean["result"]
    blockers: list[str] = []
    if lean["claim_type"] != contract.claim_type:
        blockers.append("wrong-claim-type")
    if state not in ALLOWED_STATES:
        blockers.append("unknown-claim-state")
    if state in BLOCKED_STATES:
        blockers.append(f"state-{state.casefold().replace(' ', '-')}-cannot-publish")
    if lean["conflicts"]:
        blockers.append("conflicting-evidence")
    if lean["missing"]:
        blockers.append("claim-has-missing-requirements")
    requirements_ok, missing_contract_requirements = _requirements_satisfied(contract, lean)
    if not requirements_ok:
        blockers.extend(f"contract-requirement-not-declared:{value}" for value in missing_contract_requirements)
    if state == "NOT APPLICABLE":
        if contract.not_applicable_policy == "block":
            blockers.append("not-applicable-blocked-by-policy")
        decision = "NOT APPLICABLE" if not blockers and contract.not_applicable_policy == "explicit" else "OMIT" if not blockers else "BLOCKED"
        publishable = not blockers and contract.not_applicable_policy == "explicit"
    else:
        if state != contract.minimum_state:
            blockers.append(f"minimum-state-{contract.minimum_state}-required")
        publishable = not blockers
        decision = "PUBLISHABLE" if publishable else "BLOCKED"
    return {
        "field": field,
        "claim_type": lean["claim_type"],
        "claim_state": state,
        "publishable": publishable,
        "decision": decision,
        "blockers": sorted(set(blockers)),
        "contract": asdict(contract),
        "provenance": {"dependencies": lean["dependencies"], "evidence": lean["evidence"]},
    }


def project_field(field: str, claim: dict[str, Any] | None, value: Any,
                  *, projector: Callable[[Any], Any] | None = None) -> dict[str, Any]:
    """Project one lean field value only when its registered contract permits it."""
    decision = publication_decision(field, claim)
    projected = None
    if decision["publishable"]:
        projected = projector(value) if projector else value
    return {"field": field, "value": projected, "publication": decision}


def contract_manifest() -> dict[str, Any]:
    return {
        "schema": "dead-signal-publication-field-contracts",
        "schema_version": 1,
        "field_count": len(FIELD_CONTRACTS),
        "fields": [asdict(contract) for contract in FIELD_CONTRACTS],
        "policy": {
            "proof_is_not_publication": True,
            "partial_unresolved_conflict_publish_silently": False,
            "not_applicable_is_missing": False,
            "unregistered_field_policy": "block",
            "projector_input": "lean-claim-result-only",
        },
    }


def audit_projection(fields: Iterable[tuple[str, dict[str, Any] | None, Any]]) -> dict[str, Any]:
    rows = [project_field(field, claim, value) for field, claim, value in fields]
    return {
        "schema": "dead-signal-publication-projection-audit",
        "schema_version": 1,
        "record_counts": {
            "fields": len(rows),
            "publishable": sum(bool(row["publication"].get("publishable")) for row in rows),
            "blocked": sum(row["publication"].get("decision") == "BLOCKED" for row in rows),
            "omitted": sum(row["publication"].get("decision") == "OMIT" for row in rows),
            "not_applicable": sum(row["publication"].get("decision") == "NOT APPLICABLE" for row in rows),
        },
        "fields": rows,
    }
