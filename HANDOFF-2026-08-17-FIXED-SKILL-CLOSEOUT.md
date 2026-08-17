# Dead Signal — Ownerless Fixed-Skill Closeout

> **Date:** 2026-08-16 night shift / 2026-08-17 UTC
> **Repository:** `raiinman/dead-signal`
> **Branch:** `main`

This handoff closes the current installed-corpus investigation into the 14 normal public weapons whose `gun_blueprint_attr_data.fixed_skill_code` values do not have exact owners in `passive_skill_data`.

## Bundle analyzed

`Dead-Signal-Intelligence-20260817-064350Z.zip`

Generated with Miner **v1.5.14.49**.

## Closeout sweep scope

The `.49` closeout discovery scanned 94,165 retained PYC files and produced 424 static candidates across eight hypothesis classes:

- `skill_constants`: 13
- `climp_callers`: 1
- `passive_table_assembly`: 256
- `package_fixed_skill`: 5
- `damage_sim_indirection`: 2
- `server_weapon_initializers`: 6
- `blueprint_identity_fallbacks`: 3
- `compatibility_overrides`: 138

All matching was static. No Once Human bytecode was executed.

## Exact findings

### 1. `SKILL_CODE_LEN = 9`

The `game_common/guncore/SkillConst.pyc` module assignment sequence correlates:

- indexed constant `54` → `9`
- indexed name `55` → `SKILL_CODE_LEN`
- raw wordcode assignment at offset `228` stores into indexed name `55`

Therefore the current installed constant is exactly:

```text
SKILL_CODE_LEN = 9
```

`GunCoreHelper.climp_skill_code(skill_code)` contains only `skill_code`, `SKILL_CODE_LEN`, and scalar `0`, consistent with bounded clipping/slicing.

All ownerless public codes (`WS1001`, `WS1101`, `WS1301`, `WS1402`, `WS14503`, `WS1501`, `WS15203`, `WS15304`, `WS15502`, `WS1601`, `WS2001`) are shorter than nine characters, so this path does not expand, pad, alias, or translate them into alternate IDs.

Only one exact `climp_skill_code` caller candidate exists in the corpus: the GunCore helper module itself. No separate conversion bridge was found.

### 2. Packaged fixed skills preserve the same `skill_code`

`BluePrintHelper.package_fixed_skill_data`:

- calls `get_blueprint_fixed_skill`
- calls `get_blueprint_fixed_skill_lv`
- packages the result with fields:
  - `skill_code`
  - `skill_lv`
  - `skill_star`
  - `break_lv`

`equip_package_fixed_skill_data` does the same for equipment.

`GunCoreHandler._init_guncore` consumes `package_fixed_skill_data` and initializes a `fixed_skill` payload.

`GunCoreHandler.get_fixed_passive_code` later reads `fixed_skill → skill_code`.

No alternate skill identifier, conversion table, owner table, alias field, or remap constant appears in this chain.

### 3. No passive-table assembly/merge rescue was proven

The broad `passive_table_assembly` category produced 256 candidates because `DataMgr` / `common_data` are heavily used across the client.

Critically, **none of those 256 candidate rows contains the exact symbol `passive_skill_data`** in an assembly/merge/loading context.

No exact static path was found that:

- loads a second passive table,
- merges seasonal passive records into `passive_skill_data`,
- patches missing `WS####` keys at runtime,
- aliases legacy skill IDs into the passive table, or
- injects the 11 ownerless public codes into `DataMgr.common_data`.

The generic DataMgr/common-data hits are therefore context noise, not evidence for an alternate owner path.

### 4. Damage-simulation mappings are not a hidden ID bridge

`CompShootDamageSimulateClient.pyc` contains:

- `WEAPON_TO_PASSIVE`
- `WEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG`
- `gun_blueprint_attr_data`
- `passive_skill_damage_simulate_data`

`get_weapon_passive_skill_config` reads:

- `blueprint_no`
- `weapon_no`
- `fixed_skill_code`
- those two mappings
- `passive_skill_damage_simulate_data`

But the module constant pool contains no ownerless `WS####` codes, no alternate passive IDs, and no relevant per-weapon hardcoded conversion values.

