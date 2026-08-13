# Dead Signal — AI Continuity / Handoff

> Canonical current-state handoff. Read this file and `PROJECT-RULES.md` first.
>
> Updated **2026-08-13 Day Shift** after the fresh v1.5.12.3 evidence pass, Calibration repair, exact Armor Tier recovery implementation, Miner v1.5.12.5 release, and Armor route hardening.

## 1. Non-negotiables

- Repository: `raiinman/dead-signal`.
- Canonical branch: **`main` only** unless the user explicitly asks otherwise.
- Installed-game / Miner evidence outranks guesses and community data.
- Never invent mechanics, recipes, compatibility, proc behavior, DPS, rankings, or multiplier semantics.
- Preserve the accepted landing page and Official Once Human X feed unless a concrete bug exists.
- Preserve one global workstation shell and the shared readability system.
- Static site only; **no WordPress runtime**.
- cPanel deployment remains **copy-only**.
- Do **not** touch DNS, SSL, domain redirects, or cPanel hosting configuration; the user is handling domain/SSL separately in another window.
- Routes that are not genuinely player-ready remain `SOON`.
- Missing recipe evidence never proves non-craftable.
- Competitor UX audit remains last, after the core database and Build Lab are broadly complete.

## 2. Fresh evidence boundary

The user's fresh installed-game **v1.5.12.3** Miner output is available from the uploaded corpus and repo-root `data.7z` (upload commit `ab78f62e34294a0fda4fadd3aa8d35d81ee59c13`). Do not ask for another v1.5.12.3 run.

Fresh compact counts:

- Weapons: **120** (95 ranged / 25 melee).
- Armor: **23 sets / 133 set pieces / 40 Key Armor / 173 total**.
- Mods: **1,618** source families.
- Attachments: **119** true player weapon-slot records from 202 raw rows.
- Deviations: **98 display-name families / 160 variants**.
- Cradles: **120 display-name families / 170 variants**.

The uploaded archive contains normalized/published data plus the reference tracer, but not a complete raw current/base table tree suitable for rerunning every Miner normalizer in this environment. Therefore final v1.5.12.5 Armor output proof still requires a real installed-client Miner run; repository-side work must continue meanwhile.

## 3. Miner v1.5.12.5 — RELEASED

### Calibration repair inherited from v1.5.12.4

Fresh v1.5.12.3 data exposed a current/legacy Calibration classifier defect. Stable pairing is proven by mined `buff_id`, not broad `group_id`.

Verified against the fresh normalized corpus:

- 188 Calibration rows = **94 current + 94 legacy**.
- **94** unique current/legacy `buff_id` pairs.
- **0 ambiguous families**.
- Current rarity counts: Rare 24 / Epic 35 / Legendary 35.
- Current guaranteed Weapon DMG roll: `D0102`.
- Rare **18–25%**, Epic **26–33%**, Legendary **34–50%**.

v1.5.12.4 chain: classifier fix `660c47b900551c96f69750527e13a8e6a589d4e5`; tests `99deebe41640398b42da25a6138c6b9a09ca2c03`; Miner CI `31745827385` SUCCESS; version bump `5586b1a9366a631836520c021ab8f063e861db9e`; release `31746463876` SUCCESS.

### Armor Tier completion added in v1.5.12.5

The old Armor canonical filter legitimately rejected malformed current `equip_data` rows that omit fields such as `art_lv`, `equip_type`, and/or `equip_lv`. Reference-tracer evidence proves the missing player-facing variant rows still exist with exact blueprint, suit, Tier-suffix, and origin-stat identity.

Implemented as a narrow post-normalization completion pass rather than weakening the proven legacy filter:

- `155168ac15e0bce2ab4a1a9370bd94f0f3950e39` — `armor_tier_normalization.py` exact variant-series completion primitives.
- `711f7c7ebdc3a0af3eee097e76294660d606fa0d` — `armor_tier_completion.py` output completion runner.
- `68014ef6a01cc09e0784e638ca19182dde5a3e2e` — canonical `miner_entry.py` runs Armor completion after `normalize_armor` and includes both modules in self-test.
- `7e3149ea81665c5e18d502849ebf20e86bf356de` — Miner regression tests for exact Blackstone variant recovery, preserved recipe conflict, and ambiguity fail-closed behavior.
- Miner CI `31749965302` — SUCCESS, including Windows package and packaged executable self-test.
- `c3c698f5d51ef0777a120540f47fa3c7a8dd005e` — remove stale incomplete-Tier review entries only after exact recovery; preserve real unresolved/conflict diagnostics.
- Miner CI `31750054876` — SUCCESS.
- `c75cb605cbf3dfd9398e97472ebee503cb245978` — intentional VERSION bump to **1.5.12.5**.
- Release workflow `31750247595` — **SUCCESS** through source tests, Windows build, packaged self-test, release creation, public asset re-download verification, and updater-manifest-last publication.
- Updater manifest commit: `fdd8627cf292d981482606317c528983cf2c6cd8`.
- Stable v1.5.12.5 SHA-256: `6df1085b4531bb46569af7ad65e0f9d6086aed2d0eb12040d114fd399a573a45`.
- Stable package size: **30,730,081 bytes**.

