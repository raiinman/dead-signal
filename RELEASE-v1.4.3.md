# Dead Signal Build Lab v1.4.3

## Weapon-card cleanup

Removed the unsolicited diagnostic/mined-weapon-core display block from player-facing weapon cards.

The removed UI included:

- Tier base proof box
- Blueprint-star ratio proof box
- Intrinsic Attack proof box
- RPM / Magazine / Range / Accuracy / Stability / Mobility / Reload / Crit / Weakspot diagnostic grid
- Attack + Calibration RNG preview

Those calculations/data remain available for the underlying stat engine work but should not be exposed as a large diagnostic panel in the normal planner UI unless explicitly requested.

### Approved crafting hierarchy

Player-facing weapon cards should follow:

1. Gear Tier
2. Blueprint Stars
3. Calibration Blueprint
4. Calibration RNG slider + exact numeric input when applicable
5. Ammo
6. Weapon Mod
7. Existing weapon accessory controls

Calibration is a weapon-crafting choice and belongs directly under Tier/Stars. The RNG input belongs directly under the selected Calibration Blueprint.
