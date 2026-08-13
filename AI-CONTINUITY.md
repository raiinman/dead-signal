# Dead Signal — AI Continuity / Handoff

> Canonical current-state handoff. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Updated **2026-08-13 — Day Shift catch-up**.

## Project rules that must not drift

- Repository: `raiinman/dead-signal`; canonical branch: **`main` only**.
- Dead Signal is a prepared static database + Build Lab workstation. **No WordPress runtime.**
- cPanel deployment is **copy-only**; do not add Python, mining, builds, downloads, scans, unzip chains, or runtime transforms to `.cpanel.yml`.
- Installed-game/Miner evidence is canonical. External databases are UX/terminology references only.
- Do not invent mechanics, compatibility, recipes, proc behavior, DPS, rankings, or multiplier semantics.
- Preserve the accepted landing page, Official Once Human X feed, one global workstation shell, readability system, and `SOON` state for unfinished routes.
- Another user-controlled window has been handling domain/SSL. This workstream must not change DNS, SSL, redirects, or cPanel hosting/domain configuration unless the user explicitly combines those tasks.

## Current `main` checkpoint

Latest verified functional HEAD before this handoff update:

`cd27ed2d30a83847b05616d9214683e539429b24` — **Fix current Calibration schema bridge**

Day Shift commits:

- `edc9a7113a3fd22d2930fc09dc9eef22359c3e2c` — harden compact Weapons contract integrity validation.
- `f032be41ccbb17f2af90bf54612c47619eb824c3` — regression-test Weapons progression integrity guards.
- `eca041ced63fde80d9041fd672bf65bbbd9b3bff` — enforce variant-aware Armor contract identity.
- `63185f80241f3195c76593d29857ce982254473d` — regression-test Armor identity guards.
- `cd27ed2d30a83847b05616d9214683e539429b24` — align Build Lab Calibration bridge with the real current contract schema and fail-closed readiness rules.

GitHub Actions is green for `f032be41...`, `63185f80...`, and `cd27ed2d...`.

## Fresh Miner boundary

Released Miner: **v1.5.12.2**.

Package SHA-256: `26a4d3013cd1eb991366da58f2d7714e1c4fc1a8f5edb46eb1549ed9cefa728d`.

A fresh v1.5.12.2 `published/` snapshot still requires access to the user's PC and is not available to this repository-only session. **Do not relabel old data or fabricate compact payloads.**

When fresh output is accessible, inspect `published/reports/data-quality.json`, `change-report.json`, and the compact `published/web/` contracts before materializing anything.

## Weapons — gold-standard vertical

Last complete accessible snapshot proved:

- 120 weapons = 95 ranged + 25 melee;
- 600 Gear Tier rows;
- 545 Blueprint-Star rows;
- 2,725 legal Tier × Star combinations;
- 120/120 art;
- 120/120 five Tier rows;
- 95/95 firearm profiles resolved.

Current UI already has catalogue, detail, compare, legal Tier × Stars, Base Attack matrix/trace, proven static stats, unresolved-effect handling, acquisition/crafting evidence, Build Lab handoff, provenance, and compact Miner adapter path.

Day Shift strengthened `tools/site/materialize-weapons-web.py` so compact data now fails closed unless it has schema v1, unique IDs, player names, exactly Gear Tier I–V, exactly five Tier×Star matrix rows, legal rarity Star caps, numeric Base Attack rows, no progression validation issues, and matching total/ranged/melee counts.

Remaining evidence queue from the last snapshot:

- 76/120 resolved weapon effects; 44 unresolved/absent, including 29 Common.
- unresolved Legendary examples include G17 – Cash Only, DBSG – Format, HAMR – Hannya, MPS7 – Chaos Domain.
- 14 weapons have missing Tier recipes, all melee. Missing recipe evidence is **not** proof of non-craftable.
- normalized `short_description` remains untrusted because a Kukri/fish-text cross-wire was observed; public description stays withheld until the resolver is proven.

## Armor & Sets

Armor remains **SOON** until a real v1.5.12.2 snapshot clears the old duplicate-ID blocker.

Variant-aware identity is now enforced by both publisher and website materializer:

`ds-a-{suit_id}-{blueprint_id}`

