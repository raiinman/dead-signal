# Dead Signal Build Lab v1.4.0

## Visible payoff from the weapon-modeling work

This release starts surfacing the new planner architecture in the production Build Lab without replacing the existing hosted core planner engine.

### New: Build Mode guard

- **MY GEAR — ACTUAL BUILD** is the default.
- **GOD ROLL — THEORETICAL BUILD** is a deliberate alternate mode.
- The mode choice is presented as two large, prominent controls in the Plan section.
- Switching into God Roll requires a confirmation so users do not accidentally theorycraft while believing they are entering owned gear.
- The selected mode remains visible in the top action bar and Loadout Report.
- The browser remembers the selected mode using `dead-signal-build-mode` in localStorage.
- God Roll mode warns again when Save, Export, or Copy Share Link is used.

### Architecture

The feature is isolated in:

- `preview/build-lab/build-mode.css`
- `preview/build-lab/build-mode.js`

The enhancement injects its own UI into the existing Build Lab DOM and exposes:

```js
window.DSBuildMode.get()
window.DSBuildMode.set(mode)
```

It also emits:

```text
dead-signal:build-mode-change
```

for future integration with Calibration RNG fields and the stat engine.

### Important limitation

v1.4.0 persists the mode per browser, but the legacy hosted `app.js` does **not yet serialize the mode into saved/exported/shared build JSON**. That integration should be done when the planner core is brought under the same source-controlled enhancement architecture or when save/share serialization is explicitly extended.

### Deployment

Normal established workflow only:

1. cPanel Git Version Control → **Update from Remote**
2. **Deploy HEAD Commit**
3. Hard refresh the planner

`.cpanel.yml` remains copy-only.
