# Dead Signal v1.2.7

## Player-facing provenance cleanup

- Removed per-item `Source:` pills from weapons, armor, calibrations, mods, system cards, pickers, and grouped mod variants.
- Removed per-item data-quality/status badges such as `COMMUNITY SNAPSHOT`, `CURRENT VERIFIED`, `OFFICIAL CURRENT`, `BASIC RECORD`, and `DETAILS PENDING` from the player-facing planner UI.
- Kept source, coverage, conflict, and verification metadata in the dataset for Dead Signal QA and future curation work.
- Added one plain-text site footer listing the project reference resources: Once Human Official, OnceHumanDB, and Wikily.
- Footer contains no outbound links and states that Dead Signal is an independent community planner and is not affiliated with or endorsed by the listed services.
- Updated the catalog-strip copy so it no longer claims per-item provenance is displayed.
- Preserved rarity styling and the restored picker selection functions from v1.2.6.

## Validation

- `app.js` syntax check passed.
- `community-data.js` syntax check passed.
- Production ZIP integrity passed.
- No player-facing `Source:` labels or data-quality badge render calls remain.
- `applyPick()` and `initCalibration()` remain present.
