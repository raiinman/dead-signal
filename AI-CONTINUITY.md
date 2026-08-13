# Dead Signal — AI Continuity / Handoff

> Canonical current-state handoff. Read this file and `PROJECT-RULES.md` first.
>
> Updated **2026-08-13 Day Shift** after Miner v1.5.12.7, exact Calibration secondary-roll validation, Attachment compatibility provenance migration, and archived Mod frame-arithmetic proof.

## 1. Non-negotiables

- Repository: `raiinman/dead-signal`; canonical branch: **`main` only** unless the user explicitly asks otherwise.
- Installed-game / Miner evidence outranks guesses and community data.
- Never invent mechanics, recipes, compatibility, proc behavior, DPS, rankings, multiplier semantics, variant identity, or crafting identity.
- Missing recipe evidence never proves non-craftable.
- Preserve the accepted landing page, Official Once Human X feed, global workstation shell, and readability system unless a concrete bug exists.
- Static site only; **no WordPress runtime**.
- cPanel deployment remains **copy-only**. Do not touch DNS, SSL, redirects, or cPanel hosting configuration.
- Routes that are not genuinely player-ready remain `SOON`.
- Transactional all-seven materialization remains the accepted ingestion path; never manually copy one category around a blocked category.
- Competitor UX audit remains last, after the core database and Build Lab are broadly complete.

## 2. Fresh evidence boundary

The user's fresh installed-game **v1.5.12.3** Miner output is archived at repo-root `data.7z` (upload commit `ab78f62e34294a0fda4fadd3aa8d35d81ee59c13`). Do not ask for another v1.5.12.3 run.

Fresh compact counts:

- Weapons: **120** (95 ranged / 25 melee).
- Armor: **23 sets / 133 set pieces / 40 Key Armor / 173 total**.
- Mods: **1,618** source families.
- Attachments: **119** true player weapon-slot records.
- Deviations: **98 display-name families / 160 variants**.
- Cradles: **120 display-name families / 170 variants**.

GitHub Actions may be used as a temporary microscope against `data.7z` when connector file-byte access is unavailable. Remove temporary research workflows after evidence is captured.

## 3. Current Miner stable — v1.5.12.7 RELEASED

Release workflow `31752859782` completed **SUCCESS** through source tests, Windows build, packaged self-test, public release verification, and updater-manifest-last publication.

Current stable manifest:

- Version: **1.5.12.7**.
- SHA-256: `e409642e3f78917f39fc46c677d5d92fdbdb40e987f8c08fa71c8ec7253732d7`.
- Size: **30,740,972 bytes**.
- VERSION bump commit: `f12150f8035a6190d0d5408149d90c65e18521e6`.

Release history relevant to current contracts:

- **v1.5.12.5** — Armor Tier exact recovery. SHA `6df1085b4531bb46569af7ad65e0f9d6086aed2d0eb12040d114fd399a573a45`, 30,730,081 bytes.
- **v1.5.12.6** — Calibration main + secondary-roll proof. SHA `62a3045743d0a2c018739db95903644ce2d883de1b695a411fad486a257e54df`, 30,737,714 bytes.
- **v1.5.12.7** — Attachment direct compatibility provenance contract v2.

## 4. Weapons — gold-standard vertical

Fresh facts:

- 120 weapons, 600 Gear Tier rows, 545 Blueprint-Star rows, 530 current recipes, 76 resolved effects.
- Browser/detail already use the hardened Miner-derived contract.
- Catalogue has search/type/rarity/sort, grid/list, compare, detail, and Build Planner handoff.
- Detail exposes legal Gear Tier × Blueprint Stars, proven Base Attack trace, firearm/handling/distance fields, acquisition, Tier recipe evidence, provenance, and explicit limits.
- Compare applies only proven static Tier/Star data; it does not claim configured DPS.

Exactly 14 weapons have no Tier I–V recipe evidence, all melee: Broken Bottle, Crowbar, Fine Dagger, Fine Steel Pipe, Machete, Metal Baseball Bat, Military Dagger, Military Shovel, Old Baseball Bat, Old Machete, Rusted Blade, Short Wrench, Steel Pipe, Warning Sign. Classification remains **recipe evidence unresolved**, not non-craftable.

