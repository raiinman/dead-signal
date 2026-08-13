# Dead Signal — AI Continuity / Handoff

> Canonical current-state handoff. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Updated **2026-08-13 — Day Shift contract hardening after Miner v1.5.12.3 release**.

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

Current code HEAD immediately before this continuity-only handoff commit: **`0fa53a903024493c48c69b1cc54f34653398079e`**.

Major commits in this Day Shift continuation:

- `123df8575da5634c41ea2a7575855d9e7a7d1e75` — normal Windows Miner CI now source-self-tests canonical `miner_entry.py`, builds the packaged app, and packaged-self-tests the executable/updater.
- `3a47e01c1ec1dc093fe7173c81c5924e762d76f3` — release workflow source self-test now also uses `miner_entry.py` before packaging.
- `f97f23f1d854bdd03fd051227d73b078002135f0` — intentional VERSION bump to Miner **v1.5.12.3**.
- `a5a45af0dc737444516075cd0fb9746ac8dea77b` — release pipeline published the verified v1.5.12.3 updater manifest.
- `e7b69c3262a10bd6c1a35dd0ca9b057240d1e4e0` — hardened Weapons materializer progression invariants.
- `ee63207a02cb74bd3b94e9f51dc5913b8cad5168` — upgraded the Weapons materializer fixtures/tests for the strict invariants.
- `4cf3119225f9fb917430fdb3a63164c66759b2e5` — browser Weapons adapter now independently enforces legal Tier/Star coverage and recomputes proven Base Attack before exposing the compatibility model.
- `a3cb93864e6e7ae7ff68a41f949eec888ce6a8fb` — executable Node regression test for the browser Weapons contract guard.
- `7eccf74cf09848858a9fec9df60f5e931e02dd29` — site CI now runs the browser Weapons contract regression test.
- `cd56eb1154f19ac76de5f7b8eadc687f980c53e2` — Armor materializer now requires player-facing slot identity, exact Tier I–V coverage, and internally consistent set piece counts.
- `67c73718b1ebe399f26c048b7d7fd6ed48ca2237` — Armor materializer fixtures/tests upgraded for the stricter invariants.
- `838688ebdd9173c95e0667b6ae95ec40072c7997` — Build Lab current Calibration bridge now validates unique canonical identity, exact one-variant current classification, D0102 semantics, and rarity-specific Weapon DMG ranges before applying canonical data.
- `0fa53a903024493c48c69b1cc54f34653398079e` — generic extended contract materializer now fails closed on unsupported schema/status/current Calibration/Attachment/family contract shapes.

Windows Miner CI run `31733538266` completed **SUCCESS**.

Release run `31733912979` completed **SUCCESS**, including source tests, Windows packaging, packaged self-test, release packaging, GitHub release publication, public re-download verification, SHA-256/size verification, and updater-manifest publication last.

Site CI run `31734057972` completed **SUCCESS** after the strict Weapons materializer/tests.

Site CI run `31739048192` completed **SUCCESS** after browser Weapons and stricter Armor materializer coverage were in place.

Site CI runs `31739311768` and `31739381588` completed **SUCCESS** for the hardened current Calibration Build Lab bridge and extended compact materializer respectively.

## Miner v1.5.12.3 — RELEASED

Canonical updater manifest now publishes:

- Version: **1.5.12.3**
- Channel: `stable`
- SHA-256: `a8da5c1bad02d1cb688a44d66438d2a24f33feebc3c06b7ae541998f9edbabd9`
- Size: `30,703,410` bytes
- Asset: `Dead-Signal-Miner-v1.5.12.3-Windows.zip`

The canonical packaging path is now proven end-to-end:

1. `tools/miner/src/miner_entry.py` is the source self-test entrypoint;
2. `tools/miner/build.ps1` packages `miner_entry.py`;
3. `publish_extended_web_data` and `publish_current_calibrations` are explicit hidden imports;
4. normal Miner CI builds and packaged-self-tests the Windows app;
5. release CI repeats source + packaged gates before publication;
6. updater manifest is written only after public asset hash/size verification.

Do not weaken this pipeline.

## Fresh-artifact boundary — next human step

The repository session still cannot run the Miner against the user's installed Once Human files.

