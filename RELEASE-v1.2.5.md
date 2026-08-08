# Dead Signal Ultimate Planner v1.2.5

## Rarity visual system

Rarity is now a first-class UI property throughout the planner.

Canonical color treatment used by Dead Signal:
- Normal / White -> white
- Common / Green -> green
- Rare / Blue -> blue
- Epic / Purple -> purple
- Legendary / Gold -> gold
- Mythic / Red -> red when applicable

Community records that currently use `Uncommon` are displayed with the green rarity family until their exact canonical rarity labels are reconciled. Non-rarity metadata values such as `Current` and `Community` remain neutral and are not assigned fake rarity colors.

Rarity identity is rendered in:
- weapon cards
- armor cards
- picker results
- mods and mod variants
- calibration blueprints
- ammunition and attachments
- deviations and consumables when a true game rarity is present
- armor set activation
- Loadout Report weapons, armor, mods, parts, deviations and consumables

The visual treatment includes a rarity badge, item-name color, card edge accent and subtle rarity background glow.

## Validation
- JavaScript syntax check passed.
- Community data syntax check passed.
- v1.2.4 -> v1.2.5 patch replay passed locally.
- Data Audit remains removed from the user-facing Loadout Report.
- Rarity values that are unknown or not true game rarity values remain neutral rather than guessed.
