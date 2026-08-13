# Dead Signal — AI Continuity / Handoff

> Canonical current-state handoff. Read this file and `PROJECT-RULES.md` first.
>
> Updated 2026-08-13 after the fresh v1.5.12.3 mine was inspected and Miner v1.5.12.4 was released.

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

Latest functional HEAD before this continuity commit: `67438e824b92d81eb01f07e4d4d746aff32c7a37` (`Test weapon skill reference audit`).

The user's fresh installed-game v1.5.12.3 output is repo-root `data.7z`, upload commit `ab78f62e34294a0fda4fadd3aa8d35d81ee59c13`. It extracted successfully and contains `web/`, `data/`, `reports/`, and `indexes/reference-tracer.sqlite`. Do not ask for another v1.5.12.3 run.

Fresh compact counts:

- Weapons: 120.
- Armor: 23 sets / 133 set pieces / 40 Key Armor / 173 total.
- Mods: 1,618 mod-code source families.
- Attachments: 119 player weapon-slot records from 202 raw records.
- Deviations: 98 display-name families / 160 source variants.
- Cradles: 120 display-name families / 170 source variants.

## Miner v1.5.12.4 — released

Fresh v1.5.12.3 data exposed a Calibration classifier defect. The old compact publisher grouped current/legacy records by broad `group_id`. Fresh normalized evidence proves the stable pair identity is the mined `buff_id` pair:

- 188 normalized rows = 94 current + 94 legacy;
- exactly 94 unique `buff_id` pairs;
- each pair has exactly one current and one legacy row;
- current rarity counts remain Rare 24 / Epic 35 / Legendary 35;
- Weapon DMG ranges remain Rare 18–25%, Epic 26–33%, Legendary 34–50%; main stat `D0102`.

Landed:

- `660c47b900551c96f69750527e13a8e6a589d4e5` — fix current Calibration family classification.
- `99deebe41640398b42da25a6138c6b9a09ca2c03` — regression tests.
- Miner CI `31745827385` — SUCCESS.
- `5586b1a9366a631836520c021ab8f063e861db9e` — bump Miner to v1.5.12.4.
- Release workflow `31746463876` — SUCCESS.
- Updater-manifest commit `8e275eb674d9edece91259bd1294483c47124372`.

Stable v1.5.12.4 manifest: SHA-256 `bffd30911a67a3ba782a3c905b1c73f0a1776b2dc0242354506ef8825d4a9bdd`, size 30,709,406 bytes.

The release change is intentionally limited to Calibration classification.

## Weapons — current gold-standard vertical

Fresh counts remain 120 weapons (95 ranged / 25 melee), 600 Gear Tier rows, 545 Blueprint-Star rows, 530 current recipes, 76 resolved effects.

### Recipe evidence

Exactly 14 weapons have no recipe for any Tier I–V, all melee: Broken Bottle, Crowbar, Fine Dagger, Fine Steel Pipe, Machete, Metal Baseball Bat, Military Dagger, Military Shovel, Old Baseball Bat, Old Machete, Rusted Blade, Short Wrench, Steel Pipe, Warning Sign.

Classification remains unresolved recipe evidence, never automatically non-craftable.

### Unresolved effects

Reference-tracer evidence now proves 14 non-Common weapons reference exact fixed `WS...` skill codes in Blueprint progression that have no exact backing `record_id` in `passive_skill_data`. The dangling codes are:

`WS1001`, `WS1101`, `WS1301`, `WS1402`, `WS14503`, `WS1501`, `WS15203`, `WS15304`, `WS15502`, `WS1601`, `WS2001`.

Do not map them to similar-looking IDs without direct alias/consumer evidence. `Metal Baseball Bat` is the remaining non-Common no-effect record and has no fixed skill code.

Landed deterministic tracer audit:

- `6a79130d1fa12352a9ea2aaba1e6b57264b9165d` — `audit-weapon-skill-references.py`.
- `67438e824b92d81eb01f07e4d4d746aff32c7a37` — tests.
- Site CI `31746629170` — SUCCESS.

Weapon `short_description` stays withheld. Fresh normalized data reproduces the Kukri/frozen-fish cross-wire, so do not expose or patch around it until localization identity/source precedence is proven.

## Armor & Sets — still blocked

