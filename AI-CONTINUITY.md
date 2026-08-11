# Dead Signal — AI Continuity / Handoff

> **Purpose:** Canonical current-state handoff for ChatGPT/Codex sessions working on Dead Signal. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Last updated: **2026-08-11 15:35 MST**

## 1. Project identity

- Project: **Dead Signal Ultimate Planner**
- Game: **Once Human**
- Repository: `raiinman/dead-signal`
- Canonical branch: **`main` only** unless the user explicitly requests otherwise.
- Live planner: `https://deadsignaldb.com/build-planner/`
- Root site: `https://deadsignaldb.com/`
- Hosting: Namecheap shared hosting / cPanel.
- Production planner target: `$HOME/public_html/build-planner/`
- Current player release: **PLAYER v1.5.2**.
- Deployment architecture: prepared static files are copied by cPanel; do not turn cPanel into a build environment.
- User deploy workflow: cPanel → Git Version Control → **Update from Remote** → **Deploy HEAD Commit** → hard refresh (`Ctrl+F5`).
- Previous expanded handoff: `archive/AI-CONTINUITY-2026-08-10-v1.5.0.md`.

## 2. Domain / DNS / SSL — RESOLVED 2026-08-11

The public-access problem investigated on 2026-08-11 was real and is now resolved.

Proven DNS state:

- Registrar/hosting DNS mode: **Namecheap Web Hosting DNS**.
- Public Google DNS (`8.8.8.8`) and Cloudflare DNS (`1.1.1.1`) both resolved `deadsignaldb.com` to **`104.207.79.85`**.
- Public NS lookup returned:
  - `dns1.namecheaphosting.com`
  - `dns2.namecheaphosting.com`
- cPanel zone root record: `deadsignaldb.com` → A → `104.207.79.85`.
- `www.deadsignaldb.com` → CNAME → `deadsignaldb.com`.
- No conflicting public-site AAAA record was observed in the cPanel zone screenshots.
- Namecheap reports DNSSEC unavailable for **Namecheap Web Hosting DNS**; DNSSEC was not the outage cause.

Proven SSL fault and repair:

- Before repair, the installed Standard SSL covered `deadsignaldb.com` but **did not cover `www.deadsignaldb.com`**.
- Windows `curl.exe -I https://www.deadsignaldb.com/` failed with `SEC_E_WRONG_PRINCIPAL`.
- `curl.exe -kI https://www.deadsignaldb.com/` proved the web server itself was healthy and wanted to return `301 Location: https://deadsignaldb.com/`; TLS validation was blocking the redirect before the browser/client could receive it.
- The user reissued/reinstalled the **Namecheap Standard SSL** against the bare domain through cPanel → Namecheap SSL.
- After issuance, normal verified `curl.exe -I https://www.deadsignaldb.com/` succeeds and returns the expected `301` redirect to `https://deadsignaldb.com/`.
- cPanel SSL/TLS Status now shows both `deadsignaldb.com` and `www.deadsignaldb.com` **Domain Validated / covered**, expiring **2027-02-25**.
- `mail`, `cpanel`, `webmail`, etc. may still show uncovered by this site certificate; they are separate service subdomains and were not the public Dead Signal website blocker.

Verified HTTP behavior after repair:

- `curl.exe -I https://deadsignaldb.com/` → **200 OK**.
- `curl.exe -I https://deadsignaldb.com/build-planner/` → **200 OK**.
- `curl.exe -I https://www.deadsignaldb.com/` → verified TLS + **301** to the bare domain.
- The v0.1.1 website auditor subsequently reached Dead Signal with **verified TLS and zero TLS-fallback pages**.

Do **not** reopen DNS/SSL changes without new evidence. The public website path is presently proven healthy from the user’s external DNS checks, curl checks, cPanel certificate status, and the later auditor crawl.

## 3. Non-negotiable deployment rule

**Build/transform before deployment. cPanel only copies prepared static files.**

Namecheap shared hosting proved unreliable when `.cpanel.yml` performed Python work, recursive scans, archive reconstruction/extraction, data transforms, or outbound downloads.

Allowed deployment operations are lightweight `mkdir`, `cp`, `rm`, and `echo`. Do **not** reintroduce Python, `find`, unzip/build chains, runtime patching, external downloads, or corpus rebuilding into normal cPanel deployment.

Persistent game PNGs remain under:

`/public_html/build-planner/assets/reference-images/`

The first meaningful reliable copy-only deployment was commit:

`c3a62dbb414ad1368850f60032890b4b4f0d75d4`

The Build Lab core references were recently changed to same-origin relative paths for its own `styles.css`, `data/community-data.js`, and `app.js`. Preserve that deployment-safe behavior; do not hard-wire production-domain URLs back into those core asset references.

## 4. Latest `main` state / recent planner work

Last known `main` HEAD immediately before this continuity refresh:

`3e9b75614241a4dd4f624469af3631e802fa9788` — **Update AI continuity for SSL work and planner state**

Recent operational work already completed on `main` includes:

- Hardened Calibration persistence bridge for per-build/per-weapon-slot state.
- Persisted **MY GEAR / GOD ROLL** mode metadata through planner extension state.
- Build Data Integrity UI that fails closed when required My Gear Calibration inputs/controls are missing.
- Saved-build labels distinguish **MY GEAR** and **GOD ROLL**.
- Share-link extension-state injection moved away from unreliable Clipboard API interception to the planner encoding boundary.
- Calibration sidecar reset hooks and transition guard prevent cross-build leakage on New, Template, Load, Clone, Import, and Share initialization.
- Loadout Report gained **Copy Loadout Text** and **Copy Farming Checklist** workflows.
- Added a raw indexed **Weapon Compare** workflow with A/B comparison, arithmetic deltas, search, weapon imagery, and safe filtered Swap behavior.
- Weapon Compare intentionally does **not** claim configured DPS or apply Tier/Stars/Calibration/attachments yet.
- Calibration picker duplicate fixed-effect footer was resolved; screenshot verification showed exactly one contained `FIXED STYLE EFFECT` block per rarity card.
- Calibration rarity/favorite spacing was hardened across picker locations.
- Planner core assets now use same-origin relative paths instead of hard-coded production-domain URLs.
- `.cpanel.yml` remains copy-only.

Important recent commits in sequence:

- `32372b604dcc611245f8ffc742878a76f157603c` — persistence hardening stage
- `166aa0f4df3dbb3834b1223af3ebe8c42d43535b` — Build Data Integrity / build-mode labeling
- `966642c59c99c26af6540c91680ae84d46cbca2c` — Share Link extension-state fix
- `1a0a17c5f80b75b663a251debbbe26f227a560b6` — transition/reset isolation
- `c5e2d6975fdc80c3b18dc76ab685f2718a166f68` — fail-closed integrity controls
- `b86adf73170333b120169eaf964adc7c8e123fe6` — Loadout Report share/checklist differentiation
- `f5cd7f5644da044d0c9a6498950699e1c35828e7` — Weapon Compare baseline
- `3dec26d23a1fe6c796bcda12ae920d7bd21727ac` — Weapon Compare search/images
- `f9185b9f9b8a41956b654d6a6f591ea7030ca684` — filtered Swap fix/cache bust
- `33c7bc97193b03968195be0db510f8ebb2eaf87f` — same-origin planner core assets
- `3e9b75614241a4dd4f624469af3631e802fa9788` — continuity refresh during SSL diagnosis

The authoritative production `app.js` source was supplied by the user during v1.5.2 persistence work and proved the native planner already owns the Calibration fields and Save/Load/Clone/Import/Export/Share functions. The current bridge remains a compatibility layer; fully vendoring/extending the core source is still preferable when it can be done safely without regressing production behavior.

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

The fixed Style effect is vital selection information. On the selected weapon it must have strong visual hierarchy before RNG controls rather than being treated like a footer/disclaimer.

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

Raw Weapon Compare is intentionally allowed before configured stat math because it compares already-indexed player-facing records and clearly labels that Tier, Stars, Calibration, attachments, and derived DPS are not applied.

## 12. Miner circular-reference fix

Miner v1.5.7.4 fixed the prior `buffs.json` circular-reference serialization issue caused by raw-level fallback pointing back to the normalized parent record.

Real v1.5.7.4 output proved:

- validation: **PASS**
- new `data/buffs.json`: **0** `_dead_signal_circular_reference` markers
- previous v1.5.7.3 output: **1,248** markers
- combat resolution remained stable at **2,711 resolved / 1,086 partial / 44 unresolved**
- Calibration localization remained **94 / 94**