The **next evidence-producing step is for the user to run Miner v1.5.12.3 locally against the real Once Human install** and make the resulting fresh published artifact available to the repository workflow/session.

Do not pretend fresh v1.5.12.3 Armor/Mod/Attachment/Deviation/Cradle evidence exists before that run.

Continue every repository-side task that does not require inventing the artifact.

## Weapons — gold-standard vertical

Last complete accessible snapshot proved:

- 120 weapons = 95 ranged + 25 melee;
- 600 Gear Tier rows;
- 545 Blueprint-Star rows;
- 2,725 legal Tier × Star combinations;
- 120/120 artwork;
- 95/95 firearm profiles resolved.

Player-facing Weapons currently provide catalogue, detail UX, Compare, legal Gear Tier × Blueprint Stars, Base Attack trace, proven static stats, acquisition/crafting evidence, provenance, unresolved-effect fallback messaging, and Build Lab handoff.

### Strict materializer + browser invariants now shipped

`tools/site/materialize-weapons-web.py` and `database/weapons/weapon-public-adapter.js` now independently fail closed unless each weapon proves:

- exactly five unique Gear Tier rows, I–V;
- exactly five unique Tier × Star matrix rows, I–V;
- a supported rarity with the exact legal Blueprint Star set `1..rarity_cap` on every Tier row;
- numeric `tier_base_attack_at_1_star`;
- numeric `preset_attack_ratio` for every star row;
- integral published Base Attack;
- `base_attack == int(tier_base_attack_at_1_star * preset_attack_ratio)` exactly;
- no upstream progression validation issues.

`tools/site/tests/test_materialize_weapons_web.py` covers missing stars, unknown rarity, missing Tier-base evidence, missing ratio evidence, Base Attack mismatch, fractional published Base Attack, duplicate IDs, count mismatches, Tier identity, and unresolved validation issues. `tools/site/tests/test-weapon-public-adapter.js` independently proves valid browser payload promotion and fail-closed behavior for missing Stars, duplicate/missing Tiers, formula mismatches, missing ratios, and unsupported rarity.

### Remaining Weapons evidence queue

- 76/120 effects resolved; 44 unresolved/absent, including 29 Common;
- unresolved Legendary examples include G17 — Cash Only, DBSG — Format, HAMR — Hannya, MPS7 — Chaos Domain;
- 14 missing Tier recipes, all melee; missing recipe evidence is **not** proof of non-craftable;
- normalized `short_description` remains intentionally withheld publicly because of the observed Kukri/fish-text cross-wire.

`normalize_weapons.py` currently obtains `short_description` from translated `item.short_desc`; the compact publisher outputs blank `description` with `withheld-until-short-description-resolver-is-verified`. Do not expose those descriptions until fresh v1.5.12.3 evidence resolves the translation/reference identity problem.

## Production website / Build Lab state

Current `main` already includes:

- Weapons compact integrity/progression guards at both materialization and browser-adapter boundaries, catalogue/detail/Compare, acquisition/crafting evidence, unresolved-effect fallback, provenance, and Build Lab handoff.
- Variant-aware Armor identity using `ds-a-{suit_id}-{blueprint_id}`, plus set-centric route, audit, strict materializer, and tests.
- Current Calibration v2 projector and dedicated standalone renderer; Build Lab bridge now revalidates current-system invariants before applying canonical data.
- Prepared fail-closed routes for Mods, Attachments, Deviations, and Cradle Overrides.
- Extended materialization now requires the publisher's expected schema version/status and category-specific readiness markers instead of accepting any same-schema payload.
- Build Lab canonical-category readiness/mapping/variant guards.
- Workstation shell exposes Miner context and is syntax-tested.

`.cpanel.yml` remains copy-only. Armor, Mods, Calibrations, Deviations, and Cradle Overrides remain `SOON` until real compact contracts prove them ready.

Two old Build Lab compatibility files remain hosting-installed only and are not in Git:

- `preview/build-lab/data/community-data.js`
- `preview/build-lab/app.js`

Do not remove those compatibility pools until canonical end-to-end browser behavior is verified.

## Armor & Sets

Armor stays `SOON` until a fresh v1.5.12.3 real snapshot proves collision-free variant identity and current recipe/effect invariants. Set-centric route, audit, materializer, and identity tests are ready.

