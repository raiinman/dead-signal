# Dead Signal — Weapon Forensics / Miner Handoff

> **Date:** 2026-08-16 night shift / 2026-08-17 UTC
> **Repository:** `raiinman/dead-signal`
> **Branch:** `main`
>
> Read `AI-CONTINUITY.md` and `PROJECT-RULES.md` first. This is the active handoff for the Weapon evidence investigation and supersedes the older Build Lab handoff as the immediate research objective.

## Current objective

Finish the player-facing Weapons database from exact installed-game evidence. The active blocker is the **14 normal public weapon records whose real `fixed_skill_code` has no conventional `passive_skill_data` owner**.

Do **not** interpret that as “no mechanic” or “broken weapon record.” These weapons still have normal blueprint/item/prototype/gun/presentation identity. The unresolved subsystem is specifically the fixed-skill ownership path.

The active question is:

> **What alternate resolver, transformation, mapping, buff path, or UI fallback handles the ownerless fixed-skill class?**

## Stable Miner release

Miner **v1.5.14.47 is RELEASED and stable**.

Release source commit:

- `a8fc68845fdf9d454ebb5cf350fb8c5508633370` — `Release Miner v1.5.14.47`

Release workflow:

- GitHub Actions run `31997169055` — **SUCCESS**
- Source tests: PASS
- Windows build: PASS
- Packaged self-test: PASS
- Release packaging: PASS
- GitHub release publication: PASS
- Public ZIP verification: PASS
- Updater manifest published last: PASS

The installed updater may be one check behind while GitHub/CDN state propagates, but the `.47` release workflow itself completed all gates successfully.

## Core weapon state

- 120 weapons total = 95 ranged / 25 melee.
- Browse/detail/compare defaults are Tier I · 1★.
- Multi-projectile damage uses exact `bullet_pattern_no -> bullet_pattern_data.bullet_num` evidence, e.g. shotgun `32×5`.
- Magazine remains withheld because the exact `get_gun_magazine_size` aggregation is unresolved. Do not infer a universal `+10` or publish the internal Q1100 value as final Magazine.
- Acquisition remains evidence-gated: 106 recipe-proven, 9 direct stronghold acquisition, 5 unresolved.
- Missing recipe evidence never proves non-craftable.
- Weapon Description and Special Skill are separate evidence paths.

## Weapon description breakthrough

The player-facing description producer path is now understood well enough to project the full catalogue systematically:

```text
weapon blueprint
→ prototype_no
→ weapon_prototype_data[prototype_no]
→ prototype_desc
→ English translation
```

The full NeoX export projection found:

- 120 / 120 weapon prototype records
- 120 / 120 `prototype_desc` fields
- 119 consistent English resolutions
- 1 translation conflict
- 0 unresolved producer fields

Representative AA12 / ACS12 evidence:

```text
Blueprint 13231101
→ Item 10231101
→ Prototype 204
→ weapon_prototype_data[204].prototype_desc
→ exact installed English translation
```

Exact installed English translation:

> `ACS12 Auto Shotgun, with its high-capacity drum mag, blasts a rapid fire rate perfect for close-quarters combat`

Keep exact source text distinct from any public canonical-name normalization such as `ACS 12`.

The description consumer stack includes `ItemDataTools` weapon item-data helpers and `get_weapon_prototype_data_val_by_key(..., 'prototype_desc', '')`. The producer path is separate from fixed-skill mechanics.

## Clean-tree control: SKS Pathfinder

Pathfinder is a good normal control because its identity and fixed-skill branches resolve cleanly.

Known identity spine:

```text
SKS - Pathfinder
blueprint 13551401
→ item 10551401
→ prototype 505
→ gun 10550131
```

Fixed-skill branch:

```text
blueprint attr
→ fixed_skill_code WS15504
→ passive_skill_data[WS15504]
→ buff_id 354505000
→ keyword_buff_id 110400000
```

Description branch:

```text
prototype 505
→ prototype_desc
→ English presentation text
```

Use Pathfinder as a conventional complete-tree comparison.

## Broken-tree control: OIC-8 / XM8 Last Carnival

Last Carnival is the clearest ownerless example.

Known identity spine:

```text
OIC-8 / XM8 - Last Carnival
blueprint 13431301
→ item 10431301
→ prototype 404
→ gun 10430131
```

Normal configuration branches continue through ammo/bullet/scatter/crosshair/stardust handles.

The broken subsystem is:

```text
blueprint 13431301
→ fixed_skill_code WS2001
→ NO exact passive_skill_data owner
```

This does **not** invalidate the rest of the weapon record. Its description path still resolves independently through prototype 404.

## Public ownerless fixed-skill population

The 14 normal public unresolved weapons collapse to 11 unique codes:

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

Canonical public mappings:

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

Across the complete structured NeoX export, each of these exact code strings appears only in `game_common/data/gun_blueprint_attr_data`.

There are 26 total ownerless `fixed_skill_code` values in the export, but the extra 15 are not equivalent to the 14 normal public weapons. Many point to records without normal `gun_blueprint_data` identities and may be orphan/stale/config-only/hidden/nonstandard. Keep those populations separate.

## Structural fingerprint of the 14 public ownerless weapons

The public class consistently shows:

```text
fixed_skill_code present
passive_skill_data owner absent
endow = false
plaques empty
base_attr E0100/E0200/E0300 = 0
correct_skill absent
correct_term_id absent
```

`endow=false` alone is not sufficient; resolved controls also exist with `endow=false`.

Interpretation must remain narrow:

> These 14 do not use the conventional fixed-passive/correction payload used by ordinary special-effect weapons.

Do not relabel them “no mechanic.”

## Fixed-skill architecture research

The architecture tracer now covers six static branches:

1. damage/passive mapping
2. GunCore / BluePrint normalization
3. helper fallback resolution
4. star/stardust resolution
5. server buff resolution
6. player-facing UI

High-value modules/functions include:

- `game_common/guncore/BluePrintHelper.pyc`
  - `get_blueprint_fixed_skill`
  - `get_blueprint_fixed_skill_lv`
  - `get_fixed_skill_default_data`
  - `get_skill_data`
- `game_common/guncore/GunCoreHelper.pyc`
  - `climp_skill_code`
  - `init_fixed_skill`
  - `convert_data_skill_slots`
  - `get_decompose_skill`
- `dcs_extend/component/shoot_new/keyword/CompShootDamageSimulateClient.pyc`
  - `WEAPON_TO_PASSIVE`
  - `WEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG`
  - `get_weapon_passive_skill_config`
- `dcs_extend/component_server/CompSkillMgr.pyc`
- `dcs_extend/component/CompCamera.pyc`
- `dcs_extend/common/shoot_utility.pyc`
- `ui/weapon_craft_part/ScrollViewItems.pyc`
  - `WRGunInfoPart.update_fixed_skills`
  - `label_skill_desc`
  - `label_skill_passivename`

Because Once Human bytecode does not always match the local Python opcode table, tolerant tracing must preserve raw offsets/opcodes/args and only safely resolved constants/names. Never execute game bytecode.

## Data Intelligence compiler integration — v1.5.14.47

A key packaging bug was found: **COMPILE DATA INTELLIGENCE** previously produced a large Intelligence ZIP but did not actually execute/include the ownerless fixed-skill forensic stage.

That is now fixed.

Implementation commits:

- `6dae3fd53c95622d6a74ed4d0f756bba2382e674` — integrate ownerless skill forensics into Intelligence compiler
- `4e9aa3a14c02a63dca80ed716bc53e617b387a5c` — regression tests for Intelligence forensic integration
- `a8fc68845fdf9d454ebb5cf350fb8c5508633370` — release Miner v1.5.14.47

Integration CI before release:

- GitHub Actions run `31996868767` — **SUCCESS**
- source tests PASS
- Windows packaged build PASS
- packaged self-test PASS

The full compiler path is now:

```text
COMPILE DATA INTELLIGENCE
→ Weapon UI Consumer Trace
→ Research Suite
→ full 120-weapon Guided Schema Trace
→ isolate unresolved skill_id values
→ Missing Skill Forensics
→ six-branch architecture trace
→ Discovery / Analytics / Publication Gate
→ Intelligence ZIP
```

The generated Intelligence ZIP must now include:

- `research/schema-trace-all-weapons.json`
- `research/missing-fixed-skill-forensics.json`

The compiler summary also exposes:

- unique unresolved skill-code count
- forensic status
- architecture branch count
- architecture functions found

## Immediate next action

1. Update the installed Miner from `.46` to **v1.5.14.47**.
2. Open **Research Console → Compiler**.
3. Click **COMPILE DATA INTELLIGENCE**.
4. When complete, use **OPEN INTELLIGENCE BUNDLES**.
5. Send the newest `Dead-Signal-Intelligence-*.zip`.
6. Confirm the ZIP contains `research/missing-fixed-skill-forensics.json` and `research/schema-trace-all-weapons.json`.
7. Inspect the six architecture branches for evidence of transformation, alternate owner, direct buff mapping, stardust remap, helper fallback, or UI-only handling.
8. If still unresolved, use exact identifiers exposed by those branches to trace into NeoX. Do not revert to fuzzy/global scalar graph traversal.

## Research doctrine

Use:

**Locate → Inspect → Follow → Verify**

- Evidence Graph / Identity Map = discovery map.
- NeoX Explorer = structured-table microscope.
- Guided Schema Trace = semantic typed-owner proof path.
- Missing Skill Forensics = bounded static consumer/architecture research.
- Cohort Diff = structural discriminator between ownerless public records and resolved controls.

The Evidence Graph can locate an occurrence; it does not make equal scalar values semantic relationships.

## Parked / unresolved items

- Magazine aggregation remains unresolved; keep Magazine unpublished.
- One weapon-description translation conflict remains quarantined until exact precedence is proven.
- The 14 ownerless public fixed-skill weapons remain unresolved mechanically until an alternate exact chain is proven.
- Do not resume broad competitor UX work while this evidence blocker is active unless priority changes.

## Non-negotiables

- Work directly on canonical `main` unless explicitly told otherwise.
- Installed-game / Miner data outranks guesses and community databases.
- Never execute game bytecode.
- Never promote fuzzy/similar IDs or global scalar collisions into authoritative evidence.
- Missing recipe evidence never proves non-craftable.
- Missing passive owner does not prove no player-facing mechanic or description.
- Weapon Description and Special Skill are separate evidence lanes.
- Never publish local Miner snapshots, `reference-tracer.sqlite`, research notes, full NeoX exports, or raw evidence bundles.
- Do not touch pre-existing `tools/miner.zip`.
- Do not route work to Perplexity unless explicitly reversed.
- Preserve copy-only cPanel deployment and accepted site architecture.
- Do not touch SSL, DNS, redirects, domain, or cPanel hosting configuration.
- Preserve the accepted landing page and Official Once Human X feed.
- Keep unfinished routes `SOON`.
