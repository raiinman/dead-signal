# Dead Signal — Fixed-Skill Routing Forensics Handoff

> **Date:** 2026-08-16 night shift / 2026-08-17 UTC
> **Repository:** `raiinman/dead-signal`
> **Branch:** `main`
>
> Read `AI-CONTINUITY.md` and `PROJECT-RULES.md` first. This handoff supersedes `HANDOFF-2026-08-16-WEAPON-FORENSICS.md` for the immediate ownerless fixed-skill investigation.

## Current objective

Finish the player-facing Weapons database from exact installed-game evidence.

The active blocker remains the **14 normal public weapons with real `fixed_skill_code` values but no conventional `passive_skill_data` owner**. Do not call these records mechanic-less or broken. Their blueprint/item/prototype/gun/presentation identities are normal; the unresolved subsystem is specifically fixed-skill routing/ownership.

The active question is now narrower:

> **What does the game do to the ownerless `WS####` code before final skill lookup?**

The four highest-priority targets are:

1. `SkillDataHelper.get_table_name(skill_code)`
2. `GunCoreHelper.climp_skill_code(skill_code)` plus `SKILL_CODE_LEN`
3. module-level `WEAPON_TO_PASSIVE`
4. module-level `WEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG` plus `get_weapon_passive_skill_config`

## Miner v1.5.14.48

Miner **v1.5.14.48 is RELEASED and stable**.

Release source commit:

- `b92e5ddaf2201bc0201585d1c8650ae6da33b1f2` — `Release Miner v1.5.14.48`

Forensic implementation commits:

- `4702fb2c6458acc6ac6ff3fa43653f752ccef9ed` — `Expand fixed-skill architecture forensic detail`
- `a1ef6c642ca02b46aa62ca2a10cb5ac56f2b9c96` — `Test expanded fixed-skill forensic detail`

Release workflow:

- GitHub Actions run `31999313452` — **SUCCESS**
- source compile/tests PASS
- Windows build PASS
- packaged self-test PASS
- release packaging PASS
- GitHub release publication PASS
- public release verification PASS
- updater manifest published last PASS

The independent source CI also passed the expanded forensic regression tests before the release build.

## What v1.5.14.48 changes

The `.47` Intelligence bundle proved the six architecture branches but was still too lossy for the four routing targets. It reported function names, `co_names`, variables, and scalar constants, but did not preserve enough instruction-level evidence to reconstruct routing safely.

`.48` expands `dead_signal_fixed_skill_architecture_trace.py` without executing game bytecode.

For selected functions/modules it now records:

- exact raw 2-byte wordcode rows:
  - byte offset
  - opcode byte
  - argument byte
- indexed `co_names`
- indexed `co_varnames`
- indexed safe scalar `co_consts`
- code length
- module-level code objects where needed

This is intentionally version-agnostic evidence. Once Human opcode tables may not match the local Python runtime, so `.48` **does not interpret unknown opcode bytes through the local `dis` table**. It preserves exact bytes and indexed pools for later correlation.

## New exact targets included in the architecture trace

### SkillDataHelper routing

The helper-fallback branch now explicitly captures:

- `<module>`
- `is_fixed_skill`
- `is_passive`
- `check_is_passive_skill`
- `is_skill_exist`
- `get_table_name`
- `get_skill_data`
- `get_skill_name`
- `get_skill_description`
- `get_skill_desc`

This is important because `.47` showed:

```text
is_skill_exist(skill_code)
→ get_table_name(skill_code)
→ DataMgr.common_data[table_name]
```

The unresolved question is the exact prefix/table routing inside `get_table_name`.

### GunCore normalization

The GunCore branch now captures the module-level constant/name pools in addition to:

- `climp_skill_code`
- `init_fixed_skill`
- `convert_data_skill_slots`
- `get_decompose_skill`
- `get_blueprint_fixed_skill`

The immediate goals are:

- determine the exact value assigned to `SKILL_CODE_LEN`
- reconstruct what `climp_skill_code` does to `skill_code`
- test whether short codes such as `WS2001` are padded, truncated, transformed, validated, or left unchanged before lookup

Do not assume the misspelled function name `climp_skill_code` means clipping until the instruction/constant evidence proves it.

### Damage/passive mapping

The damage/passive branch now includes the module-level code object for:

`dcs_extend/component/shoot_new/keyword/CompShootDamageSimulateClient.pyc`

This is specifically to recover construction/use evidence for:

- `WEAPON_TO_PASSIVE`
- `WEAPON_PASSIVE_TO_SKILL_DAMAGE_CONFIG`

and correlate those globals with:

- blueprint/gun identity
- `fixed_skill_code`
- `passive_skill_damage_simulate_data`

Do not infer mapping contents merely because the global names occur in the same module. Use the raw wordcode and indexed pools to prove assignment/use relationships.

