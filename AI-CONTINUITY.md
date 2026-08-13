# Dead Signal — AI Continuity / Handoff

> **Purpose:** Canonical current-state handoff for ChatGPT/Codex sessions working on Dead Signal. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Last updated: **2026-08-13 (Night Shift active; Miner v1.5.12.2 released; Weapons UX/integrity pass landed; fresh v1.5.12.2 local publish still needs materialization into the website)**

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

Weapons are the first fully migrated player-facing category and Night Shift's primary completion target.

The last full installed-game snapshot available to the AI session was mined with v1.5.12.1 and confirmed:

- **120 canonical weapons = 95 ranged + 25 melee**
- **600 Gear Tier rows**
- **545 Blueprint-Star rows**
- **2,725 legal Gear Tier × Blueprint Star combinations**
- **120/120 weapon artwork linked**
- **120/120 exactly five Gear Tier rows**
- **95/95 firearm profiles resolved**
- **0 unresolved firearm profiles**

Miner **v1.5.12.2** is now released, but a fresh v1.5.12.2 mine has not yet been transported from the user's PC into the repository/session. Until that happens, do not claim the browser payload itself is v1.5.12.2 data.

Existing website files/routes:

- Current committed browser projection: `database/weapons/weapon-math-data.js`
- Catalogue: `/database/weapons/`
- Reusable detail: `/database/weapons/detail/?weapon=<id>`
- Dedicated SKS route: `/database/weapons/sks-pathfinder/`
- Planner consumes the canonical committed weapon payload through `preview/build-lab/weapon-data-adapter.js`.
- `preview/build-lab/catalogue-handoff.js` preserves requested Gear Tier and Blueprint Stars from the catalogue/detail route into the Build Lab when those values are legal for the selected weapon.

Player-facing terminology:

- **Gear Tier** = I–V only.
- **Blueprint Stars** are separate and rarity-capped.
- Primary UI term is **Base Attack**, not internal `Intrinsic Attack`.

Proven static rule:

```text
Base Attack = int(tier_base_attack * preset_attack_ratio[stars])
```

D0101 + D0102 share one additive ratio bucket; D0100 is flat Attack. Runtime proc logic, enemy mitigation, conditional buffs, and configured DPS remain fail-closed until proven.

### Night Shift Weapons UX/integrity pass — landed on `main`

The catalogue/detail path was upgraded without inventing new mechanics:

- Compare now supports **per-weapon legal Gear Tier and Blueprint Stars** rather than comparing only a fixed baseline.
- Configured Compare Base Attack comes from the selected proven Tier × Star matrix.
- Compare now surfaces mined handling/damage-profile fields where available: RPM, magazine, reload, accuracy, stability, range, mobility, full-damage distance, minimum-damage distance, and minimum-damage multiplier.
- Crit Rate, Crit DMG, and Weakspot DMG are read only from matching mined star attributes; rows disappear if neither weapon provides a proven value.
- Compare can display simple arithmetic deltas for numeric fields; it does **not** imply configured DPS.
- Generic weapon detail now separates **Combat**, **Handling**, **Damage Profile**, **Weapon Mechanic**, **Gear Tier × Blueprint Stars**, and **Verification/limits**.
- Detail pages show the proven Base Attack calculation trace and preserve the selected Tier/Stars in the Build Lab handoff URL.
- Resolved weapon-effect text is allowed; unresolved effects display an explicit unresolved/absent state.
- The known-bad `short_description` / flavor-text fallback was removed from both the catalogue and Build Lab adapter.
- The stale visible Miner-version label on the Weapons catalogue was removed in favor of a generic Miner-verified label.
- Frontend script cache keys were bumped so a normal cPanel copy deploy does not leave browsers on the previous catalogue/adapter JavaScript.

Key implementation commits from this pass:

- `eaedb4a927c42729cc83372f5923caf61c3990e7` — Upgrade weapons comparison and detail evidence UX
- `cdd2bfb70798b95eda3d1ddc5d7dfaf960061890` — Harden weapon catalogue numeric formatting
- `a55a57e1b5a6915afc96fac16ee7e0201903700e` — Refresh weapon catalogue runtime label and cache key
- `18c251d895a23dfca3ddcaef60a729ac73c532db` — Cache-bust upgraded generic weapon details
- `4b9e341695826dc4fa5f460b7a1b7811f967a190` — Cache-bust upgraded SKS weapon details
- `1fff1d4ce9329c9f67b3ded270af3d4ee5c27c0c` — Remove unsafe weapon flavor fallback from Build Lab
- `85161883bb0ceda5f7b73ccce7a85490dee92119` — Cache-bust hardened Build Lab weapon adapter

### Snapshot findings still awaiting deeper mechanic/schema work

The last full snapshot showed:

- **76/120** weapons resolving a weapon effect.
- **44/120** with no resolved effect; **29 of those are Common**, so absence may be legitimate for many of them.
- Known Legendary unresolved examples: **G17 – Cash Only, DBSG – Format, HAMR – Hannya, MPS7 – Chaos Domain**.
- **14 weapons** appeared to lack Tier recipes; all 14 were melee. This remains a `non-craftable` vs `missing recipe` classification problem until separately proven.
- At least one normalized short-description mapping was cross-wired (Kukri receiving unrelated fish-flavor text). The website and public publisher now fail closed instead of exposing those strings.

## 7. Miner v1.5.12.2 — Publishing & Integrity hotfix line

Canonical Miner source is `tools/miner/`.

**Current canonical/released version: `1.5.12.2`.**

Release sequence:

- v1.5.12.0 introduced Publishing & Integrity.
- v1.5.12.1 fixed the behavior where a `BLOCKED` data-quality state incorrectly returned extractor exit code `1`; `BLOCKED` is now a quality/reporting state, not a Miner crash.
- v1.5.12.2 hardens the public publisher against two real snapshot integrity problems:
  1. weapon short descriptions are withheld from the public contract until their resolver is verified;
  2. Armor set-piece canonical IDs are variant-aware using **`suit_id + blueprint_id`** rather than blueprint ID alone.

### v1.5.12.2 verified release

The Windows release workflow completed successfully through:

1. source compilation;
2. Miner unit tests;
3. source self-test;
4. packaged Miner/updater build;
5. packaged self-test;
6. release ZIP packaging;
7. GitHub release creation;
8. public re-download;
9. byte-size and SHA-256 verification;
10. updater manifest publication last.

Current `tools/miner/release/latest.json` points to:

- version: **1.5.12.2**
- channel: `stable`
- package: `Dead-Signal-Miner-v1.5.12.2-Windows.zip`
- SHA-256: `26a4d3013cd1eb991366da58f2d7714e1c4fc1a8f5edb46eb1549ed9cefa728d`
- size: **30,671,335 bytes**

Release commits:

- `74147fc61b0ace5140d41668abfd05fdbbfb3f06` — Bump Miner to v1.5.12.2
- `a14591e4a8352d9711efd52a5c6e501a8d048343` — Publish Miner v1.5.12.2 updater release

### Publisher hardening / regression coverage

`tools/miner/src/extractor/publish_web_data.py` now:

- publishes weapon `description` as blank until the short-description resolver is proven safe;
- records `verification.description_status = withheld-until-short-description-resolver-is-verified`;
- gives set pieces public IDs shaped as **`ds-a-{suit_id}-{blueprint_id}`**;
- preserves `suit_id` on the public set-piece record and relationship-graph node.

Regression tests live in `tools/miner/tests/test_publish_web_integrity.py` and prove:

- known-wrong `short_description` text does not escape into the public Weapons contract;
- two Armor suit variants may reuse the same blueprint ID without colliding in public canonical identity.

Relevant commits:

