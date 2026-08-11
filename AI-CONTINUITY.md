# Dead Signal — AI Continuity / Handoff

> **Purpose:** Canonical current-state handoff for ChatGPT/Codex sessions working on Dead Signal. Read this file before changing anything. The prior full handoff is preserved verbatim at `archive/AI-CONTINUITY-2026-08-10-v1.5.0.md`.
>
> Last updated: **2026-08-10 23:55 MST**

## 1. Project identity

- Project: **Dead Signal Ultimate Planner**
- Game: **Once Human**
- Repository: `raiinman/dead-signal`
- Branch: **`main` only** unless the user explicitly requests otherwise.
- Live planner: `https://deadsignaldb.com/build-planner/`
- Hosting: Namecheap shared hosting / cPanel.
- Production planner target: `$HOME/public_html/build-planner/`
- User deploy workflow: cPanel → Git Version Control → **Update from Remote** → **Deploy HEAD Commit** → hard refresh (`Ctrl+F5`).
- Current player release: **PLAYER v1.5.1**
- PLAYER v1.5.1 commit: `acb25f0fb7682c914db98bfbe89a2daba33d8260`

## 2. Non-negotiable deployment rule

**Build/transform before deployment. cPanel only copies prepared static files.**

Namecheap shared hosting proved unreliable when `.cpanel.yml` performed Python work, recursive scans, archive reconstruction/extraction, data transforms, or outbound downloads.

Allowed deployment operations are lightweight `mkdir`, `cp`, `rm`, and `echo`. Do **not** reintroduce Python, `find`, unzip/build chains, runtime patching, external downloads, or corpus rebuilding into normal cPanel deployment.

Persistent game PNGs remain under:

`/public_html/build-planner/assets/reference-images/`

The first meaningful reliable copy-only deployment was commit:

`c3a62dbb414ad1368850f60032890b4b4f0d75d4`

## 3. Current Build Lab / UX rules

Dead Signal is a full-width tactical Build Lab, not a cramped dashboard.

Confirmed direction:

- Real weapon and armor images in picker and selected cards.
- Readability outranks maximum information density.
- Shared text-size system: `compact`, `default`, `large`, `xlarge`.
- Origin-wide preference key: `dead-signal-font-size`.
- Prefer small, visible, screenshot-driven iterations over giant rewrites.
- Loadout Report belongs below/with the workspace rather than consuming a permanent right rail.
- Cradle Overrides stays a contained tactical sub-card with internal scroll.

### Build modes

1. **MY GEAR — ACTUAL BUILD**
   - Default/safer mode.
   - Dead Signal fills deterministic game data.
   - Player enters only server/account-specific RNG that public game files cannot know.

2. **GOD ROLL — THEORETICAL BUILD**
   - Deliberate and visually obvious.
   - Uses legal maximum RNG values.
   - Must clearly state values may not match owned gear.

Eventually build mode must be embedded in save/export/share payloads so a God Roll cannot be mistaken for owned gear.

### Calibration RNG input

**No sliders.**

My Gear uses exact numeric `%` inputs, legal ranges, validation/clamping, and 0.1% increments where the game does. God Roll displays locked legal maxima.

## 4. Calibration Blueprint UX — current approved flow

Calibration belongs under Gear Tier / Blueprint Stars and before Ammo, Weapon Mod, and accessories.

Approved order:

```text
Gear Tier
Blueprint Stars
Calibration Style / Mod Type
Calibration Blueprint rarity/record
Fixed Calibration Style Effect
Weapon DMG RNG input
Secondary Attribute
Secondary RNG input
Ammo
Weapon Mod
Accessories
...
```

### Style-first picker

Two-step workflow:

1. **Calibration Style / Mod Type first** — examples: `Energy`, `Heavy`, `Precision`, `Rapid`, `Vanguard`.
2. **Rarity second** — only native Rare / Epic / Legendary records available for the chosen Style.

Native Calibration Blueprint records remain source of truth for ID, compatibility, rarity, etc.

Short Style labels are currently **derived from blueprint names**. The latest miner bridge recovered exact localized Style descriptions but still found **no canonical localized Style-name field**. Do not invent one.

### Picker-card presentation

Calibration picker cards may show:

- item/calibration name
- rarity
- exact mined fixed Style description

Do **not** re-add:

- Weapon DMG RNG boxes
- “Random on drop” boxes
- a four-secondary-pool dump
- legacy `Current Calibration` labels

RNG controls belong after selection on the weapon card.

## 5. PLAYER v1.5.1 — Calibration Style descriptions shipped

