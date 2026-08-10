# Dead Signal — AI Continuity / Handoff

> **Purpose:** Canonical handoff for future ChatGPT/Codex sessions working on Dead Signal. Read this file **before changing anything**. Update it after meaningful milestones, architecture/deployment discoveries, major data changes, miner discoveries, or significant UI decisions.
>
> Last updated: **2026-08-10 15:16 MST**

## 1. Project identity

- Project: **Dead Signal Ultimate Planner**
- Game: **Once Human**
- Repository: `raiinman/dead-signal`
- Branch: **`main` only** unless the user explicitly requests otherwise.
- Live planner: `https://deadsignaldb.com/build-planner/`
- Hosting: Namecheap shared hosting / cPanel.
- Production planner target: `$HOME/public_html/build-planner/`
- User deploy workflow: cPanel → Git Version Control → **Update from Remote** → **Deploy HEAD Commit** → hard refresh if needed.

## 2. Non-negotiable deployment rule

**Do not invent a new deployment workflow.**

Namecheap shared hosting proved unreliable when `.cpanel.yml` performed runtime/build work such as Python, recursive scans, archive reconstruction/extraction, data transforms, or outbound release downloads.

A minimal deployment and then the current static deployment proved that **copy-only cPanel deployment is reliable**.

### HARD RULE

> **Build/transform before deployment. cPanel only copies prepared static files.**

Current `.cpanel.yml` may use lightweight `mkdir`, `cp`, `rm`, and `echo`. Do **not** reintroduce Python, `find`, unzip/build chains, runtime patching, external downloads, or corpus rebuilding into normal cPanel deploys.

Persistent game PNGs under `/public_html/build-planner/assets/reference-images/` stay on hosting and are not recopied/scanned every deploy.

The first meaningful copy-only deployment that fully completed was commit:

`c3a62dbb414ad1368850f60032890b4b4f0d75d4`

## 3. Current Build Lab / UI direction

The planner is a full-width tactical Build Lab rather than a cramped dashboard.

Confirmed direction:

- Real hosted weapon and armor images display in picker/selected cards.
- Sidebar Signal Status/radar block was removed; it belongs to the main site, not the planner workspace.
- Cradle Overrides is a contained tactical sub-card with its own internal scroll.
- Loadout Report is below the workspace rather than consuming a permanent right rail.
- Left navigation includes a Loadout Report jump link.
- Typography/readability was increased; tiny 8–10px body/detail text is not the design target.
- Readability outranks maximum information density.

### Build-mode UX decision — IMPORTANT

The planner will have two highly prominent modes:

1. **MY GEAR — ACTUAL BUILD**
   - This is the safer/default mode.
   - Dead Signal fills all deterministic game data automatically.
   - The user only enters server/account-specific RNG values that cannot be known from the public game files.
   - Example: the exact RNG roll on a Calibration Blueprint the player actually looted.

2. **GOD ROLL — THEORETICAL BUILD**
   - Must be a deliberate, obvious selection.
   - Uses maximum legal RNG rolls for theorycrafting/build comparison.
   - Must clearly state that the values may not match gear the player owns.

The mode selector should be large and difficult to miss, not a tiny radio control. The active mode should remain visibly labeled throughout the planner and should be persisted into saved/shared builds so a shared build cannot be mistaken for actual owned gear.

For RNG entry in **My Gear** mode, use a **slider synchronized with an exact numeric input**. Typing e.g. `25.7%` moves the slider; dragging the slider updates the input. Do **not** add redundant MIN/MID/MAX buttons; they take up space. Slider endpoints already show the legal range.

## 4. Shared readability / accessibility system

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

Build Lab exposes these as `A− / A / A+ / A++` and stores the preference in origin-wide localStorage under:

`dead-signal-font-size`

The editable WordPress theme source is not currently present in this repo. Do not claim the main WordPress site is already wired to the readability system.

## 5. Current production/static files

The copy-only cPanel deployment currently copies prepared files including:

