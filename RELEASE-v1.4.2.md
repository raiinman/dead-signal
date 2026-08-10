# Dead Signal Build Lab v1.4.2

## Weapon crafting hierarchy

Calibration Blueprint is now treated as part of the weapon crafting core rather than a downstream accessory-style field.

Weapon-card order is now:

1. Gear Tier
2. Blueprint Stars
3. Calibration Blueprint
4. Calibration RNG controls (My Gear) / automatic legal maximum (God Roll)
5. Mined weapon-core calculations and static stats
6. Existing Ammo / Weapon Mod / accessory controls continue below

### Calibration picker behavior

The new prominent Calibration Blueprint control delegates to the planner's existing native calibration picker. The old native control is hidden only when its container is safely identified, preserving the existing picker/compatibility logic.

### RNG behavior

Once a Calibration Blueprint is selected, its RNG controls sit directly beneath it:

- synchronized slider + exact numeric input in My Gear
- 0.1% step
- Rare: 18.0-25.0%
- Epic: 26.0-33.0%
- Legendary: 34.0-50.0%
- God Roll automatically uses the legal maximum

### Implementation

- `preview/build-lab/weapon-layout.js`
- `preview/build-lab/weapon-layout.css`
- `preview/build-lab/weapon-model-ui.js`
- `preview/build-lab/weapon-model.css`

The layout enhancement is intentionally separate from the legacy hosted planner core and remains compatible with copy-only cPanel deployment.
