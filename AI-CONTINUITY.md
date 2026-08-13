# Dead Signal — AI Continuity / Handoff

> **Purpose:** Canonical current-state handoff for ChatGPT/Codex sessions working on Dead Signal. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Last updated: **2026-08-13 (Night Shift active; Miner v1.5.12.1 live; fresh mined snapshot audited; Weapons completion in progress)**

## 1. Project identity

- Project: **Dead Signal Ultimate Planner**
- Game: **Once Human**
- Repository: `raiinman/dead-signal`
- Canonical branch: **`main` only** unless the user explicitly asks otherwise.
- Root site: `https://deadsignaldb.com/`
- Live planner: `https://deadsignaldb.com/build-planner/`
- Hosting: **Namecheap shared hosting / cPanel Git Version Control**.
- Product architecture: one connected player-facing database + Build Planner workstation.
- Historical deep handoffs remain available in Git history and `archive/`.

## 2. Production architecture

Dead Signal is primarily a prepared static site deployed by copy-only cPanel tasks, with one intentional server-side exception:

- `index.html`, `landing-workstation.css`, `site.js` — landing page.
- `shared/workstation-shell.css` / `.js` — one global workstation shell.
- `shared/readability.css` / `.js` — origin-wide text-size system.
- `database/weapons/` — live Weapons catalogue/detail vertical.
- `preview/build-lab/` — source for live Build Planner deployment.
- `api/twitter/cache/index.php` — small cached Official Once Human X feed endpoint.
- `.cpanel.yml` — copy-only deployment manifest.

There is **no WordPress runtime**. Do not reintroduce WordPress.

Deployment rule: cPanel may use lightweight `mkdir`, `cp`, explicitly targeted `rm`, and status `echo`. Do not build, normalize, extract, scan, download, run Python, or perform archive work inside `.cpanel.yml`.

## 3. Global workstation / landing state

Dead Signal is one workstation, not unrelated wiki pages.

- Exactly one global sidebar.
- Desktop collapse persists under `dead-signal-nav-collapsed`.
- Mobile uses the existing off-canvas drawer/menu/scrim/Escape behavior.
- Global shell owns brand, primary navigation, active route, readability, and Miner/system context.
- Route pages own only local tools/content.
- Gold/amber structural accents remain forbidden because they conflict with Legendary rarity semantics.

The landing page is accepted and should be treated as **frozen unless a concrete bug appears**.

Approved landing behavior:

- Hero: **Know the data. Build beyond it.**
- Environment/signal hero art only; avoid people, characters, weapons, creatures, factions, flags, classes, or emblems.
- Official `@OnceHuman_` feed remains on the right.
- One canonical database search lives in the top command strip.
- Do **not** restore the removed lower `Search the Signal` field.
- Top search filters database systems, Enter moves to the database section, `/` focuses it.
- Weapons is live; Armor & Sets, Mods, Calibrations, Deviations, and Cradle Overrides stay `SOON` until their real player-facing routes are ready.

## 4. Official Once Human X feed — frozen working path

Canonical implementation: `api/twitter/cache/index.php`.

Working path:

**Namecheap PHP → public `x.com/OnceHuman_` profile HTML → current status IDs → newest-first snowflake ordering → public/keyless X oEmbed text → public post HTML media/thread evidence → local 5-minute cache → same-origin homepage iframe**

No X developer account, API v2 credentials, Bearer Token, OAuth, paid widget, SociableKIT, Jina runtime, GitHub feed worker, or visitor-side X timeline widget is required.

Feed supports current posts, relative timestamps, photo previews, best-effort video/GIF posters with `OPEN ON X`, conservative same-author thread detection, and fail-soft caching. The user confirmed it looks good live. Do not reopen this pipeline without a real failure.

## 5. External database doctrine

Wikily, OnceHumanDB, and similar community sites are **reference material only** for:

- UX and information architecture;
- feature discovery;
- terminology checks;
- seeing what information players find useful;
- ideas for making Dead Signal clearer and more useful.

Their item totals, record inventories, and coverage counts are **not completeness benchmarks** for Dead Signal. Do not add/remove records or judge Miner coverage by matching another website.

Canonical current-item counts come from Dead Signal's installed-game Miner plus Dead Signal's player-facing filtering rules. If an external database conflicts with proven current Miner evidence, the Miner wins.

## 6. Weapons database / canonical state

