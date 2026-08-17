# Dead Signal — Weapon Forensics / Miner Handoff

> **Date:** 2026-08-16
> **Repository:** `raiinman/dead-signal`
> **Branch:** `main`
>
> Read `AI-CONTINUITY.md` and `PROJECT-RULES.md` first. This file is the current-session delta for the active Weapon evidence investigation and supersedes the older Build Lab handoff as the immediate research objective.

## Current objective

Finish the player-facing Weapons database using exact installed-game evidence, with special attention to the **14 public weapon records whose `fixed_skill_code` has no matching `passive_skill_data` owner**.

Do not assume these weapons have no mechanic merely because the conventional passive-skill row is absent. The user explicitly corrected the framing: they may not have a conventional passive skill, but they should still have a player-facing description, identity, or some alternate presentation/mechanic path.

The active question is therefore:

> **What distinguishes the 14 normal public weapons that carry a fixed-skill code but do not resolve through the conventional passive-skill/correction payload, and what player-facing path does that class use instead?**

## Stable Miner release

Miner **v1.5.14.42** is RELEASED and stable.

Release source commit:

- `7269a106a7578d5d07df9d44a0835baeaa3107ab` — `Release Miner v1.5.14.42`

Release workflow:

- GitHub Actions run `31986930652` — **SUCCESS**
- Source tests: PASS
- Windows build: PASS
- Packaged self-test: PASS
- Release packaging: PASS
- GitHub release publication: PASS
- Public ZIP verification: PASS
- Updater manifest published last: PASS

Stable updater manifest:

```json
{
  "schema_version": 1,
  "version": "1.5.14.42",
  "channel": "stable",
  "download_url": "https://github.com/raiinman/dead-signal/releases/download/miner-v1.5.14.42/Dead-Signal-Miner-v1.5.14.42-Windows.zip",
  "sha256": "a7e2465e54a2e141ecd66f91345e3c571a3de85a719c60151f1c6eb3ddba0d2d",
  "size": 133438404,
  "notes_url": "https://github.com/raiinman/dead-signal/releases/tag/miner-v1.5.14.42"
}
```

Installed Miners should now see `.42` through normal **Check for Updates** behavior.

## Full NeoX export investigation

The user provided a complete NeoX structured-table export produced by the Miner. The export was inspected as research evidence only and is **not committed or published**.

Completeness observed in that export:

- 41,757 table files plus manifest
- 41,340 catalogued tables
- zero expected-table files missing
- approximately 1.43 GB of exported structured NeoX source data

Important policy remains unchanged:

- do not publish the full export;
- do not commit raw snapshots, `reference-tracer.sqlite`, research bundles, or machine-specific evidence paths;
- use the export as a discovery corpus, not automatic publication authority.

## Exact unresolved fixed-skill evidence

The original public unresolved fixed-skill codes remain:

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

Across the complete structured NeoX export, each of these exact strings appears only in:

- `game_common/data/gun_blueprint_attr_data`

There is no alternate structured NeoX table containing those exact code strings.

The larger `fixed_skill_code` population contains additional ownerless codes, but those extra records are **not equivalent to the 14 public unresolved weapons**. Many of the additional ownerless entries have no normal `gun_blueprint_data` identity and appear orphaned/stale/config-only/hidden/nonstandard. Keep those populations separate.

## Public unresolved population

The 11 unresolved codes map to **14 normal public weapon identities** because some codes are shared by multiple public blueprints.

Known public examples include:

- SR2000 / WA2000 Jungle Camouflage — `WS1001`
- DE.50 Goshawk — `WS1101`
- MPS7 Focus — `WS1301`
- MPS7 Urban Ninja — `WS1301`
- SOCR Sand Dancer — `WS1402`
- SR2000 Die Another Day — `WS14503`
- SN700 Dark Snowflake — `WS1501`
- DBSG Format — `WS15203`
- MPS7 Chaos Domain — `WS15304`
- HAMR Hannya — `WS15502`
- MG4 Sandstorm — `WS1601`
- R500 Interfade — `WS2001`
- G17 Cash Only — `WS2001`
- OIC-8 Last Carnival — `WS2001`

