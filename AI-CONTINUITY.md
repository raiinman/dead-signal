# Dead Signal — AI Continuity / Handoff

> Canonical current-state handoff. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Updated **2026-08-13 immediately before the 2:00 PM America/Phoenix Day Shift run**.

## 2:00 PM transition — READ THIS FIRST

The user has **Miner v1.5.12.3 running right now against the real Once Human install**. Do not ask them to rerun it unless the current run actually fails. The next high-value action is to consume the fresh `published/` artifact as soon as it becomes available.

Do not individually copy category JSON into website files. The repository now has a controlled inspection + transactional ingestion workflow.

### First command when the fresh `published/` folder is available

Run the read-only inspection first:

```text
python tools/site/inspect-published-snapshot.py <fresh-published-dir> --output <inspection-receipt.json>
```

This combines:

- strict all-seven materialization validation;
- Weapons contract audit;
- Armor contract audit;
- Mod / Attachment / Deviation / Cradle research queues.

If strict validation says `may_materialize=true`, run a transactional dry-run receipt:

```text
python tools/site/materialize-published-snapshot.py <fresh-published-dir> --dry-run --report <materialize-receipt.json>
```

Only after the receipts are reviewed should the same materializer be run without `--dry-run`.

### Important: Mod 2.0 progression research

A new observational audit landed at code commit `95feef4de36ef75dd2d82042808a91a2561be7db`:

```text
python tools/site/audit-mod-level-progression.py <fresh-published-dir> --output <mod-level-audit.json>
```

Why it exists: v1.5.12.3 already emits normalized `data/progression.json`, including the `mod_level` track sourced from `new_mod_level_data.json`. The audit compares numeric tokens in those rows with compact Mod `mod_code` / `main_entry_code` values **only as correlation evidence**. A numeric overlap is a research lead, never proof of a relationship.

The audit source is landed, but its dedicated unit-test file was not yet committed before this handoff. **Test it before relying on its results.** Do not change the public Mod contract based only on untested numeric overlap.

## Rules that must not drift

- Repo: `raiinman/dead-signal`; canonical branch: **`main` only**.
- Static database + Build Lab workstation. **No WordPress runtime.**
- Production deploy path: cPanel Git Version Control using copy-only `.cpanel.yml`.
- Installed-game / Miner evidence is canonical. External databases are UX/terminology references only.
- Never invent mechanics, compatibility, recipes, proc behavior, DPS, rankings, or multiplier semantics.
- Preserve accepted landing page and Official Once Human X feed unless there is a concrete bug.
- Preserve one global workstation shell/readability system.
- Unfinished categories stay visibly `SOON` until verified compact contracts are materialized and browser-verified.
- Do not touch DNS/SSL/cPanel hosting configuration unless explicitly asked in that context.
- Missing recipe evidence is never automatically classified as non-craftable.

## Current code checkpoint before this handoff commit

Latest code HEAD immediately before this continuity update:

`95feef4de36ef75dd2d82042808a91a2561be7db` — **Add Mod level progression correlation audit**.

Recent important commits:

- `4fef86f7cc8be52e16bcaaa0865248f2dff97f38` — transactional all-seven Miner snapshot materializer.
- `bce21b4cc11e195ee65e9bd23a7018e50d2c22e0` — dry-run, validation-isolation, all-seven replacement, and rollback tests.
- `1d049b35867cc294ce83817d998d4924df2c63ac` — dedicated Mod 2.0 evidence renderer.
- `fc611f8cd326a24e676515d271566c747ef56d44` — dedicated Mod route tests, including inline JS syntax check.
- `c59218c855d77239b02f424661aaf9a90d26675b` — behavior-focused route wiring tests for dedicated vs shared renderers.
- `56440076eb0e90c9895ef1c8dd08339b85402ad9` — extended Mod / Attachment / Deviation / Cradle research audit.
- `ad57fb660987c0899cb7235fcafdc734e2ba83b5` — extended audit regression tests.
- `8c782b132b2bf2a65a4335b8c797441ddadd3b1d` — combined fresh-snapshot inspection receipt.
- `f06fa9b18135874d3637568e2f8d7d2915dd3ae1` — combined inspection tests.
- `95feef4de36ef75dd2d82042808a91a2561be7db` — Mod-level progression correlation audit.

Verified CI:

- Site CI `31741728411` for `f06fa9b...` completed **SUCCESS**.
- Extended audit test run `31741510725` completed **SUCCESS**.
- Site CI `31740889848` after route-wiring correction completed **SUCCESS**.

The `95feef4...` Mod-level audit still needs its own targeted test before being treated as proven tooling.

## Miner v1.5.12.3 — RELEASED AND NOW RUNNING LOCALLY

