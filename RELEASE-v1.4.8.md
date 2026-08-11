# Dead Signal Build Lab v1.4.8

## Calibration picker cards now show the mined stats

This release fixes two legacy presentation problems in the Calibration Blueprint picker.

### Removed legacy label

`Current Calibration` was old source/category metadata from the community-data layer. It was not useful player-facing information and is now hidden on Calibration Blueprint picker cards.

### Calibration stats are now the primary card description

Calibration picker cards now expand to show the current mined rarity-specific RNG information:

- guaranteed Weapon DMG roll range
- all four possible secondary stats
- the legal RNG range for each secondary

Current rules:

- Rare: Weapon DMG 18-25%; Weakspot DMG 12-18%; Crit Rate 8-12%; Elemental DMG 12-18%; Crit DMG 20-30%
- Epic: Weapon DMG 26-33%; Weakspot DMG 15-21%; Crit Rate 10-14%; Elemental DMG 12-18%; Crit DMG 25-35%
- Legendary: Weapon DMG 34-50%; Weakspot DMG 18-24%; Crit Rate 12-16%; Elemental DMG 15-20%; Crit DMG 30-40%

The existing compatibility/applicability paragraph remains underneath as supporting information rather than serving as the only description.

### Rarity source

The picker enhancement now reads the rarity directly from the picker card's own rarity metadata/badge first, then falls back to card text only if necessary. This is independent from the selected-weapon calibration bridge.

### Layout

Calibration Blueprint cards opt out of the old compact/clipped picker-card height so the stat summary is actually visible.

### Still pending

Exact fixed Calibration Style wording/effects remain a separate buff/localization bridge. This release does not invent those descriptions.

### Deployment

1. cPanel Git Version Control -> Update from Remote
2. Deploy HEAD Commit
3. Hard refresh (`Ctrl+F5`)

`.cpanel.yml` remains copy-only.