Do not claim the real installed-client Armor output is 850 Tier rows until a fresh v1.5.12.5 run proves it. The implementation and packaging are proven; the installed-client result is the remaining evidence gate.

## 4. Weapons — gold-standard vertical

Fresh facts:

- 120 weapons.
- 600 Gear Tier rows.
- 545 Blueprint-Star rows.
- 530 current recipes.
- 76 resolved player-facing effects.
- Weapon browser/detail route already consumes the compact Miner contract through the hardened public adapter.
- Catalogue supports search/type/rarity/sort, grid/list, two-weapon compare, detail handoff, and Build Planner handoff.
- Detail route exposes legal Gear Tier × Blueprint Stars, proven Base Attack trace, raw firearm/handling/distance fields, acquisition evidence, Tier recipe evidence, provenance, and explicit limits.
- Compare applies only proven Tier/Star static data and does not claim configured DPS.
- Missing or unresolved effect text is visibly labeled rather than substituted.

### Recipe gaps

Exactly 14 weapons have no Tier I–V recipe evidence, all melee: Broken Bottle, Crowbar, Fine Dagger, Fine Steel Pipe, Machete, Metal Baseball Bat, Military Dagger, Military Shovel, Old Baseball Bat, Old Machete, Rusted Blade, Short Wrench, Steel Pipe, Warning Sign.

Classification: **recipe evidence unresolved**. Never automatically label these non-craftable.

### Unresolved non-Common effects

Reference-tracer evidence proves 14 non-Common weapons reference fixed `WS...` codes with no exact backing `passive_skill_data.record_id`:

`WS1001`, `WS1101`, `WS1301`, `WS1402`, `WS14503`, `WS1501`, `WS15203`, `WS15304`, `WS15502`, `WS1601`, `WS2001`.

Do not alias similar-looking IDs without direct evidence. Metal Baseball Bat is the remaining non-Common no-effect record and has no fixed skill code.

Audit `6a79130d1fa12352a9ea2aaba1e6b57264b9165d`; tests `67438e824b92d81eb01f07e4d4d746aff32c7a37`; site CI `31746629170` SUCCESS.

### Short-description blocker

`normalize_weapons.py` currently feeds `item.short_desc` through the globally merged shared Translator. The fresh corpus reproduces the Kukri/frozen-tilapia cross-wire. The reference tracer does not index enough localized-string provenance to prove which translation layer supplied the bad value.

Therefore public `short_description` remains intentionally withheld. Correct next Miner direction is **translation provenance / collision diagnostics**, not a Kukri one-off override.

### Minor player-facing clarity gap

Catalogue cards use the default latest Gear Tier / first legal Blueprint-Star cell, which is Tier V · 1★ in the current contract, while the card label still says only `Base Attack`. Detail already labels this correctly as `Tier V · 1★ Base Attack`. Prefer making the catalogue label equally explicit when touching the catalogue next.

## 5. Armor & Sets — current exact model

Canonical set-piece identity is `ds-a-{suit_id}-{blueprint_id}`. Blueprint IDs can be reused across suit variants, so `suit_id` is mandatory identity context.

Fresh v1.5.12.3 Armor has 15 pieces missing exactly one Tier stat row. Every gap has a crafting recipe, so none may be classified non-craftable and no values may be interpolated.

### All 15 missing stat rows are recoverable by exact evidence

For every gap the current installed-game evidence contains exactly one item that:

- matches exact `blueprint_no`;
- matches exact public `suit_id` (or `0` for Key Armor);
- has an item-ID suffix equal to the missing Tier, consistent with every existing sibling Tier;
- has a current `equip_origin_data` record;
- has the exact sibling origin stat-code schema.

The refined evidence audit is `ca43077edc5270388f7f132acdfcf580fe432caa`; site CI `31749411919` — SUCCESS.

### Blackstone crafting identity is a separate unresolved layer

Two stat rows are exact but their recipe/map output points to generic Blackstone suit `1031`:

- Blackstone Boots - Cold T3: exact stat row `24003303`, suit `1033`; recipe output `24003103`, suit `1031`.
- Blackstone Gloves - Heat T3: exact stat row `25003203`, suit `1032`; recipe output `25003103`, suit `1031`.

The v1.5.12.5 completion pass recovers the exact variant stat row but **does not rewrite the recipe output**. It annotates acquisition identity as unresolved output variant and preserves a review diagnostic.

### Player route hardening

- `8abde23312c0c196d2d6d15c50b1b89ae9aff839` — Armor browser now independently fails closed on wrong schema/version, malformed canonical IDs, duplicate identities, parent-suit mismatch, piece-count mismatch, or anything other than exactly five unique Gear Tiers I–V per piece.
- Site CI `31750389515` — SUCCESS.
- `30d816714a06bfa089bca1e8bf2a2fcd7c6918bc` — cache-bust hardened Armor browser JS.

`database/armor/armor-data.js` remains a null placeholder. Do not materialize old v1.5.12.3 Armor into the route. Wait for real v1.5.12.5 output to prove the repaired 850-row invariant, then materialize transactionally.