Commit:

`acb25f0fb7682c914db98bfbe89a2daba33d8260`

Release notes:

`RELEASE-v1.5.1.md`

New prepared static files:

- `preview/build-lab/calibration-style-display.js`
- `preview/build-lab/calibration-style-display.css`

`index.html` now identifies the planner as **PLAYER v1.5.1** and loads both files. `.cpanel.yml` only gained two copy commands for these prepared static assets; deployment remains copy-only.

The display map contains all **94 current Calibration Blueprint records**, keyed by blueprint name + rarity, and exposes the exact localized fixed Style description mined from the current client.

Examples:

- Rapid Assault Rifle — Legendary: `Fire Rate +20%, Reload Speed +10%, Attack -10%`
- Precision Assault Rifle — Legendary: `Attack +25%, Range +40%, Fire Rate -10%`
- Vanguard Rifle — Legendary: `After reloading from empty, the next shot is guaranteed to trigger its keyword effect.`
- Energy Rifle — Legendary: `After taking damage, automatically reload 1 bullet (cooldown: 0.3s). Attack +10%.`

Selected weapon cards now get a contained **FIXED CALIBRATION STYLE EFFECT** block before RNG controls.

## 6. Current database baseline

Player-facing / normalized baseline:

- Weapons: **120**
- Armor: **173**
- Armor Sets: **23**
- Current Calibrations: **94**
- Unique player-facing Deviations: **97**
- Unique player-facing Cradles: **120**
- Usable Ammo: **144**
- Build-relevant Consumables: **150**
- Older planner-facing Mods: **817 entries / 105 families**
- Older planner Attachments: **108**

Latest miner normalization snapshot:

- mods: **1,618**
- calibrations: **188 raw = 94 current + 94 legacy**
- ammo: **187**
- attachments: **202 raw**
- cradles: **170**
- deviations: **160**
- consumables: **1,086**
- buffs: **3,841 records / 11,046 buff definitions**
- statuses: **24**
- keywords: **10**
- skills: **590**
- stat definitions: **838**
- progression: **1,563**

Weapon normalization:

- weapons: **120**
- ranged: **95**
- melee: **25**
- tier stat rows: **600**
- blueprint attribute rows: **545**
- blueprint-star axis validated: **true**
- preset-attack-ratio coverage complete: **true**
- current recipes: **530**
- translation misses: **0**

Armor normalization:

- armor sets: **23**
- armor set pieces: **133**
- key armor: **40**
- armor pieces: **173**
- tier stat rows: **850**
- translation misses: **0**

Raw attachment data has 202 records, but the stat-aggregator investigation identifies **119 actual weapon-slot accessories**:

- Sight: 30
- Muzzle: 36
- Tactical: 36
- Magazine: 17

Do not dump all 202 raw rows into the player picker.

## 7. Game Miner / factual hierarchy

For factual game data use:

1. **Game Miner / installed game files**
2. OnceHumanDB
3. Wikily
4. Official Once Human sources for patch/system corrections and authoritative change notes

Do not blindly expose internal/runtime rows. Filter to player-visible/current data.

The miner parsed Once Human `script.npk` with **0 parse errors**.

`reference-tracer.sqlite` is roughly 255 MB with ~1.35M occurrences. Do **not** upload it to normal production.

## 8. Actual miner package / source layout

The real Dead Signal Miner source modules ship under:

`_internal/extractor/`

Important modules:

- `weapon_progression.py`
- `normalize_weapons.py`
- `combat_resolver.py`
- `export_bindict.py`
- `normalize_extended.py`
- `npk_extract.py`

Packaged runtime uses Python 3.11. Validate modified extractor source against Python 3.11 before packaging. Remove stale `__pycache__` for modified modules before ZIP creation.

Game PYC files use Python 3.11 magic but transformed/remapped opcodes. **Stock `dis` is not authoritative.** Use code-object metadata, raw wordcode, known remapped tails, constants/names/locals, and corroborating tables. Do not execute game bytecode.

The GUI window may still display **Dead Signal Miner 1.4.0** for patched 1.5.x packages. Identify running build by extracted folder/package name and traceback path, not GUI title.

## 9. Blueprint Stars × Gear Tier — SOLVED

Separate axes:

- `corr_forge_lv = [1,2,3,4,5]` = **Gear Tier I–V**
- `strength_lv` = **Blueprint Star level**

Rarity star caps:

- Common: up to 3★
- Rare: generally up to 4★
- Epic: up to 5★
- Legendary: up to 6★

No universal Tier multiplier reproduces every weapon. Store mined Tier values per weapon.