These are normal player-facing weapons with blueprint/item/gun/name/icon/rarity/brand/prototype identity. They are not simply missing item records.

## Presentation identity finding

Exact item-ID searches show these weapons have normal `item_data` records with:

- localized name payload
- `item_type_name`
- `forge_icon`
- `icon`
- `icon_equip`
- normal item/equip identity fields

However, no direct player-facing weapon description field was found by exact item ID in the obvious structured tables.

The `$S@TIDS$` suffix embedded in name strings is **not proven to be a unique global description identifier** and should not be treated as one without further resolver evidence.

Therefore the current model separates two independent paths:

1. **Mechanical identity** — blueprint → `fixed_skill_code` → conventional passive/correction system or alternate system.
2. **Presentation identity** — item/blueprint → name/icon/type/detail UI/localization path.

Do not collapse those into one problem.

## Complete-vs-incomplete control comparison

A known conventional complete weapon such as AUG / Electron Cloud was compared against OIC-8 / Last Carnival.

Conventional complete weapon behavior includes:

- `fixed_skill_code` has a matching `passive_skill_data` owner;
- player-facing passive skill fields resolve through that owner;
- blueprint term rows can carry `correct_skill` and `correct_term_id`;
- blueprint specialization attributes may contain nonzero E0100/E0200/E0300 values;
- plaques/correction metadata may be populated.

Last Carnival and the other unresolved public weapons instead terminate at their exact `fixed_skill_code` and do **not** acquire the conventional passive owner/correction payload.

The critical interpretation is narrow:

> These weapons do not use the conventional fixed-passive/correction payload. This does **not** prove they have no player-facing description or mechanic.

## Catalogue-wide structural test

A catalogue-wide classification test was run over normal `blueprint_template_no = 10` weapon blueprints.

`endow=false` by itself is **not** the answer. There are resolved weapons with `endow=false` and valid passive owners.

The important unresolved fingerprint is the combined structure:

```text
fixed_skill_code present
passive_skill_data owner absent
endow = false
plaques empty
base_attr E0100/E0200/E0300 = 0
correct_skill absent
correct_term_id absent
```

That fingerprint isolates the same 14 public unresolved weapons rather than a random mixture of weapon records.

A slightly reduced fingerprint also isolates the class:

```text
fixed_skill_code present
plaques empty
base attrs all zero
correct_skill absent
correct_term_id absent
```

This is strong structural evidence that the 14 are a consistent configuration class, not 14 unrelated damaged records.

Do not assign runtime semantics to that class yet.

## New cohort-diff tracer

The Miner now contains a dedicated exact structural cohort tracer:

- `tools/miner/src/dead_signal_fixed_skill_cohort_diff.py`

Commits:

- `6674d9fcf78ae7ef181c962b05fa046ea64f0d6d` — `Add fixed-skill cohort fingerprint trace`
- `02269fdd056422d654febff569d360cf27f069da` — `Test fixed-skill cohort fingerprint trace`

Its purpose:

- read installed `gun_blueprint_attr_data` and `passive_skill_data` read-only;
- isolate the unresolved structural cohort;
- build a same-`endow=false` resolved control cohort with exact passive ownership;
- flatten blueprint fields;
- report field-path presence/value-shape differences between cohorts;
- never fuzzy-match identities;
- never execute game bytecode;
- never publish player-facing data automatically.

The first Windows CI for the tracer was green:

- GitHub Actions run `31986640147` — **SUCCESS**

## Missing Skill Forensics integration

The cohort tracer is integrated into the real Missing Skill Forensics pipeline.

Commits:

- `60c8350995596efd0a627acdfc0bdbc0a9868216` — `Integrate fixed-skill cohort diff into forensics`
- `420e3385316154a6a430d30414b4926af5515282` — `Test cohort diff forensics integration`

`missing-fixed-skill-forensics.json` is now schema v6 and includes:

- `fixed_skill_cohort_diff`
- normal weapon blueprint count
- unresolved cohort count
- same-endow resolved control count
- exact discriminating field-path count
- per-field unresolved-vs-control summaries

Integration CI:

- GitHub Actions run `31986799306` — **SUCCESS**

The new `next_step` in the report explicitly instructs the researcher to rank cohort field differences and follow only exact candidate fields into their owning tables/consumers.

## Existing fixed-skill architecture evidence remains valid

Do not discard the earlier static architecture work.

Known direct/static consumer areas still include:

1. damage/passive mapping
2. GunCore normalization
3. star/stardust resolution
4. player-facing weapon-craft UI

Key modules previously isolated include:

- `dcs_extend/component/shoot_new/keyword/CompShootDamageSimulateClient.pyc`
- `dcs_extend/component_server/CompSkillMgr.pyc`
- `game_common/guncore/BluePrintHelper.pyc`
- `game_common/guncore/GunCoreHelper.pyc`
- `dcs_extend/component/CompCamera.pyc`
- `dcs_extend/common/shoot_utility.pyc`
- `ui/weapon_craft_part/ScrollViewItems.pyc`

These establish static adjacency only. They do not prove runtime values or allow heuristic substitution for the missing 11 codes.

## Research doctrine

Use:

**Locate → Inspect → Follow → Verify**

- Evidence Graph / Identity Map = discovery map.
- NeoX Explorer = exact structured-table microscope.
- Guided Schema Trace = semantic typed-owner proof path.
- Missing Skill Forensics = bounded static consumer/architecture research.
- Cohort Diff = exact structural discriminator between unresolved and resolved controls.

Do not return to broad brute-force graph traversal when a typed owner-field or cohort discriminator can narrow the search.

## Immediate next sequence

1. Update the installed Miner to **v1.5.14.42**.
2. Run a fresh complete Weapon Schema Trace / Missing Skill Forensics pass against the current installed client.
3. Open `missing-fixed-skill-forensics.json`.
4. Inspect `fixed_skill_cohort_diff.record_counts` first.
5. Confirm the real installed-data unresolved cohort still matches the expected 14 public records.
6. Rank `fixed_skill_cohort_diff.field_diff` by fields that are systematically present/absent or structurally different across the unresolved cohort versus same-`endow=false` resolved controls.
7. For promising fields, trace the exact field owner/consumer. Do not infer semantics from the field name alone.
8. In parallel, continue the independent presentation-path investigation for item detail/description UI and localization consumers.
9. If a field leads to an alternate mechanic/presentation system, prove the exact chain before changing public weapon records.
10. If no alternate system exists, preserve the unresolved state rather than fabricating mechanic text.

## What to request from the user after the fresh run

Prefer the smallest relevant research reports rather than a new full raw export.

Most useful files:

- `missing-fixed-skill-forensics.json`
- `schema-trace-all-weapons.json`
- a compact evidence export for one representative unresolved weapon if the cohort diff identifies a promising field

Do **not** ask for raw snapshots or the complete NeoX archive unless the compact reports prove insufficient.

## Parked items

- Magazine reconstruction remains parked. Do not restore Magazine until the exact `get_gun_magazine_size` contribution chain is proven.
- Do not resume broad competitor UX work while this weapon-evidence blocker is active unless the user changes priority.
- Build Lab Weapon Selector geometry was previously stabilized; see `HANDOFF-2026-08-15-BUILD-LAB.md` for that history. The current priority is weapon evidence/forensics.

## Non-negotiables

- Work directly on canonical `main` unless the user explicitly says otherwise.
- Installed-game / Miner data outranks guesses and community databases.
- Never execute game bytecode.
- Never promote fuzzy/similar IDs into authoritative evidence.
- Missing recipe evidence never proves non-craftable.
- Missing passive owner does not prove no player-facing mechanic or description.
- Never publish local Miner snapshots, `reference-tracer.sqlite`, research notes, full NeoX exports, or raw evidence bundles.
- Do not touch pre-existing `tools/miner.zip`.
- Do not route work to Perplexity unless the user explicitly reverses that decision.
- Preserve copy-only cPanel deployment and accepted site architecture.
- Do not touch SSL, DNS, redirects, domain, or cPanel hosting configuration.
- Preserve the accepted landing page and Official Once Human X feed.
- Keep unfinished routes `SOON`.