Reference-tracer evidence proves 14 non-Common weapons reference fixed `WS...` codes with no exact backing `passive_skill_data.record_id`: `WS1001`, `WS1101`, `WS1301`, `WS1402`, `WS14503`, `WS1501`, `WS15203`, `WS15304`, `WS15502`, `WS1601`, `WS2001`. Do not alias similar-looking IDs. Metal Baseball Bat is the remaining non-Common no-effect record and has no fixed skill code.

Weapon `short_description` remains withheld. Fresh data reproduces the Kukri/frozen-tilapia cross-wire, and the tracer does not expose enough localization-source provenance to prove a repair. Correct direction is translation provenance/collision diagnostics, not a one-off override.

Minor clarity gap: catalogue card `Base Attack` is the latest Tier / first legal star cell, currently Tier V · 1★. Detail labels this correctly; catalogue should eventually say `Tier V · 1★ Base Attack` or equivalent.

## 5. Armor & Sets — exact recovery implemented, real-client proof still required

Canonical set-piece identity is `ds-a-{suit_id}-{blueprint_id}`. Blueprint IDs are reused across suits, so `suit_id` is mandatory identity context.

Fresh v1.5.12.3 Armor has 15 pieces missing exactly one Tier stat row. Every gap is recipe-backed; no row may be interpolated or called non-craftable.

Every missing stat row has exactly one evidence-backed recovery candidate matching:

- exact `blueprint_no`;
- exact public `suit_id` (or `0` for Key Armor);
- missing Tier item-ID suffix consistent with sibling Tiers;
- current `equip_origin_data`;
- exact sibling origin stat-code schema.

Implementation chain:

- `155168ac15e0bce2ab4a1a9370bd94f0f3950e39` — exact variant-series primitives.
- `711f7c7ebdc3a0af3eee097e76294660d606fa0d` — completion runner.
- `68014ef6a01cc09e0784e638ca19182dde5a3e2e` — `miner_entry.py` integration/self-test.
- `7e3149ea81665c5e18d502849ebf20e86bf356de` — regressions.
- Miner CI `31749965302` SUCCESS.
- `c3c698f5d51ef0777a120540f47fa3c7a8dd005e` — clean only recovered stale review entries.
- Miner CI `31750054876` SUCCESS.

Two Blackstone crafting-output conflicts remain deliberately separate from stat identity:

- Blackstone Boots - Cold T3: exact stat row `24003303`, suit `1033`; recipe output `24003103`, suit `1031`.
- Blackstone Gloves - Heat T3: exact stat row `25003203`, suit `1032`; recipe output `25003103`, suit `1031`.

Do not rewrite those recipe outputs as if variant crafting identity were proven.

Armor browser independently fails closed on malformed canonical IDs, duplicate identity, suit mismatch, count mismatch, or anything other than five unique Tiers I–V. `database/armor/armor-data.js` remains a null placeholder. A real installed-client run on v1.5.12.5 or later is still required to prove the expected **173 × 5 = 850 Tier rows** before materialization.

## 6. Current Calibrations — main + secondary pool proven and released

Current/legacy pairing is proven by mined `buff_id`, not broad `group_id`:

- 188 normalized rows = **94 current + 94 legacy**.
- 94 shared `buff_id` identities.
- 0 ambiguous families.
- Current rarity counts: Rare 24 / Epic 35 / Legendary 35.

Guaranteed main roll:

- stat `D0102` / Weapon DMG.
- Rare **18–25%**.
- Epic **26–33%**.
- Legendary **34–50%**.

Fresh normalized evidence also proves every current record has exactly four secondary candidates with equal mined source weights `[200,200,200,200]`. Preserve those weights; do **not** claim they are percentages unless separately proven.

Exact secondary candidates/ranges:

- Rare: Weakspot DMG 12–18%; Crit Rate 8–12%; Elemental DMG 12–18%; Crit DMG 20–30%.
- Epic: Weakspot DMG 15–21%; Crit Rate 10–14%; Elemental DMG 12–18%; Crit DMG 25–35%.
- Legendary: Weakspot DMG 18–24%; Crit Rate 12–16%; Elemental DMG 15–20%; Crit DMG 30–40%.

Important commits/CIs:

- `093fde74021481817880751a5eac2268cd4a1197` — current projector requires proven main + secondary pool.
- `debdb5678d807d81fa49bcf59f9c2efb5d90b273` — generic compact publisher preserves `affix_ids_weight`.
- `eaa6342deb559dbac0869fbad3b23c16506bb978` — old function-style tests converted to real `unittest` execution; covers 94-family regrouping, ambiguity blocking, exact rarity ranges, secondary pool, and compact weight preservation.
- Miner CI `31752058808` SUCCESS.
- v1.5.12.6 release SUCCESS.
- `987624894a367cf9f2a529759bf7bed64f2c6ecc` — static materializer updated for the current Calibration variant-status string and secondary-pool invariants; site CI `31752598468` SUCCESS.