- `preview/build-lab/index.html`
- `preview/build-lab/build-lab.css`
- `preview/build-lab/media-enhancements.css`
- `preview/build-lab/density-enhancements.css`
- `preview/build-lab/planner-cleanup.css`
- `shared/readability.css`
- `shared/readability.js`
- `preview/build-lab/armor-image-map.js`
- `preview/build-lab/player-images.js`

No runtime transformation belongs in deployment.

## 6. Image architecture

### Master assets

The complete mined image/archive set is approximately **3 GB**, split into seven 7-Zip volumes (`assets.7z.001`–`.007`). These are archival/source assets and should **not** be pushed into normal Git history or normal web-hosting deployment.

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

Armor was not missed by the miner:

- 173 armor records
- 173/173 have image references
- 173/173 resolve to physical PNGs
- 172 unique physical armor PNGs because two records share one image

Static exact mapping:

`preview/build-lab/armor-image-map.js`

## 7. Current player-facing database baseline

Normalized/player-facing corpus before today’s new accessory reconciliation:

- Weapons: **120**
- Armor: **173**
- Armor Sets: **23**
- Mods: **817 entries / 105 families**
- Planner Attachments: **108** in the older normalized planner corpus
- Current Calibrations: **94**
- Unique player-facing Deviations: **97**
- Unique player-facing Cradles: **120**
- Usable Ammo: **144**
- Build-relevant Consumables: **150**

Raw attachment data contains **202 records**. The newer stat-aggregator investigation identifies **119 actual weapon-slot accessories** across:

- Sight: **30**
- Muzzle: **36**
- Tactical: **36**
- Magazine: **17**

The remaining raw attachment rows include ammo/arrows/shells/grenades/etc. Do not dump all 202 into the weapon-accessory picker. Reconcile the older 108 planner count with the newly identified 119 slot accessories before replacing production data.

## 8. Game Miner / factual hierarchy

For factual game data use this hierarchy:

1. **Game Miner** / installed game files
2. OnceHumanDB
3. Wikily
4. Official Once Human sources for patch/system corrections and authoritative change notes

Do not blindly expose runtime/internal rows from the miner. Filter to player-visible/current data.

The miner parsed Once Human `script.npk` with **0 parse errors**.

Important raw counts:

- weapons: 120
- armor: 173 normalized player-facing pieces
- mods: 1,618 raw
- attachments: 202 raw
- cradles: 170 raw / 120 unique player-facing
- calibrations: 188 raw = 94 current + 94 legacy
- deviations: 160 raw / 97 normalized unique player-facing
- ammo: 187 raw / 144 normalized planner entries
- consumables: 1,086 raw / 150 build-relevant
- relationships: 10,830
- reference image mappings: ~30,939 distinct / ~28,504 resolved

`reference-tracer.sqlite` is roughly 255 MB with ~1.35M occurrences. **Do not upload it to normal production.**

## 9. Actual miner package and source layout

The user supplied the real Dead Signal Miner package. Do not repeat the earlier mistake of patching only a repo-side probe when the user asks to patch the miner.

The miner ships Python source under:

`_internal/extractor/`

Important modules include:

- `weapon_progression.py`
- `normalize_weapons.py`
- `combat_resolver.py`
- `export_bindict.py`
- `normalize_extended.py`
- `npk_extract.py`

The packaged runtime uses Python 3.11. Validate modified extractor source against Python 3.11 before packaging. Remove stale `__pycache__` for modified modules before ZIP creation so shipped source is authoritative.

Game PYC files use Python 3.11 magic but have remapped/transformed opcodes. **Stock `dis` output is not authoritative even when it appears to succeed.** Use code-object metadata, raw wordcode, known remapped tails, constants/names/locals, and corroborating data tables. Do not execute game bytecode.

## 10. Blueprint Stars × Gear Tier — SOLVED

This was the major progression breakthrough on 2026-08-10.

### Separate axes