- `9609a310a6cbdfe82dffbcfe058b4e061d5b06a1` — Harden publisher weapon descriptions and armor identity
- `b4866fbf0746260a9bd128a24b66b900349ec579` — Add publisher integrity regression tests

The regression tests passed in the release pipeline and in the replacement source-test workflow.

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

## 8. Miner updater / CI / release rules

The Miner has a working GitHub self-update feature. **Preserve it.**

Current architecture:

- GitHub `main` is the canonical maintained source.
- Verified Windows release packages are built through `.github/workflows/release-miner-v1512.yml`.
- Installed Miners discover released updates through `tools/miner/release/latest.json`.
- The release manifest is updated **last**, only after the exact GitHub-hosted release ZIP exists and its public URL, byte size, and SHA-256 have been verified.
- The updater accepts GitHub-hosted HTTPS packages and validates size + SHA-256 before installation.
- Do not manually hand the user replacement EXEs/ZIPs when the updater path can deliver the patch correctly.
- Keep CI-only fake game-install markers isolated to test/release infrastructure; they are not mined data and must never become runtime assumptions.

### Night Shift CI hardening

A release-engineering flaw was discovered: the old release workflow fired on every `tools/miner/**` source/test commit, causing same-version release jobs to rebuild and republish v1.5.12.1 while work was still being staged.

This is now fixed:

- `.github/workflows/release-miner-v1512.yml` publishes automatically **only when `tools/miner/VERSION` changes** (manual dispatch remains available).
- Release jobs use a dedicated concurrency group so release work cannot race itself.
- `.github/workflows/test-miner.yml` is the normal source/test CI path for Miner Python/tests/dependency/build-environment changes.
- The obsolete `.github/workflows/materialize-miner-source.yml` / `Verify Miner source` workflow was removed. Its last red check was not a source failure; it omitted `PYTHONPATH`, causing `test_gun_profiles.py` to fail import with `ModuleNotFoundError: extractor` while the correctly configured release pipeline passed the same source.
- The replacement `Test Miner source` workflow completed successfully, including compilation, unit tests, and source self-test.

CI hardening commits:

- `832d384fdc9d80e6eecb675b2978226e2c44b725` — Separate Miner release trigger from source changes
- `c42bff0321d90a28f24233eb90f4f042701066c3` — Add Miner source test workflow
- `fd16a2d77161cabc95776e8e67dec9c378055da5` — Replace stale Miner verifier workflow

## 9. Current player-facing data baseline

Last fresh known Dead Signal baseline from the installed-game snapshot:

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

Armor remains `SOON` until a **fresh v1.5.12.2 generated snapshot** proves its public identity invariants against the real installed-game dataset.

The Armor normalizer supports:

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

### Variant identity blocker — publisher fix landed, real-snapshot revalidation still required

The v1.5.12.1 snapshot was `BLOCKED` because public Armor set pieces used blueprint ID alone and legitimate variant families reuse underlying blueprint IDs.

Known examples included:

- Blackstone Set
- Blackstone Set (Cold)
- Blackstone Set (Heat)
- Rustic / Snowland Rustic variants

The normalizer already provides a real parent `suit_id`, so v1.5.12.2 now identifies a set piece as:

```text
ds-a-{suit_id}-{blueprint_id}
```

This is deterministic and variant-aware without inventing name slugs or deduplicating legitimate variants. A regression test proves synthetic same-blueprint/different-suit variants remain unique.

**Do not mark Armor READY solely because the code fix exists.** Run v1.5.12.2 against the user's real installed-game snapshot and confirm the generated quality report clears the duplicate canonical-ID blocker before building/publishing the Armor route.

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

## 13. Night Shift — active objectives and exact checkpoint

**Night Shift is active.** Do not substitute stale older priorities.

### Completed in the current Night Shift tranche

