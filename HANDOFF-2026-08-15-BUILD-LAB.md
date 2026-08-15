# Dead Signal — Build Lab / Weapon Selector Handoff

> **Date:** 2026-08-15
> **Repository:** `raiinman/dead-signal`
> **Branch:** `main`
>
> Read `AI-CONTINUITY.md` and `PROJECT-RULES.md` completely first. This file is the current-session delta and should be read immediately after them.

## Current user direction

The user decided the previous planner direction was becoming too cramped and overworked. They referenced `resurgencebuilds.com/builder/` as a useful UX example and said Wikily covers the basic player-facing information we need, while Dead Signal can go beyond it because our mined dataset is richer.

Important doctrine remains unchanged:

- Dead Signal's installed-game / Miner data is the source of truth for numbers and mechanics.
- Wikily, OnceHumanDB, Resurgence Builds, screenshots, videos, and other community sources are **UX / information-architecture / search clues only** unless exact installed-game evidence independently proves a data claim.
- Do not reconcile Dead Signal's mined math to screenshot-derived community values.
- Some weapons legitimately have **no special skill**. `no-fixed-skill-reference` is not automatically an error or missing mechanic.
- Weapon description and special-skill/mechanic are separate concepts.

## Planner redesign decision

Two new visual directions were created during the session: one for the Build Lab planner and one for the Weapon Selector. The user explicitly approved those directions with: **“Yeah those two renders line up better with my idea. please code them.”**

The implementation direction is therefore approved; do not revert to the older dense/legacy picker layout without user approval.

### Weapon Selector approved structure

The weapon selector is now intended to behave as a modern full-featured selection workspace rather than the old compact list:

- prominent `SELECT / Weapon` header
- search by weapon name, skill, or description
- top filters instead of the old redundant left column
- filters for category/type, rarity, acquisition, and mechanic evidence
- pagination with **10 weapons per page**
- large rich weapon cards
- weapon image/art on the left for desktop cards
- name, rarity, category, Tier I · 1★ identity
- separate **WEAPON DESCRIPTION** section
- separate **SPECIAL SKILL** section with evidence state
- DMG / Fire Rate / Range summary
- Acquisition evidence summary
- mechanic/evidence status
- favorites support

The user explicitly asked to remove the old left filter column because it duplicated the top controls.

## Data / card semantics

### Weapon description

Cards need a dedicated weapon-description area. Do not substitute suspect translation handles just to fill it.

If no verified player-facing description is publishable, show a compact withheld/not-verified state rather than inventing text. The current selector adapter has `weaponDescription()` fail-closed logic.

### Special skill

Special skill is separate from weapon description.

Current internal evidence states include:

- `resolved-player-facing-effect`
- `exact-fixed-skill-record-missing`
- `exact-fixed-skill-record-present-effect-text-unresolved`
- `no-fixed-skill-reference`

Do **not** render every `no-fixed-skill-reference` weapon as unresolved. Some weapons genuinely have no special skill. Future exact evidence work should distinguish a valid standard/no-special-skill state from true unresolved mechanic evidence.

### AA12 example

The AA12 card was used repeatedly as the visible example.

- AA12 is currently showing mined Tier I · 1★ values such as `38×5`, Fire Rate `180`, Range `40` in the selector.
- Its special-skill path currently has no resolved player-facing fixed-skill text.
- Do not use OnceHumanDB screenshot-derived AA12 stats to alter Dead Signal's numbers.
- External AA12 description text may be used only as a localization/search clue until exact installed-game handle identity is proven.

## Pagination requirement

The user explicitly requested:

> “lets load only 10 weapons at a time so lets create pages. ease the load times”

This is a hard UX requirement for the current selector.

The selector uses `PAGE_SIZE = 10` in `database/weapons/weapon-public-adapter.js`.

Pagination must control the same DOM records the picker renders. Do not allow old picker CSS to override `[hidden]` page state.

## Mobile requirements / bugs found

The user tested the live mobile site and reported two concrete failures:

1. the Weapon Selector did not scroll correctly on mobile;
2. it did not behave as 10-per-page on mobile, and images did not load/fit correctly.

A mobile-oriented fix was attempted so the whole modal becomes the scroll surface rather than using nested scrolling. This avoids the mobile browser scroll trap.

Current desired mobile behavior:

- one card per row
- whole modal scrolls naturally
- exactly 10 paginated records are present for the current page
- hidden off-page cards stay `display:none`
- weapon art uses a shallower mobile art panel and `object-fit: contain`
- footer/pagination remains reachable by scrolling

## Latest desktop production bug

The user then showed the live desktop site still visibly broken.

Screenshot symptom:

- only roughly two rows of rich weapon cards are visible at the top;
- a very large empty black cavity fills the rest of the modal before the footer;
- the inner scrollbar stops well above the footer.

This proved the prior fixes were not actually solving the results viewport geometry.

Important diagnosis:

- this is not simply “missing cards”;
- the results list / arsenal body is not consuming the available modal height correctly;
- the base picker rebuilds all weapon buttons from scratch on search/type changes, then `weapon-public-adapter.js` upgrades those nodes into rich cards;
- late-loaded CSS can therefore override or collapse the selector geometry after the adapter renders it.

## Latest commit

Current latest selector fix:

- **Commit:** `3be221f325d6d298c233ff6be93c1442eea981a9`
- **Message:** `Fix weapon selector viewport geometry across desktop and mobile`
- **File changed:** `shared/readability.js`

This commit adds a late viewport/geometry guard scoped to `/build-planner/` and `#picker.arsenal-mode`.

It currently forces:

- modal as a true flex column on desktop/tablet
- header/tools/footer as non-growing regions
- `.arsenal-body` to flex-grow into the remaining modal height
- `.arsenal-center` to fill that height
- `.bl-picker-list` to `height:100%`, `max-height:none`, and scroll vertically
- two-column rich-card grid on desktop
- approximately 320px card/art height on desktop
- one-column layout below ~1050px
- whole-modal scroll behavior below 680px
- `[hidden]` picker records to `display:none!important`
- compact unverified-description treatment
- larger readable description / skill text line clamps

No GitHub workflow run was attached to the commit at the time of handoff, so do **not** claim CI passed for it without checking.

## Why the shared guard exists

`database/weapons/weapon-public-adapter.js` owns selector rendering/data semantics, but the live site has repeatedly shown CSS/order conflicts between:

- `preview/build-lab/build-lab.css`
- `shared/readability.css`
- dynamic styles injected by `weapon-public-adapter.js`
- late mobile/readability guards

The latest approach deliberately uses a narrowly scoped late-loaded guard in `shared/readability.js` because that asset is guaranteed to load after page CSS and can prevent the old page CSS from collapsing the results surface.

Do not broadly redesign `shared/readability.js`; this must remain scoped specifically to Build Lab selector geometry.

## Base picker behavior discovered

`preview/build-lab/index.html` still contains the legacy generic picker implementation.

Key behavior:

- `openPicker()` sets context and calls `renderPicker()`.
- `renderPicker()` rebuilds the entire `#pickerList` with generic `.bl-pick` buttons.
- It can create up to 400 base records.
- `weapon-public-adapter.js` then intercepts/enhances Weapon mode into the rich selector.

This matters because page/filter logic and the adapter must not maintain conflicting assumptions about which records exist in the DOM.

## Cache/version concern

The live Build Lab HTML currently references assets using versioned URLs such as:

- `build-lab.css?v=2.0.0`
- `/database/weapons/weapons-data.js?v=20260814b`
- `/database/weapons/weapon-public-adapter.js?v=20260814b`

If the live site still displays the **exact old geometry** after commit `3be221f...` has deployed, do not immediately rewrite the selector again.

First verify which asset body the production browser is actually receiving. There is a real possibility that an old versioned URL / CDN/browser cache is serving stale JS or CSS.

If stale delivery is proven, cache-bust the relevant asset references deliberately rather than stacking another CSS patch on code the browser is not receiving.

Do not touch SSL, DNS, redirects, domain, cPanel hosting configuration, or the accepted deployment architecture while diagnosing this.

## Recent user feedback to preserve

The user became frustrated when visual changes were made that they had not approved. Their exact feedback included:

> “You made a lot of unapproved changes”

Therefore:

- make narrow fixes to the approved render direction;
- do not independently change visual information architecture unless necessary for a concrete bug;
- when debugging layout, preserve the approved rich-card visual structure instead of replacing it with a different card type or compressed fallback.

The user also repeatedly said the cards were cramped. The approved selector direction therefore favors readable vertical space rather than extreme information density.

## Immediate next sequence for the new chat

1. Read `AI-CONTINUITY.md`, `PROJECT-RULES.md`, then this handoff.
2. Confirm canonical `main` includes `3be221f325d6d298c233ff6be93c1442eea981a9`.
3. Check CI/status for the latest commit if available.
4. Verify whether the production Build Lab is actually serving the updated `shared/readability.js` / selector code before making another visual patch.
5. If production is current, inspect the computed geometry of `#picker.arsenal-mode`, `.arsenal-body`, `.arsenal-center`, and `.bl-picker-list` and fix the **single actual owner** of the remaining bad dimension.
6. If production is stale, update the relevant cache-version reference rather than stacking more CSS overrides.
7. Retest desktop Weapon Selector with 10 results/page and verify the results viewport reaches the footer without a dead black cavity.
8. Retest mobile: scroll to the footer, confirm exactly 10 records for the page, and verify weapon art loading/fit.
9. Do not resume Magazine investigation right now; it is parked.
10. Once selector behavior is stable, continue the broader approved Build Lab redesign without unapproved structural changes.

## Files most relevant to resume

- `database/weapons/weapon-public-adapter.js`
- `shared/readability.js`
- `shared/readability.css`
- `preview/build-lab/index.html`
- `preview/build-lab/build-lab.css`
- `tools/site/tests/test-weapon-public-adapter.js`

## Project boundaries still in force

- Work directly on canonical `main` unless user says otherwise.
- Never execute game bytecode.
- Never publish local Miner snapshots, `reference-tracer.sqlite`, research notes, or raw evidence bundles.
- Do not touch the pre-existing local untracked `tools/miner.zip`.
- Do not route work to Perplexity unless user explicitly reverses the decision.
- Copy-only cPanel architecture stays intact.
- Do not touch SSL/DNS/redirect/domain/cPanel hosting configuration.
- Preserve the accepted landing page and Official Once Human X feed.
- External sites remain UX/reference/search clues; mined client data remains authoritative for Dead Signal's numbers and mechanics.
