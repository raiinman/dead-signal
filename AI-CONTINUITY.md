# Dead Signal — AI Continuity / Handoff

> **Purpose:** Canonical current-state handoff for ChatGPT/Codex sessions working on Dead Signal. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Last updated: **2026-08-12 (Miner-backed weapon corpus migration)**

### 2026-08-12 Weapons catalogue vertical slice — implemented locally by Codex

Codex resumed from commit `ab71438cf15d0c023879417bcf103f624c9d13d3` and implemented the approved first database catalogue slice on `main` in the local working tree:

- `database/weapons/` now provides a static, responsive catalogue over the 120-record installed-game Miner snapshot;
- search, weapon-type and rarity filters, name/rarity/Base Attack/Fire Rate/Magazine sorting, and grid/list views are implemented;
- two-record raw indexed comparison is implemented and explicitly excludes Tier, Blueprint Stars, Calibration, attachments, and derived DPS;
- all weapon cards expose artwork, important indexed stats, provenance, an inspect route, comparison selection, and safe Build Planner handoff;
- `database/weapons/sks-pathfinder/` is the representative canonical detail route, with indexed stats, weapon effect, Tier I–V progression, Blueprint Star multipliers, source/coverage, and explicit limits on unproven relationships;
- `database/weapons/detail/?weapon=<id>` supplies the reusable detail architecture for the remaining current records;
- the root Weapons category now links to `/database/weapons/`;
- `preview/build-lab/catalogue-handoff.js` opens the appropriate planner weapon picker, prefiltered to the requested catalogue record, without overwriting an existing build;
- `.cpanel.yml` remains copy-only and now copies the prepared catalogue/detail files plus the planner handoff script.

Verification completed against a local deployment mirror reconstructed from the existing prepared planner/player-corpus bundles:

- JavaScript syntax checks passed;
- all 11 Miner unit tests passed;
- `git diff --check` passed;
- real-browser desktop catalogue rendering showed 120/120 records;
- search isolated SKS — Pathfinder correctly;
- representative detail progression rendered 5 Tier values and 6 Blueprint Star multipliers;
- planner handoff opened the primary picker prefiltered to SKS — Pathfinder;
- 390 × 844 mobile verification produced a one-column catalogue with no horizontal overflow.

These changes are not a live deployment until they are committed/pushed to public `main` and cPanel runs **Update from Remote** followed by **Deploy HEAD Commit**.

## 1. Project identity

- Project: **Dead Signal Ultimate Planner**
- Game: **Once Human**
- Repository: `raiinman/dead-signal`
- Canonical branch: **`main` only** unless the user explicitly requests otherwise.
- Live planner: `https://deadsignaldb.com/build-planner/`
- Root site: `https://deadsignaldb.com/`
- Hosting: Namecheap shared hosting / cPanel.
- Product architecture: Dead Signal is a connected player-facing database and Build Planner. The database supports research and discovery; the planner turns selected data into complete loadouts.
- Root landing source: `index.html`, `site.css`, and `site.js` (no WordPress, PHP, or server-side application runtime).
- The approved database-forward landing page and its six category artworks were committed to public `main` at `114514a05b24b15945ae741aab2e8f1a37952cfc`. cPanel still requires **Update from Remote** followed by **Deploy HEAD Commit** to publish a new `main` commit to the live domain.
- Production planner target: `$HOME/public_html/build-planner/`
- Current player release line: **PLAYER v1.5.2**.
- `main` HEAD fetched immediately before the Codex handoff work: `b112baca5d501123b5043d52817fd960495e48c2`.
- Previous expanded historical handoff: `archive/AI-CONTINUITY-2026-08-10-v1.5.0.md`.

## 2. Ownership split — IMPORTANT

### ChatGPT / repository-side work

ChatGPT may:

- reason about mined game data and planner mechanics;
- inspect and update repository source/data/documentation;
- maintain this continuity file and `PROJECT-RULES.md`;
- work on the planner, concepts, normalized data, miner extraction-engine source, probes, schemas, tests, and documentation in GitHub;
- help Codex by leaving exact implementation requirements, evidence, hashes, and acceptance criteria in the repository.

### Codex / local Windows Miner work

**Codex owns the local Miner application, executable packaging, and EXE updates.**

When an executable Miner update is required:

- do **not** make ChatGPT rebuild, patch, package, or hand the user another Miner EXE/ZIP;
- do **not** return to repeated manual source-package handoffs;
- Codex should work from the canonical GitHub Miner source, update/recreate the maintained GUI/launcher, run local Windows/PyInstaller build steps, test the executable, and publish/update the executable release path;
- the planned in-app **Check for Updates / Update Miner** feature belongs to the maintained GUI/launcher and should be implemented by Codex in the local build workflow;
- GitHub source is the development source of truth; executable files are release/build artifacts.

This ownership rule supersedes the older workflow where ChatGPT repeatedly produced downloadable Miner ZIPs.

## 3. Miner source migration — v1.5.7.4 baseline

### 2026-08-12 integrity correction and v1.5.8.0 handoff

The earlier Base64 transport snapshot was structurally readable but did **not** match its documented SHA-256. A byte comparison with the exact verified v1.5.7.4 package proved that only `extractor/weapon_progression.py` was corrupted; the other 25 transported files matched.

- reconstructed transport SHA-256: `d6680766d1d9014c14f2c5af6480c37e4748abde2b7cf3e9f52a91b59a0e3400`
- claimed transport SHA-256: `8f307bf54f8da494505d2aaa4a0fd9d11f818b043449489f5df166e80e54e2e6`
- corrupted `weapon_progression.py`: `179da89e7b9fe8152e1e3abbe70988e12c731008b489b720cf0fe79f7f2a0e9d`
- verified release `weapon_progression.py`: `b2ad070e1f96fd7dae5a15094ff7d7a9a22ccee2f19703865d77beefffad94df`

Codex recovered the fourteen authored source files directly from the exact local package whose size and SHA-256 already matched this continuity record. `SOURCE-MANIFEST-v1.5.7.4.json` records each imported file. The broken Base64 chunks/materializer are retired; normal files in `tools/miner/src/` are authoritative and CI verifies without auto-committing to `main`.

Miner **v1.5.8.0** now includes maintained source for:

- the existing red/black Windows GUI and complete-harvest workflow;
- the local pipeline coordinator connected to the recovered v1.5.7.4 engine;
- a GitHub manifest-based **Check for Updates** control;
- size/SHA-256-verified downloads and a separate rollback-capable updater helper;
- reproducible PyInstaller build and release packaging scripts;
- stale circular-reference diagnostic cleanup at the start of combat resolution;
- automated source-integrity and updater tests.

The final local v1.5.8.0 packaged build passed its packaged `--self-test`. The local release ZIP is 30,074,202 bytes with SHA-256 `4a06bf1492b5c915cf4fb3a51b759205e2829f1d7646c6d8c4279e01aec32b58`. This ZIP is a local artifact until explicitly uploaded as a GitHub release; `release/latest.json` intentionally contains no download URL before that upload exists.

The user supplied:

`Dead-Signal-Miner-v1.5.7.4-Raw-Level-Fallback-Source-Fix(1).zip`

Provenance:

- package size: **31,452,630 bytes**
- package SHA-256: `dff5a8b5e9602e3964c365f90d219899ca0f86ef196813a1cb4d0a5a6ded88e2`
- frozen EXE SHA-256: `8661ba1b5ede49d9d2f39380721694e80672ca7112419bd4ec3b8401f52cca16`
- source-only migration snapshot size: **125,058 bytes**
- source-only snapshot SHA-256: `8f307bf54f8da494505d2aaa4a0fd9d11f818b043449489f5df166e80e54e2e6`
- packaged runtime: Python **3.11**

Canonical Miner home is now:

`tools/miner/`

Important migration files:

- `tools/miner/README.md`
- `tools/miner/MIGRATION-v1.5.7.4.md`
- `tools/miner/VERSION`
- `tools/miner/requirements.txt`
- `tools/miner/SOURCE-MANIFEST-v1.5.7.4.json`
- `tools/miner/scripts/import_verified_release.py`
- `.github/workflows/materialize-miner-source.yml`
- GitHub Issue **#1** — canonical Miner source migration tracker

The original 15-part Base64 bridge was removed after the integrity correction above. Do not restore or rely on it. The exact verified package was used once to recover the direct source tree; ordinary development now uses those maintained source files.

Recovered authored source includes:

- `normalize_weapons.py`
- `export_bindict.py`
- `combat_resolver.py`
- `link_published_images.py`
- `pvr_to_png.py`
- `find_zstd_dicts.py`
- `export_marshaled_bindict.py`
- `normalize_extended.py`
- `reference_images.py`
- `weapon_progression.py`
- `normalize_armor.py`
- `npk_extract.py`
- `neoxtractor/core/bindict/parser.py`
- `neoxtractor/core/bindict/__init__.py`

Pinned package dependency baseline:

- `Pillow==12.3.0`
- `lz4==4.4.5`
- `texture2ddecoder==1.0.6`
- `zstandard==0.25.0`

### GUI/launcher gap — closed by Codex in v1.5.8.0

The supplied v1.5.7.4 package did **not** contain the Windows GUI/launcher as loose maintained `.py` source. That entrypoint is frozen inside `Dead Signal Miner.exe`.

Codex recreated the maintained entrypoint from Dead Signal's own earlier v1.4.0 GUI/core foundation and connected it to the verified recovered engine. This does not claim the frozen EXE was decompiled. Future GUI, engine, build, and updater work begins with `tools/miner/src/`; do not return to repeated ZIP source handoffs.

The former auto-writing materializer workflow is now a read-only Windows verification workflow that installs pinned runtime dependencies, compile-checks source, and runs unit tests.

## 4. Miner factual hierarchy / safety rules

For factual game data use:

1. **Game Miner / installed game files**
2. OnceHumanDB
3. Wikily
4. Official Once Human sources for authoritative patch/system corrections

Do not blindly expose internal/runtime rows. Filter to current player-visible data.

The Miner parsed Once Human `script.npk` with **0 parse errors**.

`reference-tracer.sqlite` is roughly 255 MB with ~1.35M occurrences. Do **not** upload it to production or normal Git history.

Game PYC files use Python 3.11 magic but transformed/remapped opcodes. **Stock `dis` is not authoritative. Do not execute game bytecode.** Use code-object metadata, constants/names/locals, raw/remapped wordcode evidence, and corroborating data tables.

## 5. Miner v1.5.7.4 proven fix

v1.5.7.4 fixed the prior `buffs.json` circular-reference serialization problem caused by raw-level fallback pointing back to the normalized parent record.

Real v1.5.7.4 output proved:

- validation: **PASS**
- new `data/buffs.json`: **0** `_dead_signal_circular_reference` markers
- prior v1.5.7.3 output: **1,248** markers
- combat resolution: **2,711 resolved / 1,086 partial / 44 unresolved**
- Calibration localization: **94 / 94**

The source fix resolves the exact raw level, falls back to level 1 when necessary, and deep-copies the presentation row rather than creating a parent back-reference. Cycle-safe serialization diagnostics remain defensive protection.

A stale `serialization-circular-references.json` could survive from a previous run; future Miner hygiene should clear/regenerate stale diagnostics.

## 6. Current player-facing / normalized database baseline

- Weapons: **120**
- Armor: **173**
- Armor Sets: **23**
- Current Calibrations: **94**
- Unique player-facing Deviations: **97**
- Unique player-facing Cradles: **120**
- Usable Ammo: **144**
- Build-relevant Consumables: **150**
- Older planner-facing Mods: **817 entries / 105 families**
- Older planner Attachments: **108**

Latest Miner normalization snapshot includes:

- mods: **1,618**
- calibrations: **188 raw = 94 current + 94 legacy**
- ammo: **187**
- attachments: **202 raw**
- cradles: **170**
- deviations: **160**
- consumables: **1,086**
- buffs: **3,841 records / 11,046 buff definitions**
- statuses: **24**
- keywords: **10**
- skills: **590**
- stat definitions: **838**
- progression: **1,563**

Weapon normalization:

- 120 weapons = 95 ranged + 25 melee
- 600 Tier-stat rows
- 545 Blueprint-attribute rows
- Blueprint-Star axis validated
- preset-attack-ratio coverage complete
- 530 current recipes
- 0 translation misses

Armor normalization:

- 173 pieces
- 23 sets
- 133 set pieces
- 40 key armor
- 850 Tier-stat rows
- 0 translation misses

Raw attachments contain 202 rows, but the stat-aggregator investigation identifies **119 real weapon-slot accessories**:

- Sight: 30
- Muzzle: 36
- Tactical: 36
- Magazine: 17

Do not dump all 202 rows into the player picker. Reconcile the older 108 planner records against the verified 119-slot set without community guesswork.

## 7. Proven weapon progression / static Attack

Gear Tier and Blueprint Stars are separate axes:

- `corr_forge_lv = [1,2,3,4,5]` = Gear Tier I–V
- `strength_lv` = Blueprint Star level

Rarity star caps: Common up to 3★, Rare generally 4★, Epic 5★, Legendary 6★.

No universal Tier multiplier reproduces every weapon. Store mined Tier values per weapon.

Blueprint Star behavior currently resolves as:

- 82 weapons through `preset_attack_radio`
- 13 through `fixed_skill_lv`
- 25 through neither
- 0 through both

Internal/proven progression formula:

```text
IntrinsicAttack = int(gun_preset_attack[GearTier] * preset_attack_radio[BlueprintStars])
```

Example internally: SKS — Pathfinder T5 6★ = `int(547 × 1.25) = 683`, not 684.

### Player-facing terminology

Do **not** expose `Intrinsic Attack` or `int(...)` as primary UI language.

Use **Base Attack**:

> Attack after Gear Tier and Blueprint Stars, before external Weapon DMG bonuses and Calibration Weapon DMG.

Readable UI arithmetic example:

`547 × 1.25 = 683`

Canonical Attack IDs:

- `D0100` = base/flat Attack family
- `D0101` = Weapon DMG ratio
- `D0102` = current Calibration Weapon DMG / Attack ratio

`D0101` and `D0102` share one additive ratio bucket:

```text
AttackRatio = 1 + Σ(D0101) + Σ(D0102)
StaticAttackFloat = IntrinsicAttack * AttackRatio + FlatAttackDelta
```

Final D0100 card display uses zero-decimal fixed-point formatting. Do not compound D0101/D0102 as independent multipliers.

## 8. Calibration Blueprint model

Current post-Jan-21-2026 Calibration Blueprints have three distinct layers:

1. deterministic fixed Style
2. guaranteed Weapon DMG RNG
3. exactly one random secondary

All **94** current records have localized fixed Style descriptions. Canonical localized short Style names remain unrecovered; current short labels are derived from blueprint names. Do not invent canonical names.

Weapon DMG RNG ranges:

- Rare: **18%–25%**
- Epic: **26%–33%**
- Legendary: **34%–50%**

Secondary pools:

- Rare: Weakspot 12–18%, Crit Rate 8–12%, Elemental 12–18%, Crit DMG 20–30%
- Epic: Weakspot 15–21%, Crit Rate 10–14%, Elemental 12–18%, Crit DMG 25–35%
- Legendary: Weakspot 18–24%, Crit Rate 12–16%, Elemental 15–20%, Crit DMG 30–40%

Observed weights are 200/200/200/200. Do not present all four secondaries as simultaneously active.

`calibration_option_gun = [7, 10]` is a separate weapon-calibration option system, not the random secondary.

Approved planner order:

```text
Gear Tier
Blueprint Stars
Calibration Style / Mod Type
Calibration Blueprint rarity/record
Fixed Calibration Style Effect
Weapon DMG RNG input
Secondary Attribute
Secondary RNG input
Ammo
Weapon Mod
Accessories
...
```

Selection remains **Style first → native rarity record second**.

My Gear uses exact numeric percentage inputs with validation/clamping. **No sliders.** God Roll displays legal maxima.

## 9. Advanced stat engine — HOLD unless proven

Known static IDs include:

- `Q0100` Stability
- `Q0300` Accuracy
- `Q0500` Range
- `Q0900` Fire Rate %
- `Q1100` Magazine flat
- `Q1101` Magazine %
- `Q1600` Mobility
- `Q2000` Drawing Speed %
- `Q2400` Reload Speed
- `Q2600` Bullet Velocity %

`Q1101` exposed a non-zero-suffix resolver hole; variants should resolve generically through `affix_prototype_data`, not one-off hardcodes.

Do not resume broad configured-DPS/runtime-proc implementation merely because IDs are known. Each family must be proven from mined evidence before becoming calculator logic.

