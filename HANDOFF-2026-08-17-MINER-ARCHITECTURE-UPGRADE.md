# Dead Signal — Miner Architecture Upgrade Handoff

> **Canonical repo:** `raiinman/dead-signal`
> **Branch:** `main`
> **For:** Codex implementation session
> **Date:** 2026-08-17 America/Phoenix / 2026-08-18 UTC
> **Baseline:** Miner **v1.5.14.61** stable
> **Release commit:** `0b0b999be3ede3a3d634e543a3735a1ae79418e7`
> **Updater publication:** `29a9b0e48bdd9a1d2c9639f5c12a8aad52027646`

## Read first

Before changing code, read these files completely:

1. `AI-CONTINUITY.md`
2. `PROJECT-RULES.md`
3. this handoff

`AI-CONTINUITY.md` is older than the current Miner release and still describes an earlier `.47` state. Preserve its rules and evidence doctrine, but treat this handoff and current `main` as the fresher implementation state for the Miner architecture work below.

Do **not** restart or redesign the project from scratch. Extend the existing Miner, Data Intelligence compiler, source tests, release workflow, and website publication pipeline.

---

# Objective

Transform the Dead Signal Miner from an excellent extractor + collection of targeted forensic analyzers into a persistent **reverse-engineered game-data compiler** that learns Once Human's data architecture once, remembers proven relationships, detects what changed after patches, and regenerates Dead Signal from that knowledge.

Target architecture:

```text
EXTRACT
  ↓
TABLE REGISTRY
  ↓
REFERENCE GRAPH
  ↓
CONSUMER INDEX
  ↓
SEMANTIC REGISTRY
  ↓
PUBLICATION ENGINE
  ↓
WEBSITE DELTA
```

The goal is to stop repeatedly rediscovering the same table shapes, joins, PYC consumers, and semantic mappings every time a new field or game patch is investigated.

The new infrastructure must be useful beyond Weapons. Weapons are the proving ground; the architecture must be category-agnostic enough to later support Armor, Mods, Attachments, Cradles, Deviations, items, etc.

---

# Current baseline that must remain intact

Miner `v1.5.14.61` is stable. Do not regress its behavior.

Relevant current source includes, at minimum:

- `tools/miner/src/dead_signal_intelligence_compiler.py`
- `tools/miner/src/dead_signal_weapon_corpus_audit.py`
- `tools/miner/src/dead_signal_weapon_site_readiness.py`
- `tools/miner/src/dead_signal_weapon_site_projection.py`
- `tools/miner/src/dead_signal_weapon_site_publish.py`
- `tools/miner/src/dead_signal_weapon_launch_gap_trace.py`
- `tools/miner/src/dead_signal_research_suite.py`
- `tools/miner/src/dead_signal_weapon_prototype_projection.py`
- `tools/miner/src/dead_signal_common_data_registry_audit.py`
- existing source tests under `tools/miner/tests/`

Current Weapons publication path is approximately:

```text
installed game / completed Miner snapshot
→ exact corpus evidence
→ website readiness
→ semantic promotion
→ family inheritance
→ `published/site/weapons-v2.json` forensic projection
→ `published/site/weapons.json` lean browser feed
→ `published/site/weapon-evidence.json` detail/provenance sidecar
```

Important current behavior from `.61`:

- 120 total weapons = 95 ranged / 25 melee.
- Installed-game data mined by Dead Signal is authoritative.
- Rarity is promoted from installed `quality_code + quality`.
- 119/120 Weapon Descriptions are promoted through the exact prototype description chain; one translation conflict remains unresolved.
- Tier-I `gun_base_params_data` semantic promotion covers all 95 ranged weapons.
- Raw firing-mode codes are resolved through installed static `ShootMode` structure; publication uses installed enum semantics, not community labels.
- Projectile/pellet counts use exact bullet-pattern evidence. The normalized pattern table is `client_data/bullet_pattern_data.json`.
- The lean browser Weapons payload is intentionally separated from the evidence/detail sidecar.
- Family inheritance is typed and domain-limited. Variant-local evidence overrides family-shared evidence.
- Missing evidence is never converted into a negative gameplay claim.

