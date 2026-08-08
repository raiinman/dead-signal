# Dead Signal Ultimate Planner v1.2.0

Planner-completeness release. Advanced damage/proc math remains intentionally out of scope until the loadout model and community catalog are stable.

## Catalog coverage in this release
- 46 / 126 current weapon records indexed
- 123 / 159 armor pieces indexed
- 20 / 20 armor-set families indexed
- 28 / 773 mod records indexed
- 18 calibration blueprint records
- 12 ammo records
- 20 / 31 Combat Deviations indexed
- 22 / 170 Cradle Overrides indexed
- 10 / 283 attachment records indexed

Coverage numbers are surfaced in the planner as an audit aid. A record may be structurally indexed while some current numeric/detail fields remain pending verification.

## Planner changes
- Gear Tier remains hard-capped to I-V.
- Blueprint Stars remain separate and rarity-capped.
- Current 2026 calibration-blueprint model supports verified ranges where known and manual exact rolls where ranges are still pending; no values are invented.
- Armor gains quick Equip Armor Set and Clear Armor actions.
- Item picker now supports search, favorites, recent items, rarity filtering, and contextual facets such as weapon type, armor set/key armor, calibration style, mod suffix, and deviation rarity.
- Picker displays shown/available corpus counts.
- Build Report adds Data Audit coverage, selected-record detail gaps, and community conflict visibility.
- Community conflicts remain flagged instead of silently resolved.
- Client-facing records contain source-name attribution only; no outbound source URLs are shipped.
- Schema version: 14.

## Validation
- `node --check app.js`: pass
- `node --check data/community-data.js`: pass
- duplicate-ID audit: pass
- client source URL scan: pass (no http/https strings)
- ZIP integrity test: pass
- deployment chunk Git blob hashes match the local chunks exactly
- production ZIP SHA-256: `e9f5c36d05c2feb4f4db36f8bd3781347833a876b382d8059237386669bff01b`

## Deployment
`.cpanel.yml` reconstructs `deploy/site-v1.2.b64.part*` and extracts the verified site into `$HOME/public_html/build-planner/`.
