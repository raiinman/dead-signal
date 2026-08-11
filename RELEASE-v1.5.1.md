# Dead Signal PLAYER v1.5.1

## Calibration Style fidelity

This release publishes the exact localized player-facing Calibration Style descriptions recovered by Dead Signal Miner v1.5.7.4.

### What changed

- Added exact Style descriptions for all **94 current Calibration Blueprint records**.
- Calibration rarity cards now show the mined fixed Style effect for that exact rarity.
- The selected weapon card now shows a contained **Fixed Calibration Style Effect** block before RNG controls.
- Derived short Style labels such as `Rapid`, `Precision`, and `Vanguard` remain in use because the current game data bridge resolves descriptions but does not expose canonical localized Style names.
- Picker cards remain clean: no RNG boxes, no four-secondary dump, and no legacy `Current Calibration` label.

### Miner evidence

The v1.5.7.4 run completed validation successfully and exported `data/buffs.json` with **zero** `_dead_signal_circular_reference` markers. The old `reports/serialization-circular-references.json` included in the output archive was stale residue from the earlier v1.5.7.3 run: its event timestamp predates the new v1.5.7.4 validation/output timestamps.

Calibration localization remained stable at:

- Current calibrations: **94**
- Localized Style descriptions: **94 / 94**
- Missing Style descriptions: **0**
- Mechanics resolution: **73 resolved / 21 partial**
- Canonical localized Style names recovered: **0**

### Deployment

Deployment remains copy-only through cPanel. Two prepared static files were added:

- `preview/build-lab/calibration-style-display.js`
- `preview/build-lab/calibration-style-display.css`

No runtime build, transform, archive extraction, Python, or data reconstruction was added to `.cpanel.yml`.
