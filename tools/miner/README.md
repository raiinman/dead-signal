# Dead Signal Miner

`tools/miner/` is the canonical editable source for the Dead Signal Once Human Miner: a local, read-only Windows intelligence workstation that turns an installed Once Human snapshot into auditable research, normalized domain records, evidence-gated website datasets, and release diagnostics.

This document is intentionally self-contained. A human operator or a replacement AI should be able to identify the authoritative locations, run and test the Miner, understand its evidence rules, extend it safely, and prepare a release without guessing.

## Current state at a glance

| Item | Canonical value |
| --- | --- |
| Stable Miner release | `v1.5.14.64` |
| Source repository | `raiinman/dead-signal` |
| Source branch | `main` |
| Editable source | `tools/miner/` in this repository |
| Typical packaged installation | `C:\Users\mikea\OneDrive\Desktop\Dead Signal Miner` |
| Typical installed game | `C:\Program Files (x86)\Steam\steamapps\common\Once Human` |
| Canonical generated output | `C:\Users\mikea\Documents\Dead Signal Miner` |
| Primary UI | Evidence Graph workspace |
| Current schema-locked domain | Weapons v1 |
| Current expansion state | Evidence Graph Expansion Phase 0 complete; Phase 1 next |
| Source test baseline | 213 tests passing at the Phase 0 handoff |

Never hard-code the observed weapon count, external catalog counts, or snapshot totals. Counts describe one installed snapshot; identity comes from exact installed-game owners and player-facing filtering rules.

## Read order before changing source

Read these files completely, in this order:

1. `PROJECT-RULES.md`
2. `AI-CONTINUITY.md`
3. `HANDOFF-CURRENT.md`
4. The current handoff named by `HANDOFF-CURRENT.md`
5. `EVIDENCE-GRAPH-EXPANSION-WORK-PLAN.md` when working beyond Weapons
6. `tools/miner/docs/EVIDENCE-GRAPH-COMPATIBILITY.md`
7. `tools/miner/docs/DATA-INTELLIGENCE.md`
8. `tools/miner/docs/weapons-v1.schema.json` for Weapons publication changes
9. `tools/miner/RELEASING.md` before building or publishing a release

The current operational handoff is authoritative over historical handoffs. Historical files remain useful design rationale and evidence history, but they are not automatic instructions to restart completed work.

## Authority and directory boundaries

There are three different things that must not be confused:

### 1. GitHub source

The repository's `tools/miner/` directory is authoritative for maintained code, tests, build scripts, documentation, release metadata, and the application version.

### 2. Packaged application

The user's desktop folder contains built executables and packaged runtime files. It is an installed artifact, not the canonical editable source. Do not reverse-edit the executable and then treat it as source.

The normal entry point is:

```text
Dead Signal Miner.exe
```

`Dead Signal Miner Updater.exe` is the separate update installer, not the normal application entry point.

### 3. Generated Miner output

The output directory contains the installed snapshot, persistent indexes, research, evidence reports, normalized records, publication artifacts, artwork, and run state. This data is local and may be large or machine-specific. It must not be committed unless a small, deliberately sanitized fixture or baseline is explicitly approved.

Do not commit or publish:

- raw game archives or extracted full-game exports;
- local Miner snapshots;
- `reference-tracer.sqlite` or other machine-scale research databases;
- persistent local catalog databases;
- Intelligence ZIPs or raw evidence bundles;
- packaged Python runtimes, executables, or release ZIPs;
- machine-specific absolute paths;
- the pre-existing untracked `tools/miner.zip`.

## Safety contract

The Miner treats the installed game as read-only. It may fingerprint and read archives, executable bytes, tables, translations, PYC files, and resource data, but it must not modify the game, Steam, anti-cheat, or installation state.

The NeoX/PYC path is static analysis only:

- parse data payloads without importing game modules;
- preserve safe names, constants, code scopes, offsets, opcodes, and raw tokens;
- tolerate opcode-version mismatches;
- never execute transformed or extracted game bytecode.

Mining and analysis are local. AI and community sources may suggest where to investigate, but they do not create proof.

## Evidence doctrine

Dead Signal is evidence-first and fail-closed. A plausible relationship is not a published fact.

### Evidence states

The exact field names vary by artifact, but the semantic boundary is:

| State | Meaning | Publication behavior |
| --- | --- | --- |
| Proven / resolved | An exact typed installed-game owner or consumer chain establishes the claim. | May publish with provenance. |
| Partial | Some required relationships are proven, but the full claim is incomplete. | Publish only the proven portion and disclose the gap. |
| Exact evidence located, semantics pending | The record or edge exists, but its player-facing meaning is not yet proven. | Retain for research; do not promote the inferred meaning. |
| Unresolved | Retained installed data does not establish the required relationship. | Show as unresolved or withhold the field. |
| Not applicable | The relationship does not apply to the record. | Preserve explicitly; do not treat it as missing. |
| Conflict | Exact evidence sources disagree or precedence is unproven. | Quarantine from authoritative publication. |

### What does not count as proof

Never promote a claim based only on:

- spelling, substring, or fuzzy-name similarity;
- a bare number that appears elsewhere;
- globally matching scalar values;
- an external database's record or total;
- a wiki, video, screenshot, search result, or community post;
- an AI-generated interpretation;
- a graph path with no typed semantic owner;
- absence of one conventional owner when alternate systems may exist.

Evidence Graph and Identity Map locate candidates. Guided Schema Trace and exact typed-owner/consumer chains establish semantics.

### Required distinctions

Preserve these distinctions in code, reports, and UI:

- missing recipe evidence does not prove an item is non-craftable;
- a proven seasonal formula owner with a missing material body is not a missing owner;
- missing conventional passive-skill ownership does not prove a weapon has no mechanic;
- Weapon Description and Special Skill are separate evidence lanes;
- a direct ID edge can be proven while trigger, chance, duration, stack, cooldown, or operation semantics remain unresolved;
- special/scenario availability remains unresolved until exact activation evidence exists;
- Gear Tier is I–V; Blueprint Stars are a separate rarity-capped system;
- current calibration-blueprint behavior must not be mixed silently with legacy calibration behavior.

## Product architecture

The Miner is a staged local data system, not a single scrape-and-export script.

```text
Installed Once Human snapshot
        |
        v
Mine -> Index -> Resolve -> Compile -> Verify
        |         |          |          |
        |         |          |          +-- publication gate and diagnostics
        |         |          +------------- normalized/research/site artifacts
        |         +------------------------ typed owners and evidence states
        +---------------------------------- persistent tables and PYC consumers
```

### Mine

- Detects or accepts the Once Human installation.
- Fingerprints relevant base/current archives and executable state.
- Locates and validates the matching Zstandard dictionary.
- Extracts supported structured tables from retained layers.
- Parses NeoX bindict data without executing bytecode.
- Merges localization evidence.
- Resolves supported game display resources into web-ready artwork.

### Index

- Maintains the content-fingerprinted structural table registry.
- Maintains the static PYC consumer index.
- Maintains typed reference edges and graph databases.
- Reuses unchanged profiles instead of rescanning unchanged content.

### Resolve

- Builds exact domain identity spines.
- Follows typed owners and consumers.
- Separates candidate, proven, rejected, unresolved, and not-applicable relationships.
- Applies the semantic registry and structured promotion policy.

### Compile

- Produces normalized domain datasets.
- Builds research and evidence reports.
- Creates lean website listing/detail artifacts.
- Computes snapshot changes and dependency invalidation.
- Packages the Data Intelligence bundle when requested.

### Verify

- Runs source and artifact integrity checks.
- Reports coverage by semantic evidence state.
- Detects publication blockers and conflicts.
- Keeps unresolved research from silently entering player-facing output.

## Completed architecture phases

The architecture upgrade is complete through Phase 7. Do not restart it:

1. Persistent table registry and full `client_data` census.
2. Persistent static PYC consumer index.
3. Typed reference graph with explicit candidate/proven/rejected states.
4. Semantic registry, structured promotion engine, and family inheritance registry.
5. Registry-backed Base/Current snapshot diff and dependency invalidation.
6. Lean website delta and field-level publication diagnostics.
7. Coverage dashboard integrated into the Miner.

Evidence Graph Expansion is a separate cross-domain program. Phase 0 froze the Weapons graph behavior as a compatibility baseline. Phase 1 is the next expansion phase; consult the work plan and current handoff before implementing it.

## User interface

Release `.64` opens directly on the first-class Evidence Graph workspace. `.63` nested the new workspace too deeply and is not the accepted interface baseline.