Do not weaken any of these rules while generalizing the architecture.

---

# Non-negotiable evidence / safety rules

These must remain hard constraints in the implementation:

- Never execute game bytecode.
- Static PYC inspection may use raw bytes, marshal-compatible code objects, symbol/name/constant inspection, and tolerant disassembly only.
- Never import the game's Python modules.
- Never attach to the game process.
- No process memory reads, debugging, hooks, injection, packet interception, DRM/decryption bypass, or anti-cheat interaction.
- No fuzzy IDs.
- No substring identity promotion.
- No bare-number identity promotion.
- No global scalar equality joins.
- No sibling-node leakage.
- A token hit or PYC symbol is a locator/consumer lead, not semantic proof.
- A typed owner/producer/consumer relationship is required for semantic publication.
- Family/shared relationships are valid only in their proven domain.
- Variant-local exact evidence overrides inherited family evidence for the same field.
- Missing recipe evidence does not mean non-craftable.
- Missing passive owner does not mean no mechanic.
- External/community sites may define research questions or UX ideas only; never import their values into authoritative Miner output.
- Do not publish raw snapshots, full NeoX exports, local machine paths, reference-tracer databases, research-only bundles, or other internal forensic artifacts to the website.
- Do not touch pre-existing `tools/miner.zip`.

---

# What to build

## 1. Permanent Table Registry

Create a persistent registry that catalogs every extracted structured table in every completed snapshot.

Suggested module:

`tools/miner/src/dead_signal_table_registry.py`

Suggested durable output/database:

- `catalogs/dead-signal-table-registry.sqlite` or DuckDB if there is a strong project-consistent reason
- lightweight JSON summary under `published/reports/` for Intelligence bundles

The registry must capture at least:

### Table identity

- layer: base/current
- normalized relative path
- namespace/root classification, e.g. `game_common`, `client_data`, other
- file size
- SHA-256 or dependency fingerprint
- record count
- extraction/parser source when known

### Structural schema

For each table:

- observed field names
- frequency of each field
- observed value types
- nullable/missing rates where inexpensive
- nested object/list shape summaries
- candidate record-key shape
- translation-handle-looking fields
- description/name/display-looking fields
- reference-looking fields such as `*_id`, `*_no`, `*_code`, `*_list`, `*_lst`, `*_map`, etc.
- scalar/list/dict reference candidates kept distinct

### Domain hints

Classify tables heuristically, but clearly mark classification as a hint rather than proof:

- Weapons
- Weapon UI
- Weapon Preview
- Ballistics
- Crosshair
- Attachments
- Equipment
- Armor
- Melee
- Crafting
- Calibration
- Cradle
- Effects / Keywords
- Deviations
- Seasons
- Maps
- Items
- Translation / presentation
- unknown

Do not hardcode the whole system around these names. Allow multiple domain tags.

### Required behavior

- deterministic output
- idempotent reruns
- per-table fingerprinting
- changed tables re-profile; unchanged tables reuse cached registry rows
- Base/Current coexist instead of silently overwriting one another
- expose API helpers that other analyzers can query without rescanning the filesystem

### First-class `client_data` census

`client_data/` must be explicitly inventoried as a first-class subsystem.

We already know the corpus contains useful tables such as:

- `client_data/bullet_pattern_data.json`
- `client_data/gun_preview_ui_param_data.json`
- `client_data/gun_preview_ui_global_param_data.json`
- `client_data/gun_blueprint_preview_accessory_data.json`
- `client_data/gun_accessory_preview_model_data.json`
- `client_data/gun_crosshair_data.json`
- `client_data/crosshair_data.json`
- `client_data/equipment_panel_attr_show_data.json`
- `client_data/equip_type_data.json`
- `client_data/equip_suit_data.json`
- `client_data/equip_craft_tab_data.json`
- `client_data/equip_craft_lv_display_data.json`
- `client_data/equip_fpp_weapon_config_data.json`
- `client_data/equip_fpp_render_config_data.json`
- `client_data/armor_preview_ui_param_data.json`
- `client_data/melee_preview_ui_param_data.json`
- `client_data/cradle_mesh_map.json`
- `client_data/cradle_override_style_data.json`
- `client_data/cradle_tip_effect_data.json`
- `client_data/effect_keyword_item_data.json`
- `client_data/effect_keyword_tab_config_data.json`
- `client_data/deviation_skill_pool_name.json`
- `client_data/big_map_item_data.json`
- `client_data/small_map_item_data.json`
- `client_data/season_description_data.json`
- `client_data/season_feature_description_data.json`

Do not assume this list is complete. Perform a full census from the actual snapshot.

Deliver a report such as:

`published/reports/client-data-census.json`

with categories, counts, structural highlights, and top reference-bearing tables.

---

## 2. Persistent Typed Reference Graph

Create a durable reference graph that stores candidate and proven typed relationships between records/tables.

Suggested module:

`tools/miner/src/dead_signal_reference_graph.py`

This is **not** a global fuzzy graph traversal engine. It is a typed relationship index.

Each edge should carry fields such as:

```text
source_table
source_record_id
source_field
source_value
source_layer

target_table
target_record_id
relationship_kind
confidence/proof_state
scope
producer/consumer/owner role
provenance
first_seen_snapshot
last_seen_snapshot
```

Proof states should distinguish at least:

- structural-candidate
- exact-record-reference
- typed-relationship-proven
- consumer-confirmed
- semantic-proven
- rejected

Do not conflate `exact value exists somewhere` with `this field owns/references that target`.

Support list/dict reference edges without flattening away the parent field path.

### Seed known exact relationships

The architecture must be able to represent current proven chains such as:

```text
weapon blueprint
→ item
→ prototype
→ Tier-I gun
```

```text
prototype_id
→ weapon_prototype_data[prototype_id].prototype_desc
→ English translation
```

```text
gun / ranged_stats bullet_pattern_id
→ client_data/bullet_pattern_data[pattern]
→ bullet_num
```

```text
fixed_skill_code
→ passive_skill_data owner (when exact owner exists)
→ buff_id
→ keyword_buff_id
```

```text
item
→ item_to_gun_mapping_data
→ gun accessory slot parameters
→ selectable ammo / accessory configuration
```

Do not hardcode Weapons-only names into the graph schema.

---

## 3. Static PYC Consumer Index

The Miner currently rescans large PYC trees for targeted research. Build a persistent static index so known consumers can be queried instantly on subsequent passes.

Suggested module:

`tools/miner/src/dead_signal_consumer_index.py`

Suggested durable output:

`catalogs/dead-signal-consumer-index.sqlite`

Index each retained PYC by fingerprint and capture safe static metadata:

- relative path
- layer/source root
- file SHA-256
- code object qualified names where marshal-compatible
- `co_names`
- safe string constants
- safe numeric constants where useful
- child code object relationships
- raw token signatures for files that cannot be reliably disassembled
- table symbols / field names / method names
- code-scope co-occurrence, not just whole-file co-occurrence

Important: Once Human bytecode may not match the local Python opcode table. The index must degrade gracefully.

If marshal succeeds but `dis` is unreliable, preserve safe code-object metadata and raw bytes/token offsets instead of failing the run.

Never execute bytecode.

### Query API

Other analyzers should be able to ask questions such as:

```text
find consumers containing `cradle_override_entry`
AND `gun_type`
within the same code object
```

or:

```text
find code scopes containing `prototype_desc`
```

or:

```text
find code scopes referencing `default_shoot_mode` / `ShootMode`
```

without rescanning ~94k PYC files.

### Known Cradle leads to preserve / validate

Current research has already surfaced strong leads including:

- `UIEquipmentData.pyc` with `cradle_override_entry`, `gun_type`, `key_word_no`, `key_word_lst`
- `impEquip.pyc` with `cradle_override`, `weapon_type`

