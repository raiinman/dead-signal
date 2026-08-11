# Dead Signal — AI Continuity / Handoff

> **Purpose:** Canonical handoff for future ChatGPT/Codex sessions working on Dead Signal. Read this file **before changing anything**. Update it after meaningful milestones, architecture/deployment discoveries, major data changes, miner discoveries, or significant UI decisions.
>
> Last updated: **2026-08-10 22:52 MST**

## 1. Project identity

- Project: **Dead Signal Ultimate Planner**
- Game: **Once Human**
- Repository: `raiinman/dead-signal`
- Branch: **`main` only** unless the user explicitly requests otherwise.
- Live planner: `https://deadsignaldb.com/build-planner/`
- Hosting: Namecheap shared hosting / cPanel.
- Production planner target: `$HOME/public_html/build-planner/`
- User deploy workflow: cPanel → Git Version Control → **Update from Remote** → **Deploy HEAD Commit** → hard refresh (`Ctrl+F5`) if needed.
- Current planner release line: **PLAYER v1.5.0**
- Current planner handoff commit before this continuity update: `d2c987c0866bfddab3109e71ad462b5aa2e80496`

## 2. Non-negotiable deployment rule

**Do not invent a new deployment workflow.**

Namecheap shared hosting proved unreliable when `.cpanel.yml` performed runtime/build work such as Python, recursive scans, archive reconstruction/extraction, data transforms, or outbound release downloads.

A minimal deployment and then the current static deployment proved that **copy-only cPanel deployment is reliable**.

### HARD RULE

> **Build/transform before deployment. cPanel only copies prepared static files.**

Current `.cpanel.yml` may use lightweight `mkdir`, `cp`, `rm`, and `echo`. Do **not** reintroduce Python, `find`, unzip/build chains, runtime patching, external downloads, or corpus rebuilding into normal cPanel deploys.

Persistent game PNGs under `/public_html/build-planner/assets/reference-images/` stay on hosting and are not recopied/scanned every deploy.

The first meaningful copy-only deployment that fully completed was:

`c3a62dbb414ad1368850f60032890b4b4f0d75d4`

## 3. Current Build Lab / UX direction

The planner is a full-width tactical Build Lab rather than a cramped dashboard.

Confirmed direction:

- Real hosted weapon and armor images display in picker/selected cards.
- Sidebar Signal Status/radar block was removed; it belongs to the main site, not the planner workspace.
- Cradle Overrides is a contained tactical sub-card with its own internal scroll.
- Loadout Report is below the workspace rather than consuming a permanent right rail.
- Left navigation includes a Loadout Report jump link.
- Typography/readability was increased; tiny body/detail text is not the design target.
- Readability outranks maximum information density.
- Prefer small, visible, screenshot-driven iterations over giant rewrites.

### 3.1 Build-mode UX — IMPORTANT

The planner has two highly prominent modes:

1. **MY GEAR — ACTUAL BUILD**
   - Default/safer mode.
   - Dead Signal fills deterministic game data automatically.
   - The user enters only server/account-specific RNG that public game files cannot know.
   - Example: exact RNG values on a Calibration Blueprint the player actually owns.

2. **GOD ROLL — THEORETICAL BUILD**
   - Deliberate, obvious selection.
   - Uses legal maximum RNG values for theorycrafting/build comparison.
   - Must clearly state that these values may not match owned gear.

The mode selector must remain large and hard to miss. The active mode must remain visible. Eventually the mode must be embedded in save/export/share payloads so a shared God Roll cannot be mistaken for owned gear.

### 3.2 RNG input decision — UPDATED

**Do not use sliders for Calibration RNG.**

The synchronized-slider experiment was removed because it caused poor interaction/re-render behavior and visual clutter.

Current approved My Gear control:

- exact numeric `%` input only
- show the legal range beside/above it
- validate/clamp against the legal range
- use 0.1% increments where the game does

God Roll should show the locked legal maximum value rather than a disabled slider.

This supersedes the older “slider + numeric field” handoff rule.

## 4. Calibration Blueprint UX — CURRENT APPROVED FLOW

Calibration is part of crafting the weapon and belongs directly under Gear Tier / Blueprint Stars, **before** Ammo, Weapon Mod, and accessories.

Approved weapon-card order:

```text
Gear Tier
Blueprint Stars
Calibration Style / Mod Type
Calibration Blueprint rarity/record
Weapon DMG RNG input
Secondary Attribute
Secondary RNG input
Ammo
Weapon Mod
Accessories
...
```