Weapons are the first fully migrated player-facing category and tonight's active completion target.

Fresh Miner v1.5.12.1 snapshot confirms:

- **120 canonical weapons = 95 ranged + 25 melee**
- **600 Gear Tier rows**
- **545 Blueprint-Star rows**
- **2,725 legal Gear Tier × Blueprint Star combinations**
- **120/120 weapon artwork linked**
- **120/120 exactly five Gear Tier rows**
- **95/95 firearm profiles resolved**
- **0 unresolved firearm profiles**

Existing website files/routes:

- Current browser projection: `database/weapons/weapon-math-data.js`
- Catalogue: `/database/weapons/`
- Reusable detail: `/database/weapons/detail/?weapon=<id>`
- Planner consumes canonical weapon data through `weapon-data-adapter.js`

Player-facing terminology:

- **Gear Tier** = I–V only.
- **Blueprint Stars** are separate and rarity-capped.
- Primary UI term is **Base Attack**, not internal `Intrinsic Attack`.

Proven static rule:

```text
Base Attack = int(tier_base_attack * preset_attack_ratio[stars])
```

D0101 + D0102 share one additive ratio bucket; D0100 is flat Attack. Runtime proc logic, enemy mitigation, conditional buffs, and configured DPS remain fail-closed until proven.

### Fresh snapshot findings that affect publication

The new v1.5.12.1 publisher proves the website can safely expose much more than it currently does, including:

- RPM, magazine, reload seconds, range, accuracy, stability, mobility;
- full-damage distance, minimum-damage distance, minimum-damage multiplier;
- ammo identity/binding;
- acquisition/blueprint fields;
- Gear Tier × Blueprint Star progression;
- Tier crafting data where a real recipe exists;
- firearm profile/configuration evidence;
- resolved weapon effects where present.

Current integrity findings:

- **76/120** weapons currently resolve a weapon effect.
- **44/120** have no resolved effect; **29 of those are Common**, so absence may be legitimate for many of them.
- The unresolved non-Common group is a mechanics-research queue, not permission to invent effects.
- Known Legendary unresolved examples include **G17 – Cash Only, DBSG – Format, HAMR – Hannya, and MPS7 – Chaos Domain**.
- **14 weapons currently appear to lack Tier recipes; all 14 are melee.** Treat this as a likely `non-craftable` vs `missing recipe` classification problem until the Miner proves otherwise.
- Only a small subset of weapon short descriptions are currently trustworthy; at least one flavor-description mapping is cross-wired (for example Kukri inheriting unrelated fish-flavor text). **Do not expose `short_description` broadly until the resolver is fixed.**
- The current Compare dialog contains Crit/Crit DMG/Weakspot rows but the catalogue stats object does not populate them. Fix during the completion pass using only correctly resolved mined attributes.

## 7. Miner v1.5.12.1 — Publishing & Integrity hotfix line

Canonical Miner source is `tools/miner/`.

**Current canonical/released version: `1.5.12.1`.**

Relevant release state:

- v1.5.12.0 introduced Publishing & Integrity.
- v1.5.12.1 fixes a release-blocking behavior where a `BLOCKED` data-quality state was incorrectly returned as extractor exit code `1`.
- `BLOCKED` is now a **quality/reporting state**, not a Miner crash.
- Real exceptions still fail the Miner normally.
- Publisher logs now print exact `Quality blocker [...]` / `Quality warning [...]` lines.
- GitHub Windows release pipeline builds, tests, packaged-self-tests, publishes, publicly re-downloads, verifies size/SHA-256, and only then updates `tools/miner/release/latest.json`.
- Current updater manifest points to the verified **v1.5.12.1** Windows release.
- The user successfully updated through the Miner's built-in updater.

### Publishing outputs

After normalization and artwork linking the Miner owns the website-facing handoff and produces:

- `published/web/weapons.json`
- `published/web/weapon-configuration.json`
- `published/web/armor.json`
- `published/web/relationship-graph.json`
- `published/web/catalog-index.json`
- `published/reports/data-quality.json`
- `published/reports/change-report.json`
- human-readable `published/reports/CHANGE-REPORT.txt`
- `published/snapshot-manifest.json`

Audit-grade normalized files remain under `published/data/`; the compact `published/web/` layer is the intended consumption contract for Dead Signal.

### Relationship graph rule

The relationship graph records direct mined identifier/evidence links such as:

- weapon → `gun_no`;
- gun → ammo item;
- gun → linked skill ID;
- weapon/passive skill → buff/keyword/status evidence;
- Armor piece → Armor Set;
- Key Armor → passive skill → buff.

Initial edges are evidence such as `proven-direct-link`. They **do not** claim trigger conditions, proc chance, stack count, duration, cooldown, refresh behavior, additive/multiplicative buckets, or DPS unless those semantics are separately proven.

This graph is the scaffold for later deeper mechanic resolution.

### Publishing/integrity philosophy

The Miner should increasingly own:

**installed game → extraction → normalization → validation → compact web projection → change/readiness reports → Dead Signal**

Do not create a second competing normalization truth inside the website.

## 8. Miner updater / release rule

The Miner has a working GitHub self-update feature. **Preserve it.**

Current architecture:

- GitHub `main` is the canonical maintained source.
- Verified Windows release packages are built through the repository's Windows GitHub release workflow.
- Installed Miners discover released updates through `tools/miner/release/latest.json`.
- The release manifest must be updated **last**, only after the exact GitHub-hosted release ZIP exists and its public URL, byte size, and SHA-256 have been verified.
- The updater accepts GitHub-hosted HTTPS packages and validates size + SHA-256 before installation.
- Do not manually hand the user replacement EXEs/ZIPs when the updater path can deliver the patch correctly.
- Keep CI-only fake game-install markers isolated to release self-test infrastructure; they are not mined data and must never become part of runtime assumptions.

## 9. Current player-facing data baseline

Fresh known Dead Signal baseline:

- Weapons: **120**
- Armor: **173**
- Armor Sets: **23**
- Current Calibrations: **94**
- Unique player-facing Deviations: **97**
- Unique player-facing Cradles: **120**
- Usable Ammo: **144**
- Build-relevant Consumables: **150**
- Older planner Mods: **817 entries / 105 families**
- Older planner Attachments: **108**

Broader Miner normalization previously observed:

- mods 1,618
- calibrations 188 raw = 94 current + 94 legacy
- ammo 187
- attachments 202 raw
- cradles 170
- deviations 160
- consumables 1,086
- buffs 3,841 records / 11,046 definitions
- statuses 24
- keywords 10
- skills 590
- stat definitions 838
- progression 1,563

Raw attachments are not equivalent to valid player picker accessories. Previously verified weapon-slot accessories were 119: 30 Sight, 36 Muzzle, 36 Tactical, 17 Magazine. Reconcile the older planner set before replacing its picker.

## 10. Armor data state / next Miner fixes

Armor remains `SOON`, but the v1.5.12.1 snapshot exposed the exact schema blocker.

The current Armor normalizer supports:

- Armor Sets and individual pieces;
- Helmet, Top, Pants, Shoes, Gloves, Mask slots;
- Tier I–V stats;
- HP, Pollution Resistance, Psi Intensity, durability, weight, and other resolved attributes;
- set bonuses with required piece counts;
- standalone Key Armor;
- Key Armor passive/effect resolution;
- rarity and blueprint IDs;
- Tier crafting recipes;
- fixed/selectable crafting materials and selectable material effects;
- currency cost and craft time;
- artwork references;
- explicit review queues for unresolved records.

### Current Armor blocker

The overall fresh snapshot reports `BLOCKED` because the public Armor projection currently builds canonical piece IDs from **blueprint ID alone**, but the installed game contains legitimate variant families that reuse underlying blueprint IDs.

Known examples:

- Blackstone Set
- Blackstone Set (Cold)
- Blackstone Set (Heat)
- Rustic / Snowland Rustic variants

Therefore:

- do **not** deduplicate them away;
- do **not** assume the Miner count is wrong;
- fix the public canonical identity scheme to be variant-aware;
- keep Armor public route `SOON` until identity is collision-free and the generated snapshot passes its internal invariants.

After Weapons completion, this is the first Miner/schema fix before the Armor catalogue is built.

## 11. Calibration / Mod rules

Current Calibration Blueprint model:

1. deterministic fixed Style;
2. guaranteed Weapon DMG RNG;
3. exactly one random secondary.

Weapon DMG RNG ranges:

- Rare 18–25%
- Epic 26–33%
- Legendary 34–50%

My Gear uses exact numeric percentage inputs with validation/clamping; **no sliders**. Calibration selection remains Style-first, then native rarity/record.

Current Mod 2.0 baseline:

- regular mods keep a main attribute and fixed sub-attributes;
- levels 1–17;
- Lv17 regular ceiling;
- Shiny Mods are distinct stronger-main-attribute variants;
- legacy random sub-attributes are not the default current model.

## 12. Readability / accessibility

Readability is a product requirement.

- Shared controller: `shared/readability.css` + `.js`.
- Modes: compact/default/large/xlarge.
- Storage key: `dead-signal-font-size`.
- New interfaces should use the shared semantic `--ds-type-*` variables rather than tiny arbitrary fixed text.
- Respect `prefers-reduced-motion`.

## 13. Night Shift — active objectives

**Night Shift is active.** Do not substitute stale older priorities.

### Primary objective — finish Weapons as the gold-standard database vertical

1. Use the user's fresh **v1.5.12.1 mined snapshot** as the authoritative source.
2. Treat the large audit/publisher output as source evidence; do **not** dump giant raw JSON into every browser route.
3. Build/use a compact canonical website Weapons contract derived from the Miner publishing output.
4. Upgrade weapon detail UX around player questions:
   - Overview
   - Combat
   - Handling
   - Damage Profile
   - Weapon Mechanic
   - Gear Tier × Blueprint Stars
   - Crafting / acquisition when proven
   - Configure in Build Lab
   - Provenance / limits
5. Populate Compare with proven fields, legal Tier/Star configuration, and simple arithmetic deltas where useful.
6. Preserve exact configured Tier/Stars when handing a weapon into Build Lab.
7. Do not expose known-bad flavor descriptions.
8. Do not convert unresolved effect/recipe fields into guessed content.
9. Do not add speculative DPS, proc frequency, enemy mitigation, rankings, or invented multiplier semantics.

### Secondary objective — patch Miner issues exposed by the fresh snapshot

After the Weapons completion pass is stable, patch the Miner/publisher for:

1. **variant-aware Armor canonical identity**;
2. explicit **non-craftable vs missing-recipe** classification;
3. **weapon short-description resolver** correctness;
4. deeper investigation of **unresolved non-Common weapon effects**;
5. any additional integrity checks discovered while wiring the real website projection.

Release Miner patches through the verified GitHub updater workflow and update `latest.json` last.

### After those fixes

The planned category order is:

**Armor & Sets → Calibrations → Mods → Attachments → Deviations / Cradles → full mechanics-aware Build Lab**

Armor should use the mature Weapons data-contract lessons, but should remain set-centric rather than blindly cloning the Weapons UI.

### End-of-shift requirement

Before stopping Night Shift:

- leave `main` in a clean, deployable state;
- record completed commits/current HEAD;
- record anything intentionally incomplete or blocked;
- update **this handoff** with the exact morning state so another session can recover without user repetition.

## 14. Files future sessions should read first

1. `AI-CONTINUITY.md`
2. `PROJECT-RULES.md`
3. `tools/miner/README.md`
4. `tools/miner/docs/PUBLISHING-v1.5.12.0.md`
5. `tools/miner/src/extractor/publish_web_data.py`
6. `tools/miner/src/miner_core.py`
7. `tools/miner/release/latest.json` before updater/release work
8. `database/weapons/index.html`
9. `database/weapons/catalogue.js` / `catalogue.css`
10. `database/weapons/weapon-math-data.js`
11. `preview/build-lab/` weapon adapter/handoff/persistence modules
12. `.cpanel.yml`

Also inspect the newest user-provided Miner `published/` snapshot when it is available in the active conversation; repository docs describe the schema, but the current mine is the authoritative current data snapshot.

## 15. Continuity rules

- Read this file and `PROJECT-RULES.md` first.
- Do not make the user re-explain history when the repo/current snapshot can answer it.
- Work on current `main`; fetch current HEAD/current blobs before writes because other sessions may commit concurrently.
- Prefer installed-game/mined evidence over community guesses.
- External databases are UX/reference material, never corpus authority.
- Do not invent mechanics, compatibility, rankings, or numeric relationships.
- Keep runtime mechanic/math resolution fail-closed until proven.
- Preserve one global shell and route-local tools.
- Unbuilt database destinations stay `SOON`.
- Preserve copy-only cPanel deployment.
- Preserve GitHub Miner self-update architecture and publish updater manifests last.
- Do not execute transformed game bytecode.
- **Update this handoff after every major Night Shift milestone, not only at the end.**
