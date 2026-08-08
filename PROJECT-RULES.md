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
- Blueprint stars may be represented as 1★–6★ where applicable.
- UI labels must say `Gear Tier` and `Blueprint Stars` so Tier V and 6★ cannot be confused.

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

## Planner before calculator
The planner must represent the actual loadout first: weapons, weapon crafting configuration, ammo, mods and variants, calibration blueprint instance and RNG rolls, attachments, six armor slots and mods, set activation, cradles, deviation, consumables, metadata, save/clone/import/export/share, and compatibility rules.

Advanced damage/proc math comes after the planner model is stable.
