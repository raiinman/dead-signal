# Dead Signal — AI Continuity / Handoff

> **Purpose:** Canonical current-state handoff for ChatGPT/Codex sessions working on Dead Signal. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Last updated: **2026-08-11 11:27 MST**

## 1. Project identity

- Project: **Dead Signal Ultimate Planner**
- Game: **Once Human**
- Repository: `raiinman/dead-signal`
- Canonical branch: **`main` only** unless the user explicitly requests otherwise.
- Live planner: `https://deadsignaldb.com/build-planner/`
- Hosting: Namecheap shared hosting / cPanel.
- Production planner target: `$HOME/public_html/build-planner/`
- Deployment architecture: prepared static files are copied by cPanel; do not turn cPanel into a build environment.
- Previous expanded handoff: `archive/AI-CONTINUITY-2026-08-10-v1.5.0.md`.

## 2. ACTIVE USER WORK — DOMAIN / SSL

**The user is currently working in another window on fixing the Dead Signal domain SSL.**

Until that work is explicitly reported complete:

- Do **not** make competing DNS, SSL, certificate, redirect, document-root, domain, or hosting-control-panel changes.
- Do **not** deploy through cPanel unless the user explicitly asks.
- Avoid architecture changes that could complicate SSL/domain diagnosis.
- Planner/source work may continue on `main` when safe, but keep hosting concerns isolated from application concerns.
- The Build Lab was recently changed to use same-origin relative paths for its own core assets (`styles.css`, `data/community-data.js`, `app.js`) instead of hard-wiring `https://deadsignaldb.com/...`; preserve that deployment-safe behavior.

## 3. Non-negotiable deployment rule

**Build/transform before deployment. cPanel only copies prepared static files.**

Namecheap shared hosting proved unreliable when `.cpanel.yml` performed Python work, recursive scans, archive reconstruction/extraction, data transforms, or outbound downloads.

Allowed deployment operations are lightweight `mkdir`, `cp`, `rm`, and `echo`. Do **not** reintroduce Python, `find`, unzip/build chains, runtime patching, external downloads, or corpus rebuilding into normal cPanel deployment.

Persistent game PNGs remain under:

`/public_html/build-planner/assets/reference-images/`

The first meaningful reliable copy-only deployment was commit:

`c3a62dbb414ad1368850f60032890b4b4f0d75d4`

## 4. Latest `main` state / recent planner work

Last known `main` HEAD before this continuity update:

`33c7bc97193b03968195be0db510f8ebb2eaf87f` — **Use same-origin planner core asset paths**

Recent operational work completed on `main` includes:

- Hardened Calibration persistence bridge for per-build/per-weapon-slot state.
- Persisted **MY GEAR / GOD ROLL** mode metadata through planner extension state.
- Build Data Integrity UI that fails closed when required My Gear Calibration inputs/controls are missing.
- Saved-build labels distinguish **MY GEAR** and **GOD ROLL**.
- Share-link extension-state injection moved away from unreliable Clipboard API interception to the planner encoding boundary.
- Calibration sidecar reset hooks and transition guard prevent cross-build leakage on New, Template, Load, Clone, Import, and Share initialization.
- Loadout Report gained **Copy Loadout Text** and **Copy Farming Checklist** workflows.
- Added a raw indexed **Weapon Compare** workflow with A/B comparison, arithmetic deltas, search, weapon imagery, and safe filtered Swap behavior.
- Weapon Compare intentionally does **not** claim configured DPS or apply Tier/Stars/Calibration/attachments yet.
- Planner core assets now use same-origin relative paths instead of hard-coded production-domain URLs.
- `.cpanel.yml` remains copy-only.

Important recent commits in sequence:

- `32372b604dcc611245f8ffc742878a76f157603c` — persistence hardening stage
- `166aa0f4df3dbb3834b1223af3ebe8c42d43535b` — Build Data Integrity / build-mode labeling
- `966642c59c99c26af6540c91680ae84d46cbca2c` — Share Link extension-state fix
- `1a0a17c5f80b75b663a251debbbe26f227a560b6` — transition/reset isolation
- `c5e2d6975fdc80c3b18dc76ab685f2718a166f68` — fail-closed integrity controls
- `b86adf73170333b120169eaf964adc7c8e123fe6` — Loadout Report share/checklist differentiation
- `f5cd7f5644da044d0c9a6498950699e1c35828e7` — Weapon Compare
- `3dec26d23a1fe6c796bcda12ae920d7bd21727ac` — Weapon Compare search/images
- `f9185b9f9b8a41956b654d6a6f591ea7030ca684` — filtered Swap fix/cache bust
- `33c7bc97193b03968195be0db510f8ebb2eaf87f` — same-origin planner core assets

## 5. Current Build Lab / UX rules

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

Build mode is now carried in the planner extension persistence layer; do not regress this.

### Calibration RNG input

**No sliders.**

My Gear uses exact numeric `%` inputs, legal ranges, validation/clamping, and 0.1% increments where the game does. God Roll displays locked legal maxima.

## 6. Calibration Blueprint model / approved UX

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