### Run Pipeline

Runs Mine → Index → Resolve → Compile → Verify. The UI supports a complete run and changed-stage work when reusable state exists. Do not fake progress or evidence-health values; UI status must come from generated run state and reports.

### Evidence Graph

The primary investigation surface. A trace should let the operator see the selected entity, typed relationships, provenance, state, blockers, and publication impact. The known `.64` acceptance control is the default SOCR - The Last Valor trace reaching `SCAN COMPLETE` with 27 interactive graph objects against the accepted local snapshot.

### Explore Data

Provides searchable access to tables, normalized data, reports, exact identifiers, and retained research. Discovery results are leads, not automatic verification.

### Data Intelligence task hubs

The consolidated interface uses five hubs rather than exposing every specialist tool at once:

- **Overview** — evidence health and next work selection.
- **Explore** — tables, records, indexes, and analytics.
- **Trace & Resolve** — Source Finder, Evidence Graph, Schema Trace, Description Flow, and Discovery.
- **Review & Publish** — Workflow Lab, Verification, Publication Gate, Launch Coverage, and Pipeline Inspector.
- **Build** — Compiler, changed-stage work, and bundle export.

Specialist tools retain contextual back-navigation. Do not reintroduce a wall of tabs or weaken manual verification to simplify the interface.

### Publish & Verify

Shows site output, site delta, evidence reports, health, blockers, and gate decisions. A `PUBLISHABLE` research decision is advisory unless the appropriate compiler/publisher explicitly projects the proven fields.

## Weapons v1 schema lock

Weapons v1 is the reference implementation and compatibility baseline. The identity model is installed-game-driven and must not be changed merely to match an external catalog.

The accepted identity spine starts from current `item_data + equip_data` identity and treats blueprint/progression as conditional enrichment. The observed `.62` snapshot produced 130 identities—117 standard-blueprint, 7 nonstandard-blueprint, and 6 special-equipped—but `130` is not a universal constant.

Weapons v1 currently covers:

- exact weapon identity and public filtering;
- blueprint/progression enrichment when an exact owner exists;
- Tier I–V and rarity-capped Blueprint Star representation;
- descriptions through the prototype description producer path;
- special effects as a separate lane;
- ranged gun profiles and proven static weapon fields;
- attachment compatibility;
- calibration compatibility;
- selectable ammunition;
- acquisition and crafting evidence distinctions;
- Cradle applicability;
- artwork linkage;
- launch/readiness warnings and site projection.

Core Weapons identity or relationship semantics may change only when new installed-game evidence requires a schema revision. Update the schema-lock tests and compatibility baseline deliberately; never patch around them with a fixed count.

Parked or unresolved evidence remains unresolved, including magazine aggregation, quarantined description conflicts, alternate ownerless fixed-skill semantics, and special scenario activation unless newer exact evidence closes a lane.

## Maintained source layout

```text
tools/miner/
├── README.md                         this guide
├── RELEASING.md                      release boundary and manifest-last procedure
├── VERSION                           single canonical application version
├── requirements.txt                  runtime dependencies
├── requirements-build.txt            build-only dependencies
├── Start Dead Signal Miner.cmd       source-development launcher
├── setup-build.ps1                   isolated Windows build environment
├── build.ps1                         PyInstaller application/updater build
├── package-release.ps1               versioned ZIP, size, and SHA-256
├── release/latest.json               updater manifest; publish last
├── assets/                            maintained application assets
├── baselines/                         reviewed compatibility baselines
├── docs/                              architecture and schema documentation
├── scripts/                           bounded maintenance/import helpers
├── src/
│   ├── dead_signal_miner.py           GUI and headless entry point
│   ├── miner_core.py                  complete pipeline coordinator
│   ├── miner_entry.py                 packaged entry support
│   ├── update_manager.py              update discovery/download verification
│   ├── miner_updater.py               out-of-process Windows installer
│   ├── dead_signal_*                  intelligence, graph, trace, gate, and UI modules
│   ├── extractor/                     normalization, projection, artwork, and domain stages
│   └── neoxtractor/                   data-only NeoX/bindict parsing
└── tests/                              source, contract, UI, publication, and release tests
```

Generated `build/`, `dist/`, local virtual environments, release ZIPs, and full outputs are artifacts, not maintained source.

