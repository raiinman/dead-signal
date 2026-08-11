# Dead Signal PLAYER v1.5.2

## Build-state persistence hardening

This release closes the highest-priority planner integrity gap discovered during the operability audit.

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

### v1.5.2 bridge

Added prepared static asset:

- `preview/build-lab/planner-state-bridge.js`

The bridge:

- synchronizes visible Calibration Weapon DMG and secondary controls into the native planner calibration fields before persistence;
- preserves intentionally blank My Gear roll inputs as blank/null instead of allowing the older midpoint defaults to masquerade as owned rolls;
- carries `MY GEAR` / `GOD ROLL` in a namespaced `state.dsExtension.buildMode` field for browser saves, exports, and share links;
- restores Build Mode from saved/imported/shared payloads when present;
- synchronizes loaded native Calibration values back into the newer player-facing controls.

Existing build payloads without `dsExtension` remain backward compatible and default to the current browser Build Mode behavior.

### Deployment

Deployment remains copy-only through cPanel. `.cpanel.yml` only gains one prepared-file copy command for `planner-state-bridge.js`.

No Python, transforms, archive work, external downloads, or runtime corpus generation were added to hosting deployment.

### Still pending live round-trip verification

PLAYER v1.5.2 should be live-tested for:

1. My Gear exact Calibration rolls → Save → Load.
2. God Roll mode → Save → Load.
3. Export → Import.
4. Copy Share Link → open shared build.
5. Two different builds using the same weapon/calibration with different rolls, to verify they no longer collide through sidecar state.

Advanced weapon stat math remains intentionally held unless current mined data proves the complete consumer/order for a stat family.
