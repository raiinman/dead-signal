# Dead Signal — AI Continuity / Handoff

> **Purpose:** Canonical current-state handoff for ChatGPT/Codex sessions working on Dead Signal. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Last updated: **2026-08-11 21:22 MST**

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

The Build Lab core references were changed to same-origin relative paths for its own `styles.css`, `data/community-data.js`, and `app.js`. Preserve that deployment-safe behavior; do not hard-wire production-domain URLs back into those core asset references.

**Concept folders are isolated review artifacts. Do not add concept folders to `.cpanel.yml` or deploy a concept to production unless the user explicitly asks to begin production translation.**

## 4. Latest `main` state / recent work

Last known `main` HEAD immediately before this continuity refresh:

`8274f08b6bc8f2608ae360228f47ee8ba8b4c6d1` — **Add Color Flow v6.6 theme colors and scrolling nav**

Recent operational planner work already completed on `main` includes:

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
- Planner core assets use same-origin relative paths instead of hard-coded production-domain URLs.
- `.cpanel.yml` remains copy-only.

Important production/planner commits in sequence:

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
- `3e9b75614241a4dd4f624469af3631e802fa9788` — earlier continuity refresh during SSL diagnosis

Recent isolated visual-concept commits:

- `4b4a06313a0197e79ea44b8d7643a66c308db3ee` — Color Breakup v2
- `3da2a7d0c1d4e1001ccf9d294ee1940e3a3412a5` — Instrumented UI v3
- `10a366c68243f1aec5436b133740bf0151ee46f3` — Visual Bible bottom-results/readability update
- `10cbda2b7d514622c6674a6f77037837060694bc` — Color Flow v4
- `faec1089284b34a1054ae68f1ead15b8fa240641` — Color Flow v5
- `56355c836d193becc8006eac9ab3dafffe1c46bd` — v5 snapshot separation + Base Attack wording
- `80284e9009d76a3fd1645286fcaecb5179501a46` — first functional Color Flow v6 weapon picker
- `14bfafbf237867db37a6e24e411369ed18c961de` — rebuilt v6 picker / clean player-facing calculation language
- `2406df03b83b687911285cb54a44b742d1bf85b8` — Cradle Override clarity / self-explaining labels
- `772db8029d86b43b702e4185158ffccc99141b08` — self-explaining UI rule added to Visual Bible
- `85eff0e0589570c2c3d3ad06fe2e94510b3e60dc` — Color Flow v6.4 Build Systems hierarchy
- `d230c51610dab0b175e3cf417ea6088377623b06` — Color Flow v6.5 unmistakable system-color zones
- `8274f08b6bc8f2608ae360228f47ee8ba8b4c6d1` — Color Flow v6.6 new colors + scrolling section-aware nav

The authoritative production `app.js` source proved the native planner already owns the Calibration fields and Save/Load/Clone/Import/Export/Share functions. The current bridge remains a compatibility layer; fully vendoring/extending the core source is still preferable when it can be done safely without regressing production behavior.

## 5. Current Build Lab / UX rules

Dead Signal is a full-width tactical Build Lab, not a cramped dashboard.

Current settled/favored direction:

- Preserve the familiar vertical planner workflow: **Plan → Weapons → Armor + Mods → Build Systems → Notes → Results**.
- Real weapon and armor images belong in picker and selected cards.
- Readability outranks maximum information density.
- Shared text-size system: `compact`, `default`, `large`, `xlarge`.
- Origin-wide preference key: `dead-signal-font-size`.
- The text-size selector belongs in the persistent left sidebar as **A− / A / A+ / A++**.
- Prefer small, visible, screenshot-driven iterations over giant rewrites.
- **Results / Loadout Report belongs full-width at the bottom of the planner flow**, not squeezed into a narrow permanent right rail.
- Important output must use the clearest typography on the page. Do not shrink result text just to fit more rows.
- Structural color should create visible landmarks as the player scrolls. Rarity-safe does **not** mean monochrome.
- Rarity colors remain item-only; especially **gold/amber is reserved for Legendary meaning**, not section identity.
- Sidebar navigation should remain visible and follow the player’s scroll position, automatically highlighting the section currently being viewed.
- The active sidebar state may inherit the section’s structural color so the sidebar participates in the visual rhythm rather than always being red.
- Cradle Overrides must be explicitly named and explained. Do not show anonymous `Slot 1`–`Slot 8` cards.
- Build Systems should have internal visual separation; Deviation / Food / Drink / Whim / Cradle Overrides should not collapse into one teal/charcoal slab.
- Controls should explain themselves on first visit. If the user has to ask what a slot, number, or card means, the label/design is unfinished.

