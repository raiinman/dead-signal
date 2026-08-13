# Dead Signal — AI Continuity / Handoff

> Canonical current-state handoff. Read this file and `PROJECT-RULES.md` first.
>
> Updated 2026-08-13 during Day Shift after the fresh v1.5.12.3 evidence pass, Miner v1.5.12.4 release, and exact Armor Tier variant-series investigation.

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

## Fresh evidence snapshot

The user's fresh installed-game v1.5.12.3 output is available from the uploaded Miner corpus and repo-root `data.7z` (upload commit `ab78f62e34294a0fda4fadd3aa8d35d81ee59c13`). Do not ask for another v1.5.12.3 run.

Fresh compact counts:

- Weapons: 120 (95 ranged / 25 melee).
- Armor: 23 sets / 133 set pieces / 40 Key Armor / 173 total.
- Mods: 1,618 source families.
- Attachments: 119 player weapon-slot records from 202 raw records.
- Deviations: 98 display-name families / 160 variants.
- Cradles: 120 display-name families / 170 variants.

## Miner v1.5.12.4 — released

Fresh v1.5.12.3 data exposed a Calibration classifier defect. Current/legacy pairing is proven by mined `buff_id`, not broad `group_id`.

Verified result:

- 188 normalized Calibration rows = 94 current + 94 legacy.
- 94 current/legacy `buff_id` pairs; 0 ambiguous families.
- Current rarity counts: Rare 24 / Epic 35 / Legendary 35.
- Current Weapon DMG ranges: Rare 18–25%, Epic 26–33%, Legendary 34–50%; main stat `D0102`.

Release chain:

- `660c47b900551c96f69750527e13a8e6a589d4e5` — fix classifier.
- `99deebe41640398b42da25a6138c6b9a09ca2c03` — regression tests.
- Miner CI `31745827385` — SUCCESS.
- `5586b1a9366a631836520c021ab8f063e861db9e` — bump to v1.5.12.4.
- Release workflow `31746463876` — SUCCESS.
- Updater-manifest commit `8e275eb674d9edece91259bd1294483c47124372`.
- Stable SHA-256 `bffd30911a67a3ba782a3c905b1c73f0a1776b2dc0242354506ef8825d4a9bdd`, size 30,709,406 bytes.

## Weapons — current gold-standard vertical

Fresh counts: 120 weapons, 600 Gear Tier rows, 545 Blueprint-Star rows, 530 current recipes, 76 resolved effects.

Exactly 14 weapons have no Tier I–V recipe evidence, all melee: Broken Bottle, Crowbar, Fine Dagger, Fine Steel Pipe, Machete, Metal Baseball Bat, Military Dagger, Military Shovel, Old Baseball Bat, Old Machete, Rusted Blade, Short Wrench, Steel Pipe, Warning Sign. Classification remains unresolved recipe evidence; never auto-label non-craftable.

Reference-tracer evidence proves 14 non-Common weapons reference fixed `WS...` codes with no exact backing `passive_skill_data.record_id`: `WS1001`, `WS1101`, `WS1301`, `WS1402`, `WS14503`, `WS1501`, `WS15203`, `WS15304`, `WS15502`, `WS1601`, `WS2001`. Do not alias similar-looking IDs without direct evidence. Metal Baseball Bat is the remaining non-Common no-effect record and has no fixed skill code.

Landed: `6a79130d1fa12352a9ea2aaba1e6b57264b9165d` audit, `67438e824b92d81eb01f07e4d4d746aff32c7a37` tests, site CI `31746629170` SUCCESS.

Weapon `short_description` remains withheld. Fresh data reproduces the Kukri/frozen-tilapia cross-wire; do not expose or patch it until localization identity/source precedence is proven.

## Armor & Sets — exact current evidence

Canonical set-piece identity remains `ds-a-{suit_id}-{blueprint_id}`. Blueprint IDs are reused across suits, so `suit_id` is required identity context.

Fresh Armor has 15 pieces missing exactly one canonical Tier stat row. Every gap is recipe-backed, so none may be called non-craftable and no values may be interpolated.

Root cause: malformed/incomplete current `equip_data` records omit canonical-filter fields (`art_lv`, `equip_type`, and/or `equip_lv`) even though player-facing variant identity and exact origin stat records still exist.

### Critical correction: all 15 stat rows are recoverable

The deeper variant-series audit supersedes the earlier intermediate 13/2 conclusion.

For every one of the 15 gaps, current installed-game evidence contains exactly one item that:

- matches the piece's exact `blueprint_no`;
- matches the exact public `suit_id` (or `0` for Key Armor);
- has an item-ID suffix equal to the missing Tier, consistent with all already-published sibling Tiers;
- has a current `equip_origin_data` record;
- has the same origin stat-code schema as its sibling Tiers.

Therefore all **15 missing stat rows are evidence-backed recovery candidates**. No interpolation is required.

### Blackstone crafting identity remains separately unresolved

Two records still have a crafting-output variant conflict, but this does **not** block their stat-row recovery:

- Blackstone Boots - Cold Tier III: exact stat row is `24003303`, suit `1033`; recipe/blueprint-art map output is generic `24003103`, suit `1031`.
- Blackstone Gloves - Heat Tier III: exact stat row is `25003203`, suit `1032`; recipe/blueprint-art map output is generic `25003103`, suit `1031`.

Do not substitute the generic crafting output as the variant's stat row, and do not rewrite the recipe to pretend the output identity is proven. Model stat identity and crafting-output identity independently.