Canonical public set-piece identity remains `ds-a-{suit_id}-{blueprint_id}`. Fresh data proves 11 Blueprint IDs are reused across multiple suits, so `suit_id` is required identity context.

Fifteen Armor records are missing one Tier stat row. Every gap is backed by a Tier crafting recipe with an explicit output item ID, so the correct classification is `crafting-output-present-stat-row-missing`. Do not synthesize/interpolate stats and do not call these non-craftable.

Landed:

- `f67d55e6df8af10237131aa9b5f9fb0ba2cbec64` — `audit-armor-tier-evidence.py`.
- `cb25f8ab06f8d7f7ce07004da7e74069ded40fc9` — tests.
- Initial site CI `31746486437` — SUCCESS.

Armor remains `SOON` until exact Tier I–V stat evidence is recovered.

## Current Calibrations

The fixed classifier was replayed against the v1.5.12.3 normalized rows and yields exactly 94 current families / 94 legacy review rows / 0 ambiguity. v1.5.12.4 must be used for the next compact output; do not hand-edit around the transactional materializer.

## Mod 2.0

`audit-mod-level-progression.py` is tested (`71968d87627ef1dda714dca104cd5d2a710c3d78`). Fresh progression has exactly 17 `mod_level` rows, Levels 1–17. There is zero numeric overlap with compact `mod_code` or `main_entry_code`, so numeric ID matching is not a valid join. Prove the consumer/meaning of `frame_lv_1..4` before changing public Mod semantics.

## Attachments

Fresh player-selectable target is confirmed: Sight 30 / Muzzle 36 / Tactical 36 / Magazine 17 = 119. Names/static effect evidence/images are present. Compact records currently have no proven `compatible_weapon_types`, so compatibility-aware Build Lab migration remains blocked. Do not invent compatibility.

## Deviations / Cradles

Deviations: 98 display-name families / 160 variants; 60 families are multi-variant. Preserve variants until identity is proven.

Cradles: 120 display-name families / 170 variants; 32 families are multi-variant. Fresh evidence shows same display names can contain materially different descriptions/buff IDs, so display name alone is not safe canonical Cradle identity. Do not auto-select variant #1.

## Build Lab / ingestion

Weapons remain the strongest canonical vertical. Armor/Calibrations/Mods/Attachments/Deviations/Cradles must fail closed when their compact contract is unready or ambiguous. Transactional all-seven materialization remains the accepted ingestion path; do not manually copy individual category payloads to bypass a blocked category.

Hosting-only legacy Build Lab files `preview/build-lab/data/community-data.js` and `preview/build-lab/app.js` are not in Git. Do not invent their mutation contract or remove compatibility pools until canonical end-to-end replacement is proven.

## Exact next sequence

1. Continue source-specific weapon short-description localization investigation; keep descriptions withheld until proven.
2. Continue Armor root-cause investigation for the 15 recipe-backed missing Tier stat rows.
3. Use the next v1.5.12.4 installed-game output to verify the 94-family Calibration compact contract end-to-end; repository-side work should continue without waiting where possible.
4. Prove Mod 2.0 `frame_lv_1..4` / Lv1–17 consumer semantics.
5. Prove Attachment compatibility from direct table/consumer evidence.
6. Resolve Deviation and Cradle variant identity, especially Cradles where display-name grouping is demonstrably unsafe.
7. Continue Build Lab canonical migration only after each category contract is proven.
8. Keep unready routes `SOON`.
9. Only after core functionality is broadly complete, audit current Wikily and OnceHumanDB for UX/features and implement evidence-backed differentiators.

## Read first

`PROJECT-RULES.md`, `data.7z`, `tools/miner/VERSION`, `tools/miner/release/latest.json`, `tools/miner/src/extractor/normalize_weapons.py`, `tools/miner/src/extractor/normalize_armor.py`, `tools/miner/src/extractor/publish_current_calibrations.py`, `tools/site/audit-weapon-skill-references.py`, `tools/site/audit-armor-tier-evidence.py`, `tools/site/audit-mod-level-progression.py`, `tools/site/audit-extended-contracts.py`, `tools/site/materialize-published-snapshot.py`, `preview/build-lab/canonical-category-bridge.js`, `.github/workflows/test-site-tools.yml`, `.cpanel.yml`.
