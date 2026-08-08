# Dead Signal Ultimate Planner v1.2.6

## Picker selection regression fix

v1.2.5 introduced the rarity visual system but accidentally removed two functions while replacing the mod-group render block:

- `applyPick()` — commits picker selections to the active loadout
- `initCalibration()` — initializes calibration state after selecting a calibration blueprint

### Symptoms

Picker cards still opened and responded to clicks, but selecting a weapon or other item did not equip it because the global `[data-select]` click handler called a missing `applyPick()` function.

### Fix

- Restored `applyPick()` with weapon, armor set, armor, armor mod, deviation, consumable, attachment, weapon mod, ammo, and calibration handling.
- Restored `initCalibration()`.
- Kept the v1.2.5 rarity visual system intact.
- Updated planner/dataset version to v1.2.6.

### Regression checks

- `app.js` syntax: PASS
- `community-data.js` syntax: PASS
- `[data-select]` click handler still calls `applyPick()`: PASS
- `applyPick()` exists: PASS
- `initCalibration()` exists: PASS
- Function inventory compared with v1.2.4: no functions missing

Production backup SHA-256: `4d318dcf2a1b3948f574b3c9582d308e7fb90baa0101c50e9ed4f5870cc76e27`
