"""Typed Mod 2.0 adapter for the generalized Dead Signal Evidence Graph.

Phase 7 keeps exact current Mod 2.0 item variants separate from browse families,
Shiny classification, suffix/frame families, and legacy randomly rolled Mods.
Only exact normalized New Mod tables are authoritative here. Frame source order is
preserved, but source positions are never assigned to frame_lv_1..4 without an
exact runtime consumer.
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

ITEM_MAP_TABLE = "game_common/data/new_mod_item_data.json"
PROPERTY_TABLE = "game_common/data/new_mod_property_data.json"
ENTRY_TABLE = "game_common/data/mod_entry_data.json"
FRAME_TABLE = "game_common/data/new_mod_frame_lib_data.json"
CURRENT_MOD_SYSTEM = "current-mod-2.0"
LEGACY_MOD_SYSTEM = "legacy-random-roll-mod"
REQUIRED_MAIN_LEVELS = tuple(range(1, 18))
PROVEN_FRAME_STATUS = "proven-frame-and-sub-entry-family-identities"


MOD_CONTRACT = AdapterContract(
    entity_type="mod",
    identity_seeds=("item_id", "mod_code"),
    canonical_owner_tables=(
        "published/web/mods.json",
        "published/data/mods.json",
        ITEM_MAP_TABLE,
        PROPERTY_TABLE,
        ENTRY_TABLE,
        FRAME_TABLE,
    ),
    allowed_outbound_fields=(
        "item_id",
        "mod_code",
        "apply_range_code",
        "genre_library_code",
        "main_entry_code",
        "frame_code",
        "shiny_buff_id",
        "shiny_replacement_mod_code",
    ),
    typed_destination_tables=(
        ("item_id", (ITEM_MAP_TABLE, "game_common/data/item_data.json")),
        ("mod_code", (ITEM_MAP_TABLE, PROPERTY_TABLE)),
        ("apply_range_code", (PROPERTY_TABLE,)),
        ("genre_library_code", (PROPERTY_TABLE,)),
        ("main_entry_code", (PROPERTY_TABLE, ENTRY_TABLE)),
        ("frame_code", (PROPERTY_TABLE, FRAME_TABLE)),
        ("shiny_buff_id", (PROPERTY_TABLE, "game_common/data/buff_level_data.json")),
        ("shiny_replacement_mod_code", (PROPERTY_TABLE,)),
    ),
    collision_prone_fields=(
        "item_id", "mod_code", "apply_range_code", "genre_library_code",
        "main_entry_code", "frame_code", "shiny_buff_id", "shiny_replacement_mod_code",
    ),
    blocked_generic_fields=("id", "no", "code", "record_id"),
    terminal_presentation_fields=(
        "name", "rarity", "gain_path", "image_reference", "is_shiny",
        "main_entry_effects", "frame_sub_entry_evidence",
    ),
    supported_claims=(
        "mod.exact_identity",
        "mod.system_classification",
        "mod.slot_compatibility",
        "mod.family_main_attribute",
        "mod.fixed_sub_attributes",
        "mod.levels_1_17",
        "mod.shiny_classification",
        "mod.suffix_frame_family",
        "mod.acquisition",
        "mod.effect_ownership",
        "mod.artwork",
    ),
    applicability_rules=(
        "exact item variants remain distinct even when mod_code families repeat",
        "current Mod 2.0 evidence is sourced only from normalized new_mod_* ownership",
        "legacy randomly rolled Mod records never enter the current Mod 2.0 graph",
        "frame source order is preserved but never mapped to frame_lv_1..4 without consumer proof",
        "shared entry, frame, or buff handles never merge Mod identities",
    ),
)


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Mod adapter could not read {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Mod adapter expected an object: {path}")
    return value


def _web_variants(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in payload.get("families", []):
        if not isinstance(family, dict):
            continue
        family_id = str(family.get("canonical_id") or "")
        for variant in family.get("variants", []):
            if not isinstance(variant, dict):
                continue
            row = dict(variant)
            item_id = row.get("item_id")
            if item_id in (None, ""):
                continue
            row.setdefault("canonical_id", f"ds-mod-var-{item_id}")
            row["family_canonical_id"] = family_id
            rows.append(row)
    return rows


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
) -> dict[str, Any]:
    return {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "claim_type": claim_type,
        "subject": {"entity_type": "mod", "canonical_id": canonical_id},
        "result": result,
        "requirements": requirements or ["exact typed Mod 2.0 evidence"],
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
    authority: str,
    state: str = "PROVEN",
) -> dict[str, Any]:
    source = f"mod:{canonical_id}"
    fingerprint = dependency_fingerprint(
        source, destination, relationship_type, source_table, source_record,
        selector, "base-current-merged", authority,
    )
    return {
        "schema_version": EDGE_SCHEMA_VERSION,
        "source": source,
        "destination": destination,
        "relationship_type": relationship_type,
        "source_table": source_table,
        "source_record": str(source_record),
        "selector": selector,
        "layer": "base-current-merged",
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


def _int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _available_levels(effects: list[dict[str, Any]]) -> list[int]:
    return sorted({_int(row.get("level")) for row in effects if isinstance(row, dict) and _int(row.get("level"))})


def _property_owner(row: dict[str, Any]) -> bool:
    """Fail-closed proxy for an exact new_mod_property_data owner.

    Normalized Mod rows originate from new_mod_item_data. Property-dependent
    claims additionally require at least one non-empty property-owned selector.
    """
    return bool(
        _int(row.get("mod_code"))
        and any(
            (
                _int(row.get("apply_range_code")),
                _int(row.get("genre_library_code")),
                _int(row.get("main_entry_code")),
                _int(row.get("frame_code")),
                bool(row.get("is_shiny")),
                _int(row.get("shiny_buff_id")),
                _int(row.get("shiny_replacement_mod_code")),
            )
        )
    )


class ModAdapter(EvidenceDomainAdapter):
    contract = MOD_CONTRACT

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
            raise ValueError("Mod published source must stay inside the Miner output folder") from exc
        return published

    def _sources(self) -> tuple[dict[str, Any], dict[str, Any]]:
        published = self._published()
        return _read(published / "web" / "mods.json"), _read(published / "data" / "mods.json")

    @staticmethod
    def _match_web(identity: object, rows: list[dict[str, Any]]) -> dict[str, Any]:
        needle = str(identity or "").strip()
        if not needle:
            raise KeyError("Mod identity is empty")
        matches: list[dict[str, Any]] = []
        for row in rows:
            aliases = {
                str(row.get("canonical_id") or ""),
                str(row.get("item_id") or ""),
                str(row.get("mod_code") or row.get("id") or ""),
            }
            if needle in aliases:
                matches.append(row)
        if not matches:
            raise KeyError(f"Unknown exact Mod identity: {identity}")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous Mod identity; use exact item/canonical ID: {identity}")
        return matches[0]

    @staticmethod
    def _match_data(web_row: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        item_id = str(web_row.get("item_id") or "")
        matches = [
            row for row in payload.get("mods", [])
            if isinstance(row, dict) and str(row.get("item_id") or "") == item_id
        ]
        if len(matches) != 1:
            raise ValueError(f"Mod normalized item owner must resolve exactly once: {item_id}")
        return matches[0]

    def graph(self, identity: object, **_: Any) -> dict[str, Any]:
        web_payload, data_payload = self._sources()
        web_row = self._match_web(identity, _web_variants(web_payload))
        row = self._match_data(web_row, data_payload)

        item_id = row.get("item_id")
        mod_code = row.get("mod_code") or row.get("id")
        canonical_id = str(web_row.get("canonical_id") or f"ds-mod-var-{item_id}")
        property_owner = _property_owner(row)
        family_id = str(web_row.get("family_canonical_id") or f"ds-mod-{mod_code}")
        effects = [effect for effect in row.get("main_entry_effects", []) if isinstance(effect, dict)]
        frame = row.get("frame_sub_entry_evidence") if isinstance(row.get("frame_sub_entry_evidence"), dict) else {}

        entity = {
            "schema_version": ENTITY_SCHEMA_VERSION,
            "entity_type": "mod",
            "canonical_id": canonical_id,
            "name": str(web_row.get("name") or row.get("name") or "Unknown Mod"),
            "classification": "Shiny Mod 2.0" if row.get("is_shiny") else "Mod 2.0",
            "identity_state": "PROVEN",
            "source_records": [
                {"table": "published/web/mods.json", "record_id": canonical_id, "layer": "published-snapshot"},
                {"table": ITEM_MAP_TABLE, "record_id": str(item_id), "layer": "base-current-merged"},
            ] + ([{"table": PROPERTY_TABLE, "record_id": str(mod_code), "layer": "base-current-merged"}] if property_owner else []),
        }

        claims: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        claims.append(_claim(
            "mod.exact_identity", canonical_id, "PROVEN",
            evidence=[{"item_id": item_id, "mod_code": mod_code, "family_canonical_id": family_id}],
            dependencies=[ITEM_MAP_TABLE, "published/web/mods.json"],
            requirements=["exact new_mod_item_data item owner", "exact source variant"],
        ))
        edges.append(_edge(
            canonical_id, family_id, "mod-browse-family",
            source_table=ITEM_MAP_TABLE, source_record=item_id,
            selector="/mod_code", authority="exact-mod-item-map-owner",
        ))

        claims.append(_claim(
            "mod.system_classification", canonical_id, "PROVEN",
            evidence=[{"classification": CURRENT_MOD_SYSTEM, "source_table": ITEM_MAP_TABLE}],
            dependencies=[ITEM_MAP_TABLE],
            requirements=["current Mod 2.0 item must originate from new_mod_item_data", "legacy random-roll records isolated"],
        ))

        apply_range = _int(row.get("apply_range_code"))
        if property_owner and apply_range:
            claims.append(_claim(
                "mod.slot_compatibility", canonical_id, "PROVEN",
                evidence=[{"apply_range_code": apply_range}], dependencies=[PROPERTY_TABLE],
                requirements=["exact new_mod_property_data apply_range selector"],
            ))
            edges.append(_edge(
                canonical_id, f"mod-apply-range:{apply_range}", "mod-slot-compatibility-selector",
                source_table=PROPERTY_TABLE, source_record=mod_code,
                selector="/apply_range", authority="exact-mod-property-selector",
            ))
        else:
            claims.append(_claim(
                "mod.slot_compatibility", canonical_id, "UNRESOLVED",
                missing=["exact apply_range owner/selector"], dependencies=[PROPERTY_TABLE],
                requirements=["exact new_mod_property_data apply_range selector"],
            ))

        genre = _int(row.get("genre_library_code"))
        main_entry = _int(row.get("main_entry_code"))
        family_evidence: list[Any] = []
        missing_family: list[Any] = []
        if property_owner and genre:
            family_evidence.append({"genre_library_code": genre})
            edges.append(_edge(
                canonical_id, f"mod-genre:{genre}", "mod-genre-family",
                source_table=PROPERTY_TABLE, source_record=mod_code,
                selector="/genre_lib", authority="exact-mod-property-selector",
            ))
        else:
            missing_family.append("genre_lib owner")
        if property_owner and main_entry:
            family_evidence.append({"main_entry_code": main_entry})
            edges.append(_edge(
                canonical_id, f"mod-entry:{main_entry}", "mod-main-entry-owner",
                source_table=PROPERTY_TABLE, source_record=mod_code,
                selector="/main_entry_no", authority="exact-mod-property-selector",
            ))
        else:
            missing_family.append("main_entry_no owner")
        family_result = "PROVEN" if not missing_family else "PARTIAL" if family_evidence else "UNRESOLVED"
        claims.append(_claim(
            "mod.family_main_attribute", canonical_id, family_result,
            evidence=family_evidence, missing=missing_family,
            dependencies=[PROPERTY_TABLE, ENTRY_TABLE],
            requirements=["exact genre family", "exact main entry family"],
        ))

        sub_ids = [value for value in frame.get("sub_entry_ids", []) if _int(value)]
        sub_families = [value for value in frame.get("sub_entry_families", []) if isinstance(value, dict)]
        if frame.get("status") == PROVEN_FRAME_STATUS and len(sub_ids) == 4 and len(sub_families) == 4:
            claims.append(_claim(
                "mod.fixed_sub_attributes", canonical_id, "PROVEN",
                evidence=[{"sub_entry_ids": sub_ids, "sub_entry_families": sub_families, "order_semantics": frame.get("order_semantics")}],
                dependencies=[FRAME_TABLE, ENTRY_TABLE],
                requirements=["exact frame row", "exact four ordered sub-entry IDs", "stable regular-level entry identities"],
            ))
            for entry_id in sub_ids:
                edges.append(_edge(
                    canonical_id, f"mod-entry:{entry_id}", "mod-fixed-sub-entry-family",
                    source_table=FRAME_TABLE, source_record=row.get("frame_code"),
                    selector="/sub_entry_item_no", authority="exact-mod-frame-sub-entry-owner",
                ))
        else:
            claims.append(_claim(
                "mod.fixed_sub_attributes", canonical_id, "UNRESOLVED",
                missing=["exact four stable frame sub-entry families"],
                dependencies=[FRAME_TABLE, ENTRY_TABLE],
                requirements=["exact frame row", "exact four ordered sub-entry IDs", "stable regular-level entry identities"],
            ))

        available = _available_levels(effects)
        missing_levels = [level for level in REQUIRED_MAIN_LEVELS if level not in available]
        if not effects:
            levels_result = "UNRESOLVED"
            levels_missing: list[Any] = ["main entry level rows 1-17"]
        elif missing_levels:
            levels_result = "PARTIAL"
            levels_missing = [{"missing_levels": missing_levels}]
        else:
            levels_result = "PROVEN"
            levels_missing = []
        claims.append(_claim(
            "mod.levels_1_17", canonical_id, levels_result,
            evidence=[{"main_entry_code": main_entry, "available_levels": available}] if effects else [],
            missing=levels_missing, dependencies=[ENTRY_TABLE],
            requirements=["exact main entry family", "exact mod_entry_data rows for Levels 1-17"],
        ))

        if property_owner:
            shiny_evidence = {
                "is_shiny": bool(row.get("is_shiny")),
                "shiny_buff_id": _int(row.get("shiny_buff_id")),
                "shiny_replacement_mod_code": _int(row.get("shiny_replacement_mod_code")),
            }
            shiny_missing: list[Any] = []
            shiny_result = "PROVEN"
            if row.get("is_shiny") and not shiny_evidence["shiny_buff_id"]:
                shiny_result = "PARTIAL"
                shiny_missing.append("Shiny buff owner")
            claims.append(_claim(
                "mod.shiny_classification", canonical_id, shiny_result,
                evidence=[shiny_evidence], missing=shiny_missing,
                dependencies=[PROPERTY_TABLE], requirements=["exact is_shiny_mod owner", "Shiny-only buff owner when applicable"],
            ))
            if shiny_evidence["shiny_buff_id"]:
                edges.append(_edge(
                    canonical_id, f"buff:{shiny_evidence['shiny_buff_id']}", "mod-shiny-buff-owner",
                    source_table=PROPERTY_TABLE, source_record=mod_code,
                    selector="/shiny_buff_id", authority="exact-mod-property-selector",
                ))
        else:
            claims.append(_claim(
                "mod.shiny_classification", canonical_id, "UNRESOLVED",
                missing=["exact new_mod_property_data owner"], dependencies=[PROPERTY_TABLE],
                requirements=["exact is_shiny_mod owner"],
            ))

        frame_code = _int(row.get("frame_code"))
        if property_owner and frame_code and frame.get("status") == PROVEN_FRAME_STATUS:
            claims.append(_claim(
                "mod.suffix_frame_family", canonical_id, "PARTIAL",
                evidence=[{"frame_code": frame_code, "sub_entry_ids": sub_ids, "source_order": sub_ids}],
                missing=["runtime consumer proving source-order position -> frame_lv_1..4 mapping"],
                dependencies=[PROPERTY_TABLE, FRAME_TABLE, ENTRY_TABLE],
                requirements=["exact frame owner", "exact sub-entry families", "runtime positional consumer for suffix level assignment"],
            ))
            edges.append(_edge(
                canonical_id, f"mod-frame:{frame_code}", "mod-frame-family",
                source_table=PROPERTY_TABLE, source_record=mod_code,
                selector="/frame", authority="exact-mod-property-selector",
            ))
        else:
            claims.append(_claim(
                "mod.suffix_frame_family", canonical_id, "UNRESOLVED",
                missing=["exact frame owner/family evidence"],
                dependencies=[PROPERTY_TABLE, FRAME_TABLE, ENTRY_TABLE],
                requirements=["exact frame owner", "exact four sub-entry families"],
            ))

        gain_path = str(row.get("gain_path") or web_row.get("gain_path") or "").strip()
        if gain_path:
            claims.append(_claim(
                "mod.acquisition", canonical_id, "PROVEN", evidence=[{"gain_path": gain_path}],
                dependencies=["game_common/data/item_data.json"], requirements=["localized installed-game gain path"],
            ))
        else:
            claims.append(_claim(
                "mod.acquisition", canonical_id, "UNRESOLVED", missing=["localized gain path owner"],
                dependencies=["game_common/data/item_data.json"], requirements=["localized installed-game gain path"],
            ))

        if main_entry and effects:
            unresolved_effects = []
            effect_evidence = []
            for effect in effects:
                level = _int(effect.get("level"))
                attrs = [str(value) for value in effect.get("attribute_codes", []) if str(value).strip()]
                buff_id = _int(effect.get("buff_id"))
                if not attrs and not buff_id:
                    unresolved_effects.append({"level": level, "missing": "attribute or buff effect owner"})
                effect_evidence.append({
                    "level": level,
                    "attribute_codes": attrs,
                    "attribute_values": effect.get("attribute_values") or [],
                    "buff_id": buff_id,
                    "description": effect.get("description") or "",
                })
            effect_result = "PARTIAL" if unresolved_effects else "PROVEN"
            claims.append(_claim(
                "mod.effect_ownership", canonical_id, effect_result,
                evidence=[{"main_entry_code": main_entry, "levels": effect_evidence}],
                missing=unresolved_effects,
                dependencies=[ENTRY_TABLE],
                requirements=["exact main_entry_no", "each effect row names an attribute or buff owner"],
            ))
        else:
            claims.append(_claim(
                "mod.effect_ownership", canonical_id, "UNRESOLVED",
                missing=["main entry owner or mod_entry_data consumer rows"], dependencies=[PROPERTY_TABLE, ENTRY_TABLE],
                requirements=["exact main_entry_no", "effect owner rows"],
            ))

        image = str(row.get("image_reference") or web_row.get("image_reference") or "").strip()
        if image:
            claims.append(_claim(
                "mod.artwork", canonical_id, "PROVEN", evidence=[{"image_reference": image}],
                dependencies=["game_common/data/item_data.json"], requirements=["exact item artwork reference"],
            ))
        else:
            claims.append(_claim(
                "mod.artwork", canonical_id, "UNRESOLVED", missing=["item artwork reference"],
                dependencies=["game_common/data/item_data.json"], requirements=["exact item artwork reference"],
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
                "phase": 7,
                "mod_system": CURRENT_MOD_SYSTEM,
                "legacy_random_roll_records_mixed": False,
                "family_canonical_id": family_id,
                "frame_position_mapping_proven": False,
                "publication_authority": False,
            },
        }
        errors = validate_generalized_graph(payload)
        if errors:
            raise ValueError(f"Mod adapter produced invalid graph: {errors}")
        return payload

    def identify(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        return self.graph(identity, **kwargs)["entity"]

    def claims(self, identity: object, **kwargs: Any) -> list[dict[str, Any]]:
        return self.graph(identity, **kwargs)["claims"]

    def resolve_claim(self, identity: object, claim_type: str, **kwargs: Any) -> dict[str, Any]:
        requested = str(claim_type or "").strip()
        if requested not in self.contract.supported_claims:
            raise KeyError(f"Unsupported Mod claim: {claim_type}")
        matches = [row for row in self.claims(identity, **kwargs) if row.get("claim_type") == requested]
        if len(matches) != 1:
            raise KeyError(f"No unique Mod claim resolved for: {claim_type}")
        return matches[0]

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
        return {
            "entity_type": "mod",
            "canonical_id": entity["canonical_id"],
            "name": entity["name"],
            "classification": entity["classification"],
            "identity_state": entity["identity_state"],
            "assessment": graph["assessment"]["result"],
            "family_canonical_id": graph["compatibility"]["family_canonical_id"],
            "publication_authority": False,
        }
