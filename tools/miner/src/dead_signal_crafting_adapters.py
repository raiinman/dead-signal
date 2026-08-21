"""Typed Recipe and Material adapters for the generalized Evidence Graph."""
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

FORGE_TABLE = "game_common/data/forge_data.json"
CHOICE_TABLE = "game_common/data/forge_choice_material_data.json"
ITEM_TABLE = "game_common/data/item_data.json"
MONEY_TABLE = "game_common/data/money_material_data.json"
FORMULA_TABLE = "client_data/forge_formula_map_data.json"
CRAFTING_DATA = "published/data/crafting.json"
MATERIAL_DATA = "published/data/materials.json"

RECIPE_CONTRACT = AdapterContract(
    entity_type="recipe",
    identity_seeds=("canonical_id", "forge_no", "server_no", "record_key"),
    canonical_owner_tables=(CRAFTING_DATA, FORGE_TABLE, FORMULA_TABLE),
    allowed_outbound_fields=(
        "output_item_id", "fixed_materials", "selectable_material_groups",
        "currency", "craft_time_seconds", "formula_map_output_item_ids",
    ),
    typed_destination_tables=(
        ("output_item_id", (ITEM_TABLE,)),
        ("fixed_materials", (ITEM_TABLE,)),
        ("selectable_material_groups", (CHOICE_TABLE,)),
        ("currency", (MONEY_TABLE,)),
        ("formula_map_output_item_ids", (FORMULA_TABLE, ITEM_TABLE)),
    ),
    collision_prone_fields=("forge_no", "server_no", "output_item_id"),
    blocked_generic_fields=("id", "no", "code", "record_id"),
    terminal_presentation_fields=("output_name", "output_image_reference"),
    supported_claims=(
        "recipe.exact_identity",
        "recipe.output_item",
        "recipe.formula_map_consistency",
        "recipe.fixed_materials",
        "recipe.selectable_material_groups",
        "recipe.currency_cost",
        "recipe.craft_time",
    ),
    applicability_rules=(
        "recipe identity is exact forge_no plus server_no",
        "simple forge keys use server 0 and are not promoted to a current server",
        "choice-group IDs and item IDs are separate typed namespaces",
        "formula map disagreement with forge output is CONFLICT",
        "missing one recipe lane never proves an output item globally non-craftable",
    ),
)

MATERIAL_CONTRACT = AdapterContract(
    entity_type="material",
    identity_seeds=("canonical_id", "item_id"),
    canonical_owner_tables=(MATERIAL_DATA, ITEM_TABLE, FORGE_TABLE, CHOICE_TABLE),
    allowed_outbound_fields=(
        "item_id", "fixed_recipe_ids", "selectable_recipe_ids",
        "choice_group_ids", "gain_path", "image_reference",
    ),
    typed_destination_tables=(
        ("item_id", (ITEM_TABLE,)),
        ("fixed_recipe_ids", (FORGE_TABLE,)),
        ("selectable_recipe_ids", (FORGE_TABLE, CHOICE_TABLE)),
        ("choice_group_ids", (CHOICE_TABLE,)),
    ),
    collision_prone_fields=("item_id", "choice_group_ids"),
    blocked_generic_fields=("id", "no", "code", "record_id"),
    terminal_presentation_fields=(
        "name", "description", "quality", "gain_path", "image_reference",
    ),
    supported_claims=(
        "material.exact_identity",
        "material.recipe_usage",
        "material.choice_group_membership",
        "material.acquisition",
        "material.artwork",
    ),
    applicability_rules=(
        "material identity is an exact item_data item ID",
        "choice-group identity is never treated as a material item ID",
        "recipe usage is reverse-projected only from typed recipe costs",
        "localized gain-path text is not a typed acquisition relation",
    ),
)