Raw Weapon Compare is intentionally allowed because it compares indexed player-facing records and explicitly does not claim Tier/Stars/Calibration/accessory/configured DPS math.

## 10. Planner / deployment rules

**Build/transform before deployment. cPanel only copies prepared static files.**

The root landing page deploys to `$HOME/public_html/`; the planner continues to deploy independently to `$HOME/public_html/build-planner/`. Keep both surfaces static and preserve the planner's same-origin relative paths.

Allowed cPanel deployment operations are lightweight `mkdir`, `cp`, `rm`, and `echo`. Do not reintroduce Python, recursive scans, archive extraction, database generation, or external downloads into `.cpanel.yml`.

Persistent game PNGs remain under:

`/public_html/build-planner/assets/reference-images/`

Preserve same-origin relative planner core asset paths.

Concept folders are isolated review artifacts. Do not add concepts to `.cpanel.yml` or deploy them unless the user explicitly asks to begin production translation.

The 2026-08-11 DNS/SSL public-site problem is resolved. Bare domain returns 200; `www` verifies TLS and redirects to the bare domain. Do not reopen DNS/SSL changes without new evidence.

## 11. Planner operability gate

Source-level persistence protections exist, but end-to-end browser verification remains required before calling persistence fully closed.

Required real-browser torture test still includes:

1. Save → Load My Gear.
2. Blank My Gear Calibration rolls remain blank rather than midpoint defaults.
3. Save → Load God Roll restores mode/badge.
4. Export → Import preserves mode and exact rolls.
5. Share Link preserves mode and exact rolls.
6. Same weapon/calibration with different saved rolls stays independent.
7. New Build does not resurrect prior rolls.
8. Templates do not inherit prior Calibration sidecar state.
9. Legacy payload without `dsExtension.buildMode` opens as My Gear.
10. Build Data Integrity changes from missing-input state to ready only after required inputs exist.
11. Missing controls must fail closed rather than produce false ready state.

## 12. Current Build Lab visual direction

Dead Signal remains a full-width tactical Build Lab using the familiar vertical flow:

**Plan → Weapons → Armor + Mods → Build Systems → Notes → Results**

Current leading concept directory is:

`concepts/color-flow-v6-10/`

Recent concept sequence moved through v6.7–v6.10, including functional armor/weapon configuration work, per-card vertical weapon configuration, restoration of the three-column weapon layout, and armor preview alignment.

Design target:

> **Dark tactical workstation with controlled colored instrumentation layered over the existing planner flow.**

Settled principles:

- readability outranks information density;
- Results / Loadout Report is full-width at the bottom;
- real weapon/armor images belong in cards/pickers;
- persistent sidebar navigation follows scroll position;
- controls must explain themselves on first visit;
- structural colors identify systems/sections; rarity colors identify items;
- **gold/amber is reserved for Legendary rarity meaning**, not structural section identity;
- Signal Rose `#C25578` and Ash Violet `#85708F` are approved structural-direction colors but not rarity colors;
- player-facing language favors **Base Attack**, not internal `Intrinsic Attack`/`int(...)` terminology;
- Cradle slots must say **Cradle Override**, not anonymous `Slot 1`–`Slot 8`.

Best synthesis remains:

> **v2 color/flow + v3 semantic discipline + v6.x expanded palette/scroll navigation + maximum Results readability.**

## 13. Website auditor / competitive baseline

Dead Signal Site Auditor v0.1.1 latest measured baseline:

| Site | Technical | Planner Fidelity | Database & Ecosystem | Avg fetched response |
|---|---:|---:|---:|---:|
| **Dead Signal** | **83.3** | **100.0** | **54.2** | **177 ms** |
| OnceHumanDB | **85.0** | **46.7** | **83.3** | **419 ms** |
| Wikily | **70.7** | **46.7** | **83.3** | **598 ms** |

The auditor detects publicly reachable feature evidence; it does **not** prove workflows operate correctly end-to-end. Dead Signal’s main competitive strength is planner fidelity; broader ecosystem gaps remain recipes/crafting surfaces, community/featured builds, voting/social discovery, maps, and guides.

Do not chase competitor DPS numbers by inventing formulas. Trustworthiness comes first.

## 14. Approved database catalogue direction

The landing-page category cards are currently presentation/navigation placeholders. Their present `#database` targets are not the finished interaction. The next product milestone is a real catalogue, starting with Weapons.