The new consumer index should make this type of narrowing routine.

---

## 4. Semantic Field Registry

Create a declarative registry of fields whose player-facing semantics have been proven.

Suggested module/data:

- `tools/miner/src/dead_signal_semantic_registry.py`
- checked-in declarative definitions under something like `tools/miner/data/semantic_registry.json` or Python structures if testing/typing strongly favors code

Each semantic definition should support:

```text
semantic_name
category/domain
owner_type
source_table
source_field
relationship prerequisite
scope: variant-local / family-shared / etc.
precedence
raw/display distinction
normalization / rounding rule if proven
required proof level
publication state
version / first proven snapshot
notes
```

Examples already suitable for representation include:

```text
fire_rate_display_rpm
→ game_common/data/gun_base_params_data.json.weapon_rpm_affix_value
```

```text
reload_score
→ gun_base_params_data.reload_loop_affix_value
```

```text
reload_time_seconds
→ gun_base_params_data.reload_loop_time
```

```text
ads_time
→ gun_base_params_data.ads_time
```

```text
bullet_speed
→ gun_base_params_data.bullet_speed
```

```text
Weapon Description
→ prototype_id
→ raw weapon_prototype_data.prototype_desc
→ exact English translation
```

```text
projectile_count
→ bullet pattern
→ client_data/bullet_pattern_data.bullet_num
```

```text
firing_mode
→ gun_base_params_data.default_shoot_mode
→ installed ShootMode static enum mapping
```

Raw/internal values must remain separate from display/player-facing values where those are different.

The semantic registry must **not** allow a field to become publishable merely because a similarly named field exists.

---

## 5. Generic Evidence Promotion Engine

Replace one-off promotion logic over time with a declarative evaluator that asks whether a semantic definition's evidence requirements are met.

Suggested module:

`tools/miner/src/dead_signal_promotion_engine.py`

Conceptual definition:

```yaml
field: firing_mode
owner: tier_one_gun
source: game_common/data/gun_base_params_data.json.default_shoot_mode
semantic_map: ShootMode
required_evidence:
  - exact-owner-record
  - static-enum
scope: variant-local
publication: resolved-installed-game
```

The exact implementation format is Codex's choice, but it must be testable and auditable.

The promotion engine should return a structured result, not just a value:

```text
value
raw_value
state
scope
precedence
provenance
semantic_definition_version
reasons_not_promoted[]
```

### Migration policy

Do **not** rewrite every existing analyzer at once.

Start by wrapping/migrating the current Weapons site projection fields while preserving byte-for-byte or semantically equivalent browser output.

Migrate incrementally behind tests.

---

## 6. Family / Inheritance Registry

Generalize the existing Weapons family rule into reusable infrastructure.

Current policy that must remain true:

```text
variant-local precedence 2
family-shared precedence 1
```

Typed family relationships can establish shared mechanics within their actual domain; they do not establish variant-local ownership.

Represent relationships such as:

- shared prototype family
- shared bullet-pattern / ballistic family
- future item/skill/equipment family types when proven

Each family relationship must declare allowed inherited semantic groups.

Example:

```text
bullet-pattern family
allowed inheritance:
- projectiles
- bullet_speed
- falloff

not allowed:
- ADS
- firing mode
- reload
- acquisition
- special skill
```

Local evidence always overrides shared evidence for the same semantic field.

Add regression tests specifically protecting against family leakage.

---

## 7. Incremental Intelligence / Dependency Cache

Extend the existing research cache into a general incremental dependency system.

Goal: do not rescan or re-profile unchanged inputs.

At minimum:

- table registry entries keyed by file/content fingerprint
- PYC consumer index entries keyed by file/content fingerprint
- semantic analyzers declare dependencies
- unchanged dependency sets reuse prior result
- changed tables invalidate only dependent relationships/semantic projections
- changed PYCs invalidate only affected consumer-index rows and semantic proofs

The full Intelligence compiler should report cache statistics:

```text
files considered
files changed
files reused
tables re-profiled
tables reused
PYCs re-indexed
PYCs reused
semantic definitions reevaluated
```

Do not optimize by silently skipping required validation. Cache identity must be content/fingerprint driven.

---

## 8. Automatic Base ↔ Current Patch Diff

Create a structured diff stage for each completed harvest.

Suggested module:

`tools/miner/src/dead_signal_snapshot_diff.py`

Output:

`published/reports/snapshot-data-diff.json`

It should report at least:

- tables added/removed/changed/unchanged
- record IDs added/removed/changed for changed structured tables
- fields added/removed/changed within changed records, bounded to practical report sizes
- PYC files added/removed/changed
- known semantic definitions affected by those changes
- website records potentially affected

The purpose is to support a future patch workflow like:

```text
Once Human patch
→ harvest
→ diff
→ revalidate only affected relationships
→ regenerate site delta
```

Do not imply a removed table/record means removed player-facing content unless the typed player-facing chain proves that consequence.

---

## 9. Website Delta Output

Add a stable website change feed generated from the previous published site projection vs the new projection.

Suggested output:

`published/site/site-delta.json`

At minimum for Weapons:

- added records
- removed records (with conservative state; do not overclaim deletion semantics)
- changed name/rarity/category
- changed Tier damage/progression
- changed promoted stats
- changed firing mode
- changed projectile count
- changed description
- changed Special Skill/evidence state
- changed acquisition/recipe availability
- changed compatibility state
- changed image reference

Include before/after hashes and semantic field names; avoid dumping entire forensic records into the lean delta.

Eventually this should be generic across categories.

---

## 10. Self-Diagnostics / Consistency Guard

Build a diagnostics layer that catches contradictions between known/published relationships and new analyzer output.

The `.60` bullet-pattern path mistake is the motivating example:

- a weapon already had a proven `bullet_pattern_id = Pat10230011`
- previous exact evidence already knew `client_data/bullet_pattern_data.json[Pat10230011].bullet_num = 5`
- a new tracer used the wrong normalized table path and returned zero pattern records

The Miner should detect this class of inconsistency automatically.

Suggested diagnostics:

- known reference target exists in registry but analyzer resolved zero table records
- semantic registry says a field is universally resolvable for a cohort but output coverage unexpectedly drops
- current publication count drops sharply without corresponding source diff
- family-shared evidence appears in a disallowed semantic group
- variant-local owner expected but only family-shared evidence found
- table locator changed between snapshots
- consumer symbol disappeared while its source field remains active
- duplicate semantic definitions conflict
- unresolved state replaces previously resolved state without changed dependency evidence

Output:

`published/reports/dead-signal-self-diagnostics.json`

Use severity levels such as INFO / WARNING / BLOCKER.

BLOCKER diagnostics should stop website publication for affected fields, not necessarily fail the whole Miner harvest.

---

## 11. Launch / Coverage Dashboard

Expose useful post-promotion coverage in the Miner UI/Research Console.

The user should see field-level counts, not only broad percentages.

Example:

```text
Weapons                 120/120
Rarity                   120/120
Descriptions             119/120
Tier-I ranged gun stats   95/95
Firing mode               95/95
Projectile semantics       x/95
Cradle compatibility       x/120
Special Skill             76 resolved / 44 evidence-state
```

The dashboard should separate:

- published/resolved
- exact evidence located but semantic proof pending
- partial
- unresolved evidence state
- unresolved
- not applicable

Where practical, clicking/opening a blocker should surface the relevant report/evidence path rather than requiring the user to search the output folder manually.

Do not invent a web server or new runtime dependency just for the dashboard; integrate with the existing Miner UI/Research Console architecture.

---

# Client Data Census — immediate high-priority proving task

Make the `client_data` census one of the first delivered pieces because it may directly accelerate the website deadline.

Questions the census should answer automatically:

1. How many `client_data` structured tables exist in Base and Current?
2. Which changed between Base and Current?
3. Which contain weapon/gun/item/blueprint/prototype identifiers?
4. Which contain display/stat/preview/crosshair/accessory/compatibility fields?
5. Which contain translation handles?
6. Which are referenced by static PYC consumers?
7. Which already join to the 120 canonical Weapons identities?
8. Which appear useful for current unresolved lanes:
   - Cradle compatibility
   - attachment compatibility
   - calibration compatibility
   - equipment panel/player-facing stat display
   - preview/accessory relationships
   - melee UI semantics

High-value tables to explicitly inspect include:

- `client_data/equipment_panel_attr_show_data.json`
- `client_data/gun_preview_ui_param_data.json`
- `client_data/gun_blueprint_preview_accessory_data.json`
- `client_data/gun_accessory_preview_model_data.json`
- `client_data/bullet_pattern_data.json`
- `client_data/cradle_override_style_data.json`

But the census must remain comprehensive rather than limited to these examples.

---

# Integration plan / recommended phases

Do not attempt this as one giant rewrite. Land it in small green commits on `main`.

## Phase 0 — Baseline guard

Before infrastructure changes:

- run existing Miner source tests
- add/confirm a regression fixture for the current Weapons publication path
- snapshot expected key counts/states from the current test fixtures
- confirm `.61` behavior is represented by tests where possible

Do not use a local user's extracted snapshot in committed tests.

## Phase 1 — Table Registry + Client Data Census

Deliver:

- persistent table registry
- incremental hashing
- `client_data` first-class classification
- report + tests
- compiler integration

This phase should already reduce repeated filesystem profiling.

## Phase 2 — Consumer Index

Deliver:

- persistent PYC index
- safe tolerant indexing
- code-scope query API
- cache reuse
- regression fixtures using synthetic/marshal-compatible test PYCs

Do not depend on executing or importing game modules.

## Phase 3 — Reference Graph

Deliver:

- typed edge schema
- candidate vs proven distinction
- graph query helpers
- seed current known Weapons relationships through existing evidence producers

Do not auto-promote graph candidates.

## Phase 4 — Semantic Registry + Promotion Engine

Deliver:

- declarative semantic definitions
- structured promotion result
- migrate current Weapons fields gradually
- preserve current browser output
- family precedence integrated

## Phase 5 — Snapshot Diff + Dependency Invalidation

Deliver:

- Base/Current structured diff
- changed dependency calculation
- cache invalidation wiring
- report

## Phase 6 — Website Delta + Self-Diagnostics

Deliver:

- `site-delta.json`
- consistency diagnostics
- publication blocking at field level for BLOCKER contradictions

## Phase 7 — Miner UI Coverage Dashboard

Deliver:

- compact launch/coverage panel
- field/state counts
- links/actions into evidence reports where existing UI allows

---

# Data/storage design guidance

Prefer SQLite for durable indexes unless an existing project component strongly justifies DuckDB for a particular analytical workload.

Do not store giant raw JSON blobs when normalized rows and hashes will do.

Recommended separation:

```text
catalogs/
  dead-signal-table-registry.sqlite
  dead-signal-consumer-index.sqlite
  dead-signal-reference-graph.sqlite   # or combined architecture DB if cleanly designed

published/reports/
  client-data-census.json
  table-registry-summary.json
  consumer-index-summary.json
  reference-graph-summary.json
  snapshot-data-diff.json
  dead-signal-self-diagnostics.json

published/site/
  weapons.json
  weapon-evidence.json
  weapons-v2.json
  site-delta.json
```

A single architecture SQLite database is acceptable if its schema stays clean and responsibilities are separated by tables. Do not force multiple databases merely to match these suggested filenames.

All persistent DB writes should be atomic/transactional where practical.

---

# Performance expectations

The infrastructure should make repeated Intelligence compiles materially faster on unchanged snapshots.

Measure and report timings.

Do not optimize by weakening evidence checks.

Expected direction:

```text
first run:
  expensive census/index build

second run, unchanged snapshot:
  near-zero table reprofile
  near-zero PYC reindex
  semantic/publication stages reuse proven architecture

patch run:
  only changed files + dependent semantic paths revalidated
```

