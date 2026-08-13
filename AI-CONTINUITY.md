# Dead Signal — AI Continuity / Handoff

> Canonical current-state handoff. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Updated **2026-08-13 — Day Shift after Miner v1.5.12.3 release, transactional snapshot ingestion, and dedicated Mod 2.0 route**.

## Rules that must not drift

- Repo: `raiinman/dead-signal`; canonical branch: **`main` only**.
- Dead Signal is a prepared static database + Build Lab workstation. **No WordPress runtime.**
- Production deploys use existing cPanel Git Version Control; `.cpanel.yml` stays **copy-only**.
- Installed-game/Miner evidence is canonical. External databases are UX/terminology references only.
- Never invent mechanics, compatibility, recipes, proc behavior, DPS, rankings, or multiplier semantics.
- Preserve the accepted landing page, Official Once Human X feed, one global workstation shell, and readability system unless there is a concrete bug.
- Unfinished database categories remain visibly `SOON` until verified compact contracts are actually materialized and browser-verified.
- Do not touch domain/DNS/SSL/cPanel hosting configuration unless explicitly asked in that context.

## Current checkpoint

Latest verified functional code HEAD before this handoff update:

`c59218c855d77239b02f424661aaf9a90d26675b` — **Keep renderer wiring tests behavior-focused**.

Site CI run `31740889848` completed **SUCCESS**. Its Python materializer/audit suite, browser Weapons guard, and Node syntax checks all passed.

Important continuation commits after the prior handoff:

- `4fef86f7cc8be52e16bcaaa0865248f2dff97f38` — add transactional all-category Miner snapshot materializer.
- `bce21b4cc11e195ee65e9bd23a7018e50d2c22e0` — regression-test dry-run, all-seven commit, validation fail-closed behavior, and rollback after a mid-commit filesystem failure.
- `1d049b35867cc294ce83817d998d4924df2c63ac` — dedicated Mod 2.0 renderer exposing mined family/variant evidence and main-entry level rows.
- `fc611f8cd326a24e676515d271566c747ef56d44` — route tests for the dedicated Mod renderer, including inline JavaScript syntax checking.
- `c59218c855d77239b02f424661aaf9a90d26675b` — correct route wiring tests so dedicated Calibrations/Mods are not required to load the generic renderer.

## Miner v1.5.12.3 — RELEASED

Canonical updater manifest:

- Version: **1.5.12.3**
- Channel: `stable`
- SHA-256: `a8da5c1bad02d1cb688a44d66438d2a24f33feebc3c06b7ae541998f9edbabd9`
- Size: `30,703,410` bytes
- Asset: `Dead-Signal-Miner-v1.5.12.3-Windows.zip`

Release pipeline `31733912979` completed **SUCCESS**: source tests, Windows packaging, packaged self-test, release packaging, GitHub release, public re-download, SHA/size verification, then updater-manifest publication.

Packaging path is proven: `miner_entry.py` → `build.ps1` → hidden imports for `publish_extended_web_data` / `publish_current_calibrations` → packaged self-test. Do not weaken it.

## Fresh-artifact boundary — next human evidence step

The repository session cannot mine the user's installed Once Human files.

The next evidence-producing step is still:

1. run **Miner v1.5.12.3** against the real Once Human install;
2. make the resulting fresh `published/` directory available to this workflow/session.

Do not pretend fresh v1.5.12.3 Armor/Mod/Attachment/Deviation/Cradle evidence exists before that run.

## Canonical fresh-snapshot ingestion — NEW

Do **not** materialize the seven website contracts manually one-by-one anymore.

Use:

```text
python tools/site/materialize-published-snapshot.py <fresh-published-dir> --dry-run --report <receipt.json>
```

If the dry-run passes and the report is reviewed, run the same command without `--dry-run`.

`tools/site/materialize-published-snapshot.py` is fail-closed and transactional:

- requires and validates Weapons, Armor, Calibrations, Mods, Attachments, Deviations, and Cradles before any website payload is replaced;
- delegates category semantics to the existing strict materializers instead of creating another normalization truth;
- stages all seven browser payloads first;
- replaces repository data files only after the whole snapshot passes;
- restores already-replaced files if the final commit phase fails;
- can emit a receipt containing source paths, SHA-256 hashes, schemas, statuses, generated timestamps, record counts, and presence/hashes for `data-quality.json` / `change-report.json`.

Tests in `tools/site/tests/test_materialize_published_snapshot.py` prove dry-run isolation, validation isolation, all-seven replacement, and rollback behavior.

## Weapons — gold-standard vertical

Last complete accessible snapshot proved:

- 120 weapons = 95 ranged + 25 melee;
- 600 Gear Tier rows;
- 545 Blueprint-Star rows;
- 2,725 legal Tier × Star combinations;
- 120/120 artwork;
- 95/95 firearm profiles resolved.

Player-facing Weapons currently provide catalogue, detail, Compare, legal Gear Tier × Blueprint Stars, Base Attack trace, proven static stats, acquisition/crafting evidence, provenance, unresolved-effect messaging, and Build Lab handoff.

Both the strict materializer and browser adapter independently require exact Tier I–V coverage, exact rarity-capped Star coverage, numeric Tier base / ratio evidence, integral Base Attack, exact `int(tier_base * ratio)` recomputation, unique IDs, and zero upstream progression validation issues.

Remaining evidence queue from the last accessible snapshot:

- 76/120 effects resolved; 44 unresolved/absent, including 29 Common;
- unresolved Legendary examples include G17 — Cash Only, DBSG — Format, HAMR — Hannya, MPS7 — Chaos Domain;
- 14 missing Tier recipes, all melee; missing recipe evidence is **not** proof of non-craftable;
- `short_description` remains intentionally withheld because of the observed Kukri/fish-text cross-wire.