### 4.1 Style-first picker

The old flat list of rarity-duplicated Calibration Blueprint records was too confusing.

Build Lab v1.5.0 introduced a two-step picker:

1. **Calibration Style / Mod Type first**
   - examples: `Energy`, `Heavy`, `Precision`, `Rapid`, `Vanguard`
2. **Rarity second**
   - show only Rare / Epic / Legendary native records available for that chosen style

The native Calibration Blueprint record remains the underlying source of truth for item ID, compatibility, rarity, etc.

For the current AUG-compatible corpus, 13 native calibration records collapse to five first-step Style choices:

- Energy
- Heavy
- Precision
- Rapid
- Vanguard

Current style labels are **derived from the blueprint name** (for example `Rapid Assault Rifle` → `Rapid`). They are temporary until the miner publishes the exact canonical localized Style name.

Files:

- `preview/build-lab/calibration-style-picker.js`
- `preview/build-lab/calibration-style-picker.css`
- `RELEASE-v1.5.0.md`

### 4.2 Calibration picker-card presentation

The user explicitly rejected RNG/stat boxes on picker cards.

Calibration picker cards should remain clean:

- item/calibration name
- rarity
- description
- no Weapon DMG RNG box
- no “Random on drop” attribute box
- no four-secondary pool dump
- no legacy `Current Calibration` label

RNG selection/input belongs **after the Calibration Blueprint is selected on the weapon**, not on picker cards.

### 4.3 Calibration selected-card controls

After selection in My Gear:

- exact Weapon DMG roll input
- choose which one random secondary the owned item rolled
- exact secondary value input

In God Roll:

- main Weapon DMG uses legal max
- selected secondary uses legal max
- do not invent an automatic “best secondary for this build” optimizer until that logic is explicitly designed

## 5. Shared readability / accessibility

Canonical shared files:

- `shared/readability.css`
- `shared/readability.js`

Build Lab loads them as:

- `/build-planner/readability.css`
- `/build-planner/readability.js`

Supported modes:

- `compact`
- `default`
- `large`
- `xlarge`

Build Lab exposes `A− / A / A+ / A++` and stores the preference in origin-wide localStorage:

`dead-signal-font-size`

The editable WordPress theme source is not currently present in this repo. Do not claim the main WordPress site is already wired to the readability system.

## 6. Current production/static files

The copy-only cPanel deployment currently copies prepared files including:

- `preview/build-lab/index.html`
- `preview/build-lab/build-lab.css`
- `preview/build-lab/media-enhancements.css`
- `preview/build-lab/density-enhancements.css`
- `preview/build-lab/planner-cleanup.css`
- `preview/build-lab/build-mode.css`
- `preview/build-lab/build-mode.js`
- `preview/build-lab/weapon-model.css`
- `preview/build-lab/weapon-model-ui.js`
- `preview/build-lab/weapon-layout.css`
- `preview/build-lab/weapon-layout.js`
- `preview/build-lab/calibration-details.css`
- `preview/build-lab/calibration-rules.js`
- `preview/build-lab/calibration-details-ui.js`
- `preview/build-lab/calibration-style-picker.css`
- `preview/build-lab/calibration-style-picker.js`
- `preview/build-lab/wm-data-01.js` … `wm-data-08.js`
- `shared/readability.css`
- `shared/readability.js`
- `preview/build-lab/armor-image-map.js`
- `preview/build-lab/player-images.js`

No runtime transformation belongs in deployment.

## 7. Image architecture

### Master assets

The complete mined image/archive set is approximately **3 GB**, split into seven 7-Zip volumes (`assets.7z.001`–`.007`). These are archival/source assets and should **not** be pushed into normal Git history or normal web deployment.

GitHub Release:

`game-assets-2026-08-09`

### Slim player image pack

`dead-signal-player-images-v1.3.zip`

- size: `13,265,970` bytes
- SHA-256: `baaeccd8940cdc31c82d87d7c51c80c4bfe6986597ef42bc79602215571a6358`
- exactly **712 PNGs**

The user manually uploaded/extracted this pack on Namecheap. PNGs persist under:

`public_html/build-planner/assets/reference-images/`

### Armor image coverage

- 173 armor records
- 173/173 have image references
- 173/173 resolve to physical PNGs
- 172 unique physical armor PNGs because two records share one image