Canonical updater manifest:

- Version: **1.5.12.3**
- Channel: `stable`
- SHA-256: `a8da5c1bad02d1cb688a44d66438d2a24f33feebc3c06b7ae541998f9edbabd9`
- Size: `30,703,410` bytes
- Asset: `Dead-Signal-Miner-v1.5.12.3-Windows.zip`

Release pipeline `31733912979` completed **SUCCESS** with source tests, Windows packaging, packaged self-test, public release verification, SHA/size verification, and updater-manifest publication last.

The user has started this released Miner on the actual game install. The fresh artifact is now the critical evidence source.

## Fresh snapshot tooling

### 1. Read-only inspection

`tools/site/inspect-published-snapshot.py`

Produces one receipt containing strict validation plus Weapons, Armor, and extended-category audit sections. Crucially, observational audits still run if strict materialization validation fails, so a bad snapshot yields actionable queues instead of only an exception.

Tests: `tools/site/tests/test_inspect_published_snapshot.py` at `f06fa9b...`.

### 2. Transactional materialization

`tools/site/materialize-published-snapshot.py`

Requires and validates all seven compact contracts before replacing any browser payload:

- Weapons
- Armor
- Calibrations
- Mods
- Attachments
- Deviations
- Cradles

It stages all seven outputs first and rolls back already-replaced files if final replacement fails. It can emit hashes, schemas, statuses, timestamps, record counts, and report-presence hashes.

Tests: `tools/site/tests/test_materialize_published_snapshot.py`.

### 3. Extended research queues

`tools/site/audit-extended-contracts.py`

Observational queues include:

- Mods: multi-variant families, variant-count mismatches, missing names/descriptions/main-entry rows, Shiny variants.
- Attachments: non-player slot records, missing names, missing static effect evidence, missing compatibility, missing images.
- Deviations: multi-variant families, variant-count mismatches, missing skill text/images.
- Cradles: multi-variant families, variant-count mismatches, missing descriptions/images/effect references.

Do not interpret an audit queue as proof that a record is invalid. It is a research queue.

## Weapons — gold-standard vertical

Last fully accessible pre-v1.5.12.3 snapshot proved:

- 120 weapons = 95 ranged + 25 melee;
- 600 Gear Tier rows;
- 545 Blueprint-Star rows;
- 2,725 legal Tier × Star combinations;
- 120/120 artwork;
- 95/95 firearm profiles resolved.

Current player-facing Weapons have catalogue, detail, Compare, legal Gear Tier × Blueprint Stars, Base Attack trace, proven static stats, acquisition/crafting evidence, provenance, unresolved-effect messaging, and Build Lab handoff.

Strict materializer + browser adapter independently enforce Tier I–V, legal rarity-capped stars, numeric Tier-base/ratio evidence, exact `int(tier_base * ratio)` Base Attack, unique IDs, and no upstream progression validation issues.

Old unresolved queue to re-check against the fresh snapshot:

- 76/120 effects resolved; 44 unresolved/absent, 29 Common;
- unresolved Legendary examples: G17 — Cash Only, DBSG — Format, HAMR — Hannya, MPS7 — Chaos Domain;
- 14 missing Tier recipes, all melee;
- `short_description` still intentionally withheld because of observed Kukri/fish-text cross-wire.

Do not carry those counts forward if fresh v1.5.12.3 proves they changed.

## Armor & Sets

Armor stays `SOON` until the fresh v1.5.12.3 snapshot passes identity and integrity gates.

Canonical set-piece identity is variant-aware:

`ds-a-{suit_id}-{blueprint_id}`

The set-centric route, audit, and strict materializer already exist. Required invariants include parent/piece `suit_id` agreement, player-facing slot, exact Tier I–V coverage, unique canonical identity, valid Key Armor IDs, and consistent declared counts.

Build Lab Armor remains a separate boundary because the deployed planner's legacy `community-data.js` / `app.js` mutation contract is hosting-installed and not in Git. Do not guess it.

## Current Calibrations

Required current contract:

- schema `dead-signal-calibrations`;
- schema_version `2`;
- publication_status `ready-current-system`;
- exactly 94 unambiguous current families;
- one current variant per family;
- D0102 main Weapon DMG roll identity;
- Rare 18–25%, Epic 26–33%, Legendary 34–50% Weapon DMG ranges.

`database/calibrations/index.html` is the dedicated current-system renderer. Build Lab revalidates the same invariants before applying canonical Calibration data.

## Mods 2.0

`database/mods/index.html` is a dedicated evidence renderer and does not load the generic extended renderer.

It accepts only:

- `dead-signal-mods` schema v1;
- publication status `mod-code-family-projection-variants-preserved`;
- non-empty canonical families with declared variant count equal to actual variants.

It exposes mined Mod evidence already in the compact contract: Mod code, all variants, rarity, Shiny identity, main-entry/apply-range/genre-library/frame codes, item ID, Shiny references, and `main_entry_effects` rows.

Multi-variant families remain visibly ambiguous and are not silently promoted to Build Lab.

Next Mod research once fresh output is available:

1. run the extended audit;
2. run the new Mod-level progression correlation audit;
3. inspect `data/progression.json` `mod_level` rows from `new_mod_level_data.json`;
4. prove key relationships before changing the compact contract to represent Lv1–17/fixed-subattribute semantics.

## Attachments

Compact publisher target is only player weapon slots:

- Sight
- Muzzle
- Tactical
- Magazine

Previous verified target was 119 player-facing records = 30 / 36 / 36 / 17; raw 202 was not the picker target. Re-check against fresh v1.5.12.3 instead of freezing the old count.

Materialization already rejects unsupported publisher status, duplicate IDs, missing/extra slot classes, and non-player slot records.

A richer dedicated Attachment renderer for static effect + compatibility is still a repo-side UI target. Several large browser-renderer writes were tool-safety false-positive blocked before this handoff; do not treat that as a product-data blocker. Continue via smaller safe changes if necessary.

## Deviations / Cradles

Source variants stay preserved. Materialization requires the variant-preserving publisher status. Build Lab separately blocks promotion when families remain ambiguous.

Fresh extended audit output should drive the next work; do not arbitrarily select source variant #1.

## Production website / Build Lab

`.cpanel.yml` remains copy-only and already deploys prepared category routes/contracts and Build Lab canonical guard/bridge assets.

Landing page stays truthful: unfinished categories remain `SOON` until their fresh contracts are materialized and browser-verified.

Hosting-only legacy Build Lab files:

- `preview/build-lab/data/community-data.js`
- `preview/build-lab/app.js`

Do not delete compatibility pools until canonical end-to-end behavior is proven.

## Exact next sequence for the 2:00 PM Day Shift

1. Read `PROJECT-RULES.md` and this file, then inspect latest `main` so concurrent work is not overwritten.
2. **First check whether the user's currently running Miner v1.5.12.3 has completed and whether the fresh `published/` artifact is accessible.**
3. If accessible, run `inspect-published-snapshot.py` first and preserve the receipt.
4. Test `audit-mod-level-progression.py` before relying on it; then run it on the fresh artifact.
5. Review strict validation + all research queues. Do not promote failing/ambiguous categories.
6. If strict all-seven validation passes, run transactional materializer dry-run, review receipt, then materialize all seven together.
7. Re-audit Weapons using fresh counts/evidence; attack non-Common unresolved effects, description resolver, and melee recipe gaps only from the fresh corpus.
8. Verify Armor identity/integrity; materialize it only if the fresh contract passes.
9. Verify current 94-family Calibrations end-to-end.
10. Use fresh Mod + progression evidence to determine current Mod 2.0 identity and Lv1–17/fixed-subattribute structure without guessing.
11. Reconcile Attachments from fresh player-slot corpus; then improve player-facing effect/compatibility UI.
12. Resolve Deviation/Cradle variant semantics before planner promotion.
13. Continue Build Lab canonical migration category by category; keep the legacy hosting pools until replacement is proven.
14. Only after core data/database functionality is broadly complete: live competitor UX audit against current Wikily / OnceHumanDB and implement evidence-backed differentiators.

## Read first / high-value files

- `PROJECT-RULES.md`
- `tools/miner/release/latest.json`
- `tools/miner/VERSION`
- `tools/miner/src/miner_entry.py`
- `tools/miner/src/extractor/publish_extended_web_data.py`
- `tools/miner/src/extractor/publish_current_calibrations.py`
- `tools/miner/src/extractor/normalize_extended.py`
- `tools/site/inspect-published-snapshot.py`
- `tools/site/tests/test_inspect_published_snapshot.py`
- `tools/site/materialize-published-snapshot.py`
- `tools/site/tests/test_materialize_published_snapshot.py`
- `tools/site/audit-weapons-contract.py`
- `tools/site/audit-armor-contract.py`
- `tools/site/audit-extended-contracts.py`
- `tools/site/tests/test_audit_extended_contracts.py`
- `tools/site/audit-mod-level-progression.py`
- `database/calibrations/index.html`
- `database/mods/index.html`
- `preview/build-lab/canonical-category-bridge.js`
- `preview/build-lab/canonical-category-variant-guard.js`
- `.github/workflows/test-site-tools.yml`
- `.cpanel.yml`
