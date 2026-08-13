# Dead Signal — AI Continuity / Handoff

> Canonical current-state handoff. Read this file and `PROJECT-RULES.md` first.
>
> Updated 2026-08-13 during Day Shift after fresh v1.5.12.3 evidence review, Miner v1.5.12.4 release, and Armor Tier recovery/variant investigation.

## Non-negotiables

- Repo `raiinman/dead-signal`; canonical branch `main` only.
- Installed-game/Miner evidence outranks guesses and community data.
- Never invent mechanics, recipes, compatibility, proc behavior, DPS, rankings, or multiplier semantics.
- Preserve the accepted landing page, Official Once Human X feed, global workstation shell, and readability system unless a concrete bug exists.
- Static site only; no WordPress runtime.
- cPanel deployment remains copy-only. Do not touch DNS/SSL/cPanel hosting configuration; the user is handling domain/SSL separately.
- Unready routes remain `SOON`.
- Missing recipe evidence never proves non-craftable.
- Competitor UX audit remains last, after the core database/Build Lab is broadly complete.

## Current main / fresh evidence

Fresh installed-game v1.5.12.3 evidence is available from the user's uploaded Miner output and repo-root `data.7z` (upload commit `ab78f62e34294a0fda4fadd3aa8d35d81ee59c13`). Do not ask for another v1.5.12.3 run.

Fresh compact counts:

- Weapons: 120.
- Armor: 23 sets / 133 set pieces / 40 Key Armor / 173 total.
- Mods: 1,618 mod-code source families.
- Attachments: 119 player weapon-slot records from 202 raw records.
- Deviations: 98 display-name families / 160 source variants.
- Cradles: 120 display-name families / 170 source variants.

## Miner v1.5.12.4 — released

Fresh v1.5.12.3 data exposed a Calibration classifier defect. Current/legacy pairing is proven by mined `buff_id`, not broad `group_id`.

Verified result after the fix:

- 188 normalized Calibration rows = 94 current + 94 legacy.
- 94 unique current/legacy `buff_id` pairs.
- 0 ambiguous families.
- Current rarity counts: Rare 24 / Epic 35 / Legendary 35.
- Current Weapon DMG ranges remain Rare 18–25%, Epic 26–33%, Legendary 34–50%; main stat `D0102`.

Landed/released:

- `660c47b900551c96f69750527e13a8e6a589d4e5` — fix current Calibration family classification.
- `99deebe41640398b42da25a6138c6b9a09ca2c03` — regression tests.
- Miner CI `31745827385` — SUCCESS.
- `5586b1a9366a631836520c021ab8f063e861db9e` — bump Miner to v1.5.12.4.
- Release workflow `31746463876` — SUCCESS.
- Updater-manifest commit `8e275eb674d9edece91259bd1294483c47124372`.
- Stable v1.5.12.4 SHA-256 `bffd30911a67a3ba782a3c905b1c73f0a1776b2dc0242354506ef8825d4a9bdd`, size 30,709,406 bytes.

## Weapons — current gold-standard vertical

Fresh counts remain 120 weapons (95 ranged / 25 melee), 600 Gear Tier rows, 545 Blueprint-Star rows, 530 current recipes, 76 resolved effects.

### Recipe evidence

Exactly 14 weapons have no recipe for any Tier I–V, all melee: Broken Bottle, Crowbar, Fine Dagger, Fine Steel Pipe, Machete, Metal Baseball Bat, Military Dagger, Military Shovel, Old Baseball Bat, Old Machete, Rusted Blade, Short Wrench, Steel Pipe, Warning Sign.

Classification remains unresolved recipe evidence, never automatically non-craftable.

### Unresolved effects

Reference-tracer evidence proves 14 non-Common weapons reference exact fixed `WS...` skill codes in Blueprint progression that have no exact backing `record_id` in `passive_skill_data`:

`WS1001`, `WS1101`, `WS1301`, `WS1402`, `WS14503`, `WS1501`, `WS15203`, `WS15304`, `WS15502`, `WS1601`, `WS2001`.