Static exact mapping:

`preview/build-lab/armor-image-map.js`

## 8. Current player-facing / raw database baseline

Normalized/player-facing baseline:

- Weapons: **120**
- Armor: **173**
- Armor Sets: **23**
- Mods: **817 entries / 105 families** in the older planner-facing corpus
- Planner Attachments: **108** in the older normalized planner corpus
- Current Calibrations: **94**
- Unique player-facing Deviations: **97**
- Unique player-facing Cradles: **120**
- Usable Ammo: **144**
- Build-relevant Consumables: **150**

Latest miner run (v1.5.7.2, before combat-resolution crash) reported raw/current-normalization counts:

- mods: 1,618
- calibrations: 188 raw = 94 current + 94 legacy
- ammo: 187
- attachments: 202
- cradles: 170
- deviations: 160
- consumables: 1,086
- buffs: 3,841 records / 11,046 buff definitions
- statuses: 24
- keywords: 10
- skills: 590
- stat definitions: 838
- progression: 1,563

Latest armor normalization in that run:

- armor sets: 23
- armor set pieces: 133
- key armor: 40
- armor pieces: 173
- tier stat rows: 850
- translation misses: 0

Latest weapon normalization in that run:

- weapons: 120
- ranged: 95
- melee: 25
- tier stat rows: 600
- blueprint attribute rows: 545
- blueprint-star axis validated: true
- preset-attack-ratio coverage complete: true
- current recipes: 530
- translation misses: 0

Raw attachment data contains 202 records. The stat-aggregator investigation identifies **119 actual weapon-slot accessories**:

- Sight: 30
- Muzzle: 36
- Tactical: 36
- Magazine: 17

Do not dump all 202 raw rows into the player picker.

## 9. Game Miner / factual hierarchy

For factual game data use:

1. **Game Miner / installed game files**
2. OnceHumanDB
3. Wikily
4. Official Once Human sources for patch/system corrections and authoritative change notes

Do not blindly expose internal/runtime rows. Filter to player-visible/current data.

The miner parsed Once Human `script.npk` with **0 parse errors**.

`reference-tracer.sqlite` is roughly 255 MB with ~1.35M occurrences. **Do not upload it to normal production.**

## 10. Actual miner package / source layout

The user supplied the real Dead Signal Miner package. Do not repeat the earlier mistake of patching only a repo-side probe when the user asks to patch the miner.

Source modules ship under:

`_internal/extractor/`

Important modules include:

- `weapon_progression.py`
- `normalize_weapons.py`
- `combat_resolver.py`
- `export_bindict.py`
- `normalize_extended.py`
- `npk_extract.py`

The packaged runtime uses Python 3.11. Validate modified extractor source against Python 3.11 before packaging. Remove stale `__pycache__` for modified modules before ZIP creation.

Game PYC files use Python 3.11 magic but have remapped/transformed opcodes. **Stock `dis` is not authoritative.** Use code-object metadata, raw wordcode, known remapped tails, constants/names/locals, and corroborating data tables. Do not execute game bytecode.

The GUI window still displays **Dead Signal Miner 1.4.0** even for patched 1.5.x packages. Identify the running patched build by its extracted folder/package name and traceback path, not the GUI title.

## 11. Blueprint Stars × Gear Tier — SOLVED

### Separate axes

- `corr_forge_lv = [1,2,3,4,5]` = **Gear Tier I–V**
- `strength_lv` = **Blueprint Star level**

Rarity caps:

- Common: up to 3★
- Rare: generally up to 4★
- Epic: up to 5★
- Legendary: up to 6★

Never conflate Gear Tier and Blueprint Stars.

### Per-weapon Tier values

There is **no universal Tier multiplier** that reproduces all weapons. Store mined Tier values per weapon.

SOCR — Outsider:

- T1 41
- T2 62
- T3 100
- T4 156
- T5 237

SKS — Pathfinder:

- T1 94
- T2 144
- T3 230
- T4 360
- T5 547

### Blueprint Star behavior is per weapon

- 82 weapons progress via `preset_attack_radio`
- 13 via `fixed_skill_lv`
- 25 change neither field in current progression data
- 0 current weapons change both

Pathfinder legendary Star ratio curve:

`[1.00, 1.05, 1.10, 1.15, 1.20, 1.25]`

`preset_attack_radio` is a **direct multiplier**.

### Proven intrinsic Attack formula

