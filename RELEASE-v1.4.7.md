# Dead Signal Build Lab v1.4.7

## Calibration rarity resolution fix

Calibration Blueprint names repeat across Rare, Epic, and Legendary variants. The previous relocation bridge matched a selected calibration by name only, so duplicate-name records could resolve to the wrong rarity (commonly Epic).

### Fix

- Selected Calibration Blueprints are now resolved using the exact variant when possible: item/data ID first, then explicit rarity metadata/classes/text within the native calibration control.
- The relocated Calibration Blueprint control now carries `data-calibration-name` and `data-calibration-rarity` explicitly.
- Weapon DMG RNG and Secondary RNG UI read that explicit selected rarity instead of scraping surrounding card text.
- The weapon RNG model no longer silently falls back to a stale saved Epic value when a selected calibration's rarity cannot be proven.
- If rarity cannot be proven, the UI reports it as unavailable instead of inventing a rarity.

### Deployment

Use the established workflow only:

1. cPanel Git Version Control -> Update from Remote
2. Deploy HEAD Commit
3. Hard refresh (`Ctrl+F5`)

`.cpanel.yml` remains copy-only.
