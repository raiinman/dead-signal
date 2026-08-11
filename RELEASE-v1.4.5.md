# Dead Signal Build Lab v1.4.5

## Calibration UX cleanup

This release fixes the calibration sliders and reduces visual overload in the selected-weapon crafting section.

### Slider behavior

The main Weapon DMG and secondary Calibration RNG controls are now true live-bound range inputs.

- Dragging a slider updates the exact numeric input in place.
- Typing a valid exact value moves the existing slider in place.
- The UI no longer rebuilds the calibration DOM on every `input` event.
- Structural re-rendering is reserved for changes such as Calibration Blueprint, rarity, secondary attribute, or Build Mode.

**Project rule:** never replace/re-render a range input while the user is actively dragging it.

### Visual hierarchy

The selected Calibration section is separated into clear stages:

1. **Calibration Blueprint** — the crafting choice.
2. **Weapon DMG Roll** — guaranteed main RNG roll.
3. **Secondary Roll** — one selected secondary attribute and its independent RNG value.

The two RNG cards now use numbered stage markers, separate borders/backgrounds, more spacing, and a larger range thumb/track.

### Picker cards

Calibration picker facts are more compact:

- Weapon DMG range
- Secondary pool and legal ranges

The verbose pending-style bridge note was removed from every picker card to reduce clutter. Fixed Style descriptions remain a separate pending data/UI bridge.

### Deployment

Use the established workflow only:

1. cPanel Git Version Control -> Update from Remote
2. Deploy HEAD Commit
3. Hard refresh (`Ctrl+F5`)

`.cpanel.yml` remains copy-only.