def _read(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Crafting adapter could not read {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Crafting adapter expected object: {path}")
    return payload


def _claim(entity_type: str, kind: str, canonical_id: str, result: str, *, evidence=None, missing=None, conflicts=None, dependencies=None, requirements=None) -> dict[str, Any]:
    return {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "claim_type": kind,
        "subject": {"entity_type": entity_type, "canonical_id": canonical_id},
        "result": result,
        "requirements": requirements or ["exact typed evidence"],
        "evidence": evidence or [],
        "missing": missing or [],
        "conflicts": conflicts or [],
        "dependencies": dependencies or [],
    }


def _edge(entity_type: str, canonical_id: str, destination: str, relation: str, *, table: str, record: object, selector: str, authority: str, layer: str = "base-current-merged", state: str = "PROVEN") -> dict[str, Any]:
    source = f"{entity_type}:{canonical_id}"
    return {
        "schema_version": EDGE_SCHEMA_VERSION,
        "source": source,
        "destination": destination,
        "relationship_type": relation,
        "source_table": table,
        "source_record": str(record),
        "selector": selector,
        "layer": layer,
        "authority": authority,
        "state": state,
        "dependency_fingerprint": dependency_fingerprint(
            source, destination, relation, table, record, selector, layer, authority,
        ),
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


class _PublishedAdapter(EvidenceDomainAdapter):
    filename = ""
    collection = ""

    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        super().__init__()

    def _published(self) -> Path:
        state = _read(self.output / "last-run.json")
        published = Path(state.get("published") or self.output / "published")
        if not published.is_absolute():
            published = self.output / published
        published = published.resolve()
        try:
            published.relative_to(self.output)
        except ValueError as exc:
            raise ValueError("Crafting published source must stay inside Miner output") from exc
        return published

    def _rows(self) -> list[dict[str, Any]]:
        payload = _read(self._published() / "data" / self.filename)
        return [row for row in payload.get(self.collection, []) if isinstance(row, dict)]


class RecipeAdapter(_PublishedAdapter):
    contract = RECIPE_CONTRACT
    filename = "crafting.json"
    collection = "recipes"

    def _match(self, identity: object) -> dict[str, Any]:
        needle = str(identity or "").strip()
        if not needle:
            raise KeyError("Recipe identity is empty")
        matches = []
        for row in self._rows():
            aliases = {
                str(row.get("canonical_id") or ""),
                str(row.get("record_key") or ""),
                f"{row.get('forge_no')}:{row.get('server_no')}",
            }
            # Bare forge_no is accepted only if unique across server variants.
            if needle == str(row.get("forge_no")) or needle in aliases:
                matches.append(row)
        if not matches:
            raise KeyError(f"Unknown recipe identity: {identity}")
        if len(matches) != 1:
            raise ValueError(f"Ambiguous recipe identity: {identity}; use forge_no:server_no")
        return matches[0]

    def graph(self, identity: object, **_: Any) -> dict[str, Any]:
        row = self._match(identity)
        canonical_id = str(row["canonical_id"])
        forge_no = int(row.get("forge_no") or 0)
        server_no = int(row.get("server_no") or 0)
        record_key = str(row.get("record_key") or f"({forge_no}, {server_no})")
        layer = str(row.get("source_layer") or "base-current-merged")
        entity = {
            "schema_version": ENTITY_SCHEMA_VERSION,
            "entity_type": "recipe",
            "canonical_id": canonical_id,
            "name": str(row.get("output_name") or f"Forge Recipe {forge_no}:{server_no}"),
            "classification": "Crafting Recipe",
            "identity_state": "PROVEN",
            "source_records": [{"table": FORGE_TABLE, "record_id": record_key, "layer": layer}],
        }
        claims: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        claims.append(_claim(
            "recipe", "recipe.exact_identity", canonical_id, "PROVEN",
            evidence=[{"forge_no": forge_no, "server_no": server_no, "record_key": record_key}],
            dependencies=[FORGE_TABLE],
            requirements=["exact forge_data record identity"],
        ))

        output_item_id = int(row.get("output_item_id") or 0)
        if output_item_id:
            claims.append(_claim(
                "recipe", "recipe.output_item", canonical_id, "PROVEN",
                evidence=[{"item_id": output_item_id, "name": row.get("output_name", "")}],
                dependencies=[FORGE_TABLE, ITEM_TABLE],
                requirements=["exact forge_data.item_no", "exact item_data owner"],
            ))
            edges.append(_edge(
                "recipe", canonical_id, f"item:{output_item_id}", "recipe-output-item",
                table=FORGE_TABLE, record=record_key, selector="/item_no",
                authority="exact-forge-output", layer=layer,
            ))
        else:
            claims.append(_claim(
                "recipe", "recipe.output_item", canonical_id, "UNRESOLVED",
                missing=["forge_data.item_no output owner"], dependencies=[FORGE_TABLE, ITEM_TABLE],
            ))

        formula_state = str(row.get("formula_map_state") or "UNRESOLVED")
        mapped = list(row.get("formula_map_output_item_ids") or [])
        if formula_state == "CONFLICT":
            claims.append(_claim(
                "recipe", "recipe.formula_map_consistency", canonical_id, "CONFLICT",
                evidence=[{"forge_output_item_id": output_item_id, "formula_map_output_item_ids": mapped}],
                conflicts=["forge_data.item_no disagrees with ITEM_NO_TO_FORGE_NO_MAP"],
                dependencies=[FORGE_TABLE, FORMULA_TABLE],
            ))
        elif formula_state == "PROVEN":
            claims.append(_claim(
                "recipe", "recipe.formula_map_consistency", canonical_id, "PROVEN",
                evidence=[{"formula_map_output_item_ids": mapped}], dependencies=[FORMULA_TABLE],
            ))
        else:
            claims.append(_claim(
                "recipe", "recipe.formula_map_consistency", canonical_id, "UNRESOLVED",
                missing=["matching ITEM_NO_TO_FORGE_NO_MAP owner"], dependencies=[FORMULA_TABLE],
            ))

        fixed = list(row.get("fixed_materials") or [])
        unresolved = list(row.get("unresolved_cost_ids") or [])
        fixed_result = "PARTIAL" if fixed and unresolved else "PROVEN" if fixed else "UNRESOLVED" if unresolved else "NOT APPLICABLE"
        claims.append(_claim(
            "recipe", "recipe.fixed_materials", canonical_id, fixed_result,
            evidence=fixed,
            missing=[{"unresolved_cost_ids": unresolved}] if unresolved else [],
            dependencies=[FORGE_TABLE, ITEM_TABLE],
            requirements=["cost ID typed as exact item_data owner"],
        ))
        for material in fixed:
            item_id = int(material.get("item_id") or 0)
            if item_id:
                edges.append(_edge(
                    "recipe", canonical_id, f"material:ds-material-{item_id}", "recipe-fixed-material",
                    table=FORGE_TABLE, record=record_key, selector="/cost_item_list",
                    authority="typed-fixed-material-cost", layer=layer,
                ))

        groups = list(row.get("selectable_material_groups") or [])
        group_result = "PROVEN" if groups else "NOT APPLICABLE"
        claims.append(_claim(
            "recipe", "recipe.selectable_material_groups", canonical_id, group_result,
            evidence=[{"group_id": group.get("group_id"), "multiplier": group.get("multiplier"), "option_count": len(group.get("options") or [])} for group in groups],
            dependencies=[FORGE_TABLE, CHOICE_TABLE],
            requirements=["cost ID typed as exact forge_choice_material_data.identity"],
        ))
        for group in groups:
            group_id = int(group.get("group_id") or 0)
            if group_id:
                edges.append(_edge(
                    "recipe", canonical_id, f"material-group:ds-material-group-{group_id}", "recipe-selectable-material-group",
                    table=FORGE_TABLE, record=record_key, selector="/cost_item_list",
                    authority="typed-choice-group-cost", layer=layer,
                ))

        currency = row.get("currency") or {}
        currency_id = int(currency.get("currency_id") or 0)
        currency_quantity = int(currency.get("quantity") or 0)
        if currency_id:
            currency_state = "PROVEN" if currency.get("source_layer") not in {None, "", "unresolved"} else "UNRESOLVED"
            claims.append(_claim(
                "recipe", "recipe.currency_cost", canonical_id, currency_state,
                evidence=[currency] if currency_state == "PROVEN" else [],
                missing=[] if currency_state == "PROVEN" else ["money_material_data currency owner"],
                dependencies=[FORGE_TABLE, MONEY_TABLE],
            ))
            if currency_state == "PROVEN":
                edges.append(_edge(
                    "recipe", canonical_id, f"currency:{currency_id}", "recipe-currency-cost",
                    table=FORGE_TABLE, record=record_key, selector="/cost_money_no",
                    authority="exact-forge-currency-cost", layer=layer,
                ))
        else:
            claims.append(_claim(
                "recipe", "recipe.currency_cost", canonical_id, "NOT APPLICABLE",
                evidence=[{"quantity": currency_quantity}], dependencies=[FORGE_TABLE],
            ))

        claims.append(_claim(
            "recipe", "recipe.craft_time", canonical_id, "PROVEN",
            evidence=[{"seconds": int(row.get("craft_time_seconds") or 0)}],
            dependencies=[FORGE_TABLE], requirements=["exact forge_data.seconds value"],
        ))

        payload = {
            "schema": GENERAL_SCHEMA,
            "schema_version": GENERAL_SCHEMA_VERSION,
            "entity": entity,
            "claims": claims,
            "edges": edges,
            "assessment": _assessment(claims),
            "domain": {"entity_type": "recipe", "adapter": type(self).__name__},
        }
        validate_generalized_graph(payload)
        return payload


class MaterialAdapter(_PublishedAdapter):
    contract = MATERIAL_CONTRACT
    filename = "materials.json"
    collection = "materials"

    def _match(self, identity: object) -> dict[str, Any]:
        needle = str(identity or "").strip()
        if not needle:
            raise KeyError("Material identity is empty")
        matches = [
            row for row in self._rows()
            if needle in {str(row.get("canonical_id") or ""), str(row.get("item_id") or "")}
        ]
        if not matches:
            raise KeyError(f"Unknown material identity: {identity}")
        if len(matches) != 1:
            raise ValueError(f"Ambiguous material identity: {identity}")
        return matches[0]

    def graph(self, identity: object, **_: Any) -> dict[str, Any]:
        row = self._match(identity)
        canonical_id = str(row["canonical_id"])
        item_id = int(row.get("item_id") or 0)
        layer = str(row.get("source_layer") or "base-current-merged")
        entity = {
            "schema_version": ENTITY_SCHEMA_VERSION,
            "entity_type": "material",
            "canonical_id": canonical_id,
            "name": str(row.get("name") or f"Material {item_id}"),
            "classification": "Crafting Material",
            "identity_state": "PROVEN",
            "source_records": [{"table": ITEM_TABLE, "record_id": str(item_id), "layer": layer}],
        }
        claims: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        claims.append(_claim(
            "material", "material.exact_identity", canonical_id, "PROVEN",
            evidence=[{"item_id": item_id, "name": row.get("name", "")}],
            dependencies=[ITEM_TABLE], requirements=["exact item_data identity"],
        ))

        fixed = list(row.get("fixed_recipe_ids") or [])
        selectable = list(row.get("selectable_recipe_ids") or [])
        usage = [{"recipe_id": value, "mode": "fixed"} for value in fixed] + [{"recipe_id": value, "mode": "selectable"} for value in selectable]
        usage_result = "PROVEN" if usage else "NOT APPLICABLE"
        claims.append(_claim(
            "material", "material.recipe_usage", canonical_id, usage_result,
            evidence=usage, dependencies=[FORGE_TABLE, CHOICE_TABLE],
            requirements=["reverse projection from typed recipe costs"],
        ))
        for recipe_id in fixed:
            edges.append(_edge(
                "material", canonical_id, f"recipe:{recipe_id}", "material-fixed-recipe-usage",
                table=CRAFTING_DATA, record=recipe_id, selector="/fixed_materials",
                authority="reverse-exact-fixed-cost", layer="normalized-evidence",
            ))
        for recipe_id in selectable:
            edges.append(_edge(
                "material", canonical_id, f"recipe:{recipe_id}", "material-selectable-recipe-usage",
                table=CRAFTING_DATA, record=recipe_id, selector="/selectable_material_groups/options",
                authority="reverse-exact-choice-group-cost", layer="normalized-evidence",
            ))

        groups = [int(value) for value in row.get("choice_group_ids") or []]
        claims.append(_claim(
            "material", "material.choice_group_membership", canonical_id,
            "PROVEN" if groups else "NOT APPLICABLE",
            evidence=[{"group_id": value} for value in groups], dependencies=[CHOICE_TABLE],
        ))
        for group_id in groups:
            edges.append(_edge(
                "material", canonical_id, f"material-group:ds-material-group-{group_id}", "material-choice-group-member",
                table=CHOICE_TABLE, record=group_id, selector="/identity,/item_id",
                authority="exact-choice-group-membership", layer="base-current-merged",
            ))

        gain_path = str(row.get("gain_path") or "").strip()
        if gain_path:
            claims.append(_claim(
                "material", "material.acquisition", canonical_id, "PARTIAL",
                evidence=[{"localized_gain_path": gain_path}],
                missing=["typed acquisition owner such as vendor/drop/reward relation"],
                dependencies=[ITEM_TABLE],
                requirements=["localized hint is presentation evidence only; typed acquisition owner required for PROVEN"],
            ))
        else:
            claims.append(_claim(
                "material", "material.acquisition", canonical_id, "UNRESOLVED",
                missing=["typed acquisition owner"], dependencies=[ITEM_TABLE],
            ))

        artwork = str(row.get("image_reference") or "").strip()
        claims.append(_claim(
            "material", "material.artwork", canonical_id,
            "PROVEN" if artwork else "UNRESOLVED",
            evidence=[{"image_reference": artwork}] if artwork else [],
            missing=[] if artwork else ["source-derived material artwork reference"],
            dependencies=[ITEM_TABLE],
        ))

        payload = {
            "schema": GENERAL_SCHEMA,
            "schema_version": GENERAL_SCHEMA_VERSION,
            "entity": entity,
            "claims": claims,
            "edges": edges,
            "assessment": _assessment(claims),
            "domain": {"entity_type": "material", "adapter": type(self).__name__},
        }
        validate_generalized_graph(payload)
        return payload
