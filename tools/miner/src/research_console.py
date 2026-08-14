"""Read-only research services for the Dead Signal Miner Research Console.

All game-derived inputs are opened read-only. Research notes and compact evidence
exports are written only beneath the selected Miner output's ``research`` folder.
Related search is deliberately separated from exact evidence and can never create
an identity edge or publication candidate.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
FILTERS = ("Tables", "Translations", "Weapons", "Buffs", "PYC symbols")
ID_KEYS = {
    "blueprint_id", "item_id", "prototype_id", "gun_no", "fixed_skill_code",
    "buff_id", "buff_ids", "translation_handle", "translation_handles",
    "raw_handle", "marker_stripped_handle", "forge_id", "forge_ids",
}
PRIORITY_FILES = (
    "weapons.json", "weapon-configuration.json", "mods.json", "attachments.json",
    "armor.json", "deviations.json", "cradles.json",
)
UNRESOLVED_GROUPS = (
    "exact missing skill record", "no fixed skill reference",
    "skill present/text unresolved", "translation collision/shared handle",
    "missing recipe evidence", "unresolved attachment compatibility",
    "ambiguous Deviation/Cradle variants", "Mod consumer-semantics blockers",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _safe_child(root: Path, candidate: Path | str, *, must_exist: bool = True) -> Path:
    root = root.expanduser().resolve()
    candidate = Path(candidate).expanduser().resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("Research paths must stay inside the selected Miner data folder") from error
    if must_exist and not candidate.exists():
        raise ValueError(f"Research input does not exist: {candidate}")
    if candidate.is_symlink():
        raise ValueError("Symbolic-link research inputs are not accepted")
    return candidate


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _walk(value: Any, pointer: str = "") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_pointer = f"{pointer}/{str(key).replace('~', '~0').replace('/', '~1')}"
            if isinstance(child, (dict, list)):
                yield from _walk(child, child_pointer)
            else:
                yield child_pointer, str(key), child
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_pointer = f"{pointer}/{index}"
            if isinstance(child, (dict, list)):
                yield from _walk(child, child_pointer)
            else:
                yield child_pointer, str(index), child


def _records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("weapons", "buffs", "attachments", "mods", "deviations", "cradles", "families", "records"):
        if isinstance(payload.get(key), list):
            return [row for row in payload[key] if isinstance(row, dict)]
    return []


def _identity(row: dict[str, Any]) -> str:
    for key in ("canonical_id", "blueprint_id", "item_id", "buff_id", "id", "source_id", "name"):
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return "unknown"


class ResearchConsole:
    """Facade over one local Miner output folder."""

    def __init__(self, output: Path | str):
        self.output = Path(output).expanduser().resolve()
        if not self.output.is_dir():
            raise ValueError("Select a Miner data folder containing last-run.json")
        self.last_run_path = _safe_child(self.output, self.output / "last-run.json")
        self.last_run = read_json(self.last_run_path, {}) or {}
        self.published = _safe_child(
            self.output, Path(self.last_run.get("published") or self.output / "published")
        )
        active = self.last_run.get("active_snapshots") or {}
        self.base = _safe_child(self.output, Path(active.get("base") or ""))
        self.current = _safe_child(self.output, Path(active.get("current") or ""))
        self.tracer = _safe_child(
            self.output, self.published / "indexes" / "reference-tracer.sqlite"
        )

    def _trace(self, value: object, limit: int = 500) -> list[dict[str, Any]]:
        if limit < 1 or limit > 5000:
            raise ValueError("Reference limit must be between 1 and 5000")
        uri = f"file:{self.tracer.as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        try:
            rows = connection.execute(
                "SELECT layer,table_name,record_id,field,json_pointer "
                "FROM occurrences WHERE value=? ORDER BY table_name,record_id LIMIT ?",
                (str(value), limit),
            ).fetchall()
        finally:
            connection.close()
        return [
            {"source": layer, "table": table, "record_id": record, "field": field,
             "json_pointer": pointer, "match": "exact", "authoritative": True}
            for layer, table, record, field, pointer in rows
        ]

    def search(self, query: object, filters: Iterable[str] = FILTERS, *, related: bool = False,
               limit: int = 250) -> dict[str, Any]:
        text = str(query).strip()
        if not text:
            return {"query": "", "mode": "related" if related else "exact", "results": []}
        selected = set(filters)
        unknown = selected.difference(FILTERS)
        if unknown:
            raise ValueError(f"Unknown research filters: {sorted(unknown)}")
        results: list[dict[str, Any]] = []
        if "Tables" in selected and not related:
            results.extend(self._trace(text, limit))
        sources = []
        if "Weapons" in selected:
            sources.append(("Weapons", self.published / "web" / "weapons.json"))
        needle = text.casefold()
        for category, path in sources:
            payload = read_json(path)
            if payload is None:
                continue
            for pointer, field, value in _walk(payload):
                scalar = str(value)
                matched = needle in scalar.casefold() if related else scalar == text
                if matched:
                    results.append({
                        "category": category, "source": str(path.relative_to(self.output)),
                        "field": field, "json_pointer": pointer, "value": scalar,
                        "match": "substring" if related else "exact",
                        "authoritative": not related,
                    })
                    if len(results) >= limit:
                        break
            if len(results) >= limit:
                break
        # Buff and PYC evidence files can be hundreds of megabytes. Stream them
        # line-by-line so a console search never duplicates those payloads in RAM.
        large_sources = []
        if "Buffs" in selected:
            large_sources.append(("Buffs", self.published / "data" / "buffs.json"))
        if "PYC symbols" in selected:
            large_sources.append(("PYC symbols", self.published / "reports" / "weapon-progression-pyc-consumers.json"))
        exact_tokens = {json.dumps(text, ensure_ascii=False), text if text.lstrip("-").isdigit() else ""}
        for category, path in large_sources:
            if not path.is_file() or len(results) >= limit:
                continue
            with path.open("r", encoding="utf-8", errors="replace") as source:
                for line_number, line in enumerate(source, 1):
                    matched = needle in line.casefold() if related else any(token and token in line for token in exact_tokens)
                    if matched:
                        results.append({"category": category, "source": str(path.relative_to(self.output)),
                                        "field": "streamed-json-line", "json_pointer": None,
                                        "line": line_number, "value": line.strip()[:500],
                                        "match": "substring" if related else "exact-token",
                                        "authoritative": not related})
                        if len(results) >= limit:
                            break
        if "Translations" in selected and len(results) < limit:
            for layer, root in (("base", self.base), ("current", self.current)):
                for path in sorted((root / "translate").glob("translate_data_en*.json")):
                    translations = read_json(path, {}) or {}
                    for pointer, field, value in _walk(translations):
                        scalar = str(value)
                        key = pointer.rsplit("/", 1)[-1]
                        matched = (needle in scalar.casefold() or needle in key.casefold()) if related else (scalar == text or key == text)
                        if matched:
                            results.append({
                                "category": "Translations", "source": layer,
                                "table": path.relative_to(root).as_posix(), "field": field,
                                "json_pointer": pointer, "value": scalar,
                                "match": "substring" if related else "exact",
                                "authoritative": not related,
                            })
                            if len(results) >= limit:
                                break
                    if len(results) >= limit:
                        break
                if len(results) >= limit:
                    break
        return {
            "schema": "dead-signal-research-search", "schema_version": SCHEMA_VERSION,
            "query": text, "mode": "related-non-authoritative" if related else "exact-authoritative",
            "identity_policy": "Related results never establish or promote identity." if related else "Exact scalar equality only.",
            "filters": sorted(selected), "result_count": len(results), "results": results[:limit],
        }

    def weapons(self) -> list[dict[str, Any]]:
        return _records(read_json(self.published / "web" / "weapons.json", {}))

    def find_weapon(self, identity: object) -> dict[str, Any]:
        wanted = str(identity).strip()
        for row in self.weapons():
            candidates = {str(row.get(key) or "") for key in ("canonical_id", "blueprint_id", "item_id", "name")}
            if wanted in candidates:
                return row
        raise ValueError(f"No exact Weapon identity matched {wanted!r}")

    @staticmethod
    def _known_ids(weapon: dict[str, Any]) -> dict[str, list[str]]:
        found: dict[str, set[str]] = defaultdict(set)
        for pointer, field, value in _walk(weapon):
            if field in ID_KEYS or field.endswith("_id") or field == "gun_no":
                values = value if isinstance(value, list) else [value]
                for item in values:
                    if item not in (None, "", 0, "0") and not isinstance(item, (dict, list)):
                        found[field].add(str(item))
        return {key: sorted(values) for key, values in sorted(found.items())}

    def translation_forensics(self, handle: object) -> dict[str, Any]:
        raw = str(handle or "").strip()
        matches = []
        for layer, root in (("base", self.base), ("current", self.current)):
            for path in sorted((root / "translate").glob("translate_data_en*.json")):
                payload = read_json(path, {}) or {}
                for pointer, _field, value in _walk(payload):
                    if pointer.rsplit("/", 1)[-1] == raw:
                        matches.append({"layer": layer, "source": path.relative_to(root).as_posix(),
                                        "key": raw, "text": str(value)})
        texts = sorted({row["text"] for row in matches})
        usage = self._trace(raw, 2000) if raw else []
        return {
            "raw_handle": raw, "matches": matches, "unique_texts": texts,
            "disagreement": len(texts) > 1, "shared_handle_usage": usage,
            "shared_usage_count": len(usage),
            "publication_status": "withheld-suspect-translation" if len(texts) != 1 or len(usage) > 1 else "research-only-pending-item-handle-verification",
        }

    def investigate_weapon(self, identity: object) -> dict[str, Any]:
        weapon = self.find_weapon(identity)
        known = self._known_ids(weapon)
        nodes = [{"id": f"weapon:{_identity(weapon)}", "kind": "weapon", "label": weapon.get("name") or _identity(weapon), "status": "present"}]
        edges = []
        missing = []
        for field, values in known.items():
            for value in values:
                traces = self._trace(value)
                node_id = f"{field}:{value}"
                status = "present" if traces else "missing-link"
                nodes.append({"id": node_id, "kind": field, "label": value, "status": status, "references": traces})
                edges.append({"from": nodes[0]["id"], "to": node_id, "field": field,
                              "provenance": "published/web/weapons.json", "authoritative": True})
                if not traces:
                    missing.append({"field": field, "value": value, "status": "missing-link"})
        desc = ((weapon.get("verification") or {}).get("short_description_evidence") or {})
        handle = desc.get("raw_handle")
        return {
            "schema": "dead-signal-weapon-investigation", "schema_version": SCHEMA_VERSION,
            "weapon": {key: weapon.get(key) for key in ("canonical_id", "name", "blueprint_id", "item_id", "category")},
            "known_ids": known, "evidence_tree": {"nodes": nodes, "edges": edges},
            "missing_links": missing, "translation_forensics": self.translation_forensics(handle) if handle else None,
            "identity_policy": "Exact identifiers only; missing records stay missing and similar IDs are never substituted.",
        }

    def unresolved_queue(self) -> dict[str, Any]:
        groups: dict[str, list[dict[str, Any]]] = {key: [] for key in UNRESOLVED_GROUPS}
        weapons = self.weapons()
        for row in weapons:
            effect = row.get("effect_resolution") or {}
            status = effect.get("status")
            item = {"identity": _identity(row), "name": row.get("name"), "status": status}
            if status == "exact-fixed-skill-record-missing":
                groups[UNRESOLVED_GROUPS[0]].append(item)
            elif status == "no-fixed-skill-reference":
                groups[UNRESOLVED_GROUPS[1]].append(item)
            elif status == "exact-fixed-skill-record-present-effect-text-unresolved":
                groups[UNRESOLVED_GROUPS[2]].append(item)
            desc = ((row.get("verification") or {}).get("short_description_evidence") or {})
            if desc.get("status") in {"translation-source-conflict", "translation-handle-shared-across-weapons"}:
                groups[UNRESOLVED_GROUPS[3]].append({**item, "status": desc.get("status")})
            tiers = ((row.get("progression") or {}).get("gear_tiers") or [])
            recipe_count = sum(bool(tier.get("recipe")) for tier in tiers if isinstance(tier, dict))
            recipes = row.get("recipes") or row.get("crafting_recipes") or []
            if not tiers:
                recipe_count = len(recipes)
            if recipe_count < 5:
                groups[UNRESOLVED_GROUPS[4]].append({**item, "status": "recipe-evidence-incomplete"})
        attachments = _records(read_json(self.published / "web" / "attachments.json", {}))
        for row in attachments:
            text = json.dumps(row, ensure_ascii=False).casefold()
            if "unresolved" in text or "blank-description" in text:
                groups[UNRESOLVED_GROUPS[5]].append({"identity": _identity(row), "name": row.get("name"), "status": "compatibility-unresolved"})
        for filename in ("deviations.json", "cradles.json"):
            variant_rows = _records(read_json(self.published / "web" / filename, {}))
            family_counts = Counter(str(row.get("name") or "") for row in variant_rows)
            seen_legacy_families = set()
            for row in variant_rows:
                count = int(row.get("variant_count") or len(row.get("variants") or []))
                if not count:
                    family_name = str(row.get("name") or "")
                    count = family_counts[family_name]
                    if family_name in seen_legacy_families:
                        continue
                    seen_legacy_families.add(family_name)
                if count > 1:
                    groups[UNRESOLVED_GROUPS[6]].append({"identity": _identity(row), "name": row.get("name"), "variants": count})
        mods = read_json(self.published / "web" / "mods.json", {}) or {}
        semantic_status = str(mods.get("mod_frame_evidence_status") or "").casefold()
        if _records(mods) and "consumer-semantics-proven" not in semantic_status:
            groups[UNRESOLVED_GROUPS[7]].append({"identity": "mod-frame-consumer-semantics", "status": "unproven-positional-consumer-semantics"})
        return {"schema": "dead-signal-unresolved-queue", "schema_version": SCHEMA_VERSION,
                "generated_utc": utc_now(), "groups": groups,
                "counts": {key: len(value) for key, value in groups.items()}}

    def evidence_graph(self, identity: object) -> dict[str, Any]:
        return self.investigate_weapon(identity)["evidence_tree"]

    def snapshots(self) -> list[Path]:
        root = _safe_child(self.output, self.output / "snapshots")
        return sorted((path for path in root.rglob("tables") if path.is_dir()), key=lambda p: str(p))

    @staticmethod
    def _canonical_map(payload: Any) -> dict[str, str]:
        rows = _records(payload)
        result = {}
        for row in rows:
            stable = _identity(row)
            result[stable] = hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        return result

    def diff_snapshots(self, before: Path | str, after: Path | str) -> dict[str, Any]:
        before = _safe_child(self.output, before)
        after = _safe_child(self.output, after)
        categories = {}
        for filename in PRIORITY_FILES:
            left_path = before / filename if before.name == "web" else before / "web" / filename
            right_path = after / filename if after.name == "web" else after / "web" / filename
            left = self._canonical_map(read_json(left_path, {}))
            right = self._canonical_map(read_json(right_path, {}))
            categories[filename.removesuffix(".json")] = {
                "added": sorted(right.keys() - left.keys()), "removed": sorted(left.keys() - right.keys()),
                "changed": sorted(key for key in left.keys() & right.keys() if left[key] != right[key]),
            }
        ordered = sorted(categories.items(), key=lambda item: (PRIORITY_FILES.index(item[0] + ".json"), item[0]))
        return {"schema": "dead-signal-snapshot-diff", "schema_version": SCHEMA_VERSION,
                "before": str(before), "after": str(after), "priority": [name for name, _ in ordered],
                "categories": dict(ordered)}

    def notes(self) -> dict[str, Any]:
        return read_json(self.output / "research" / "bookmarks.json", {"schema": "dead-signal-research-bookmarks", "schema_version": 1, "items": []})

    def save_note(self, target: object, note: str, *, bookmark: bool = True) -> dict[str, Any]:
        payload = self.notes()
        items = payload.setdefault("items", [])
        items.append({"id": f"note-{len(items)+1}", "target": str(target), "note": str(note).strip(),
                      "bookmark": bool(bookmark), "created_utc": utc_now()})
        _atomic_json(_safe_child(self.output, self.output / "research" / "bookmarks.json", must_exist=False), payload)
        return items[-1]

    def export_evidence(self, evidence: dict[str, Any], name: str = "research-evidence") -> Path:
        safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", name).strip(".-") or "research-evidence"
        path = _safe_child(self.output, self.output / "research" / "evidence" / f"{safe_name}.json", must_exist=False)
        payload = {"schema": "dead-signal-evidence", "schema_version": 1, "generated_utc": utc_now(),
                   "source": "local-read-only-miner-snapshot", "publication_status": "research-only", "evidence": evidence}
        _atomic_json(path, payload)
        return path

    def integrity_dashboard(self) -> dict[str, Any]:
        quality = read_json(self.published / "reports" / "data-quality.json", {}) or {}
        validation = read_json(self.published / "reports" / "validation.json", {}) or {}
        manifest = read_json(self.published / "snapshot-manifest.json", {}) or {}
        queue = self.unresolved_queue()
        files = manifest.get("files") or []
        present = sum((self.published / str(row.get("path") or "")).is_file() for row in files if isinstance(row, dict))
        return {"schema": "dead-signal-research-integrity", "schema_version": 1,
                "snapshot_quality": quality.get("overall_status") or manifest.get("quality_status") or "UNKNOWN",
                "validation": validation, "manifest_files": len(files), "manifest_files_present": present,
                "reference_tracer_read_only": self.tracer.is_file(), "unresolved_counts": queue["counts"],
                "policies": {"game_inputs": "read-only", "bytecode": "never executed", "identity": "exact-only",
                             "related_search": "non-authoritative", "translations": "suspect text withheld"}}
