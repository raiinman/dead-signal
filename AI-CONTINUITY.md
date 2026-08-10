# Dead Signal — AI Continuity / Handoff

> **Purpose:** Canonical handoff for future ChatGPT/Codex sessions working on Dead Signal. Read this file **before changing anything**. Update it after meaningful milestones, architecture/deployment discoveries, major data changes, or significant UI decisions.
>
> Last updated: **2026-08-10 01:13 MST**

## 1. Project identity

- Project: **Dead Signal Ultimate Planner**
- Game: **Once Human**
- Repository: `raiinman/dead-signal`
- Branch: **`main` only** unless the user explicitly requests otherwise.
- Live planner: `https://deadsignaldb.com/build-planner/`
- Hosting: Namecheap shared hosting / cPanel.
- Production planner target: `$HOME/public_html/build-planner/`
- User deploy workflow: cPanel → Git Version Control → **Update from Remote** → **Deploy HEAD Commit** → hard refresh if needed.

## 2. Non-negotiable deployment rule

**Do not invent a new deployment workflow.**

Namecheap shared hosting proved unreliable when `.cpanel.yml` performed runtime/build work such as Python, recursive scans, archive reconstruction/extraction, data transforms, or outbound release downloads.

A minimal deployment and then the current static deployment proved that **copy-only cPanel deployment is reliable**.

### HARD RULE

> **Build/transform before deployment. cPanel only copies prepared static files.**

Current `.cpanel.yml` may use lightweight `mkdir`, `cp`, `rm`, and `echo`. Do **not** reintroduce Python, `find`, unzip/build chains, runtime patching, external downloads, or corpus rebuilding into normal cPanel deploys.

Persistent game PNGs under `/public_html/build-planner/assets/reference-images/` stay on hosting and are not recopied/scanned every deploy.

## 3. Confirmed deployment breakthrough

The first meaningful copy-only deployment that fully completed was commit:

`c3a62dbb414ad1368850f60032890b4b4f0d75d4`

cPanel showed the same value for **HEAD Commit** and **Last Deployed SHA**, and `deploy-status.txt` reached:

```text
Dead Signal static image deployment
RUN copy Build Lab files
OK copy Build Lab files
COMPLETE static image deployment
```

Git fetch and the deploy engine themselves were proven healthy. The earlier hangs were caused by complex server-side work.

## 4. Current planner UI state

Current direction is a full-width tactical Build Lab rather than a cramped dashboard.

Recent confirmed/pushed changes:

- Real hosted **weapon images** display in the picker and selected cards.
- Real hosted **armor images** are mapped and display; armor was not missing from the miner.
- Sidebar **Signal Status/radar block was removed** because it belongs to the main website, not the planner workspace.
- **Cradle Overrides** is now a contained tactical sub-card with its own internal scroll instead of a page-length list.
- The **Loadout Report** no longer consumes a permanent right rail. The planner uses full width and the report sits beneath the workspace in a wider, more readable layout.
- The left navigation includes a **Loadout Report** jump link.
- Typography received a readability bump; tiny 8–10px body/detail text should no longer be the default design target.

Do not casually undo these changes to regain density. The user explicitly prioritized readability and usable workspace width.

## 5. Shared readability / accessibility system

Readability is now a first-class Dead Signal feature.

Canonical shared files:

- `shared/readability.css`
- `shared/readability.js`

Build Lab loads them as:

- `/build-planner/readability.css`
- `/build-planner/readability.js`

### Supported modes

- `compact` — high-density option
- `default` — comfortable normal reading size
- `large`
- `xlarge`

The Build Lab sidebar exposes these as:

`A− / A / A+ / A++`

The controller stores the user preference in origin-wide `localStorage`:

`dead-signal-font-size`

Because localStorage is origin-wide, the same preference can follow the user between the planner and the WordPress site **once the WordPress theme loads the same shared files**.

### Typography architecture

`shared/readability.css` defines semantic `--ds-type-*` variables and maps the existing Build Lab typography onto them. New Dead Signal interfaces should use these variables instead of adding arbitrary tiny fixed pixel sizes.

The system deliberately scales typography rather than applying browser-style page zoom, so game art and the whole layout do not unnecessarily balloon.

