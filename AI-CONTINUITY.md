# Dead Signal — AI Continuity / Handoff

> **Purpose:** Canonical current-state handoff for ChatGPT/Codex sessions working on Dead Signal. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Last updated: **2026-08-12 (production landing, live official X feed, header-polish checkpoint)**

## 1. Project identity

- Project: **Dead Signal Ultimate Planner**
- Game: **Once Human**
- Repository: `raiinman/dead-signal`
- Canonical branch: **`main` only** unless the user explicitly asks otherwise.
- Root site: `https://deadsignaldb.com/`
- Live planner: `https://deadsignaldb.com/build-planner/`
- Hosting: **Namecheap shared hosting / cPanel Git Version Control**.
- Current player release line: **PLAYER v1.5.2**.
- Product architecture: one connected player-facing database + Build Planner workstation.
- Historical deep handoff remains available in Git history and `archive/AI-CONTINUITY-2026-08-10-v1.5.0.md`.

## 2. Current production architecture

Dead Signal is primarily a prepared static site deployed by copy-only cPanel tasks, with **one intentional server-side exception**:

- `index.html`, `landing-workstation.css`, `site.js` — root landing page.
- `shared/workstation-shell.css` / `.js` — one global workstation shell.
- `shared/readability.css` / `.js` — origin-wide text-size system.
- `database/weapons/` — live Weapons catalogue/detail vertical.
- `preview/build-lab/` — source for the live Build Planner deployment.
- `api/twitter/cache/index.php` — small server-side cached official Once Human X feed used by the landing hero.
- `.cpanel.yml` — copy-only deployment manifest.

There is **no WordPress runtime**. Do not reintroduce WordPress.

### cPanel rule

Deployment remains copy-only. Allowed operations are lightweight `mkdir`, `cp`, explicitly targeted `rm`, and status `echo` operations. Do not build, normalize, extract, scan, download, or run Python inside `.cpanel.yml`.

The X feed PHP endpoint is runtime code, but it is already-prepared source copied into place by cPanel; deployment itself remains copy-only.

## 3. Approved global workstation shell

Dead Signal is one workstation, not unrelated wiki pages.

- Use exactly **one global sidebar**.
- Sidebar desktop collapse is explicit and persists under `dead-signal-nav-collapsed`.
- Do not return to hover-only expansion.
- Mobile uses the existing menu button, scrim, Escape handling, and off-canvas drawer.
- Global shell owns brand, primary route navigation, active route state, text-size controls, and Miner/status context.
- Each route owns only local tools/content.
- Do not add a second global sidebar, duplicate masthead, or decorative page hero above functional content.

The shared motion layer in `shared/workstation-shell.css` provides progressive-enhancement page transitions, coordinated sidebar motion, smoother controls/cards, reduced-motion handling, and same-origin navigation continuity. Keep motion restrained and functional.

## 4. Landing page — approved current state

The landing page is now accepted live by the user.

Product flow:

1. Understand what Dead Signal is.
2. Choose **Open Build Lab** or **Explore Database**.
3. Search the signal.
4. Choose one of six database systems.

Hero:

- Main copy: **Know the data. Build beyond it.**
- Background art: `assets/hero/dead-signal-environment-hero-v2.png`.
- Hero identity rule: environment/signal imagery only. Avoid people, player avatars, humanoid silhouettes, weapons, creatures, factions, classes, flags, and emblems.
- Right side is the **Official Once Human Feed**, replacing the old fake loadout mockup.

Database cards:

- Weapons is the only currently live category route.
- Armor & Sets, Mods, Calibrations, Deviations, and Cradle Overrides remain visibly `SOON` and non-clickable until their player-facing migrations/routes are ready.
- Existing six category-art families are approved and should be reused.

## 5. Official Once Human X feed — WORKING / FREE / SERVER-SIDE

The feed architecture is settled and should not be replaced casually.

Working path:

**Namecheap PHP → public `x.com/OnceHuman_` profile HTML → current status IDs → newest-first snowflake ordering → public/keyless X oEmbed for post text → public post HTML for media/thread hints → local 5-minute cache → same-origin homepage iframe**

Important facts:

- **No X developer account is required.**
- No Bearer Token, API key, OAuth, paid widget, SociableKIT, Jina runtime, GitHub Actions worker, or visitor-side X widget is required.
- `api/twitter/cache/index.php` is the canonical implementation.
- The temporary `/api/twitter/probe/` diagnostic was removed and cPanel explicitly removes the old deployed probe directory.
- The homepage directly embeds `/api/twitter/cache/` in a same-origin iframe.
- Old `platform.twitter.com/widgets.js`, `platform.x.com/widgets.js`, direct syndication iframes, debug query modes, and retry loaders were removed.

Current feed behavior:

- current posts from `@OnceHuman_`, newest first;
- relative timestamps;
- avatar/author/post links;
- photo previews from public `pbs.twimg.com/media/...` sources;
- best-effort video/GIF poster detection with **VIDEO · OPEN ON X** treatment rather than proxying/hosting video;
- conservative same-author thread detection using public conversation/status evidence;
- local cache fails soft: keep useful cached output rather than blanking the homepage when upstream X is temporarily unavailable.

Do not switch back to X's direct public timeline widget: it failed to initialize reliably on Dead Signal and the direct syndication route produced rate limiting.

The user confirmed the current feed looks good live. Treat future feed changes as small polish unless a real failure is demonstrated.

Recent feed commits:

- `4f32748e` — use Namecheap server for live X feed;
- `a288c6bd` / `f558098f` — remove temporary probe and deployment debris;
- `0957e76d` — simplify homepage to direct same-origin feed iframe;
- `a5ca0b12` — add public photo previews;
- `50514256` — add video poster and conservative thread detection;
- `ab31f62` — responsive breathing room around hero/feed.

## 6. Landing command/header checkpoint

The hero/feed is stable enough to freeze.

First command/header polish is implemented on `main` at **`ce2836ae` (`Polish landing command header`)** and is awaiting the user's live cPanel deployment/review.

That pass intentionally does not touch the feed pipeline. It adds:

- desktop sticky command strip at widths above the mobile-shell breakpoint;
- more compact 66 px desktop height;
- clearer DS route-identity chip;
- search icon + `/` keyboard hint inside the command search field;
- stronger focus treatment;
- verified-data state as a compact cyan pill instead of loose text;
- tighter Build Lab CTA proportions;
- medium-width priority change: hide redundant route identity before hiding verified state;
- mobile/tablet spacing that avoids collision with the fixed workstation menu.

If the user accepts this live, freeze the commandbar too and continue deeper into the database experience. If feedback is negative, adjust **header only** before touching Weapons or Build Lab.

## 7. Weapons database / canonical data state

Weapons are the first fully migrated player-facing category.

- 120 weapons total = 95 ranged + 25 melee.
- 600 Tier rows.
- 545 Blueprint-Star rows.
- 2,725 legal Tier × Star combinations.
- Current player-facing projection: `database/weapons/weapon-math-data.js`.
- Catalogue: `/database/weapons/`.
- Representative detail: `/database/weapons/sks-pathfinder/`.
- Reusable detail route: `/database/weapons/detail/?weapon=<id>`.
- Planner consumes the same canonical weapon payload through `weapon-data-adapter.js`.

Player-facing terminology:

- say **Gear Tier** and **Blueprint Stars**;
- Gear Tier is I–V only;
- rarity caps Blueprint Stars;
- say **Base Attack**, not internal `Intrinsic Attack` as the primary UI term.

Proven static attack rule:

```text
Base Attack = int(tier_base_attack * preset_attack_ratio[stars])
```

Static D0101 + D0102 ratios share one additive ratio bucket; D0100 is flat attack. Do not invent configured DPS/runtime proc relationships beyond proven mined evidence.

## 8. Current player-facing data baseline

- Weapons: **120**
- Armor: **173**
- Armor Sets: **23**
- Current Calibrations: **94**
- Unique player-facing Deviations: **97**
- Unique player-facing Cradles: **120**
- Usable Ammo: **144**
- Build-relevant Consumables: **150**
- Older planner Mods: **817 / 105 families**
- Older planner Attachments: **108**

Latest broader Miner snapshot includes:

- mods: 1,618
- calibrations: 188 raw = 94 current + 94 legacy
- ammo: 187
- attachments: 202 raw
- cradles: 170
- deviations: 160
- consumables: 1,086
- buffs: 3,841 records / 11,046 definitions
- statuses: 24
- keywords: 10
- skills: 590
- stat definitions: 838
- progression: 1,563

Raw attachments contain 202 rows, but verified weapon-slot accessories currently resolve to 119 player-facing accessories: 30 Sight, 36 Muzzle, 36 Tactical, 17 Magazine. Do not dump all raw rows into the picker.