Avoid repeated `rglob` over the entire tree in independent analyzers once the table/consumer indexes exist.

During migration, old analyzers may remain as fallback until equivalent indexed queries are tested.

---

# Testing requirements

Every phase needs source tests before release.

Add deterministic fixtures for:

- table schema profiling
- table fingerprint reuse / invalidation
- Base vs Current layer precedence
- list/dict reference preservation
- typed reference edges
- rejected fuzzy/scalar collisions
- consumer code-scope co-occurrence
- tolerant PYC fallback when disassembly fails
- semantic definition proof requirements
- variant-local overrides family-shared
- disallowed family leakage rejection
- publication state transitions
- unresolved stays unresolved when proof is missing
- snapshot diff added/removed/changed records
- website delta generation
- self-diagnostic blocker on contradictory table locator
- no regression of lean browser payload boundaries

Keep test fixtures synthetic and small.

Run the existing full Miner source suite after each meaningful phase.

---

# Release / Git discipline

- Work directly on `main` unless the user explicitly changes that instruction.
- Small coherent commits.
- Do not bundle unrelated website/design work into Miner architecture commits.
- Keep source tests green.
- Use the existing Windows packaging and packaged self-test release gate.
- Updater manifest must remain the last publication step after asset verification.
- GitHub source is canonical; Windows release ZIP is an artifact.
- Do not touch `tools/miner.zip`.

Do **not** bump/release the Miner after every tiny internal commit. Release at meaningful phase boundaries when the new infrastructure is usable and tested.

---

# Website deadline / prioritization

Dead Signal is aiming to finish the website by **August 25, 2026**.

Therefore, architecture work must improve launch velocity rather than become an open-ended rewrite.

Priority order:

1. Table Registry + full `client_data` census
2. Consumer Index
3. typed Reference Graph
4. Semantic Registry / generic promotion around current Weapons pipeline
5. snapshot diff / incremental invalidation
6. self-diagnostics
7. website delta
8. UI dashboard polish

If a large abstraction threatens the deadline, deliver the smallest reusable infrastructure that materially removes repeated research work and keep moving.

Weapons/website blockers still take precedence over elegance.

---

# Definition of success

This handoff is complete when the Miner can do the following without bespoke full-tree rescans for every question:

1. Given a table/field name, instantly describe where it exists, its schema, layer, and changes.
2. Given a record identifier, enumerate exact typed reference candidates and their proof state.
3. Given a field/token such as `prototype_desc`, `cradle_override_entry`, or `default_shoot_mode`, return indexed PYC consumer scopes.
4. Given a semantic field such as `reload_score`, explain exactly which source field/owner/relationship proves it and whether it is publishable.
5. Reuse that proof across all applicable records.
6. Detect when a new patch changes any dependency in that proof chain.
7. Revalidate only affected semantics.
8. Generate updated website payloads plus a concise `site-delta.json`.
9. Block contradictory/unproven field publication through self-diagnostics.
10. Show the user a clear coverage/blocker dashboard.

The desired end state is:

> **Dead Signal Miner understands the data architecture it has already proven instead of rediscovering it every session.**

---

# Immediate first action for Codex

Start with **Phase 0 + Phase 1** only.

1. Read current `main` source and existing tests.
2. Run the test suite before changing anything.
3. Design the table-registry schema around the actual completed-snapshot directory structure already used by the Miner.
4. Implement persistent per-table fingerprinting and structural profiling.
5. Add the complete `client_data` census report.
6. Wire the registry/census into `COMPILE DATA INTELLIGENCE` without removing existing analyzers.
7. Add tests for caching, Base/Current precedence, schema profiling, and client-data classification.
8. Run full source tests.
9. Commit cleanly on `main`.
10. Report exact files changed, tests run, timings, registry counts, client_data table count, and any newly surfaced high-value tables/relationships.

Do not ask for approval between those implementation steps unless an actual destructive/ambiguous project decision is encountered. Continue until Phase 1 is green and committed.
