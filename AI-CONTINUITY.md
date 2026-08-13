# Dead Signal — AI Continuity / Handoff

> **Purpose:** Canonical current-state handoff for ChatGPT/Codex sessions working on Dead Signal. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Last updated: **2026-08-13 — Night Shift active; Miner v1.5.12.2 released; Weapons UX/integrity and compact-contract bridge landed; fresh local v1.5.12.2 mine is the remaining workstation-dependent step.**

## 1. Project identity

- Project: **Dead Signal Ultimate Planner**
- Game: **Once Human**
- Repository: `raiinman/dead-signal`
- Canonical branch: **`main` only** unless the user explicitly asks otherwise.
- Root site: `https://deadsignaldb.com/`
- Live planner: `https://deadsignaldb.com/build-planner/`
- Hosting: **Namecheap shared hosting / cPanel Git Version Control**.
- Product model: one connected player-facing database + Build Planner workstation.

## 2. Production architecture / frozen decisions

Dead Signal is a prepared static site with one narrow PHP exception:

- landing: `index.html`, `landing-workstation.css`, `site.js`
- global shell: `shared/workstation-shell.css` / `.js`
- readability: `shared/readability.css` / `.js`
- Weapons: `database/weapons/`
- Build Lab source: `preview/build-lab/`
- Official Once Human X feed cache: `api/twitter/cache/index.php`
- deploy manifest: `.cpanel.yml`

**No WordPress runtime. Do not reintroduce WordPress.**

cPanel deployment remains **copy-only**. It may use targeted `mkdir`, `cp`, `rm`, and lightweight `echo`; do not mine, normalize, scan, unzip, download, build, or run Python inside `.cpanel.yml`.

The landing page and working Official Once Human X feed are accepted/frozen unless a concrete bug appears. Keep exactly one global sidebar, persistent desktop collapse, existing mobile drawer behavior, shared readability controls, and `SOON` labels for unfinished routes. Gold/amber structural accents remain forbidden because Legendary rarity owns that semantic color space.

## 3. Data doctrine

The installed-game Miner is canonical for migrated player-facing categories.

Wikily, OnceHumanDB, official/community pages, videos, Reddit, Chinese sites, etc. may be used for UX ideas, terminology checks, feature discovery, and validation of unresolved behavior. Their item totals and inventories are **not** completeness targets. If current proven Miner evidence conflicts with an external database, the Miner wins.

Do not invent mechanics, compatibility, proc behavior, rankings, multiplier semantics, enemy mitigation, or configured DPS.

## 4. Weapons — proven baseline

Weapons are the first fully migrated player-facing category and the current gold-standard target.

The last complete installed-game snapshot available to this AI session was mined with v1.5.12.1 and proved:

- **120 canonical weapons = 95 ranged + 25 melee**
- **600 Gear Tier rows**
- **545 Blueprint-Star rows**
- **2,725 legal Gear Tier × Blueprint Star combinations**
- **120/120 artwork linked**
- **120/120 exactly five Gear Tier rows**
- **95/95 firearm profiles resolved**
- **0 unresolved firearm profiles**

Miner **v1.5.12.2** is released, but a fresh v1.5.12.2 mine has not yet been transported from the user's PC into this repo/session. Do **not** relabel the currently committed browser corpus as v1.5.12.2 until that happens.

Player-facing terminology:

- **Gear Tier** = I–V only.
- **Blueprint Stars** are separate and rarity-capped.
- UI term is **Base Attack**, not internal `Intrinsic Attack`.

Proven static formula:

```text
Base Attack = int(tier_base_attack * preset_attack_ratio[stars])
```

D0101 + D0102 share one additive ratio bucket; D0100 is flat Attack. Runtime proc logic, conditional effects, enemy mitigation, and configured DPS remain fail-closed.

## 5. Weapons Night Shift UX/integrity pass — landed

Current routes:

- catalogue: `/database/weapons/`
- reusable detail: `/database/weapons/detail/?weapon=<id>`
- dedicated SKS route: `/database/weapons/sks-pathfinder/`
- Build Lab: `/build-planner/`

Landed improvements:

- Compare supports **legal per-weapon Gear Tier + Blueprint Stars**.
- Compare Base Attack comes from the selected Tier × Star matrix.
- Compare exposes proven RPM, magazine, reload, accuracy, stability, range, mobility, distance-profile fields, and mined star attributes where available.
- Crit Rate / Crit DMG / Weakspot rows only appear when matching mined attributes exist.
- Numeric deltas are simple arithmetic only; no DPS implication.
- Generic detail is separated into **Combat**, **Handling**, **Damage Profile**, **Weapon Mechanic**, **Gear Tier × Blueprint Stars**, and **Verification / limits**.
- Detail shows the proven Base Attack calculation trace.
- Exact selected Tier/Stars are preserved into Build Lab through `catalogue-handoff.js`.
- Resolved weapon-effect text is allowed; unresolved/absent effects remain explicit.
- Unsafe `short_description` flavor fallback was removed from catalogue/detail and Build Lab.
- Numeric helpers no longer render null as zero.
- stale visible Miner-version labels were removed from player-facing Weapons UI.
- cache keys were bumped for the upgraded frontend modules.

Key commits:

- `eaedb4a927c42729cc83372f5923caf61c3990e7` — Upgrade weapons comparison and detail evidence UX
- `cdd2bfb70798b95eda3d1ddc5d7dfaf960061890` — Harden weapon catalogue numeric formatting
- `a55a57e1b5a6915afc96fac16ee7e0201903700e` — Refresh weapon catalogue runtime label and cache key
- `1fff1d4ce9329c9f67b3ded270af3d4ee5c27c0c` — Remove unsafe weapon flavor fallback from Build Lab
- `85161883bb0ceda5f7b73ccce7a85490dee92119` — Cache-bust hardened Build Lab weapon adapter

## 6. Compact Miner Weapons contract — browser path is now prepared

The Miner's intended website contract is `published/web/weapons.json`. Night Shift prepared the site to consume it without creating a second normalization truth.

New files:

- `database/weapons/weapons-data.js`
  - currently a **null placeholder** only;
  - will contain the exact compact public JSON wrapped as `window.DS_WEAPONS_WEB` after materialization.
- `database/weapons/weapon-public-adapter.js`
  - thin compatibility bridge;
  - if a valid `dead-signal-weapons` public contract is present, it becomes the preferred source and is adapted into the temporary `DS_WEAPON_MATH` consumer shape;
  - if no compact payload is present, the existing `weapon-math-data.js` remains the fallback.
- `tools/site/materialize-weapons-web.py`
  - accepts `weapons.json`, `published/web/`, or the Miner `published/` directory;
  - validates schema, non-empty records, unique canonical IDs, and declared record count;
  - wraps the **exact JSON payload** for static browser use;
  - does not reinterpret or normalize game data.
- `tools/site/tests/test_materialize_weapons_web.py`
- `.github/workflows/test-site-tools.yml`

Load order is now prepared on catalogue, detail, SKS, and Build Lab:

```text
weapons-data.js
→ weapon-math-data.js        # temporary legacy fallback
→ weapon-public-adapter.js   # compact contract wins when present
→ normal route consumers
```

`.cpanel.yml` copies the compact payload + bridge to both `/database/weapons/` and `/build-planner/`; deployment remains copy-only.

Website-data CI passes:

- compact-contract materializer unit tests: **green**
- Node syntax checks for Weapons / Build Lab adapter modules: **green**

Key commits:

- `ac3985ef9fed3354abee3ab533cdbf6d9c4601ef` — Add compact Weapons contract placeholder
- `d21025e5b2051bd7f2042df3b033236261ac469b` — Add compact Weapons public compatibility bridge
- `d9765608b1d3521698f26d25bda51bff16b899c8` — Add compact Weapons contract materializer
- `96747cd0e9e363f034f373b31dd345e66f3d00ee` — Prefer compact public Weapons contract in catalogue
- `90de358edebff400fceb7f4805a3abc9a4aa082a` — Prefer compact public Weapons contract in details
- `ec544e62ea009d4fc16e9cd6956c1c9ece3ab8b6` — Prefer compact public Weapons contract on SKS detail
- `c60a7d932a7c2a1ebcb79ac350c151be1601f74d` — Prefer compact public Weapons contract in Build Lab
- `0f0d28f8312739d57534e618aa4b9e413ca86fbf` — Deploy compact Weapons contract compatibility files
- `1694d0ca79a209146104a4c1b97c132386dd722f` — Add Weapons contract materializer tests
- `a943b562406e8490b8fb4c88caf6f5f0c9572936` — Add Weapons website data-path CI

## 7. Miner v1.5.12.2 — current released version

Canonical Miner source: `tools/miner/`.

**Current canonical/released version: `1.5.12.2`.**

History:

- v1.5.12.0 introduced Publishing & Integrity.
- v1.5.12.1 made `BLOCKED` a quality/reporting state instead of a Miner crash.
- v1.5.12.2 fixes two real publisher integrity issues:
  1. unverified weapon `short_description` text is withheld from the public contract;
  2. Armor set-piece public identity is variant-aware via `suit_id + blueprint_id`.

The Windows release passed source compile/tests, source self-test, package build, packaged self-test, GitHub release creation, public re-download, size/SHA verification, and updater-manifest publication last.

Current updater manifest:

- version: **1.5.12.2**
- package: `Dead-Signal-Miner-v1.5.12.2-Windows.zip`
- SHA-256: `26a4d3013cd1eb991366da58f2d7714e1c4fc1a8f5edb46eb1549ed9cefa728d`
- size: **30,671,335 bytes**

Release commits:

- `74147fc61b0ace5140d41668abfd05fdbbfb3f06` — Bump Miner to v1.5.12.2
- `a14591e4a8352d9711efd52a5c6e501a8d048343` — Publish Miner v1.5.12.2 updater release

Publisher hardening:

- public weapon `description` is blank until short-description resolver is proven safe;
- `verification.description_status` records the withholding state;
- Armor set-piece public ID is `ds-a-{suit_id}-{blueprint_id}`;
- set-piece public records and graph nodes preserve `suit_id`.

Regression tests prove both the short-description fail-closed rule and same-blueprint/different-suit Armor identity.

Relevant commits:

- `9609a310a6cbdfe82dffbcfe058b4e061d5b06a1` — Harden publisher weapon descriptions and armor identity
- `b4866fbf0746260a9bd128a24b66b900349ec579` — Add publisher integrity regression tests

## 8. Miner publishing contract

After normalization/artwork linking, the Miner produces:

- `published/web/weapons.json`
- `published/web/weapon-configuration.json`
- `published/web/armor.json`
- `published/web/relationship-graph.json`
- `published/web/catalog-index.json`
- `published/reports/data-quality.json`
- `published/reports/change-report.json`
- `published/reports/CHANGE-REPORT.txt`
- `published/snapshot-manifest.json`

Audit-grade normalized files remain under `published/data/`; compact `published/web/` is the intended Dead Signal consumption contract.

Relationship graph edges are direct evidence only: weapon → gun, gun → ammo/skill, weapon/passive skill → buff/keyword/status, Armor piece → set, Key Armor → passive skill → buff. These links do **not** prove triggers, proc chance, stack count, duration, cooldown, refresh behavior, additive/multiplicative buckets, or DPS.

## 9. Miner CI/release architecture

Night Shift fixed an important release-engineering flaw. Previously, ordinary `tools/miner/**` source commits could republish the same release version.

Current rules:

- `.github/workflows/test-miner.yml` handles normal Miner source/test validation.
- `.github/workflows/release-miner-v1512.yml` automatically publishes **only when `tools/miner/VERSION` changes**; manual dispatch remains available.
- release jobs use a dedicated concurrency group.
- updater manifest remains the last release write.
- obsolete `.github/workflows/materialize-miner-source.yml` / `Verify Miner source` was removed. Its final red check was an environment bug (`PYTHONPATH` missing), not a Miner regression.
- replacement `Test Miner source` workflow is green.

CI commits:

- `832d384fdc9d80e6eecb675b2978226e2c44b725` — Separate Miner release trigger from source changes
- `c42bff0321d90a28f24233eb90f4f042701066c3` — Add Miner source test workflow
- `fd16a2d77161cabc95776e8e67dec9c378055da5` — Replace stale Miner verifier workflow

## 10. Armor state

Armor remains `SOON` until a fresh v1.5.12.2 real snapshot proves its invariants.

The v1.5.12.1 snapshot was `BLOCKED` because legitimate variant families reused blueprint IDs while the public publisher used blueprint ID alone. Known examples included Blackstone base/cold/heat and Rustic/Snowland Rustic.

The normalizer already supplies a real parent `suit_id`, so v1.5.12.2 now uses:

```text
ds-a-{suit_id}-{blueprint_id}
```

A regression test proves same-blueprint/different-suit records remain unique.

**Do not mark Armor READY merely because the code fix landed.** Run the real v1.5.12.2 snapshot and verify `published/reports/data-quality.json` clears the duplicate canonical-ID blocker first.

## 11. Known unresolved Weapons research queue

Last full snapshot findings:

- **76/120** weapons resolved a weapon effect.
- **44/120** had no resolved effect; **29 of those were Common**.
- known unresolved Legendary examples: **G17 – Cash Only, DBSG – Format, HAMR – Hannya, MPS7 – Chaos Domain**.
- **14 weapons** had one or more missing Tier recipes; all 14 were melee.
- at least one short-description mapping was cross-wired (Kukri receiving unrelated fish-flavor text).

Resolver inspection this shift confirmed:

- current weapon-effect publication begins with the Blueprint level-1 `fixed_skill_code`, then passive skill → buff → translated player-facing text;
- firearm `gun_skill_no` is preserved separately as direct relationship evidence and must **not** automatically be treated as the player's weapon mechanic;
- missing Tier recipes currently mean the forge row did not resolve for recorded tiers; this is insufficient evidence to call the weapon non-craftable.

Therefore:

- do not guess missing effects from `gun_skill_no`;
- do not label the 14 melee weapons non-craftable without stronger evidence;
- use the fresh snapshot's direct relationships/raw normalized rows to classify them.

## 12. Other current player-facing baseline

Last known installed-game baseline:

- Armor: **173**
- Armor Sets: **23**
- current Calibrations: **94**
- unique player-facing Deviations: **97**
- unique player-facing Cradles: **120**
- usable Ammo: **144**
- build-relevant Consumables: **150**
- older planner Mods: **817 entries / 105 families**
- older planner Attachments: **108**

Broader normalized corpus previously observed:

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

Raw attachment totals are not equivalent to valid player-picker accessories. Previously verified weapon-slot accessories: 119 = 30 Sight + 36 Muzzle + 36 Tactical + 17 Magazine.

## 13. Calibration / Mod rules

Calibration Blueprint model:

1. deterministic fixed Style;
2. guaranteed Weapon DMG RNG;
3. exactly one random secondary.

Weapon DMG RNG ranges:

- Rare 18–25%
- Epic 26–33%
- Legendary 34–50%

My Gear uses exact numeric percentage inputs with validation/clamping; **no sliders**.

Current Mod 2.0 baseline:

- regular mods keep a main attribute + fixed sub-attributes;
- levels 1–17;
- Lv17 regular ceiling;
- Shiny Mods are distinct stronger-main-attribute variants;
- legacy random sub-attributes are not the default current model.

