# Dead Signal — AI Continuity / Handoff

> Read this file and `PROJECT-RULES.md` first. Canonical current-state handoff for `raiinman/dead-signal` on `main`.
>
> Updated **2026-08-13 Day Shift** after fresh installed-client proof, Miner v1.5.12.8 release, Mod frame-library research, and Deviation/Cradle browser hardening.

## Non-negotiables

- Work directly on canonical `main` unless the user explicitly requests otherwise.
- Installed-game / Miner evidence outranks guesses and community corpus counts.
- Never invent mechanics, recipes, compatibility, proc behavior, DPS, rankings, multiplier semantics, crafting identity, or variant identity.
- Missing recipe evidence never proves non-craftable.
- Preserve accepted landing page, Official Once Human X feed, global workstation shell, and readability system unless a concrete bug exists.
- Static/copy-only cPanel deployment. No WordPress runtime. Do not touch DNS, SSL, redirects, domain settings, or cPanel hosting configuration.
- Routes that are not genuinely ready remain `SOON`.
- Use transactional all-seven materialization for a final Miner snapshot; do not hand-copy one category around a blocked category.
- Competitor UX audit remains last, after core database + Build Lab migration is broadly complete.

## Stable Miner / current release

Miner **v1.5.12.8 is RELEASED and stable**.

Release chain:

- `28741e919668da0aac73b3f447298c193f5717d7` — fresh v1.5.12.7 installed-client evidence note.
- `2a48e197e33c956c4c90a1d3b1b0c101d6d1a1a7` — Calibration binary-float comparison repair.
- `b0b76b6a4d3ece160983d89366e83d673fe60ec8` — intentional VERSION bump to 1.5.12.8.
- `1329230baff3c7a24866dba0262e246c7c753aa0` — release bot publishes stable updater manifest last.

Release workflow `31756476284` completed **SUCCESS** through source tests, Windows build, packaged self-test, release publication, public re-download verification, and updater manifest last.

Stable package:

- Version: **1.5.12.8**
- SHA-256: `b70cd294fd45616ecbb5409fb3e790fecce1e20879c5d5ebfb3040553a53b95e`
- Size: **30,742,885 bytes**

The old repo-root research archive `data.7z` was deleted at `91d55bb1968efe4d8eb702f7293f5dfc7829e473`. Do not claim it remains in Git.

## Fresh installed-client proof — v1.5.12.7

Durable evidence: `docs/evidence/installed-client-v1.5.12.7-2026-08-13.md`.

Fresh run facts:

- Overall Miner validation PASS.
- Weapons: **120**.
- Armor: **23 sets / 133 set pieces / 40 Key Armor / 173 total pieces**.
- Armor Gear Tier rows: **865 = 173 × 5**. Any older handoff saying 850 is wrong arithmetic.
- All prior 15 missing Armor stat rows recovered; **0 unresolved stat-row gaps**.
- Attachments: **119**, with **110 direct localized compatibility statements / 9 unresolved blank-description records**.
- Mods: **1,618** source families.
- Deviations: **98 display-name families / 160 source variants**.
- Cradles: **120 display-name families / 170 source variants**.

Do not request another v1.5.12.7 run. The next useful external proof is one fresh run on **v1.5.12.8 or newer**.

## Weapons — gold-standard vertical

- 120 weapons = 95 ranged + 25 melee.
- 600 Gear Tier rows, 545 Blueprint-Star rows, 530 current recipes.
- Catalogue, detail UX, compare, legal Gear Tier × Blueprint Stars, acquisition/crafting evidence, provenance, unresolved-effect handling, and Build Planner handoff are implemented.
- Compare applies only proven static Tier/Star inputs; it does not claim configured DPS.
- Short descriptions remain withheld because fresh data reproduces the Kukri/frozen-tilapia localization cross-wire. Correct repair direction is translation provenance/collision diagnostics, never a one-off override.
- 14 melee weapons lack Tier I–V recipe evidence and remain **recipe evidence unresolved**, never “non-craftable.”
- 14 non-Common weapons reference exact `WS...` IDs with no exact passive-skill backing. Do not alias similar IDs.
- Minor clarity cleanup remains: catalogue card `Base Attack` is actually default Tier V · 1★. Detail already labels it correctly.

## Armor & Sets — invariant proven, route still `SOON`