The previous exact structured-data scan also found all 11 public ownerless codes only in `gun_blueprint_attr_data`, with no exact scalar owners in `passive_skill_damage_simulate_data` or any other retained structured table.

Therefore these mappings are runtime caches/indices, not a proven fixed-skill alias table.

### 5. Blueprint-identity fallback routes still end at the same unresolved code

The only exact blueprint/fixed-skill consumers discovered are:

- `CompCameraOtherPlayer._get_gun_sp_track_time`
- `CompShootDamageSimulateClient.get_weapon_passive_skill_config`
- `CompSkillMgrNpc._get_gun_ps_buff_id`

They all start from `blueprint_no → gun_blueprint_attr_data → fixed_skill_code`.

The camera/star path continues through `passive_skill_data → star_skill_no → stardust_gun_skill_data`.

The server buff path continues through the fixed-skill code toward passive-skill/buff handling.

The damage-sim path uses the same `fixed_skill_code` as described above.

No independent blueprint-ID, prototype-ID, gun-ID, or item-ID keyed mechanic owner was found for these 14 weapons.

### 6. Compatibility / legacy / replacement sweep found no conversion bridge

The broad compatibility category produced 138 token candidates. Most are animation/UI files or unrelated uses of words such as `override` and `replace`.

The skill-relevant matches reduce to ordinary fixed-skill consumers/presentation paths including:

- `impGunCore._prase_fix_skill`
- `BluePrintHelper.get_blueprint_fixed_skill`
- `BluePrintHelper.get_fixed_skill_default_data`
- `BluePrintHelper.package_fixed_skill_data`
- `GunCoreHandler.get_fixed_passive_code`
- `SkillDataHelper.is_fixed_skill`
- `MainUIDataModel.get_gun_sp_skill`
- `ItemDataTools.get_gun_passive_attr`
- weapon-craft / blueprint UI `update_fixed_skills` functions
- `shoot_utility.get_star_cast_skill_behavior_name`

No function combines a legacy/migrate/replace/override path with `fixed_skill_code` and an alternate skill identifier or owner table.

The actual `replace` hits in `CompSkillMgr` are deviation replacement sources, not weapon fixed-skill migration.

## Routing conclusion

The current installed-game corpus now supports the following exact model:

```text
weapon blueprint
→ gun_blueprint_attr_data.fixed_skill_code = WS####
→ WS is classified as a passive-skill namespace
→ generic lookup expects passive_skill_data[WS####]
→ package/serialization preserves the same WS#### code
→ SKILL_CODE_LEN = 9, so these short codes are not transformed by clipping
→ no exact current passive owner exists for the 11 public ownerless codes
→ no alternate table, runtime merge, legacy conversion, hardcoded remap, damage-sim owner, server initializer, or blueprint-identity fallback was proven
```

## Publication-safe conclusion

Use this wording internally and in evidence metadata:

> The current installed-game corpus contains real weapon `fixed_skill_code` references for these records, but no exact current owner/resolution path for those codes was found after exhaustive static tracing of the known fixed-skill architecture and closeout hypotheses.

Do **not** claim:

- the weapons have no player-facing mechanic;
- the codes are definitely broken;
- the codes are definitely removed content;
- a community description is therefore correct;
- missing passive ownership proves non-functionality.

A reasonable internal classification is:

```text
ownerless-current-corpus / likely dangling-or-legacy fixed-skill reference
```

with the `likely` qualifier kept separate from the proven evidence state.

## Branch status

The ownerless `WS####` lookup investigation is **closed for the current installed corpus**.

Reopen only if one of these occurs:

1. a future game build changes the relevant tables/modules;
2. a newly retained exact source layer exposes a missing owner or conversion table;
3. runtime-observable evidence can be captured safely and independently tied back to an exact installed data identity;
4. a previously unavailable typed table becomes extractable and contains one of the exact ownerless codes.

Do not continue broad corpus searches for the same `WS####` strings without new evidence.

## Remaining weapon blockers unrelated to this closeout

- Magazine aggregation remains unresolved; keep Magazine unpublished.
- One weapon-description translation conflict remains quarantined.
- The 14 weapon special-skill descriptions remain unresolved unless an independent exact installed evidence chain is discovered in a future build/source layer.

## Doctrine

Installed-game evidence remains authoritative. Missing ownership is an evidence state, not permission to import community mechanics.
