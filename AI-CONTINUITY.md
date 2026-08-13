# Dead Signal — AI Continuity / Handoff

> **Purpose:** Canonical current-state handoff for ChatGPT/Codex sessions working on Dead Signal. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Last updated: **2026-08-13 (Miner v1.5.12.0 Publishing & Integrity landed; Weapons completion night next)**

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

Weapons are the first fully migrated player-facing category.

- 120 weapons = 95 ranged + 25 melee.
- 600 Gear Tier rows.
- 545 Blueprint-Star rows.
- 2,725 legal Gear Tier × Blueprint Star combinations.
- Existing browser projection: `database/weapons/weapon-math-data.js`.
- Catalogue: `/database/weapons/`.
- Reusable detail: `/database/weapons/detail/?weapon=<id>`.
- Planner consumes the same canonical weapon data through `weapon-data-adapter.js`.

Player-facing terminology:

- **Gear Tier** = I–V only.
- **Blueprint Stars** are separate and rarity-capped.
- Primary UI term is **Base Attack**, not internal `Intrinsic Attack`.

Proven static rule:

```text
Base Attack = int(tier_base_attack * preset_attack_ratio[stars])
```

D0101 + D0102 share one additive ratio bucket; D0100 is flat Attack. Runtime proc logic, enemy mitigation, conditional buffs, and configured DPS remain fail-closed until proven.

### Weapons completion opportunity

The website currently exposes less than the Miner already knows. The next Weapons pass should surface existing mined/proven fields such as:

- Crit / Crit DMG / Weakspot attributes where correctly resolved;
- actual reload seconds;
- ammunition binding;
- damage falloff distances/multiplier;
- acquisition / blueprint information;
- Tier I–V crafting recipes;
- firearm/profile/configuration evidence;
- unique weapon mechanic text and linked evidence without invented runtime semantics.

The current Compare dialog already has Crit/Crit DMG/Weakspot rows, but the catalogue stats object does not populate those fields yet. Fix this as part of the completion pass.

## 7. Miner v1.5.12.0 — Publishing & Integrity

Canonical Miner source is `tools/miner/`.

**Current canonical source version: `1.5.12.0`.**

Verified source commit:

- `951ff290bd1c00bc3c803a94c33a0b5ee664d490` — **Miner v1.5.12 publishing and integrity**.

The GitHub materialization run successfully passed:

- patch SHA-256 verification;
- Python 3.11 setup/dependencies;
- compile check;
- full Miner unit-test suite (**31/31 passing**);
- final verified source commit.

Temporary patch chunks/workflow were removed by the final commit.

### v1.5.12 publishing outputs

After normalization and artwork linking the Miner now owns the website-facing handoff and produces:

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

The initial relationship graph records direct mined identifier/evidence links such as:

- weapon → `gun_no`;
- gun → ammo item;
- gun → linked skill ID;
- weapon/passive skill → buff/keyword/status evidence;
- Armor piece → Armor Set;
- Key Armor → passive skill → buff.

Initial edges are evidence such as `proven-direct-link`. They **do not** claim trigger conditions, proc chance, stack count, duration, cooldown, refresh behavior, additive/multiplicative buckets, or DPS unless those semantics are separately proven.

This graph is the scaffold for later deeper mechanic resolution.

### v1.5.12 other changes

- Obsolete WordPress Studio sync/config/UI workflow was removed.
- `publish_web_data.py` added as the canonical publishing/integrity stage.
- Internal data-quality/readiness reporting is based on the Miner corpus itself, never external-site counts.
- Snapshot/change reporting can show what changed between successful local mines after Once Human patches.
- Snapshot manifest fingerprints Miner/game/pipeline/output artifacts for reproducibility.
- `build.ps1` includes the new publisher module.

## 8. Miner updater / release rule

The Miner has a working GitHub self-update feature. **Preserve it.**

Important separation:

- GitHub `main` is the canonical maintained **source**.
- Codex/local Windows owns building/testing the Windows Miner release package/EXE.
- Installed Miners discover released updates through `tools/miner/release/latest.json`.
- The release manifest must be updated **last**, only after the exact GitHub-hosted release ZIP exists and its public URL, byte size, and SHA-256 have been verified.
- The updater accepts GitHub-hosted HTTPS packages and validates size + SHA-256 before installation.
- Do not point `latest.json` at v1.5.12.0 merely because source is now on `main`.

Therefore at this checkpoint:

- v1.5.12.0 source: **landed and verified**.
- v1.5.12.0 installed self-update release: **pending Codex/local Windows packaging and verified GitHub asset**.
- Existing release manifest should remain on the last verified packaged release until that work is complete.

ChatGPT does not own recurring manual EXE/ZIP handoffs; Codex owns local Windows package lifecycle.

## 9. Current player-facing data baseline

Known current Dead Signal player-facing baseline:

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

## 10. Armor data state

The current Miner Armor normalizer is already substantially richer than the old website handoff implied. It supports:

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

Armor is still `SOON` on the public site. Do not enable it until a current real `published/web/armor.json` snapshot has been generated and the player-facing catalogue/detail experience is ready.

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

## 13. Immediate evening plan

The next work block is **Weapons completion**, not another landing-page polish pass and not Armor yet.

1. Use Miner v1.5.12's new publishing contract as the canonical web-data path.
2. Generate/inspect the newest real local Miner `published/web/weapons.json` when available; do not substitute community database counts.
3. Expand the website weapon projection/adapter so the browser consumes the useful already-mined weapon detail instead of only the old math-focused subset.
4. Upgrade weapon detail UX around player questions:
   - Overview
   - Combat
   - Handling
   - Damage Profile
   - Weapon Mechanic
   - Gear Tier × Blueprint Stars
   - Crafting
   - Configure in Build Lab
5. Upgrade Compare with actual populated proven fields, legal Tier/Star configuration, and simple proven arithmetic deltas where useful.
6. Keep configured DPS, proc frequency, enemy mitigation, rankings, and speculative mechanics out until fully proven.
7. Once Weapons is the gold-standard vertical, use its data/presentation lessons for Armor without cloning the UI blindly.

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

## 15. Continuity rules

- Read this file and `PROJECT-RULES.md` first.
- Do not make the user re-explain history when the repo can answer it.
- Work on current `main`; fetch current HEAD before writes because other sessions may commit concurrently.
- Prefer installed-game/mined evidence over community guesses.
- External databases are UX/reference material, never corpus authority.
- Do not invent mechanics, compatibility, rankings, or numeric relationships.
- Keep runtime mechanic/math resolution fail-closed until proven.
- Preserve one global shell and route-local tools.
- Unbuilt database destinations stay `SOON`.
- Preserve copy-only cPanel deployment.
- Preserve GitHub Miner self-update architecture and publish updater manifests last.
- Do not execute transformed game bytecode.
- ChatGPT does not own Miner EXE packaging/updating; Codex does.
- Update this handoff after major milestones.
