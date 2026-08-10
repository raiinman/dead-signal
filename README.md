# Dead Signal

Dead Signal is an independent Once Human database and build-planning project. The current player-facing planner is deployed from this repository to `https://deadsignaldb.com/build-planner/`.

## Repository layout

- `.cpanel.yml` — canonical cPanel deployment recipe.
- `deploy/site-v1.2.b64.part*` — base planner bundle.
- `deploy/patch-v1.2.*.py` — incremental planner patches still required by the current base bundle.
- `deploy/player-corpus-v1.3.b64.part*` — normalized player-facing v1.3 data corpus.
- `deploy/dead-signal-player-images-v1.3.zip` — slim player-facing image pack.
- `deploy/patch-player-images-v1.3.py` — resolves mined image references after extraction.
- `preview/build-lab/` — live Build Lab presentation files copied over the planner shell during deployment. The folder name is historical; these files are production inputs.

## Deployment

Dead Signal uses one deployment path:

1. Update `main`.
2. In cPanel Git Version Control, run **Update from Remote**.
3. Run **Deploy HEAD Commit**.

The planner deploys to:

```text
$HOME/public_html/build-planner/
```

The deploy reconstructs the base planner, applies required patches, installs the v1.3 player corpus and local image pack, resolves image paths, then copies the Build Lab presentation layer.

## Current development phase

Finish player-facing database completeness and imagery first. Exact combat/stat modeling comes after the visible corpus is stable and verified.

Do not invent missing game mechanics or numeric relationships. Preserve uncertainty until the underlying data can be verified.