### Current structural palette direction

Core/established:

- Signal Red: `#E6323E`
- Gunmetal / Weapons blue: `#58778C`
- Technical Cyan: `#39BFC6`
- Muted Indigo family for supporting systems
- Instrument / Ice Blue family for report/tooling
- Deep Teal for system/status meaning where appropriate

New colors tested in Color Flow v6.6 and explicitly liked by the user:

- **Signal Rose: `#C25578`** — warm structural accent for food/consumables/supporting systems.
- **Ash Violet: `#85708F`** — dusty violet-gray for Whim/utility/support panels.

These two colors are considered approved visual direction from the user’s reaction. They should be formally added to the Visual Bible on the next design-system update unless superseded.

Do not use Signal Rose or Ash Violet as item rarity semantics. The item rarity layer stays distinct.

### Build modes

1. **MY GEAR — ACTUAL BUILD**
   - Default/safer mode.
   - Dead Signal fills deterministic game data.
   - Player enters only server/account-specific RNG that public game files cannot know.

2. **GOD ROLL — THEORETICAL BUILD**
   - Deliberate and visually obvious.
   - Uses legal maximum RNG values.
   - Must clearly state values may not match owned gear.

Build mode is carried in the planner extension persistence layer; do not regress this.

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

Internal/proven progression formula:

```text
IntrinsicAttack = int(gun_preset_attack[GearTier] * preset_attack_radio[BlueprintStars])
```

Example internally: SKS — Pathfinder T5 6★ = `int(547 × 1.25) = 683`, not 684.

### Player-facing terminology rule

Do **not** expose `Intrinsic Attack` or `int(...)` as primary player-facing language.

Use:

**Base Attack**

Meaning:

> Attack after Gear Tier and Blueprint Stars, before external Weapon DMG bonuses and Calibration Weapon DMG.

If showing the arithmetic in UI, prefer the plain readable form:

```text
547 × 1.25 = 683
```

The user explicitly found **Intrinsic Attack** confusing. Keep that name only as an internal/code/math term when necessary.

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

The largest remaining production verification gate is **live browser round-trip testing**. Source-level persistence protections are in place, but real browser behavior still needs to be verified with the user present.

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

Current user-facing focus has shifted temporarily from architecture/data-mining work to **settling the Build Lab visual system through isolated concepts**.

Priority order now:

1. Continue visual review using the strongest concept direction rather than creating unrelated layouts.
2. Treat **Color Breakup v2 flow/rhythm + v6.6 palette/scroll nav + full-width bottom Results + self-explaining labels** as the current target combination.
3. Finish deciding structural color usage, including approved Signal Rose and Ash Violet placement.
4. Keep concepts isolated from production until the user explicitly says the direction is settled and asks to translate it.
5. When production translation begins, migrate design decisions deliberately into the real Build Lab rather than replacing the planner core wholesale.
6. Preserve the live-browser persistence torture test as an open production gate; do not forget it because design work is active.
7. Reconcile the older **108 planner attachments** against the verified **119 true weapon-slot accessories** from mined data once visual direction / production migration permits.
8. Expand real player-facing database surfaces from normalized mined data, with recipes/crafting as a high-value ecosystem gap.
9. Plan community build discovery/publishing only after the core build schema and persistence behavior are browser-proven.
10. Keep advanced configured DPS/runtime proc math last unless mined evidence fully proves each layer.

## 17. Files future sessions should read first

1. `AI-CONTINUITY.md`
2. `PROJECT-RULES.md`
3. `.cpanel.yml`
4. `concepts/instrumented-ui-v3/VISUAL-BIBLE.md`
5. latest active concept, currently `concepts/color-flow-v6-6/index.html`
6. `OPERABILITY-AUDIT.md`
7. latest `RELEASE-v*.md`
8. `COMPETITOR-AUDIT-2026-08-11.md`
9. `preview/build-lab/index.html`
10. planner persistence/transition/integrity bridge files under `preview/build-lab/`
11. `preview/build-lab/planner-report-tools.js`
12. `preview/build-lab/weapon-compare.js`
13. `preview/build-lab/weapon-compare.css`
14. Calibration Style/picker/details modules under `preview/build-lab/`
15. `shared/readability.css`
16. `shared/readability.js`
17. player image maps/assets

