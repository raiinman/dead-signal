# Dead Signal — Codex Local Takeover Handoff

> **Canonical repo:** `raiinman/dead-signal`
> **Branch:** `main`
> **Date:** 2026-08-18 America/Phoenix
> **For:** Local Codex session with direct access to the user's Dead Signal Miner output and repository checkout
> **Stable packaged Miner baseline:** `v1.5.14.61`
> **Current source state:** `main` contains substantial post-.61 architecture/UI work that is not yet a packaged release

## Authority / precedence

Read these files completely before changing code:

1. `PROJECT-RULES.md`
2. `AI-CONTINUITY.md`
3. `HANDOFF-2026-08-17-MINER-ARCHITECTURE-UPGRADE.md`
4. **this handoff**

For current operational state, **this handoff supersedes older Miner/Weapons handoffs where they conflict**. Older files remain valuable as evidence history and design rationale.

Do not restart the project or redo already-closed forensic lanes.

---

# Why Codex is taking over now

The local Codex session has an advantage the remote assistant does not: it can inspect the user's actual completed Miner output, persistent architecture databases, very large reports, and repository checkout directly on disk.

Use that local access aggressively but safely.

Do **not** ask the user to upload giant Intelligence bundles when the same evidence is already present locally.

Resolve the active Miner output directory from the user's local `last-run.json` / Miner settings rather than hardcoding machine-specific paths into source or commits.

The local output contains the authoritative completed Once Human snapshot plus the post-.61 architecture products. Treat installed-game/Miner evidence as authoritative.

---

# Immediate objectives

## Objective A — Determine the actual current state from local files

Before making further architectural assumptions, inspect the local completed output directly:

- `last-run.json`
- `published/data/`
- `published/web/`
- `published/site/`
- `published/reports/`
- `research/`
- `catalogs/`
- newest `intelligence/Dead-Signal-Intelligence-*` output if useful

Inspect the persistent databases directly where appropriate:

- `catalogs/dead-signal-table-registry.sqlite`
- `catalogs/dead-signal-consumer-index.sqlite`
- `catalogs/dead-signal-reference-graph.sqlite`
- `catalogs/dead-signal-analytics.duckdb`
- existing structured-table/reference indexes as needed

Use the local files to answer:

1. Which post-.61 architecture phases are genuinely complete vs scaffolding?
2. Which outputs are internally consistent?
3. Which stages are still doing redundant full scans despite the new indexes?
4. Which website-facing fields are actually resolved after post-.61 promotion?
5. What are the real remaining Weapons launch blockers?
6. Which `client_data` tables/relationships are immediately useful beyond the previously known subset?
7. Is the redesigned Miner UI accurately representing what the pipeline does?

Do not infer these from commit names alone. Verify against code and local outputs.

## Objective B — Fix the Intelligence bundle/export design

The latest local Data Intelligence compile produced an approximately **6 GB** output/bundle footprint. This is not acceptable as the normal AI/review handoff artifact.

The new architecture itself appears to work; the bundling policy is the problem.

Observed latest compile summary:

- 41,771 registry tables
- 94,165 PYC files indexed
- 562,321 consumer scopes
- 919 reference-graph edges
- 12 semantic definitions
- 10,886 `client_data` table instances / 10,703 distinct `client_data` paths
- 120 weapons
- cache statistics: **135,936 files considered, 0 changed, 135,936 reused**
- 41,771 tables reused, 0 reprofiled
- 94,165 PYCs reused, 0 reindexed

This proves the new cache/index layer is functioning on an unchanged snapshot.

However, `dead_signal_intelligence_compiler._bundle_members()` currently includes persistent local architecture databases and broadly includes report/research JSON files. That causes the shareable bundle to absorb data that should remain local.

Known large local artifacts include approximately:

- `published/reports/snapshot-data-diff.json` — ~891 MB
- `published/data/weapon-progression-investigation.json` — ~293 MB
- `published/reports/weapon-progression-pyc-consumers.json` — ~269 MB
- `published/data/buffs.json` — ~62 MB
- `published/reports/weapon-description-static-dataflow.json` — ~37 MB
- `published/reports/common-data-registry-static-audit.json` — ~35 MB
- `published/reports/dead-signal-table-profiles.json` — ~27 MB
- `published/reports/weapon-corpus-audit.json` — ~23 MB

The architecture handoff required bounded practical diff/report output; a nearly 1 GB `snapshot-data-diff.json` violates that intent.

### Required bundle model

Separate output into two concepts:

```text
LOCAL INTELLIGENCE
  persistent/heavy; stays on the user's PC
  - architecture SQLite/DuckDB databases
  - exhaustive schema/profile indexes
  - full forensic traces
  - full detailed diffs
  - raw/large research artifacts

SHAREABLE INTELLIGENCE BUNDLE
  compact, deterministic, sufficient for AI/review
  - compiled summary
  - snapshot identity/fingerprints without unsafe machine-path leakage
  - registry/client_data summary
  - consumer-index summary
  - reference-graph summary
  - semantic registry summary
  - bounded snapshot-diff summary
  - coverage dashboard
  - self-diagnostics
  - launch-gap / blocker summaries
  - lean site payloads/evidence needed for review
  - targeted unresolved evidence only
```