Other examples: Blast Pants Tier I resolves exact stat row `23001401` suit `1005`; Charmed Mag Top Tier II resolves exact stat row `22013102` suit `0`.

Landed Armor evidence tooling:

- `f67d55e6df8af10237131aa9b5f9fb0ba2cbec64` — recipe-vs-stat Tier audit.
- `cb25f8ab06f8d7f7ce07004da7e74069ded40fc9` — tests.
- Site CI `31746486437` — SUCCESS.
- `bdd2421cf5d7db8796d35382c3a6818dd43d774e` — initial exact recovery audit; site CI `31749057850` SUCCESS.
- `ca43077edc5270388f7f132acdfcf580fe432caa` — refined recovery audit separating stat identity from crafting identity. CI run `31749411919` was queued at the time of this handoff update; re-check before relying on it.

A dedicated unit-test file for the refined audit was attempted twice but rejected by the GitHub connector safety classifier. Do not claim that dedicated test is landed.

A proposed Miner helper `tools/miner/src/armor_tier_repair.py` was also rejected by the connector safety classifier before creation. The intended safe rule is now fully specified by the audit: recover only one exact blueprint+suit+Tier-suffix candidate with matching origin stat schema, while preserving recipe-output variant conflicts as diagnostics. Do not weaken the public five-Tier invariant.

## Current Calibrations

The v1.5.12.4 classifier is proven against the v1.5.12.3 normalized corpus to yield 94 current / 94 legacy / 0 ambiguity. Use a v1.5.12.4 compact output for final end-to-end publisher verification; do not hand-edit around the transactional materializer.

## Mod 2.0

`audit-mod-level-progression.py` is tested (`71968d87627ef1dda714dca104cd5d2a710c3d78`). Fresh progression has exactly Levels 1–17 and proves this invariant for every row:

`frame_lv_1 + frame_lv_2 + frame_lv_3 + frame_lv_4 = mod_level`

This proves level encoding only. It does not prove which sub-attribute occupies each frame, assignment order, upgrade behavior, or Shiny semantics. Numeric overlap with compact `mod_code` / `main_entry_code` is zero, so numeric ID matching is not a valid join.

## Attachments

Player-selectable target is proven: Sight 30 / Muzzle 36 / Tactical 36 / Magazine 17 = 119.

Fresh localized installed-game text provides explicit compatibility wording for 109/119. Some rules are model-specific, so broad class inference would lose semantics. Ten records lack equivalent direct compatibility evidence and must remain unresolved until another direct table/consumer proves them. Never infer compatibility from accessory-code names.

## Deviations / Cradles

Deviations: 98 display-name families / 160 variants; 60 families multi-variant. Preserve variants until identity is proven.

Cradles: 120 display-name families / 170 variants; 32 families multi-variant. Same display names can have different IDs, buff IDs, style codes, images, and descriptions. Display name alone is not canonical identity; never auto-select variant #1.

## Build Lab / ingestion

Weapons remain the strongest canonical vertical. Armor/Calibrations/Mods/Attachments/Deviations/Cradles must fail closed when compact contracts are unready or ambiguous. Transactional all-seven materialization remains the accepted ingestion path; do not manually copy individual category payloads around a blocked category.

Hosting-only legacy Build Lab files `preview/build-lab/data/community-data.js` and `preview/build-lab/app.js` are not in Git. Do not invent their mutation contract or remove compatibility pools until canonical replacement is proven.

## Exact next sequence

1. Re-check site CI run `31749411919` for refined Armor recovery audit.
2. Land dedicated regression coverage for the refined Armor audit if connector writes permit.
3. Implement the evidence-gated Armor normalizer/repair rule: recover all 15 exact stat rows, preserve the two Blackstone recipe-output conflicts as unresolved acquisition diagnostics, and target 850 Armor Tier stat rows without weakening invariants.
4. Run Miner CI; only bump/release Miner if the Armor change is proven and an intentional release is warranted.
5. Continue weapon short-description localization-source investigation; keep text withheld until proven.
6. Verify v1.5.12.4 Calibration compact output end-to-end when available; continue repo-side work without waiting where possible.
7. Trace Mod 2.0 `frame_lv_1..4` consumers beyond the proven Level 1–17 arithmetic.
8. Migrate 109 direct-evidence Attachment compatibility rules; leave 10 unresolved.
9. Resolve Deviation/Cradle variant identity.
10. Continue canonical Build Lab migration only after category contracts are proven.
11. Keep unready routes `SOON`.
12. Only after core functionality is broadly complete, audit current Wikily/OnceHumanDB for UX/features and implement safe differentiators.

## Read first

`PROJECT-RULES.md`, fresh Miner output, `tools/miner/VERSION`, `tools/miner/release/latest.json`, `tools/miner/src/extractor/normalize_weapons.py`, `tools/miner/src/extractor/normalize_armor.py`, `tools/miner/src/extractor/publish_current_calibrations.py`, `tools/site/audit-weapon-skill-references.py`, `tools/site/audit-armor-tier-evidence.py`, `tools/site/audit-armor-tier-recovery.py`, `tools/site/audit-mod-level-progression.py`, `tools/site/audit-extended-contracts.py`, `tools/site/materialize-published-snapshot.py`, `preview/build-lab/canonical-category-bridge.js`, `.github/workflows/test-site-tools.yml`, `.cpanel.yml`.
