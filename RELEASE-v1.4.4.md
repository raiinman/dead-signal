# Dead Signal Build Lab v1.4.4

## Calibration RNG data is now visible

This release bridges the already-mined current Calibration Blueprint RNG data into the player-facing Build Lab.

### Picker cards

Current Calibration Blueprint picker cards now show:

- Main **Weapon DMG** RNG range
- The **one random secondary** pool and each legal range
- A transparent note that exact fixed Style wording is still a separate localization/formatter bridge

Current mined rules are universal by rarity across all 94 current Calibration Blueprints:

- Rare: Weapon DMG 18-25%; Weakspot 12-18%; Crit Rate 8-12%; Elemental 12-18%; Crit DMG 20-30%
- Epic: Weapon DMG 26-33%; Weakspot 15-21%; Crit Rate 10-14%; Elemental 12-18%; Crit DMG 25-35%
- Legendary: Weapon DMG 34-50%; Weakspot 18-24%; Crit Rate 12-16%; Elemental 15-20%; Crit DMG 30-40%

All current secondary choices are equal-weight in the mined snapshot (200 / 200 / 200 / 200), so exactly one secondary is rolled on the dropped blueprint.

### Selected weapon / My Gear

After choosing a Calibration Blueprint, the crafting block now supports the second RNG layer:

1. Main Calibration Weapon DMG slider + exact input
2. Secondary Attribute selector
3. Secondary RNG slider + exact input for the selected attribute

The controls use 0.1% increments.

### God Roll

God Roll keeps the chosen secondary attribute but automatically uses that attribute's maximum legal roll. Automatic build-aware secondary selection is not implemented yet and should not be faked.

### Still pending

Fixed calibration Style descriptions/effects are already linked through mined buff data, but exact player-facing wording/formatting still needs its own bridge. Do not treat the generic compatibility description as the Style effect.

### Deployment

Normal established workflow only:

1. cPanel Git Version Control -> Update from Remote
2. Deploy HEAD Commit
3. Hard refresh

`.cpanel.yml` remains copy-only.