Approved route family:

- `/database/weapons/`
- `/database/armor/`
- `/database/mods/`
- `/database/calibrations/`
- `/database/deviations/`
- `/database/cradle/`

Build the **Weapons catalogue first** and use its architecture as the reusable pattern for the other five categories. The catalogue must use the same normalized, provenance-aware data as the planner; do not create a second manually maintained factual dataset.

Weapons catalogue requirements:

- search by weapon name;
- filters for weapon type, rarity, damage/status characteristics, and other fields proven by normalized data;
- sorting by useful player-facing fields such as name, rarity, Base Attack, Fire Rate, and Magazine where supported;
- grid/list views designed for research rather than only quick selection;
- real weapon artwork and important stats on each card;
- Compare and Add to Build actions;
- honest incomplete/unverified-data indicators;
- individual weapon detail routes with Tier I–V stats, Blueprint Star progression, weapon feature/status mechanics, Calibration compatibility, attachments, compatible/recommended mods when proven, source/verification information, and a Configure in Build Planner action.

The intended user flow is:

**Discover in database → inspect details → compare → send configured item to planner.**

The catalogue should be more informative than the planner picker. The picker remains optimized for fast selection; the catalogue provides explanation, comparison, filtering, and research depth. The landing-page search should eventually search real records across all categories and route to catalogue results.

Implementation constraints:

- keep the public surface lightweight and static-hosting compatible;
- preserve the copy-only cPanel workflow;
- prefer reusable catalogue components/styles/data adapters rather than six unrelated implementations;
- use shared readability controls and player-facing terminology;
- do not invent recommendations, compatibility, mechanics, or derived rankings without evidence;
- preserve normalized-record provenance internally and clearly mark uncertainty;
- connect the Weapons landing card to its catalogue as soon as that route exists.

### Next-chat starting task

Read `AI-CONTINUITY.md`, `PROJECT-RULES.md`, the current root landing files, the planner weapon picker/compare modules, and the normalized weapon-data sources. Then inspect the exact available weapon schema before proposing or building UI. Implement a polished static Weapons catalogue vertical slice, including catalogue browsing, filters/search/sort, one representative detail view, and a safe handoff into the planner. Verify it in a real browser at desktop and mobile widths before expanding to other categories.

## 15. Miner v1.5.9.0 full weapon-math milestone

On 2026-08-12, Codex ran the canonical Miner against the installed Once Human game and completed a full pass successfully. The output root was `C:\Users\mikea\Documents\Dead Signal Miner`; `last-run.json` records Miner `1.5.9.0` completing at `2026-08-12T21:41:39.577441+00:00`.

The run processed the full installed weapon database and published `published/data/weapon-math.json` with:

- 120 weapons total: 95 ranged and 25 melee;
- 600 tier rows and 545 blueprint-star rows;
- 2,725 legal Tier x Star combinations;
- complete proven static math for 120/120 weapons;
- zero weapon-math validation issues;
- 530 current recipes, 76 weapon effects, 188 calibrations, and 202 attachments in the wider normalized snapshot;
- combat validation passing and zero table parse errors.

Miner `1.5.9.0` adds an evidence-backed static weapon-math export. Its proven base-attack rule is `int(tier_base_attack * preset_attack_ratio[stars])`. The static modifier contract groups D0101 and D0102 additively, then applies D0100 as flat attack: `base_attack * (1 + sum(D0101) + sum(D0102)) + sum(D0100_flat)`. Python integer conversion intentionally truncates positive fractional results, matching the extracted computation.

The export fails closed when required tier/star source data is incomplete. It explicitly does not claim configured DPS, runtime proc frequency, enemy mitigation, conditional buffs, or contributions from mods, armor, cradles, deviations, consumables, or team buffs until those layers are independently proven. Do not present the unit-test fixture `547 * 1.25 = 683` as an SKS value; the mined common SKS has three legal blueprint stars and Tier V base attack 769.

The Miner cache check was also hardened. Cached layers are now accepted only when every layer-specific required table is present, preventing an archive-SHA match from reusing an incomplete extraction. A previously incomplete current-layer cache was correctly rejected and refreshed during the canonical run.

