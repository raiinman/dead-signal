# Dead Signal — AI Continuity / Handoff

> **Purpose:** This is the canonical handoff file for future ChatGPT/Codex sessions working on Dead Signal. Read this file **before changing anything**. Update it after meaningful milestones, architectural changes, deployment discoveries, or major data/UI work.
>
> Last updated: **2026-08-09 22:35 MST**

## 1. Project identity

- Project: **Dead Signal Ultimate Planner**
- Game: **Once Human**
- Repository: `raiinman/dead-signal`
- Branch: **`main` only** unless the user explicitly requests otherwise.
- Live planner: `https://deadsignaldb.com/build-planner/`
- Hosting: Namecheap shared hosting / cPanel.
- Deployment target: `$HOME/public_html/build-planner/`
- cPanel repository path: `/home/deadthrr/repositories/dead-signal`
- Remote: `https://github.com/raiinman/dead-signal.git`

## 2. Non-negotiable workflow rule

**Do not invent a new deployment workflow.**

The working flow is:

1. Commit finished source/static files to `raiinman/dead-signal` on `main`.
2. User opens cPanel → Git Version Control.
3. **Update from Remote**.
4. **Deploy HEAD Commit**.
5. Hard refresh browser with `Ctrl+Shift+R` when needed.

### Critical shared-hosting discovery

Namecheap/cPanel shared hosting became unreliable when `.cpanel.yml` performed runtime/build work such as:

- Python patch scripts
- recursive `find` scans
- archive reconstruction/unzip chains
- server-side JS/data transforms
- outbound GitHub Release downloads

A minimal deploy test proved that **copy-only deployment is reliable**.

### HARD DEPLOYMENT RULE

> **Build/transform in GitHub or locally. cPanel must only copy already-prepared static files.**

Current `.cpanel.yml` is intentionally copy-only. Do **not** reintroduce Python, `find`, unzip/build chains, runtime patching, or external downloads into deployment without explicit user approval and a strong reason.

## 3. Current deployment status

### Last confirmed successful live deployment

Commit confirmed by screenshot as both cPanel **HEAD Commit** and **Last Deployed SHA**:

`c3a62dbb414ad1368850f60032890b4b4f0d75d4`

`deploy-status.txt` reached:

```text
Dead Signal static image deployment
RUN copy Build Lab files
OK copy Build Lab files
COMPLETE static image deployment
```

This was the breakthrough that proved copy-only deployment works.

### Current repo state at time this handoff was created

Before this continuity file, latest work on `main` included visual polish through:

`b5ed8a0f5f02b8875b48e20961870ce4c11f5830`

That polish may **not yet be deployed**. The next cPanel Update/Deploy will include it plus this continuity file commit, but `.cpanel.yml` only copies production Build Lab files.

## 4. Current live UI state

Confirmed by user screenshot after the successful static image deploy:

- Weapon picker opens correctly.
- Real mined Once Human weapon artwork is visible in cards.
- AKM, AUG, KAM variants, M416, etc. displayed real hosted images.
- Two-column picker density remains intact.
- Rarity borders/badges are visible.
- User reaction: **“looking good!”**

The image problem is therefore solved for weapon cards at the architecture level.

### Latest visual polish pushed after that screenshot

Pending/next visual pass includes:

- larger weapon artwork inside image bays
- less dead space around thumbnails
- slightly stronger rarity framing/glow
- subtle hover zoom
- improved breathing room for selected/system/mod thumbnails

Do not redesign the whole picker unless the user asks. Current direction is **small, surgical polish**.

## 5. Image architecture

### Master assets

The full mined asset archive is approximately **3 GB**, split into:

- `assets.7z.001`
- `assets.7z.002`
- `assets.7z.003`
- `assets.7z.004`
- `assets.7z.005`
- `assets.7z.006`
- `assets.7z.007`

These are archival/source assets. **Do not upload the 3 GB set to normal web hosting or the Git repo.**

GitHub Release:

`game-assets-2026-08-09`

Release URL:

`https://github.com/raiinman/dead-signal/releases/tag/game-assets-2026-08-09`

### Slim player image pack

File:

`dead-signal-player-images-v1.3.zip`

Verified size:

`13,265,970 bytes`

SHA-256:

`baaeccd8940cdc31c82d87d7c51c80c4bfe6986597ef42bc79602215571a6358`

Contains exactly **712 PNG files**.

The user manually uploaded and extracted this ZIP in cPanel so the physical PNGs persist on Namecheap hosting under:

`public_html/build-planner/assets/reference-images/`