For miner work, inspect the actual miner package/source under `_internal/extractor/`. GitHub sidecar probes are not the authoritative miner implementation.

For the latest quantitative competitor check, prefer the most recent **v0.1.1+ Dead Signal Site Auditor JSON/ZIP supplied by the user** over the older checked-in narrative audit, while preserving the auditor’s detection/confidence caveats.

## 18. Continuity rules

- Read this file and `PROJECT-RULES.md` first.
- Fetch current `main` HEAD before changing repository files because automation/other sessions may have committed.
- Work on `main`; do not create branches unless the user asks.
- Preserve copy-only cPanel deployment.
- Keep concepts isolated from production unless the user explicitly asks to deploy/translate them.
- Do not modify `.cpanel.yml` merely to expose a concept mockup.
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
- Player-facing language must favor clarity over internal terminology.
- Gold/amber structural accents are forbidden because they collide with Legendary rarity semantics.

## 19. Current visual-design direction — 2026-08-11 evening

The visual work began because the live Build Lab felt too minimalist / monochrome / dreary despite having a good underlying workflow. The user wanted more color and stronger section breakup without sacrificing readability or making the planner feel like generic cyberpunk.

### Design identity

Current one-line target:

> **Dark tactical workstation with controlled colored instrumentation layered over the existing planner flow.**

Personality:

**Dark • Tactical • Precise • Dangerous • Technical • Readable • Alive**

“Alive” should come from information hierarchy, color landmarks, responsive state, and useful interaction — not constant animation or gratuitous glow.

### 80 / 20 rule

Keep roughly 80% of the familiar Build Lab workflow and improve the remaining 20% through:

- section identity
- color rhythm
- spacing
- depth
- status feedback
- readability
- self-explaining controls
- clearer final output

Do not redesign the planner simply because a new visual treatment is possible.

### Concept lineage and user reactions

#### Color Breakup v2

This remains an important reference because the user repeatedly felt that **something about v2 worked**.

What worked:

- more color landmarks
- stronger page rhythm
- smoother vertical flow
- changing visual temperature as the player moved down the page

Problem:

- it originally used amber/gold structurally in places, which clashes with rarity semantics.

Lesson:

> Preserve v2’s visual rhythm, not its rarity-conflicting color assignments.

#### Instrumented UI v3

What worked:

- clean tactical grammar
- clear technical/instrument feel

Problem:

- too gray / too restrained
- lost the life and color rhythm the user liked in v2

Lesson:

> Semantic discipline is good, but “rarity-safe” must not become nearly monochrome.

#### Color Flow v4

Major outcome:

- moved Results / Loadout Report to a **full-width bottom payoff** rather than a narrow right-side rail.

The user strongly preferred this because everything in Results can be read clearly.

#### Color Flow v5 / v5.1

Added/refined:

- persistent sidebar text-size selector
- stronger section color beats
- better top snapshot separation
- individual snapshot cards with real gutters/surfaces instead of one long dark strip
- `Intrinsic Attack` replaced by player-facing **Base Attack**

#### Color Flow v6 / v6.2

The concept became lightly functional.

Initial v6 picker attempt failed in the user’s browser and still exposed internal `int(...)` language. The user called this out.

v6.2 rebuilt the picker as a normal fixed overlay rather than relying on native `<dialog>` behavior and removed player-facing `int(...)`, `Intrinsic Attack`, and dev-style calculation labels.

The mockup uses a verified embedded weapon-progression sample (20 records in the concept) so opening the picker does not depend on production scripts. Selecting a weapon updates the Primary card and bottom Results; Gear Tier and Blueprint Stars are adjustable and update Base Attack.

This is still a **concept interaction**, not a production migration or claim that the entire 120-weapon picker has been ported into the concept.

#### Color Flow v6.3

The user asked what `Slot 1` through `Slot 8` meant. They were intended to be the eight **Cradle Override** positions.

This became a major design rule:

> **If the project owner has to ask what a control/card/slot is, a normal player will not know either.**

Cradle design direction:

- call the subsystem **Cradle Overrides**
- explain that the build can equip up to 8
- show `0 / 8 selected`
- use a readable **4 × 2** card arrangement
- cards should say `Cradle Override 1`, etc., not anonymous `Slot 1`
- empty state should say `Not selected` + what belongs there + a clear selection action