## Persistent architecture files

Important local databases include:

- `catalogs/dead-signal-table-registry.sqlite` — content-fingerprinted structural table catalog;
- `catalogs/dead-signal-consumer-index.sqlite` — static PYC scopes, names, safe constants, hierarchy, and raw-token fallbacks;
- `catalogs/dead-signal-reference-graph.sqlite` — typed relationship graph used for trace and invalidation.

Use these indexes before launching a new broad scan. A broad rescan is justified only when the snapshot changed, the required family is absent, or a verified limitation in the retained index prevents the bounded query.

## Generated output layout

Exact files depend on completed stages and snapshot contents. Treat the following as roles, not a promise that every run creates every optional directory:

```text
<output>/
├── catalogs/             persistent structural and consumer indexes
├── manifests/            snapshot/run inventory and fingerprints
├── snapshots/            retained Base/Current structured snapshot material
├── normalized/           domain-normalized intermediate records
├── indexes/              searchable resource/domain indexes
├── research/             non-publishing traces and forensic reports
├── published/
│   ├── data/             authoritative rich domain evidence records
│   ├── web/              compact player-facing prepared datasets
│   ├── site/             lean listing/detail and site delta artifacts
│   └── reports/          quality, coverage, trace, conflict, and gate reports
├── assets/               resolved website-ready artwork
├── reports/              additional operator-facing reports
└── scratch/              disposable diagnostics and bounded temporary work
```

### Key publication and research artifacts

Common high-value outputs include:

- `published/data/weapons.json` — rich evidence-bearing Weapons records;
- `published/site/weapons-v2.json` — lean website projection;
- `published/site/weapon-evidence.json` — detail evidence payload;
- `published/site/site-delta.json` — field/site change diagnostics;
- `published/web/weapon-configuration.json` — configuration inputs kept separate from catalogue payloads;
- `published/web/relationship-graph.json` — direct mined identity links without invented runtime semantics;
- `published/reports/dead-signal-coverage-dashboard.json` — semantic coverage state;
- `published/reports/dead-signal-publication-gate.json` — publication gate result;
- `published/reports/dead-signal-self-diagnostics.json` — internal diagnostics;
- `published/reports/client-data-census.json` — structural census whose labels are discovery hints, not proof;
- `published/reports/table-registry-summary.json` and `consumer-index-summary.json` — index health;
- `published/reports/snapshot-data-diff.json` — Base/Current changes and impact;
- `research/schema-trace-all-weapons.json` — full Weapons typed schema trace;
- `research/missing-fixed-skill-forensics.json` — bounded alternate-owner forensic output.

Read artifact-level `schema`, `schema_version`, `source`, `state`, and provenance fields before consuming a file. Do not assume similarly named `published/data`, `published/web`, and `published/site` files are interchangeable.

## Install development dependencies

From the repository root in PowerShell:

```powershell
python -m venv .venv-miner
.\.venv-miner\Scripts\python.exe -m pip install -r tools\miner\requirements.txt
```

The project currently pins Pillow, LZ4, texture decoding, Zstandard, DuckDB, Polars, and PyArrow. Build environments additionally install PyInstaller through `requirements-build.txt`.

## Run from source

The maintained source launcher is:

```powershell
& 'tools\miner\Start Dead Signal Miner.cmd'
```

For an explicit invocation from the repository root:

```powershell
$env:PYTHONPATH = ((Resolve-Path 'tools\miner\src').Path + ';' + (Resolve-Path 'tools\miner\src\extractor').Path + ';' + (Resolve-Path 'tools\miner\src\neoxtractor').Path)
.\.venv-miner\Scripts\python.exe tools\miner\src\dead_signal_miner.py
```

Headless full run:

```powershell
$env:PYTHONPATH = ((Resolve-Path 'tools\miner\src').Path + ';' + (Resolve-Path 'tools\miner\src\extractor').Path + ';' + (Resolve-Path 'tools\miner\src\neoxtractor').Path)
.\.venv-miner\Scripts\python.exe tools\miner\src\dead_signal_miner.py --run --install 'C:\Program Files (x86)\Steam\steamapps\common\Once Human' --output 'C:\Users\mikea\Documents\Dead Signal Miner' --mode full
```

Supported top-level CLI options are:

- `--self-test`
- `--run`
- `--install PATH`
- `--output PATH`
- `--mode full`

If `--run` cannot detect Once Human and `--install` is omitted, it exits rather than guessing.

## Verification

Run verification from the repository root with the Miner virtual environment active or explicitly selected.

### Fast syntax/import check

```powershell
.\.venv-miner\Scripts\python.exe -m compileall -q tools\miner\src tools\miner\tests
```

### Complete source test suite

```powershell
$env:PYTHONPATH = ((Resolve-Path 'tools\miner\src').Path + ';' + (Resolve-Path 'tools\miner\src\extractor').Path + ';' + (Resolve-Path 'tools\miner\src\neoxtractor').Path)
.\.venv-miner\Scripts\python.exe -m unittest discover -s tools\miner\tests -v
```

### Source self-test

```powershell
$env:PYTHONPATH = ((Resolve-Path 'tools\miner\src').Path + ';' + (Resolve-Path 'tools\miner\src\extractor').Path + ';' + (Resolve-Path 'tools\miner\src\neoxtractor').Path)
.\.venv-miner\Scripts\python.exe tools\miner\src\dead_signal_miner.py --self-test
```

The self-test checks maintained engine files and imports. It requires dependencies and a detectable Once Human installation but does not perform a full mine.

### Test selection guidance

Always run the complete source suite before a release. During development, also run the narrow tests for the changed contract. Examples:

- identity/evidence: `test_weapon_identity_spine.py`, `test_weapon_schema_trace.py`;
- attachments/calibration/ammo: `test_attachment_compatibility.py`, `test_weapon_build_compatibility.py`, `test_weapon_configuration.py`;
- publication: `test_weapon_site_projection.py`, `test_publish_web_integrity.py`;
- graph architecture: `test_reference_graph.py`, `test_evidence_graph_phase0_baseline.py`;
- persistent indexes: `test_table_registry.py`, `test_consumer_index.py`;
- UI: `test_data_intelligence_ui.py`, `test_miner_ui_lifecycle.py`;
- updater/release: `test_update_manager.py`, `test_miner_updater.py`, `test_packaging_entrypoint.py`.

Do not rewrite a reviewed baseline merely to make a regression pass. Determine whether installed evidence requires an intentional compatibility revision.

## Build a Windows package

From `tools/miner/` in PowerShell:

```powershell
.\setup-build.ps1
.\build.ps1
python src\dead_signal_miner.py --self-test
.\dist\Dead Signal Miner\Dead Signal Miner.exe --self-test
.\package-release.ps1
```

The build creates the main application and separate updater helper. The packaging script creates the versioned ZIP and prints its exact byte size and SHA-256.

Do not commit `dist/`, `build/`, the packaged runtime, or generated release archives.

## Release procedure: manifest last

`tools/miner/VERSION` is the canonical application version. A source commit on `main` does not automatically make an installed Miner update. Installed applications discover releases through `tools/miner/release/latest.json`.

Required order:

1. Complete the intended source change.
2. Update tests and documentation.
3. Run the full source suite.
4. Set the intended version in `VERSION` and all explicitly version-coupled metadata.
5. Build the Windows package.
6. Run source and packaged self-tests.
7. Create the versioned ZIP/checksum.
8. Upload the ZIP as the GitHub release asset.
9. Download or inspect the public asset and verify exact byte size and SHA-256.
10. Update and publish `release/latest.json` **last**.
11. Verify the public manifest describes the already-available verified asset.

The updater accepts only GitHub-hosted HTTPS downloads, verifies declared byte size and SHA-256, then hands installation to the separate updater after the Miner closes. The helper provides rollback for files already being replaced.

Never publish the manifest before the asset is available and verified. That would expose installed users to an update boundary that cannot be satisfied safely.

## How to add or expand a game domain

Do not begin by building a page or matching another site's inventory. Follow the evidence architecture:

1. Read the expansion plan and current handoff.
2. Define the player-facing identity owner from installed data.
3. Record the exact source tables, keys, layers, and consumer evidence.
4. Model typed edges and explicit applicability.
5. Separate proven, partial, unresolved, not-applicable, and conflict states.
6. Add normalization without erasing raw provenance.
7. Add bounded research reports for unknown lanes.
8. Add publication projection that emits only permitted semantics.
9. Add coverage and publication-gate diagnostics.
10. Add fixtures, contract tests, and compatibility baselines.
11. Run against the real local persistent indexes before any broad rescan.
12. Update the current handoff with exact results and remaining blockers.

