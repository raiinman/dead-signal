#!/usr/bin/env python3
"""Dead Signal weapon progression investigator.

Static/offline analysis only. This script does not import or execute game code.
It is intended to run after the existing Once Human script.npk extraction stage.

Goals:
  1. Recover Tier I-V weapon stat rows and infer tier ratios.
  2. Find Blueprint Star / enhancement / quality records and numeric tables.
  3. Find records where star + tier + weapon stats meet.
  4. Query reference-tracer.sqlite, when present, for provenance leads.
  5. Emit evidence-first reports without inventing a progression formula.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sqlite3
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

STAR_TERMS = (
    "blueprintstar", "blueprint_star", "blueprint star", "starlevel", "star_level",
    "starrank", "star_rank", "enhance", "enhancement", "blueprintenhance",
    "blueprint_enhance", "qualitylevel", "quality_level", "qualityrank", "quality_rank",
)
TIER_TERMS = (
    "weapontier", "weapon_tier", "gear tier", "geartier", "tierlevel", "tier_level",
    "crafttier", "craft_tier", "equipmenttier", "equipment_tier",
)
STAT_TERMS = (
    "attack", "atk", "damage", "dmg", "baseattack", "base_attack", "basedamage", "base_damage",
    "firepower", "weaponattack", "weapon_attack", "weapondamage", "weapon_damage",
)

ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5}


def norm_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


STAR_KEYS = {norm_key(x) for x in STAR_TERMS} | {
    "star", "stars", "starlevel", "starrank", "blueprintstars", "enhancelevel", "enhancementlevel",
    "blueprintlevel", "quality", "qualitylevel",
}
TIER_KEYS = {norm_key(x) for x in TIER_TERMS} | {"tier", "leveltier", "craftlevel"}
STAT_KEYS = {norm_key(x) for x in STAT_TERMS}
ID_KEYS = {
    "id", "weaponid", "weapon_id", "itemid", "item_id", "templateid", "template_id", "blueprintid",
    "blueprint_id", "equipid", "equip_id", "rowid", "row_id",
}
NAME_KEYS = {"name", "weaponname", "weapon_name", "displayname", "display_name", "itemname", "item_name"}
RARITY_KEYS = {"rarity", "quality", "grade", "color", "raritylevel", "rarity_level"}


@dataclass
class Evidence:
    source_file: str
    json_path: str
    kind: str
    score: int
    weapon_id: str | None = None
    weapon_name: str | None = None
    tier: int | None = None
    stars: int | None = None
    stat_name: str | None = None
    stat_value: float | None = None
    rarity: str | None = None
    keys: str | None = None
    preview: str | None = None


def scalar_preview(v: Any, limit: int = 180) -> str:
    try:
        s = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        s = repr(v)
    return s if len(s) <= limit else s[: limit - 3] + "..."


def parse_intish(value: Any, lo: int, hi: int) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        iv = int(value)
        return iv if float(value) == iv and lo <= iv <= hi else None
    s = str(value).strip().lower()
    s = s.replace("tier", "").replace("star", "").replace("★", "").strip(" _-:")
    if s in ROMAN:
        iv = ROMAN[s]
        return iv if lo <= iv <= hi else None
    if re.fullmatch(r"\d+", s):
        iv = int(s)
        return iv if lo <= iv <= hi else None
    return None


def number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    if isinstance(value, str):
        s = value.strip().replace(",", "")
        if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", s):
            try:
                return float(s)
            except ValueError:
                pass
    return None


def first_value(obj: dict[str, Any], normalized_keys: set[str]) -> Any:
    for k, v in obj.items():
        if norm_key(k) in normalized_keys:
            return v
    return None


def first_text(obj: dict[str, Any], normalized_keys: set[str]) -> str | None:
    v = first_value(obj, normalized_keys)
    if isinstance(v, (str, int)):
        s = str(v).strip()
        return s or None
    return None


def score_object(obj: dict[str, Any]) -> tuple[int, set[str]]:
    keys = {norm_key(k) for k in obj}
    hits: set[str] = set()
    score = 0
    for label, terms, weight in (
        ("star", STAR_KEYS, 7),
        ("tier", TIER_KEYS, 6),
        ("stat", STAT_KEYS, 5),
        ("rarity", {norm_key(x) for x in RARITY_KEYS}, 2),
    ):
        if keys & terms:
            hits.add(label)
            score += weight
    joined = " ".join(str(k).lower() for k in obj)
    if "blueprint" in joined:
        score += 2
    if "weapon" in joined:
        score += 2
    if "mult" in joined or "coeff" in joined or "scale" in joined:
        score += 3
    return score, hits


def extract_stat_pairs(obj: dict[str, Any]) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for k, v in obj.items():
        nk = norm_key(k)
        if nk in STAT_KEYS or any(term in nk for term in ("attack", "damage", "firepower")):
            n = number(v)
            if n is not None:
                out.append((str(k), n))
    return out


def walk_json(node: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    yield path, node
    if isinstance(node, dict):
        for k, v in node.items():
            child = f"{path}.{k}" if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(k)) else f"{path}[{json.dumps(str(k))}]"
            yield from walk_json(v, child)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_json(v, f"{path}[{i}]")


def scan_json_file(path: Path, root: Path, max_bytes: int) -> tuple[list[Evidence], Counter]:
    evidence: list[Evidence] = []
    counts: Counter = Counter()
    try:
        if path.stat().st_size > max_bytes:
            return evidence, Counter({"skipped_too_large": 1})
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return evidence, Counter({"json_parse_error": 1})

    rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    for jp, node in walk_json(data):
        if not isinstance(node, dict):
            continue
        score, hits = score_object(node)
        if score < 5:
            continue

        wid = first_text(node, {norm_key(x) for x in ID_KEYS})
        wname = first_text(node, {norm_key(x) for x in NAME_KEYS})
        rarity = first_text(node, {norm_key(x) for x in RARITY_KEYS})
        tier = None
        stars = None
        for k, v in node.items():
            nk = norm_key(k)
            if tier is None and nk in TIER_KEYS:
                tier = parse_intish(v, 1, 5)
            if stars is None and nk in STAR_KEYS:
                stars = parse_intish(v, 1, 6)

        stats = extract_stat_pairs(node)
        keys_str = ",".join(map(str, node.keys()))[:500]
        preview = scalar_preview(node)

        if tier is not None and stats:
            for stat_name, stat_value in stats:
                evidence.append(Evidence(rel, jp, "tier_stat", score, wid, wname, tier, stars, stat_name, stat_value, rarity, keys_str, preview))
                counts["tier_stat"] += 1
        if stars is not None and stats:
            for stat_name, stat_value in stats:
                evidence.append(Evidence(rel, jp, "star_stat", score, wid, wname, tier, stars, stat_name, stat_value, rarity, keys_str, preview))
                counts["star_stat"] += 1
        if tier is not None and stars is not None:
            evidence.append(Evidence(rel, jp, "star_tier_join", score + 5, wid, wname, tier, stars, None, None, rarity, keys_str, preview))
            counts["star_tier_join"] += 1
        if "star" in hits and ("tier" in hits or "stat" in hits):
            evidence.append(Evidence(rel, jp, "progression_candidate", score, wid, wname, tier, stars, None, None, rarity, keys_str, preview))
            counts["progression_candidate"] += 1
        elif score >= 10:
            evidence.append(Evidence(rel, jp, "high_score_candidate", score, wid, wname, tier, stars, None, None, rarity, keys_str, preview))
            counts["high_score_candidate"] += 1

        for k, v in node.items():
            nk = norm_key(k)
            if isinstance(v, list) and 3 <= len(v) <= 12 and any(t in nk for t in ("star", "tier", "scale", "mult", "coeff", "ratio", "enhance", "quality")):
                nums = [number(x) for x in v]
                if all(x is not None for x in nums):
                    evidence.append(Evidence(rel, f"{jp}.{k}", "numeric_curve", score + 4, wid, wname, tier, stars, str(k), None, rarity, keys_str, scalar_preview(v)))
                    counts["numeric_curve"] += 1

    return evidence, counts


def iter_json_files(root: Path) -> Iterable[Path]:
    ignore_dirs = {".git", "node_modules", "venv", ".venv", "__pycache__", "assets", "reference-images"}
    for p in root.rglob("*.json"):
        if not p.is_file():
            continue
        if any(part.lower() in ignore_dirs for part in p.parts):
            continue
        yield p


def infer_tier_curves(evidence: list[Evidence]) -> dict[str, Any]:
    groups: dict[tuple[str, str], dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for e in evidence:
        if e.kind != "tier_stat" or e.tier is None or e.stat_value is None:
            continue
        weapon = e.weapon_id or e.weapon_name or f"{e.source_file}:{e.json_path}"
        groups[(weapon, norm_key(e.stat_name or "stat"))][e.tier].append(e.stat_value)

    normalized_groups = []
    ratio_samples: dict[int, list[float]] = defaultdict(list)
    for (weapon, stat), by_tier in groups.items():
        tiers = {t: statistics.median(vals) for t, vals in by_tier.items() if vals}
        if len(tiers) < 2:
            continue
        base_tier = 1 if 1 in tiers and tiers[1] != 0 else min(tiers)
        base = tiers[base_tier]
        if not base:
            continue
        ratios = {t: v / base for t, v in sorted(tiers.items())}
        for t, r in ratios.items():
            ratio_samples[t].append(r)
        normalized_groups.append({"weapon": weapon, "stat": stat, "base_tier": base_tier, "values": tiers, "ratios": ratios})

    aggregate = {}
    for tier, vals in sorted(ratio_samples.items()):
        if not vals:
            continue
        med = statistics.median(vals)
        mad = statistics.median(abs(v - med) for v in vals) if len(vals) > 1 else 0.0
        aggregate[str(tier)] = {
            "n": len(vals),
            "median_ratio": med,
            "mean_ratio": statistics.fmean(vals),
            "mad": mad,
            "min": min(vals),
            "max": max(vals),
        }
    return {"groups": normalized_groups, "aggregate": aggregate}


def tracer_search(db_path: Path, terms: list[str], per_term_limit: int = 250) -> dict[str, Any]:
    out: dict[str, Any] = {"database": str(db_path), "schema": {}, "hits": []}
    if not db_path.exists():
        out["missing"] = True
        return out
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for table in tables:
            cols = list(con.execute(f'PRAGMA table_info("{table.replace(chr(34), chr(34)*2)}")'))
            out["schema"][table] = [{"name": r[1], "type": r[2]} for r in cols]
            text_cols = [r[1] for r in cols if (r[2] or "").upper() in ("", "TEXT", "VARCHAR", "CHAR", "CLOB")]
            preferred = [c for c in text_cols if norm_key(c) in {"value", "field", "jsonlocation", "sourcefile", "sourcetable", "recordid", "gamelayer", "path"}]
            query_cols = preferred or text_cols[:4]
            if not query_cols:
                continue
            safe_table = table.replace('"', '""')
            for term in terms:
                clauses = " OR ".join(f'CAST("{c.replace(chr(34), chr(34)*2)}" AS TEXT) LIKE ?' for c in query_cols)
                sql = f'SELECT * FROM "{safe_table}" WHERE {clauses} LIMIT ?'
                params = [f"%{term}%"] * len(query_cols) + [per_term_limit]
                try:
                    rows = con.execute(sql, params).fetchall()
                except sqlite3.Error:
                    continue
                for row in rows:
                    d = dict(row)
                    d["_table"] = table
                    d["_term"] = term
                    out["hits"].append(d)
        out["hit_count"] = len(out["hits"])
    finally:
        con.close()
    return out


def dedupe_evidence(items: list[Evidence]) -> list[Evidence]:
    seen = set()
    out = []
    for e in sorted(items, key=lambda x: (-x.score, x.source_file, x.json_path, x.kind, x.stat_name or "")):
        key = (e.source_file, e.json_path, e.kind, e.tier, e.stars, e.stat_name, e.stat_value)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def write_csv(path: Path, evidence: list[Evidence]) -> None:
    fields = list(asdict(Evidence("", "", "", 0)).keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for e in evidence:
            w.writerow(asdict(e))


def write_report(path: Path, root: Path, evidence: list[Evidence], counts: Counter, tier: dict[str, Any], tracer: dict[str, Any] | None) -> None:
    kinds = Counter(e.kind for e in evidence)
    lines = [
        "# Dead Signal Weapon Progression Investigation",
        "",
        f"Input root: `{root}`",
        "",
        "## Purpose",
        "",
        "Find evidence for the exact relationship between **Blueprint Stars × Gear Tier I–V × displayed weapon stats** without assuming a formula.",
        "",
        "## Scan summary",
        "",
    ]
    for k, v in sorted(counts.items()):
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Evidence classes", ""])
    for k, v in kinds.most_common():
        lines.append(f"- {k}: {v}")

    lines.extend(["", "## Aggregate Tier ratios", ""])
    agg = tier.get("aggregate", {})
    if agg:
        lines.append("Ratios are normalized to Tier I when available. They are evidence summaries, **not yet a declared game formula**.")
        lines.append("")
        lines.append("| Tier | n | median | mean | MAD | min | max |")
        lines.append("|---:|---:|---:|---:|---:|---:|---:|")
        for t, s in agg.items():
            lines.append(f"| {t} | {s['n']} | {s['median_ratio']:.8g} | {s['mean_ratio']:.8g} | {s['mad']:.4g} | {s['min']:.8g} | {s['max']:.8g} |")
    else:
        lines.append("No usable repeated Tier stat groups were recovered automatically.")

    if tracer is not None:
        lines.extend(["", "## Reference tracer", ""])
        if tracer.get("missing"):
            lines.append("`reference-tracer.sqlite` was not found/provided.")
        else:
            lines.append(f"- Hits: {tracer.get('hit_count', 0)}")
            lines.append(f"- Tables inspected: {len(tracer.get('schema', {}))}")

    lines.extend(["", "## Highest-value candidates", ""])
    for e in evidence[:80]:
        bits = [f"**{e.kind}**", f"score {e.score}", f"`{e.source_file}`", f"`{e.json_path}`"]
        if e.weapon_name or e.weapon_id:
            bits.append(f"weapon={e.weapon_name or e.weapon_id}")
        if e.tier is not None:
            bits.append(f"tier={e.tier}")
        if e.stars is not None:
            bits.append(f"stars={e.stars}")
        if e.stat_name is not None:
            bits.append(f"{e.stat_name}={e.stat_value}")
        lines.append("- " + " · ".join(bits))

    lines.extend([
        "",
        "## Interpretation rule",
        "",
        "Do not promote any multiplier into Dead Signal's calculator until it reproduces multiple weapons across multiple tiers/stars and the remaining error is explainable by the game's rounding behavior.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Hunt Once Human weapon Blueprint Star × Gear Tier progression evidence in Dead Signal miner exports.")
    ap.add_argument("root", type=Path, help="Miner output root containing raw/normalized JSON exports")
    ap.add_argument("--tracer", type=Path, default=None, help="Optional reference-tracer.sqlite path; auto-detected under root/indexes/")
    ap.add_argument("--out", type=Path, default=None, help="Output directory (default: <root>/investigations/weapon-progression)")
    ap.add_argument("--max-json-mb", type=int, default=128, help="Skip individual JSON files larger than this (default 128 MB)")
    args = ap.parse_args()

    root = args.root.resolve()
    out_dir = (args.out or (root / "investigations" / "weapon-progression")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    evidence: list[Evidence] = []
    counts: Counter = Counter()
    json_files = list(iter_json_files(root))
    counts["json_files_seen"] = len(json_files)
    max_bytes = args.max_json_mb * 1024 * 1024
    for p in json_files:
        ev, c = scan_json_file(p, root, max_bytes)
        evidence.extend(ev)
        counts.update(c)

    evidence = dedupe_evidence(evidence)
    tier_curves = infer_tier_curves(evidence)

    tracer_path = args.tracer
    if tracer_path is None:
        candidates = [root / "indexes" / "reference-tracer.sqlite", root / "reference-tracer.sqlite"]
        tracer_path = next((p for p in candidates if p.exists()), candidates[0])
    tracer = tracer_search(tracer_path.resolve(), [
        "BlueprintStar", "Blueprint Star", "StarLevel", "StarRank", "Enhance", "Enhancement",
        "WeaponTier", "GearTier", "TierLevel", "Attack", "Damage", "Multiplier", "Coefficient",
    ])

    write_csv(out_dir / "weapon-progression-candidates.csv", evidence)
    payload = {
        "schemaVersion": 1,
        "purpose": "Blueprint Stars x Gear Tier I-V x displayed weapon stats",
        "inputRoot": str(root),
        "scanCounts": dict(counts),
        "evidence": [asdict(e) for e in evidence],
        "tierInference": tier_curves,
        "referenceTracer": tracer,
    }
    (out_dir / "weapon-progression-investigation.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(out_dir / "weapon-progression-report.md", root, evidence, counts, tier_curves, tracer)

    print(f"[Dead Signal] scanned {len(json_files)} JSON files")
    print(f"[Dead Signal] evidence rows: {len(evidence)}")
    print(f"[Dead Signal] tracer hits: {tracer.get('hit_count', 0)}")
    print(f"[Dead Signal] output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
