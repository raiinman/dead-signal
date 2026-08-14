# Dead Signal — AI Continuity / Handoff

> Read this file and `PROJECT-RULES.md` first. Canonical current-state handoff for `raiinman/dead-signal` on `main`.
>
> Updated **2026-08-13 Day Shift** after fresh installed-client v1.5.12.8 proof, all-seven contract validation, Weapon star-axis correction, and Armor Tier/recipe UX work.

## Non-negotiables

- Work directly on canonical `main` unless the user explicitly requests otherwise.
- Installed-game / Miner evidence outranks guesses and community corpus counts.
- Never invent mechanics, recipes, compatibility, proc behavior, DPS, rankings, multiplier semantics, crafting identity, or variant identity.
- Missing recipe evidence never proves non-craftable.
- Preserve accepted landing page, Official Once Human X feed, global workstation shell, and readability system unless a concrete bug exists.
- Static/copy-only cPanel deployment. No WordPress runtime. Do not touch DNS, SSL, redirects, domain settings, or cPanel hosting configuration.
- Routes that are not genuinely ready remain `SOON`.
- Use transactional all-seven materialization for a final Miner snapshot; do not hand-copy one category around another category.
- Competitor UX audit remains last, after core database + Build Lab migration is broadly complete.

## Stable Miner

Miner **v1.5.12.8 is RELEASED and stable**.

Release chain:

- `2a48e197e33c956c4c90a1d3b1b0c101d6d1a1a7` — Calibration float comparison repair.
- `b0b76b6a4d3ece160983d89366e83d673fe60ec8` — VERSION 1.5.12.8.
- `1329230baff3c7a24866dba0262e246c7c753aa0` — updater manifest published last.
- Release workflow `31756476284` SUCCESS.

## Miner Research Console — source complete on main

The read-only Miner Research Console is implemented and verified on canonical `main`:

- `29df27b66ebf0729709ddc00b8430a5d8a867240` — adds the Research Console service, desktop UI, exact evidence search, explicitly non-authoritative Related Search, Weapon Investigator, exact-ID reverse lookup, provenance graph, unresolved queue, translation forensics, prioritized snapshot diff, local bookmarks/notes, compact research evidence export, and integrity/coverage dashboard.
- `e4711592ca9350a57a754f8dac4e39f01b95a0e8` — hardens frozen-app packaging/self-test behavior and applies the final dark results-grid treatment found during GUI smoke testing.
- GitHub Actions `31777559089` (`Test Miner source`) SUCCESS for `e4711592ca9350a57a754f8dac4e39f01b95a0e8`; source tests, Windows build, and packaged self-test all passed.
- Local validation: 64 Miner source tests PASS; dependency-complete source self-test PASS; Windows PyInstaller build PASS; packaged self-test exit code 0; GUI smoke PASS for the main Miner window and the Research Console window.
- Local verified executable SHA-256: `466c8575ba030ce5d361c3e4ff61ca575b22fe0efb4cbc1b5d5525e07a883d8e` (developer build only; not a published release asset).
- `a4619b7d7c2c4894cdc068f5ac25218a778c04d1` — corrects the version collision with the previously published v1.5.12.9 package and releases the Research Console as Miner v1.5.13.0.
- Release workflow `31777944199` SUCCESS: source tests, Windows build, packaged self-test, release packaging, GitHub asset publication, public asset download/hash verification, and updater-manifest-last publication all passed.
- Public v1.5.13.0 package: SHA-256 `cd023bcf643a55c02f24798135e23011e7534f581b585ff01a6b3b233a3a9729`, size 30,826,730 bytes; updater-manifest commit `df17efa4ff5b702de4733e22059bdf9b1e109b1b`.

Safety boundaries are enforced in code and tests: game files and snapshot inputs are read-only, research paths cannot traverse outside the selected Miner data folder, the SQLite tracer is opened read-only, no game bytecode is executed, IDs are never fuzzy-promoted, Related Search cannot create authoritative evidence, graph edges retain source provenance, and suspect/shared/conflicting translations remain withheld from publication. `reference-tracer.sqlite`, snapshots, research notes, exports, builds, and packaged runtimes remain local/generated and are not committed.

Current Research Console blockers / follow-up:

1. The existing local published snapshot was produced by released Miner v1.5.12.8. After updating to v1.5.13.0, run one complete snapshot before relying on the newly projected Weapon effect/translation classifications in the console; existing snapshot evidence still correctly exposes 14 missing recipe series, 9 unresolved attachment compatibilities, 92 ambiguous Deviation/Cradle families, and the Mod consumer-semantics blocker.
2. Mod frame positional consumer semantics remain unproven and fail-closed.
3. Deviation/Cradle multi-variant player-selection semantics remain unproven and fail-closed.
4. Miner v1.5.13.0 is released through `release/latest.json`. Installed v1.5.12.9 clients must run Check for Updates once more to receive the Research Console build.

Stable package:

- SHA-256 `b70cd294fd45616ecbb5409fb3e790fecce1e20879c5d5ebfb3040553a53b95e`
- Size 30,742,885 bytes.

## Fresh installed-client proof — v1.5.12.8 COMPLETE

Durable evidence note:

- `docs/evidence/installed-client-v1.5.12.8-2026-08-13.md`
- evidence-note commit `ba48ff8ac0219fa494b0a767204e2550d1205c07`.

Uploaded archive identity:

- SHA-256 `59a5164d223931963e4383bfb0cbc5439e2b47b457c7bfdb574f9dba0d3df743`
- 27,291,055 bytes.
- Archive is not stored in Git.
- Miner `reports/validation.json`: PASS.

Fresh compact facts:

- Weapons: **120** = 95 ranged / 25 melee.
- Armor: **23 sets / 133 set pieces / 40 Key Armor / 173 pieces / 865 Tier rows / 865 current recipe rows**.
- Calibrations: **94 current families**, Rare 24 / Epic 35 / Legendary 35, 0 ambiguous, 0 secondary-pool failures.
- Mods: **1,618** families.
- Attachments: **119**, 110 direct localized compatibility texts / 9 unresolved blank-description records.
- Deviations: **98 display-name families / 160 source variants / 60 multi-variant families**.
- Cradles: **120 display-name families / 170 source variants / 32 multi-variant families**.

After the repository fixes below, **all seven fresh compact contracts pass the strict transaction semantics**. The verified local v1.5.12.8 `published/` snapshot was transactionally materialized into all seven production browser payloads and committed together at `857f11f16e3912dea3745d363d1bfcf3f310ed8f` (`Materialize verified v1.5.12.8 database snapshot`).

## 2026-08-13 transactional materialization complete

- Canonical `main` was fast-forwarded to `3e147ca97b773cbede1700fe615dea75c743551c` before repository writes.
- Source snapshot: `C:\Users\mikea\Documents\Dead Signal Miner\published`, produced by Miner v1.5.12.8 at `2026-08-14T00:49:29.620138+00:00`.
- All seven source contract hashes exactly matched `docs/evidence/installed-client-v1.5.12.8-2026-08-13.md`.
- Dry-run validation passed before replacement; the live transaction then replaced Weapons, Armor, Calibrations, Mods, Attachments, Deviations, and Cradles together.
- Production payload commit: `857f11f16e3912dea3745d363d1bfcf3f310ed8f`.
- Validation after materialization: 83 Python site tests PASS; `test-weapon-public-adapter.js` PASS; `git diff --check` PASS.
- Current HEAD before this continuity-only follow-up commit: `857f11f16e3912dea3745d363d1bfcf3f310ed8f`.
- No SSL, DNS, redirect, domain, cPanel hosting configuration, accepted landing-page, Official Once Human X feed, or copy-only deployment changes were made.
- Remaining blockers: exact Armor-to-Build-Lab mapping still needs the legacy runtime pool shape; Mod 2.0 positional consumer semantics remain unproven; Deviation/Cradle multi-variant families remain fail-closed for player selection.
- Database navigation/routes remain `SOON` until each route is genuinely player-ready; materialization alone does not authorize readiness promotion.

## Transaction / ingestion path

The approved final path remains all-seven transactional materialization.

Fresh snapshot exposed and fixed two stale repository gates:

1. `73bde75ff8f28b31853c87e2923a8e89ea557319` — extended materializer accepts current Calibration status `current-system-selected-from-shared-buff-identity-and-proven-main-plus-secondary-rolls`.
2. Weapon rarity is a **maximum Blueprint-Star cap**, not an unconditional exact star count. See Weapons section below.

New helper:

- `9dd7a3a4a8590d2a8ca72e691cf2b1fae4c398d1` — `tools/site/materialize-miner-zip.py` safely accepts a local Miner ZIP, checks archive traversal, extracts to temp, and delegates to the existing all-seven transactional materializer.
- `332a550ed631e0040932c87de8cda0a3ca41e346` — ZIP-helper regressions for traversal rejection and dry-run delegation.

This helper is developer-side only. It does not run on cPanel and does not change copy-only deployment.

The seven production JS payloads are now materially present in the repository together at `857f11f16e3912dea3745d363d1bfcf3f310ed8f`. Future refreshes must continue to use the same all-seven transaction rather than hand-copying categories independently.

## Weapons — gold-standard vertical

Baseline:

- 120 weapons.
- 600 Gear Tier rows.
- 545 Blueprint-Star rows.
- 530 current recipe rows.
- Catalogue/detail/compare/Build Planner handoff implemented.
- Short descriptions remain withheld because installed data reproduces the Kukri/frozen-tilapia localization cross-wire.
- 14 melee recipe series remain unresolved, never “non-craftable.”
- 14 non-Common fixed `WS...` references lack exact backing passive-skill record IDs; never alias similar IDs.

### Blueprint-Star legality correction from v1.5.12.8

Fresh installed-client output disproves the old exact-rarity-count assumption.

Observed distribution:

- Common: 32 × 3★.
- Rare: 25 × 4★.
- Rare: **Metal Baseball Bat × 3★**.
- Epic: 26 × 5★.
- Legendary: 36 × 6★.

For every weapon the mined `progression.blueprint_stars` axis is contiguous `1..N`, `N` is at or below the rarity cap, and every Tier × Star matrix exactly matches that weapon's own source axis.

Landed generic fix — no weapon-specific exception:

- `9efde702380dd456695931de178ac3f47daf66e6` — Python transactional materializer validates source star axis and rarity cap.
- `7e5af6cfabbe6f7a69c07638347883389b0651c8` — browser Weapons guard uses the same rule.
- `ae0b01c2c81a126817dd16d0d5dcda390979ec1d` / `9bb3d28f9fe2e9457ed02addd5ee630bf3278df8` — browser/Python regressions including a Rare 3★ case.
- Site CI `31762139671` SUCCESS.

Minor clarity cleanup still remains: catalogue card `Base Attack` is the default Tier V · 1★ value and should be labeled accordingly. Compare can keep generic Base Attack because Tier/Stars are configurable there.

## Armor & Sets — invariant proven, route prepared

Canonical identity:

- set piece `ds-a-{suit_id}-{blueprint_id}`.
- Key Armor `ds-ka-{blueprint_id}`.

Fresh v1.5.12.8 proof:

- 173 player-facing pieces.
- exactly five unique Tier I-V rows each.
- **865 Tier rows**.
- **865 current recipe rows**.
- all 15 previously missing stat rows recovered.
- Armor data-quality status READY.

Two Blackstone crafting-output conflicts remain explicit:

- Blackstone Boots - Cold T3: stat item `24003303`, suit `1033`; recipe output `24003103`, suit `1031`.
- Blackstone Gloves - Heat T3: stat item `25003203`, suit `1032`; recipe output `25003103`, suit `1031`.

Do not rewrite those recipe outputs as exact variant crafting proof.

Route UX:

- `9b1f5d5c2476c27c92c77b31ea80c189e3504bb8` exposes proven per-Tier HP, Pollution Resist, Psi Intensity, durability, and expandable current recipe evidence.
- The renderer flags recipe output/stat-row ID mismatch rather than silently treating it as exact.
- Site CI `31762251084` SUCCESS.

`database/armor/armor-data.js` now contains the verified v1.5.12.8 contract. Armor remains `SOON` until the route and Build Lab integration are genuinely player-ready.

## Current Calibrations

Proven current system:

- 188 normalized = 94 current + 94 legacy.
- Current compact contract = 94 families.
- Rare 24 / Epic 35 / Legendary 35.
- D0102 Weapon DMG main roll: Rare 18–25%, Epic 26–33%, Legendary 34–50%.
- Exactly one secondary from four mined candidates; each source weight is 200. Do not call 200 a probability percentage.

Secondary ranges:

- Rare: Weakspot 12–18; Crit Rate 8–12; Elemental 12–18; Crit DMG 20–30.
- Epic: Weakspot 15–21; Crit Rate 10–14; Elemental 12–18; Crit DMG 25–35.
- Legendary: Weakspot 18–24; Crit Rate 12–16; Elemental 15–20; Crit DMG 30–40.

Landed:

- `2a48e197...` float-safe projection fix.
- `4b2a614d2760a8248268c6da58e13fa3cff1915e` Build Lab bridge accepts current status.
- `0d2d2ef7d5f0d77449fd84780f89fdb810dfd190` updates stale site regression; CI `31757476809` SUCCESS.
- `743ce215047fa8a279e5f2f242629d4ed21fb244` Calibration route visibly lists all four proven secondary candidates/ranges and raw mined weights without inventing probabilities.
- `73bde75...` transactional materializer status gate fixed from the fresh v1.5.12.8 proof.

## Attachments

Exactly 119 player-selectable weapon-slot records:

- Sight 30.
- Muzzle 36.
- Tactical 36.
- Magazine 17.
- 110 direct localized compatibility texts.
- 9 unresolved blank-description records.

Preserve direct text. Never infer English descriptions into guessed weapon IDs/classes.

## Mod 2.0

Proven progression arithmetic: Levels 1–17 and each row satisfies

`frame_lv_1 + frame_lv_2 + frame_lv_3 + frame_lv_4 = mod_level`.

Direct frame-library join proven:

- normalized Mods carry `frame_code` from `new_mod_property_data.frame`.
- `new_mod_frame_lib_data` is keyed by frame code.
- 1,618 Mods; 32 frame codes used; 37 frame-library records observed; 0 used codes missing; every used frame exposes exactly four ordered sub-entry IDs.
- `87bba600449f3d5096725189d4bd46acee96626c` — machine audit; CI `31756941230` SUCCESS.

Do not claim ordered sub-entry positions correspond to `frame_lv_1..4`. Runtime symbols `get_mod_sub_entry_data` / `get_mod_sub_entry_desc` exist, but consumer internals are not safely proven from the available uploaded artifact.

Build Lab has no canonical Mod mapping yet. Do not add name-only matching.

## Deviations / Cradles

Fresh v1.5.12.8 output proves source-variant canonical IDs are present and valid.

- Deviation variants: `ds-dev-{source_id}`.
- Cradle variants: `ds-cradle-{source_id}`.
- Display-name family remains browse grouping, not player-selectable identity.
- `c727af989ed8181a7ee790475b93b71b0ff157b1` hardens database browser validation and displays canonical variant identity.

Build Lab guard intentionally blocks either category when any display-name family has multiple source variants. Do not auto-pick variant 1.

## Build Lab migration

Canonical bridge currently covers Calibrations, Attachments, Deviations, and Cradles.

Boundaries:

1. Armor has no canonical bridge config; exact mapping must use suit + blueprint identity.
2. Mod 2.0 has no canonical bridge config and remains gated on consumer semantics / exact legacy runtime shape.
3. Deviations/Cradles remain fail-closed while families contain multiple source variants.
4. `preview/build-lab/data/community-data.js` and `preview/build-lab/app.js` are hosting-installed compatibility files, not stored in Git. Do not invent mappings without their runtime pool shape.

## Global shell / readiness

- `3899e37b1109795728947864cb56c79f60af038d` — shell footer shows Miner 1.5.12.8.
- Armor, Mods, Calibrations, Deviations, Cradles remain `SOON` until their routes and integrations are genuinely player-ready; the final payloads are now transactionally materialized.

## Exact next sequence

1. Push materialization commit `857f11f16e3912dea3745d363d1bfcf3f310ed8f` and this continuity follow-up to canonical `origin/main`, then verify site CI.
2. Finish exact Armor → Build Lab mapping once the legacy runtime pool shape is accessible.
3. Continue Mod frame consumer investigation; frame-library join is proven, positional semantics are not.
4. Resolve Deviation/Cradle player-selectable variant semantics only from evidence.
5. Finish canonical Build Lab migration away from stale compatibility pools.
6. Keep database navigation/routes `SOON` until each is genuinely player-ready.
7. Minor Weapons catalogue clarity cleanup: `Base Attack` → `Tier V · 1★ Base Attack`.
8. Only after core functionality is broadly complete, perform a fresh Wikily/OnceHumanDB UX/features audit; never copy their corpus counts.
