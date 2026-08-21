"""Canonical Phase-6 Armor Set adapter.

The base set adapter builds the typed claims. This narrow wrapper binds each
set→piece membership edge to an actual equip_data record (the canonical first
tier item) rather than to a reusable blueprint identifier.
"""
from __future__ import annotations

from typing import Any

from dead_signal_armor_adapters import ArmorSetAdapter as _ArmorSetAdapter
from dead_signal_evidence_contracts import dependency_fingerprint, validate_generalized_graph


class ArmorSetAdapter(_ArmorSetAdapter):
    def graph(self, identity: object, **kwargs: Any) -> dict[str, Any]:
        payload = super().graph(identity, **kwargs)
        row = self._match(identity, self._rows())
        item_owner_by_piece: dict[str, object] = {}
        for piece in row.get("pieces", []):
            if not isinstance(piece, dict):
                continue
            canonical_id = str(piece.get("canonical_id") or "")
            tiers = [tier for tier in piece.get("tiers", []) if isinstance(tier, dict)]
            item_id = tiers[0].get("item_id") if tiers else None
            if canonical_id and item_id not in (None, ""):
                item_owner_by_piece[canonical_id] = item_id

        for edge in payload.get("edges", []):
            if edge.get("relationship_type") != "armor-set-contains-piece":
                continue
            destination = str(edge.get("destination") or "")
            piece_id = destination.split("armor:", 1)[1] if destination.startswith("armor:") else ""
            item_id = item_owner_by_piece.get(piece_id)
            if item_id in (None, ""):
                raise ValueError(f"Armor set piece lacks an exact equipment record owner: {piece_id}")
            edge["source_record"] = str(item_id)
            edge["dependency_fingerprint"] = dependency_fingerprint(
                edge["source"], edge["destination"], edge["relationship_type"],
                edge["source_table"], edge["source_record"], edge["selector"],
                edge["layer"], edge["authority"],
            )

        errors = validate_generalized_graph(payload)
        if errors:
            raise ValueError(f"Armor-set adapter produced invalid graph after provenance binding: {errors}")
        return payload
