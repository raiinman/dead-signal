# Dead Signal Miner

`tools/miner/` is the canonical source for the Dead Signal Once Human Miner. The application reads the user's installed game files locally and produces structured, website-ready snapshots without uploading the game files or spending AI usage on extraction.

## Maintained layout

```text
tools/miner/
├── src/
│   ├── dead_signal_miner.py     Windows GUI and headless entrypoint
│   ├── miner_core.py            local extraction pipeline coordinator
│   ├── update_manager.py        update discovery, download, and verification
│   ├── miner_updater.py         out-of-process Windows update installer
│   ├── extractor/               recovered and maintained extraction engine
│   └── neoxtractor/             data-only bindict parser
├── assets/                      application icon
├── tests/                       updater and source-integrity tests
├── release/latest.json          in-app update manifest
├── build.ps1                    reproducible PyInstaller build
├── package-release.ps1          versioned ZIP and SHA-256 generation
├── setup-build.ps1              isolated Windows build environment
├── VERSION                      one canonical application version
└── MIGRATION-v1.5.7.4.md        recovered-source provenance
```

Generated Miner output, game archives, SQLite indexes, Python runtimes, executables, and release ZIPs are intentionally excluded from Git.

## Run from source

Install `requirements.txt`, then run `Start Dead Signal Miner.cmd` or:

```powershell
$env:PYTHONPATH = 'tools/miner/src;tools/miner/src/extractor;tools/miner/src/neoxtractor'
python tools/miner/src/dead_signal_miner.py
```

The interface remains centered on one action: **Mine Complete Database**. It mines every supported database category and referenced display artwork, then automatically builds website publishing artifacts and integrity reports. The retired WordPress Studio copy workflow has been removed.

### v1.5.12.0 — Publishing & Integrity

Version 1.5.12.0 turns the Miner into the authoritative content pipeline for Dead Signal, not just the extraction engine. After normalization and artwork linking it now publishes:

- `published/web/weapons.json` — compact player-facing weapon records combining normalized identity, acquisition, combat/handling/falloff fields, Tier I–V recipes, Blueprint Stars, proven Tier × Star math, firearm profile identifiers, and configuration catalogs;
- `published/web/weapon-configuration.json` — fail-closed weapon configuration inputs separated from the main weapon catalogue payload;
- `published/web/armor.json` — compact Armor Sets, pieces, Key Armor, Tier I–V stats, set bonuses, Key Armor effects, recipes, and crafting material groups;
- `published/web/relationship-graph.json` — direct mined identity links such as weapon → gun → ammo/skill and equipment → passive skill → buff, explicitly without inventing trigger/chance/stack/duration semantics;
- `published/web/catalog-index.json` — record-count index across normalized audit datasets;
- `published/reports/data-quality.json` — internal readiness checks based only on Dead Signal's mined player-facing corpus and required relationships, never community-site item counts;
- `published/reports/change-report.json` and `CHANGE-REPORT.txt` — added/removed/changed canonical records compared with the previous successful published web snapshot;
- `published/snapshot-manifest.json` — Miner version, base/current script fingerprints, game executable hash, resource-index fingerprint, pipeline-source hashes, output sizes, and SHA-256 hashes for published JSON artifacts.

The first v1.5.12.0 run establishes the local comparison baseline. Later runs report actual changes in the installed game snapshot without comparing Dead Signal's corpus to Wikily, OnceHumanDB, or another community database.

The relationship graph is deliberately an evidence scaffold. A direct ID link can be `proven-direct-link` while runtime semantics remain unresolved. Future mechanic work can add trigger, chance, stack, duration, cooldown, and stat-operation resolvers only when the full path is proven.

### Weapon evidence exports retained

The existing weapon evidence pipeline remains intact:

- `published/data/weapon-math.json` validates every legal Gear Tier × Blueprint Star combination and implements only proven static Attack math;
- `published/data/weapon-configuration.json` traces ammo, attachment, weapon Mod, and current Calibration inputs with fail-closed static-modifier eligibility;
- `published/data/gun-profiles.json` preserves the canonical item-to-gun spine and directly linked firing, stability, scatter, accessory-slot, range-template, reload-template, and downstream IDs.

Runtime procs, enemy mitigation, conditional buffs, and configured DPS remain excluded until independently proven.

## Dead Signal Data Intelligence

The Miner now includes a branded, read-only **DEAD SIGNAL / DATA INTELLIGENCE** workspace layered on top of completed local snapshots. It combines the NeoX Explorer, Table Profiler, Weapon Description Source Finder, exact Evidence Graph, Identity Map, embedded DuckDB/Polars/Arrow analytics, Workflow Lab, Discovery, Pipeline Inspector, manual Verification registry, and generalized Publication Gate.

The canonical Miner completes extraction/normalization/publishing first. Data Intelligence then generates non-publishing research products. Discovery, clustering, analytics, and workflows can suggest leads but cannot assign `VERIFIED`; only explicit manual evidence review can do that. Even a `PUBLISHABLE` Publication Gate decision is advisory and does not automatically rewrite `published/web/*`.

`COMPILE DATA INTELLIGENCE` also maintains `catalogs/dead-signal-table-registry.sqlite`, a content-fingerprinted structural catalog of every Base and Current JSON table. Unchanged tables reuse their prior profiles. The compiler writes `published/reports/table-registry-summary.json` and a first-class `published/reports/client-data-census.json`; all domain, presentation, translation, and reference labels in these reports are discovery hints rather than semantic proof.

See [`docs/DATA-INTELLIGENCE.md`](docs/DATA-INTELLIGENCE.md) for the complete architecture, evidence-state definitions, automatic report list, and Weapon Description verification policy.

## Verify

```powershell
python -m compileall -q tools/miner/src tools/miner/tests
python -m unittest discover -s tools/miner/tests -v
python tools/miner/src/dead_signal_miner.py --self-test
```

The self-test requires the dependencies and a detectable Once Human installation. It checks the maintained engine files and imports without mining the game.

## Build and release

See `RELEASING.md`. `setup-build.ps1` creates a dedicated build environment, `build.ps1` produces the Miner plus its separate updater helper, and `package-release.ps1` creates the versioned ZIP/checksum. Publish `release/latest.json` only after its exact release asset is online and verified.

The in-app updater accepts only GitHub-hosted HTTPS downloads and verifies declared byte size and SHA-256 before installation. Installation happens in a separate helper after the Miner closes, with rollback for files already being replaced.

## Source and data safety

- GitHub source is authoritative; release ZIPs are artifacts.
- The Miner keeps the existing NPK/PYC extraction design and does not execute transformed game bytecode.
- Do not commit generated snapshots, `reference-tracer.sqlite`, raw game archives, or packaged runtimes.
- Do not turn discovered ratios into calculator formulas without multi-entity evidence and rounding validation.
- Production hosting remains governed by the repository's copy-only cPanel process; Miner work must not modify it.