Player-route enhancement to visibly list the four secondary candidates was attempted but connector-blocked. Do not claim it landed. Current data contract/materializer are ready; route still emphasizes the main Weapon DMG roll.

## 7. Attachments — direct compatibility provenance migrated

Player-selectable target remains:

- Sight 30.
- Muzzle 36.
- Tactical 36.
- Magazine 17.
- Total **119**.

### Critical corrected count

A GitHub Actions audit against archived `data.7z` superseded the old 109/10 handoff count:

- **110 / 119** have direct localized installed-game compatibility wording.
- **9 / 119** are unresolved because their description is blank.
- **0 / 119** have populated coded `compatible_weapon_types` arrays in this archived compact contract.

These are not contradictory facts. Direct localized wording is evidence; coded compatibility arrays are a separate absent data path.

The exact nine unresolved records are:

1. Forward Compensator — `ds-att-220_acp_cmpn_01` — Muzzle.
2. Medium-Caliber suppressor — `ds-att-220_556_sup_01` — Muzzle.
3. Angled Grip — `ds-att-320_sla_grip_01` — Tactical.
4. Light Front Guard Grip — `ds-att-320_grip_uvg_01` — Tactical.
5. Light Vertical Grip — `ds-att-320_lsm_grip_01` — Tactical.
6. Modular Laser Sight — `ds-att-320_mawl_laser_01` — Tactical.
7. One-piece Front Grip — `ds-att-320_cqb_grip_01` — Tactical.
8. Small Triangle Grip — `ds-att-320_tri_grip_02` — Tactical.
9. Small Vertical Grip — `ds-att-320_smv_grip_01` — Tactical.

Direct wording includes broad class rules and model-specific rules such as KAM-rarity conditions and named weapon series. **Never convert these English phrases into guessed weapon IDs or broad class codes. Preserve them verbatim.**

Landed implementation:

- `attachment_compatibility.py` extracts only direct `Can be equipped on ...` / `fits all ...` wording or returns unresolved.
- `54ccb7c2d64efb98d9f3753e73b23d7459b5d144` — Attachment compact contract upgraded to schema v2 with per-row `compatibility_evidence`, direct/unresolved counts, and explicit no-inference policy.
- Miner CI `31752483572` SUCCESS including Windows package/self-test.
- `0d2bc007dfa32cf10b97c35cfe27ad2e7e135712` — executable parser regressions folded into existing Miner `unittest`; job `94621795027` SUCCESS through package/self-test.
- `987624894a367cf9f2a529759bf7bed64f2c6ecc` — site materializer validates Attachment schema v2 evidence statuses/text/counts.
- `1b0acec85da6dcc2c12e0b6b5852adb4c8d21cc5` — shared player renderer displays direct compatibility text or explicit unresolved status and rejects old Attachment schema v1; site CI `31752662291` SUCCESS.
- `07ec050b11a2dbec2c55cc3c56a42c66447bfa90` — dedicated provenance audit separating localized text from coded compatibility.
- `3eda176e829000323bf46e20cb7cd98d87e74dc6` — provenance audit tests; site CI `31752801116` SUCCESS.
- v1.5.12.7 release `31752859782` SUCCESS.

Two cache-bust/explanatory edits to `database/attachments/index.html` were connector-blocked. The renderer JS is landed; do not claim the route HTML cache-bust landed.

## 8. Mod 2.0 — arithmetic proven, semantic consumer absent from current archive

The current Mod progression has exactly Levels **1–17** and proves for every row:

`frame_lv_1 + frame_lv_2 + frame_lv_3 + frame_lv_4 = mod_level`

Exact sequence remains:

- L1 `[1,0,0,0]`
- L2 `[1,1,0,0]`
- L3 `[1,1,1,0]`
- L4 `[1,1,1,1]`
- L5 `[2,1,1,1]`
- L6 `[2,2,1,1]`
- L7 `[2,2,2,1]`
- L8 `[2,2,2,2]`
- L9 `[3,2,2,2]`
- L10 `[3,3,2,2]`
- L11 `[3,3,3,2]`
- L12 `[4,3,3,2]`
- L13 `[4,4,3,2]`
- L14 `[4,4,4,2]`
- L15 `[5,4,4,2]`
- L16 `[5,5,4,2]`
- L17 `[5,5,5,2]`

