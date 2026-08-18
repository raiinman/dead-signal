# Dead Signal — Weapon Launch Warnings and Attachment Compatibility

Date: 2026-08-18

This handoff continues the completed Weapon Identity Spine work on canonical `main`. It records the exact boundaries proven from the retained `.62` Base/Current tables. No external catalog count or fixed weapon total was introduced.

## Completed sequence

1. **Ten melee recipe owners**
   - All ten formerly owner-unresolved melee weapons have exact records in `game_common/data/blueprint_recipe_season_data.json`.
   - Each record owns five `corr_forge_lv` → `corr_forge_no` selections under season key `0`.
   - The referenced forge material bodies are not present in the retained `forge_data` layer, so publication now distinguishes `exact seasonal owner / material body unresolved` from `recipe owner unresolved`.
   - A bounded exact-only investigator is retained at `tools/miner/src/extractor/investigate_melee_recipe_owners.py`.

2. **Morgan progression owner**
   - Morgan item `10219901`, blueprint `13219901`, has exact Blueprint Star owner `(13219901, 1)` in `gun_blueprint_attr_data.json`.
   - That row proves a one-level Blueprint Star progression owner; no exact five-tier equipment owner was found.
   - Its state is therefore `exact-blueprint-star-owner-gear-tier-owner-unresolved`, not a generic missing progression owner.

3. **Thirteen nonstandard/special effect-owner gaps**
   - The typed, locality-bounded retained-table trace was rerun after preserving `effect-owner-unresolved` through evidence enrichment.
   - None of the thirteen resolved a weapon-specific effect owner.
   - Twelve expose only shared `wp_dust_1000`, used by 293 gun records; this is shared gun-system evidence, not a weapon mechanic.
   - Stealthblade has related exact records but no mechanic candidate.
   - The trace also now rejects substring collisions such as `ability` inside `stability`, and nonresolving trigger-distance scalars are not counted as mechanic candidates.
   - Do not reopen this branch without new typed installed-game evidence.

4. **Attachment compatibility**
   - Player weapon attachments: 119 (83 non-player/default slot records excluded).
   - Direct installed-game compatibility wording: 110.
   - Explicit generic-category mappings: 89.
   - Explicit `all weapons` mappings: 2.
   - Unresolved descriptions: 9.
   - Named-model phrases remain literal source text and are never guessed into weapon IDs. Only explicit generic terms such as `sniper rifles` are projected to canonical Weapon categories.

## Current `.62` publication boundary

- Weapons: 130 source-derived identities (117 standard, 7 nonstandard, 6 special).
- Effects: 76 resolved, 27 no fixed skill reference, 14 exact fixed-skill records with unresolved player text, 13 unresolved effect owners.
- Recipe warnings: 10 exact seasonal owners whose material bodies remain unresolved; zero generic unresolved recipe owners in the standard lane.
- Progression warnings: one unresolved gear-tier owner (Morgan), with its exact Blueprint Star owner retained.
- Artwork: all 130 weapon identities linked.
- Cradle recomputation: 303 compatible, 737 incompatible, 2,210 unresolved, 8,060 not applicable.
- Web publication remains `PARTIAL` for the precise effect-text/effect-owner, material-body, and Morgan gear-tier warnings above.
- Stable release boundary remains `v1.5.14.62`; no release was cut.
- `tools/miner.zip` remains protected and untouched.

## Verification

Run the full Miner suite from the repository root with the Miner virtual environment. Recompute normalized Weapons, typed evidence, image links, Cradle applicability, extended web contracts, and the main web quality report against the retained Base `cce900774fbac48d` and Current `3b0d5f9596497613` tables.

The next attachment work, if desired, should trace the nine unresolved descriptions or prove exact named-model aliases through a typed installed-game owner. Do not infer IDs from English model spelling.