Canonical Armor identity is variant-aware:

- Set piece: `ds-a-{suit_id}-{blueprint_id}`.
- Key Armor: `ds-ka-{blueprint_id}`.

Fresh real-client proof validates the recovery end-to-end:

- 173 pieces.
- Exactly five unique Gear Tiers I–V for every piece.
- **865 Tier rows**.
- All 15 previously dropped stat rows recovered.
- Zero unresolved stat-row gaps.

Two Blackstone crafting-output conflicts remain deliberately separate from stat identity:

- Blackstone Boots - Cold T3: exact stat item `24003303`, suit `1033`; recipe output `24003103`, suit `1031`.
- Blackstone Gloves - Heat T3: exact stat item `25003203`, suit `1032`; recipe output `25003103`, suit `1031`.

Never rewrite those recipe outputs as variant-specific crafting proof.

The set-centric Armor route/materializer are prepared and fail closed, but `database/armor/armor-data.js` remains a null placeholder. Keep Armor `SOON` until a final transactional snapshot is materialized. The contract already contains per-Tier HP, Pollution Resist, Psi Intensity, resolved stat provenance, and current recipe/material evidence; exposing more of that in route UX remains useful follow-up work.

## Current Calibrations — float defect fixed in v1.5.12.8

Proven current system:

- 188 normalized rows = 94 current + 94 legacy.
- 94 shared `buff_id` identities.
- Rare 24 / Epic 35 / Legendary 35.
- Main Weapon DMG `D0102`: Rare 18–25%, Epic 26–33%, Legendary 34–50%.
- Exactly one secondary from four observed candidates, each with mined source weight 200. Do not turn those weights into probability percentages without separate proof.

Secondary ranges:

- Rare: Weakspot 12–18, Crit Rate 8–12, Elemental 12–18, Crit DMG 20–30.
- Epic: Weakspot 15–21, Crit Rate 10–14, Elemental 12–18, Crit DMG 25–35.
- Legendary: Weakspot 18–24, Crit Rate 12–16, Elemental 15–20, Crit DMG 30–40.

Fresh v1.5.12.7 exposed an exact-equality float bug: Epic Crit Rate max `0.14 × 100` becomes `14.000000000000002`, so all 35 Epic families were wrongly rejected and the compact projector produced 59/94.

`2a48e197...` replaces brittle exact numeric equality with tolerance-safe comparison while retaining stat-ID, weight, rarity-range, and shared-buff identity checks. Replay against the actual user ZIP yields exactly **94/94**, Rare 24 / Epic 35 / Legendary 35, 0 ambiguous, 0 secondary failures. Miner CI `31756412509` SUCCESS including Windows package/self-test.

An explicit new Epic `0.14` regression-file write was connector-blocked; do not claim that specific test landed.

Build Lab stale status gate is now fixed:

- `4b2a614d2760a8248268c6da58e13fa3cff1915e` — canonical bridge accepts current projector status `current-system-selected-from-shared-buff-identity-and-proven-main-plus-secondary-rolls`.

A final v1.5.12.8 snapshot is still needed before transactional materialization.

## Attachments — schema v2 provenance contract

Exactly 119 player weapon attachments: Sight 30 / Muzzle 36 / Tactical 36 / Magazine 17.

Fresh proof:

- 110 / 119 have direct localized installed-game compatibility wording.
- 9 / 119 are unresolved because their description is blank.
- coded `compatible_weapon_types` arrays remain empty in this snapshot.

Preserve exact localized wording, including model-specific rules. Never convert English text into guessed weapon IDs or broad class codes.

Attachment schema v2 publisher, materializer, route renderer, audit, and Build Lab guard are landed/tested.

## Mod 2.0 — direct frame-library join newly proven

Previously proven progression has exactly Levels 1–17 and every row satisfies:

`frame_lv_1 + frame_lv_2 + frame_lv_3 + frame_lv_4 = mod_level`

New fresh-tracer evidence this shift:

- Normalized Mods carry `frame_code` from `new_mod_property_data.frame`.
- Installed-game table `game_common/data/new_mod_frame_lib_data.json` is keyed by frame code.
- Every frame record preserves an ordered `sub_entry_item_no` list.
- Fresh corpus: 1,618 Mod records; **32 frame codes used**; tracer exposes **37 frame-library records**; zero used frame codes missing; every used frame has exactly four sub-entry IDs.