## `.47` evidence that motivated this pass

The newest valid `.47` bundle was:

`Dead-Signal-Intelligence-20260817-052848Z.zip`

It correctly contained:

- `research/schema-trace-all-weapons.json`
- `research/missing-fixed-skill-forensics.json`

The `.47` forensic report completed over 5,091 candidate files and covered all 11 unresolved codes, all 14 public ownerless weapons, six architecture branches, nine high-value modules, and 26 functions.

Important structural result:

The 14 public ownerless records remain a coherent class:

```text
fixed_skill_code present
passive_skill_data owner absent
endow = false
plaques empty
base_attr E0100/E0200/E0300 = 0
correct_skill absent
correct_term_id absent
```

Normal resolved controls commonly carry non-zero base-attribute and/or correction payloads. This supports the narrow conclusion that the 14 do not use the conventional fixed-passive/correction payload used by ordinary special-effect weapons.

It does **not** prove they have no mechanic.

## Public ownerless fixed-skill class

14 normal public weapons collapse to 11 codes:

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

Keep the extra 15 ownerless codes in the wider 26-code population separate; they are not the same public-normal weapon class.

## Current branch interpretation

### Generic fixed-skill helper path

`.47` showed the generic path:

```text
get_fixed_skill_default_data
→ blueprint fixed skill + level
→ get_skill_data
→ PassiveSkillHelper-compatible presentation/data access
```

The helper stack exposes name/title/rarity/icon/description/rich-description/sub-skill/copywriting concepts. Ordinary fixed skills therefore expect a skill representation resolvable by the helper architecture.

### Stardust branch

No independent rescue path proven. Current evidence still travels through fixed skill → passive skill data → star skill → stardust skill data.

### Server buff branch

No independent owner proven. Current evidence still travels through skill code → passive skill data → buff id.

### Player-facing UI

No independent UI-only owner proven. `WRGunInfoPart.update_fixed_skills` still uses `PassiveSkillHelper` / skill-data structures for presentation.

These negative branch results are useful because they prioritize the routing/normalization and damage-mapping branches.

## Immediate next action

1. Update installed Miner to **v1.5.14.48**.
2. Open **Research Console → Compiler**.
3. Click **COMPILE DATA INTELLIGENCE**.
4. Send the newest `Dead-Signal-Intelligence-*.zip`.
5. Confirm it contains `research/missing-fixed-skill-forensics.json`.
6. Inspect these exact entries first:
   - `helper_fallback_resolution` → `SkillDataHelper.pyc` → `get_table_name`
   - `helper_fallback_resolution` → `SkillDataHelper.pyc` → `is_passive`
   - `guncore_normalization` → `GunCoreHelper.pyc` → `<module>` and `climp_skill_code`
   - `damage_passive_mapping` → `CompShootDamageSimulateClient.pyc` → `<module>` and `get_weapon_passive_skill_config`
7. Correlate raw wordcode arguments only against the emitted indexed name/constant pools. Do not apply a guessed local opcode table.
8. Follow only exact identifiers proven by those functions into NeoX typed-owner tables.
9. If those routes still do not prove an alternate owner, keep the 14 mechanics unresolved rather than importing community descriptions.

## Research doctrine

Use:

**Locate → Inspect → Follow → Verify**

- Identity Map / Evidence Graph = locator only.
- NeoX Explorer = structured-table microscope.
- Guided Schema Trace = typed-owner semantic proof.
- Missing Skill Forensics = bounded static architecture investigation.
- Raw wordcode + indexed pools = exact byte evidence, not automatically decoded semantics.

Never execute Once Human bytecode.

## Existing parked blockers

- Magazine aggregation remains unresolved; keep Magazine unpublished.
- One weapon-description translation conflict remains quarantined.
- The 14 ownerless public fixed-skill weapons remain mechanically unresolved until an alternate exact chain is proven.
- Competitor UX work remains lower priority while this blocker is active.

## Non-negotiables

- Work directly on canonical `main` unless explicitly told otherwise.
- Installed-game / Miner evidence outranks guesses and community databases.
- Never execute game bytecode.
- Never promote fuzzy IDs, substring similarity, bare-number matches, or global scalar collisions into proof.
- Missing passive ownership does not prove no player-facing mechanic.
- Weapon Description and Special Skill remain separate evidence lanes.
- Do not publish local Miner snapshots, `reference-tracer.sqlite`, research notes, full NeoX exports, or raw evidence bundles.
- Do not touch pre-existing `tools/miner.zip`.
- Preserve copy-only cPanel deployment and accepted site architecture.
- Do not touch DNS, SSL, redirects, domain, or cPanel hosting configuration.
- Preserve the accepted landing page and Official Once Human X feed.
- Keep unfinished routes `SOON`.
