# Dead Signal PLAYER v1.5.2

## Build-state persistence hardening

This release closes the highest-priority planner integrity gaps discovered during the operability audit.

### Confirmed UI fix

The live Calibration picker was rechecked after the v1.5.1 polish pass. The prior duplicate fixed-Style footer is gone: each Calibration rarity card now shows one contained `FIXED STYLE EFFECT` block inside the card body.

### Core source recovered

The authoritative Build Lab `app.js` source was supplied and reviewed. It confirms that the native planner state already owns:

- selected Calibration Blueprint
- exact Calibration Attack / Weapon DMG roll
- selected Calibration secondary attribute
- exact Calibration secondary roll
- Save / Load / Clone / Import / Export / Copy Share Link serialization flow

The newer weapon-model and Calibration UI layers had been persisting their visible RNG controls in separate localStorage sidecars instead of reliably feeding the native planner fields.

### v1.5.2 persistence bridge

Added prepared static asset:

- `preview/build-lab/planner-state-bridge.js`

The bridge:

- synchronizes visible Calibration Weapon DMG and secondary controls into the native planner calibration fields before persistence;
- preserves intentionally blank My Gear roll inputs as blank/null instead of allowing the older midpoint defaults to masquerade as owned rolls;
- carries `MY GEAR` / `GOD ROLL` in a namespaced `state.dsExtension.buildMode` field for browser saves, exports, and share links;
- stores visible Calibration UI state per weapon slot so same-weapon builds can remain independent;
- restores Build Mode and per-slot Calibration UI from saved/imported/shared payloads when present;
- captures Share Link extensions at the synchronous base64-encoding boundary rather than relying on writable Clipboard API methods.

### Cross-build sidecar isolation

The weapon-model and Calibration-secondary modules now expose explicit reset hooks:

- `window.DSWeaponModelUI.reset()`
- `window.DSCalibrationDetailsUI.reset()`

A new prepared static asset, `preview/build-lab/planner-transition-reset.js`, runs before core transition handlers and resets both in-memory sidecars plus their localStorage backing keys before:

- New Build
- Template load
- saved Build Load
- saved Build Clone
- Import
- Share-hash initialization

Incoming builds first return to the safer **MY GEAR** default. A v1.5.2 payload carrying `dsExtension.buildMode` can then restore GOD ROLL. Legacy payloads without mode metadata therefore no longer inherit an unrelated theorycraft mode from the browser session.

### Build Data Integrity UI

PLAYER v1.5.2 also includes the advisory Build Data Integrity layer. It labels saved builds as MY GEAR or GOD ROLL and warns when selected My Gear Calibration Blueprints are missing the exact account-specific Weapon DMG roll, secondary identity, or secondary roll. Missing RNG remains blank instead of being invented.

### Deployment

Deployment remains copy-only through cPanel. `.cpanel.yml` copies the prepared bridge, transition-reset, and integrity assets along with the existing static Build Lab files.

No Python, transforms, archive work, external downloads, or runtime corpus generation were added to hosting deployment.

### Still pending live round-trip verification

PLAYER v1.5.2 should be live-tested for:

1. My Gear exact Calibration rolls → Save → Load.
2. Intentionally blank My Gear rolls → Save → Load remain blank.
3. God Roll mode → Save → Load.
4. Export → Import.
5. Copy Share Link → open shared build.
6. Two different builds using the same weapon/calibration with different rolls remain independent.
7. New Build and Template transitions do not resurrect the prior build's Calibration sidecar values.
8. Legacy payloads without `dsExtension.buildMode` open as MY GEAR.

Advanced weapon stat math remains intentionally held unless current mined data proves the complete consumer/order for a stat family.