A `serialization-circular-references.json` file surviving in the v1.5.7.4 ZIP was stale residue from the previous run. Future miner hygiene should clear/regenerate stale diagnostics.

## 13. Website Auditor v0.1.1 / latest competitive baseline

A lightweight local **Dead Signal Site Auditor** was built for repeatable public audits. Current useful version: **v0.1.1**.

v0.1.1 characteristics:

- zero third-party Python dependencies;
- small robots-aware crawl;
- technical/accessibility checks;
- first-party JavaScript scanning so SPA-injected planner features can be detected;
- fail-closed competitor comparison if Dead Signal itself cannot be crawled confidently;
- TLS verification fallback exists only as a diagnostic path and is explicitly recorded;
- Markdown + JSON output suitable for later ChatGPT/Codex ingestion.

The latest user-run audit ZIP was `dead-signal-audit-20260811-152146.zip` and identifies itself as **Dead Signal Site Auditor v0.1.1**.

Latest measured results:

| Site | Technical | Planner Fidelity | Database & Ecosystem | Avg fetched response |
|---|---:|---:|---:|---:|
| **Dead Signal** | **83.3** | **100.0** | **54.2** | **177 ms** |
| OnceHumanDB | **85.0** | **46.7** | **83.3** | **419 ms** |
| Wikily | **70.7** | **46.7** | **83.3** | **598 ms** |

Dead Signal TLS was **verified by the auditor** with **0 TLS-fallback pages**.

Dead Signal received **100.0 planner-feature detection** because the audit found all 13 rubric capabilities:

- Build Planner
- Calibration modeling
- My Gear / actual build
- God Roll / theorycraft
- Save builds
- Share builds
- Import / Export
- Weapon Compare
- Build Data Integrity guard
- Loadout Report
- Farming Checklist
- Compatibility filtering
- Text-size/accessibility controls

This **does not mean the planner is operationally proven end-to-end**. The auditor detects publicly reachable feature evidence; the real browser persistence torture test in section 15 is still required.

### Auditor caveat: Dead Signal SPA confidence

The v0.1.1 audit marked Dead Signal crawl confidence **low** because it fetched only one HTML application page, even though it successfully scanned first-party JS and detected the full planner rubric. Because of that confidence rule, the auditor automatically withheld its competitor-delta list.

Treat this as an **auditor confidence-model limitation for a single-page application**, not evidence of a Dead Signal outage. A future auditor v0.1.2 should allow high confidence for an SPA when the entry page returns successfully, TLS verifies, first-party scripts are successfully scanned, sufficient feature evidence exists, and sampled links/assets are healthy.

### Latest technical cleanup signals

The v0.1.1 static audit found for Dead Signal:

- HTTPS: present
- title/description/viewport/lang/H1/main/nav basics: present
- cache/compression/X-Content-Type-Options: detected
- **HSTS: not detected**
- **Content-Security-Policy: not detected**
- 1 of 6 fetched inputs lacked aria/placeholder/title hints in static HTML

Do not blindly add a strict CSP to WordPress/Build Lab. Any HSTS/CSP change must be staged and verified so it does not break WordPress, the planner, hosted assets, authentication, or required third-party behavior. The single unlabeled-input result is a scanner lead, not yet a proven player-facing accessibility defect; inspect the actual control first.

## 14. Current competitive interpretation

The older checked-in audit is:

`COMPETITOR-AUDIT-2026-08-11.md`

The v0.1.1 local audit is newer and should be treated as the latest quantitative baseline when available.

Current interpretation:

- **Planner fidelity is Dead Signal’s strongest competitive position.** The auditor detected 100% of its planner rubric on Dead Signal versus 46.7% for each competitor.
- Dead Signal differentiators include current Calibration Blueprint structure, exact My Gear RNG, explicit God Roll separation, Build Data Integrity, local saves/clones/import/export/share, compatibility filtering, readability controls, Loadout Report, farming checklist, and raw indexed Weapon Compare.
- OnceHumanDB and Wikily remain much stronger in the broader **database/community ecosystem** (both 83.3% detected vs Dead Signal 54.2%).
- Material ecosystem gaps detected on Dead Signal: **recipes/crafting, community/featured builds, voting/social discovery, interactive maps, guides**.
- OnceHumanDB also has mature featured builds, broader database surfaces, and DPS presentation.
- Wikily has stronger public/community discovery, profiles/authorship/social workflows, maps, and guides.

