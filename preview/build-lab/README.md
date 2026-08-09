# Dead Signal Build Lab visual pass

This is a staging-only visual integration of the live v1.2.8 Ultimate Planner with the Dead Signal WordPress design language.

## Scope

- Adds the fixed Dead Signal intelligence sidebar and Build Lab navigation.
- Adds a compact cinematic Build Lab header.
- Reworks planner panels, picker surfaces, status cards, report cards, form controls, and coverage cards toward the WordPress tactical UI language.
- Adds image-ready selected-item and picker cards with clean fallbacks for the current image-less v1.2.8 corpus.
- Adds ultrawide/4K density rules so larger displays gain useful information density rather than empty space.
- Keeps the existing v1.2.8 planner DOM IDs, JavaScript behavior, schema 14, and community-data corpus unchanged.
- Does not change combat math, item data, compatibility logic, saves, imports/exports, sharing, templates, or picker behavior.

## Isolated cPanel preview deployment

On the `agent/build-lab-visual-pass` branch, `.cpanel.yml` is intentionally different from `main` and deploys only this preview to:

`$HOME/public_html/build-lab-preview/`

That should make the preview available at:

`https://deadsignaldb.com/build-lab-preview/`

It does not write to `$HOME/public_html/build-planner/`.

## Validation

- Existing planner DOM IDs used by the v1.2.8 app are preserved.
- Media enhancements handle missing imagery with intentional tactical fallbacks.
- Future `imageUrl`, `assetPath`, and `imagePath` fields can light up the cards without changing the planner layout again.
- Production `/build-planner/` remains isolated while this branch is deployed.

## Production path

After visual approval, package the approved source into the normal Dead Signal deployment payload and only then update the production deployment on `main`.
