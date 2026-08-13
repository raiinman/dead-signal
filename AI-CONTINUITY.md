# Dead Signal — AI Continuity / Handoff

> Canonical current-state handoff. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Updated **2026-08-13 — Day Shift canonical Miner packaging proof**.

## Rules that must not drift

- Repo: `raiinman/dead-signal`; canonical branch: **`main` only**.
- Dead Signal is a prepared static database + Build Lab workstation. **No WordPress runtime.**
- Production deploys use the existing cPanel Git Version Control workflow; `.cpanel.yml` stays **copy-only**.
- Installed-game/Miner evidence is canonical. External databases are UX/terminology references only.
- Never invent mechanics, compatibility, recipes, proc behavior, DPS, rankings, or multiplier semantics.
- Preserve the accepted landing page and Official Once Human X feed unless there is a concrete bug.
- Preserve the one global workstation shell/readability system.
- Unfinished database categories remain visibly `SOON` until verified compact contracts are ready.
- Do not touch domain/DNS/SSL/cPanel hosting configuration while the user's separate SSL work remains in progress unless explicitly asked in that context.

## Current HEAD / latest verified work

Latest verified functional commits:

- `fc05b0f1669a003ab8846e188b13ba776f6f617f` — packages the Miner through `tools/miner/src/miner_entry.py` and explicitly includes `publish_extended_web_data` + `publish_current_calibrations` as PyInstaller hidden imports.
- `3bf9334287ec74eab53e61ec0bc2a76f28ad1151` — adds `tools/miner/tests/test_packaging_entrypoint.py` to statically guard the canonical packaging contract.
- `123df8575da5634c41ea2a7575855d9e7a7d1e75` — normal Windows Miner CI now source-self-tests `miner_entry.py`, builds the packaged app, and packaged-self-tests the executable/updater.
- `3a47e01c1ec1dc093fe7173c81c5924e762d76f3` — release workflow source self-test now also uses `miner_entry.py` before its existing package/release verification pipeline.

Windows Miner CI run `31733538266` completed **SUCCESS**. It proved all of the following on a Windows runner:

1. source compile succeeds;
2. Miner unit tests succeed;
3. canonical `miner_entry.py --self-test` succeeds;
4. `build.ps1` packages the Miner successfully;
5. packaged `Dead Signal Miner.exe --self-test` succeeds;
6. packaged updater helper exists.

The prior workflow-write tooling blocker is therefore resolved.

## Miner release boundary — exact current state

Released Miner remains **v1.5.12.2**.

Current `tools/miner/VERSION` is still `1.5.12.2`.

The repository is now technically ready for the intentional **v1.5.12.3** bump: canonical source and packaged Windows gates both pass and the release workflow uses the same canonical entrypoint.

However, this automation session's connector refused the `tools/miner/VERSION` write itself with a safety/tooling block. This is **not** a code or CI failure. Do not claim v1.5.12.3 was released until the VERSION bump actually lands and the release workflow finishes successfully.

Once the VERSION bump can be written, let the existing release pipeline build, self-test, publish, re-download/hash/size-verify the public asset, and publish `tools/miner/release/latest.json` last. Do not bypass that sequence.

## Production website / Build Lab state

Current `main` already includes:

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

## Weapons — gold-standard vertical

Last complete accessible snapshot proved:

- 120 weapons = 95 ranged + 25 melee;
- 600 Gear Tier rows;
- 545 Blueprint-Star rows;
- 2,725 legal Tier × Star combinations;
- 120/120 artwork;
- 95/95 firearm profiles resolved.

Player-facing Weapons currently provide catalogue, detail UX, Compare, legal Gear Tier × Blueprint Stars, Base Attack trace, proven static stats, acquisition/crafting evidence, provenance, unresolved-effect fallback messaging, and Build Lab handoff.

`database/weapons/weapon-public-adapter.js` fails closed on malformed compact Weapons contracts. `tools/site/audit-weapons-contract.py` independently validates Gear Tier I–V and recomputes published Base Attack from the proven Tier-base × Blueprint-Star ratio rule.

