# Dead Signal — AI Continuity / Handoff

> Canonical current-state handoff. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Updated **2026-08-13 — Day Shift + production website + Miner packaging audit**.

## Rules that must not drift

- Repo: `raiinman/dead-signal`; canonical branch: **`main` only**.
- Dead Signal is a prepared static database + Build Lab workstation. **No WordPress runtime.**
- Production deploys use the existing cPanel Git Version Control workflow; `.cpanel.yml` stays **copy-only**.
- Installed-game/Miner evidence is canonical. External databases are UX/terminology references only.
- Never invent mechanics, compatibility, recipes, proc behavior, DPS, rankings, or multiplier semantics.
- Preserve the accepted landing page and Official Once Human X feed unless there is a concrete bug.
- Unfinished database categories remain visibly `SOON` until their verified compact contracts are ready.

## Current checkpoint

Current production-source work on `main` includes:

- Weapons compact integrity/progression guards, acquisition/crafting evidence, catalogue/detail/Compare upgrades, and Build Lab handoff.
- Variant-aware Armor identity using `ds-a-{suit_id}-{blueprint_id}`, plus set-centric route, audit, materializer, and tests.
- Current Calibration v2 projector and dedicated standalone renderer.
- Prepared fail-closed routes for Mods, Attachments, Deviations, and Cradle Overrides.
- Build Lab canonical-category readiness, mapping, and variant guards.
- Workstation shell now exposes current Miner context and has syntax coverage.

Important recent commits:

- `eb1af76a791094ac91b6a3d1b81cb950ca3bb2fa` — fail closed on invalid Weapons public contract.
- `2b42a302cb5277a2ad0287a02b8af9b485242401` — guard Build Lab canonical contract readiness.
- `0d5a98627e767c8a41d9d2d49ffcb9a0a2c94b1c` — include the canonical category guard in site CI.
- `fd7a7fe692f01617cc357caa03464a1e5bb81981` — show current Miner version in workstation shell.
- `16e08dc087ee3f5585b0bd5fb8f95596e1cac16d` — syntax-check global workstation shell.
- `c6c434f68683e4e09c3b7ab5c182204b3c9f3125` — remove the unintended repository preview hub; production website is the review target.
- `14bedd54737495f4b2477b67bd390b90be5644aa` — correct the production website deployment handoff.

Site CI runs covering the Weapons adapter, Build Lab guard, and workstation shell completed successfully.

## Production website deployment state

`.cpanel.yml` is already prepared to copy today's production-ready source for the accepted landing/shared shell, Weapons vertical, prepared category routes, and Build Lab canonical contract overlays. It remains copy-only.

Armor, Mods, Calibrations, Deviations, and Cradle Overrides remain visibly `SOON` until real compact contracts prove them ready. Source routes may exist after deployment but must remain fail-closed and must not be promoted as complete.

This repository session cannot trigger the Namecheap/cPanel Git deployment itself because no hosting connector is available here.

## Build Lab source boundary

Two old compatibility files remain hosting-installed only and are not in Git:

- `preview/build-lab/data/community-data.js`
- `preview/build-lab/app.js`

Repository tests can prove compact contracts, guards, shell, and overlays, but cannot claim full legacy picker/application behavior is verified. Do not remove compatibility data until canonical end-to-end browser behavior is proven.

## Miner release boundary — critical packaging blocker

Currently released Miner: **v1.5.12.2**.

SHA-256: `26a4d3013cd1eb991366da58f2d7714e1c4fc1a8f5edb46eb1549ed9cefa728d`.

The compact extended publisher and current Calibration projector were added after v1.5.12.2 shipped. The next useful full-data release must therefore be **v1.5.12.3 or later**.

`tools/miner/src/miner_entry.py` is the intended new entrypoint and installs the extended compact publication plus exact current Calibration projection.

The Day Shift packaging audit proved that the verified Windows release path does **not yet use that entrypoint**:

- `tools/miner/build.ps1` still packages `dead_signal_miner.py` as the PyInstaller main script;
- its explicit hidden-import list omits `publish_extended_web_data` and `publish_current_calibrations`;
- `.github/workflows/test-miner.yml` still source-self-tests `dead_signal_miner.py`;
- `.github/workflows/release-miner-v1512.yml` also source-self-tests `dead_signal_miner.py` before packaging.

Therefore **do not bump VERSION and do not release v1.5.12.3 until the package/test/release path is changed to use and prove `miner_entry.py`**. The release pipeline is otherwise correctly ordered: source tests, packaged self-test, package, GitHub release, public hash/size verification, updater manifest last.

The GitHub connector rejected direct replacement of the PowerShell/workflow files during this pass, so the packaging defect is documented rather than worked around or hidden.

After a verified v1.5.12.3 release, run it against the real Once Human install and inspect fresh reports/contracts before materializing website data.