- Upgraded Weapons Compare to apply legal Gear Tier/Blueprint Stars and expose proven mined comparison fields.
- Upgraded generic weapon detail structure around Combat, Handling, Damage Profile, Mechanic, progression, and provenance.
- Preserved configured Tier/Stars into Build Lab handoff.
- Removed unsafe weapon flavor-description fallback from both Weapons catalogue/detail and Build Lab.
- Hardened numeric display against null-as-zero rendering.
- Patched the Miner public publisher to withhold unverified weapon short descriptions.
- Patched Armor set-piece identity to use `suit_id + blueprint_id`.
- Added regression tests for both publisher integrity issues.
- Released and publicly verified **Miner v1.5.12.2** through the built-in updater path.
- Split Miner test CI from release CI and removed the stale contradictory verifier workflow.

### Current implementation checkpoint

The latest functional/CI commit before this handoff update is:

`fd16a2d77161cabc95776e8e67dec9c378055da5` — Replace stale Miner verifier workflow

`main` is intended to remain deployable. The modified player-facing files are already included in the existing copy-only `.cpanel.yml`; no deployment-time build step was added.

### Primary remaining blocker — fresh website payload transport

The website still uses the committed static `database/weapons/weapon-math-data.js` browser projection. The AI session does **not** have a direct PC filesystem/remote-control connector despite the user's permission, and no fresh `published/` snapshot was found in the available File Library.

Therefore the next workstation-dependent step is:

1. update the user's installed Miner to **v1.5.12.2** through its built-in updater;
2. run a fresh mine/publish against the installed game;
3. inspect `published/reports/data-quality.json` and `published/reports/change-report.json`;
4. verify Armor duplicate IDs are cleared on the real snapshot;
5. materialize the fresh compact `published/web/weapons.json` (and related public contract files as needed) into the prepared website payload;
6. only then describe the live/committed browser corpus as refreshed to v1.5.12.2.

Do **not** fake this step by relabeling the old static browser data.

### Remaining Weapons work after fresh payload is available

- Wire the compact Miner public Weapons contract into the browser without creating a second normalization truth.
- Add proven crafting and acquisition sections from the fresh publisher output.
- Revalidate Crit/Crit DMG/Weakspot attribute mappings against real v1.5.12.2 records.
- Classify the 14 missing melee recipes as legitimately non-craftable vs unresolved/missing evidence.
- Investigate unresolved non-Common weapon effects through direct relationship evidence; no guessed proc semantics.
- Decide when Weapons has earned gold-standard/frozen status.

### Then continue category order

**Armor & Sets → Calibrations → Mods → Attachments → Deviations / Cradles → full mechanics-aware Build Lab**

Armor should use the mature Weapons data-contract lessons, but should remain set-centric rather than blindly cloning the Weapons UI.

### End-of-shift requirement

Before stopping Night Shift:

- leave `main` in a clean, deployable state;
- record completed commits/current implementation checkpoint;
- record anything intentionally incomplete or blocked;
- update **this handoff** with the exact morning state so another session can recover without user repetition.

## 14. Files future sessions should read first

1. `AI-CONTINUITY.md`
2. `PROJECT-RULES.md`
3. `tools/miner/README.md`
4. `tools/miner/docs/PUBLISHING-v1.5.12.0.md`
5. `tools/miner/src/extractor/publish_web_data.py`
6. `tools/miner/tests/test_publish_web_integrity.py`
7. `tools/miner/src/miner_core.py`
8. `tools/miner/release/latest.json` before updater/release work
9. `.github/workflows/test-miner.yml`
10. `.github/workflows/release-miner-v1512.yml`
11. `database/weapons/index.html`
12. `database/weapons/catalogue.js` / `catalogue.css`
13. `database/weapons/weapon-math-data.js`
14. `preview/build-lab/weapon-data-adapter.js`
15. `preview/build-lab/catalogue-handoff.js`
16. `.cpanel.yml`

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
- Ordinary Miner source/test commits should run the test workflow, **not** publish a release. Bump `tools/miner/VERSION` only when intentionally cutting a verified update.
- Do not execute transformed game bytecode.
- **Update this handoff after every major Night Shift milestone, not only at the end.**