```text
IntrinsicAttack =
int(
    gun_preset_attack[GearTier]
    * preset_attack_radio[BlueprintStars]
)
```

For positive Attack this is truncation toward zero / floor-equivalent.

Pathfinder T5 6★:

```text
547 × 1.25 = 683.75
int(...) = 683
```

Do **not** round this stage to 684.

## 12. Calibration Blueprint model — CURRENT MINED UNDERSTANDING

Current calibration is the post-Jan-21-2026 system and is separate from intrinsic Tier/Stars.

A dropped current Calibration Blueprint has three conceptually separate layers.

### 12.1 Fixed Calibration Style

Each current calibration carries a deterministic **Style** linked through buff data.

The miner already sees:

- Style buff ID / level
- underlying Style mechanics
- fixed stat/effect contributions for many styles
- logic-tree/buff relationships

Current investigation status from the 94 current calibrations:

- all 94 have Style linkage
- 73 were structurally fully resolved in the prior investigation
- 21 were partial due to more complex buff/keyword logic
- ~329 individual Style effects were resolved across the set

Examples of deterministic Style behavior seen in game/screenshots and consistent with mined mechanics include:

- Rapid Shot style: Fire Rate / Magazine / Attack changes
- Vanguard style: reload-from-empty → guaranteed keyword-trigger behavior

**Important:** the exact player-facing localized Style **name and description** are not yet published into the planner. That is the active v1.5.7 investigation.

### 12.2 Guaranteed Weapon DMG RNG

Every one of the **94 current Calibration Blueprint records** has the main calibration `affix_val_range`.

Current distribution:

- 24 Rare: **18%–25%**
- 35 Epic: **26%–33%**
- 35 Legendary: **34%–50%**
- zero current exceptions

Generation path includes `random.uniform(min,max)` and rounding on the raw fraction; UI values use 0.1% precision.

This main roll maps into **`D0102`** and joins the weapon Attack-ratio bucket.

Weapon DMG is therefore a guaranteed calibration RNG stat; the value is random, the stat identity is not.

### 12.3 One random secondary

The drop also rolls **one** secondary attribute from the current weighted pool.

Current candidates / legal ranges by rarity:

**Rare**
- Weakspot DMG 12–18%
- Crit Rate 8–12%
- Elemental DMG 12–18%
- Crit DMG 20–30%

**Epic**
- Weakspot DMG 15–21%
- Crit Rate 10–14%
- Elemental DMG 12–18%
- Crit DMG 25–35%

**Legendary**
- Weakspot DMG 18–24%
- Crit Rate 12–16%
- Elemental DMG 15–20%
- Crit DMG 30–40%

Current observed weights are 200/200/200/200, i.e. equal-weight in this snapshot.

Do **not** present all four as active stats on a calibration card. Only one is rolled on an owned dropped blueprint.

### 12.4 +7/+10 options are separate

Recovered global:

`calibration_option_gun = [7, 10]`

These belong to the weapon-calibration option system and are **not** the same as the dropped blueprint’s random secondary. Keep separate in data model and UI.

## 13. Calibration Style localization bridge — ACTIVE INVESTIGATION

The missing player-facing Style text was traced to `buff_level_data`.

The current client uses fields such as:

- `buff_template_id`
- `buff_lv`
- `buff_desc`

The normalizer had been looking primarily for older aliases such as:

- `buff_id`
- `level`
- `desc`

This explains why mechanics were present while the nice Style description stayed blank.

The v1.5.7 patch adds current-field aliases and attempts to resolve `buff_desc` through the English translation/TIDS data, while preserving:

- raw source description
- localized description
- localization status
- Style buff ID/level
- resolved Style mechanics

A Vanguard-style raw record was observed to contain the source description corresponding to the “after reloading from empty…” effect plus a localization token.

Goal of the next successful run:

- exact localized Style description
- canonical Style name if present in game data
- explicit report if only description resolves but name remains absent

Do not invent Style text in the planner. Use derived short names only until canonical text is mined.

## 14. Static weapon-card Attack aggregator — SOLVED

Static affix sources include:

- `base_affix_add`
- `accessory_affix_add`
- `rand_affix_add`
- `affix_option_add`
- `cal_affix`
- `correct_affix_add`

Canonical Attack IDs:

- `D0100` = base/flat Attack family
- `D0101` = Weapon DMG ratio
- `D0102` = Current Weapon DMG / calibration-related Attack ratio