The Armor materializer now additionally requires every player-facing piece to have a slot, exactly five unique Gear Tier rows I–V, parent/piece `suit_id` agreement, variant-aware canonical identity, and matching declared set piece counts.

**Build Lab Armor handoff remains a separate verified boundary:** the legacy `community-data.js` and `app.js` consumed by the deployed planner are hosting-installed and absent from Git, so this repository session cannot prove the exact legacy Armor collection/mutation contract. Do not guess that bridge. Prepare/activate it only after those runtime files or an equivalent canonical planner contract are available for inspection.

Never classify missing forge data as non-craftable without direct game evidence.

## Current Calibrations

Canonical current contract:

- schema `dead-signal-calibrations`;
- schema_version `2`;
- publication_status `ready-current-system` only at exactly 94 unambiguous current families;
- exactly one current variant per family; legacy rows remain audit-only.

Proven Weapon DMG ranges: Rare 18–25%, Epic 26–33%, Legendary 34–50%. My Gear uses exact numeric inputs; no sliders.

Both the generic materialization boundary and Build Lab canonical bridge now independently require the v2 current-system classification, 94 families, one variant each, no duplicate/ambiguous family IDs, D0102 main-roll identity, and the exact rarity-specific roll ranges before promotion.

Do not reintroduce obsolete schema `dead-signal-calibrations-current` or route current Calibration behavior through the generic legacy renderer. `database/calibrations/index.html` remains the dedicated current-system renderer.

## Mods / Attachments / Deviations / Cradles

- Mods: preserve mined variants; current Mod 2.0 player-selectable identity still needs fresh proof. Materialization requires schema v1 and publisher status `mod-code-family-projection-variants-preserved` with at least one source variant per family.
- Attachments: player weapon slots only — Sight, Muzzle, Tactical, Magazine. Last verified player-facing count was 119 = 30 / 36 / 36 / 17; raw 202 is not the picker target. Materialization now rejects non-ready contracts, duplicate IDs, missing/extra slot classes, or records outside those four player slots.
- Deviations / Cradles: preserve source variants. Materialization requires the publisher's variant-preserving status; Build Lab separately blocks promotion when canonical families remain ambiguous or contracts are unready.

## Next exact sequence

1. User runs released Miner **v1.5.12.3** against the real Once Human install and provides/makes available the fresh published artifact.
2. Audit/materialize Weapons from that output; investigate unresolved non-Common effects, unsafe short descriptions, and missing melee recipes.
3. Verify Armor variant identity, recipe/effect invariants, materialize Armor & Sets, then integrate only if the contract passes and the planner's legacy Armor target contract is inspectable.
4. Materialize/test the 94-family current Calibration contract end-to-end; the repository-side validator/Build Lab gate is now prepared.
5. Prove current Mod 2.0 variant identity and migrate it; reject stale/unsupported publisher status at materialization.
6. Reconcile/materialize the 119 player-selectable Attachments and compatibility; the materializer now rejects non-player slot types.
7. Resolve Deviation/Cradle variant semantics or provide explicit variant choice before planner promotion.
8. Finish Build Lab canonical migration and remove old compatibility pools only after end-to-end verification.
9. After core functionality is broadly complete, audit current Wikily / OnceHumanDB UX/features and implement evidence-backed differentiators without using their corpus counts as completeness targets.

## Read first next session

`PROJECT-RULES.md`, `tools/miner/release/latest.json`, `tools/miner/VERSION`, `tools/miner/src/miner_entry.py`, `tools/miner/build.ps1`, `tools/miner/tests/test_packaging_entrypoint.py`, `.github/workflows/test-miner.yml`, `.github/workflows/release-miner-v1512.yml`, `publish_extended_web_data.py`, `publish_current_calibrations.py`, `normalize_weapons.py`, `normalize_armor.py`, `tools/site/materialize-weapons-web.py`, `tools/site/tests/test_materialize_weapons_web.py`, `tools/site/tests/test-weapon-public-adapter.js`, `audit-weapons-contract.py`, `materialize-armor-web.py`, `materialize-extended-contract.py`, `database/calibrations/index.html`, `preview/build-lab/canonical-category-bridge.js`, `canonical-category-variant-guard.js`, `.github/workflows/test-site-tools.yml`, `.cpanel.yml`.