- `corr_forge_lv = [1,2,3,4,5]` maps to **Gear Tier I–V**.
- `strength_lv` maps to **Blueprint Star level**.
- Rarity caps match current game behavior:
  - Common: up to 3★
  - Rare: generally up to 4★
  - Epic: up to 5★
  - Legendary: up to 6★

Gear Tier and Blueprint Stars must never be conflated.

### Tier values

`gun_blueprint_attr_data.json` contains per-weapon progression rows. There is **no single universal Tier multiplier** that reproduces all weapons. Store mined Tier values per weapon directly.

Examples:

SOCR — Outsider base Attack by Tier:

- T1: 41
- T2: 62
- T3: 100
- T4: 156
- T5: 237

SKS — Pathfinder base Attack by Tier:

- T1: 94
- T2: 144
- T3: 230
- T4: 360
- T5: 547

This corrected the old mistaken assumption that Outsider `156` was Tier V; it is Tier IV 1★.

### Blueprint Star behavior is per weapon

The game provides a per-blueprint `preset_attack_radio` progression curve. It is a **direct multiplier**, not “+X%” syntax. Example legendary curve for Pathfinder:

`[1.00, 1.05, 1.10, 1.15, 1.20, 1.25]`

But do not assume every weapon uses Attack scaling:

- **82 weapons** progress via `preset_attack_radio`
- **13 weapons** instead progress via `fixed_skill_lv`
- **25 weapons** change neither field in the current snapshot
- **0** current weapons change both in the same progression data

Therefore Blueprint Stars are data-driven per weapon, not a generic global Attack formula.

### Proven intrinsic Attack formula

Static code capsules proved both `get_gun_omg_value()` and `get_gun_attack_base()` return the equivalent of:

```python
return preset_attack * attack_radio
```

The downstream base-weapon path then converts that value with `int(...)`.

Canonical intrinsic formula:

```text
IntrinsicAttack = int(
    gun_preset_attack[GearTier]
    * preset_attack_radio[BlueprintStars]
)
```

For positive weapon Attack this is truncation toward zero / floor-equivalent.

Pathfinder T5 6★:

```text
547 × 1.25 = 683.75
int(...) = 683
```

**Do not round this stage to 684.**

## 11. Calibration Blueprint model — current mined understanding

Current calibration system is post-Jan-21-2026 and separate from intrinsic Blueprint Star × Gear Tier progression.

### 11.1 Calibration drop anatomy

A current Calibration Blueprint drop has distinct layers:

1. **Fixed style effect**
   - referenced through a `buff_id`
   - can affect Attack, Fire Rate, Reload, Magazine, etc. depending on style

2. **Calibration Attack roll**
   - stored via the calibration’s `affix_val_range`
   - current ranges are universal by rarity across the 94 current calibration records:
     - Rare: **18%–25%**
     - Epic: **26%–33%**
     - Legendary: **34%–50%**
   - generation path contains `random.uniform(min,max)` and `round(..., 3)` on the raw fraction, corresponding to **0.1% UI increments**

3. **One weighted random secondary term**
   - generated by the weighted term selector (`generate_correct_print_term_id` / related helpers)
   - current candidate weights observed as **200 / 200 / 200 / 200**, so each of four candidates is currently equal-weight
   - secondary term has its own stat/range and is distinct from the main 18–25 / 26–33 / 34–50 Attack roll

### 11.2 +7/+10 calibration options are separate

Recovered global:

`calibration_option_gun = [7, 10]`

These are consumed by the weapon-calibration option system and are **not the same thing as the random term rolled when a Calibration Blueprint drops**. Keep these systems separate in both data model and UI.

### 11.3 Calibration Attack stat ID

The large Calibration Blueprint Attack roll feeds **`D0102`**, which belongs to the weapon’s additive Attack-ratio bucket. It is not a standalone multiplicative layer.

## 12. Static weapon-card Attack aggregator — SOLVED STRUCTURE

The client aggregation path combines multiple static affix sources, including:

- `base_affix_add`
- `accessory_affix_add`
- `rand_affix_add`
- `affix_option_add`
- `cal_affix`
- `correct_affix_add`

These feed the generic weapon stat aggregator rather than separate one-off formulas.

### Canonical Attack IDs

- `D0100` = base/flat Attack family
- `D0101` = Weapon DMG ratio contribution
- `D0102` = Current Weapon DMG / calibration-related Attack ratio contribution

`D0101` and `D0102` join the same **additive ratio bucket**.

Canonical static Attack structure:

```text
AttackRatio = 1 + Σ(D0101 contributions) + Σ(D0102 contributions)

StaticAttackFloat =
    IntrinsicAttack * AttackRatio
    + FlatAttackDelta
```

`FlatAttackDelta` is additional non-base `D0100` contribution.

This means modifiers that share D0101/D0102 add before multiplication. Do **not** compound them as separate multipliers.

Example:

- Calibration Attack: +42.7% (`D0102 = +0.427`)
- Suppressor: -15% Weapon DMG (`D0101 = -0.15`)

```text
AttackRatio = 1 + 0.427 - 0.150 = 1.277
```

Do not calculate `×1.427×0.85`.

## 13. Final static weapon-card Attack display — SOLVED

The final formatter path uses `AffixUtils.get_affix_name_and_val2()` and prototype metadata from `affix_prototype_data`.

Recovered prototype records:

- `D0100`: `type = 1`, format `"{:.0f}"`
- `D0101`: `type = 2`, format `"{:.1%}"`
- `D0102`: `type = 2`, format `"{:.1%}"`

Important distinction:

- **Blueprint Star/Tier stage:** actual `int(...)` truncation
- **Final D0100 weapon-card display:** zero-decimal fixed-point formatting via `"{:.0f}"`

The `int()` seen inside the generic formatter belongs to percentage precision logic, not to D0100 truncation.

Therefore do not add a second `int()` truncation after the fully aggregated static Attack float. Preserve the float through aggregation, then display D0100 using the game’s zero-decimal format rule.

Example with Pathfinder intrinsic `683` and only +42.7% Attack ratio:

```text
683 × 1.427 = 974.641
D0100 card display → 975
```

## 14. Accessories are part of the same stat engine

The in-game accessory slots currently identified are:

- Sight
- Muzzle
- Tactical
- Magazine

Accessories are not cosmetic. They contribute stat IDs into the same generic weapon-card aggregator.

Examples already seen in mined data:

- Tactical Holographic Sight: Accuracy, Mobility, Drawing Speed
- Large Brake: Accuracy, Bullet Velocity
- Tactical Laser Sight: Accuracy
- Suppressors: can carry `D0101 = -0.15`, i.e. **-15% Weapon DMG**

### Important normalization fixes already made

1. `gun_accessory_attr_data` can store stats as direct `(stat_id, value)` pairs rather than parallel arrays. The miner was updated to understand both layouts.
2. D0101/D0102 were initially being dropped from normalized `resolved_stats` even when raw attachment data contained them. The exporter/resolver was fixed.
3. The v1.5.2.1 hotfix run confirmed **40 raw D0101/D0102 attachment modifiers in, 40 resolved planner modifiers out**.

### Historical hotfix note

v1.5.2 initially crashed at ~82% because a patch accidentally wrote literal `\n` characters into a comment, causing the `STAT_CODE = re.compile(...)` definition to remain commented out. v1.5.2.1 fixed this. When modifying extractor source, scan for escaped-newline mistakes and import-test the module before packaging.

## 15. Static weapon-card stat families now identified

Current mined mapping for common accessory/static card stats:

- `Q0100` = Stability
- `Q0300` = Accuracy
- `Q0500` = Range
- `Q0900` = Fire Rate %
- `Q1100` = Magazine Capacity — flat
- `Q1101` = Magazine Capacity — %
- `Q1600` = Mobility
- `Q2000` = Drawing Speed %
- `Q2400` = Reload Speed
- `Q2600` = Bullet Velocity %