Blueprint Star behavior is per weapon:

- 82 weapons progress through `preset_attack_radio`
- 13 through `fixed_skill_lv`
- 25 change neither field in current progression data
- 0 current weapons change both

Proven intrinsic Attack formula:

```text
IntrinsicAttack = int(
    gun_preset_attack[GearTier]
    * preset_attack_radio[BlueprintStars]
)
```

For positive Attack this truncates toward zero/floor-equivalent.

SKS — Pathfinder T5 6★:

```text
547 × 1.25 = 683.75
int(...) = 683
```

Do not round this stage to 684.

## 10. Calibration Blueprint model — SOLVED CURRENT STRUCTURE

Current post-Jan-21-2026 Calibration Blueprints have three separate layers.

### Fixed Style

Style is deterministic. Current v1.5.7.4 evidence:

- current Calibration records: **94**
- Style linkage: **94 / 94**
- localized English Style descriptions: **94 / 94**
- missing localized descriptions: **0**
- mechanics: **73 structurally resolved / 21 partial**
- canonical localized Style names: **0 recovered**

Use exact descriptions. Keep derived short Style labels until canonical names are found elsewhere in game data.

### Guaranteed Weapon DMG RNG

Every one of the 94 current records has `affix_val_range`:

- Rare: **18%–25%** (24 records)
- Epic: **26%–33%** (35 records)
- Legendary: **34%–50%** (35 records)

Main roll maps to **`D0102`** and joins the weapon Attack-ratio bucket.

### One random secondary

Exactly one secondary is rolled from the current pool.

Rare:
- Weakspot DMG 12–18%
- Crit Rate 8–12%
- Elemental DMG 12–18%
- Crit DMG 20–30%

Epic:
- Weakspot DMG 15–21%
- Crit Rate 10–14%
- Elemental DMG 12–18%
- Crit DMG 25–35%

Legendary:
- Weakspot DMG 18–24%
- Crit Rate 12–16%
- Elemental DMG 15–20%
- Crit DMG 30–40%

Observed current weights are 200/200/200/200.

Do not present all four as active stats.

### +7/+10 options are separate

Recovered global:

`calibration_option_gun = [7, 10]`

This is a separate weapon-calibration option system, not the random secondary.

## 11. Static weapon-card Attack — SOLVED

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
- `D0102` = current Calibration Weapon DMG / Attack ratio

`D0101` and `D0102` use the **same additive ratio bucket**:

```text
AttackRatio = 1 + Σ(D0101) + Σ(D0102)
StaticAttackFloat = IntrinsicAttack * AttackRatio + FlatAttackDelta
```

Do not compound D0101/D0102 as independent multipliers.

Final D0100 card display uses zero-decimal fixed-point formatting, not a second truncation.

Example:

```text
683 × 1.427 = 974.641
final D0100 display → 975
```

## 12. Static stat families — next major model work

Known IDs:

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

`Q1101` exposed a non-zero-suffix resolver hole. Resolve variants generically through `affix_prototype_data`; do not one-off hardcode.

Next static-card targets:

1. Fire Rate / RPM (`Q0800` + `Q0900`)
2. Magazine (`Q1100` + `Q1101`)
3. Reload
4. Accuracy
5. Stability
6. Range
7. Mobility
8. Drawing Speed
9. Bullet Velocity

Planner architecture rule:

```text
Selected weapon / Tier / Stars
        + accessories
        + Calibration Style
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

Do not build a pile of one-off formulas.

Runtime combat buffs/procs from armor sets, mods, Cradles, Deviations, consumables, statuses, etc. remain a separate later layer until direct consumers/order are traced.

## 13. Miner v1.5.7.3 → v1.5.7.4 circular-reference resolution — SOLVED

v1.5.7.3 successfully diagnosed the previous `buffs.json` serialization crash.

It found **1,248** repeated cycles of one shape:

```text
$/buffs/<index>/raw_level_definition
    → back-reference to $/buffs/<index>
