# Dead Signal Miner v1.5.14.70

Released 2026-08-22.

## Fixes

- Prevented the packaged Windows application from hanging before the UI appeared.
- Deferred the Evidence Graph’s expensive startup work until after the stable shell is visible.
- Removed the automatic default weapon trace during startup.
- Avoided constructing the Phase 13 generalized shell during packaged startup.

## Evidence Graph

- Added armor and armor-set tracing to the stable Evidence Graph screen.
- Armor pieces, sets, Key Armor, claims, and exact provenance edges now route through the existing generalized evidence adapters.
- Unsupported entity types remain fail-closed instead of being rendered as weapons.

## Verification

- Packaged startup verified with a responsive window at approximately 69 MB RAM.
- Armor adapter, armor provenance, and packaged-startup tests pass.

## Release artifact

- Windows package: `Dead-Signal-Miner-v1.5.14.70-Windows.zip`
- SHA-256: `f082bc56b6fce9af0e17ad8944f85e3fac618930eddcb4be1bc2c1a29d82f5d8`