Implement an explicit allowlist or artifact classification policy. Do **not** return to `glob("*.json")` over all reports/research as the normal shareable export policy.

Keep persistent architecture databases local by default.

Add size accounting to bundle creation and tests protecting against accidental inclusion of known heavy/local-only classes.

If useful, provide an optional explicit **full forensic export** mode separate from the normal shareable Intelligence bundle; do not make full forensic export the default.

## Objective C — Bound `snapshot-data-diff.json`

The current snapshot diff report is far too large.

Preserve detailed diff information locally in a database or separate deep artifact if valuable, but make the normal JSON report bounded.

The normal report should prioritize:

- table added/removed/changed/unchanged counts
- changed table paths
- bounded per-table record counts
- bounded representative changed record IDs/fields
- semantic definitions affected
- website records potentially affected
- truncation metadata / pointers to local deep detail

Do not dump hundreds of megabytes of record-level changes into the normal report.

## Objective D — Validate and finish the new Miner architecture

The architecture handoff phases were implemented in a rapid sequence after `.61`:

- persistent table registry + `client_data` census
- static PYC consumer index
- typed reference graph
- semantic field registry
- promotion engine
- family registry
- snapshot diff/dependency work
- site delta
- self diagnostics
- coverage dashboard
- unified Miner pipeline-console redesign

Do a real local validation pass now.

For each subsystem, inspect:

- implementation quality
- whether compiler integration is real
- whether outputs are populated meaningfully
- cache/invalidation correctness
- whether tests cover behavior rather than mere imports
- whether current Weapons publication actually consumes the generic systems
- whether old bespoke scans can now be replaced or narrowed safely

Do not rewrite working systems merely for elegance. Fix concrete gaps and preserve launch velocity.

---

# Current Weapons state to preserve

Canonical corpus:

- 120 weapons total
- 95 ranged
- 25 melee
- Tier I · 1★ default presentation
- installed-game/Miner evidence authoritative

Current known strong lanes:

- rarity is authoritative from installed normalized quality fields
- Tier-I ranged gun-base semantics cover all 95 ranged weapons
- firing-mode semantics were resolved from installed static `ShootMode` structure
- exact multi-projectile/pellet counts use typed bullet-pattern evidence from `client_data/bullet_pattern_data.json`
- Weapon Description producer path is `prototype_id -> weapon_prototype_data.prototype_desc -> English translation`
- 119/120 description translations were previously resolved consistently; one translation conflict remains quarantined
- browser-facing lean site payload is intentionally separate from rich evidence/detail data
- family inheritance is typed/domain-limited; local exact evidence wins

Verify the **current local outputs** rather than assuming every older count still matches the latest source.

## Fixed-skill lane is closed unless evidence changes

Do not reopen broad fixed-skill forensics merely because 14 public weapon records remain unresolved.

Latest local research still shows:

- 14 weapon records with unresolved fixed-skill ownership
- 11 unique codes: `WS1001`, `WS1101`, `WS1301`, `WS1402`, `WS14503`, `WS1501`, `WS15203`, `WS15304`, `WS15502`, `WS1601`, `WS2001`
- exact blueprint fixed-skill references exist
- static routing/consumer architecture exists
- no alternate exact current passive-skill owner has been proven

The all-weapons Guided Schema Trace still reports:

- 120 requested / 120 traced
- 106 clean
- 14 with unresolved stops
- 0 failures
- 2,014 typed branches
- 11 unique unresolved skill codes

Latest fixed-skill forensics still finds all 11 exact code values in `gun_blueprint_attr_data` and expected consumers such as `BluePrintHelper`, `GunCoreHelper`, `CompSkillMgr`, and client damage-simulation code. Those are routing/consumer evidence, not alternate owners.

Safe current classification remains:

> Current installed evidence does not resolve this fixed-skill reference through any known current passive-skill owner path.

Never translate that into “no mechanic,” “broken weapon,” or an invented community mechanic.

---

# High-priority local research lanes after infrastructure validation

Once the exporter/architecture issues are under control, use the local indexes to close launch-relevant fields rather than returning to broad brute-force scans.

Priority order:

1. **Cradle compatibility/applicability**
   - use the persistent consumer index and exact Cradle tables/consumers
   - previous strong consumers include `UIEquipmentData.pyc` with `cradle_override_entry`, `gun_type`, `key_word_no`, `key_word_lst`, and `impEquip.pyc` with `cradle_override`, `weapon_type`
   - prove typed category/keyword/weapon relationships before publication

