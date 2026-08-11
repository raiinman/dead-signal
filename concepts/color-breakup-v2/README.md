# Dead Signal — Color Breakup Concept v2

This concept intentionally moves back toward the existing Build Lab structure while keeping the stronger color language from the visual render.

## Live preview

[Open the rendered concept](https://htmlpreview.github.io/?https://github.com/raiinman/dead-signal/blob/main/concepts/color-breakup-v2/index.html)

## What changed from v1

- Restores the familiar left Build Lab navigation and stacked section flow.
- Uses color as section identity instead of turning the planner into a dashboard.
- Loads the production `community-data.js` from `deadsignaldb.com` when available.
- Shows live corpus counts for weapons, armor, calibrations, mods, deviations, and cradles.
- Samples real weapon records into the visible weapon cards.
- Clearly falls back to the last verified planner snapshot if production data cannot load.
- Remains isolated under `concepts/` and is not copied by `.cpanel.yml`.