Example known file:

`public_html/build-planner/assets/reference-images/ar/ar_ak47_n-0ea00206dd9c.png`

Browser path:

`/build-planner/assets/reference-images/ar/ar_ak47_n-0ea00206dd9c.png`

The images are served by **Namecheap web hosting**, not GitHub at runtime.

## 6. Current browser-side image renderer

The successful architecture uses a static browser-side enhancer:

`preview/build-lab/player-images.js`

It reads the existing `window.DS_COMMUNITY` corpus, resolves `imageAsset` / related image fields to hosted `/build-planner/assets/...` URLs, and injects media into:

- picker cards
- selected weapon cards
- selected armor cards
- system cards
- mod groups

It is loaded by `preview/build-lab/index.html` with a cache-busted version.

Do not replace this with server-side patching unless there is a clear reason.

## 7. Current copy-only cPanel deployment

The working deployment copies prepared files from the repo into `$HOME/public_html/build-planner/`.

Current production files copied include:

- `preview/build-lab/index.html` → `index.html`
- `preview/build-lab/build-lab.css` → `build-lab.css`
- `preview/build-lab/media-enhancements.css` → `media-enhancements.css`
- `preview/build-lab/density-enhancements.css` → `density-enhancements.css`
- `preview/build-lab/player-images.js` → `player-images.js`

The deploy also writes `deploy-status.txt` and removes obsolete `media-enhancements.js` / old test file where applicable.

### Why this exists

Earlier deploys hung because cPanel shared hosting was asked to do runtime work. Important failed approaches:

1. Download image ZIP from GitHub Release during deploy → hung/unreliable.
2. Put 13 MB image ZIP in repo and extract during deploy → still problematic.
3. Recursive hosted image count (`find ... | wc -l`) → deploy stopped at `RUN persistent image verification`.
4. Python `patch-player-media-v1.3.py` during deploy → targeted deploy hung again.
5. Minimal echo-only `.cpanel.yml` → **worked immediately**.
6. Copy-only static deployment → **worked immediately and advanced Last Deployed SHA**.

Do not repeat the failed approaches casually.

## 8. Player-facing v1.3 database status

Current normalized player-facing corpus counts:

- Weapons: **120**
- Armor: **173**
- Armor Sets: **23**
- Mods: **817 entries / 105 families**
- Planner Attachments: **108**
- Current Calibrations: **94**
- Unique player-facing Deviations: **97**
- Unique player-facing Cradles: **120**
- Usable Ammo: **144**
- Build-relevant Consumables: **150**

Data quality checks previously passed for player-facing use:

- readable Mod effects
- readable Cradle effects
- Deviations have readable abilities/descriptions
- all 23 armor sets have bonuses
- ammo/calibration compatibility validates to weapon classes
- 8 old attachment rows remain unresolved for exact weapon compatibility and should be marked unresolved
- junk/internal text removed from player-facing corpus

Current priority remains:

> **Finish player-facing database + imagery + planner UX first. Exact combat math/stat modeling comes later.**

## 9. Miner/source hierarchy

When resolving factual game data, use this practical hierarchy:

1. **Game Miner** for directly extractable installed-game facts
2. **OnceHumanDB**
3. **Wikily**
4. **Official Once Human sources** for current-patch/system corrections and authoritative change notes

Do not blindly expose mined runtime/system rows. Filter to current, player-visible information.

## 10. Game Miner summary

The local miner successfully parsed Once Human `script.npk` with **0 parse errors**.

Important raw datasets included:

- weapons
- armor sets
- attachments
- relationships
- cradles
- mods
- reference-images
- buffs
- statuses
- deviations
- image-coverage
- progression
- calibrations
- consumables
- ammo
- skills

Notable raw counts:

- weapons: 120
- armor: 173 player-facing pieces after normalization
- mods: 1,618 raw
- attachments: 202 raw
- cradles: 170 raw / 120 unique player-facing
- calibrations: 188 raw = 94 current + 94 legacy
- deviations: 160 raw / 97 normalized unique player-facing
- ammo: 187 raw / 144 normalized planner entries
- consumables: 1,086 raw / 150 build-relevant
- relationships: 10,830
- reference image mappings: ~30,939 distinct, ~28,504 resolved

Large forensic index `reference-tracer.sqlite` is roughly 255 MB with ~1.35M occurrences. **Do not upload it to normal production repo/hosting.**

## 11. Image coverage notes

The slim 712-file player image set covers the player-facing corpus broadly.

