# Dead Signal Ultimate Planner v1.2.2

## Loadout Report: equipped item stats

This release restores the intended distinction between planner data and deferred combat math.

### What the Loadout Report now shows
- Every known indexed weapon stat for each equipped weapon: DMG, RPM, magazine, reload, Crit Rate, Crit DMG, Weakspot DMG, range, effective range, mobility, and pellets where available.
- Equipped ammo modifiers when known.
- Equipped weapon-mod effect text plus Mod 2.0 instance level / Shiny state.
- Current calibration blueprint style and the exact RNG Attack / bonus-attribute rolls stored in the build.
- Equipped attachment effects.
- Armor HP and pollution-resistance values where indexed.
- Equipped armor-mod effect text plus Mod 2.0 instance level / Shiny state.
- Key-armor effects.
- Combat Deviation abilities / description, consumable effects, and selected Cradle effects.

### Math boundary
These values are labeled **Indexed Item Stats**. Dead Signal does not yet calculate Tier/Star scaling, proc chains, final DPS, or other derived combat results from them. Known values are displayed; unknown values remain pending instead of being invented.

### Deployment
cPanel deploys the verified v1.2 bundle, applies the v1.2.1 layout/cache patch, then applies the v1.2.2 Loadout Report patch.