For Armor and Armor Sets, for example, first establish exact piece identity, slot ownership, set membership, Key Armor identity, tier data, set-bonus owners, effect owners, recipes/material bodies, acquisition, and artwork. Do not infer a set relationship from matching names alone.

## Efficient research workflow

Use:

```text
Locate -> Inspect -> Follow -> Verify
```

- **Locate** with persistent table/consumer indexes and exact identifiers.
- **Inspect** the bounded source record and its layer/provenance.
- **Follow** typed owners or static consumer paths.
- **Verify** the player-facing semantic meaning and publication state.

Prefer exact owner fields, indexed code consumers, and cohort discriminators over brute-force graph traversal. Stop a broad scan when the bounded evidence question is answered. Preserve unresolved state when it is not.

## AI continuation checklist

An AI taking over Miner work should perform this checklist before editing:

1. Confirm the working directory is the canonical repository checkout, not the packaged desktop folder.
2. Read the required documents in the stated order.
3. Check `git status`, current branch, and `origin/main` without modifying unrelated work.
4. Preserve the untracked `tools/miner.zip`.
5. Read `VERSION`; do not assume a version from conversation history.
6. Inspect the local output and persistent indexes before requesting an upload or running broad discovery.
7. State the exact evidence question and the publication field it affects.
8. Identify whether the work is research-only, normalization, publication, UI, build, or release work.
9. Keep discovery candidates separate from verified evidence.
10. Add or update narrow tests, then run the full suite in proportion to risk.
11. Review the exact diff and stage only intended files.
12. Update the current handoff with commands, results, counts, blockers, and next action.
13. Do not build, release, alter updater metadata, deploy the website, or push unrelated files unless explicitly authorized.

If another AI still needs to ask what is canonical, where the output lives, whether fuzzy matching is allowed, whether game bytecode may execute, what branch is used, what tests to run, or how releases are ordered, the answer is already in this document and the referenced current handoff.

## Common failure modes

- Editing the packaged desktop folder instead of `tools/miner/` source.
- Treating community totals as a completeness target.
- Hard-coding an observed snapshot count.
- Converting a fuzzy alias or graph candidate into a typed identity.
- Equating a missing conventional owner with a missing mechanic.
- Publishing a raw code with an invented label.
- Re-running a multi-hour broad scan before querying persistent indexes.
- Claiming an interrupted full compile completed.
- Committing generated snapshots, local databases, or Intelligence bundles.
- Touching protected `tools/miner.zip`.
- Updating `release/latest.json` before the public asset is verified.
- Changing production hosting or cPanel behavior during Miner work.

## Relationship to the website

The Miner prepares player-facing data; it does not replace the website's copy-only deployment architecture. Normal cPanel deployment must not mine, normalize, download, unzip, scan, or rebuild game data on the server.

Do not change DNS, SSL, redirects, hosting configuration, the accepted landing page, or the Official Once Human feed while performing Miner work. Website routes that are not genuinely complete remain `SOON`.

## Additional documentation

- [`docs/DATA-INTELLIGENCE.md`](docs/DATA-INTELLIGENCE.md) — workspace architecture, research tools, and evidence policy.
- [`docs/EVIDENCE-GRAPH-COMPATIBILITY.md`](docs/EVIDENCE-GRAPH-COMPATIBILITY.md) — Phase 0 graph compatibility contract.
- [`docs/PUBLISHING-v1.5.12.0.md`](docs/PUBLISHING-v1.5.12.0.md) — historical publishing architecture foundation.
- [`docs/weapons-v1.schema.json`](docs/weapons-v1.schema.json) — schema-locked Weapons contract.
- [`RELEASING.md`](RELEASING.md) — concise build and release checklist.
- [`MIGRATION-v1.5.7.4.md`](MIGRATION-v1.5.7.4.md) — recovered-source provenance.

## Credits and legal note

Dead Signal Miner is part of the Dead Signal Once Human workstation and database project. Once Human names, artwork, and game data remain the property of their respective owners. The Miner exists to create a locally auditable, provenance-preserving data foundation for the Dead Signal player tools.