Style-first selection remains required: choose Calibration Style/Mod Type first, then a native Rare/Epic/Legendary record compatible with that Style.

Short Style labels are derived from blueprint names because no canonical localized Style-name field has been recovered. Do not invent one. Exact localized fixed Style descriptions have been mined for all 94 current records.

Picker cards may show name, rarity, and exact fixed Style description. RNG controls belong after selection on the weapon card; do not dump all four possible secondaries onto the picker card.

## 7. Current database baseline

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

Latest miner normalization snapshot includes:

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

Weapon normalization: **120 weapons** = 95 ranged + 25 melee, 600 tier-stat rows, 545 blueprint-attribute rows, Blueprint-Star axis validated, preset-attack-ratio coverage complete, 530 current recipes, 0 translation misses.

Armor normalization: **173 pieces**, 23 sets, 133 set pieces, 40 key armor, 850 tier-stat rows, 0 translation misses.

Raw attachment data has 202 records, but the stat-aggregator investigation identifies **119 actual weapon-slot accessories**:

- Sight: 30
- Muzzle: 36
- Tactical: 36
- Magazine: 17

Do not dump all 202 raw rows into the player picker. The planner still has the older 108-record accessory corpus; reconciliation to the verified 119-slot set remains a major data-completeness task. Do not fabricate the missing records from community guesses.

## 8. Game Miner / factual hierarchy

For factual game data use:

1. **Game Miner / installed game files**
2. OnceHumanDB
3. Wikily
4. Official Once Human sources for patch/system corrections and authoritative change notes

Do not blindly expose internal/runtime rows. Filter to player-visible/current data.

The miner parsed Once Human `script.npk` with **0 parse errors**. `reference-tracer.sqlite` is roughly 255 MB with ~1.35M occurrences; do **not** upload it to normal production.

The real miner source modules ship under `_internal/extractor/`, including `weapon_progression.py`, `normalize_weapons.py`, `combat_resolver.py`, `export_bindict.py`, `normalize_extended.py`, and `npk_extract.py`.

Packaged runtime uses Python 3.11. Game PYC files use Python 3.11 magic but transformed/remapped opcodes. **Stock `dis` is not authoritative.** Do not execute game bytecode.

## 9. Proven weapon progression / static Attack

Gear Tier and Blueprint Stars are separate axes:

- `corr_forge_lv = [1,2,3,4,5]` = Gear Tier I–V
- `strength_lv` = Blueprint Star level

Rarity star caps: Common up to 3★, Rare generally 4★, Epic 5★, Legendary 6★.

No universal Tier multiplier reproduces every weapon. Store mined Tier values per weapon.

Blueprint Star behavior currently resolves as 82 weapons through `preset_attack_radio`, 13 through `fixed_skill_lv`, 25 through neither, 0 through both.

Proven intrinsic Attack formula:

```text
IntrinsicAttack = int(gun_preset_attack[GearTier] * preset_attack_radio[BlueprintStars])
```

Example: SKS — Pathfinder T5 6★ = `int(547 × 1.25) = 683`, not 684.

Canonical Attack IDs:

- `D0100` = base/flat Attack family
- `D0101` = Weapon DMG ratio
- `D0102` = current Calibration Weapon DMG / Attack ratio

`D0101` and `D0102` share one additive ratio bucket:

```text
AttackRatio = 1 + Σ(D0101) + Σ(D0102)
StaticAttackFloat = IntrinsicAttack * AttackRatio + FlatAttackDelta
```

Final D0100 card display uses zero-decimal fixed-point formatting. Do not compound D0101/D0102 as independent multipliers.

## 10. Calibration Blueprint evidence

Current post-Jan-21-2026 Calibration Blueprints have three separate layers: deterministic fixed Style, guaranteed Weapon DMG RNG, and exactly one random secondary.

All **94** current records have localized fixed Style descriptions. Canonical localized Style names remain unrecovered.

Weapon DMG RNG ranges:

- Rare: **18%–25%**
- Epic: **26%–33%**
- Legendary: **34%–50%**

Secondary pools:

- Rare: Weakspot 12–18%, Crit Rate 8–12%, Elemental 12–18%, Crit DMG 20–30%
- Epic: Weakspot 15–21%, Crit Rate 10–14%, Elemental 12–18%, Crit DMG 25–35%
- Legendary: Weakspot 18–24%, Crit Rate 12–16%, Elemental 15–20%, Crit DMG 30–40%

Observed current weights are 200/200/200/200. Do not present all four as active stats.

`calibration_option_gun = [7, 10]` is a separate weapon-calibration option system, not the random secondary.

## 11. Advanced stat-engine work — HOLD unless proven

Known static IDs include `Q0100` Stability, `Q0300` Accuracy, `Q0500` Range, `Q0900` Fire Rate %, `Q1100` Magazine flat, `Q1101` Magazine %, `Q1600` Mobility, `Q2000` Drawing Speed %, `Q2400` Reload Speed, and `Q2600` Bullet Velocity %.

`Q1101` exposed a non-zero-suffix resolver hole; variants should resolve generically through `affix_prototype_data`, not one-off hardcodes.

