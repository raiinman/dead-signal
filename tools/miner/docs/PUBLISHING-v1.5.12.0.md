# Dead Signal Miner v1.5.12.0 — Publishing & Integrity

## Goal

Make one successful local mine produce the complete handoff required by Dead Signal's website and future mechanic resolvers.

The installed-game Miner remains the authority for current player-facing record counts. Community databases are design/UX references only and are never used to decide whether a record should exist.

## New publishing stage

After normalization and artwork linking, `publish_web_data.py` creates a stable `published/web/` layer and integrity reports.

### Web contracts

- `web/weapons.json`
- `web/weapon-configuration.json`
- `web/armor.json`
- `web/relationship-graph.json`
- `web/catalog-index.json`

Audit-grade normalized files remain under `published/data/`; the new web layer is the compact consumption contract for Dead Signal.

## Integrity outputs

- `reports/data-quality.json` measures internal invariants, unique canonical IDs, Tier coverage, proven firearm-profile resolution, effect/recipe/artwork coverage, and Armor readiness.
- `reports/change-report.json` and `reports/CHANGE-REPORT.txt` compare the new web snapshot against the previous local web snapshot.
- `snapshot-manifest.json` records Miner version, base/current script SHA-256 fingerprints, game executable/resource/pipeline fingerprints, and SHA-256/size metadata for published JSON artifacts.

## Relationship graph contract

The initial graph records direct identifiers and evidence only. Examples:

- weapon → `gun_no`
- gun → ammo item
- gun → linked skill ID
- weapon → fixed passive skill → buff/keyword status
- Armor piece → Armor Set
- Key Armor → passive skill → buff

Every initial edge is explicitly `proven-direct-link`. The graph does **not** claim trigger conditions, proc chance, stacks, duration, cooldown, refresh behavior, additive/multiplicative buckets, or DPS.

That distinction is the foundation for later runtime-effect resolution: relationship evidence can exist before calculator eligibility.

## Removed workflow

WordPress Studio fields, CLI switches, settings, and copy logic were removed. Dead Signal no longer uses WordPress. The Miner's supported publishing destination is its own `published/` output, which the repository/site build can consume as prepared data.

## Update-channel note

GitHub remains the authoritative source and the installed Miner checks `tools/miner/release/latest.json`. Do not publish `latest.json` for v1.5.12.0 until Codex/local Windows has built and tested the exact release ZIP and its public GitHub asset URL, byte size, and SHA-256 are known. The manifest is updated last so installed Miners never see an unverifiable update.
