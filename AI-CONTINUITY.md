# Dead Signal — AI Continuity / Handoff

> Read this file and `PROJECT-RULES.md` first. Canonical current-state continuity for `raiinman/dead-signal` on `main`.
>
> Updated **2026-08-16 night shift / 2026-08-17 UTC** after the weapon-description breakthrough, ownerless fixed-skill architecture expansion, Data Intelligence compiler integration, and Miner v1.5.14.47 release.

## Immediate objective

Finish the player-facing Once Human Weapons database from exact installed-game evidence.

The active blocker is **14 normal public weapons with a real `fixed_skill_code` but no conventional `passive_skill_data` owner**. Do not call these “no mechanic” or “broken weapon records.” Their identity, item, prototype, gun, tier, and presentation paths are normal; the unresolved subsystem is specifically fixed-skill ownership/resolution.

Active question:

> What alternate resolver, transformation, mapping, direct buff path, stardust path, helper fallback, or player-facing UI path handles the ownerless fixed-skill class?

See `HANDOFF-2026-08-16-WEAPON-FORENSICS.md` for the detailed current-session research state.

## Non-negotiables

- Work directly on canonical `main` unless the user explicitly requests otherwise.
- Installed-game / Miner evidence is authoritative for numbers and mechanics.
- Wikily, OnceHumanDB, Resurgence Builds, screenshots, videos, and community material are UX/search clues only unless independently proven by installed evidence.
- Never invent mechanics, recipes, compatibility, proc behavior, DPS, rankings, multiplier semantics, crafting identity, or variant identity.
- Missing recipe evidence never proves non-craftable.
- Missing passive-skill ownership never proves no player-facing mechanic or description.
- Weapon Description and Special Skill are separate evidence lanes.
- Never execute game bytecode.
- Never promote fuzzy/similar IDs, substring matches, global scalar equality collisions, or bare-number matches into authoritative evidence.
- Evidence Graph / Identity Map is a locator, not semantic proof. Guided Schema Trace is the typed-owner semantic proof path.
- Never publish local Miner snapshots, `reference-tracer.sqlite`, research notes, full NeoX exports, raw evidence bundles, or machine-specific paths.
- Do not touch pre-existing `tools/miner.zip`.
- Do not route Dead Signal work to Perplexity unless the user explicitly reverses that decision.
- Preserve copy-only cPanel deployment. Do not touch DNS, SSL, redirects, domain settings, or cPanel hosting configuration.
- Preserve the accepted landing page and Official Once Human X feed.
- Routes that are not genuinely ready remain `SOON`.
- GitHub source is authoritative; release packages are artifacts.
- Updater manifest must be published last after release asset verification.

## Stable Miner

Miner **v1.5.14.47 is RELEASED and stable**.

Release source commit:

- `a8fc68845fdf9d454ebb5cf350fb8c5508633370` — `Release Miner v1.5.14.47`

Release workflow:

- GitHub Actions run `31997169055` — **SUCCESS**
- source tests PASS
- Windows build PASS
- packaged self-test PASS
- release packaging PASS
- GitHub release publication PASS
- public asset verification PASS
- updater manifest published last PASS

v1.5.14.47 exists specifically to carry the ownerless fixed-skill forensic chain through **COMPILE DATA INTELLIGENCE** and into the uploadable Intelligence ZIP.

## Core Weapon catalogue state

- 120 weapons total = 95 ranged / 25 melee.
- Browse/detail/compare defaults are Tier I · 1★.
- Multi-projectile damage is represented through exact `bullet_pattern_no -> bullet_pattern_data.bullet_num` evidence; e.g. `32×5`.
- Magazine remains unpublished because exact `get_gun_magazine_size` aggregation is unresolved. Internal Q1100 values are not final player-facing Magazine values.
- Acquisition remains evidence-gated: 106 recipe-proven, 9 direct stronghold acquisition, 5 unresolved.
- Suspect/cross-wired descriptions remain withheld unless exact producer/translation identity is proven.

## Weapon description path — major breakthrough

The player-facing weapon-description producer path is now understood:

```text
weapon blueprint
→ prototype_no
→ weapon_prototype_data[prototype_no]
→ prototype_desc
→ English translation
```

Full NeoX projection results:

- 120 / 120 prototype records found
- 120 / 120 `prototype_desc` fields found
- 119 consistent translation resolutions
- 1 translation conflict
- 0 unresolved producer fields

Representative AA12 / ACS12 chain:

```text
Blueprint 13231101
→ Item 10231101
→ Prototype 204
→ weapon_prototype_data[204].prototype_desc
→ English translation
```

Exact installed English translation:

`ACS12 Auto Shotgun, with its high-capacity drum mag, blasts a rapid fire rate perfect for close-quarters combat`

Do not silently replace exact source text with normalized public naming when reporting evidence.

The static consumer path includes `ItemDataTools` weapon item-data helpers and a formula using `get_weapon_prototype_data_val_by_key(prototype_no, 'prototype_desc', '')`.

## Conventional control — SKS Pathfinder

Known clean tree:

```text
SKS - Pathfinder
blueprint 13551401
→ item 10551401
→ prototype 505
→ gun 10550131
```

Fixed-skill branch:

```text
fixed_skill_code WS15504
→ passive_skill_data[WS15504]
→ buff_id 354505000
→ keyword_buff_id 110400000
```

Description branch resolves separately through prototype 505 → `prototype_desc` → English presentation text.

Use Pathfinder as a conventional clean-tree comparison.

## Ownerless control — OIC-8 / XM8 Last Carnival

Known identity spine:

```text
blueprint 13431301
→ item 10431301
→ prototype 404
→ gun 10430131
```

The normal gun/ammo/bullet/scatter/crosshair/stardust branches remain intact.

The unresolved subsystem is:

```text
fixed_skill_code WS2001
→ no exact passive_skill_data owner
```

Its description still resolves independently through prototype 404.

## Public ownerless fixed-skill class

14 normal public weapons collapse to 11 unique codes:

- `WS1001`
- `WS1101`
- `WS1301`
- `WS1402`
- `WS14503`
- `WS1501`
- `WS15203`
- `WS15304`
- `WS15502`
- `WS1601`
- `WS2001`

Canonical mappings:

- `WS1001` → 13541201 / 10541201 → SR2000 / WA2000 Jungle Camouflage
- `WS1101` → 13111201 / 10111201 → DE.50 Goshawk
- `WS1301` → 13331201 / 10331201 → MPS7 Focus
- `WS1301` → 13332201 / 10332201 → MPS7 Urban Ninja
- `WS1402` → 13411201 / 10411201 → SOCR Sand Dancer
- `WS14503` → 13541301 / 10541301 → SR2000 Die Another Day
- `WS1501` → 13511201 / 10511201 → SN700 Dark Snowflake
- `WS15203` → 13212401 / 10212401 → DBSG Format
- `WS15304` → 13332401 / 10332401 → MPS7 Chaos Domain
- `WS15502` → 13531301 / 10531301 → HAMR Hannya
- `WS1601` → 13621201 / 10621201 → MG4 Sandstorm
- `WS2001` → 13121301 / 10121301 → R500 Interfade
- `WS2001` → 13131301 / 10131301 → G17 Cash Only
- `WS2001` → 13431301 / 10431301 → OIC-8 / XM8 Last Carnival

All 11 exact code strings appear only in `game_common/data/gun_blueprint_attr_data` across the full structured NeoX export.

The full ownerless code population is larger (26 unique codes), but the extra 15 are not the same class as these 14 normal public weapons. Keep them separate.

## Structural fingerprint of the 14

The normal public ownerless class consistently shows:

```text
fixed_skill_code present
passive_skill_data owner absent
endow = false
plaques empty
base_attr E0100/E0200/E0300 = 0
correct_skill absent
correct_term_id absent
```

`endow=false` alone is not diagnostic; resolved controls also exist with it.

Narrow interpretation only:

> These 14 do not use the conventional fixed-passive/correction payload used by ordinary special-effect weapons.

## Fixed-skill forensic architecture

The architecture tracer now covers six static branches:

1. damage/passive mapping
2. GunCore / BluePrint normalization
3. helper fallback resolution
4. star/stardust resolution
5. server buff resolution
6. player-facing UI

High-value static modules include:

- `game_common/guncore/BluePrintHelper.pyc`
- `game_common/guncore/GunCoreHelper.pyc`
- `dcs_extend/component/shoot_new/keyword/CompShootDamageSimulateClient.pyc`
- `dcs_extend/component_server/CompSkillMgr.pyc`
- `dcs_extend/component/CompCamera.pyc`
- `dcs_extend/common/shoot_utility.pyc`
- `ui/weapon_craft_part/ScrollViewItems.pyc`

Important functions/symbols include:

- `get_blueprint_fixed_skill`
- `get_blueprint_fixed_skill_lv`
- `get_fixed_skill_default_data`
- `get_skill_data`
- `climp_skill_code`
- `init_fixed_skill`
- `convert_data_skill_slots`
- `get_decompose_skill`
- `WEAPON_TO_PASSIVE`
- `WEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG`
- `get_weapon_passive_skill_config`
- `WRGunInfoPart.update_fixed_skills`
- `label_skill_desc`
- `label_skill_passivename`

Once Human bytecode may not match the local Python opcode table. Tolerant static tracing must preserve raw offsets/opcodes/args and only safely resolved constants/names. Never execute game bytecode.

## Full NeoX export

The user supplied a complete research-only NeoX export:

- 41,758 archive entries = 41,757 table files + manifest
- 41,340 catalogued tables
- approximately 1.43 GB exported source bytes
- zero expected table files missing

Do not commit or publish this export. Use it as a discovery corpus only.

## Data Intelligence compiler integration — v1.5.14.47

A packaging gap was discovered after a user-run Intelligence bundle: the bundle contained many reports but did **not** execute/include `missing-fixed-skill-forensics.json`.

That is fixed in `.47`.

Implementation commits:

- `6dae3fd53c95622d6a74ed4d0f756bba2382e674` — integrate ownerless skill forensics into Intelligence compiler
- `4e9aa3a14c02a63dca80ed716bc53e617b387a5c` — regression-test bundle integration
- `a8fc68845fdf9d454ebb5cf350fb8c5508633370` — release Miner v1.5.14.47

Pre-release integration CI:

- GitHub Actions run `31996868767` — **SUCCESS**

The complete compiler path now includes:

```text
Weapon UI Consumer Trace
→ Research Suite
→ full 120-weapon Guided Schema Trace
→ unresolved skill_id extraction
→ Missing Skill Forensics
→ six-branch architecture trace
→ Discovery / Analytics / Publication Gate
→ Intelligence ZIP
```

The Intelligence ZIP must include:

- `research/schema-trace-all-weapons.json`
- `research/missing-fixed-skill-forensics.json`

## Immediate next steps

1. Installed Miner updates from `.46` to **v1.5.14.47**.
2. Open **Research Console → Compiler**.
3. Click **COMPILE DATA INTELLIGENCE**.
4. Send the newest `Dead-Signal-Intelligence-*.zip`.
5. Verify the ZIP contains `research/schema-trace-all-weapons.json` and `research/missing-fixed-skill-forensics.json`.
6. Read the six architecture branches for exact evidence of transformation, alternate owner, direct buff mapping, stardust remap, helper fallback, or UI-only behavior.
7. Follow only exact returned identifiers into NeoX / typed owner tables.
8. If no alternate chain is proven, preserve unresolved mechanic state rather than filling from community data.

## Research workflow

Use:

**Locate → Inspect → Follow → Verify**

- Identity Map / Evidence Graph = locator/index.
- NeoX Explorer = microscope.
- Guided Schema Trace = semantic typed-owner proof path.
- Missing Skill Forensics = bounded static consumer/architecture investigation.
- Cohort Diff = exact structural comparison between ownerless public records and resolved controls.

Do not brute-force global graph traversal when an exact owner field, code consumer, or cohort discriminator can narrow the path.

## Parked blockers

- Magazine aggregation remains unresolved; do not restore Magazine.
- One weapon-description translation conflict remains quarantined until exact language/precedence evidence is proven.
- The 14 ownerless public fixed-skill weapons remain mechanically unresolved until an alternate exact chain is proven.
- Competitor UX audit remains lower priority until the core database / Build Lab migration is broadly complete.

## Build Lab continuity

The richer Weapon Selector remains approved:

- `SELECT / Weapon`
- search by name / skill / description
- top filters for category/type, rarity, acquisition, mechanic evidence
- no redundant left filter column
- 10 records per page
- rich weapon cards with art, name, rarity, category, Tier I · 1★, Weapon Description, Special Skill, DMG / Fire Rate / Range, acquisition/evidence, favorites
- mobile one card per row with natural modal scroll and reachable pagination

Known selector geometry fixes already landed; do not reintroduce the desktop black-cavity regression or mobile hidden-page layout bug.

## Deployment continuity

Dead Signal uses a copy-only cPanel deployment model. Do not reintroduce WordPress runtime. Do not alter DNS/SSL/redirect/domain/cPanel hosting settings. Preserve accepted landing page and Official Once Human X feed. Unfinished routes stay `SOON`.
