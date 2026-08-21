"""Typed Calibration Blueprint adapter for the generalized Dead Signal Evidence Graph.

The adapter keeps current Calibration Blueprints separate from unresolved/legacy
gear-calibration material, uses exact weapon type selectors only, and preserves
raw roll weights without inventing probabilities.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from dead_signal_calibration_relations import (
    FOUR_STATE_RELATIONSHIPS,
    PRINT_SOURCE_TABLE,
    calibration_system_classification,
    calibration_weapon_relation,
    exact_print_owner,
    invert_weapon_calibration_states,
    is_current_calibration_blueprint,
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


CALIBRATION_CONTRACT = AdapterContract(
    entity_type="calibration",
    identity_seeds=("calibration_id", "item_id", "group_id", "style_code"),
    canonical_owner_tables=(
        "published/web/calibrations.json",
        "game_common/data/item_data.json",
        PRINT_SOURCE_TABLE,
        "game_common/data/gun_correct_common_terms_data.json",
    ),
    allowed_outbound_fields=(
        "calibration_id",
        "item_id",
        "group_id",
        "style_code",
        "weapon_type_codes",
        "buff_id",
        "affix_ids",
    ),
    typed_destination_tables=(
        ("calibration_id", (PRINT_SOURCE_TABLE, "game_common/data/item_data.json")),
        ("item_id", ("game_common/data/item_data.json", PRINT_SOURCE_TABLE)),
        ("group_id", (PRINT_SOURCE_TABLE,)),
        ("style_code", (PRINT_SOURCE_TABLE,)),
    ),
    collision_prone_fields=("calibration_id", "item_id", "group_id", "style_code"),
    blocked_generic_fields=("id", "no", "code", "record_id"),
    terminal_presentation_fields=(
        "name", "rarity", "style_code", "weapon_type_codes", "roll_range", "gain_path",
    ),
    supported_claims=(
        "calibration.exact_identity",
        "calibration.style_owner",
        "calibration.weapon_types",
        "calibration.weapon_relationship",
        "calibration.compatibility_consistency",
        "calibration.rarity",
        "calibration.attack_range",
        "calibration.secondary_attribute_pool",
        "calibration.acquisition",
        "calibration.system_classification",
    ),
    applicability_rules=(
        "current Calibration Blueprints require an exact gun_correct_print_data owner",
        "legacy gear calibration is never merged into the current Blueprint lane",
        "weapon compatibility uses exact weapon_type codes only",
        "roll probabilities are never inferred from missing or normalized weights",
        "affix_val_range numeric bounds do not prove combat application semantics",
    ),
)


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Calibration adapter could not read {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Calibration adapter expected an object: {path}")
    return value


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [row for row in payload.get(key, []) if isinstance(row, dict)]


def _web_variants(payload: dict[str, Any]) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for family in payload.get("families", []):
        if not isinstance(family, dict):
            continue
        family_id = str(family.get("canonical_id") or "")
        for row in family.get("variants", []):
            if not isinstance(row, dict):
                continue
            item = dict(row)
            calibration_id = item.get("calibration_id") or item.get("id") or item.get("item_id")
            if calibration_id in (None, ""):
                continue
            item.setdefault("calibration_id", calibration_id)
            item.setdefault("canonical_id", f"ds-cal-var-{calibration_id}")
            item["family_canonical_id"] = family_id
            variants.append(item)
    return variants


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
    subject: dict[str, Any] = {"entity_type": "calibration", "canonical_id": canonical_id}
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
    authority: str,
    state: str,
) -> dict[str, Any]:
    source = f"calibration:{canonical_id}"
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


class CalibrationAdapter(EvidenceDomainAdapter):
    contract = CALIBRATION_CONTRACT

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
            raise ValueError("Calibration published source must stay inside the Miner output folder") from exc
        return published

    def _sources(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        published = self._published()
        return (
            _read(published / "web" / "calibrations.json"),
            _read(published / "data" / "calibrations.json"),
            _read(published / "data" / "weapons.json"),
        )

    @staticmethod
    def _match(identity: object, rows: list[dict[str, Any]]) -> dict[str, Any]:
        needle = str(identity or "").strip()
        if not needle:
            raise KeyError("Calibration identity is empty")
        matches = []
        for row in rows:
            calibration_id = row.get("calibration_id") or row.get("id") or row.get("item_id")
            aliases = {
                str(row.get("canonical_id") or f"ds-cal-var-{calibration_id}"),
                str(calibration_id or ""),
                str(row.get("item_id") or ""),
            }
            if needle in aliases:
                matches.append(row)
        if not matches:
            raise KeyError(f"Unknown exact calibration identity: {identity}")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous exact calibration identity: {identity}")
        return matches[0]

    @staticmethod
    def _data_match(web_row: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
        calibration_id = str(web_row.get("calibration_id") or web_row.get("id") or web_row.get("item_id") or "")
        exact = [
            row for row in rows
            if str(row.get("calibration_id") or row.get("id") or row.get("item_id") or "") == calibration_id
        ]
        if len(exact) != 1:
            raise ValueError(f"Calibration normalized owner must resolve exactly once: {calibration_id}")
        return exact[0]

    def graph(self, identity: object, **_: Any) -> dict[str, Any]:
        web_payload, data_payload, weapon_payload = self._sources()
        web_row = self._match(identity, _web_variants(web_payload))
        data_row = self._data_match(web_row, _rows(data_payload, "calibrations"))
        weapons = _rows(weapon_payload, "weapons")

        calibration_id = data_row.get("calibration_id") or data_row.get("id") or data_row.get("item_id")
        canonical_id = str(web_row.get("canonical_id") or f"ds-cal-var-{calibration_id}")
        item_id = data_row.get("item_id") or calibration_id
        owner_proven = exact_print_owner(data_row)
        system = calibration_system_classification(data_row)
        current = is_current_calibration_blueprint(data_row)

        entity = {
            "schema_version": ENTITY_SCHEMA_VERSION,
            "entity_type": "calibration",
            "canonical_id": canonical_id,
            "name": str(web_row.get("name") or data_row.get("name") or "Unknown Calibration"),
            "classification": system,
            "identity_state": "PROVEN",
            "source_records": [
                {"table": "published/web/calibrations.json", "record_id": canonical_id, "layer": "published-snapshot"},
                {"table": "game_common/data/item_data.json", "record_id": str(item_id), "layer": "base-current-merged"},
            ] + ([{"table": PRINT_SOURCE_TABLE, "record_id": str(calibration_id), "layer": "base-current-merged"}] if owner_proven else []),
        }

        claims: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        claims.append(_claim(
            "calibration.exact_identity", canonical_id, "PROVEN",
            evidence=[{"calibration_id": calibration_id, "item_id": item_id, "family": web_row.get("family_canonical_id")}],
            dependencies=["published/web/calibrations.json", "game_common/data/item_data.json"],
            requirements=["one exact calibration variant", "one exact item identity"],
        ))

        style_code = data_row.get("calibration_style_code") or web_row.get("style_code")
        if owner_proven and style_code not in (None, "", 0, "0"):
            claims.append(_claim(
                "calibration.style_owner", canonical_id, "PROVEN",
                evidence=[{"style_code": style_code, "source_table": PRINT_SOURCE_TABLE}],
                dependencies=[PRINT_SOURCE_TABLE],
                requirements=["exact gun_correct_print_data owner", "non-empty correct_style"],
            ))
            edges.append(_edge(
                canonical_id, f"calibration-style:{style_code}", "calibration-style-owner",
                source_table=PRINT_SOURCE_TABLE, source_record=calibration_id,
                selector="/correct_style", authority="exact-calibration-print-owner", state="PROVEN",
            ))
        else:
            claims.append(_claim(
                "calibration.style_owner", canonical_id, "UNRESOLVED",
                missing=["exact calibration style owner"], dependencies=[PRINT_SOURCE_TABLE],
                requirements=["exact gun_correct_print_data owner", "non-empty correct_style"],
            ))

        if owner_proven:
            claims.append(_claim(
                "calibration.system_classification", canonical_id, "PROVEN",
                evidence=[{"classification": system, "source_table": PRINT_SOURCE_TABLE}],
                dependencies=[PRINT_SOURCE_TABLE],
                requirements=["exact current Calibration Blueprint owner"],
            ))
        else:
            claims.append(_claim(
                "calibration.system_classification", canonical_id, "UNRESOLVED",
                missing=["current or legacy system owner"], dependencies=[PRINT_SOURCE_TABLE],
                requirements=["do not label ownerless subtype-39 items as legacy"],
            ))

        type_codes = []
        for value in data_row.get("weapon_type_codes") or []:
            try:
                number = int(value)
            except (TypeError, ValueError):
                continue
            if number:
                type_codes.append(number)
        type_codes = sorted(set(type_codes))
        if current and type_codes:
            claims.append(_claim(
                "calibration.weapon_types", canonical_id, "PROVEN",
                evidence=[{"weapon_type_codes": type_codes}], dependencies=[PRINT_SOURCE_TABLE],
                requirements=["exact weapon_type_lst on a current Calibration Blueprint owner"],
            ))
            for code in type_codes:
                edges.append(_edge(
                    canonical_id, f"weapon-type:{code}", "calibration-compatible-weapon-type",
                    source_table=PRINT_SOURCE_TABLE, source_record=calibration_id,
                    selector="/weapon_type_lst", authority="exact-calibration-weapon-type-selector", state="PROVEN",
                ))
        else:
            claims.append(_claim(
                "calibration.weapon_types", canonical_id, "UNRESOLVED",
                missing=["current exact weapon_type_lst"], dependencies=[PRINT_SOURCE_TABLE],
                requirements=["current Calibration Blueprint", "non-empty weapon_type_lst"],
            ))

        relationship_conflicts: list[dict[str, Any]] = []
        if current:
            reverse = invert_weapon_calibration_states(weapons, calibration_id)
            reverse_by_weapon: dict[str, list[str]] = {}
            for state, ids in reverse.items():
                for weapon_id in ids:
                    reverse_by_weapon.setdefault(weapon_id, []).append(state)
            for weapon in weapons:
                weapon_id = str(weapon.get("canonical_id") or weapon.get("blueprint_id") or weapon.get("item_id") or "")
                if not weapon_id:
                    continue
                forward = calibration_weapon_relation(weapon, data_row)
                reverse_states = reverse_by_weapon.get(weapon_id, [])
                reverse_state = reverse_states[0] if len(reverse_states) == 1 else None
                if reverse_state != forward:
                    conflict = {"weapon": weapon_id, "forward": forward, "reverse": reverse_states or ["missing"]}
                    relationship_conflicts.append(conflict)
                    result = "CONFLICT"
                    evidence: list[Any] = []
                    conflicts = [conflict]
                else:
                    result = "NOT APPLICABLE" if forward == "not-applicable" else "UNRESOLVED" if forward == "unresolved" else "PROVEN"
                    evidence = [{"forward": forward, "reverse": reverse_state}]
                    conflicts = []
                claims.append(_claim(
                    "calibration.weapon_relationship", canonical_id, result,
                    evidence=evidence,
                    missing=["exact weapon type relationship"] if result == "UNRESOLVED" else [],
                    conflicts=conflicts,
                    dependencies=[PRINT_SOURCE_TABLE, "published/data/weapons.json"],
                    requirements=["shared four-state policy", "weapon-side reverse state agrees"],
                    relationship={"weapon": weapon_id, "state": forward},
                ))
                edges.append(_edge(
                    canonical_id, f"weapon:{weapon_id}", f"calibration-{forward}-weapon",
                    source_table=PRINT_SOURCE_TABLE, source_record=calibration_id,
                    selector="/weapon_type_lst", authority="exact-calibration-weapon-type-selector",
                    state=result,
                ))
            if relationship_conflicts:
                claims.append(_claim(
                    "calibration.compatibility_consistency", canonical_id, "CONFLICT",
                    conflicts=relationship_conflicts,
                    dependencies=[PRINT_SOURCE_TABLE, "published/data/weapons.json"],
                    requirements=["all forward and reverse relationships agree exactly"],
                ))
            elif weapons:
                claims.append(_claim(
                    "calibration.compatibility_consistency", canonical_id, "PROVEN",
                    evidence=[{"weapons_checked": len(weapons), "states": list(FOUR_STATE_RELATIONSHIPS)}],
                    dependencies=[PRINT_SOURCE_TABLE, "published/data/weapons.json"],
                    requirements=["all forward and reverse relationships agree exactly"],
                ))
        else:
            claims.append(_claim(
                "calibration.compatibility_consistency", canonical_id, "UNRESOLVED",
                missing=["current Calibration Blueprint classification"],
                dependencies=[PRINT_SOURCE_TABLE],
                requirements=["legacy or ownerless calibration material cannot enter current compatibility graph"],
            ))

        rarity = str(data_row.get("quality") or web_row.get("rarity") or "").strip()
        if rarity and rarity.casefold() != "unknown":
            claims.append(_claim(
                "calibration.rarity", canonical_id, "PROVEN",
                evidence=[{"rarity": rarity, "quality_code": data_row.get("quality_code")}],
                dependencies=["game_common/data/item_data.json"], requirements=["exact item quality"],
            ))
        else:
            claims.append(_claim(
                "calibration.rarity", canonical_id, "UNRESOLVED",
                missing=["item rarity"], dependencies=["game_common/data/item_data.json"],
                requirements=["exact item quality"],
            ))

        roll_range = data_row.get("calibration_roll_range") or web_row.get("roll_range") or {}
        if roll_range.get("raw_minimum") is not None and roll_range.get("raw_maximum") is not None:
            claims.append(_claim(
                "calibration.attack_range", canonical_id, "PARTIAL",
                evidence=[roll_range],
                missing=["combat application semantics"],
                dependencies=[PRINT_SOURCE_TABLE],
                requirements=["exact affix_val_range", "consumer proof for combat meaning"],
            ))
        else:
            claims.append(_claim(
                "calibration.attack_range", canonical_id, "UNRESOLVED",
                missing=["affix_val_range"], dependencies=[PRINT_SOURCE_TABLE],
                requirements=["exact affix_val_range", "consumer proof for combat meaning"],
            ))

        affix_ids = data_row.get("affix_ids") or []
        weights = data_row.get("affix_ids_weight") or web_row.get("affix_ids_weight") or []
        affixes = data_row.get("affixes") or web_row.get("affixes") or []
        pool_evidence = {
            "affix_ids": affix_ids,
            "raw_weights": weights,
            "affixes": affixes,
            "probability_policy": "Raw exact weights are preserved; probabilities are not inferred or normalized by the Evidence Graph.",
        }
        if affix_ids and weights:
            pool_result = "PROVEN"
            pool_missing: list[Any] = []
        elif affix_ids:
            pool_result = "PARTIAL"
            pool_missing = ["exact affix weights"]
        else:
            pool_result = "UNRESOLVED"
            pool_missing = ["secondary attribute pool"]
        claims.append(_claim(
            "calibration.secondary_attribute_pool", canonical_id, pool_result,
            evidence=[pool_evidence] if affix_ids else [], missing=pool_missing,
            dependencies=[PRINT_SOURCE_TABLE, "game_common/data/gun_correct_common_terms_data.json"],
            requirements=["exact affix IDs", "exact raw weights before any probability statement"],
        ))

        gain_path = str(data_row.get("gain_path") or web_row.get("gain_path") or "").strip()
        if gain_path:
            claims.append(_claim(
                "calibration.acquisition", canonical_id, "PROVEN",
                evidence=[{"gain_path": gain_path}], dependencies=["game_common/data/item_data.json"],
                requirements=["localized installed-game gain path"],
            ))
        else:
            claims.append(_claim(
                "calibration.acquisition", canonical_id, "UNRESOLVED",
                missing=["localized gain path"], dependencies=["game_common/data/item_data.json"],
                requirements=["localized installed-game gain path"],
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
                "phase": 5,
                "system_classification": system,
                "current_calibration_blueprint": current,
                "four_state_relationships": list(FOUR_STATE_RELATIONSHIPS),
                "forward_reverse_agreement": current and not relationship_conflicts,
                "relationship_conflicts": relationship_conflicts,
                "legacy_gear_calibration_mixed": False,
                "publication_authority": False,
            },
        }
        errors = validate_generalized_graph(payload)
        if errors:
            raise ValueError(f"Calibration adapter produced invalid graph: {errors}")
        return payload

    def identify(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        return self.graph(identity, **kwargs)["entity"]

    def claims(self, identity: object, **kwargs: Any) -> list[dict[str, Any]]:
        return self.graph(identity, **kwargs)["claims"]

    def resolve_claim(self, identity: object, claim_type: str, **kwargs: Any) -> dict[str, Any]:
        requested = str(claim_type or "").strip()
        if requested not in self.contract.supported_claims:
            raise KeyError(f"Unsupported calibration claim: {claim_type}")
        matches = [row for row in self.claims(identity, **kwargs) if row.get("claim_type") == requested]
        if not matches:
            raise KeyError(f"No calibration claim resolved for: {claim_type}")
        if len(matches) == 1:
            return matches[0]
        counts = Counter(str(row.get("result")) for row in matches)
        if counts["CONFLICT"]:
            result = "CONFLICT"
        elif counts["UNRESOLVED"] or counts["PARTIAL"]:
            result = "PARTIAL"
        elif counts["PROVEN"]:
            result = "PROVEN"
        else:
            result = "NOT APPLICABLE"
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
        return {
            "entity_type": "calibration",
            "canonical_id": entity["canonical_id"],
            "name": entity["name"],
            "classification": entity["classification"],
            "identity_state": entity["identity_state"],
            "assessment": graph["assessment"]["result"],
            "forward_reverse_agreement": graph["compatibility"]["forward_reverse_agreement"],
            "publication_authority": False,
        }