`D0101` and `D0102` share the same additive ratio bucket.

```text
AttackRatio =
1
+ Σ(D0101)
+ Σ(D0102)

StaticAttackFloat =
IntrinsicAttack * AttackRatio
+ FlatAttackDelta
```

Do not compound D0101/D0102 as independent multipliers.

Example:

- calibration +42.7%
- suppressor -15%

Correct:

```text
1 + 0.427 - 0.150 = 1.277
```

Not `1.427 × 0.85`.

## 15. Final static Attack display — SOLVED

Prototype metadata:

- `D0100`: type 1, format `"{:.0f}"`
- `D0101`: type 2, format `"{:.1%}"`
- `D0102`: type 2, format `"{:.1%}"`

Important distinction:

- Tier/Star stage: real `int(...)` truncation
- final D0100 card: zero-decimal fixed-point formatting

The `int()` inside the generic formatter belongs to rate-format precision logic, not D0100 truncation.

Example:

```text
683 × 1.427 = 974.641
final D0100 display → 975
```

Do not apply a second truncation at the end.

## 16. Accessories / static stat families

Accessories feed the same generic stat engine.

Weapon accessory slots:

- Sight
- Muzzle
- Tactical
- Magazine

Important normalization fixes already made:

1. `gun_accessory_attr_data` can use direct `(stat_id, value)` pairs rather than only parallel arrays.
2. D0101/D0102 were initially dropped from normalized accessory stats; fixed.
3. v1.5.2.1 confirmed **40 raw D0101/D0102 attachment modifiers in, 40 resolved out**.

Known stat-family IDs:

- `Q0100` Stability
- `Q0300` Accuracy
- `Q0500` Range
- `Q0900` Fire Rate %
- `Q1100` Magazine Capacity flat
- `Q1101` Magazine Capacity %
- `Q1600` Mobility
- `Q2000` Drawing Speed %
- `Q2400` Reload Speed
- `Q2600` Bullet Velocity %

`Q1101` exposed a non-zero-suffix resolver hole; resolve variants generically through `affix_prototype_data`, not one-off hardcoding.

Future static-card targets remain:

- Fire Rate / RPM (`Q0800` + `Q0900`)
- Magazine (`Q1100` + `Q1101`)
- Reload
- Accuracy
- Stability
- Range
- Mobility
- Drawing Speed
- Bullet Velocity

## 17. Planner architecture rule

Do **not** build a collection of one-off formulas.

Mirror the game’s generic stat/affix architecture:

```text
Selected weapon / Tier / Stars
        + selected accessories
        + Calibration Blueprint Style
        + Calibration RNG
        + calibration-level options
        + other static affix sources
                ↓
        canonical stat contributions
                ↓
        stat-family aggregator
                ↓
        displayed static weapon card
```

Only server/account-specific RNG should require player entry in My Gear.

Runtime combat buffs/procs from armor sets, weapon mods, Cradles, Deviations, consumables, temporary statuses, etc. remain a **separate layer** until their direct consumer/order is traced.

## 18. Miner version history — KEY MILESTONES

Progression/combat investigation packages:

- v1.4.3 — Focus Consumer Code Capsules
- v1.4.4 — Proven Multiply + Caller Chain
- v1.4.5 — D0100 Display Chain
- v1.4.6 — Display Int Conversion Proven
- v1.4.7 — Calibration RNG Consumer Trace
- v1.4.8 — Calibration Attack Ratio + Weighted Drop Trace
- v1.4.9 — Calibration Layers + Combined Attack Bucket
- v1.5.0 — Generic Weapon Stat Aggregator + Accessory Trace
- v1.5.1 — Accessory Stat Map + Proven Static Attack
- v1.5.2 — Attack Affix Export Fix + Final Formatter Trace; had `STAT_CODE` crash
- v1.5.2.1 — `STAT_CODE` hotfix
- v1.5.3 — D0100 Final Formatter Branch Probe
- v1.5.4 — D0100 Prototype Export-Root Fix
- v1.5.5 — D0100 Final Display Rule
- v1.5.6 — Static Weapon Card Stat Families
- v1.5.7 — Calibration Style Localization Bridge
- v1.5.7.1 — Sparse Current Snapshot fallback hotfix; insufficient because preflight ran earlier inside EXE
- v1.5.7.2 — Embedded preflight hotfix; successfully got past missing current-table preflight, then exposed circular JSON reference at 82%
- **v1.5.7.3 — Circular Reference Diagnostic Hotfix — CURRENT NEXT-RUN BUILD**

