# Dead Signal — Competitor Audit — 2026-08-11

Scope: current public Once Human planner/database experience at Wikily and OnceHumanDB, compared against Dead Signal PLAYER v1.5.2.

## Executive position

Dead Signal is already differentiated on planner fidelity: explicit Gear Tier vs Blueprint Stars, current Calibration Blueprint structure, exact My Gear RNG entry, God Roll mode, compatibility filtering, build integrity status, local save/clone/import/export/share, accessibility text scaling, and a consolidated Loadout Report.

The strongest competitor advantages are no longer basic loadout assembly. They are discovery/community and broader database tooling.

## OnceHumanDB

Current public strengths observed:

- Build Planner supports weapons, armor, mods, deviations, cradle overrides and food/buffs.
- Builds are encoded in the URL for sharing.
- Featured Builds expose curated/meta loadouts with displayed DPS and set combinations.
- Dedicated Weapon Compare exists.
- Site-wide database covers weapons, armor, sets, mods, attachments, items, deviations, memetics, identities, recipes and overrides.
- Public copy claims 2,877 crafting recipes and 126 weapons.

Dead Signal advantage:

- More explicit crafting-state modeling for current Calibration Blueprints.
- My Gear vs God Roll separation.
- Exact player-entered RNG instead of silently presenting one theoretical result as owned gear.
- Richer persistence workflow: browser saves, cloning, JSON import/export, share links.
- Accessibility/readability controls are a first-class planner feature.
- Build Data Integrity warns when account-specific Calibration information is incomplete.

Material gaps:

1. Weapon Compare.
2. Public/featured build discovery.
3. Broader recipe/item/memetic database presentation.
4. Trustworthy derived DPS once stat/combat consumers are fully traced.

## Wikily

Current public strengths observed:

- Large public community-build directory with search/filtering.
- Build pages support copying builds and public authorship.
- Planner surfaces weapons, ammunition, mods, Calibration, armor, Cradles, Deviations and food.
- Community/voting/social discovery is more mature than Dead Signal.

Current weakness observed:

Several indexed public build pages still expose older Calibration-style attribute presentation patterns. Dead Signal should not copy those legacy assumptions; mined current-client evidence remains the source of truth.

Dead Signal advantage:

- Current post-2026 Calibration model is stricter and evidence-backed.
- Explicit exact-roll entry and theoretical maximum mode.
- Stronger local ownership/persistence workflow without requiring an account.
- Build integrity signaling.
- Compatibility filtering and concise tactical workspace.

Material gaps:

1. Community build publishing/discovery/voting.
2. Public profile/authorship layer.
3. Larger guide/map ecosystem outside the planner.

## Changes made from this audit

PLAYER v1.5.2 now adds two low-risk player workflows directly to the Loadout Report:

- **Copy Loadout Text** — produces a compact plain-text build summary suitable for Discord, Reddit, notes, guild chat, or troubleshooting.
- **Copy Farming Checklist** — produces a deduplicated checkbox list of selected gear, mods, systems and Cradles.

These complement URL sharing rather than duplicate competitor behavior. Neither feature changes game math or persistence semantics.

## Recommended next differentiation sequence

1. Finish live persistence round-trip verification.
2. Reconcile 119 mined true weapon-slot accessories into the player-facing attachment corpus.
3. Add a stat-aware Weapon Compare only from proven static stat families.
4. Add a local/public build-library layer after the core build schema is fully source-controlled.
5. Expand database surfaces for recipes/items only from normalized mined exports.
6. Add derived DPS last, after runtime buff/proc ordering is directly evidenced.

Do not chase competitor DPS numbers by inventing formulas. Dead Signal wins by being more trustworthy first, then broader.