## Weapons

Last complete accessible snapshot proved:

- 120 weapons = 95 ranged + 25 melee;
- 600 Gear Tier rows;
- 545 Blueprint-Star rows;
- 2,725 legal Tier × Star combinations;
- 120/120 artwork;
- 95/95 firearm profiles resolved.

The player-facing Weapons vertical now has catalogue, details, Compare, legal Tier × Stars, Base Attack trace, proven static stats, acquisition/crafting evidence, provenance, unresolved-effect fallback messaging, and Build Lab handoff.

The public adapter now refuses malformed compact contracts before creating the compatibility model: wrong schema/version, blank/duplicate canonical IDs, non-proven progression status, incomplete Tier × Star matrices, or inherited progression validation issues fail closed.

`tools/site/audit-weapons-contract.py` independently validates Tier I–V identity and recomputes each published Base Attack cell from the proven Tier-base × Blueprint-Star ratio rule.

Remaining evidence queue:

- 76/120 weapon effects resolved; 44 unresolved/absent, including 29 Common;
- unresolved Legendary examples include G17 — Cash Only, DBSG — Format, HAMR — Hannya, MPS7 — Chaos Domain;
- 14 missing Tier recipes, all melee; missing recipe evidence is **not** proof of non-craftable;
- `short_description` remains untrusted because of the observed Kukri/fish-text cross-wire.

A future Weapons hardening pass should make `tools/site/materialize-weapons-web.py` enforce the same exact legal star-set and Base Attack recomputation already enforced by the audit.

## Armor & Sets

Armor stays `SOON` until a fresh v1.5.12.3+ snapshot proves collision-free real output. Set-centric route, audit, materializer, and identity tests are ready.

Never classify missing forge data as non-craftable without direct game evidence.

## Current Calibrations

Canonical current contract:

- schema `dead-signal-calibrations`;
- schema_version `2`;
- publication_status `ready-current-system` only at exactly 94 unambiguous current families;
- exactly one current variant per family; legacy rows remain audit-only.

Proven Weapon DMG ranges: Rare 18–25%, Epic 26–33%, Legendary 34–50%. My Gear uses exact numeric inputs; no sliders.

Do not reintroduce obsolete schema `dead-signal-calibrations-current` or route the current system back through the generic legacy renderer.

## Mods / Attachments / Deviations / Cradles

- Mods: preserve mined variants; current Mod 2.0 player-selectable identity still needs fresh proof.
- Attachments: player weapon slots only — Sight, Muzzle, Tactical, Magazine. Last verified player-facing count was 119 = 30 / 36 / 36 / 17; raw 202 is not the picker target. Build Lab now blocks an unready compact contract, duplicate canonical IDs, or a contract missing one of those four slot types.
- Deviations / Cradles: preserve source variants. Build Lab now validates expected compact schema/version/publication status and blocks planner promotion when a family remains ambiguous.

## Next exact sequence

1. Fix the Windows Miner package path so the built app uses `miner_entry.py` and contains both new publisher modules.
2. Make Miner source/release self-tests exercise that same entrypoint.
3. Run Miner CI and prove the packaged Windows self-test succeeds.
4. Only then bump VERSION to v1.5.12.3 and let the existing verified updater pipeline publish it.
5. Run v1.5.12.3 against the real Once Human install.
6. Audit/materialize Weapons and investigate unresolved non-Common effects, unsafe descriptions, and missing melee recipes from fresh evidence.
7. Verify/materialize Armor and integrate it only after real-output invariants pass.
8. Materialize/test the 94-family current Calibration contract end-to-end.
9. Prove current Mod 2.0 variant identity and migrate it.
10. Reconcile/materialize the 119 player-selectable Attachments and compatibility.
11. Resolve Deviation/Cradle variant semantics or provide explicit variant choice before planner promotion.
12. Remove old Build Lab compatibility pools only after canonical end-to-end verification.
13. After core functionality is broadly complete, audit current competitor UX/features and implement evidence-backed differentiators.

## Read first next session

`PROJECT-RULES.md`, `tools/miner/release/latest.json`, `tools/miner/src/miner_entry.py`, `tools/miner/build.ps1`, `.github/workflows/test-miner.yml`, `.github/workflows/release-miner-v1512.yml`, `publish_extended_web_data.py`, `publish_current_calibrations.py`, `normalize_weapons.py`, `normalize_armor.py`, `tools/site/materialize-weapons-web.py`, `audit-weapons-contract.py`, `materialize-armor-web.py`, `materialize-extended-contract.py`, `database/calibrations/index.html`, `preview/build-lab/canonical-category-bridge.js`, `canonical-category-variant-guard.js`, `.github/workflows/test-site-tools.yml`, `.cpanel.yml`.