## 14. Readability

Readability is a product requirement.

- shared controller: `shared/readability.css` + `.js`
- modes: compact/default/large/xlarge
- storage key: `dead-signal-font-size`
- new UI should use shared semantic `--ds-type-*` variables
- respect `prefers-reduced-motion`

## 15. Exact Night Shift checkpoint / remaining blocker

Latest functional + CI checkpoint before this handoff update:

`a943b562406e8490b8fb4c88caf6f5f0c9572936` — **Add Weapons website data-path CI**

`main` is intended to remain deployable. No runtime build step was added to cPanel.

### The one workstation-dependent step

The website's `weapons-data.js` is intentionally still a null placeholder because this session has no direct PC filesystem/remote-control tool despite the user's permission, and no fresh Miner `published/` snapshot was available in the File Library.

Next sequence when local output becomes accessible:

1. update the installed Miner through its built-in updater to **v1.5.12.2**;
2. run a fresh mine/publish against the installed Once Human game;
3. inspect `published/reports/data-quality.json` and `change-report.json`;
4. confirm the real Armor duplicate-ID blocker is cleared;
5. run:

```text
python tools/site/materialize-weapons-web.py <path-to-Miner-published>
```

6. verify the generated `database/weapons/weapons-data.js` contains the fresh compact contract;
7. run/confirm website-data CI;
8. commit the materialized payload;
9. only then remove the legacy `weapon-math-data.js` fallback after real-browser validation.

Do **not** fake this step by changing labels on the old payload.

### Remaining Weapons work after fresh payload lands

- render proven crafting/acquisition fields from compact public records;
- revalidate Crit/Crit DMG/Weakspot mappings against real current records;
- classify missing melee recipes as genuinely non-craftable vs unresolved evidence;
- investigate unresolved non-Common effects using direct relationship evidence;
- decide when Weapons earns frozen/gold-standard status.

Then proceed:

**Armor & Sets → Calibrations → Mods → Attachments → Deviations / Cradles → full mechanics-aware Build Lab**

## 16. Files future sessions read first

1. `AI-CONTINUITY.md`
2. `PROJECT-RULES.md`
3. `tools/miner/release/latest.json`
4. `tools/miner/src/extractor/publish_web_data.py`
5. `tools/miner/src/extractor/normalize_weapons.py`
6. `tools/miner/src/extractor/normalize_armor.py`
7. `tools/miner/tests/test_publish_web_integrity.py`
8. `.github/workflows/test-miner.yml`
9. `.github/workflows/release-miner-v1512.yml`
10. `tools/site/materialize-weapons-web.py`
11. `.github/workflows/test-site-tools.yml`
12. `database/weapons/weapons-data.js`
13. `database/weapons/weapon-public-adapter.js`
14. `database/weapons/catalogue.js`
15. `preview/build-lab/weapon-data-adapter.js`
16. `preview/build-lab/catalogue-handoff.js`
17. `.cpanel.yml`

Always inspect the newest local Miner `published/` snapshot when it becomes available; repo docs define the contract, but the current mine defines current game data.

## 17. Continuity rules

- Do not make the user re-explain repo history that the handoff/current snapshot answers.
- Work on current `main`; fetch current blobs before writes because another session may commit concurrently.
- Prefer installed-game/mined evidence over community guesses.
- External databases are UX/reference material, never corpus authority.
- Keep mechanics/math fail-closed until proven.
- Preserve one global workstation shell.
- Keep unfinished database routes `SOON`.
- Preserve copy-only cPanel deployment.
- Preserve the Miner self-update path and publish updater manifest last.
- Ordinary Miner source/test commits run test CI; **only intentional VERSION changes should publish a release**.
- Do not execute transformed game bytecode.
- Update this handoff after every major Night Shift milestone and again at morning/end-of-shift.
