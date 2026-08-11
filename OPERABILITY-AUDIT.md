# Dead Signal — Operability Audit

Last checked: 2026-08-11 00:32 MST

This file records player-facing operational blockers that should be resolved before Dead Signal is called broadly complete. It is intentionally separate from advanced combat/stat math.

## Current status

- Canonical branch: `main`
- Current player release: PLAYER v1.5.1
- Copy-only cPanel deployment remains required.
- Calibration Style localization is complete for 94/94 current Calibration Blueprints.
- The latest picker polish (`d01b16c623616db070eb6b225b2bc753a0a493ad`) keeps the mined Style source node hidden and renders one visible inline Style-effect block, preventing the prior duplicate footer copy. This still needs live-browser confirmation after deployment.

## Verified operational blocker: planner sidecar state is not part of the core build payload

Several important planner systems currently persist outside the native build payload:

- Build mode uses localStorage key `dead-signal-build-mode` in `preview/build-lab/build-mode.js`.
- Weapon-model / Calibration Weapon DMG state uses localStorage key `dead-signal-weapon-model-v1` in `preview/build-lab/weapon-model-ui.js`.
- Calibration secondary identity/value uses localStorage key `dead-signal-calibration-secondary-v1` in `preview/build-lab/calibration-details-ui.js`.

The build-mode module itself warns that saved/exported/shared data **may** represent theoretical values, which confirms that mode is not yet embedded in the native build payload.

The native Save / My Builds / Clone / Import / Export / Copy Share Link behavior is supplied by the externally loaded production file:

`https://deadsignaldb.com/build-planner/app.js?v=1.3.4-armor-images`

That core `app.js` source is not currently present in `raiinman/dead-signal`. GitHub code search also returns no repository copy of `app.js`.

### Why this matters

Until the core payload owns these fields, two builds can collide in browser-side sidecar state, and exported/shared builds cannot be guaranteed to preserve:

- My Gear vs God Roll mode
- exact Calibration Weapon DMG roll
- selected Calibration secondary attribute
- exact Calibration secondary roll

This is a player-data integrity issue, not cosmetic polish.

### Safe resolution

Do **not** monkeypatch JSON, Blob downloads, clipboard, or unrelated browser APIs to guess at the core payload format.

The correct next step is to recover or vendor the authoritative Build Lab `app.js` source into the repository, then extend its native build schema/version so these fields are first-class save/import/export/share properties with backward-compatible defaults.

## Advanced stat math

Held unless mined files already prove a complete stat-family consumer/order. Do not invent formulas merely to make the UI look finished.

## Next operational priorities

1. Live-verify the duplicate Calibration Style footer is gone and rarity/favorite spacing is correct after deploying current `main`.
2. Recover the authoritative core `app.js` source so build mode + Calibration RNG can become native payload fields.
3. Audit save/load/clone/import/export/share round trips once the payload is under source control.
4. Audit picker and selected-card workflows across weapons, armor, mods, attachments, Deviations, Cradles, ammo, and consumables.
5. Reconcile the older 108 planner attachments with the 119 mined true weapon-slot accessories when the mined attachment export is available in a form that can be safely integrated.
6. Only after broad operational completeness, run the live Wikily + OnceHumanDB competitor audit and close material usability/data gaps.
