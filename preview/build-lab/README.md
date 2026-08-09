# Dead Signal Build Lab visual pass

This is a staging-only visual integration of the live v1.2.8 Ultimate Planner with the Dead Signal WordPress design language.

## Scope

- Adds the fixed Dead Signal intelligence sidebar and Build Lab navigation.
- Adds a compact cinematic Build Lab header using the existing Dead Signal theme artwork.
- Reworks planner panels, picker surfaces, status cards, report cards, form controls, and coverage cards toward the WordPress tactical UI language.
- Keeps the existing v1.2.8 planner DOM IDs, JavaScript behavior, schema 14, and community-data corpus unchanged.
- Does not change combat math, item data, compatibility logic, saves, imports/exports, sharing, templates, or picker behavior.

## Safety

This preview is intentionally not wired into `.cpanel.yml` and cannot change the live site merely by existing in GitHub.

## Validation

- `node --check app.js` passes on the complete local preview bundle.
- `node --check data/community-data.js` passes.
- Every static `$('<id>')` reference in `app.js` still resolves to an element in the updated `index.html`.
- Preview ZIP integrity passes.

## Production path

After visual approval, package the approved source into the normal Dead Signal deployment payload and only then update `.cpanel.yml`.