```

The source bug was in `combat_resolver.py` raw-level fallback. A missing `(buff_id, level)` lookup fell back to the normalized parent `level_record`, which could make:

```text
row["raw_level_definition"] = row
```

v1.5.7.4 changed the resolver to:

1. use exact raw `(buff_id, level)` when available;
2. if absent and requested level is not 1, try the actual raw level-1 record;
3. if still absent, use a detached deep copy of the normalized record rather than the parent object itself.

Package:

`Dead-Signal-Miner-v1.5.7.4-Raw-Level-Fallback-Source-Fix.zip`

SHA-256:

`dff5a8b5e9602e3964c365f90d219899ca0f86ef196813a1cb4d0a5a6ded88e2`

Real v1.5.7.4 output proved the fix:

- validation: **PASS**
- new `data/buffs.json`: **0** `_dead_signal_circular_reference` markers
- previous v1.5.7.3 output: **1,248** markers
- combat resolution counts remained stable: **2,711 resolved / 1,086 partial / 44 unresolved**
- Calibration localization remained **94 / 94**

Important: `reports/serialization-circular-references.json` was still present in the v1.5.7.4 output ZIP, but its event timestamp was older than the new `buffs.json` and validation timestamps. It was **stale residue from the v1.5.7.3 run**, not a new cycle report.

Future miner hygiene improvement: clear or regenerate stale diagnostic reports so old failures cannot be mistaken for current-run evidence.

## 14. Planner feature baseline

Planner supports:

- 3 weapon slots
- Gear Tier / Blueprint Stars
- Calibration Style-first workflow
- exact mined Calibration Style descriptions
- Calibration rarity/native record
- exact Weapon DMG RNG entry
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

The project is beyond basic planner architecture. Current work is **data fidelity + generic static stat-engine reconstruction + actual-vs-theoretical UX**.

## 15. Files future sessions should read first

1. `AI-CONTINUITY.md`
2. `PROJECT-RULES.md`
3. `.cpanel.yml`
4. `RELEASE-v1.5.1.md`
5. `preview/build-lab/index.html`
6. `preview/build-lab/calibration-style-display.js`
7. `preview/build-lab/calibration-style-display.css`
8. `preview/build-lab/calibration-style-picker.js`
9. `preview/build-lab/calibration-style-picker.css`
10. `preview/build-lab/calibration-details-ui.js`
11. `preview/build-lab/calibration-details.css`
12. `preview/build-lab/weapon-layout.js`
13. `preview/build-lab/weapon-model-ui.js`
14. `preview/build-lab/build-mode.js`
15. `shared/readability.css`
16. `shared/readability.js`
17. `preview/build-lab/player-images.js`
18. `preview/build-lab/armor-image-map.js`

For miner work, inspect the actual miner package/source under `_internal/extractor/`. GitHub sidecar probes are not the authoritative miner implementation.

The previous expanded handoff is archived at:

`archive/AI-CONTINUITY-2026-08-10-v1.5.0.md`

## 16. Immediate next steps

1. **Deploy PLAYER v1.5.1 through the existing cPanel Git workflow and visually verify the new Calibration Style descriptions.**
2. Keep picker cards clean; exact fixed Style description is allowed, RNG UI is not.
3. Add miner hygiene so stale `serialization-circular-references.json` cannot survive a successful later run and confuse diagnosis.
4. Continue generic static weapon-card stat-family work:
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
5. Reconcile older 108 planner attachments vs 119 identified true weapon-slot accessories.
6. Preserve copy-only cPanel deployment.
7. Later move to runtime combat layers with the same evidence-first approach.

## 17. Continuity rules

- Read this file first.
- Work on `main`; do not create branches unless the user asks.
- Preserve copy-only cPanel deployment.
- Do not upload the 3 GB master archive or `reference-tracer.sqlite` to normal production.
- Keep real hosted game images under `assets/reference-images/`.
- Prefer installed-game/mined evidence over community guesses.
- Do not execute transformed game bytecode.
- Do not trust stock `dis` on transformed Once Human PYC without corroboration.
- Prefer small, testable UI changes and screenshot/live iteration.
- Isolate the broken layer before changing unrelated code.
- Do not make the user re-explain project history when the repo can answer it.
- Update this file after major milestones.
- Accessibility/readability is a product requirement.
- Calibration RNG stays exact numeric fields only; no sliders.
- Calibration selection stays Style-first, then rarity/owned RNG.

---

### Continuity checkpoint

**Critical handoff as of 2026-08-10 23:55 MST:** Gear Tier × Blueprint Stars intrinsic Attack is solved; static Attack aggregation/final D0100 display are solved; Calibration Weapon DMG and one-secondary RNG models are solved; exact localized Calibration Style descriptions now resolve 94/94; canonical Style names remain absent; the v1.5.7.4 raw-level fallback source fix eliminated the 1,248 circular serialization back-references in a real run; PLAYER v1.5.1 has been committed to `main` and publishes the mined Style descriptions through prepared static UI files while preserving copy-only deployment. **Next action is cPanel deploy + visual verification, then continue the generic static stat-family engine.**
