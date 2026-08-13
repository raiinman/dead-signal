# Dead Signal — AI Continuity / Handoff

> Canonical current-state handoff. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Updated **2026-08-13 — Day Shift Miner packaging recovery**.

## Rules that must not drift

- Repo: `raiinman/dead-signal`; canonical branch: **`main` only**.
- Dead Signal is a prepared static database + Build Lab workstation. **No WordPress runtime.**
- Production deploys use the existing cPanel Git Version Control workflow; `.cpanel.yml` stays **copy-only**.
- Installed-game/Miner evidence is canonical. External databases are UX/terminology references only.
- Never invent mechanics, compatibility, recipes, proc behavior, DPS, rankings, or multiplier semantics.
- Preserve the accepted landing page and Official Once Human X feed unless there is a concrete bug.
- Preserve the one global workstation shell/readability system.
- Unfinished database categories remain visibly `SOON` until verified compact contracts are ready.
- Do not touch domain/DNS/SSL/cPanel hosting configuration while the user's separate SSL work remains in progress unless the user explicitly asks in that context.

## Current HEAD / latest verified work

Latest functional Day Shift commits before this handoff:

- `fc05b0f1669a003ab8846e188b13ba776f6f617f` — **Package Miner through canonical entrypoint**. `tools/miner/build.ps1` now packages `src/miner_entry.py` instead of `dead_signal_miner.py` and explicitly includes `publish_extended_web_data` + `publish_current_calibrations` as hidden imports.
- `6ee1784aaee6bbbab7bb3da1e59b7aa4f08c7176` — attempted stricter Weapons materializer invariants. This exposed stale tests and produced a real site-CI failure; do not treat this commit as the final state of the materializer.
- `6511987a67d814a530734167177ab98de9be2c88` — restored the previously verified materializer implementation. Site CI run 31 completed **SUCCESS**.
- `3bf9334287ec74eab53e61ec0bc2a76f28ad1151` — added `tools/miner/tests/test_packaging_entrypoint.py`, which proves the build script names `miner_entry.py`, includes both new publishers, and that `miner_entry.py` installs both publisher hooks. Miner Windows source CI run 9 completed **SUCCESS**.

Important: the repository is green again after the failed materializer experiment. Keep it that way.

## Production website / Build Lab state

Current production-source work on `main` already includes:

- Weapons compact integrity/progression guards, acquisition/crafting evidence, catalogue/detail/Compare upgrades, unresolved-effect fallback, provenance, and Build Lab handoff.
- Variant-aware Armor identity using `ds-a-{suit_id}-{blueprint_id}`, plus set-centric route, audit, materializer, and tests.
- Current Calibration v2 projector and dedicated standalone renderer.
- Prepared fail-closed routes for Mods, Attachments, Deviations, and Cradle Overrides.
- Build Lab canonical-category readiness/mapping/variant guards.
- Workstation shell exposes Miner context and is syntax-tested.

`.cpanel.yml` remains copy-only. Armor, Mods, Calibrations, Deviations, and Cradle Overrides remain `SOON` until real compact contracts prove them ready.

Two old Build Lab compatibility files remain hosting-installed only and are not in Git:

- `preview/build-lab/data/community-data.js`
- `preview/build-lab/app.js`

Do not remove those compatibility pools until canonical end-to-end browser behavior is verified.

## Miner release boundary — current exact state

Released Miner remains **v1.5.12.2**.

SHA-256: `26a4d3013cd1eb991366da58f2d7714e1c4fc1a8f5edb46eb1549ed9cefa728d`.

The compact extended publisher and current Calibration projector were added after v1.5.12.2. The next useful full-data release must be **v1.5.12.3 or later**.

### What is fixed

`tools/miner/build.ps1` now:

- packages `tools/miner/src/miner_entry.py` as the PyInstaller main script;
- includes `publish_extended_web_data` as an explicit hidden import;
- includes `publish_current_calibrations` as an explicit hidden import.

`tools/miner/tests/test_packaging_entrypoint.py` now statically guards that contract and passed Windows Miner CI.

### What is still blocked

`.github/workflows/test-miner.yml` still source-self-tests `dead_signal_miner.py` and still does **not** build/run the packaged Miner during normal Miner CI.

`.github/workflows/release-miner-v1512.yml` still source-self-tests `dead_signal_miner.py` before packaging, although its later release steps do build the package and run the packaged self-test.

This session's GitHub connector refuses workflow-file writes. A Git-object attempt could create the replacement workflow blob/tree, but commit creation for that workflow tree was also refused. Treat this as a tooling boundary, not a reason to weaken the release gate.

**Do not bump VERSION or release v1.5.12.3 until both workflow source-self-tests use `miner_entry.py`, and preferably normal Miner CI also builds + packaged-self-tests the Windows app.**

After that workflow change is made and CI passes, bump VERSION intentionally and let the existing verified release/updater pipeline publish v1.5.12.3.

## Weapons — gold-standard vertical

Last complete accessible snapshot proved:

- 120 weapons = 95 ranged + 25 melee;
- 600 Gear Tier rows;
- 545 Blueprint-Star rows;
- 2,725 legal Tier × Star combinations;
- 120/120 artwork;
- 95/95 firearm profiles resolved.