Do **not** resume broad weapon-math/stat-engine implementation merely because these IDs are known. Proceed only when mined files provide enough evidence to implement a stat family confidently without speculation. Runtime buffs/procs remain a later layer until direct consumers/order are traced.

## 12. Miner circular-reference fix

Miner v1.5.7.4 fixed the prior `buffs.json` circular-reference serialization issue caused by raw-level fallback pointing back to the normalized parent record.

Real v1.5.7.4 output proved:

- validation: **PASS**
- new `data/buffs.json`: **0** `_dead_signal_circular_reference` markers
- previous v1.5.7.3 output: **1,248** markers
- combat resolution remained stable at **2,711 resolved / 1,086 partial / 44 unresolved**
- Calibration localization remained **94 / 94**

A `serialization-circular-references.json` file surviving in the v1.5.7.4 ZIP was stale residue from the previous run. Future miner hygiene should clear/regenerate stale diagnostics.

## 13. Competitor audit — completed once, re-audit later

A live audit against current Wikily Once Human and OnceHumanDB was performed during the PLAYER v1.5.2 stabilization work. See:

`COMPETITOR-AUDIT-2026-08-11.md`

Key findings at that checkpoint:

- OnceHumanDB was stronger in dedicated comparison/DPS presentation, featured builds, and broader database surfaces such as recipes/items/memetics.
- Wikily was stronger in public/community build discovery, authorship/social workflows, and mature build browsing/filtering.
- Dead Signal was already differentiated by explicit My Gear vs God Roll, current Calibration modeling, exact player RNG entry, compatibility filtering, local save/clone/import/export/share, accessibility scaling, Build Data Integrity, and Loadout Report.
- Dead Signal subsequently added a raw indexed Weapon Compare plus copyable loadout/farming workflows.
- Remaining comparison gap is progression/configuration-aware comparison; implement only as underlying stat families become proven.
- Public/community build discovery remains a later product gap.

Re-audit after meaningful operational/data improvements rather than copying competitor features blindly.

## 14. Planner operability gate

The largest remaining verification gate is **live browser round-trip testing**. Source-level persistence protections are in place, but real browser behavior still needs to be verified with the user present.

Required torture test:

1. Save → Load a normal My Gear build.
2. Save intentionally blank My Gear Calibration rolls and confirm they stay blank rather than becoming midpoint defaults.
3. Save → Load a God Roll build and confirm mode restores correctly.
4. Export → Import.
5. Share Link round trip.
6. Two saved builds using the same weapon but different Calibration rolls; confirm no cross-build leakage.
7. New Build and Template transitions; confirm old sidecar values do not survive.
8. Legacy build without extension mode metadata; confirm safe fallback to My Gear.

Do not call persistence fully closed until these tests pass in a real browser.

## 15. Immediate priorities after SSL work is stable

1. Run the live planner persistence torture test with the user.
2. Fix any browser/runtime failures found by that test before adding more architecture.
3. Reconcile the older **108 planner attachments** against the verified **119 true weapon-slot accessories** from mined data once a safe normalized/player-facing source is available.
4. Continue picker/card/UI/data-presentation cleanup and other evidence-backed player usability work.
5. Keep advanced stat-engine work on hold except for stat families proven end-to-end from mined evidence.
6. Re-audit Wikily/OnceHumanDB after meaningful improvements.

## 16. Files future sessions should read first

1. `AI-CONTINUITY.md`
2. `PROJECT-RULES.md`
3. `.cpanel.yml`
4. latest `RELEASE-v*.md`
5. `COMPETITOR-AUDIT-2026-08-11.md`
6. `preview/build-lab/index.html`
7. planner persistence/transition/integrity bridge files under `preview/build-lab/`
8. `preview/build-lab/weapon-compare.js`
9. `preview/build-lab/weapon-compare.css`
10. Calibration Style/picker/details modules under `preview/build-lab/`
11. `shared/readability.css`
12. `shared/readability.js`
13. player image maps/assets

For miner work, inspect the actual miner package/source under `_internal/extractor/`. GitHub sidecar probes are not the authoritative miner implementation.

## 17. Continuity rules

- Read this file and `PROJECT-RULES.md` first.
- Work on `main`; do not create branches unless the user asks.
- Preserve copy-only cPanel deployment.
- While the user is fixing SSL/domain configuration in another window, do not interfere with DNS/SSL/redirect/domain/cPanel hosting settings.
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

**Critical handoff as of 2026-08-11 11:27 MST:** the planner has moved well beyond the old PLAYER v1.5.1 checkpoint. Persistence/build-mode extension handling, transition isolation, fail-closed Build Data Integrity, loadout sharing/checklist tools, raw Weapon Compare, compare search/images/safe Swap, and same-origin core asset paths are now on `main`. Copy-only deployment remains mandatory. The live browser persistence torture test is still the primary operability gate, and the 108-vs-119 attachment reconciliation is the primary known data-completeness gap. **The user is actively fixing the domain SSL in another window; do not make competing hosting/domain/SSL changes until they report that work complete.**