Fresh v1.5.12.3 evidence is required before changing those conclusions.

## Armor & Sets

Armor remains `SOON` until a fresh v1.5.12.3 real snapshot proves collision-free variant identity and current recipe/effect invariants.

Variant-aware identity is `ds-a-{suit_id}-{blueprint_id}`. The set-centric route, audit, and materializer exist. Materialization requires parent/piece `suit_id` agreement, player-facing slot identity, exact Tier I–V coverage, unique canonical IDs, valid Key Armor IDs, and consistent declared counts.

Build Lab Armor handoff remains a separate boundary because the legacy `community-data.js` / `app.js` mutation contract is hosting-installed and absent from Git. Do not guess it.

## Current Calibrations

Canonical current contract:

- schema `dead-signal-calibrations`;
- schema_version `2`;
- publication_status `ready-current-system` only at exactly 94 unambiguous current families;
- exactly one selected current variant per family; legacy variants remain audit-only;
- main roll stat identity D0102;
- Weapon DMG ranges Rare 18–25%, Epic 26–33%, Legendary 34–50%.

Standalone `database/calibrations/index.html` is the dedicated current-system renderer. Build Lab independently revalidates the same current-system invariants before applying canonical Calibration data.

Do not reintroduce obsolete schema `dead-signal-calibrations-current` as a real contract.

## Mods 2.0 — dedicated evidence route now landed

`database/mods/index.html` no longer loads the generic category renderer. It requires:

- schema `dead-signal-mods`;
- schema_version `1`;
- publication_status `mod-code-family-projection-variants-preserved`;
- non-empty families with canonical IDs;
- preserved source variants whose declared variant count matches the actual array.

The route exposes only mined evidence already present in the compact contract:

- Mod family / mod code;
- every preserved source variant;
- rarity and Shiny identity;
- `main_entry_code`, `apply_range_code`, `genre_library_code`, `frame_code`;
- item ID, Shiny buff/replacement codes when present;
- all mined `main_entry_effects` level rows with names/descriptions/attribute codes/values/buff IDs.

Multi-variant families are visibly marked ambiguous. Dead Signal does **not** silently choose variant #1 or promote ambiguous families into Build Lab.

This is presentation of mined Mod evidence, not proof yet of complete current Mod 2.0 player-selectable identity. Fresh v1.5.12.3 output remains required.

## Attachments / Deviations / Cradles

- Attachments: compact publisher accepts player weapon slots only — Sight, Muzzle, Tactical, Magazine. Last verified player-facing count was 119 = 30 / 36 / 36 / 17; raw 202 is not a picker target. Materialization rejects unsupported status, duplicate IDs, missing/extra slot classes, and non-player slot records. Next repo UI target is a dedicated attachment renderer for static effects + compatibility.
- Deviations / Cradles: source variants stay preserved. Materialization requires the variant-preserving publisher status; Build Lab separately blocks promotion whenever a family remains ambiguous.

## Production website / Build Lab state

`.cpanel.yml` remains copy-only and already copies the prepared category routes/contracts and Build Lab canonical guard/bridge assets.

Landing page still correctly keeps Armor, Mods, Calibrations, Deviations, and Cradles `SOON` until real compact contracts are materialized and verified. Do not flip labels just because route source exists.

Two old Build Lab compatibility files remain hosting-installed only:

- `preview/build-lab/data/community-data.js`
- `preview/build-lab/app.js`

Do not remove those compatibility pools until canonical end-to-end browser behavior is verified.

## Next exact sequence

1. User runs Miner **v1.5.12.3** against the real Once Human install and supplies the fresh `published/` artifact.
2. Run `materialize-published-snapshot.py` in `--dry-run` mode and inspect the receipt / Miner reports.
3. If all seven contracts pass, transactionally materialize the snapshot.
4. Audit Weapons; investigate unresolved non-Common effects, unsafe descriptions, and missing melee recipes from fresh evidence.
5. Verify/materialize Armor and integrate only after both public contract and planner target identity are proven.
6. Verify the 94-family current Calibration contract end-to-end.
7. Use fresh Mod output to resolve current player-selectable family/variant identity; keep the dedicated evidence route fail-closed otherwise.
8. Build the dedicated Attachment route and reconcile current compatibility from the fresh 119-style player-slot corpus.
9. Resolve Deviation/Cradle variant semantics or provide explicit variant selection before planner promotion.
10. Finish Build Lab canonical migration; remove old compatibility pools only after end-to-end verification.
11. When core functionality is broadly complete, audit current Wikily / OnceHumanDB UX/features and implement evidence-backed differentiators without using their corpus counts as completeness targets.

## Read first next session

`PROJECT-RULES.md`, `tools/miner/release/latest.json`, `tools/miner/VERSION`, `tools/miner/src/miner_entry.py`, `tools/miner/build.ps1`, `.github/workflows/test-miner.yml`, `.github/workflows/release-miner-v1512.yml`, `publish_extended_web_data.py`, `publish_current_calibrations.py`, `normalize_weapons.py`, `normalize_armor.py`, `tools/site/materialize-published-snapshot.py`, `tools/site/tests/test_materialize_published_snapshot.py`, `materialize-weapons-web.py`, `materialize-armor-web.py`, `materialize-extended-contract.py`, `audit-weapons-contract.py`, `database/calibrations/index.html`, `database/mods/index.html`, `preview/build-lab/canonical-category-bridge.js`, `canonical-category-variant-guard.js`, `.github/workflows/test-site-tools.yml`, `.cpanel.yml`.