All 18 Miner tests pass, including four weapon-math tests and three cache-regression tests. The project-local `.venv-miner/`, Python bytecode, and cache directories are ignored by Git.

The Weapons catalogue now consumes a prepared public projection at `database/weapons/weapon-math-data.js`. It retains all 120 weapons and all 2,725 legal Tier x Star calculations in a roughly 1.4 MB static payload while removing duplicated internal resolver metadata from the 8.7 MB audit export. The payload now also carries canonical `ds-w-<blueprint-id>` IDs, mined acquisition text, and 120/120 resolved installed-game image paths. The catalogue has no `DS_COMMUNITY`, `community-data.js`, or old `wm-data-*` dependency.

The planner loads the same payload before `app.js`. `weapon-data-adapter.js` replaces the legacy planner core's weapon pool with `DS_WEAPON_DATA`, so no old-corpus weapon survives initialization; it leaves non-weapon categories intact until each receives its own Miner-backed migration. Weapon comparison, progression controls, imagery lookup, and catalogue handoff now consume this canonical weapon set. The eight obsolete `wm-data-01.js` through `wm-data-08.js` shards were removed from the repository and are explicitly removed by cPanel deployment.

Generic weapon detail routes now expose legal Gear Tier and rarity-capped Blueprint Star controls, show the verified Base Attack result and calculation trace, and include the selected weapon/tier/stars in the Build Planner handoff. The planner opens its filtered picker and applies the requested configuration after the player selects the weapon. cPanel deployment copies the prepared payload without performing server-side generation.

Real-browser verification passed at desktop and 390 px mobile widths: 120/120 cards rendered, filtering status was correct, no horizontal overflow occurred, the math controls reflowed and remained usable, and a clean AKM detail load produced Tier V 3-star Base Attack 204 from `182 x 1.13 = 204.75`, truncated to 204, with no console errors.

## 16. Cohesive workstation shell milestone

On 2026-08-12, the production landing page, Weapons catalogue, weapon detail routes, and Build Planner were moved under one shared workstation shell. `shared/workstation-shell.css` and `.js` now own the persistent route-aware sidebar, brand, workspace/database/intelligence navigation, text-size controls, desktop frame, and mobile drawer. Page-specific toolbars and content remain local to their route; duplicate global headers and the planner-only legacy sidebar are suppressed by the shell.

The architecture rule is now: one global shell, route-local tools, and shared canonical data. New database verticals should register in the shared navigation and reuse this frame instead of creating another header/sidebar system. Unbuilt destinations remain visibly marked `SOON`; do not imply that they are live. The sidebar's Weapon Compare route opens the planner compare workspace when the canonical weapon payload is available, and Mining Coverage targets the current weapon relationship map.

Desktop browser checks passed for the landing, Weapons, and planner routes: exactly one workstation sidebar rendered, route state was correct, displaced legacy navigation was hidden, and the planner's former horizontal overflow was removed. The mobile shell is CSS-driven below 1100 px with an explicit menu button, scrim, Escape close, and reduced-motion handling.

The planner's former stacked masthead and decorative hero were subsequently replaced by one compact command bar. It owns route identity, system state, and grouped Start/Build/Transfer/Share actions in a single header, using cyan for system state and red for primary/destructive emphasis. Preserve the existing action element IDs because planner modules bind to them.

## 17. Immediate priorities

1. Migrate Armor from the remaining compatibility corpus to the normalized Miner snapshot using the same canonical-data pattern established for Weapons.
2. Package, upload, and verify the v1.5.9.0 Windows ZIP as a GitHub release when the user wants to distribute it, then update `tools/miner/release/latest.json` **last** with the exact public URL, size, and SHA-256.
3. Make the prepared public-data projection reproducible from Miner outputs for every migrated category, keeping cPanel deployment copy-only.
4. Continue visual review from `concepts/color-flow-v6-10/`; do not fork into unrelated design directions.
5. Preserve the real-browser persistence torture test as an open production gate.
6. Reconcile 108 older planner attachments against 119 verified weapon-slot accessories.
7. After Weapons establishes the reusable catalogue pattern, expand it to Armor, Mods, Calibrations, Deviations, and Cradle Overrides.
8. Keep configured DPS/runtime proc math last unless each layer is fully proven.

## 18. Files future sessions should read first