2. **Projectile semantics completeness**
   - exact pattern-count lane is `gun -> bullet_pattern_no -> client_data/bullet_pattern_data -> bullet_num`
   - do not assume patternless weapons imply projectile count 1 until installed default/fallback behavior is proven

3. **Attachment/calibration/selectable-ammo compatibility**
   - exploit table registry + client_data census + typed reference graph
   - distinguish UI preview/display relationships from true compatibility

4. **Description conflict / remaining publication reconciliation**
   - preserve the one known conflicting translation until exact language/precedence evidence resolves it

5. **Melee player-facing semantics**
   - determine what is genuinely not-applicable vs unresolved rather than forcing firearm-style fields onto melee

---

# Client data is now first-class

The latest local census reports more than ten thousand `client_data` paths/instances, far beyond the few dozen tables previously surfaced manually.

Do not treat `client_data` as merely decorative UI data.

Use the table registry and consumer index to classify it and find exact client-facing semantics, including possible:

- player-facing stat display
- weapon preview parameters
- crosshair relationships
- attachment preview/compatibility clues
- bullet patterns
- Cradle presentation/selectors
- equipment panel attribute display
- crafting UI grouping
- melee UI behavior
- effect/keyword presentation

Heuristic domain tags are discovery hints only, not semantic proof.

---

# Unified Miner redesign — user usability issue

Current `main` redesigns the GUI into a pipeline console with roughly:

```text
Run Pipeline
Explore Data
Publish & Verify
```

and stages:

```text
MINE -> INDEX -> RESOLVE -> COMPILE -> VERIFY
```

The user reported that the redesign is confusing to operate.

Preserve the richer console, but improve affordances for normal use.

At minimum make the UI explain the difference between:

- **Run Complete Pipeline** — game updated / fresh snapshot required
- **Run Changed Stages** — same snapshot, Miner/analyzer code or dependent stages changed
- **Compile Data Intelligence** — research/review artifact generation from an existing completed snapshot

A compact Quick Start panel/help text is preferred over reverting to the old UI.

Do not make the user learn internal architecture terminology to perform the common workflow.

---

# Evidence and safety doctrine

These remain hard requirements:

- Never execute game bytecode or import game modules.
- Static PYC inspection only.
- Never attach to the game process.
- No memory reading, hooks, injection, packet interception, decryption/DRM bypass, or anti-cheat interaction.
- No fuzzy IDs.
- No substring ownership promotion.
- No bare-number identity promotion.
- No global scalar equality joins.
- PYC/token hits are locator/consumer evidence, not semantic proof.
- Typed owner/producer/consumer relationship is required for semantic publication.
- Missing evidence never becomes a negative gameplay claim.
- External/community sites are research-question/UX references only.
- Do not publish local machine paths, raw snapshots, full NeoX exports, local architecture DBs, or research-only forensic corpora.
- Do not touch pre-existing `tools/miner.zip`.
- GitHub `main` is canonical source; release ZIPs are artifacts.
- Work directly on `main` unless the user explicitly says otherwise.
- Use small coherent commits and keep tests green.

---

# Release discipline

Do **not** immediately stamp all post-.61 source as `.62` merely because it exists on `main`.

First:

1. inspect local post-.61 outputs
2. fix shareable Intelligence bundling
3. bound the giant snapshot diff
4. validate new architecture modules and tests
5. ensure the redesigned UI has a clear normal-user path
6. run full source tests
7. run packaged Windows self-test through the existing release gate

Then release at a meaningful tested boundary.

Updater manifest remains the last publication step after exact asset verification.

---

# Website deadline

Dead Signal's target remains **August 25, 2026**.

Architecture work must increase launch velocity rather than become a research project of its own.

Prioritize work that closes player-facing database gaps, improves deterministic rebuilds, or makes the user's workflow safer/easier.

---

# First actions for the local Codex session

Do these without waiting for repeated approval unless an actual destructive/ambiguous decision appears:

1. Read the four files listed at the top of this handoff.
2. Inspect the current local repository and `git status`/recent commits.
3. Resolve the active Miner output from local metadata.
4. Inspect `last-run.json` and the newest compiled Intelligence summary.
5. Measure the Intelligence directory/bundle members and identify exact size contributors.
6. Inspect `dead_signal_intelligence_compiler._bundle_members()` and replace broad bundling with explicit artifact classification/allowlisting.
7. Bound `snapshot-data-diff.json`; retain deep detail locally if useful.
8. Add regression tests for bundle membership and size-policy behavior.
9. Inspect each new architecture subsystem against its actual local DB/report output.
10. Run the full Miner source tests.
11. Commit coherent fixes on `main`.
12. Update this handoff or create a successor with exact findings, counts, tests, and remaining launch blockers.

After that, continue into the highest-value unresolved player-facing lane using the new local indexes—most likely Cradle applicability unless the local validation reveals a more urgent publication blocker.

The guiding principle is now:

> **Use the local persistent architecture to answer questions directly. Stop exporting or rescanning enormous corpora when the proof is already indexed on the user's machine.**