## 9. Calibration / mod model rules

Current Calibration Blueprints:

1. deterministic fixed Style;
2. guaranteed Weapon DMG RNG;
3. exactly one random secondary.

Weapon DMG RNG ranges:

- Rare 18%–25%
- Epic 26%–33%
- Legendary 34%–50%

My Gear uses exact numeric percentage inputs with validation/clamping. **No sliders.** Calibration selection remains Style-first, then native rarity/record.

Current Mod 2.0 baseline:

- regular mods keep a main attribute and fixed sub-attributes;
- mod level 1–17;
- Lv.17 regular ceiling;
- Shiny Mods are distinct stronger-main-attribute variants;
- legacy random-sub-attribute logic is not the default current model.

## 10. Miner ownership / source rule

Canonical Miner development source is under `tools/miner/`.

- ChatGPT may inspect/update repository-side Miner source, data, tests, schemas, and docs.
- **Codex owns local Windows EXE packaging/build/update work.**
- Do not return to repeated manual Miner ZIP/EXE handoffs from ChatGPT.
- Do not execute transformed Once Human game bytecode.
- Stock `dis` is not authoritative for transformed game PYC without corroboration.

Current weapon relationship milestones include Miner 1.5.10/1.5.11 configuration and gun-profile exports. Keep runtime proc/conditional math fail-closed until proven.

## 11. Readability / accessibility

Readability is a product requirement.

- Shared system: `shared/readability.css` + `shared/readability.js`.
- Modes: compact, default, large, xlarge.
- Origin-wide storage key: `dead-signal-font-size`.
- New interfaces should use shared semantic `--ds-type-*` variables rather than tiny arbitrary text.
- Reduced-motion users must not be forced through decorative motion.

## 12. Deployment / production rules

- Work on current `main`; fetch current HEAD before writes because other sessions may commit concurrently.
- Production publishes through cPanel Git Version Control: **Update from Remote → Deploy HEAD Commit**.
- Preserve copy-only deployment.
- Do not reopen DNS/SSL work without new evidence; the prior public-site DNS/SSL problem was resolved.
- Do not upload the ~3 GB master asset archive or `reference-tracer.sqlite` into normal Git/production.
- Keep concept folders isolated unless the user explicitly approves production translation.

## 13. Immediate priorities

1. Have the user deploy/review **`ce2836ae`** header polish live.
2. If accepted, freeze the landing hero/feed/header and continue layer-by-layer into the next database category experience.
3. Migrate Armor from the compatibility corpus to the normalized Miner snapshot using the same canonical-data pattern as Weapons.
4. Make public-data projections reproducible from Miner outputs for each migrated category.
5. Preserve the Build Planner persistence torture test as an open production gate.
6. Reconcile older planner attachments against the verified 119 weapon-slot accessory set.
7. Keep configured DPS/runtime proc math last unless each layer is fully proven.

## 14. Files future sessions should read first

1. `AI-CONTINUITY.md`
2. `PROJECT-RULES.md`
3. `.cpanel.yml`
4. `index.html`
5. `landing-workstation.css`
6. `site.js`
7. `shared/workstation-shell.css` / `.js`
8. `api/twitter/cache/index.php` for official-feed work
9. `database/weapons/weapon-math-data.js`
10. `database/weapons/index.html` + catalogue/detail JS/CSS
11. `preview/build-lab/index.html` and planner bridge/persistence modules
12. `tools/miner/README.md`, `tools/miner/VERSION`, and canonical `tools/miner/` source for Miner work

## 15. Continuity rules

- Read this file and `PROJECT-RULES.md` first.
- Do not make the user re-explain project history when the repository can answer it.
- Prefer small, testable UI changes and screenshot/live iteration.
- Isolate the broken layer before changing unrelated code.
- Unbuilt database destinations stay visibly `SOON`.
- Preserve one global shell and route-local tools.
- Prefer installed-game/mined evidence over community guesses.
- Do not invent mechanics, compatibility, rankings, or numeric relationships.
- Gold/amber structural accents remain forbidden because they collide with Legendary rarity semantics.
- Update this handoff after major milestones.
- **The official X feed is now a deliberate server-side exception; do not remove PHP merely because older handoff text said the site was fully static.**
- **Do not replace the working feed with a visitor-side X widget without strong new evidence.**
- **ChatGPT does not own Miner EXE packaging/updating; Codex does.**