Two v0.1.1 Dead Signal ecosystem detections should **not** be treated as proof of completed product surfaces:

- `Profiles / authorship` was triggered by planner text such as the **Author** field; Dead Signal does not yet have a mature public profile system.
- `DPS presentation` was triggered by an asset/text occurrence; Dead Signal does **not** yet have a trustworthy configured-DPS engine. Do not claim otherwise.

Do not chase competitor DPS numbers by inventing formulas. Dead Signal’s strategy is to be more trustworthy first, then broader.

## 15. Planner operability gate

The largest remaining verification gate is **live browser round-trip testing**. Source-level persistence protections are in place, but real browser behavior still needs to be verified with the user present.

Required torture test:

1. Save → Load a normal My Gear build.
2. Save intentionally blank My Gear Calibration rolls and confirm they stay blank rather than becoming midpoint defaults.
3. Save → Load a God Roll build and confirm mode restores correctly and the saved-build list displays the correct mode badge.
4. Export → Import preserves mode and exact My Gear Calibration rolls.
5. Share Link round trip preserves mode and exact My Gear Calibration rolls.
6. Two saved builds using the same weapon/calibration but different rolls remain independent.
7. New Build followed by re-selecting the same weapon/calibration does not resurrect the previous build’s rolls.
8. Template transition after another build does not inherit prior Calibration sidecar values.
9. Legacy saved/imported/shared build without `dsExtension.buildMode` opens as My Gear rather than inheriting an existing God Roll mode.
10. Build Data Integrity changes from `NEEDS PLAYER INPUT` to ready after completing required selected Calibration inputs.
11. If required Calibration controls fail to render, integrity must fail closed rather than show a false ready state.

Do not call persistence fully closed until these tests pass in a real browser.

## 16. Immediate priorities

1. Run the live planner persistence torture test with the user.
2. Fix any browser/runtime failures found by that test before adding more architecture.
3. Reconcile the older **108 planner attachments** against the verified **119 true weapon-slot accessories** from mined data once a safe normalized/player-facing source is available.
4. Inspect the auditor’s one unlabeled-input lead and fix it only if it maps to a real player-facing accessibility gap.
5. Consider HSTS/CSP only as a carefully staged technical-hardening project; do not risk breaking WordPress/Build Lab for a score increase.
6. Expand real player-facing database surfaces from normalized mined data, with recipes/crafting as a high-value ecosystem gap.
7. Plan community build discovery/publishing only after the core build schema and persistence behavior are browser-proven.
8. Upgrade Weapon Compare to progression/configuration-aware comparison only as each static stat family becomes fully proven.
9. Keep advanced derived DPS/runtime proc math last.
10. Improve the website auditor SPA confidence model before relying on automatic competitor-delta output.

## 17. Files future sessions should read first

1. `AI-CONTINUITY.md`
2. `PROJECT-RULES.md`
3. `OPERABILITY-AUDIT.md`
4. `.cpanel.yml`
5. latest `RELEASE-v*.md`
6. `COMPETITOR-AUDIT-2026-08-11.md`
7. `preview/build-lab/index.html`
8. planner persistence/transition/integrity bridge files under `preview/build-lab/`
9. `preview/build-lab/planner-report-tools.js`
10. `preview/build-lab/weapon-compare.js`
11. `preview/build-lab/weapon-compare.css`
12. Calibration Style/picker/details modules under `preview/build-lab/`
13. `shared/readability.css`
14. `shared/readability.js`
15. player image maps/assets

For miner work, inspect the actual miner package/source under `_internal/extractor/`. GitHub sidecar probes are not the authoritative miner implementation.

For the latest quantitative competitor check, prefer the most recent **v0.1.1+ Dead Signal Site Auditor JSON/ZIP supplied by the user** over the older checked-in narrative audit, while preserving the auditor’s detection/confidence caveats.

## 18. Continuity rules

- Read this file and `PROJECT-RULES.md` first.
- Work on `main`; do not create branches unless the user asks.
- Preserve copy-only cPanel deployment.
- Do not reopen DNS/SSL/redirect/domain settings without new evidence; the 2026-08-11 public-site SSL fault was fixed and verified.
- Preserve same-origin relative planner core asset paths.
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
- The Calibration fixed Style effect is vital information and must not be visually demoted to footer/fine-print treatment.
- A website-auditor detection is evidence of reachable text/assets, not proof that a workflow is operational end-to-end.