The materializer verifies parent `suit_id`, Set IDs, Key Armor IDs, unique piece identity, names, and declared counts. CI is green. A set-centric Armor route/audit/materializer already exists. Do not mark READY before real `data-quality.json` proves the blocker cleared.

## Current Calibrations

The proven current projector emits:

- schema **`dead-signal-calibrations`**;
- schema_version **2**;
- publication_status **`ready-current-system`** only when exactly 94 current families are unambiguous;
- one current variant per family; legacy/non-current variants retained separately for audit.

Weapon DMG ranges: Rare 18–25%, Epic 26–33%, Legendary 34–50%. Current system also has exactly one random secondary. My Gear uses exact numeric inputs; no sliders.

Day Shift fixed Build Lab, which had incorrectly expected nonexistent schema `dead-signal-calibrations-current`. It now requires the real v2 schema, `ready-current-system`, 94 families, zero ambiguous families, and one variant per family.

**Known UI blocker:** `database/extended-catalogue.js` still contains the stale `dead-signal-calibrations-current` literal. The GitHub connector refused that large-file replacement in this session. Do **not** mutate the Miner schema to accommodate it; patch that renderer literal through a normal local file path when available. Until then the standalone Calibration route remains fail-closed rather than displaying wrong data.

## Mods / Attachments / Deviations / Cradles

Routes and null compact-contract placeholders already exist for all four.

- Mods: compact publisher groups by mined `mod_code` and preserves variants. Do not silently select the first variant; current Mod 2.0 player-selectable identity still needs fresh evidence before Build Lab migration.
- Attachments: publisher filters to player weapon slots only: Sight, Muzzle, Tactical, Magazine. Last verified player-slot count was 119 = 30/36/36/17. Raw 202 is not a picker target. Build Lab bridge is prepared but fresh IDs/compatibility must be verified before removing stale 108-record data.
- Deviations / Cradles: compact families preserve source variants. `canonical-category-variant-guard.js` blocks Build Lab promotion whenever a family has anything other than exactly one variant. Keep that guard until explicit variant semantics are proven.

## Build Lab migration state

Prepared canonical inputs exist for Weapons, current Calibrations, Attachments, Deviations, and Cradle Overrides. `canonical-category-bridge.js` only replaces a legacy pool when all canonical records map unambiguously. Variant guard runs before the bridge. Mods are not yet safely promoted.

No cPanel deploy, DNS/SSL change, landing-page change, X-feed change, or hosting architecture change was made by this Day Shift.

## Next exact sequence

1. Obtain fresh Miner v1.5.12.2 `published/` output from the user's PC.
2. Audit/materialize Weapons; verify catalogue/detail/compare/acquisition/crafting/Build Lab in browser.
3. Investigate unresolved non-Common weapon effects, short-description resolver evidence, and missing melee recipes from fresh raw/direct relationships.
4. Verify Armor quality report clears duplicate IDs; materialize and test set-centric database + Build Lab identity.
5. Fix the one stale standalone Calibration renderer schema literal, then materialize the 94-family v2 current contract and test exact current behavior.
6. Prove current Mod 2.0 family/variant identity before Build Lab migration.
7. Reconcile/materialize 119-style player weapon-slot Attachments and compatibility.
8. Resolve Deviation/Cradle variant semantics or build explicit variant selection; never discard variants silently.
9. Remove stale Build Lab compatibility pools only after end-to-end canonical verification.
10. Once core functionality is broadly complete, audit current Wikily and OnceHumanDB for UX/features only and implement evidence-backed differentiators.

## Read first next session

`PROJECT-RULES.md`, `tools/miner/release/latest.json`, `tools/miner/src/extractor/publish_web_data.py`, `publish_extended_web_data.py`, `publish_current_calibrations.py`, `normalize_weapons.py`, `normalize_armor.py`, `tools/site/materialize-weapons-web.py`, `materialize-armor-web.py`, `materialize-extended-contract.py`, `database/extended-catalogue.js`, `preview/build-lab/canonical-category-bridge.js`, `canonical-category-variant-guard.js`, `.github/workflows/test-site-tools.yml`, `.cpanel.yml`.
