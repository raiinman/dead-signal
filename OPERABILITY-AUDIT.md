# Dead Signal — Operability Audit

Last checked: 2026-08-11 02:31 MST

This file records player-facing operational blockers that should be resolved before Dead Signal is called broadly complete. It is intentionally separate from advanced combat/stat math.

## Current status

- Canonical branch: `main`
- Current player release: **PLAYER v1.5.2**
- Copy-only cPanel deployment remains required.
- Calibration Style localization is complete for 94/94 current Calibration Blueprints.
- Live-browser screenshot confirmation shows the Calibration picker with exactly one contained `FIXED STYLE EFFECT` block per rarity card. The prior duplicate footer copy is resolved.
- The authoritative production `app.js` source has been supplied and reviewed, so native persistence behavior is no longer inferred from UI symptoms.
- PLAYER v1.5.2 now includes a player-facing Build Data Integrity status and saved-build mode badges so incomplete My Gear Calibration RNG and God Roll saves are not visually ambiguous.

## Planner persistence — bridge hardened, live round-trip still pending

The recovered core source confirms the native planner state already owns:

- selected Calibration Blueprint
- `calibrationAttack`
- `calibrationBonusStat`
- `calibrationBonusValue`
- Save / Load / Clone / Import / Export / Copy Share Link state serialization

The newer presentation layers were keeping visible values in separate sidecars:

- Build mode: `dead-signal-build-mode`
- weapon-model Weapon DMG UI: `dead-signal-weapon-model-v1`
- Calibration secondary UI: `dead-signal-calibration-secondary-v1`

That creates an integrity risk because two builds using the same weapon/calibration can otherwise inherit the same visible sidecar values.

### PLAYER v1.5.2 bridge

Prepared static file:

`preview/build-lab/planner-state-bridge.js`

The bridge now:

1. synchronizes visible My Gear Calibration Weapon DMG and secondary controls back through the core app's native `data-cal-*` inputs before Save / Export / Share;
2. stores Build Mode in a backward-compatible namespaced extension: `state.dsExtension.buildMode`;
3. stores the visible Calibration UI state per weapon slot under `state.dsExtension.calibration`;
4. restores the per-build visible Calibration state after Load / Clone / Import / Share instead of trusting global sidecar values;
5. preserves intentionally blank My Gear roll fields as blank/null across bridge-managed round trips, even though the older core normalization initializes missing calibration ranges to midpoint defaults;
6. falls back to the recovered core calibration values for older builds that do not yet contain the extension.

This per-build extension is important because merely syncing the sidecars into the native core before Save is not enough: the older core `normalizeState()` fills null Calibration rolls with midpoint values during load. The v1.5.2.1 hardening explicitly preserves user-visible blank state and prevents a previous build's sidecar values from leaking into a newly loaded build.

The bridge remains a compatibility layer. The recovered core `app.js` should be vendored and extended directly when the full source is landed in GitHub, which will allow the temporary persistence interception layer to be removed.

## Build Data Integrity UI

Prepared static files:

- `preview/build-lab/planner-integrity-ui.js`
- `preview/build-lab/planner-integrity.css`

This layer is deliberately advisory rather than blocking. It:

- marks saved builds as **MY GEAR** or **GOD ROLL** using the persisted `state.dsExtension.buildMode` value;
- checks selected ranged-weapon Calibration UI in My Gear mode for a missing exact Weapon DMG roll, missing secondary identity, or missing exact secondary roll;
- explicitly states that Dead Signal preserves missing account-specific RNG as blank rather than inventing a number;
- reports **READY TO SAVE / SHARE** when selected Calibration inputs are internally complete;
- reports **THEORYCRAFT MODE** in God Roll mode, where legal maximum Calibration RNG is intentionally assumed.

This closes a user-facing ambiguity that remained after persistence itself was hardened: saved builds can now be distinguished by mode before loading them, and incomplete My Gear Calibration state is visible in the Loadout Report instead of silently looking finished.

## Required live round-trip verification

Before persistence can be called closed, verify:

1. My Gear exact Weapon DMG + one secondary roll → Save → Load.
2. My Gear intentionally blank RNG fields → Save → Load remain blank.
3. God Roll mode → Save → Load restores God Roll visibly and the saved-build list shows the GOD ROLL badge.
4. Export → Import preserves build mode and exact My Gear calibration rolls.
5. Copy Share Link → open link preserves mode and exact My Gear calibration rolls.
6. Two saved builds using the same weapon/calibration but different rolls remain independent.
7. Build Data Integrity status changes from NEEDS PLAYER INPUT to READY after completing the selected Calibration inputs.

## Advanced stat math

Held unless mined files already prove a complete stat-family consumer/order. Do not invent formulas merely to make the UI look finished.

## Next operational priorities

1. Live-verify the PLAYER v1.5.2 persistence and integrity-UI round trips above.
2. Audit picker and selected-card workflows across weapons, armor, mods, attachments, Deviations, Cradles, ammo, and consumables.
3. Reconcile the older 108 planner attachments with the 119 mined true weapon-slot accessories when the mined attachment export is available in a form that can be safely integrated.
4. Vendor and extend the recovered core `app.js`, then remove the temporary persistence interception layer.
5. Only after broad operational completeness, run the live Wikily + OnceHumanDB competitor audit and close material usability/data gaps.
