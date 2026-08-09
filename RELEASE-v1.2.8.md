# Dead Signal Ultimate Planner v1.2.8

Picker readability release.

## Changes

- Reworked generic item picker cards for clearer visual hierarchy.
- Item name and rarity now share a deliberate header row instead of stacking unpredictably.
- Fixed the broad `.pick span` CSS selector that was interfering with nested rarity badges.
- Moved the favorite star into the card corner so it no longer consumes a full vertical column.
- Converted compact weapon/armor facts into separate stat chips.
- Contained long item-effect text to a readable three-line preview.
- Increased picker spacing and dialog width on desktop.
- Improved picker toolbar and filter spacing.
- Preserved the rarity color system from v1.2.5.
- Preserved picker selection behavior restored in v1.2.6.
- Mobile picker collapses cleanly to one column.

## Validation

- `app.js` syntax: PASS
- `community-data.js` syntax: PASS
- v1.2.7 -> v1.2.8 patch replay: exact output match
- Function-set regression check: no functions removed
- `applyPick()` selection handler: present
- Production ZIP integrity: PASS

Production ZIP SHA-256: `8788e6e10566540ba290d1df7d7635dcedd4593c8efd0be6125682d2362579f2`