`Q1101` exposed another resolver hole because it is a non-zero-suffix variant. The next miner build resolves these generically through `affix_prototype_data` instead of hardcoding one ID.

The next mechanics targets are especially:

- Fire Rate: base/absolute RPM + percentage form (`Q0800` / `Q0900` family)
- Magazine Capacity: flat + percentage (`Q1100` / `Q1101`)
- Reload
- Accuracy
- Stability
- Range
- Mobility
- Drawing Speed
- Bullet Velocity

Goal: determine each stat family’s exact order of operations rather than merely naming the IDs.

## 16. Miner version history / latest handoff

Major packages created during the 2026-08-10 progression investigation:

- v1.4.3 — Focus Consumer Code Capsules
- v1.4.4 — Proven Multiply + Caller Chain
- v1.4.5 — D0100 Display Chain
- v1.4.6 — Display Int Conversion Proven
- v1.4.7 — Calibration RNG Consumer Trace
- v1.4.8 — Calibration Attack Ratio + Weighted Drop Trace
- v1.4.9 — Calibration Layers + Combined Attack Bucket
- v1.5.0 — Generic Weapon Stat Aggregator + Accessory Trace
- v1.5.1 — Accessory Stat Map + Proven Static Attack
- v1.5.2 — Attack Affix Export Fix + Final Formatter Trace (had crash)
- v1.5.2.1 — STAT_CODE hotfix
- v1.5.3 — D0100 Final Formatter Branch Probe
- v1.5.4 — D0100 Prototype Export-Root Fix
- v1.5.5 — D0100 Final Display Rule
- **v1.5.6 — Static Weapon Card Stat Families** — current next-run package

Latest completed data run was from **v1.5.5** and validated successfully.

Current next-run package:

`Dead-Signal-Miner-v1.5.6-Static-Weapon-Card-Stat-Families.zip`

SHA-256:

`bd8d9218f1ef6a61169d16ee78f1e2b2594d94f28d426f94f9a43bd3c9df4e2f`

v1.5.6 is designed to:

- resolve stat variants such as Q1101 through `affix_prototype_data`
- capture Fire Rate/RPM helpers
- capture weapon accuracy/range helpers
- capture reload helpers
- capture stability helpers
- investigate flat + percentage order of operations for non-Attack weapon-card stats

Do not restart the investigation from Stars/Tier or Calibration Attack; those discoveries are already captured above.

## 17. Planner architecture rule from today’s work

Do **not** build a collection of one-off formulas such as:

```text
weapon × stars × calibration × accessory × mod ...
```

The game is exposing a generic stat/affix pipeline. Dead Signal should mirror that architecture:

```text
Selected weapon / Tier / Stars
        + selected accessories
        + Calibration Blueprint
        + calibration-level options
        + other static affix sources
                ↓
        canonical stat contributions
                ↓
        stat-family aggregator
                ↓
        displayed static weapon card
```

Deterministic game data should be loaded automatically from the mined database. Only server-assigned/account-specific RNG should require player input in My Gear mode.

Runtime combat buffs/procs from armor sets, weapon mods, Cradles, Deviations, consumables, temporary status effects, etc. should remain a **separate layer** until their direct consumers/order of operations are traced. Do not mix runtime combat state into static weapon-card math merely because both can affect damage.

## 18. Planner feature baseline

Planner already supports:

- 3 weapon slots
- ammo
- calibration configuration
- attachments
- 6 armor slots
- armor mods
- quick-equip armor sets
- Deviations
- Cradles
- consumables
- build identity/metadata
- loadout report
- rarity handling
- local save/templates
- import/export
- share links
- compatibility filtering

The project has moved beyond “basic planner architecture.” Current major work is **data fidelity + exact stat engine reconstruction + UX for actual-vs-theoretical builds**.

## 19. Current game-system modeling rules

Read `PROJECT-RULES.md` too. Key rules:

- Gear Tier is I–V only.
- Blueprint Stars are separate from Gear Tier.
- Blueprint Star behavior is per weapon; do not assume Stars always raise Attack.
- Current weapon calibration model follows the post-Jan-21-2026 system.
- Calibration Blueprint drop RNG and +7/+10 weapon-calibration options are separate systems.
- Current Mod 2.0 behavior should be modeled instead of legacy random-subattribute assumptions.
- Static weapon-card math and runtime combat/proc math are separate layers.
- Readability/accessibility is canonical and should be reused by new pages.

## 20. Files future sessions should read first

1. `AI-CONTINUITY.md`
2. `PROJECT-RULES.md`
3. `.cpanel.yml`
4. `shared/readability.css`
5. `shared/readability.js`
6. `preview/build-lab/index.html`
7. `preview/build-lab/planner-cleanup.css`
8. `preview/build-lab/player-images.js`
9. `preview/build-lab/armor-image-map.js`
10. `preview/build-lab/media-enhancements.css`
11. `preview/build-lab/build-lab.css`
12. `preview/build-lab/density-enhancements.css`

For miner work, also inspect the actual uploaded miner package/source under `_internal/extractor/`; GitHub sidecar probes are not the authoritative miner implementation.

Old `deploy/patch-*.py` files are historical artifacts and are not part of normal live deployment.

## 21. Immediate next steps

1. **Run v1.5.6** and inspect its `data` / `reports` output.
2. Confirm Q1101 and other non-zero-suffix prototype-backed stat variants resolve correctly in normalized data.
3. Reconstruct exact static-card formulas/order of operations for:
   - Fire Rate / RPM
   - Magazine Capacity
   - Reload Speed
   - Accuracy
   - Stability
   - Range
   - Mobility
   - Drawing Speed
   - Bullet Velocity
4. Reconcile the older 108 planner attachment count against the newly identified 119 actual Sight/Muzzle/Tactical/Magazine accessories.
5. Once static weapon-card stat families are proven, implement the generic stat engine into the planner rather than writing one-off calculations.
6. Then move to runtime combat layers (mods, armor set effects, Cradles, Deviations, consumables, temporary buffs/procs) with the same evidence-first approach.
7. Continue preserving copy-only cPanel deployment and current readability/image architecture while math work proceeds.

## 22. Continuity rules for future AI sessions

- **Read this file first.**
- Do not create new branches unless the user asks.
- Work on `main` under the established workflow.
- Do not change deployment architecture without discussing it with the user.
- Preserve copy-only cPanel deployment.
- Do not upload the 3 GB master archive or `reference-tracer.sqlite` to normal production.
- Keep real images on Namecheap under `assets/reference-images/`.
- Prefer installed-game/mined evidence over community guesses for formulas.
- Do not trust stock Python `dis` on transformed Once Human PYC instructions without corroboration.
- Do not execute game bytecode; static inspection only.
- Prefer small, testable UI changes and screenshot/live iteration over giant rewrites.
- Isolate the broken layer before changing unrelated code.
- Do not make the user re-explain project history when this file/repo can answer it.
- Update this file after major milestones.

## 23. User workflow preferences relevant to this project

- Direct action and live iteration are preferred over long abstract planning.
- The user is a **kinetic learner**; interactive/visual mockups are often more useful than abstract prose.
- Screenshots/visual confirmation are valuable.
- Established workflows should not be changed without a strong reason.
- Keep deploy instructions compact and sequential.
- Accessibility/readability is explicitly a priority.
- For planner RNG controls, prefer tactile controls such as synchronized sliders + numeric inputs.

---

### Continuity checkpoint

A future AI/Codex session that reads this file should be able to resume Dead Signal without the original chat transcript. The critical handoff as of 2026-08-10 is: **Blueprint Star × Gear Tier intrinsic Attack is solved; static Attack aggregation and final D0100 display are solved; Calibration Blueprint RNG and its D0102 Attack contribution are separated from +7/+10 calibration options; accessories feed the same generic stat engine; next work is v1.5.6 and the remaining static weapon-card stat families.**