Do not map them to similar-looking IDs without direct alias/consumer evidence. `Metal Baseball Bat` is the remaining non-Common no-effect record and has no fixed skill code.

Landed deterministic tracer audit:

- `6a79130d1fa12352a9ea2aaba1e6b57264b9165d` — `audit-weapon-skill-references.py`.
- `67438e824b92d81eb01f07e4d4d746aff32c7a37` — tests.
- Site CI `31746629170` — SUCCESS.

Weapon `short_description` stays withheld. Fresh normalized data reproduces the Kukri/frozen-fish cross-wire, so do not expose or patch around it until localization identity/source precedence is proven.

## Armor & Sets — current exact evidence

Canonical public set-piece identity remains `ds-a-{suit_id}-{blueprint_id}`. Fresh data proves Blueprint IDs can be reused across suit variants, so `suit_id` is required player-facing identity context.

Fifteen Armor records are missing one Tier stat row. Every gap has a current Tier crafting recipe with an explicit output item ID, so none may be classified as non-craftable and no stats may be interpolated.

The root cause is now narrowed: malformed/incomplete `equip_data` rows omit fields required by `normalize_armor.py`'s canonical filter (`art_lv`, `equip_type`, and/or `equip_lv`) even though the item, blueprint, recipe output, and origin-stat record exist.

Fresh reference-tracer + compact Armor evidence proves two different classes:

1. **13 of 15 gaps are exact-recovery candidates.** The recipe output item, `blueprint_art_to_equip_map` `(blueprint_id, tier)` mapping, equip `blueprint_no`, expected set/key `suit_id`, and `equip_origin_data` record all agree.
2. **2 of 15 gaps are Blackstone variant conflicts and must remain blocked.** `Blackstone Boots - Cold` Tier III (`suit_id` 1033) and `Blackstone Gloves - Heat` Tier III (`suit_id` 1032) resolve through recipe/map to generic Blackstone suit `1031`. A matching blueprint is not sufficient to substitute the generic item into those player-facing variants.

Examples:

- Blast Pants Tier I: blueprint `23301401` → recipe/map output `23001401`; equip suit `1005`; exact recovery evidence agrees.
- Charmed Mag Top Tier II: blueprint `22313101` → recipe/map output `22013102`; key-armor suit `0`; exact recovery evidence agrees.
- Blackstone Boots - Cold Tier III: blueprint `24303101` → recipe/map output `24003103`; mapped equip suit is `1031`, not Cold suit `1033`; block as variant conflict.
- Blackstone Gloves - Heat Tier III: blueprint `25303101` → recipe/map output `25003103`; mapped equip suit is `1031`, not Heat suit `1032`; block as variant conflict.

Landed earlier:

- `f67d55e6df8af10237131aa9b5f9fb0ba2cbec64` — `audit-armor-tier-evidence.py`.
- `cb25f8ab06f8d7f7ce07004da7e74069ded40fc9` — tests.
- Site CI `31746486437` — SUCCESS.

New Day Shift audit:

- `bdd2421cf5d7db8796d35382c3a6818dd43d774e` — `tools/site/audit-armor-tier-recovery.py`.
- The audit requires recipe output + exact blueprint-art map + equip blueprint + expected suit/key identity + origin stat record before classifying a missing Tier as `recoverable-exact-game-evidence`.
- Variant mismatch is classified `blocked-armor-variant-conflict`.
- Two attempts to add its unit-test file were rejected by the GitHub connector safety classifier. Do not claim the test is landed until a later session successfully writes/runs it.

Armor remains `SOON` until the normalizer safely recovers the 13 exact rows and separately resolves (or explicitly preserves) the two Blackstone variant gaps. Do not weaken the five-Tier public materializer merely to publish around those two gaps.

## Current Calibrations

The fixed v1.5.12.4 classifier is proven on the v1.5.12.3 normalized corpus to produce 94 current families / 94 legacy review rows / 0 ambiguity. Use v1.5.12.4 for the next compact Miner output; do not hand-edit around the transactional materializer.

## Mod 2.0

