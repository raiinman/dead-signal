"""Typed active-Cradle adapter for the generalized Evidence Graph."""
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
REPORT_PATH = "published/reports/weapon-cradle-applicability.json"
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
        "entry_id", "buff_id", "keyword_id", "style_code",
        "active_config_keys", "active_season_ids", "positive_item_selectors",
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
        "entry_id", "buff_id", "keyword_id", "style_code",
        "active_config_keys", "active_season_ids", "positive_item_selectors",
    ),
    blocked_generic_fields=("id", "no", "code", "record_id"),
    terminal_presentation_fields=(
        "name", "description", "image_reference", "selected_image_reference",
        "equipped_image_reference", "disabled_image_reference",
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
        "only installed override_unlock_lst members enter the active graph",
        "inactive legacy entries are excluded",
        "positive hold_item_check type/sub_type selectors prove weapon applicability",
        "raw attack/keyword selectors remain unresolved",
        "no weapon selector means NOT APPLICABLE to weapon selection only",
        "scenario membership stays separate from weapon applicability",
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


def _int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _variants(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in payload.get("families", []):
        if not isinstance(family, dict):
            continue
        for variant in family.get("variants", []):
            if not isinstance(variant, dict) or variant.get("id") in (None, ""):
                continue
            row = dict(variant)
            row.setdefault("cradle_id", row["id"])
            row.setdefault("canonical_id", f"ds-cradle-{row['id']}")
            row["family_canonical_id"] = family.get("canonical_id")
            rows.append(row)
    return rows


def _claim(kind: str, canonical_id: str, result: str, *, evidence=None, missing=None, conflicts=None, dependencies=None, requirements=None) -> dict[str, Any]:
    return {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "claim_type": kind,
        "subject": {"entity_type": "cradle", "canonical_id": canonical_id},
        "result": result,
        "requirements": requirements or ["exact typed Cradle evidence"],
        "evidence": evidence or [],
        "missing": missing or [],
        "conflicts": conflicts or [],
        "dependencies": dependencies or [],
    }


def _edge(canonical_id: str, destination: str, relation: str, *, table: str, record: object, selector: str, authority: str) -> dict[str, Any]:
    source = f"cradle:{canonical_id}"
    return {
        "schema_version": EDGE_SCHEMA_VERSION,
        "source": source,
        "destination": destination,
        "relationship_type": relation,
        "source_table": table,
        "source_record": str(record),
        "selector": selector,
        "layer": "base-current-merged",
        "authority": authority,
        "state": "PROVEN",
        "dependency_fingerprint": dependency_fingerprint(
            source, destination, relation, table, record, selector,
            "base-current-merged", authority,
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
            raise ValueError("Cradle published source must stay inside Miner output") from exc
        return published

    def _sources(self):
        published = self._published()
        return (
            _read(published / "web" / "cradles.json"),
            _read(published / "data" / "cradles.json"),
            _read(published / "data" / "weapons.json"),
            _read(published / "reports" / "weapon-cradle-applicability.json"),
        )

    @staticmethod
    def _active_rows(web: dict[str, Any]) -> list[dict[str, Any]]:
        return [row for row in _variants(web) if row.get("active_config_keys")]

    @staticmethod
    def _match(identity: object, rows: list[dict[str, Any]]) -> dict[str, Any]:
        needle = str(identity or "").strip()
        matches = [
            row for row in rows
            if needle in {str(row.get("canonical_id") or ""), str(row.get("cradle_id") or row.get("id") or "")}
        ]
        if not matches:
            raise KeyError(f"Unknown active Cradle identity: {identity}")
        if len(matches) != 1:
            raise ValueError(f"Ambiguous Cradle identity: {identity}")
        return matches[0]

    @staticmethod
    def _one_by_id(rows: list[Any], entry_id: int, field: str) -> dict[str, Any]:
        matches = [row for row in rows if isinstance(row, dict) and _int(row.get(field)) == entry_id]
        if len(matches) != 1:
            raise ValueError(f"Cradle owner must resolve exactly once: {entry_id}")
        return matches[0]

    @staticmethod
    def _reverse(selector: dict[str, Any], weapons: dict[str, Any]) -> dict[str, list[str]]:
        result = {"compatible": [], "incompatible": [], "unresolved": [], "not_applicable": []}
        state = str(selector.get("state") or "")
        allowed = {
            (_int(row.get("item_type")), _int(row.get("item_sub_type")))
            for row in selector.get("positive_item_selectors", []) if isinstance(row, dict)
        }
        for weapon in weapons.get("weapons", []):
            if not isinstance(weapon, dict):
                continue
            wid = str(weapon.get("canonical_id") or weapon.get("blueprint_id") or weapon.get("item_id") or "")
            cradle = ((weapon.get("compatibility") or {}).get("cradle") or {})
            item = cradle.get("item_selector") or {}
            pair = (_int(item.get("item_type")), _int(item.get("item_sub_type")))
            if state == PROVEN_SELECTOR:
                bucket = "compatible" if pair != (0, 0) and pair in allowed else "incompatible"
            elif state == UNRESOLVED_SELECTOR:
                bucket = "unresolved"
            else:
                bucket = "not_applicable"
            result[bucket].append(wid)
        for values in result.values():
            values.sort()
        return result

    @staticmethod
    def _forward(entry_id: int, weapons: dict[str, Any]) -> dict[str, list[str]]:
        result = {"compatible": [], "incompatible": [], "unresolved": [], "not_applicable": []}
        for weapon in weapons.get("weapons", []):
            if not isinstance(weapon, dict):
                continue
            wid = str(weapon.get("canonical_id") or weapon.get("blueprint_id") or weapon.get("item_id") or "")
            cradle = ((weapon.get("compatibility") or {}).get("cradle") or {})
            if entry_id in [_int(v) for v in cradle.get("compatible_exact_ids", [])]:
                bucket = "compatible"
            elif entry_id in [_int(v) for v in cradle.get("incompatible_exact_ids", [])]:
                bucket = "incompatible"
            elif entry_id in [_int(v) for v in cradle.get("unresolved_ids", [])]:
                bucket = "unresolved"
            else:
                bucket = "not_applicable"
            result[bucket].append(wid)
        for values in result.values():
            values.sort()
        return result

    def graph(self, identity: object, **_: Any) -> dict[str, Any]:
        web, data, weapons, report = self._sources()
        active = self._active_rows(web)
        row = self._match(identity, active)
        entry_id = _int(row.get("cradle_id") or row.get("id"))
        data_row = self._one_by_id(data.get("cradles", []), entry_id, "id")
        selector = self._one_by_id(report.get("selectors", []), entry_id, "entry_id")
        canonical_id = str(row.get("canonical_id") or f"ds-cradle-{entry_id}")
        configs = sorted({str(v) for v in row.get("active_config_keys", []) if str(v).strip()})
        seasons = sorted({str(v) for v in row.get("active_season_ids", []) if str(v).strip()})

        entity = {
            "schema_version": ENTITY_SCHEMA_VERSION,
            "entity_type": "cradle",
            "canonical_id": canonical_id,
            "name": str(row.get("name") or data_row.get("name") or f"Cradle {entry_id}"),
            "classification": "Active Cradle",
            "identity_state": "PROVEN",
            "source_records": (
                [{"table": ENTRY_TABLE, "record_id": str(entry_id), "layer": "base-current-merged"}]
                + [{"table": CONFIG_TABLE, "record_id": key, "layer": "base-current-merged"} for key in configs]
            ),
        }
        claims: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        claims.append(_claim(
            "cradle.exact_identity", canonical_id, "PROVEN",
            evidence=[{"entry_id": entry_id, "active_config_keys": configs}],
            dependencies=[ENTRY_TABLE, CONFIG_TABLE],
            requirements=["exact entry owner", "at least one active configuration membership"],
        ))
        claims.append(_claim(
            "cradle.active_configuration", canonical_id, "PROVEN",
            evidence=[{"config_keys": configs, "season_ids": seasons}],
            dependencies=[CONFIG_TABLE],
            requirements=["exact override_unlock_lst membership"],
        ))
        for key in configs:
            edges.append(_edge(
                canonical_id, f"cradle-config:{key}", "active-cradle-configuration",
                table=CONFIG_TABLE, record=key, selector="/override_unlock_lst",
                authority="exact-active-cradle-membership",
            ))

        # The current report preserves membership but not the nested outer-list
        # position. Fail closed until that exact slot/group owner is retained.
        claims.append(_claim(
            "cradle.slot", canonical_id, "UNRESOLVED",
            missing=["outer override_unlock_lst slot/group position not retained in published evidence"],
            dependencies=[CONFIG_TABLE],
            requirements=["exact configuration slot position owner"],
        ))

        buff_id = _int(data_row.get("buff_id"))
        visited = [_int(v) for v in selector.get("visited_buff_ids", []) if _int(v)]
        logic_trees = [str(v) for v in selector.get("logic_trees", []) if str(v).strip()]
        effect_evidence = []
        effect_missing = []
        if buff_id:
            effect_evidence.append({"buff_id": buff_id})
            edges.append(_edge(
                canonical_id, f"buff:{buff_id}", "cradle-effect-buff-owner",
                table=ENTRY_TABLE, record=entry_id, selector="/buff_id",
                authority="exact-cradle-entry-buff-reference",
            ))
        else:
            effect_missing.append("entry buff_id owner")
        if visited:
            effect_evidence.append({"visited_buff_ids": visited, "logic_trees": logic_trees})
        elif buff_id:
            effect_missing.append("retained buff/logic-tree consumer chain")
        effect_result = "PROVEN" if effect_evidence and not effect_missing else "PARTIAL" if effect_evidence else "UNRESOLVED"
        claims.append(_claim(
            "cradle.effect_owner", canonical_id, effect_result,
            evidence=effect_evidence, missing=effect_missing,
            dependencies=[ENTRY_TABLE, BUFF_TABLE, LOGIC_TABLE],
            requirements=["exact entry buff reference", "retained consumer chain"],
        ))

        selector_state = str(selector.get("state") or "")
        positive = selector.get("positive_item_selectors") or []
        if selector_state == PROVEN_SELECTOR:
            app_result, app_missing = "PROVEN", []
            app_evidence = [{"state": selector_state, "positive_item_selectors": positive}]
        elif selector_state == UNRESOLVED_SELECTOR:
            app_result = "UNRESOLVED"
            app_missing = ["typed meaning for raw attack/keyword/weapon selectors"]
            app_evidence = [{"state": selector_state, "raw_selectors": selector.get("unresolved_raw_selectors") or []}]
        else:
            app_result, app_missing = "NOT APPLICABLE", []
            app_evidence = [{"state": NOT_WEAPON_SELECTED}]
        claims.append(_claim(
            "cradle.weapon_applicability", canonical_id, app_result,
            evidence=app_evidence, missing=app_missing,
            dependencies=[REPORT_PATH, LOGIC_TABLE, ITEM_TABLE],
            requirements=["exact positive hold_item_check selector or explicitly unresolved raw selector"],
        ))
        for selected in positive:
            if not isinstance(selected, dict):
                continue
            item_type, subtype = _int(selected.get("item_type")), _int(selected.get("item_sub_type"))
            edges.append(_edge(
                canonical_id, f"weapon-item-selector:{item_type}:{subtype}", "cradle-positive-weapon-selector",
                table=LOGIC_TABLE, record=entry_id, selector="hold_item_check(type/sub_type)",
                authority="exact-positive-hold-item-check",
            ))

        reverse = self._reverse(selector, weapons)
        forward = self._forward(entry_id, weapons)
        same = reverse == forward
        claims.append(_claim(
            "cradle.weapon_direction_consistency", canonical_id, "PROVEN" if same else "CONFLICT",
            evidence=[{"cradle_to_weapon": reverse, "weapon_to_cradle": forward}],
            conflicts=[] if same else [{"cradle_to_weapon": reverse, "weapon_to_cradle": forward}],
            dependencies=[REPORT_PATH, "published/data/weapons.json"],
            requirements=["Cradle-to-weapon recomputation equals weapon-to-Cradle projection"],
        ))

        claims.append(_claim(
            "cradle.scenario_availability", canonical_id, "PARTIAL",
            evidence=[{"config_keys": configs, "season_ids": seasons}],
            missing=["current runtime scenario/config selection"],
            dependencies=[CONFIG_TABLE],
            requirements=["installed config/season membership", "separate current-scenario gate"],
        ))

        images = {
            key: str(data_row.get(key) or row.get(key) or "").strip()
            for key in ("image_reference", "selected_image_reference", "equipped_image_reference", "disabled_image_reference")
        }
        present = {key: value for key, value in images.items() if value}
        claims.append(_claim(
            "cradle.artwork", canonical_id, "PROVEN" if present else "UNRESOLVED",
            evidence=[present] if present else [],
            missing=[] if present else ["Cradle entry artwork reference"],
            dependencies=[ENTRY_TABLE],
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
                "active_corpus_size": len(active),
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
            dep for claim in self.claims(identity, **kwargs)
            for dep in claim.get("dependencies", []) if str(dep or "").strip()
        })

    def presentation(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        graph = self.graph(identity, **kwargs)
        entity = graph["entity"]
        return {
            "entity_type": "cradle",
            "canonical_id": entity["canonical_id"],
            "name": entity["name"],
            "classification": entity["classification"],
            "assessment": graph["assessment"]["result"],
            "scenario_gate_separate": True,
            "publication_authority": False,
        }
