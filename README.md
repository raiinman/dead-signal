# Dead Signal

Dead Signal is an independent, data-driven Once Human build-planning project. The planner is the product; the root website is a lightweight landing page that introduces it.

- Website: `https://deadsignaldb.com/`
- Build Planner: `https://deadsignaldb.com/build-planner/`

## Repository layout

- `index.html`, `site.css`, `site.js` — static root landing page.
- `preview/build-lab/` — production planner presentation files. The directory name is historical; do not treat it as disposable preview output.
- `shared/` — shared readability controls used across Dead Signal interfaces.
- `deploy/` — required prepared planner bundles and patches used by the current deployment path.
- `tools/miner/` — canonical Miner source, tests, build support, and updater metadata.
- `concepts/` — isolated design explorations; not production deployment inputs.
- `archive/` — superseded continuity records retained for history.
- `RELEASE-v*.md` — historical planner release notes retained at the root pending a deliberate documentation migration.

No WordPress or PHP runtime is required.

## Deployment

Dead Signal uses cPanel Git Version Control from `main`:

1. Update from Remote.
2. Deploy HEAD Commit.

`.cpanel.yml` performs copy-only deployment:

- root landing files → `$HOME/public_html/`
- planner files → `$HOME/public_html/build-planner/`

Builds, data transforms, downloads, and archive extraction must happen before deployment, never in cPanel. Persistent player-facing PNGs remain on the server under `build-planner/assets/reference-images/`.

## Working rules

Read `AI-CONTINUITY.md` and `PROJECT-RULES.md` before making changes. Preserve the planner, mined-data provenance, Miner source, and uncertainty around unproven game mechanics.
