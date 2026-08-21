"""Typed Cradle adapter for the generalized Dead Signal Evidence Graph.

Phase 8 reuses the installed-data active Cradle corpus produced by
``dead_signal_cradle_applicability``. Inactive legacy entries are never admitted
into the graph. Weapon applicability is recomputed from exact positive
``hold_item_check(type/sub_type)`` selectors and compared with the published
weapon-side compatibility lists. Scenario/season membership remains a separate
gate and is never collapsed into one current-scenario claim.
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

ENTRY_TABLE = "game_common/data/cradle_override_entry_data.json"
CONFIG_TABLE = "game_common/data/cradle_override_config_new_data.json"
ITEM_TABLE = "game_common/data/item_data.json"
BUFF_TABLE = "game_common/data/buff/buff_data*.json"
LOGIC_TABLE = "game_common/data/logic_tree/<buff logic_tree_data>.json"
REPORT = "published/reports/weapon-cradle-applicability.json"
PROVEN_SELECTOR = "weapon-selector-exact"
UNRESOLVED_SELECTOR = "weapon-relation-unresolved"
NOT_WEAPON_SELECTED = "not-weapon-selected"

CRADLE_CONTRACT = AdapterContract(
    entity_type="cradle",
    identity_seeds=("cradle_id", "entry_id"),
    canonical_owner_tables=(
        "published/web/cradles.json",
        "published/data/cradles.json",
        ENTRY_TABLE,
        CONFIG_TABLE,
        BUFF_TABLE,
        LOGIC_TABLE,
    ),
    allowed_outbound_fields=(
        "entry_id",
        "buff_id",
        "keyword_id",
        "style_code",
        "active_config_keys",
        "active_season_ids",
        "positive_item_selectors",
    ),
    typed_destination_tables=(
        ("entry_id", (ENTRY_TABLE, CONFIG_TABLE)),
        ("buff_id", (ENTRY_TABLE, BUFF_TABLE)),
        ("keyword_id", (ENTRY_TABLE,)),
        ("style_code", (ENTRY_TABLE,)),
        ("active_config_keys", (CONFIG_TABLE,)),
        ("active_season_ids", (CONFIG_TABLE,)),
        ("positive_item_selectors", (LOGIC_TABLE, ITEM_TABLE)),
    ),
    collision_prone_fields=(
        "entry_id",
        "buff_id",
        "keyword_id",
        "style_code",
        "active_config_keys",
        "active_season_ids",
        "positive_item_selectors",
    ),
    blocked_generic_fields=("id", "no", "code", "record_id"),
    terminal_presentation_fields=(
        "name",
        "description",
        "image_reference",
        "selected_image_reference",
        "equipped_image_reference",
        "disabled_image_reference",
    ),
    supported_claims=(
        "cradle.exact_identity",
        "cradle.active_configuration",
        "cradle.slot",
        "cradle.effect_owner",
        "cradle.weapon_applicability",
        "cradle.weapon_direction_consistency",
        "cradle.scenario_availability",
        "cradle.artwork",
    ),
    applicability_rules=(
        "only entries referenced by installed override_unlock_lst are active Cradles",
        "inactive legacy entries never enter the current graph",
        "positive hold_item_check type/sub_type selectors prove weapon applicability",
        "raw attack/keyword selectors remain unresolved",
        "absence of a weapon selector means NOT APPLICABLE to weapon selection, not that the Cradle effect is unusable",
        "scenario/season membership is evaluated separately from weapon applicability",
    ),
)


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cradle adapter could not read {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Cradle adapter expected an object: {path}")
    return value


def _family_variants(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in payload.get("families", []):
        if not isinstance(family, dict):
            continue
        family_id = str(family.get("canonical_id") or "")
        for variant in family.get("variants", []):
            if not isinstance(variant, dict):
                continue
            row = dict(variant)
            entry_id = row.get("id")
            if entry_id in (None, ""):
                continue
            row.setdefault("cradle_id", entry_id)
            row.setdefault("canonical_id", f"ds-cradle-{entry_id}")
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
        "subject": {"entity_type": "cradle", "canonical_id": canonical_id},
        "result": result,
        "requirements": requirements or ["exact typed Cradle evidence"],
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
    source = f"cradle:{canonical_id}"
    fingerprint = dependency_fingerprint(
        source,
        destination,
        relationship_type,
        source_table,
        source_record,
        selector,
        "base-current-merged",
        authority,
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
        return int(value)
    except (TypeError, ValueError):
        return 0


class CradleAdapter(EvidenceDomainAdapter):
    contract = CRADLE_CONTRACT

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
            raise ValueError("Cradle published source must stay inside the Miner output folder") from exc
        return published

    def _sources(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        published = self._published()
        return (
            _read(published / "web" / "cradles.json"),
            _read(published / "data" / "cradles.json"),
            _read(published / "data" / "weapons.json"),
            _read(published / "reports" / "weapon-cradle-applicability.json"),
        )

    @staticmethod
    def _active_rows(web: dict[str, Any]) -> list[dict[str, Any]]:
        return [row for row in _family_variants(web) if row.get("active_config_keys")]

    @staticmethod
    def _match(identity: object, rows: list[dict[str, Any]]) -> dict[str, Any]:
        needle = str(identity or "").strip()
        if not needle:
            raise KeyError("Cradle identity is empty")
        matches = []
        for row in rows:
            aliases = {
                str(row.get("canonical_id") or ""),
                str(row.get("cradle_id") or row.get("id") or ""),
            }
            if needle in aliases:
                matches.append(row)
        if not matches:
            raise KeyError(f"Unknown active Cradle identity: {identity}")
        if len(matches) != 1:
            raise ValueError(f"Ambiguous Cradle identity: {identity}")
        return matches[0]

    @staticmethod
    def _data_row(entry_id: int, data: dict[str, Any]) -> dict[str, Any]:
        matches = [
            row for row in data.get("cradles", [])
            if isinstance(row, dict) and _int(row.get("id")) == entry_id
        ]
        if len(matches) != 1:
            raise ValueError(f"Cradle normalized owner must resolve exactly once: {entry_id}")
        return matches[0]

    @staticmethod
    def _selector(entry_id: int, report: dict[str, Any]) -> dict[str, Any]:
        matches = [
            row for row in report.get("selectors", [])
            if isinstance(row, dict) and _int(row.get("entry_id")) == entry_id
        ]
        if len(matches) != 1:
            raise ValueError(f"Active Cradle selector evidence must resolve exactly once: {entry_id}")
        return matches[0]

    @staticmethod
    def _reverse_relationships(entry_id: int, selector: dict[str, Any], weapons: dict[str, Any]) -> dict[str, list[str]]:
        result = {"compatible": [], "incompatible": [], "unresolved": [], "not_applicable": []}
        state = str(selector.get("state") or "")
        allowed = {
            (_int(row.get("item_type")), _int(row.get("item_sub_type")))
            for row in selector.get("positive_item_selectors", [])
            if isinstance(row, dict)
        }
        for weapon in weapons.get("weapons", []):
            if not isinstance(weapon, dict):
                continue
            canonical_id = str(weapon.get("canonical_id") or weapon.get("blueprint_id") or weapon.get("item_id") or "")
            cradle = ((weapon.get("compatibility") or {}).get("cradle") or {})
            item_selector = cradle.get("item_selector") or {}
            pair = (_int(item_selector.get("item_type")), _int(item_selector.get("item_sub_type")))
            if state == PROVEN_SELECTOR:
                bucket = "compatible" if pair in allowed and pair != (0, 0) else "incompatible"
            elif state == UNRESOLVED_SELECTOR:
                bucket = "unresolved"
            else:
                bucket = "not_applicable"
            result[bucket].append(canonical_id)
        for bucket in result:
            result[bucket].sort()
        return result

    @staticmethod
    def _weapon_side(entry_id: int, weapons: dict[str, Any]) -> dict[str, list[str]]:
        result = {"compatible": [], "incompatible": [], "unresolved": [], "not_applicable": []}
        for weapon in weapons.get("weapons", []):
            if not isinstance(weapon, dict):
                continue
            canonical_id = str(weapon.get("canonical_id") or weapon.get("blueprint_id") or weapon.get("item_id") or "")
            cradle = ((weapon.get("compatibility") or {}).get("cradle") or {})
            if entry_id in [_int(value) for value in cradle.get("compatible_exact_ids", [])]:
                result["compatible"].append(canonical_id)
            elif entry_id in [_int(value) for value in cradle.get("incompatible_exact_ids", [])]:
                result["incompatible"].append(canonical_id)
            elif entry_id in [_int(value) for value in cradle.get("unresolved_ids", [])]:
                result["unresolved"].append(canonical_id)
            else:
                result["not_applicable"].append(canonical_id)
        for bucket in result:
            result[bucket].sort()
        return result

    def graph(self, identity: object, **_: Any) -> dict[str, Any]:
        web, data, weapons, report = self._sources()
        active_rows = self._active_rows(web)
        row = self._match(identity, active_rows)
        entry_id = _int(row.get("cradle_id") or row.get("id"))
        data_row = self._data_row(entry_id, data)
        selector = self._selector(entry_id, report)
        canonical_id = str(row.get("canonical_id") or f"ds-cradle-{entry_id}")
        config_keys = sorted({str(value) for value in row.get("active_config_keys", []) if str(value).strip()})
        season_ids = sorted({str(value) for value in row.get("active_season_ids", []) if str(value).strip()})

        entity = {
            "schema_version": ENTITY_SCHEMA_VERSION,
            "entity_type": "cradle",
            "canonical_id": canonical_id,
            "name": str(row.get("name") or data_row.get("name") or f"Cradle {entry_id}"),
            "classification": "Active Cradle",
            "identity_state": "PROVEN",
            "source_records": [
                {"table": ENTRY_TABLE, "record_id": str(entry_id), "layer": "base-current-merged"},
                {"table": CONFIG_TABLE, "record_id": key, "layer": "base-current-merged"}
                for key in config_keys
            ],
        }

        claims: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        claims.append(_claim(
            "cradle.exact_identity", canonical_id, "PROVEN",
            evidence=[{"entry_id": entry_id, "active_config_keys": config_keys}],
            dependencies=[ENTRY_TABLE, CONFIG_TABLE],
            requirements=["exact cradle entry", "membership in at least one installed active configuration"],
        ))
        for key in config_keys:
            edges.append(_edge(
                canonical_id, f"cradle-config:{key}", "active-cradle-configuration",
                source_table=CONFIG_TABLE, source_record=key,
                selector="/override_unlock_lst", authority="exact-active-cradle-membership",
            ))

        claims.append(_claim(
            "cradle.active_configuration", canonical_id, "PROVEN",
            evidence=[{"config_keys": config_keys, "season_ids": season_ids}],
            dependencies=[CONFIG_TABLE],
            requirements=["exact installed override_unlock_lst membership"],
        ))

        claims.append(_claim(
            "cradle.slot", canonical_id, "UNRESOLVED",
            missing=["exact outer override_unlock_lst slot/group position is not retained by the current published report"],
            dependencies=[CONFIG_TABLE],
            requirements=["exact configuration slot position owner"],
        ))

        buff_id = _int(data_row.get("buff_id"))
        visited = [_int(value) for value in selector.get("visited_buff_ids", []) if _int(value)]
        logic_trees = [str(value) for value in selector.get("logic_trees", []) if str(value).strip()]
        effect_evidence = []
        effect_missing = []
        if buff_id:
            effect_evidence.append({"buff_id": buff_id})
            edges.append(_edge(
                canonical_id, f"buff:{buff_id}", "cradle-effect-buff-owner",
                source_table=ENTRY_TABLE, source_record=entry_id,
                selector="/buff_id", authority="exact-cradle-entry-buff-reference",
            ))
        else:
            effect_missing.append("entry buff_id owner")
        if visited:
            effect_evidence.append({"visited_buff_ids": visited, "logic_trees": logic_trees})
        elif buff_id:
            effect_missing.append("buff/logic-tree consumer chain")
        effect_result = "PROVEN" if effect_evidence and not effect_missing else "PARTIAL" if effect_evidence else "UNRESOLVED"
        claims.append(_claim(
            "cradle.effect_owner", canonical_id, effect_result,
            evidence=effect_evidence, missing=effect_missing,
            dependencies=[ENTRY_TABLE, BUFF_TABLE, LOGIC_TABLE],
            requirements=["exact entry buff reference", "retained buff/logic-tree consumer evidence"],
        ))

        state = str(selector.get("state") or "")
        positive = selector.get("positive_item_selectors") or []
        if state == PROVEN_SELECTOR:
            applicability_result = "PROVEN"
            applicability_evidence = [{"state": state, "positive_item_selectors": positive}]
            applicability_missing = []
        elif state == UNRESOLVED_SELECTOR:
            applicability_result = "UNRESOLVED"
            applicability_evidence = [{"state": state, "raw_selectors": selector.get("unresolved_raw_selectors") or []}]
            applicability_missing = ["typed weapon meaning for raw attack/keyword/weapon selectors"]
        else:
            applicability_result = "NOT APPLICABLE"
            applicability_evidence = [{"state": NOT_WEAPON_SELECTED}]
            applicability_missing = []
        claims.append(_claim(
            "cradle.weapon_applicability", canonical_id, applicability_result,
            evidence=applicability_evidence, missing=applicability_missing,
            dependencies=[REPORT, LOGIC_TABLE, ITEM_TABLE],
            requirements=["exact positive hold_item_check type/sub_type or explicitly unresolved raw selector"],
        ))
        for selected in positive:
            if not isinstance(selected, dict):
                continue
            item_type = _int(selected.get("item_type"))
            item_sub_type = _int(selected.get("item_sub_type"))
            edges.append(_edge(
                canonical_id,
                f"weapon-item-selector:{item_type}:{item_sub_type}",
                "cradle-positive-weapon-selector",
                source_table=LOGIC_TABLE,
                source_record=entry_id,
                selector="hold_item_check(type/sub_type)",
                authority="exact-positive-hold-item-check",
            ))

        reverse = self._reverse_relationships(entry_id, selector, weapons)
        forward = self._weapon_side(entry_id, weapons)
        if reverse == forward:
            consistency_result = "PROVEN"
            conflicts: list[Any] = []
        else:
            consistency_result = "CONFLICT"
            conflicts = [{"cradle_to_weapon": reverse, "weapon_to_cradle": forward}]
        claims.append(_claim(
            "cradle.weapon_direction_consistency", canonical_id, consistency_result,
            evidence=[{"cradle_to_weapon": reverse, "weapon_to_cradle": forward}],
            conflicts=conflicts,
            dependencies=[REPORT, "published/data/weapons.json"],
            requirements=["Cradle-to-weapon recomputation must equal weapon-to-Cradle publication"],
        ))

        if config_keys:
            scenario_result = "PARTIAL"
            scenario_evidence = [{"config_keys": config_keys, "season_ids": season_ids}]
            scenario_missing = ["current runtime scenario/config selection proving this membership is active now"]
        else:
            scenario_result = "UNRESOLVED"
            scenario_evidence = []
            scenario_missing = ["active configuration membership"]
        claims.append(_claim(
            "cradle.scenario_availability", canonical_id, scenario_result,
            evidence=scenario_evidence, missing=scenario_missing,
            dependencies=[CONFIG_TABLE],
            requirements=["installed configuration/season membership", "separate current-scenario gate"],
        ))

        images = {
            key: str(data_row.get(key) or row.get(key) or "").strip()
            for key in (
                "image_reference",
                "selected_image_reference",
                "equipped_image_reference",
                "disabled_image_reference",
            )
        }
        present_images = {key: value for key, value in images.items() if value}
        if present_images:
            claims.append(_claim(
                "cradle.artwork", canonical_id, "PROVEN",
                evidence=[present_images], dependencies=[ENTRY_TABLE],
                requirements=["exact Cradle entry artwork reference"],
            ))
        else:
            claims.append(_claim(
                "cradle.artwork", canonical_id, "UNRESOLVED",
                missing=["Cradle entry artwork reference"], dependencies=[ENTRY_TABLE],
                requirements=["exact Cradle entry artwork reference"],
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
                "phase": 8,
                "active_corpus_size": len(active_rows),
                "inactive_legacy_leakage": False,
                "weapon_relationships": reverse,
                "scenario_gate_separate": True,
                "publication_authority": False,
            },
        }
        errors = validate_generalized_graph(payload)
        if errors:
            raise ValueError(f"Cradle adapter produced invalid graph: {errors}")
        return payload

    def identify(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        return self.graph(identity, **kwargs)["entity"]

    def claims(self, identity: object, **kwargs: Any) -> list[dict[str, Any]]:
        return self.graph(identity, **kwargs)["claims"]

    def resolve_claim(self, identity: object, claim_type: str, **kwargs: Any) -> dict[str, Any]:
        requested = str(claim_type or "").strip()
        if requested not in self.contract.supported_claims:
            raise KeyError(f"Unsupported Cradle claim: {claim_type}")
        matches = [row for row in self.claims(identity, **kwargs) if row.get("claim_type") == requested]
        if len(matches) != 1:
            raise KeyError(f"No unique Cradle claim resolved for: {claim_type}")
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
            "entity_type": "cradle",
            "canonical_id": entity["canonical_id"],
            "name": entity["name"],
            "classification": entity["classification"],
            "identity_state": entity["identity_state"],
            "assessment": graph["assessment"]["result"],
            "weapon_relationships": graph["compatibility"]["weapon_relationships"],
            "scenario_gate_separate": True,
            "publication_authority": False,
        }
