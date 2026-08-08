# Dead Signal Ultimate Planner v1.2.3

## Fix
- Restores the missing `gatherEffects()` function used by the Loadout Report.
- Fixes a JavaScript `ReferenceError` that aborted `renderSummary()` and left the right-side report blank after loadout changes.
- Equipped weapon Indexed Item Stats from v1.2.2 now render as intended.
- Restores Combined Build Effects collection for selected weapons, mods, armor sets, armor mods, deviations, cradles, attachments, ammo, and consumables.

## Regression test
The complete cPanel chain was replayed from the v1.2 base through patches v1.2.1, v1.2.2, and v1.2.3. A build with SOCR - Outsider equipped rendered the Loadout Report with DMG 156, RPM 515, MAG 30, Reload 2.3s, Crit Rate 6%, Crit DMG 39%, and Weakspot 60%.

Advanced Tier/Star scaling and derived combat math remain intentionally deferred.