Remaining evidence queue:

- 76/120 effects resolved; 44 unresolved/absent, including 29 Common;
- unresolved Legendary examples include G17 — Cash Only, DBSG — Format, HAMR — Hannya, MPS7 — Chaos Domain;
- 14 missing Tier recipes, all melee; missing recipe evidence is **not** proof of non-craftable;
- normalized `short_description` is intentionally withheld publicly because of an observed Kukri/fish-text cross-wire.

`normalize_weapons.py` obtains `short_description` from translated `item.short_desc`; the compact publisher deliberately outputs blank `description` with `withheld-until-short-description-resolver-is-verified`. Do not expose those descriptions until fresh evidence resolves the translation/reference identity problem.

### Weapons materializer hardening

A prior half-change at `6ee1784aaee6bbbab7bb3da1e59b7aa4f08c7176` tried to make `materialize-weapons-web.py` enforce exact rarity star sets and recompute Base Attack, but stale fixtures made site CI fail. `6511987a67d814a530734167177ab98de9be2c88` restored the verified materializer.

The correct next repository-side improvement is an **atomic** materializer + fixture/test change that enforces:

- exact Blueprint Star set `1..rarity_cap` for every Tier row;
- numeric `tier_base_attack_at_1_star`;
- numeric `preset_attack_ratio` per star;
- `base_attack == int(tier_base_attack_at_1_star * preset_attack_ratio)` exactly.

This automation session attempted an atomic Git-object write for that change, but the connector safety layer rejected blob creation. Do not repeat a one-file half-change; either land implementation + tests atomically or leave the existing green implementation in place.

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

The repository session cannot run the Miner against the user's installed Once Human files. A fresh v1.5.12.3+ mined artifact exists only after the verified release is published and the user runs it locally.

Do not pretend fresh Armor/Mod/Attachment/Deviation/Cradle evidence exists before that run. Continue every repository-side task that does not require inventing the artifact.

## Next exact sequence

1. Land the intentional `tools/miner/VERSION` bump from `1.5.12.2` to `1.5.12.3` when tooling permits.
2. Verify the release workflow completes end-to-end and `tools/miner/release/latest.json` is updated only after public asset verification.
3. User runs v1.5.12.3 against the real Once Human install.
4. Audit/materialize Weapons from fresh output; investigate unresolved non-Common effects, unsafe descriptions, and missing melee recipes.
5. Upgrade Weapons materializer + tests atomically to exact star-set and Base Attack recomputation invariants if not already landed.
6. Verify/materialize Armor and integrate only after real-output invariants pass.
7. Materialize/test the 94-family current Calibration contract end-to-end.
8. Prove current Mod 2.0 variant identity and migrate it.
9. Reconcile/materialize the 119 player-selectable Attachments and compatibility.
10. Resolve Deviation/Cradle variant semantics or provide explicit variant choice before planner promotion.
11. Remove old Build Lab compatibility pools only after canonical end-to-end verification.
12. After core functionality is broadly complete, audit current Wikily / OnceHumanDB UX/features and implement evidence-backed differentiators.

## Read first next session

`PROJECT-RULES.md`, `tools/miner/release/latest.json`, `tools/miner/VERSION`, `tools/miner/src/miner_entry.py`, `tools/miner/build.ps1`, `tools/miner/tests/test_packaging_entrypoint.py`, `.github/workflows/test-miner.yml`, `.github/workflows/release-miner-v1512.yml`, `publish_extended_web_data.py`, `publish_current_calibrations.py`, `normalize_weapons.py`, `normalize_armor.py`, `tools/site/materialize-weapons-web.py`, `tools/site/tests/test_materialize_weapons_web.py`, `audit-weapons-contract.py`, `materialize-armor-web.py`, `materialize-extended-contract.py`, `database/calibrations/index.html`, `preview/build-lab/canonical-category-bridge.js`, `canonical-category-variant-guard.js`, `.github/workflows/test-site-tools.yml`, `.cpanel.yml`.