## 19. v1.5.7.x crash chain — DO NOT REPEAT

### 19.1 Sparse current snapshot

The game’s current patch snapshot can be sparse: unchanged tables may exist only in the newest base snapshot.

The failing tables were:

- `char_property_data.json`
- `equip_origin_data.json`
- `buff_level_data.json`

v1.5.7.1 added base/current fallback/materialization in external extractor code, but the GUI still failed because the hard preflight was embedded in `miner_core` inside the EXE and ran before that fallback.

v1.5.7.2 patched the embedded preflight so only genuinely current-owned tables such as `item_data` / `equip_data` remain mandatory-current; stable tables may fall back to base.

Evidence that this fix works: the user’s v1.5.7.2 run completed armor, weapons, Mods/Calibrations/Ammo/Attachments/etc. and entered combat resolution instead of dying on missing normalized-data inputs.

### 19.2 Circular reference in `buffs.json`

The v1.5.7.2 run then failed at ~82%:

```text
CombatPipeline.run()
→ resolve_buff_file()
→ write_json(data_dir / "buffs.json", payload)
→ json.dumps(...)
ValueError: Circular reference detected
```

Traceback path proved the user was running the **v1.5.7.2** folder.

This is the current blocker before Style output can be inspected.

### 19.3 v1.5.7.3 current patch

Current package:

`Dead-Signal-Miner-v1.5.7.3-Circular-Reference-Diagnostic-Hotfix.zip`

SHA-256:

`db9047c79178b69e737dec9cb9f008c87bcdaee087f701a2a7324c4cecdfee32`

v1.5.7.3 keeps:

- Calibration Style localization bridge
- sparse current-snapshot fallback
- embedded EXE preflight fix

and adds:

- normal `json.dumps` first
- if and only if Python raises `Circular reference detected`, a structural safe-copy fallback cuts only the actual back-edge
- a diagnostic report intended to record the exact cycle path instead of hiding the bug

Expected diagnostic:

`reports/serialization-circular-references.json`

Do **not** use `check_circular=False`; that can recurse forever and does not solve the data problem.

### IMPORTANT NEXT ACTION

The user is about to provide output from a **real v1.5.7.3 run**.

When files arrive:

1. verify the run path/build was v1.5.7.3, not an older extracted folder
2. inspect `reports/serialization-circular-references.json` if present
3. inspect `published/data/calibrations.json`
4. inspect Style/localization fields:
   - Style buff ID/level
   - raw `buff_desc`
   - localized Style description
   - localization status
   - canonical Style name if recovered
5. remove the underlying circular reference at source if the diagnostic identifies it
6. only then wire exact Style descriptions into the planner

## 20. Historical miner bug worth remembering

v1.5.2 initially crashed around 82% because a patch wrote literal `\n` characters into a comment, leaving:

`STAT_CODE = re.compile(...)`

effectively commented out.

v1.5.2.1 fixed it.

When modifying miner source:

- syntax-check Python 3.11
- import-test modified modules
- scan for accidental escaped-newline/comment mistakes
- remove stale `__pycache__`
- test ZIP integrity
- prefer synthetic smoke tests for new serializers/resolvers

## 21. Planner feature baseline

Planner supports:

- 3 weapon slots
- Gear Tier / Blueprint Stars
- Calibration Style-first workflow
- Calibration rarity/native record
- exact Calibration Weapon DMG RNG entry
- Calibration secondary identity/value entry
- ammo
- weapon mods
- attachments
- 6 armor slots
- armor mods
- quick-equip armor sets
- Deviations
- Cradles
- consumables
- build identity/metadata
- Loadout Report
- rarity handling
- local save/templates
- import/export
- share links
- compatibility filtering
- prominent My Gear / God Roll mode

The project is beyond basic planner architecture. Current work is **data fidelity + exact stat engine reconstruction + calibration Style fidelity + actual-vs-theoretical UX**.

## 22. Current game-system modeling rules

Read `PROJECT-RULES.md` too.

Key rules:

- Gear Tier is I–V only.
- Blueprint Stars are separate.
- Blueprint Star behavior is per weapon.
- Current weapon calibration follows the post-Jan-21-2026 system.
- Calibration Style is deterministic.
- Calibration Weapon DMG is guaranteed RNG by rarity.
- Calibration secondary identity/value is one random drop attribute.
- +7/+10 weapon-calibration options are a separate system.
- Current Mod 2.0 behavior should be modeled instead of legacy random-subattribute assumptions.
- Static weapon-card math and runtime combat/proc math are separate.
- Never show all four calibration secondary possibilities as if all are active stats.
- Never invent missing Style descriptions.
- Readability/accessibility is canonical.

## 23. Files future sessions should read first

1. `AI-CONTINUITY.md`
2. `PROJECT-RULES.md`
3. `.cpanel.yml`
4. `preview/build-lab/index.html`
5. `preview/build-lab/calibration-style-picker.js`
6. `preview/build-lab/calibration-style-picker.css`
7. `preview/build-lab/calibration-details-ui.js`
8. `preview/build-lab/calibration-details.css`
9. `preview/build-lab/weapon-layout.js`
10. `preview/build-lab/weapon-model-ui.js`
11. `preview/build-lab/build-mode.js`
12. `preview/build-lab/planner-cleanup.css`
13. `shared/readability.css`
14. `shared/readability.js`
15. `preview/build-lab/player-images.js`
16. `preview/build-lab/armor-image-map.js`

For miner work, inspect the actual uploaded miner package/source under `_internal/extractor/`. GitHub sidecar probes are not the authoritative miner implementation.

Old `deploy/patch-*.py` files are historical artifacts and are not part of normal live deployment.

## 24. Immediate next steps

1. **Receive and inspect the user’s v1.5.7.3 output.**
2. Confirm whether the circular-reference diagnostic was generated and identify the exact back-reference.
3. Inspect Calibration Style localized descriptions and canonical Style names.
4. If exact Style text is recovered, publish it into the planner under the Style-first selection flow.
5. Keep Calibration picker cards clean; do not re-add RNG attribute boxes.
6. Continue exact static weapon-card stat-family work after the Style bridge is stable:
   - Q1101/prototype variants
   - Fire Rate/RPM
   - Magazine
   - Reload
   - Accuracy
   - Stability
   - Range
   - Mobility
   - Drawing Speed
   - Bullet Velocity
7. Reconcile older 108 planner attachments vs 119 identified true weapon-slot accessories.
8. Preserve copy-only cPanel deployment.
9. Later move to runtime combat layers with the same evidence-first approach.

## 25. Continuity rules for future AI sessions

- **Read this file first.**
- Do not create new branches unless the user asks.
- Work on `main`.
- Do not change deployment architecture without discussing it.
- Preserve copy-only cPanel deployment.
- Do not upload the 3 GB master archive or `reference-tracer.sqlite` to normal production.
- Keep real images on Namecheap under `assets/reference-images/`.
- Prefer installed-game/mined evidence over community guesses.
- Do not trust stock `dis` on transformed Once Human PYC without corroboration.
- Do not execute game bytecode.
- Prefer small, testable UI changes and screenshot/live iteration.
- Isolate the broken layer before changing unrelated code.
- Do not make the user re-explain project history when this file/repo can answer it.
- Update this file after major milestones.

## 26. User workflow preferences relevant to this project

- Direct action and live iteration are preferred over long abstract planning.
- The user is a **kinetic learner**; interactive/visual results are more useful than abstract prose.
- Screenshots/visual confirmation are valuable.
- Established workflows should not be changed without a strong reason.
- Keep deploy instructions compact and sequential.
- Accessibility/readability is explicitly a priority.
- Calibration RNG input preference is now **exact numeric fields only; no sliders**.
- Calibration selection should reflect the game’s mental model: **Style/Mod Type first**, then rarity/owned RNG.
- Avoid cluttering picker cards with information that belongs after selection.

---

### Continuity checkpoint

A future AI/Codex session should be able to resume without the original chat transcript.

**Critical handoff as of 2026-08-10 22:52 MST:** Blueprint Star × Gear Tier intrinsic Attack is solved; static Attack aggregation and final D0100 display are solved; Calibration Weapon DMG is a guaranteed RNG stat feeding D0102; one secondary is random; Calibration Style is deterministic and its mechanics are already mined; the live planner now uses a Style-first Calibration picker and exact numeric RNG entry; canonical localized Style text is the current mining target; v1.5.7.2 proved the sparse-snapshot preflight fix but crashed on a circular `buffs.json` payload; **v1.5.7.3 is the exact next-run build and the user is about to provide its output.**
