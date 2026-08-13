# Dead Signal — AI Continuity / Handoff

> Canonical current-state handoff. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Updated **2026-08-13 — Day Shift + production website handoff**.

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
- `fd7a7fe692f01617cc357caa03464a1e5bb81981` — show current Miner version in workstation shell.
- `16e08dc087ee3f5585b0bd5fb8f95596e1cac16d` — syntax-check global workstation shell.
- `c6c434f68683e4e09c3b7ab5c182204b3c9f3125` — remove the unintended repository preview hub; production website is the review target.

## Production website deployment state

`.cpanel.yml` is already prepared to copy today's production-ready source for:

- Landing/shared workstation shell/readability;
- Weapons catalogue/detail/SKS route and compact adapter files;
- Armor route/materializer outputs;
- Calibrations, Mods, Attachments, Deviations, and Cradles route shells/data placeholders;
- Build Lab canonical-category contracts/bridge/variant guards.

The landing page intentionally keeps Armor, Mods, Calibrations, Deviations, and Cradle Overrides as `SOON` until real compact contracts prove them ready. Their source routes may exist on hosting after deployment, but they must remain fail-closed and must not be promoted as complete.

**This repository session cannot trigger the Namecheap/cPanel Git deployment itself because no cPanel/Namecheap hosting connector is available.** The production source is on `main`; the remaining publication action is the existing cPanel Git Version Control deploy of current `main`.

## Miner release boundary

Currently released Miner: **v1.5.12.2**.

SHA-256: `26a4d3013cd1eb991366da58f2d7714e1c4fc1a8f5edb46eb1549ed9cefa728d`.

The extended compact publisher and current Calibration projector were added after v1.5.12.2 shipped. **The next useful full-data release must therefore be v1.5.12.3 or later.** A new v1.5.12.2 mine is not sufficient for the full Day Shift migration.

`tools/miner/src/miner_entry.py` is the intended entrypoint for the next package and includes the extended compact publication step plus current Calibration projection. Do not bump VERSION until the Windows package path is proven to use it and the publisher modules are included/tested.

After v1.5.12.3 is released, run it against the real Once Human install and inspect fresh reports/contracts before materializing website data.

## Weapons

Last complete accessible snapshot proved:

- 120 weapons = 95 ranged + 25 melee;
- 600 Gear Tier rows;
- 545 Blueprint-Star rows;
- 2,725 legal Tier × Star combinations;
- 120/120 artwork;
- 95/95 firearm profiles resolved.

The player-facing Weapons vertical now has catalogue, details, Compare, legal Tier × Stars, Base Attack trace, proven static stats, acquisition/crafting evidence, provenance, and Build Lab handoff.

Remaining evidence queue:

- 76/120 weapon effects resolved; 44 unresolved/absent, including 29 Common;
- unresolved Legendary examples include G17 — Cash Only, DBSG — Format, HAMR — Hannya, MPS7 — Chaos Domain;
- 14 missing Tier recipes, all melee; missing recipe evidence is **not** proof of non-craftable;
- `short_description` remains untrusted because of the observed Kukri/fish-text cross-wire.

## Armor & Sets

Armor stays `SOON` until a fresh v1.5.12.3+ snapshot proves collision-free real output. Set-centric route, audit, materializer, and identity tests are ready.

## Current Calibrations

Canonical current contract:

- schema `dead-signal-calibrations`;
- schema_version `2`;
- publication_status `ready-current-system` only at exactly 94 unambiguous current families;
- exactly one current variant per family; legacy rows remain audit-only.

Proven Weapon DMG ranges: Rare 18–25%, Epic 26–33%, Legendary 34–50%. My Gear uses exact numeric inputs; no sliders.

Do not reintroduce obsolete schema `dead-signal-calibrations-current`.

## Mods / Attachments / Deviations / Cradles

- Mods: preserve mined variants; current Mod 2.0 player-selectable identity still needs fresh proof.
- Attachments: player weapon slots only — Sight, Muzzle, Tactical, Magazine. Last verified player-facing count was 119 = 30 / 36 / 36 / 17; raw 202 is not the picker target.
- Deviations / Cradles: preserve source variants. Variant guard blocks planner promotion when identity is ambiguous.

## Next exact sequence

1. Deploy current `main` through the existing cPanel Git Version Control production workflow.
2. Finish and prove the v1.5.12.3 Windows Miner package path.
3. Release v1.5.12.3 through the existing version-driven workflow.
4. Run v1.5.12.3 against the real Once Human install.
5. Audit/materialize Weapons and browser-verify the full production vertical.
6. Use fresh evidence to investigate unresolved non-Common weapon effects, unsafe descriptions, and missing melee recipes.
7. Verify/materialize Armor.
8. Materialize/test the 94-family current Calibration contract.
9. Prove current Mod 2.0 variant identity.
10. Reconcile/materialize player-selectable Attachments and compatibility.
11. Resolve Deviation/Cradle variant semantics or provide explicit variant choice.
12. Remove old Build Lab compatibility pools only after canonical end-to-end verification.
13. After the core is broadly complete, audit current competitor UX/features and implement evidence-backed differentiators.

## Read first next session

`PROJECT-RULES.md`, `tools/miner/release/latest.json`, `tools/miner/src/miner_entry.py`, `publish_extended_web_data.py`, `publish_current_calibrations.py`, `normalize_weapons.py`, `normalize_armor.py`, `tools/site/materialize-weapons-web.py`, `materialize-armor-web.py`, `materialize-extended-contract.py`, `database/calibrations/index.html`, `preview/build-lab/canonical-category-bridge.js`, `canonical-category-variant-guard.js`, `.github/workflows/test-site-tools.yml`, `.cpanel.yml`.