### WordPress integration status

The editable WordPress theme source (`functions.php` / enqueue code) is **not currently present in this GitHub repo**, based on repository search. Do not claim the main WordPress site is already wired to the readability system.

When the theme source is available, integrate these exact shared files and the same `dead-signal-font-size` setting so the user preference becomes truly site-wide.

## 6. Current Build Lab production files

The copy-only cPanel deployment currently copies prepared files including:

- `preview/build-lab/index.html` → `index.html`
- `preview/build-lab/build-lab.css` → `build-lab.css`
- `preview/build-lab/media-enhancements.css` → `media-enhancements.css`
- `preview/build-lab/density-enhancements.css` → `density-enhancements.css`
- `preview/build-lab/planner-cleanup.css` → `planner-cleanup.css`
- `shared/readability.css` → `readability.css`
- `shared/readability.js` → `readability.js`
- `preview/build-lab/armor-image-map.js` → `armor-image-map.js`
- `preview/build-lab/player-images.js` → `player-images.js`

No runtime transformation belongs in this deployment.

## 7. Image architecture

### Master assets

The complete mined image/archive set is approximately **3 GB**, split into seven 7-Zip volumes (`assets.7z.001`–`.007`). These are archival/source assets and should **not** be pushed into normal Git history or normal web-hosting deployment.

GitHub Release:

`game-assets-2026-08-09`

### Slim player image pack

`dead-signal-player-images-v1.3.zip`

- size: `13,265,970` bytes
- SHA-256: `baaeccd8940cdc31c82d87d7c51c80c4bfe6986597ef42bc79602215571a6358`
- exactly **712 PNGs**

The user manually uploaded/extracted this pack on Namecheap, so the PNGs persist under:

`public_html/build-planner/assets/reference-images/`

Known example:

`/build-planner/assets/reference-images/ar/ar_ak47_n-0ea00206dd9c.png`

### Browser renderer

`preview/build-lab/player-images.js` reads `window.DS_COMMUNITY` and injects hosted imagery into picker cards, selected weapon/armor cards, systems, and mod groups.

### Armor mapping

Armor was **not** missed by the miner.

Verified player-facing armor image coverage:

- 173 armor records
- 173/173 have image references
- 173/173 resolved to physical PNGs
- 172 unique physical armor PNGs because two records share one image
- zero missing armor mappings

Static exact mapping lives in:

`preview/build-lab/armor-image-map.js`

It is loaded before `player-images.js` and copied statically by cPanel.

## 8. Player-facing v1.3 database status

Normalized player-facing corpus:

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

Quality checks previously passed for player-facing use:

- readable Mod effects
- readable Cradle effects
- Deviations have readable abilities/descriptions
- all 23 armor sets have bonuses
- ammo/calibration compatibility validates to weapon classes
- 8 old attachment rows remain unresolved for exact weapon compatibility and should stay marked unresolved
- junk/internal text removed from player-facing corpus

Priority remains:

> **Finish player-facing database + imagery + UX before exact combat math/stat modeling.**

## 9. Image coverage notes

Known intentional no-image consumables:

- Whim Potion: Chloro-armor
- Whim Potion: Fluid Type
- Whim Potion: Predator
- Whim Potion: Utter Delight
- Whim Time

Broad player-facing image coverage after mapping work:

- weapons: 120/120
- armor: 173/173
- mods: 817/817 mapped at data level
- attachments: 108/108
- deviations: 97/97
- cradles: 120/120
- calibrations: 94/94
- ammo: 144/144
- consumables: 145/150
- armorSets: 23/23

Continue category-by-category browser presentation work instead of bringing back deploy-time resolvers.

## 10. Game Miner / factual hierarchy

For factual data use this practical hierarchy:

1. **Game Miner** for directly extractable installed-game facts
2. **OnceHumanDB**
3. **Wikily**
4. **Official Once Human sources** for current-patch/system corrections and authoritative change notes

Do not blindly expose runtime/system rows from the miner. Filter to player-visible/current data.

The miner parsed Once Human `script.npk` with **0 parse errors**.

Important raw counts:

- weapons: 120
- armor: 173 normalized player-facing pieces
- mods: 1,618 raw
- attachments: 202 raw
- cradles: 170 raw / 120 unique player-facing
- calibrations: 188 raw = 94 current + 94 legacy
- deviations: 160 raw / 97 normalized unique player-facing
- ammo: 187 raw / 144 normalized planner entries
- consumables: 1,086 raw / 150 build-relevant
- relationships: 10,830
- reference image mappings: ~30,939 distinct, ~28,504 resolved

`reference-tracer.sqlite` is roughly 255 MB with ~1.35M occurrences. **Do not upload it to normal production.**

## 11. Product/design direction

Dead Signal aims for:

- OnceHumanDB depth
- Wikily polish
- OhDex visual immediacy
- Dead Signal’s own high-end tactical/command-center identity

Design language:

- dark tactical intelligence terminal
- background around `#06080a`
- red accents around `#e51f2b` / `#ff3440`
- angular cards
- restrained scanline/signal motifs
- fixed left Build Lab navigation
- natural readable typography
- rarity readable but not gaudy
- homepage = cinematic front door
- planner = operations room / Build Lab

**Readability now outranks maximum information density.**

## 12. Planner feature baseline

Planner already supports:

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

The main historical problem was data/image completeness, not the underlying planner architecture.

## 13. Current game-system modeling rules

Read `PROJECT-RULES.md` for canonical rules. Key examples:

- Gear Tier is I–V only.
- Blueprint stars are separate from Gear Tier.
- Current weapon calibration model follows the post-Jan-21-2026 system rather than obsolete Gear Calibration behavior.
- Current Mod 2.0 behavior should be modeled instead of legacy random-subattribute assumptions.
- Planner fidelity comes before advanced damage/proc math.
- Readability/accessibility system is canonical and should be reused by new pages.

## 14. Files future sessions should read first

1. `AI-CONTINUITY.md`
2. `PROJECT-RULES.md`
3. `.cpanel.yml`
4. `shared/readability.css`
5. `shared/readability.js`
6. `preview/build-lab/index.html`
7. `preview/build-lab/planner-cleanup.css`
8. `preview/build-lab/player-images.js`
9. `preview/build-lab/armor-image-map.js`
10. `preview/build-lab/media-enhancements.css`
11. `preview/build-lab/build-lab.css`
12. `preview/build-lab/density-enhancements.css`

Old `deploy/patch-*.py` files are historical artifacts and are **not** part of normal live deployment.

## 15. Immediate next steps

1. Deploy the current Build Lab readability controls with the normal copy-only cPanel workflow.
2. Test all four text modes at normal browser zoom, especially picker cards, Armor, Build Systems, Cradles, and Loadout Report.
3. Adjust any clipping/wrapping found at `large` or `xlarge` without shrinking the global mode back down.
4. Continue player-facing imagery for Deviations / Mods / Cradles / other systems as needed.
5. When the WordPress theme source becomes available, enqueue `shared/readability.css/js` on the main site and surface the same preference/control in the main navigation/sidebar so the setting is genuinely site-wide.
6. After imagery + UX are solid, move into exact stats/combat math.

## 16. Continuity rules for future AI sessions

- **Read this file first.**
- Do not create new branches unless the user asks.
- Work on `main` under the established workflow.
- Do not change deployment architecture without discussing it with the user.
- Preserve copy-only cPanel deployment.
- Do not upload the 3 GB master archive or `reference-tracer.sqlite` to normal production.
- Keep real images on Namecheap under `assets/reference-images/`.
- Prefer small, testable UI changes and screenshot/live iteration over giant rewrites.
- Isolate the broken layer before changing unrelated code.
- Do not make the user re-explain project history when this file/repo can answer it.
- Update this file after major milestones.

## 17. User workflow preferences relevant to this project

- Direct action and live iteration are preferred over long abstract planning.
- Screenshots/visual confirmation are valuable.
- Established workflows should not be changed without a strong reason.
- Keep deploy instructions compact and sequential.
- Accessibility/readability is explicitly a priority.

---

### Continuity checkpoint

A future AI session that reads this file should be able to resume Dead Signal without relying on the original long chat transcript.
