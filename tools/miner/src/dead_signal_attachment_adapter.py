"""Typed Attachment adapter for the generalized Dead Signal Evidence Graph.

Attachment identity and presentation come from the Miner's source-derived
published contracts. Compatibility is recomputed with the same shared four-state
policy used by weapon projection, then compared against the inverted weapon-side
relationship lists. Disagreement is a conflict; named-model spelling is never a
join key.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from dead_signal_attachment_relations import (
    FOUR_STATE_RELATIONSHIPS,
    attachment_weapon_relation,
    invert_weapon_attachment_states,
)
from dead_signal_domain_adapters import AdapterContract, EvidenceDomainAdapter
from dead_signal_evidence_contracts import (
    ASSESSMENT_SCHEMA_VERSION,
    CLAIM_SCHEMA_VERSION,
    EDGE_SCHEMA_VERSION,
    ENTITY_SCHEMA_VERSION,
    EVIDENCE_STATES,
    GENERAL_SCHEMA,
    GENERAL_SCHEMA_VERSION,
    dependency_fingerprint,
    validate_generalized_graph,
)


ATTACHMENT_TYPES = {"Sight", "Muzzle", "Tactical", "Magazine"}

ATTACHMENT_CONTRACT = AdapterContract(
    entity_type="attachment",
    identity_seeds=("attachment_id", "accessory_id", "item_id"),
    canonical_owner_tables=(
        "published/web/attachments.json",
        "game_common/data/gun_accessory_item_to_accessory_map_data.json",
        "game_common/data/gun_accessory_base_params_data.json",
        "game_common/data/item_data.json",
        "game_common/data/gun_accessory_attr_data.json",
    ),
    allowed_outbound_fields=(
        "item_id",
        "attachment_id",
        "accessory_id",
        "accessory_code",
        "affix_code",
        "passive_buff_id",
        "weapon_type_list",
        "gun_type_list",
        "weapon_item_no_list",
        "gun_no_list",
        "image_reference",
    ),
    typed_destination_tables=(
        ("attachment_id", ("game_common/data/gun_accessory_base_params_data.json",)),
        ("accessory_id", ("game_common/data/gun_accessory_base_params_data.json",)),
        ("item_id", ("game_common/data/item_data.json", "game_common/data/gun_accessory_item_to_accessory_map_data.json")),
    ),
    collision_prone_fields=("attachment_id", "accessory_id", "item_id"),
    blocked_generic_fields=("id", "no", "code", "record_id"),
    terminal_presentation_fields=(
        "name", "attachment_type", "rarity", "description", "effects",
        "gain_path", "image_reference",
    ),
    supported_claims=(
        "attachment.exact_identity",
        "attachment.accessory_owner",
        "attachment.slot_type",
        "attachment.weapon_relationship",
        "attachment.compatibility_consistency",
        "attachment.stat_modifiers",
        "attachment.acquisition",
        "attachment.artwork",
    ),
    applicability_rules=(
        "attachment identity must resolve to one exact published canonical identity",
        "weapon compatibility uses structured installed-game scope or exact typed weapon item IDs only",
        "named-model spelling is discovery text only and never establishes a relationship",
        "forward and reverse compatibility disagreement is CONFLICT",
        "missing stat, acquisition, or artwork evidence remains UNRESOLVED",
    ),
)


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Attachment adapter could not read {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Attachment adapter expected an object: {path}")
    return value


def _records(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [row for row in payload.get(key, []) if isinstance(row, dict)]


def _claim(
    claim_type: str,
    canonical_id: str,
    result: str,
    *,
    evidence: list[Any] | None = None,
    missing: list[Any] | None = None,
    conflicts: list[Any] | None = None,
    dependencies: list[str] | None = None,
    requirements: list[Any] | None = None,
    relationship: dict[str, Any] | None = None,
) -> dict[str, Any]:
    subject = {"entity_type": "attachment", "canonical_id": canonical_id}
    if relationship:
        subject["relationship"] = relationship
    return {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "claim_type": claim_type,
        "subject": subject,
        "result": result,
        "requirements": requirements or ["exact typed evidence"],
        "evidence": evidence or [],
        "missing": missing or [],
        "conflicts": conflicts or [],
        "dependencies": dependencies or [],
    }


def _edge(
    canonical_id: str,
    destination: str,
    relationship_type: str,
    *,
    source_table: str,
    source_record: object,
    selector: str,
    layer: str,
    authority: str,
    state: str,
) -> dict[str, Any]:
    source = f"attachment:{canonical_id}"
    fingerprint = dependency_fingerprint(
        source, destination, relationship_type, source_table, source_record,
        selector, layer, authority,
    )
    return {
        "schema_version": EDGE_SCHEMA_VERSION,
        "source": source,
        "destination": destination,
        "relationship_type": relationship_type,
        "source_table": source_table,
        "source_record": str(source_record),
        "selector": selector,
        "layer": layer,
        "authority": authority,
        "state": state,
        "dependency_fingerprint": fingerprint,
    }


def _assessment(claims: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(row.get("result") or "UNRESOLVED") for row in claims)
    conflicts = [row["claim_type"] for row in claims if row.get("result") == "CONFLICT"]
    missing = [row["claim_type"] for row in claims if row.get("result") in {"PARTIAL", "UNRESOLVED"}]
    if conflicts:
        result = "CONFLICT"
    elif missing and any(row.get("result") == "PROVEN" for row in claims):
        result = "PARTIAL"
    elif missing:
        result = "UNRESOLVED"
    else:
        result = "PROVEN"
    return {
        "schema_version": ASSESSMENT_SCHEMA_VERSION,
        "result": result,
        "claim_counts": {state: counts.get(state, 0) for state in EVIDENCE_STATES},
        "missing": missing,
        "conflicts": conflicts,
    }


class AttachmentAdapter(EvidenceDomainAdapter):
    contract = ATTACHMENT_CONTRACT

    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        super().__init__()

    def _published(self) -> Path:
        state_path = self.output / "last-run.json"
        if not state_path.is_file():
            raise ValueError("Attachment adapter requires a completed Miner output with last-run.json")
        state = _read(state_path)
        published = Path(state.get("published") or self.output / "published")
        if not published.is_absolute():
            published = self.output / published
        published = published.resolve()
        try:
            published.relative_to(self.output)
        except ValueError as exc:
            raise ValueError("Attachment published source must stay inside the Miner output folder") from exc
        return published

    def _sources(self) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
        published = self._published()
        web = _read(published / "web" / "attachments.json")
        data_attachments = _read(published / "data" / "attachments.json")
        data_weapons = _read(published / "data" / "weapons.json")
        return published, web, data_attachments, data_weapons

    @staticmethod
    def _match(identity: object, rows: list[dict[str, Any]]) -> dict[str, Any]:
        needle = str(identity or "").strip()
        if not needle:
            raise KeyError("Attachment identity is empty")
        matches = []
        for row in rows:
            aliases = {
                str(row.get("canonical_id") or ""),
                str(row.get("accessory_code") or row.get("id") or ""),
                str(row.get("item_id") or ""),
            }
            if needle in aliases:
                matches.append(row)
        if not matches:
            raise KeyError(f"Unknown exact attachment identity: {identity}")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous exact attachment identity: {identity}")
        return matches[0]

    @staticmethod
    def _data_match(web_row: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
        code = str(web_row.get("accessory_code") or web_row.get("id") or "")
        item = str(web_row.get("item_id") or "")
        exact = [
            row for row in rows
            if str(row.get("accessory_code") or row.get("id") or "") == code
            and (not item or str(row.get("item_id") or "") == item)
        ]
        if len(exact) != 1:
            raise ValueError(f"Attachment normalized owner must resolve exactly once: {code}")
        return exact[0]

    def graph(self, identity: object, **_: Any) -> dict[str, Any]:
        _published, web_payload, data_attachment_payload, weapon_payload = self._sources()
        web_row = self._match(identity, _records(web_payload, "attachments"))
        data_row = self._data_match(web_row, _records(data_attachment_payload, "attachments"))
        weapons = _records(weapon_payload, "weapons")

        canonical_id = str(web_row.get("canonical_id") or "")
        accessory_code = str(web_row.get("accessory_code") or web_row.get("id") or "")
        item_id = data_row.get("item_id") or web_row.get("item_id")
        if not canonical_id or not accessory_code or item_id in (None, ""):
            raise ValueError("Attachment identity is missing canonical/accessory/item provenance")

        entity = {
            "schema_version": ENTITY_SCHEMA_VERSION,
            "entity_type": "attachment",
            "canonical_id": canonical_id,
            "name": str(web_row.get("name") or "Unknown Attachment"),
            "classification": str(web_row.get("attachment_type") or "attachment"),
            "identity_state": "PROVEN",
            "source_records": [
                {
                    "table": "published/web/attachments.json",
                    "record_id": canonical_id,
                    "layer": "published-snapshot",
                },
                {
                    "table": "game_common/data/gun_accessory_item_to_accessory_map_data.json",
                    "record_id": str(item_id),
                    "layer": "base-current-merged",
                },
                {
                    "table": "game_common/data/gun_accessory_base_params_data.json",
                    "record_id": accessory_code,
                    "layer": "base-current-merged",
                },
            ],
        }

        claims: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        identity_evidence = {
            "canonical_id": canonical_id,
            "accessory_code": accessory_code,
            "item_id": item_id,
            "source": "published/web/attachments.json",
        }
        claims.append(_claim(
            "attachment.exact_identity", canonical_id, "PROVEN",
            evidence=[identity_evidence],
            dependencies=["published/web/attachments.json"],
            requirements=["one canonical attachment", "one accessory code", "one item owner"],
        ))
        edges.append(_edge(
            canonical_id, f"item:{item_id}", "attachment-item-owner",
            source_table="game_common/data/gun_accessory_item_to_accessory_map_data.json",
            source_record=item_id,
            selector="/accessory_no|accessory_id",
            layer="base-current-merged",
            authority="normalized-exact-item-accessory-map",
            state="PROVEN",
        ))

        owner_trace = (data_row.get("compatibility_evidence") or {}).get("owner_trace") or {}
        owner_state = str(owner_trace.get("state") or "")
        owner_proven = owner_state in {"direct-installed-text-owner", "exact-typed-selector-owner"}
        if owner_proven:
            claims.append(_claim(
                "attachment.accessory_owner", canonical_id, "PROVEN",
                evidence=[owner_trace],
                dependencies=[str(owner_trace.get("source_table") or "game_common/data/gun_accessory_base_params_data.json")],
                requirements=["exact accessory owner record"],
            ))
        else:
            claims.append(_claim(
                "attachment.accessory_owner", canonical_id, "UNRESOLVED",
                evidence=[owner_trace] if owner_trace else [],
                missing=["typed compatibility selector owner"],
                dependencies=["game_common/data/gun_accessory_base_params_data.json"],
                requirements=["exact accessory owner record", "typed compatibility selector or direct installed wording"],
            ))

        slot = str(data_row.get("attachment_type") or web_row.get("attachment_type") or "")
        if slot in ATTACHMENT_TYPES:
            slot_evidence = {"attachment_type": slot, "item_id": item_id, "subtype_code": data_row.get("subtype_code")}
            claims.append(_claim(
                "attachment.slot_type", canonical_id, "PROVEN",
                evidence=[slot_evidence],
                dependencies=["game_common/data/item_data.json"],
                requirements=["player attachment subtype maps to a supported slot"],
            ))
            edges.append(_edge(
                canonical_id, f"slot:{slot}", "attachment-slot-type",
                source_table="game_common/data/item_data.json",
                source_record=item_id,
                selector="/sub_type",
                layer="base-current-merged",
                authority="normalized-item-subtype-slot-map",
                state="PROVEN",
            ))
        else:
            claims.append(_claim(
                "attachment.slot_type", canonical_id, "UNRESOLVED",
                missing=["supported player attachment slot"],
                dependencies=["game_common/data/item_data.json"],
                requirements=["Sight, Muzzle, Tactical, or Magazine subtype"],
            ))

        direct_by_weapon: dict[str, str] = {}
        for weapon in weapons:
            weapon_id = str(weapon.get("canonical_id") or weapon.get("blueprint_id") or weapon.get("item_id") or "")
            if weapon_id:
                direct_by_weapon[weapon_id] = attachment_weapon_relation(weapon, data_row)
        reverse = invert_weapon_attachment_states(weapons, accessory_code)
        reverse_by_weapon: dict[str, list[str]] = {}
        for state, weapon_ids in reverse.items():
            for weapon_id in weapon_ids:
                reverse_by_weapon.setdefault(weapon_id, []).append(state)

        relationship_conflicts = []
        for weapon in weapons:
            weapon_id = str(weapon.get("canonical_id") or weapon.get("blueprint_id") or weapon.get("item_id") or "")
            if not weapon_id:
                continue
            forward_state = direct_by_weapon[weapon_id]
            reverse_states = reverse_by_weapon.get(weapon_id, [])
            reverse_state = reverse_states[0] if len(reverse_states) == 1 else None
            if reverse_state != forward_state:
                relationship_conflicts.append({
                    "weapon": weapon_id,
                    "forward": forward_state,
                    "reverse": reverse_states or ["missing"],
                })
                result = "CONFLICT"
                conflicts = [relationship_conflicts[-1]]
                evidence = []
                edge_state = "CONFLICT"
            else:
                result = "NOT APPLICABLE" if forward_state == "not-applicable" else "UNRESOLVED" if forward_state == "unresolved" else "PROVEN"
                conflicts = []
                evidence = [{"forward": forward_state, "reverse": reverse_state}]
                edge_state = result
            claims.append(_claim(
                "attachment.weapon_relationship", canonical_id, result,
                evidence=evidence,
                missing=["typed compatibility owner"] if result == "UNRESOLVED" else [],
                conflicts=conflicts,
                dependencies=["published/data/weapons.json", "published/data/attachments.json"],
                requirements=["shared four-state policy", "weapon-side reverse state agrees"],
                relationship={"weapon": weapon_id, "state": forward_state},
            ))
            edges.append(_edge(
                canonical_id, f"weapon:{weapon_id}", f"attachment-{forward_state}-weapon",
                source_table="published/data/weapons.json",
                source_record=weapon_id,
                selector=f"/compatibility/attachment/{forward_state.replace('-', '_')}_ids",
                layer="published-snapshot",
                authority="shared-four-state-attachment-policy",
                state=edge_state,
            ))

        if relationship_conflicts:
            claims.append(_claim(
                "attachment.compatibility_consistency", canonical_id, "CONFLICT",
                conflicts=relationship_conflicts,
                dependencies=["published/data/weapons.json", "published/data/attachments.json"],
                requirements=["all forward and reverse weapon relationships agree exactly"],
            ))
        elif weapons:
            claims.append(_claim(
                "attachment.compatibility_consistency", canonical_id, "PROVEN",
                evidence=[{"weapons_checked": len(direct_by_weapon), "states": list(FOUR_STATE_RELATIONSHIPS)}],
                dependencies=["published/data/weapons.json", "published/data/attachments.json"],
                requirements=["all forward and reverse weapon relationships agree exactly"],
            ))
        else:
            claims.append(_claim(
                "attachment.compatibility_consistency", canonical_id, "UNRESOLVED",
                missing=["weapon corpus"],
                dependencies=["published/data/weapons.json"],
                requirements=["weapon corpus available for bidirectional comparison"],
            ))

        modifier_evidence = {
            "effects": data_row.get("effects"),
            "attribute_codes": data_row.get("attribute_codes") or [],
            "passive_buff_id": data_row.get("passive_buff_id"),
            "affix_code": data_row.get("affix_code"),
        }
        if modifier_evidence["effects"] or modifier_evidence["attribute_codes"] or modifier_evidence["passive_buff_id"]:
            claims.append(_claim(
                "attachment.stat_modifiers", canonical_id, "PROVEN",
                evidence=[modifier_evidence],
                dependencies=["game_common/data/gun_accessory_attr_data.json"],
                requirements=["exact attachment affix owner exposes modifier evidence"],
            ))
        else:
            claims.append(_claim(
                "attachment.stat_modifiers", canonical_id, "UNRESOLVED",
                missing=["attachment modifier evidence"],
                dependencies=["game_common/data/gun_accessory_attr_data.json"],
                requirements=["exact attachment affix owner exposes modifier evidence"],
            ))

        gain_path = str(data_row.get("gain_path") or web_row.get("gain_path") or "").strip()
        if gain_path:
            claims.append(_claim(
                "attachment.acquisition", canonical_id, "PROVEN",
                evidence=[{"gain_path": gain_path}],
                dependencies=["game_common/data/item_data.json"],
                requirements=["localized installed-game gain path"],
            ))
        else:
            claims.append(_claim(
                "attachment.acquisition", canonical_id, "UNRESOLVED",
                missing=["localized gain path"],
                dependencies=["game_common/data/item_data.json"],
                requirements=["localized installed-game gain path"],
            ))

        artwork = str(data_row.get("image_reference") or web_row.get("image_reference") or "").strip()
        if artwork:
            claims.append(_claim(
                "attachment.artwork", canonical_id, "PROVEN",
                evidence=[{"image_reference": artwork}],
                dependencies=["game_common/data/item_data.json", "game_common/data/gun_accessory_base_params_data.json"],
                requirements=["source-derived image reference"],
            ))
        else:
            claims.append(_claim(
                "attachment.artwork", canonical_id, "UNRESOLVED",
                missing=["source-derived image reference"],
                dependencies=["game_common/data/item_data.json", "game_common/data/gun_accessory_base_params_data.json"],
                requirements=["source-derived image reference"],
            ))

        payload = {
            "schema": GENERAL_SCHEMA,
            "schema_version": GENERAL_SCHEMA_VERSION,
            "brand": "Dead Signal",
            "entity": entity,
            "claims": claims,
            "edges": edges,
            "assessment": _assessment(claims),
            "compatibility": {
                "phase": 4,
                "four_state_relationships": list(FOUR_STATE_RELATIONSHIPS),
                "forward_reverse_agreement": not relationship_conflicts,
                "relationship_conflicts": relationship_conflicts,
                "publication_authority": False,
            },
        }
        errors = validate_generalized_graph(payload)
        if errors:
            raise ValueError(f"Attachment adapter produced invalid graph: {errors}")
        return payload

    def identify(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        return self.graph(identity, **kwargs)["entity"]

    def claims(self, identity: object, **kwargs: Any) -> list[dict[str, Any]]:
        return self.graph(identity, **kwargs)["claims"]

    def resolve_claim(self, identity: object, claim_type: str, **kwargs: Any) -> dict[str, Any]:
        requested = str(claim_type or "").strip()
        if requested not in self.contract.supported_claims:
            raise KeyError(f"Unsupported attachment claim: {claim_type}")
        matches = [row for row in self.claims(identity, **kwargs) if row.get("claim_type") == requested]
        if not matches:
            raise KeyError(f"No attachment claim resolved for: {claim_type}")
        if len(matches) == 1:
            return matches[0]
        counts = Counter(str(row.get("result")) for row in matches)
        result = "CONFLICT" if counts["CONFLICT"] else "PARTIAL" if counts["UNRESOLVED"] or counts["PARTIAL"] else "PROVEN"
        return {"claim_type": requested, "result": result, "claims": matches}

    def dependencies(self, identity: object, **kwargs: Any) -> list[str]:
        return sorted({
            dependency
            for claim in self.claims(identity, **kwargs)
            for dependency in claim.get("dependencies", [])
            if str(dependency or "").strip()
        })

    def presentation(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        graph = self.graph(identity, **kwargs)
        entity = graph["entity"]
        compatibility = graph["compatibility"]
        return {
            "entity_type": "attachment",
            "canonical_id": entity["canonical_id"],
            "name": entity["name"],
            "classification": entity["classification"],
            "identity_state": entity["identity_state"],
            "assessment": graph["assessment"]["result"],
            "forward_reverse_agreement": compatibility["forward_reverse_agreement"],
            "publication_authority": False,
        }