`audit-mod-level-progression.py` is tested (`71968d87627ef1dda714dca104cd5d2a710c3d78`). Fresh progression has exactly 17 `mod_level` rows, Levels 1–17.

Proven arithmetic invariant:

`frame_lv_1 + frame_lv_2 + frame_lv_3 + frame_lv_4 = mod_level`

for every Level 1–17 row. This proves the level encoding only. It does not prove which sub-attribute occupies each frame, assignment order, upgrade behavior, or Shiny semantics. There is zero numeric overlap with compact `mod_code` or `main_entry_code`; numeric ID matching is not a valid join.

## Attachments

Fresh player-selectable target is confirmed: Sight 30 / Muzzle 36 / Tactical 36 / Magazine 17 = 119.

Fresh localized installed-game evidence provides explicit compatibility wording for 109/119 records. Some rules are model-specific, so broad weapon-class inference would lose real semantics. Ten records still lack equivalent direct compatibility evidence and must remain unresolved until another table/consumer proves them.

Do not invent compatibility from accessory-code names.

## Deviations / Cradles

Deviations: 98 display-name families / 160 variants; 60 families are multi-variant. Preserve variants until identity is proven.

Cradles: 120 display-name families / 170 variants; 32 families are multi-variant. Same display names can contain materially different record IDs, buff IDs, style codes, images, and descriptions. Display name alone is not safe canonical Cradle identity. Do not auto-select variant #1.

## Build Lab / ingestion

Weapons remain the strongest canonical vertical. Armor/Calibrations/Mods/Attachments/Deviations/Cradles must fail closed when their compact contract is unready or ambiguous. Transactional all-seven materialization remains the accepted ingestion path; do not manually copy individual category payloads to bypass a blocked category.

Hosting-only legacy Build Lab files `preview/build-lab/data/community-data.js` and `preview/build-lab/app.js` are not in Git. Do not invent their mutation contract or remove compatibility pools until canonical end-to-end replacement is proven.

## Exact next sequence

1. Land/run regression coverage for `audit-armor-tier-recovery.py` if connector writes permit it.
2. Modify `normalize_armor.py` with an evidence-gated fallback that recovers only the 13 exact Tier rows. The fallback must require recipe output + `blueprint_art_to_equip_map` + blueprint identity + expected suit/key identity + origin stat row. Do not recover the two Blackstone variant conflicts through generic suit `1031`.
3. Re-run Armor normalization/integrity. Target: recover the 13 exact rows while keeping Blackstone conflicts explicit; do not relax public five-Tier invariants unless a separate product decision is made.
4. Continue source-specific weapon short-description localization investigation; keep descriptions withheld until proven.
5. Verify v1.5.12.4 Calibration compact output end-to-end when available; repository-side work should continue without waiting where possible.
6. Prove Mod 2.0 `frame_lv_1..4` consumer semantics beyond the already-proven Level 1–17 sum invariant.
7. Migrate the 109 direct-evidence Attachment compatibility rules; leave the remaining 10 unresolved.
8. Resolve Deviation and Cradle variant identity, especially Cradles where display-name grouping is demonstrably unsafe.
9. Continue Build Lab canonical migration only after each category contract is proven.
10. Keep unready routes `SOON`.
11. Only after core functionality is broadly complete, audit current Wikily and OnceHumanDB for UX/features and implement evidence-backed differentiators.

## Read first

`PROJECT-RULES.md`, fresh Miner output, `tools/miner/VERSION`, `tools/miner/release/latest.json`, `tools/miner/src/extractor/normalize_weapons.py`, `tools/miner/src/extractor/normalize_armor.py`, `tools/miner/src/extractor/publish_current_calibrations.py`, `tools/site/audit-weapon-skill-references.py`, `tools/site/audit-armor-tier-evidence.py`, `tools/site/audit-armor-tier-recovery.py`, `tools/site/audit-mod-level-progression.py`, `tools/site/audit-extended-contracts.py`, `tools/site/materialize-published-snapshot.py`, `preview/build-lab/canonical-category-bridge.js`, `.github/workflows/test-site-tools.yml`, `.cpanel.yml`.