Landed machine enforcement:

- `0f2f09bac5e5de84624aadab016672983e29a3a7` — `audit-mod-frame-arithmetic.py`.
- `0738cafdebaed5b4e9f7d331d4ac280af323d2f9` — tests; site CI `31752913019` SUCCESS.
- Archived-corpus research job `94622422583` ran the audit and returned `ready: true`, Levels 1–17, zero problems.

The same archived-corpus scan found each of `frame_lv_1`, `frame_lv_2`, `frame_lv_3`, `frame_lv_4` **only in `data/progression.json`, exactly 17 occurrences each, and nowhere else in the archived Miner output**.

Therefore the current archive has no direct consumer evidence that identifies frame-to-sub-attribute assignment. Do not infer frame meaning, assignment order, upgrade behavior, or Shiny semantics from the progression sequence. A new table/consumer extraction is required for that semantic step.

Temporary Mod research workflow was removed at commit `6761403607618cf0284491234b07a0d606d80cf5`.

## 9. Deviations / Cradles — next identity problem

Deviations:

- 98 display-name families / 160 variants.
- 60 families are multi-variant.

Cradles:

- 120 display-name families / 170 variants.
- 32 families are multi-variant.
- Same display names can carry different IDs, buff IDs, style codes, images, descriptions, and other source identity.

Display name alone is **not** canonical variant identity for either category. Never auto-select variant #1.

Before changing these contracts or Build Lab behavior, inspect `preview/build-lab/canonical-category-variant-guard.js` and `canonical-category-bridge.js` to verify current fail-closed behavior. Then audit whether any exact fields partition variants into player-selectable/current-state identities; preserve all variants where that cannot be proven.

## 10. Build Lab / ingestion

Weapons remain the strongest canonical vertical. Armor, Calibrations, Mods, Attachments, Deviations, and Cradles must fail closed when contracts are unready or ambiguous.

Hosting-only legacy Build Lab files `preview/build-lab/data/community-data.js` and `preview/build-lab/app.js` are not in Git. Do not invent their mutation contract or remove compatibility pools until canonical replacement is proven.

Current shared variant guard is expected to block multi-variant Deviation/Cradle families; verify this before any migration work.

## 11. Exact continuation order

1. Inspect Build Lab Deviation/Cradle variant guard and bridge; verify no `variant[0]` auto-selection exists.
2. Audit archived Deviation variants for exact identity discriminators beyond display name; preserve unresolved variants.
3. Audit archived Cradle variants for exact identity discriminators beyond display name; preserve unresolved variants.
4. Continue Build Lab canonical migration only where a category has a proven player-selectable identity/contract.
5. For Mod 2.0, stop semantic modeling at frame arithmetic until a new direct consumer/table is extracted.
6. When convenient, run current Miner **v1.5.12.7** on the installed client. This single fresh output can prove Armor 850 Tier rows, Calibration 94 current families + secondary pools, and Attachment 110/9 provenance end-to-end. Do not block repo-side work while waiting.
7. Keep Weapon short descriptions withheld until localization provenance is proven.
8. Keep unready routes `SOON`.
9. Only after core functionality is broadly complete, audit current competitors for UX/features and implement evidence-backed differentiators.

## 12. Read first

`PROJECT-RULES.md`, `tools/miner/VERSION`, `tools/miner/release/latest.json`, `tools/miner/src/miner_entry.py`, `tools/miner/src/extractor/normalize_weapons.py`, `tools/miner/src/extractor/normalize_armor.py`, `tools/miner/src/extractor/armor_tier_normalization.py`, `tools/miner/src/extractor/armor_tier_completion.py`, `tools/miner/src/extractor/publish_current_calibrations.py`, `tools/miner/src/extractor/publish_extended_web_data.py`, `tools/miner/src/extractor/attachment_compatibility.py`, `tools/site/materialize-extended-contract.py`, `tools/site/audit-attachment-compatibility.py`, `tools/site/audit-mod-frame-arithmetic.py`, `database/extended-catalogue.js`, `preview/build-lab/canonical-category-variant-guard.js`, `preview/build-lab/canonical-category-bridge.js`, `.github/workflows/test-site-tools.yml`, `.cpanel.yml`.
