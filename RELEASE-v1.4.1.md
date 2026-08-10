# Dead Signal Build Lab v1.4.1

## Visible mined weapon model

This release turns the weapon progression/miner work into an interactive Build Lab feature.

### Weapon cards now surface mined game data

For supported selected weapons, the weapon card gains a **MINED WEAPON CORE** panel containing:

- Gear Tier I–V Attack values mined per weapon.
- Blueprint Star progression mined per weapon.
- Proven intrinsic Attack calculation:

```text
IntrinsicAttack = int(TierBaseAttack × StarAttackRatio)
```

- Base weapon-card facts where available: RPM, Magazine, Range, Accuracy, Stability, Mobility, Reload, Crit Rate, Crit DMG, and Weakspot DMG.

The data bundle contains the current 120-weapon progression corpus used in the miner investigation.

Example: **SKS - Pathfinder** Tier V / 6★:

```text
547 × 1.25 = 683.75
Intrinsic Attack = 683
```

### Calibration Blueprint RNG control

When a selected weapon card contains a Calibration Blueprint, the new model panel exposes the account-specific Attack RNG roll.

Current mined legal ranges:

- Rare: 18.0%–25.0%
- Epic: 26.0%–33.0%
- Legendary: 34.0%–50.0%

In **MY GEAR** mode:

- A slider and exact numeric input are synchronized.
- Typing a value moves the slider.
- Dragging the slider updates the exact value.
- Step size is 0.1%, matching the mined drop-roll precision.

In **GOD ROLL** mode:

- The legal maximum is applied automatically.

### Attack preview scope

The panel can preview the proven Calibration RNG Attack contribution on top of intrinsic Attack.

It deliberately labels this as an RNG-only preview. It does **not** yet pretend that fixed Calibration style effects, accessory D0101/D0102 Weapon DMG modifiers, or every other static affix source have been fully wired into the live card. Those layers are being integrated through the same mined stat-aggregator model rather than guessed.

### Architecture

New source-controlled files:

- `preview/build-lab/weapon-model.css`
- `preview/build-lab/weapon-model-ui.js`
- `preview/build-lab/wm-data-01.js` through `wm-data-08.js`

The feature is isolated from the legacy hosted `app.js`. Existing planner selection/save behavior remains the core; the weapon-model layer observes selected weapon cards and adds mined calculations without rewriting the picker engine.

### Deployment

Normal established workflow only:

1. cPanel Git Version Control → **Update from Remote**
2. **Deploy HEAD Commit**
3. Hard refresh the planner

`.cpanel.yml` remains copy-only and only copies prepared static files.