## 6. Current Calibrations

The corrected classifier is packaged in v1.5.12.5. Repository evidence already proves the 94-current/94-legacy split against the fresh v1.5.12.3 normalized corpus, but final compact end-to-end proof should use a v1.5.12.5 Miner output.

Do not hand-edit around the transactional materializer. Continue repository-side route/bridge safety work while waiting for the next installed-client run.

## 7. Mod 2.0

Existing tested audit commit: `71968d87627ef1dda714dca104cd5d2a710c3d78`.

Fresh progression proves exactly 17 current Mod levels and, for every Level 1–17 row:

`frame_lv_1 + frame_lv_2 + frame_lv_3 + frame_lv_4 = mod_level`

Exact current sequence:

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

Quality mapping in these exact progression rows:

- quality 1 → Levels 1–2
- quality 2 → Levels 3–4
- quality 3 → Levels 5–6
- quality 4 → Levels 7–8
- quality 5 → Levels 9–17

This proves only the literal four-frame level encoding and current level/quality mapping. It does **not** prove which sub-attribute occupies each frame, assignment order, upgrade behavior, or Shiny replacement semantics. Numeric overlap with compact `mod_code` / `main_entry_code` is zero, so numeric ID matching is invalid.

The fresh reference tracer has no direct `frame_lv_1..4` consumer evidence by those field names. Continue consumer tracing before modeling gameplay semantics.

## 8. Attachments

Player-selectable target is proven:

- Sight 30
- Muzzle 36
- Tactical 36
- Magazine 17
- Total **119**

Fresh localized installed-game text provides explicit compatibility wording for **109/119**. Some rules are model-specific, so broad weapon-class inference loses real semantics. Ten records still lack equivalent direct compatibility evidence and remain unresolved.

Never infer compatibility from accessory-code names.

## 9. Deviations / Cradles

Deviations: 98 display-name families / 160 variants; 60 families multi-variant. Preserve variants until identity is proven.

Cradles: 120 display-name families / 170 variants; 32 families multi-variant. Same display name can have different IDs, buff IDs, style codes, images, and descriptions. Display name alone is **not** canonical Cradle identity. Never auto-select variant #1.

## 10. Build Lab / ingestion

Weapons remain the strongest canonical vertical. Armor, Calibrations, Mods, Attachments, Deviations, and Cradles must fail closed when compact contracts are unready or ambiguous.

Transactional all-seven materialization remains the accepted ingestion path; never manually copy one category around a blocked category merely to make a route look populated.

Hosting-only legacy Build Lab files `preview/build-lab/data/community-data.js` and `preview/build-lab/app.js` are not in Git. Do not invent their mutation contract or remove compatibility pools until canonical replacement is proven.

## 11. Exact continuation order

1. Treat Weapons as the gold-standard database vertical; close only remaining real player-facing clarity/integrity gaps and continue short-description provenance investigation without guessing.
2. Ask for/run **v1.5.12.5** installed-client output when appropriate to prove Armor reaches 173 pieces × 5 Tiers = 850 Tier rows and Calibrations publish 94 current families. Do not block unrelated repository work while waiting.
3. When the v1.5.12.5 Armor invariant is proven, materialize Armor transactionally and finish set-centric player detail / Build Lab handoff.
4. Verify current Calibration compact output end-to-end and integrate exact current behavior.
5. Continue Mod 2.0 consumer tracing beyond the proven Level 1–17 frame arithmetic; migrate only proven semantics.
6. Migrate the 109 direct-evidence Attachment compatibility rules; keep 10 unresolved.
7. Resolve Deviation and Cradle variant identity.
8. Finish Build Lab canonical migration category by category; stale compatibility data remains only where exact replacement is not yet proven.
9. Keep unready routes `SOON`.
10. Only after core functionality is broadly complete, audit current Wikily Once Human and OnceHumanDB for UX/features and implement evidence-backed differentiators without copying their corpus counts.

## 12. Read first

`PROJECT-RULES.md`, `tools/miner/VERSION`, `tools/miner/release/latest.json`, `tools/miner/src/miner_entry.py`, `tools/miner/src/extractor/normalize_weapons.py`, `tools/miner/src/extractor/normalize_armor.py`, `tools/miner/src/extractor/armor_tier_normalization.py`, `tools/miner/src/extractor/armor_tier_completion.py`, `tools/miner/src/extractor/publish_current_calibrations.py`, `tools/site/audit-weapon-skill-references.py`, `tools/site/audit-armor-tier-recovery.py`, `tools/site/audit-mod-level-progression.py`, `tools/site/materialize-published-snapshot.py`, `database/weapons/`, `database/armor/`, `preview/build-lab/canonical-category-bridge.js`, `.github/workflows/test-miner.yml`, `.github/workflows/test-site-tools.yml`, `.cpanel.yml`.

### Functional checkpoint before this handoff commit

Latest functional site commit before rewriting this handoff: `30d816714a06bfa089bca1e8bf2a2fcd7c6918bc`.
