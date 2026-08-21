"""Typed Armor Piece and Armor Set adapters for the generalized Evidence Graph.

Phase 6 keeps piece identity separate from set identity, preserves suit-qualified
piece canonical IDs when blueprint IDs are reused, and treats Key Armor as an
explicit standalone armor classification rather than forcing it into a set.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

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

EQUIP_TABLE = "game_common/data/equip_data.json"
ITEM_TABLE = "game_common/data/item_data.json"
ORIGIN_TABLE = "game_common/data/equip_origin_data.json"
SUIT_TABLE = "game_common/data/suit_data.json"
BLUEPRINT_ATTR_TABLE = "game_common/data/equip_blueprint_attr_data.json"
PASSIVE_TABLE = "game_common/data/passive_skill_data.json"
BUFF_TABLE = "game_common/data/buff_level_data.json"
FORGE_TABLE = "game_common/data/forge_data.json"

ARMOR_CONTRACT = AdapterContract(
    entity_type="armor",
    identity_seeds=("canonical_id", "blueprint_id", "item_id"),
    canonical_owner_tables=(
        "published/web/armor.json", EQUIP_TABLE, ITEM_TABLE, ORIGIN_TABLE,
        BLUEPRINT_ATTR_TABLE, PASSIVE_TABLE, BUFF_TABLE, FORGE_TABLE,
    ),
    allowed_outbound_fields=(
        "blueprint_id", "item_id", "suit_id", "slot_id", "passive_skill_code",
        "buff_id", "forge_no",
    ),
    typed_destination_tables=(
        ("blueprint_id", (BLUEPRINT_ATTR_TABLE, EQUIP_TABLE)),
        ("item_id", (ITEM_TABLE, EQUIP_TABLE)),
        ("suit_id", (SUIT_TABLE, EQUIP_TABLE)),
        ("passive_skill_code", (PASSIVE_TABLE, BLUEPRINT_ATTR_TABLE)),
        ("buff_id", (BUFF_TABLE, PASSIVE_TABLE)),
        ("forge_no", (FORGE_TABLE,)),
    ),
    collision_prone_fields=("blueprint_id", "suit_id", "passive_skill_code", "buff_id"),
    blocked_generic_fields=("id", "no", "code", "record_id"),
    terminal_presentation_fields=("name", "slot", "rarity", "image_asset", "key_effect"),
    supported_claims=(
        "armor.exact_identity", "armor.equipment_owner", "armor.slot",
        "armor.rarity", "armor.base_attributes", "armor.crafting",
        "armor.acquisition", "armor.artwork", "armor.set_membership",
        "armor.key_armor_effect",
    ),
    applicability_rules=(
        "set-piece identity includes suit identity when blueprint IDs are reused",
        "Key Armor is standalone unless an exact suit owner exists",
        "tier attributes require exact equipment/origin lineage",
        "missing crafting evidence never means non-craftable",
        "shared skill or buff handles never merge armor identities",
    ),
)

ARMOR_SET_CONTRACT = AdapterContract(
    entity_type="armor_set",
    identity_seeds=("canonical_id", "suit_id"),
    canonical_owner_tables=("published/web/armor.json", SUIT_TABLE, EQUIP_TABLE),
    allowed_outbound_fields=("suit_id", "blueprint_id", "pieces_required", "attribute_code", "buff_id"),
    typed_destination_tables=(("suit_id", (SUIT_TABLE, EQUIP_TABLE)), ("blueprint_id", (EQUIP_TABLE,))),
    collision_prone_fields=("suit_id", "blueprint_id"),
    blocked_generic_fields=("id", "no", "code", "record_id"),
    terminal_presentation_fields=("name", "image_asset", "piece_count", "set_bonuses"),
    supported_claims=(
        "armor_set.exact_identity", "armor_set.pieces", "armor_set.activation_thresholds",
        "armor_set.bonus_owners", "armor_set.key_armor_membership",
    ),
    applicability_rules=(
        "set membership requires exact suit_id ownership",
        "activation thresholds come only from affix_need_num_list projection",
        "bonus descriptions without an attribute or buff owner remain partial",
        "Key Armor is not silently attached to a suit",
    ),
)


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Armor adapter could not read {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Armor adapter expected an object: {path}")
    return value


def _published(output: Path) -> Path:
    state = _read(output / "last-run.json")
    published = Path(state.get("published") or output / "published")
    if not published.is_absolute():
        published = output / published
    published = published.resolve()
    try:
        published.relative_to(output)
    except ValueError as exc:
        raise ValueError("Armor published source must stay inside the Miner output folder") from exc
    return published


def armor_piece_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for armor_set in payload.get("armor_sets", []):
        if not isinstance(armor_set, dict):
            continue
        for piece in armor_set.get("pieces", []):
            if not isinstance(piece, dict):
                continue
            row = dict(piece)
            row["classification"] = "Set Armor"
            row["set_canonical_id"] = armor_set.get("canonical_id")
            row["set_name"] = armor_set.get("name")
            row["suit_id"] = armor_set.get("suit_id")
            rows.append(row)
    for piece in payload.get("key_armor", []):
        if not isinstance(piece, dict):
            continue
        row = dict(piece)
        row["classification"] = "Key Armor"
        row["set_canonical_id"] = None
        row["suit_id"] = None
        rows.append(row)
    return rows


def armor_set_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in payload.get("armor_sets", []) if isinstance(row, dict)]


def _claim(claim_type: str, entity_type: str, canonical_id: str, result: str, *, evidence=None, missing=None, conflicts=None, dependencies=None, requirements=None) -> dict[str, Any]:
    return {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "claim_type": claim_type,
        "subject": {"entity_type": entity_type, "canonical_id": canonical_id},
        "result": result,
        "requirements": requirements or ["exact typed evidence"],
        "evidence": evidence or [],
        "missing": missing or [],
        "conflicts": conflicts or [],
        "dependencies": dependencies or [],
    }


def _edge(entity_type: str, canonical_id: str, destination: str, relationship_type: str, *, source_table: str, source_record: object, selector: str, authority: str, state: str = "PROVEN", layer: str = "base-current-merged") -> dict[str, Any]:
    source = f"{entity_type}:{canonical_id}"
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
        "dependency_fingerprint": dependency_fingerprint(source, destination, relationship_type, source_table, source_record, selector, layer, authority),
    }


def _assessment(claims: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(row.get("result") or "UNRESOLVED") for row in claims)
    conflicts = [row["claim_type"] for row in claims if row.get("result") == "CONFLICT"]
    missing = [row["claim_type"] for row in claims if row.get("result") in {"PARTIAL", "UNRESOLVED"}]
    if conflicts:
        result = "CONFLICT"
    elif missing and counts["PROVEN"]:
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


class ArmorAdapter(EvidenceDomainAdapter):
    contract = ARMOR_CONTRACT

    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        super().__init__()

    def _rows(self) -> list[dict[str, Any]]:
        return armor_piece_rows(_read(_published(self.output) / "web" / "armor.json"))

    @staticmethod
    def _match(identity: object, rows: list[dict[str, Any]]) -> dict[str, Any]:
        needle = str(identity or "").strip()
        if not needle:
            raise KeyError("Armor identity is empty")
        matches = []
        for row in rows:
            aliases = {str(row.get("canonical_id") or ""), str(row.get("blueprint_id") or "")}
            aliases.update(str(tier.get("item_id")) for tier in row.get("tiers", []) if isinstance(tier, dict) and tier.get("item_id") not in (None, ""))
            if needle in aliases:
                matches.append(row)
        if not matches:
            raise KeyError(f"Unknown exact armor identity: {identity}")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous armor identity; use the suit-qualified canonical ID: {identity}")
        return matches[0]

    def graph(self, identity: object, **_: Any) -> dict[str, Any]:
        row = self._match(identity, self._rows())
        canonical_id = str(row.get("canonical_id") or "")
        blueprint_id = row.get("blueprint_id")
        tiers = [tier for tier in row.get("tiers", []) if isinstance(tier, dict)]
        classification = str(row.get("classification") or "Armor")
        if not canonical_id or blueprint_id in (None, "") or not tiers:
            raise ValueError("Armor identity lacks canonical blueprint/tier ownership")

        entity = {
            "schema_version": ENTITY_SCHEMA_VERSION,
            "entity_type": "armor",
            "canonical_id": canonical_id,
            "name": str(row.get("name") or "Unknown Armor"),
            "classification": classification,
            "identity_state": "PROVEN",
            "source_records": [{"table": "published/web/armor.json", "record_id": canonical_id, "layer": "published-snapshot"}],
        }
        claims: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        claims.append(_claim("armor.exact_identity", "armor", canonical_id, "PROVEN", evidence=[{"canonical_id": canonical_id, "blueprint_id": blueprint_id, "classification": classification}], dependencies=["published/web/armor.json", EQUIP_TABLE], requirements=["one suit-qualified or Key Armor canonical identity", "one blueprint owner"]))

        tier_evidence = []
        for tier in tiers:
            item_id = tier.get("item_id")
            if item_id in (None, ""):
                continue
            tier_evidence.append({"item_id": item_id, "data_level": tier.get("data_level"), "blueprint_id": tier.get("blueprint_id")})
            edges.append(_edge("armor", canonical_id, f"item:{item_id}", "armor-tier-item-owner", source_table=EQUIP_TABLE, source_record=item_id, selector="/blueprint_no|equip_type|suit_id|art_lv", authority="normalized-exact-armor-equipment-owner"))
        owner_result = "PROVEN" if tier_evidence and all(str(x.get("blueprint_id")) == str(blueprint_id) for x in tier_evidence) else "CONFLICT"
        claims.append(_claim("armor.equipment_owner", "armor", canonical_id, owner_result, evidence=tier_evidence if owner_result == "PROVEN" else [], conflicts=[] if owner_result == "PROVEN" else [{"reason": "tier blueprint ownership disagrees", "tiers": tier_evidence}], dependencies=[EQUIP_TABLE], requirements=["all canonical tier rows point to the same blueprint owner"]))

        slot = str(row.get("slot") or "").strip()
        slot_id = row.get("slot_id")
        if slot and slot_id not in (None, ""):
            claims.append(_claim("armor.slot", "armor", canonical_id, "PROVEN", evidence=[{"slot": slot, "slot_id": slot_id}], dependencies=[EQUIP_TABLE], requirements=["exact equip_type slot owner"]))
            edges.append(_edge("armor", canonical_id, f"armor-slot:{slot_id}", "armor-slot-owner", source_table=EQUIP_TABLE, source_record=tiers[0].get("item_id"), selector="/equip_type", authority="normalized-exact-armor-slot"))
        else:
            claims.append(_claim("armor.slot", "armor", canonical_id, "UNRESOLVED", missing=["armor slot owner"], dependencies=[EQUIP_TABLE]))

        rarity = str(row.get("rarity") or "").strip()
        if rarity and rarity.casefold() != "unknown":
            claims.append(_claim("armor.rarity", "armor", canonical_id, "PROVEN", evidence=[{"rarity": rarity, "quality_code": row.get("quality_code")}], dependencies=[EQUIP_TABLE, ITEM_TABLE], requirements=["exact equipment/item quality owner"]))
        else:
            claims.append(_claim("armor.rarity", "armor", canonical_id, "UNRESOLVED", missing=["armor rarity"], dependencies=[EQUIP_TABLE, ITEM_TABLE]))

        attr_rows = []
        missing_attr_tiers = []
        for tier in tiers:
            attrs = tier.get("attributes") or []
            if attrs:
                attr_rows.append({"item_id": tier.get("item_id"), "data_level": tier.get("data_level"), "attributes": attrs, "hp": tier.get("hp"), "pollution_resistance": tier.get("pollution_resistance"), "psi_intensity": tier.get("psi_intensity")})
            else:
                missing_attr_tiers.append(tier.get("item_id"))
        if attr_rows and not missing_attr_tiers:
            attr_result = "PROVEN"
        elif attr_rows:
            attr_result = "PARTIAL"
        else:
            attr_result = "UNRESOLVED"
        claims.append(_claim("armor.base_attributes", "armor", canonical_id, attr_result, evidence=attr_rows, missing=[{"tier_item_ids": missing_attr_tiers}] if missing_attr_tiers else ([] if attr_rows else ["tier base attributes"]), dependencies=[ORIGIN_TABLE, EQUIP_TABLE], requirements=["exact equip_origin base attributes for every canonical tier"]))

        recipes = [recipe for recipe in row.get("crafting_recipes", []) if isinstance(recipe, dict)]
        if recipes:
            claims.append(_claim("armor.crafting", "armor", canonical_id, "PROVEN", evidence=recipes, dependencies=[FORGE_TABLE, "game_common/data/equip_blueprint_data.json"], requirements=["exact blueprint → forge recipe series"]))
            claims.append(_claim("armor.acquisition", "armor", canonical_id, "PARTIAL", evidence=[{"craftable": True, "recipe_count": len(recipes)}], missing=["non-crafting acquisition channels"], dependencies=[FORGE_TABLE], requirements=["crafting proves one acquisition path, not every acquisition path"]))
        else:
            claims.append(_claim("armor.crafting", "armor", canonical_id, "UNRESOLVED", missing=["crafting recipe owner"], dependencies=[FORGE_TABLE], requirements=["missing recipe evidence is not non-craftable proof"]))
            claims.append(_claim("armor.acquisition", "armor", canonical_id, "UNRESOLVED", missing=["source-derived acquisition path"], dependencies=[ITEM_TABLE, FORGE_TABLE]))

        artwork = str(row.get("image_asset") or row.get("icon") or "").strip()
        claims.append(_claim("armor.artwork", "armor", canonical_id, "PROVEN" if artwork else "UNRESOLVED", evidence=[{"image_asset": artwork}] if artwork else [], missing=[] if artwork else ["source-derived artwork"], dependencies=[ITEM_TABLE]))

        set_id = row.get("set_canonical_id")
        suit_id = row.get("suit_id")
        if classification == "Set Armor" and set_id and suit_id not in (None, ""):
            claims.append(_claim("armor.set_membership", "armor", canonical_id, "PROVEN", evidence=[{"set_canonical_id": set_id, "suit_id": suit_id, "set_name": row.get("set_name")}], dependencies=[EQUIP_TABLE, SUIT_TABLE], requirements=["exact nonzero suit_id owner"]))
            edges.append(_edge("armor", canonical_id, f"armor_set:{set_id}", "armor-member-of-set", source_table=EQUIP_TABLE, source_record=tiers[0].get("item_id"), selector="/suit_id", authority="normalized-exact-suit-membership"))
        elif classification == "Key Armor" and not set_id and suit_id in (None, "", 0, "0"):
            claims.append(_claim("armor.set_membership", "armor", canonical_id, "NOT APPLICABLE", evidence=[{"classification": "Key Armor", "suit_id": suit_id}], dependencies=[EQUIP_TABLE], requirements=["standalone Key Armor has explicit no-suit ownership in the normalized player-facing corpus"]))
        else:
            claims.append(_claim("armor.set_membership", "armor", canonical_id, "UNRESOLVED", missing=["exact suit membership state"], dependencies=[EQUIP_TABLE, SUIT_TABLE]))

        if classification == "Key Armor":
            skill = str(row.get("passive_skill_code") or "").strip()
            buff_id = row.get("buff_id")
            effect = str(row.get("key_effect") or "").strip()
            if skill and buff_id not in (None, "", 0, "0") and effect:
                claims.append(_claim("armor.key_armor_effect", "armor", canonical_id, "PROVEN", evidence=[{"passive_skill_code": skill, "buff_id": buff_id, "effect": effect}], dependencies=[BLUEPRINT_ATTR_TABLE, PASSIVE_TABLE, BUFF_TABLE], requirements=["blueprint fixed skill owner", "passive skill buff owner", "player-facing buff text"]))
                edges.append(_edge("armor", canonical_id, f"passive-skill:{skill}", "key-armor-fixed-skill", source_table=BLUEPRINT_ATTR_TABLE, source_record=blueprint_id, selector="/fixed_skill_code", authority="normalized-exact-key-armor-skill-owner"))
                edges.append(_edge("armor", canonical_id, f"buff:{buff_id}", "key-armor-effect-buff", source_table=PASSIVE_TABLE, source_record=skill, selector="/buff_id", authority="normalized-exact-key-armor-buff-owner"))
            else:
                claims.append(_claim("armor.key_armor_effect", "armor", canonical_id, "UNRESOLVED", evidence=[{"passive_skill_code": skill, "buff_id": buff_id}] if skill or buff_id else [], missing=["complete Key Armor skill → buff → effect chain"], dependencies=[BLUEPRINT_ATTR_TABLE, PASSIVE_TABLE, BUFF_TABLE]))
        else:
            claims.append(_claim("armor.key_armor_effect", "armor", canonical_id, "NOT APPLICABLE", evidence=[{"classification": classification}], dependencies=["published/web/armor.json"]))

        payload = {"schema": GENERAL_SCHEMA, "schema_version": GENERAL_SCHEMA_VERSION, "brand": "Dead Signal", "entity": entity, "claims": claims, "edges": edges, "assessment": _assessment(claims), "compatibility": {"phase": 6, "publication_authority": False}}
        errors = validate_generalized_graph(payload)
        if errors:
            raise ValueError(f"Armor adapter produced invalid graph: {errors}")
        return payload

    def identify(self, identity: object, **kwargs: Any) -> dict[str, Any]: return self.graph(identity, **kwargs)["entity"]
    def claims(self, identity: object, **kwargs: Any) -> list[dict[str, Any]]: return self.graph(identity, **kwargs)["claims"]
    def resolve_claim(self, identity: object, claim_type: str, **kwargs: Any) -> dict[str, Any]:
        requested = str(claim_type or "").strip()
        if requested not in self.contract.supported_claims: raise KeyError(f"Unsupported armor claim: {claim_type}")
        matches = [row for row in self.claims(identity, **kwargs) if row.get("claim_type") == requested]
        if not matches: raise KeyError(f"No armor claim resolved for: {claim_type}")
        return matches[0]
    def dependencies(self, identity: object, **kwargs: Any) -> list[str]: return sorted({d for c in self.claims(identity, **kwargs) for d in c.get("dependencies", []) if str(d).strip()})
    def presentation(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        graph = self.graph(identity, **kwargs); entity = graph["entity"]
        return {"entity_type": "armor", "canonical_id": entity["canonical_id"], "name": entity["name"], "classification": entity["classification"], "assessment": graph["assessment"]["result"], "publication_authority": False}


class ArmorSetAdapter(EvidenceDomainAdapter):
    contract = ARMOR_SET_CONTRACT

    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        super().__init__()

    def _rows(self) -> list[dict[str, Any]]:
        return armor_set_rows(_read(_published(self.output) / "web" / "armor.json"))

    @staticmethod
    def _match(identity: object, rows: list[dict[str, Any]]) -> dict[str, Any]:
        needle = str(identity or "").strip()
        matches = [row for row in rows if needle in {str(row.get("canonical_id") or ""), str(row.get("suit_id") or "")}]
        if not matches: raise KeyError(f"Unknown exact armor-set identity: {identity}")
        if len(matches) > 1: raise ValueError(f"Ambiguous armor-set identity: {identity}")
        return matches[0]

    def graph(self, identity: object, **_: Any) -> dict[str, Any]:
        row = self._match(identity, self._rows())
        canonical_id = str(row.get("canonical_id") or "")
        suit_id = row.get("suit_id")
        pieces = [piece for piece in row.get("pieces", []) if isinstance(piece, dict)]
        if not canonical_id or suit_id in (None, ""):
            raise ValueError("Armor set lacks exact canonical/suit identity")
        entity = {"schema_version": ENTITY_SCHEMA_VERSION, "entity_type": "armor_set", "canonical_id": canonical_id, "name": str(row.get("name") or "Unknown Armor Set"), "classification": "Armor Set", "identity_state": "PROVEN", "source_records": [{"table": SUIT_TABLE, "record_id": str(suit_id), "layer": "base-current-merged"}]}
        claims: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        claims.append(_claim("armor_set.exact_identity", "armor_set", canonical_id, "PROVEN", evidence=[{"suit_id": suit_id, "canonical_id": canonical_id}], dependencies=[SUIT_TABLE], requirements=["exact suit_data owner"]))

        if pieces:
            piece_evidence = []
            for piece in pieces:
                pid = piece.get("canonical_id")
                if not pid: continue
                piece_evidence.append({"canonical_id": pid, "blueprint_id": piece.get("blueprint_id"), "slot": piece.get("slot")})
                edges.append(_edge("armor_set", canonical_id, f"armor:{pid}", "armor-set-contains-piece", source_table=EQUIP_TABLE, source_record=piece.get("blueprint_id"), selector="/suit_id", authority="normalized-exact-suit-piece-owner"))
            claims.append(_claim("armor_set.pieces", "armor_set", canonical_id, "PROVEN" if piece_evidence else "UNRESOLVED", evidence=piece_evidence, missing=[] if piece_evidence else ["set pieces"], dependencies=[SUIT_TABLE, EQUIP_TABLE], requirements=["every published set piece carries this exact suit_id"]))
        else:
            claims.append(_claim("armor_set.pieces", "armor_set", canonical_id, "UNRESOLVED", missing=["canonical set pieces"], dependencies=[SUIT_TABLE, EQUIP_TABLE]))

        bonuses = [bonus for bonus in row.get("set_bonuses", []) if isinstance(bonus, dict)]
        thresholds = [int(bonus.get("pieces_required")) for bonus in bonuses if str(bonus.get("pieces_required") or "").isdigit() and int(bonus.get("pieces_required")) > 0]
        if bonuses and len(thresholds) == len(bonuses):
            claims.append(_claim("armor_set.activation_thresholds", "armor_set", canonical_id, "PROVEN", evidence=[{"pieces_required": thresholds}], dependencies=[SUIT_TABLE], requirements=["exact affix_need_num_list threshold for every published bonus"]))
        elif bonuses:
            claims.append(_claim("armor_set.activation_thresholds", "armor_set", canonical_id, "PARTIAL", evidence=[{"pieces_required": thresholds}], missing=["one or more activation thresholds"], dependencies=[SUIT_TABLE]))
        else:
            claims.append(_claim("armor_set.activation_thresholds", "armor_set", canonical_id, "UNRESOLVED", missing=["set bonus thresholds"], dependencies=[SUIT_TABLE]))

        owned = []
        ownerless = []
        for bonus in bonuses:
            owner = {"pieces_required": bonus.get("pieces_required"), "attribute_code": bonus.get("attribute_code"), "attribute_value": bonus.get("attribute_value"), "buff_info": bonus.get("buff_info") or [], "description": bonus.get("description") or ""}
            if owner["attribute_code"] not in (None, "") or owner["buff_info"]:
                owned.append(owner)
            else:
                ownerless.append(owner)
        if owned and not ownerless:
            bonus_result = "PROVEN"
        elif owned or ownerless:
            bonus_result = "PARTIAL"
        else:
            bonus_result = "UNRESOLVED"
        claims.append(_claim("armor_set.bonus_owners", "armor_set", canonical_id, bonus_result, evidence=owned + ownerless if bonuses else [], missing=[{"ownerless_bonuses": len(ownerless)}] if ownerless else ([] if bonuses else ["set bonus owners"]), dependencies=[SUIT_TABLE], requirements=["exact activation threshold", "attribute_code or buff_info owner; description text alone is not ownership proof"]))

        claims.append(_claim("armor_set.key_armor_membership", "armor_set", canonical_id, "NOT APPLICABLE", evidence=[{"reason": "Key Armor is normalized as standalone no-suit armor; it is not inferred into a suit"}], dependencies=[EQUIP_TABLE, SUIT_TABLE], requirements=["do not infer Key Armor membership from names, shared skills, or shared handles"]))
        payload = {"schema": GENERAL_SCHEMA, "schema_version": GENERAL_SCHEMA_VERSION, "brand": "Dead Signal", "entity": entity, "claims": claims, "edges": edges, "assessment": _assessment(claims), "compatibility": {"phase": 6, "publication_authority": False}}
        errors = validate_generalized_graph(payload)
        if errors: raise ValueError(f"Armor-set adapter produced invalid graph: {errors}")
        return payload

    def identify(self, identity: object, **kwargs: Any) -> dict[str, Any]: return self.graph(identity, **kwargs)["entity"]
    def claims(self, identity: object, **kwargs: Any) -> list[dict[str, Any]]: return self.graph(identity, **kwargs)["claims"]
    def resolve_claim(self, identity: object, claim_type: str, **kwargs: Any) -> dict[str, Any]:
        requested = str(claim_type or "").strip()
        if requested not in self.contract.supported_claims: raise KeyError(f"Unsupported armor-set claim: {claim_type}")
        matches = [row for row in self.claims(identity, **kwargs) if row.get("claim_type") == requested]
        if not matches: raise KeyError(f"No armor-set claim resolved for: {claim_type}")
        return matches[0]
    def dependencies(self, identity: object, **kwargs: Any) -> list[str]: return sorted({d for c in self.claims(identity, **kwargs) for d in c.get("dependencies", []) if str(d).strip()})
    def presentation(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        graph = self.graph(identity, **kwargs); entity = graph["entity"]
        return {"entity_type": "armor_set", "canonical_id": entity["canonical_id"], "name": entity["name"], "classification": "Armor Set", "assessment": graph["assessment"]["result"], "publication_authority": False}
