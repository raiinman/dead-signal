# Dead Signal — Operability Audit

Last checked: 2026-08-11 00:47 MST

This file records player-facing operational blockers that should be resolved before Dead Signal is called broadly complete. It is intentionally separate from advanced combat/stat math.

## Current status

- Canonical branch: `main`
- Current player release: **PLAYER v1.5.2**
- Copy-only cPanel deployment remains required.
- Calibration Style localization is complete for 94/94 current Calibration Blueprints.
- Live-browser screenshot confirmation now shows the Calibration picker with exactly one contained `FIXED STYLE EFFECT` block per rarity card. The prior duplicate footer copy is resolved.
- The authoritative production `app.js` source has now been supplied and reviewed, so native persistence behavior is no longer inferred from UI symptoms.

## Planner persistence — bridge implemented, live round-trip still pending

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

That creates a real integrity risk because the displayed build can diverge from the state that the core app serializes.

### PLAYER v1.5.2 mitigation

Prepared static file:

`preview/build-lab/planner-state-bridge.js`

The bridge is based on the recovered core source and known payload/DOM contracts; it is not guessing at unknown serialization behavior.

It currently:

1. synchronizes visible My Gear Calibration Weapon DMG and secondary controls back through the core app's native `data-cal-*` inputs before Save / Export / Share;
2. preserves blank My Gear roll fields as `null` instead of allowing the older midpoint initialization to masquerade as an owned roll;
3. stores Build Mode as a backward-compatible namespaced extension: `state.dsExtension.buildMode`;
4. restores Build Mode from browser saves, imported builds, and share-link payloads when the extension exists;
5. synchronizes native loaded Calibration values back into the newer player-facing controls after Load / Clone / Import / Share.

The core `app.js` should still be vendored into the repository when practical. The v1.5.2 bridge is a compatibility layer that lets the current externally loaded core and the newer presentation stack behave like one planner without changing cPanel architecture.

## Required live round-trip verification

Before persistence can be called closed, verify:

1. My Gear exact Weapon DMG + one secondary roll → Save → Load.
2. God Roll mode → Save → Load restores God Roll visibly.
3. Export → Import preserves build mode and exact My Gear calibration rolls.
4. Copy Share Link → open link preserves mode and exact My Gear calibration rolls.
5. Two saved builds using the same weapon/calibration but different rolls remain independent.

## Advanced stat math

Held unless mined files already prove a complete stat-family consumer/order. Do not invent formulas merely to make the UI look finished.

## Next operational priorities

1. Live-verify the PLAYER v1.5.2 persistence round trips above.
2. Audit picker and selected-card workflows across weapons, armor, mods, attachments, Deviations, Cradles, ammo, and consumables.
3. Reconcile the older 108 planner attachments with the 119 mined true weapon-slot accessories when the mined attachment export is available in a form that can be safely integrated.
4. Vendor the recovered core `app.js` into source control when the full file can be landed safely, eliminating the remaining externally loaded core dependency.
5. Only after broad operational completeness, run the live Wikily + OnceHumanDB competitor audit and close material usability/data gaps.