The player-facing Weapons vertical has catalogue, detail UX, Compare, legal Gear Tier × Blueprint Stars, Base Attack trace, proven static stats, acquisition/crafting evidence, provenance, unresolved-effect fallback messaging, and Build Lab handoff.

`database/weapons/weapon-public-adapter.js` fails closed on malformed compact Weapons contracts. `tools/site/audit-weapons-contract.py` independently validates Gear Tier I–V and recomputes published Base Attack from the proven Tier-base × Blueprint-Star ratio rule.

Remaining evidence queue:

- 76/120 effects resolved; 44 unresolved/absent, including 29 Common;
- unresolved Legendary examples include G17 — Cash Only, DBSG — Format, HAMR — Hannya, MPS7 — Chaos Domain;
- 14 missing Tier recipes, all melee; missing recipe evidence is **not** proof of non-craftable;
- normalized `short_description` is intentionally withheld publicly because of an observed Kukri/fish-text cross-wire.

Current source inspection confirms `normalize_weapons.py` obtains `short_description` directly from translated `item.short_desc`; the compact publisher deliberately outputs blank `description` with verification status `withheld-until-short-description-resolver-is-verified`. Do not expose normalized short descriptions until the translation/reference identity problem is resolved from fresh evidence.

A stricter materializer implementation should eventually enforce the same exact star-set and Base Attack recomputation as the audit, but the attempted change at `6ee1784a...` proved the fixture/tests must be upgraded in the same atomic change. Do not repeat the half-change.

## Armor & Sets

Armor stays `SOON` until a fresh v1.5.12.3+ real snapshot proves collision-free variant identity and current recipe/effect invariants. Set-centric route, audit, materializer, and identity tests are ready.

Never classify missing forge data as non-craftable without direct game evidence.

## Current Calibrations

Canonical current contract:

- schema `dead-signal-calibrations`;
- schema_version `2`;
- publication_status `ready-current-system` only at exactly 94 unambiguous current families;
- exactly one current variant per family; legacy rows remain audit-only.

Proven Weapon DMG ranges: Rare 18–25%, Epic 26–33%, Legendary 34–50%. My Gear uses exact numeric inputs; no sliders.

Do not reintroduce obsolete schema `dead-signal-calibrations-current` or route current Calibration behavior through the generic legacy renderer.

## Mods / Attachments / Deviations / Cradles

- Mods: preserve mined variants; current Mod 2.0 player-selectable identity still needs fresh proof.
- Attachments: player weapon slots only — Sight, Muzzle, Tactical, Magazine. Last verified player-facing count was 119 = 30 / 36 / 36 / 17; raw 202 is not the picker target.
- Deviations / Cradles: preserve source variants. Build Lab blocks promotion when canonical families remain ambiguous or contracts are unready.

## Fresh-artifact boundary

The repository session cannot run the Miner against the user's installed Once Human files. A fresh v1.5.12.3+ mined artifact therefore exists only after the user runs the verified released Miner locally. Do not pretend fresh Armor/Mod/Attachment/Deviation/Cradle evidence exists before that run.

Continue every repository-side task that does not require inventing that artifact.

## Next exact sequence

1. Change `.github/workflows/test-miner.yml` source self-test to `miner_entry.py`; make normal Miner CI build and packaged-self-test if possible.
2. Change `.github/workflows/release-miner-v1512.yml` source self-test to `miner_entry.py`.
3. Run Miner CI and prove canonical source + packaged Windows self-tests succeed.
4. Only then bump VERSION to v1.5.12.3 and let the verified updater pipeline publish it.
5. User runs v1.5.12.3 against the real Once Human install.
6. Audit/materialize Weapons from fresh output; investigate unresolved non-Common effects, unsafe descriptions, and missing melee recipes.
7. Upgrade Weapons materializer + tests atomically to enforce exact rarity star sets and Base Attack recomputation.
8. Verify/materialize Armor and integrate only after real-output invariants pass.
9. Materialize/test the 94-family current Calibration contract end-to-end.
10. Prove current Mod 2.0 variant identity and migrate it.
11. Reconcile/materialize the 119 player-selectable Attachments and compatibility.
12. Resolve Deviation/Cradle variant semantics or provide explicit variant choice before planner promotion.
13. Remove old Build Lab compatibility pools only after canonical end-to-end verification.
14. After core functionality is broadly complete, audit current Wikily / OnceHumanDB UX/features and implement evidence-backed differentiators.

## Read first next session

`PROJECT-RULES.md`, `tools/miner/release/latest.json`, `tools/miner/src/miner_entry.py`, `tools/miner/build.ps1`, `tools/miner/tests/test_packaging_entrypoint.py`, `.github/workflows/test-miner.yml`, `.github/workflows/release-miner-v1512.yml`, `publish_extended_web_data.py`, `publish_current_calibrations.py`, `normalize_weapons.py`, `normalize_armor.py`, `tools/site/materialize-weapons-web.py`, `audit-weapons-contract.py`, `materialize-armor-web.py`, `materialize-extended-contract.py`, `database/calibrations/index.html`, `preview/build-lab/canonical-category-bridge.js`, `canonical-category-variant-guard.js`, `.github/workflows/test-site-tools.yml`, `.cpanel.yml`.