Known no-image consumables with no resolved `imageRef`:

- Whim Potion: Chloro-armor
- Whim Potion: Fluid Type
- Whim Potion: Predator
- Whim Potion: Utter Delight
- Whim Time

These can intentionally remain placeholders unless a valid image source is later found.

Earlier audit showed records with image assets available for:

- weapons: 120/120
- armor: 173/173 after mapping/resolution work
- mods: 817/817
- attachments: 108/108
- deviations: 97/97
- cradles: 120/120
- calibrations: 94/94
- ammo: 144/144
- consumables: 145/150
- armorSets: 23/23

Current browser-side renderer should be extended/tuned category by category rather than reintroducing deployment-time resolvers.

## 12. Product/design direction

Dead Signal aims to combine/surpass:

- Wikily polish
- OnceHumanDB depth
- OhDex visual immediacy
- Dead Signal’s own high-end tactical/command-center identity

Design language:

- dark tactical intelligence terminal
- background near `#06080a`
- red accents (`#e51f2b`, bright red near `#ff3440`)
- angular cards
- restrained scanline/signal/radar motifs
- fixed left navigation on Build Lab
- natural readable typography
- rarity should be readable but not gaudy
- homepage = cinematic front door
- planner = operations room / Build Lab

User likes bold/out-of-pocket design thinking, but continuity and functionality matter more than random redesigns.

## 13. Planner feature baseline

Existing planner architecture already supports:

- 3 weapon slots
- ammo
- calibration configuration
- attachments
- 6 armor slots
- armor mods
- quick-equip armor sets
- Deviations
- Cradles
- consumables
- build identity/metadata
- loadout report
- rarity handling
- local save/templates
- import/export
- share links
- compatibility filtering

The main problem was data/image completeness, not basic planner architecture.

## 14. Current game-system modeling rules

See `PROJECT-RULES.md` for detailed canonical rules. Important examples:

- Gear Tier is I–V only.
- Blueprint stars are separate from Gear Tier.
- Current weapon calibration blueprint model follows the post-Jan-21-2026 system rather than obsolete gear calibration behavior.
- Current Mod 2.0 behavior should be modeled instead of old random-subattribute assumptions.
- Planner fidelity comes before advanced combat/proc math.

## 15. Files worth reading first in a future session

Read these before editing:

1. `AI-CONTINUITY.md` — this file
2. `PROJECT-RULES.md` — canonical product/game modeling constraints
3. `.cpanel.yml` — deployment must remain copy-only
4. `preview/build-lab/index.html`
5. `preview/build-lab/player-images.js`
6. `preview/build-lab/media-enhancements.css`
7. `preview/build-lab/build-lab.css`
8. `preview/build-lab/density-enhancements.css`

Do not assume old `deploy/patch-*.py` scripts are still part of the live deployment. Many are historical artifacts from the old runtime-patching workflow.

## 16. Immediate next steps from this handoff

At the time this file was created, the next work should be:

1. Deploy/check the latest visual polish commit(s) using the proven copy-only cPanel workflow.
2. Inspect Primary Weapon picker after polish.
3. Open **Armor picker** and verify hosted imagery there.
4. Tune armor presentation if necessary.
5. Check Deviations / systems / mods / Cradles visually and extend the browser-side enhancer where needed.
6. Keep expanding player-facing imagery/UX until the planner feels visually complete.
7. Only after player-facing database + imagery + UX are solid, move into specific exact stats and combat math.

## 17. Continuity rules for future AI sessions

- **Read this file first.**
- Do not create new branches unless the user asks.
- Work directly on `main` when authorized, as has been the established workflow.
- Do not change hosting/deployment architecture without discussing it with the user.
- Preserve copy-only cPanel deployment.
- Do not upload the 3 GB master asset archive to production hosting or normal Git history.
- Do not put `reference-tracer.sqlite` into normal production.
- Keep real images on Namecheap hosting under `assets/reference-images/`.
- Prefer small, testable UI changes and live screenshots over giant rewrites.
- When something breaks, isolate the exact layer before changing unrelated code.
- Update this file whenever a major milestone changes the project state.

## 18. User interaction/work style notes relevant to this project

- User prefers direct action and live iteration over long abstract planning.
- User wants screenshots/visual confirmation and practical steps.
- User gets frustrated when established workflows are changed without need.
- Do not make them re-explain project history when this file or repo can answer it.
- Keep instructions compact and sequential.

---

### Continuity checkpoint

If a future AI session can read this file, it should be able to resume Dead Signal without relying on the original long chat transcript.
