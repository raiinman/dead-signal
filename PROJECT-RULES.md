# Dead Signal — Canonical Planner Rules

These rules are project constraints for the community-first Ultimate Planner.

## Product direction
- Build the complete planner/builder before advanced damage math.
- Community data is the working corpus while planner UX/schema are stabilized.
- Mined data integration remains a later phase.
- Do not invent mechanics or numeric relationships that are not verified.

## Provenance / transparency
- Preserve source provenance internally on records.
- Show plain-text attribution to users when useful (for example: `Source: Wikily`, `Source: OnceHumanDB`, `Source: Once Human Official`).
- Absolutely no outbound source links or clickable link-backs in the Dead Signal UI.

## Gear progression terminology
- Gear Tier is I–V only. There is no Gear Tier VI.
- Blueprint enhancement/star rank is a separate system from Gear Tier.
- Blueprint-star caps are rarity-dependent rather than a universal Tier VI: current community references list Green up to 3★, Blue up to 4★, Purple up to 5★, and Gold up to 6★.
- UI labels must say `Gear Tier` and `Blueprint Stars` so Tier V and 6★ cannot be confused.
- The planner must not offer a blueprint-star rank above the selected blueprint item's rarity cap.

## Current weapon calibration blueprint model
Current-game behavior is based on the January 21, 2026 Once Human Version 2.3.1 changes:
- The old weapon Gear Calibration feature was removed.
- Calibration Blueprints are applied when crafting weapons.
- New Calibration Blueprints retain their style attribute.
- New Calibration Blueprints always include one RNG Attack bonus whose range depends on rarity (officially stated up to 50%).
- The previous two random bonus attributes were merged into one RNG bonus attribute.
- The bonus attribute pool includes categories such as Crit Rate, Crit DMG, Elemental DMG, and Weakspot DMG.
- Official example for a new Legendary blueprint: Attack 33%–50% + Elemental DMG 15%–20%.
- Legacy/pre-update items may exist, but the default planner should model the current system; legacy support should be explicitly separated if added later.

## Current mod model
Current-game behavior is based on the January 21, 2026 Mod 2.0 overhaul:
- Regular mods retain their main attribute but now use fixed sub-attributes rather than random sub-attribute combinations.
- Mods have levels 1–17; mod level is derived from the summed sub-attribute levels.
- Lv. 17 is the regular-mod ceiling.
- Shiny Mods are a distinct higher-end version with the same sub-attributes as Lv. 17 but a slightly stronger main attribute.
- Special suffix families such as Crescent, Lunar, and Downstar continue to exist; current seasonal suffix families can also exist.
- Legacy mods may still be usable, but old randomly rolled mod sub-attributes should not be the default model for new builds.

## Planner before calculator
The planner must represent the actual loadout first: weapons, weapon crafting configuration, ammo, current calibration-blueprint instance and RNG rolls, attachments, current Mod 2.0 selections, six armor slots and mods, set activation, cradles, deviation, consumables, metadata, save/clone/import/export/share, and compatibility rules.

Advanced damage/proc math comes after the planner model is stable.