1. `AI-CONTINUITY.md`
2. `PROJECT-RULES.md`
3. `tools/miner/README.md` for Miner work
4. `tools/miner/MIGRATION-v1.5.7.4.md` for Miner provenance/source state
5. `tools/miner/VERSION`
6. `.cpanel.yml`
7. `concepts/instrumented-ui-v3/VISUAL-BIBLE.md`
8. `concepts/color-flow-v6-10/index.html`
9. `OPERABILITY-AUDIT.md`
10. latest `RELEASE-v*.md`
11. `preview/build-lab/index.html`
12. planner persistence/transition/integrity bridge files under `preview/build-lab/`
13. Calibration Style/picker/details modules under `preview/build-lab/`
14. `preview/build-lab/weapon-compare.js` / `.css`
15. `shared/readability.css` / `.js`

### Miner-specific reading rule

For Miner logic, **do not default back to an old extracted `_internal/extractor/` folder or ask the user for another source ZIP.**

Start with the canonical GitHub `tools/miner/` source/migration state. If an executable/build-system task is required, hand that implementation to **Codex**, which owns the local Windows build environment and EXE lifecycle.

## 19. Continuity rules

### 2026-08-12 weapon-configuration mining milestone

- Miner `1.5.11.0` now publishes `published/data/gun-profiles.json`, promoting `item_to_gun_mapping_data` and `gun_no` into the canonical firearm relationship spine.
- All 95 ranged weapons resolve to base, stability, scatter, range-template, reload-template, skill-ID, projectile-ID, and available accessory-slot evidence. The remaining 25 catalogue weapons are melee and are correctly classified as not applicable; unresolved firearm profiles: 0.
- Raw gun fields are preserved as evidence and provenance, but are not automatically treated as combat formulas until their semantics are proven.
- The weapons catalogue now includes a responsive visual system map showing the `item_id` -> `gun_no` spine, verified 95/95 firearm coverage, six connected data branches, and the next runtime-effect resolution target.
- Miner `1.5.10.0` publishes `published/data/weapon-configuration.json` using a fail-closed application policy.
- The installed-client run proved 30 ammunition slot/affix bindings, containing 23 static modifiers, and connected proven ammo packs to 81 of 95 ranged weapon records.
- The provenance chain is `item_to_gun_mapping_data` -> `gun_accessory_slot_params_data` slot 8 -> `gun_accessory_bullet_map_data` -> `gun_accessory_base_params_data` -> `gun_accessory_attr_data`.
- Fourteen ranged weapons remain explicitly unresolved; do not fill them by category/name inference.
- Static attachment modifiers may be calculated directly. Passive buffs and conditional/runtime weapon-mod nodes remain excluded until their trigger/stack/duration semantics are resolved.
- Current calibration styles are mined, but rolled values and term choices are player inputs and must not be silently invented.

- Read this file and `PROJECT-RULES.md` first.
- Fetch current `main` HEAD before repository writes because other sessions may commit concurrently.
- Work on `main`; do not create branches unless the user asks.
- Preserve copy-only cPanel deployment.
- Keep concepts isolated from production until explicitly approved for translation/deployment.
- Do not reopen resolved DNS/SSL settings without new evidence.
- Do not upload the 3 GB master asset archive or `reference-tracer.sqlite` into normal production/Git history.
- Prefer installed-game/mined evidence over community guesses.
- Do not execute transformed game bytecode.
- Do not trust stock `dis` on transformed Once Human PYC without corroboration.
- Prefer small, testable UI changes and screenshot/live iteration.
- Isolate the broken layer before changing unrelated code.
- Do not make the user re-explain project history when the repository can answer it.
- Update this file after major milestones.
- Accessibility/readability is a product requirement.
- Calibration RNG stays exact numeric fields only; no sliders.
- Calibration selection stays Style-first, then rarity/owned RNG.
- The Calibration fixed Style effect is vital information and must not be demoted to footer/fine print.
- Website-auditor detection is evidence of reachable features, not proof of operational correctness.
- Player-facing language must favor clarity over internal terminology.
- Gold/amber structural accents are forbidden because they collide with Legendary rarity semantics.
- **ChatGPT does not own Miner EXE packaging/updating. Codex does.**
- **GitHub `tools/miner/` is the canonical Miner development source; EXEs/ZIPs are build/release artifacts.**