Machine audit:

- `87bba600449f3d5096725189d4bd46acee96626c` — `tools/site/audit-mod-frame-library.py`.
- Site CI `31756941230` SUCCESS.

Do **not** claim list index 0..3 maps to `frame_lv_1..4`. Recovered PYC evidence identifies runtime functions `get_mod_sub_entry_desc` and `get_mod_sub_entry_data` in `ui/data_tools/ItemDataTools.pyc`, but the actual PYC exists only in the user's local Miner snapshot path and is not in the uploaded ZIP. That is the exact remaining positional-semantics boundary.

Build Lab currently has no canonical Mod config. Do not add a name-based shortcut.

## Deviations / Cradles — source identity hardened

Display name is browse grouping only, not canonical source identity.

Research:

- Deviations: 60 multi-variant display-name families; 45 differ semantically, 15 remain distinct source-ID aliases/candidates.
- Cradles: 32 multi-variant families; 30 differ semantically, and the remaining two differ in visual/equipped-image state.

Landed:

- `552190b38cec60697d7d42600c0751580620213d` — Deviation variants get `ds-dev-{source_id}`, Cradle variants get `ds-cradle-{source_id}`; display-name family remains grouping. Miner CI `31753442792` SUCCESS.
- `487221ac8a0d37b0b1015a6a15499a2d075af4a6` — transactional materializer validates source-variant IDs/counts. Site CI `31753515193` SUCCESS.
- `c727af989ed8181a7ee790475b93b71b0ff157b1` — player database browser requires exact publication status/source-variant identities before rendering and displays canonical source identity on preserved variants.

Build Lab `canonical-category-variant-guard.js` intentionally nulls a Deviation/Cradle category if any family has anything other than exactly one variant. Load order is canonical data → guard → bridge → legacy app, so ambiguous current families cannot silently reach `variants[0]`. Keep this fail-closed behavior.

v1.5.12.8 includes the source-variant publisher. A fresh v1.5.12.8 client run is still needed to prove those IDs in actual output.

## Build Lab migration state

Canonical bridge currently handles Calibrations, Attachments, Deviations, and Cradles by validating/matching into legacy `window.DS_COMMUNITY` pools.

Remaining boundaries:

1. Armor has no canonical bridge config. Mapping must use exact suit + blueprint identity; never name-only matching.
2. Mod 2.0 has no canonical bridge config and remains gated on frame consumer semantics.
3. Deviations/Cradles remain intentionally blocked while display-name families contain multiple source variants; do not auto-pick variant 1.
4. `preview/build-lab/data/community-data.js` and `preview/build-lab/app.js` are not stored in Git; they are hosting-installed compatibility files. Without that runtime pool shape, do not pretend Armor/Mod canonical mapping can be completed safely in-repo.

## Global workstation shell / readiness

- `3899e37b1109795728947864cb56c79f60af038d` updates global shell footer to **Miner 1.5.12.8**.
- Database nav still intentionally marks Armor, Mods, Calibrations, Deviations, and Cradles as `future`/SOON. Keep those statuses until route payloads are transactionally materialized and genuinely player-ready.

## Exact next sequence

1. Confirm site CI for `c727af...`, `4b2a614d...`, and `3899e37b...`; fix failures.
2. User should run **Miner v1.5.12.8 once** and provide the fresh output. This is the next useful external proof run.
3. Verify final output: Calibration 94/94 with zero failures; Armor 173/865; Attachments 110/9; Deviation/Cradle variants carry canonical source IDs.
4. Run transactional all-seven materialization from that snapshot; promote only passing categories.
5. Finish Armor route UX and Build Lab integration once exact legacy/runtime mapping is accessible.
6. Continue Mod frame consumer investigation; direct frame-library join is proven, positional frame-level semantics are not.
7. Resolve Deviation/Cradle player-selectable variant semantics only from evidence.
8. Finish canonical Build Lab migration away from stale compatibility pools.
9. Minor Weapons catalogue clarity cleanup remains: `Base Attack` → `Tier V · 1★ Base Attack`.
10. Only after core functionality is broadly complete, perform fresh Wikily/OnceHumanDB UX/features audit and implement safe evidence-backed improvements; never copy their corpus counts.