#### Color Flow v6.4 / v6.5

The user said the Loadout System / Build Systems section still blended together.

v6.4 attempted stronger tints but the screenshot proved the whole area still read as teal/charcoal.

v6.5 corrected the underlying problem by reducing the parent teal wash and making internal subsystem color zones much more obvious.

Current Build Systems principle:

- parent section should not drown all children in one color family
- Deviation, Food, Drink, Whim, and Cradle Overrides need visibly different instrument treatments
- colored header bands / card tints should be strong enough to read instantly, not only exist as 1px CSS border differences

#### Color Flow v6.6 — current leading concept

Path:

`concepts/color-flow-v6-6/index.html`

Key additions:

- **Signal Rose `#C25578`**
- **Ash Violet `#85708F`**
- user explicitly reacted positively to both colors
- sticky/fixed left sidebar continues to follow page scrolling
- current section is automatically highlighted as the player moves through the planner
- active sidebar color follows the structural color of the current section
- visible current-section indicator in the sidebar

Current sidebar color mapping in the concept:

- Plan → Signal Red
- Weapons → Gunmetal / Steel Blue
- Armor + Mods → Indigo family
- Build Systems → Instrument Blue
- Notes → Technical Cyan
- Results → Ice Blue

### Rarity vs structural color law

Rarity colors identify the **item**.

Structural colors identify **where the player is / what system they are using**.

Do not blur those meanings.

Especially:

- **Gold / amber = Legendary item meaning only**
- do not use gold/amber as Weapons/Armor/section/nav identity
- saturated rarity purple/blue should not be copied directly as structural colors either; use darker/more muted related families

Current structural spectrum is intentionally broader than before:

**Signal Red → Signal Rose → Ash Violet → Indigo → Instrument Blue → Steel Blue → Technical Cyan → Teal**

This broader spectrum is a strength as long as it remains controlled and does not become “rainbow soup.”

### Snapshot / corpus strip rule

The top player-facing data snapshot must read as a set of **individual instruments/cards**.

Do not present seven corpus counts as one continuous dark table strip.

Use:

- real gutters
- individual surfaces
- individual borders
- restrained per-card tone
- clear count + label hierarchy

### Results rule

**Results are the payoff.**

Full-width bottom Results is now a core design law, not just a concept experiment.

Flow:

**Build identity → weapon/gear choices → systems → notes → final Results**

Results should have enough width for:

- build identity
- integrity/state
- slot completion
- primary weapon result
- long weapon/style effects
- progression/Base Attack explanation
- loadout summary
- warnings/formulas
- copy/export/share/compare tools

Do not use tiny gray microtype for important output.

If a player has to lean toward the monitor to read the result, the design failed.

### Player-facing language rule

Internal names are not automatically good UI labels.

Known example:

- internal/dev term: `Intrinsic Attack`
- preferred player-facing term: **Base Attack**

Preferred explanation:

> Attack after Gear Tier and Blueprint Stars, before external Weapon DMG bonuses and Calibration Weapon DMG.

When showing the calculation, use a human-readable expression such as:

`547 × 1.25 = 683`

Do not foreground programming implementation such as `int(...)` in player-facing UI.

### Self-explaining UI law

Every important interactive region should answer:

1. What is this?
2. What belongs here?
3. What is selected/missing?
4. What can I do next?

Avoid vague labels such as:

- `Slot 1`
- `Configured`
- `System Online`
- generic `Value`
- generic `Select` without the target noun

Status words such as READY/VALID are fine only after the UI already makes clear **what** is ready or valid.

### Template comparison render

A side-by-side design-review flowchart render was generated in chat comparing:

1. Current Live Site
2. Color Breakup v2
3. Instrumented UI v3
4. Color Flow v4
5. Color Flow v5
6. Color Flow v6.6

The render’s settling direction matched the current discussion:

- keep the old/familiar vertical planner flow
- use stronger structural color landmarks without colliding with rarity colors
- keep Results full-width at the bottom for readability

The generated comparison image itself is not currently checked into the repository; treat the textual decisions above as canonical unless the image is later added explicitly.

### Current best synthesis

The visual target is best summarized as:

> **v2 color/flow + v3 semantic discipline + v6.6 expanded palette/scrolling navigation + maximum Results readability.**

Do not return to a mostly gray instrument panel. Do not return to amber/gold structural sections. Do not throw away the familiar planner flow.

The user is currently comparing/refining this direction before production translation.
