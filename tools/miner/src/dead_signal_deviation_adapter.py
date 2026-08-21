"""Typed Deviation adapter for the generalized Dead Signal Evidence Graph.

Deviation source IDs are canonical variant identity. Display names are browse
aliases only and never merge variants or establish ownership. Player-facing
skills are separated from exact skill-ID ownership, while acquisition and
scenario availability stay unresolved until typed source owners are traced.
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

DEVIATION_TABLE = "game_common/data/deviation_base_data.json"
SKILL_TABLE = "game_common/data/deviation_skills_data.json"
DATA_PATH = "published/data/deviations.json"

DEVIATION_CONTRACT = AdapterContract(
    entity_type="deviation",
    identity_seeds=("deviation_id", "canonical_id"),
    canonical_owner_tables=(DATA_PATH, DEVIATION_TABLE, SKILL_TABLE),
    allowed_outbound_fields=("skill_ids",),
    typed_destination_tables=(("skill_ids", (SKILL_TABLE,)),),
    collision_prone_fields=("deviation_id", "skill_ids"),
    blocked_generic_fields=("id", "no", "code", "record_id"),
    terminal_presentation_fields=(
        "name", "deviation_type_code", "unit_id", "unit_type",
        "collection_value", "containment", "mood", "temperature",
        "quality_coefficients", "power_coefficients", "balance_coefficients",
        "territory_effects", "meme_ids", "skills", "skill_catalog",
        "image_reference",
    ),
    supported_claims=(
        "deviation.exact_identity",
        "deviation.variant_family",
        "deviation.abilities",
        "deviation.containment",
        "deviation.mood_power",
        "deviation.trait_ownership",
        "deviation.acquisition",
        "deviation.scenario_availability",
        "deviation.artwork",
    ),
    applicability_rules=(
        "exact deviation_base_data source ID is canonical variant identity",
        "display name is browse grouping only and never identity proof",
        "deviation_base_data.skill_ids may link only to exact deviation_skills_data rows",
        "embedded skill text without a skill ID is presentation evidence, not exact skill ownership",
        "raw territory-effect and meme IDs are not promoted to traits without typed definition owners",
        "meme IDs do not prove scenario availability",
        "missing acquisition evidence remains UNRESOLVED",
    ),
)


def _read(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Deviation adapter could not read {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Deviation adapter expected an object: {path}")
    return payload


def _as_int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _claim(kind: str, canonical_id: str, result: str, *, evidence=None, missing=None, conflicts=None, dependencies=None, requirements=None) -> dict[str, Any]:
    return {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "claim_type": kind,
        "subject": {"entity_type": "deviation", "canonical_id": canonical_id},
        "result": result,
        "requirements": requirements or ["exact typed Deviation evidence"],
        "evidence": evidence or [],
        "missing": missing or [],
        "conflicts": conflicts or [],
        "dependencies": dependencies or [],
    }


def _edge(canonical_id: str, destination: str, relation: str, *, record: object, selector: str, authority: str) -> dict[str, Any]:
    source = f"deviation:{canonical_id}"
    return {
        "schema_version": EDGE_SCHEMA_VERSION,
        "source": source,
        "destination": destination,
        "relationship_type": relation,
        "source_table": DEVIATION_TABLE,
        "source_record": str(record),
        "selector": selector,
        "layer": "base-current-merged",
        "authority": authority,
        "state": "PROVEN",
        "dependency_fingerprint": dependency_fingerprint(
            source, destination, relation, DEVIATION_TABLE, record, selector,
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


def _has_values(value: Any) -> bool:
    if isinstance(value, dict):
        return any(item not in (None, "", [], {}) for item in value.values())
    if isinstance(value, list):
        return bool(value)
    return value not in (None, "")


class DeviationAdapter(EvidenceDomainAdapter):
    contract = DEVIATION_CONTRACT

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
            raise ValueError("Deviation published source must stay inside Miner output") from exc
        return published

    def _rows(self) -> list[dict[str, Any]]:
        payload = _read(self._published() / "data" / "deviations.json")
        return [row for row in payload.get("deviations", []) if isinstance(row, dict)]

    def _match(self, identity: object) -> dict[str, Any]:
        needle = str(identity or "").strip()
        if not needle:
            raise KeyError("Deviation identity is empty")
        matches = []
        for row in self._rows():
            deviation_id = _as_int(row.get("deviation_id") or row.get("id"))
            canonical_id = str(row.get("canonical_id") or f"ds-dev-{deviation_id}")
            if needle in {canonical_id, str(deviation_id)}:
                normalized = dict(row)
                normalized["deviation_id"] = deviation_id
                normalized["canonical_id"] = canonical_id
                matches.append(normalized)
        if not matches:
            raise KeyError(f"Unknown Deviation identity: {identity}")
        if len(matches) != 1:
            raise ValueError(f"Ambiguous Deviation source identity: {identity}")
        return matches[0]

    def _family(self, row: dict[str, Any]) -> dict[str, Any]:
        name = str(row.get("name") or "").strip()
        key = name.casefold() if name else f"id-{row['deviation_id']}"
        siblings = []
        for candidate in self._rows():
            candidate_name = str(candidate.get("name") or "").strip()
            candidate_key = candidate_name.casefold() if candidate_name else f"id-{_as_int(candidate.get('id'))}"
            if candidate_key == key:
                siblings.append(_as_int(candidate.get("deviation_id") or candidate.get("id")))
        siblings = sorted({value for value in siblings if value})
        return {
            "family_key": key,
            "family_canonical_id": f"ds-dev-family-{key}",
            "variant_ids": siblings,
            "variant_count": len(siblings),
            "policy": "display-name-browse-group-only-source-id-remains-canonical",
        }

    def graph(self, identity: object, **_: Any) -> dict[str, Any]:
        row = self._match(identity)
        deviation_id = int(row["deviation_id"])
        canonical_id = str(row["canonical_id"])
        name = str(row.get("name") or f"Deviation {deviation_id}")
        family = self._family(row)
        entity = {
            "schema_version": ENTITY_SCHEMA_VERSION,
            "entity_type": "deviation",
            "canonical_id": canonical_id,
            "name": name,
            "classification": "Deviation",
            "identity_state": "PROVEN",
            "source_records": [{
                "table": DEVIATION_TABLE,
                "record_id": str(deviation_id),
                "layer": "base-current-merged",
            }],
        }
        claims: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        claims.append(_claim(
            "deviation.exact_identity", canonical_id, "PROVEN",
            evidence=[{
                "deviation_id": deviation_id,
                "deviation_type_code": row.get("deviation_type_code"),
                "unit_id": row.get("unit_id"),
                "unit_type": row.get("unit_type"),
                "collection_value": row.get("collection_value"),
            }],
            dependencies=[DEVIATION_TABLE],
            requirements=["exact deviation_base_data source record"],
        ))
        claims.append(_claim(
            "deviation.variant_family", canonical_id, "PROVEN",
            evidence=[family], dependencies=[DEVIATION_TABLE],
            requirements=["family grouping may use display name for browsing but not identity proof"],
        ))

        catalog = [item for item in row.get("skill_catalog", []) if isinstance(item, dict)]
        embedded = [item for item in row.get("skills", []) if isinstance(item, dict) and (item.get("name") or item.get("description"))]
        exact_skills = [item for item in catalog if _as_int(item.get("id"))]
        if exact_skills:
            claims.append(_claim(
                "deviation.abilities", canonical_id, "PROVEN",
                evidence=[{"exact_skill_catalog": exact_skills, "embedded_presentation": embedded}],
                dependencies=[DEVIATION_TABLE, SKILL_TABLE],
                requirements=["exact deviation_base_data.skill_ids joined to deviation_skills_data source IDs"],
            ))
            for skill in exact_skills:
                skill_id = _as_int(skill.get("id"))
                edges.append(_edge(
                    canonical_id, f"deviation-skill:{skill_id}", "deviation-skill-owner",
                    record=deviation_id, selector="/skill_ids",
                    authority="exact-deviation-skill-id",
                ))
        elif embedded:
            claims.append(_claim(
                "deviation.abilities", canonical_id, "PARTIAL",
                evidence=[{"embedded_presentation": embedded}],
                missing=["exact deviation skill ID owner for embedded player-facing text"],
                dependencies=[DEVIATION_TABLE, SKILL_TABLE],
            ))
        else:
            claims.append(_claim(
                "deviation.abilities", canonical_id, "UNRESOLVED",
                missing=["Deviation ability owner"], dependencies=[DEVIATION_TABLE, SKILL_TABLE],
            ))

        containment = row.get("containment") if isinstance(row.get("containment"), dict) else {}
        claims.append(_claim(
            "deviation.containment", canonical_id,
            "PROVEN" if _has_values(containment) else "UNRESOLVED",
            evidence=[containment] if _has_values(containment) else [],
            missing=[] if _has_values(containment) else ["containment values in deviation_base_data"],
            dependencies=[DEVIATION_TABLE],
        ))

        mood_power = {
            "mood": row.get("mood") or {},
            "temperature": row.get("temperature") or {},
            "quality_coefficients": row.get("quality_coefficients") or {},
            "power_coefficients": row.get("power_coefficients") or {},
            "balance_coefficients": row.get("balance_coefficients") or {},
        }
        claims.append(_claim(
            "deviation.mood_power", canonical_id,
            "PROVEN" if any(_has_values(value) for value in mood_power.values()) else "UNRESOLVED",
            evidence=[mood_power] if any(_has_values(value) for value in mood_power.values()) else [],
            missing=[] if any(_has_values(value) for value in mood_power.values()) else ["mood/power coefficient owner"],
            dependencies=[DEVIATION_TABLE],
        ))

        raw_traits = {
            "territory_effects": list(row.get("territory_effects") or []),
            "meme_ids": list(row.get("meme_ids") or []),
        }
        if raw_traits["territory_effects"] or raw_traits["meme_ids"]:
            claims.append(_claim(
                "deviation.trait_ownership", canonical_id, "PARTIAL",
                evidence=[raw_traits],
                missing=["typed trait-definition owner for raw territory_effects/meme_ids references"],
                dependencies=[DEVIATION_TABLE],
                requirements=["raw IDs are preserved but not promoted to player-facing trait semantics"],
            ))
        else:
            claims.append(_claim(
                "deviation.trait_ownership", canonical_id, "UNRESOLVED",
                missing=["typed Deviation trait-definition owner"], dependencies=[DEVIATION_TABLE],
            ))

        claims.append(_claim(
            "deviation.acquisition", canonical_id, "UNRESOLVED",
            missing=["typed vendor/drop/reward/acquisition owner"],
            dependencies=[DEVIATION_TABLE],
            requirements=["localized or community acquisition text is not sufficient for PROVEN"],
        ))
        claims.append(_claim(
            "deviation.scenario_availability", canonical_id, "UNRESOLVED",
            evidence=[{"meme_ids": raw_traits["meme_ids"]}] if raw_traits["meme_ids"] else [],
            missing=["typed scenario/season availability owner"],
            dependencies=[DEVIATION_TABLE],
            requirements=["meme_ids are not scenario proof"],
        ))

        artwork = str(row.get("image_reference") or row.get("image_asset") or "").strip()
        claims.append(_claim(
            "deviation.artwork", canonical_id,
            "PROVEN" if artwork else "UNRESOLVED",
            evidence=[{"image_reference": artwork}] if artwork else [],
            missing=[] if artwork else ["source-derived Deviation artwork reference"],
            dependencies=[DEVIATION_TABLE],
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
                "variant_family": family,
                "publication_authority": False,
            },
        }
        errors = validate_generalized_graph(payload)
        if errors:
            raise ValueError(f"Deviation adapter produced invalid graph: {errors}")
        return payload
