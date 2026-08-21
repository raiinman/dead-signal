"""Searchable entity registry for the generalized Dead Signal Evidence Graph.

The registry indexes only source-derived entities whose entity type has a
registered typed adapter. Names are search aliases only; they never create proof.
"""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any, Iterable

from dead_signal_domain_adapters import EvidenceAdapterRegistry

REGISTRY_SCHEMA = "dead-signal-entity-registry"
REGISTRY_SCHEMA_VERSION = 1


def _records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("weapons", "attachments", "calibrations", "armor", "mods", "cradles", "materials", "recipes", "deviations", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def _family_variants(payload: dict[str, Any], *, canonical_prefix: str, identity_field: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for family in payload.get("families", []):
        if not isinstance(family, dict):
            continue
        family_id = str(family.get("canonical_id") or "")
        for variant in family.get("variants", []):
            if not isinstance(variant, dict):
                continue
            row = dict(variant)
            identity = row.get(identity_field)
            if identity in (None, ""):
                continue
            row.setdefault("canonical_id", f"{canonical_prefix}-{identity}")
            row["family_canonical_id"] = family_id
            result.append(row)
    return result


def _calibration_variants(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _family_variants(payload, canonical_prefix="ds-cal-var", identity_field="item_id")
    for row in rows:
        calibration_id = row.get("calibration_id") or row.get("id") or row.get("item_id")
        row["calibration_id"] = calibration_id
        row["canonical_id"] = f"ds-cal-var-{calibration_id}"
    return rows


def _mod_variants(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return _family_variants(payload, canonical_prefix="ds-mod-var", identity_field="item_id")


def _cradle_rows(data: dict[str, Any], report: dict[str, Any]) -> list[dict[str, Any]]:
    """Join normalized Cradles to active selector rows; no compact web dependency."""
    by_id = {
        str(row.get("id")): row
        for row in data.get("cradles", [])
        if isinstance(row, dict) and row.get("id") not in (None, "")
    }
    result: list[dict[str, Any]] = []
    for selector in report.get("selectors", []):
        if not isinstance(selector, dict):
            continue
        entry_id = selector.get("entry_id")
        source = by_id.get(str(entry_id))
        if source is None:
            continue
        row = dict(source)
        row["cradle_id"] = entry_id
        row["canonical_id"] = f"ds-cradle-{entry_id}"
        row["classification"] = "Active Cradle"
        row["active_config_keys"] = list(selector.get("config_keys") or row.get("active_config_keys") or [])
        row["active_season_ids"] = list(selector.get("season_ids") or row.get("active_season_ids") or [])
        result.append(row)
    return result


def _armor_pieces(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for armor_set in payload.get("armor_sets", []):
        if not isinstance(armor_set, dict):
            continue
        for piece in armor_set.get("pieces", []):
            if not isinstance(piece, dict):
                continue
            row = dict(piece)
            row.setdefault("classification", "Set Armor")
            row["set_canonical_id"] = armor_set.get("canonical_id")
            row["suit_id"] = armor_set.get("suit_id")
            result.append(row)
    for piece in payload.get("key_armor", []):
        if not isinstance(piece, dict):
            continue
        row = dict(piece)
        row.setdefault("classification", "Key Armor")
        result.append(row)
    return result


def _armor_sets(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in payload.get("armor_sets", []) if isinstance(row, dict)]


def _first(row: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _normalize_identity_state(value: object) -> str:
    text = str(value or "").strip().upper().replace("_", " ").replace("-", " ")
    if text in {"PROVEN", "VERIFIED"}:
        return "PROVEN"
    if text == "PARTIAL":
        return "PARTIAL"
    if text in {"NOT APPLICABLE", "NA", "N/A"}:
        return "NOT APPLICABLE"
    if text == "CONFLICT":
        return "CONFLICT"
    return "UNRESOLVED"


def _load(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


class DeadSignalEntityRegistry:
    """Read-only searchable registry over adapter-backed published entities."""

    def __init__(self, output: Path | str, adapters: EvidenceAdapterRegistry):
        self.output = Path(output).expanduser().resolve()
        self.adapters = adapters
        self._entities: dict[tuple[str, str], dict[str, Any]] = {}
        self._aliases: dict[str, set[tuple[str, str]]] = {}
        self._recent: deque[tuple[str, str]] = deque(maxlen=20)

    def _published_web(self) -> Path:
        last_run = self.output / "last-run.json"
        if not last_run.is_file():
            raise ValueError("Entity registry requires a completed Miner output with last-run.json")
        try:
            state = json.loads(last_run.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError("Entity registry could not read last-run.json") from exc
        published = Path(state.get("published") or self.output / "published")
        if not published.is_absolute():
            published = self.output / published
        published = published.resolve()
        try:
            published.relative_to(self.output)
        except ValueError as exc:
            raise ValueError("Published registry source must stay inside the Miner output folder") from exc
        return published / "web"

    def rebuild(self) -> dict[str, Any]:
        self._entities.clear()
        self._aliases.clear()
        web = self._published_web()
        source_map = {
            "weapon": web / "weapons.json",
            "attachment": web / "attachments.json",
            "calibration": web / "calibrations.json",
            "armor": web / "armor.json",
            "armor_set": web / "armor.json",
            "mod": web / "mods.json",
            "deviation": web / "deviations.json",
        }
        indexed_by_type: dict[str, int] = {}
        for entity_type in self.adapters.entity_types():
            if entity_type == "cradle":
                path = web.parent / "data" / "cradles.json"
                report_path = web.parent / "reports" / "weapon-cradle-applicability.json"
                payload = _load(path)
                report = _load(report_path)
                if payload is None or report is None:
                    indexed_by_type[entity_type] = 0
                    continue
                rows = _cradle_rows(payload, report)
            else:
                path = source_map.get(entity_type)
                if path is None or not path.is_file():
                    indexed_by_type[entity_type] = 0
                    continue
                payload = _load(path)
                if payload is None:
                    indexed_by_type[entity_type] = 0
                    continue
                if entity_type == "calibration":
                    rows = _calibration_variants(payload)
                elif entity_type == "mod":
                    rows = _mod_variants(payload)
                elif entity_type == "armor":
                    rows = _armor_pieces(payload)
                elif entity_type == "armor_set":
                    rows = _armor_sets(payload)
                else:
                    rows = _records(payload)
            count = 0
            for row in rows:
                entity = self._entity_from_row(entity_type, row, path)
                if entity is None:
                    continue
                key = (entity_type, entity["canonical_id"])
                if key in self._entities:
                    raise ValueError(f"Duplicate canonical entity identity: {entity_type}:{entity['canonical_id']}")
                self._entities[key] = entity
                for alias in entity["aliases"]:
                    self._aliases.setdefault(alias.casefold(), set()).add(key)
                count += 1
            indexed_by_type[entity_type] = count
        return {
            "schema": REGISTRY_SCHEMA,
            "schema_version": REGISTRY_SCHEMA_VERSION,
            "total": len(self._entities),
            "by_entity_type": indexed_by_type,
            "adapter_types": list(self.adapters.entity_types()),
        }

    def _entity_from_row(self, entity_type: str, row: dict[str, Any], path: Path) -> dict[str, Any] | None:
        canonical = _first(row, ("canonical_id", "calibration_id", "suit_id", "blueprint_id", "item_id", "attachment_id", "mod_id", "cradle_id", "deviation_id"))
        name = _first(row, ("name", "display_name", "title"))
        if canonical in (None, "") or name in (None, ""):
            return None
        canonical_text = str(canonical)
        aliases: list[str] = [canonical_text, str(name)]
        for key in ("calibration_id", "suit_id", "blueprint_id", "item_id", "prototype_id", "attachment_id", "accessory_id", "mod_id", "mod_code", "cradle_id", "deviation_id", "family_canonical_id", "set_canonical_id"):
            value = row.get(key)
            if value not in (None, ""):
                aliases.append(str(value))
        for tier in row.get("tiers", []) if isinstance(row.get("tiers"), list) else []:
            if isinstance(tier, dict) and tier.get("item_id") not in (None, ""):
                aliases.append(str(tier.get("item_id")))
        aliases = sorted(set(aliases), key=lambda item: (item.casefold(), item))
        identity_state = _normalize_identity_state(_first(row, ("identity_state", "state", "evidence_state")) or "PROVEN")
        source_owner = path.relative_to(self.output).as_posix()
        return {
            "entity_type": entity_type,
            "canonical_id": canonical_text,
            "aliases": aliases,
            "display_name": str(name),
            "category": str(_first(row, ("category", "classification", "slot", "type")) or ("Armor Set" if entity_type == "armor_set" else "")),
            "source_owner": source_owner,
            "identity_state": identity_state,
            "artwork_reference": _first(row, ("artwork", "artwork_reference", "image_asset", "image_reference", "icon", "icon_path", "image")),
            "availability_state": str(_first(row, ("availability_state", "availability", "status")) or "UNRESOLVED"),
            "graph_target": {"entity_type": entity_type, "canonical_id": canonical_text},
        }

    def get(self, entity_type: str, canonical_id: object) -> dict[str, Any]:
        key = (str(entity_type).casefold(), str(canonical_id))
        entity = self._entities.get(key)
        if entity is None:
            raise KeyError(f"Unknown registered entity: {entity_type}:{canonical_id}")
        self._recent.appendleft(key)
        return dict(entity)

    def search(self, query: object, *, entity_type: str | None = None, unresolved_only: bool = False, limit: int = 100) -> list[dict[str, Any]]:
        if limit < 1 or limit > 1000:
            raise ValueError("Registry search limit must be between 1 and 1000")
        needle = str(query or "").strip().casefold()
        type_filter = str(entity_type or "").strip().casefold()
        matches: list[dict[str, Any]] = []
        for key, entity in self._entities.items():
            if type_filter and key[0] != type_filter:
                continue
            if unresolved_only and entity["identity_state"] not in {"PARTIAL", "UNRESOLVED", "CONFLICT"}:
                continue
            if needle and not any(needle in alias.casefold() for alias in entity["aliases"]):
                continue
            matches.append(entity)
        matches.sort(key=lambda row: (row["entity_type"], row["display_name"].casefold(), row["canonical_id"]))
        return [dict(row) for row in matches[:limit]]

    def recent(self) -> list[dict[str, Any]]:
        seen: set[tuple[str, str]] = set()
        result: list[dict[str, Any]] = []
        for key in self._recent:
            if key in seen or key not in self._entities:
                continue
            seen.add(key)
            result.append(dict(self._entities[key]))
        return result
