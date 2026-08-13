# Dead Signal — Canonical Planner Rules

These are the working constraints for the Ultimate Planner.

## Product direction
- Finish the player-facing database, imagery, and planner workflow before advanced damage math.
- The installed-game Miner snapshot is the canonical source for migrated player-facing categories. Weapons are fully migrated; the v1.3 compatibility corpus remains only for categories not yet migrated.
- Mined game data should be preferred for extractable factual data. Community and official references may validate unresolved behavior, but must not silently override canonical mined records or serve as a runtime fallback for migrated categories.
- Do not invent mechanics or numeric relationships that are not verified.

## Deployment architecture
- Production deploys use the existing `main` branch and cPanel Git Version Control workflow only.
- Namecheap shared-hosting deployment must remain **copy-only**.
- Build, normalize, patch, transform, validate, unzip, scan, or generate files before deployment; do not perform those operations inside `.cpanel.yml`.
- `.cpanel.yml` should only create destination directories, copy already-prepared files, remove explicitly obsolete presentation/diagnostic files when necessary, and write lightweight status markers.
- Persistent hosted game imagery under `/public_html/build-planner/assets/reference-images/` is not rebuilt or scanned during normal deploys.
- Do not add server-side Python, recursive `find`, archive reconstruction/extraction, external downloads, or runtime build steps back into normal cPanel deployment.
- **Intentional runtime exception:** `api/twitter/cache/index.php` is a small PHP endpoint for the landing-page Official Once Human Feed. It is copied as prepared source by cPanel; it fetches public X pages at runtime, maintains a short local cache, and does not require an X developer account, Bearer Token, API key, OAuth, paid widget, or GitHub worker.
- Do not generalize that PHP exception into a server-side application framework. Dead Signal remains primarily a prepared static workstation with one narrowly scoped feed cache endpoint.

## Global workstation architecture
- Dead Signal uses exactly **one global workstation sidebar**.
- The global shell owns brand, primary route navigation, route state, readability controls, and system/Miner context.
- Individual routes own only local tools and local content.
- Do not add a second global sidebar, duplicate global masthead, or unrelated route-specific shell.
- Desktop sidebar collapse must remain explicit and persisted with `dead-signal-nav-collapsed`; do not return to hover-only expansion.
- Unbuilt database destinations remain visibly `SOON`; do not imply unfinished routes are live.
- Shared motion should remain restrained, progressive-enhancement behavior with reduced-motion support.
- The landing page uses **one canonical database search** in the top command strip. Do not reintroduce a second full-width `Search the Signal` field below the hero. The top search filters the database systems directly, Enter moves to the database section, and `/` focuses that same field.

## Readability / accessibility
- Readability is a product requirement, not optional polish. Do not optimize information density to the point that normal text requires squinting.
- The canonical text-size system lives in `shared/readability.css` and `shared/readability.js`.
- Supported user modes are `compact`, `default`, `large`, and `xlarge`; **Default must remain a comfortable reading size** and Compact is the high-density option.
- The selected mode is stored origin-wide in `localStorage` under `dead-signal-font-size`, so the same preference can follow the user between Dead Signal sections on the same domain.
- New Dead Signal interfaces should map typography onto the shared semantic `--ds-type-*` variables rather than adding arbitrary fixed tiny font sizes.
- The Build Lab exposes the control as `A− / A / A+ / A++` in the left sidebar. Other site sections should use the same setting and shared controller when integrated.
- Text scaling should prioritize typography, not browser-style page zoom; do not unnecessarily enlarge game art or destroy layout proportions.
- Respect `prefers-reduced-motion` for decorative motion and transitions.

## Provenance / transparency
- Preserve source provenance internally on records.
- Show plain-text attribution to users when useful (for example: `Source: Wikily`, `Source: OnceHumanDB`, `Source: Once Human Official`).
- Do not add outbound source links or clickable link-backs in normal database/planner factual attribution UI.
- **Official social-feed exception:** the landing-page Official Once Human Feed may link to the verified `@OnceHuman_` profile and original X posts because opening the source post is part of the feed interaction itself, not factual-record attribution.

## Official Once Human feed
- Canonical implementation: `api/twitter/cache/index.php`.
- Working architecture: Namecheap PHP reads the public `x.com/OnceHuman_` profile, extracts current status IDs, orders them newest-first, uses public/keyless X oEmbed for post text, inspects public post HTML for media/thread evidence, then serves a short same-origin cache to the landing page.
- No X developer account, API v2 credentials, Bearer Token, OAuth, SociableKIT, Jina runtime, GitHub Actions feed worker, direct syndication iframe, or visitor-side X widget is part of the approved architecture.
- Photo previews are allowed from public X media URLs.
- Video/GIF posts should use a public poster/thumbnail with an `OPEN ON X` treatment rather than proxying or hosting the actual video stream.
- Thread detection must be conservative and evidence-based; missing a thread is preferable to grouping unrelated posts.
- If upstream X temporarily fails, prefer serving the last useful cached feed instead of blanking the homepage.
- Do not replace this working path merely to imitate X's native widget chrome.

## Gear progression terminology
- Gear Tier is I–V only. There is no Gear Tier VI.
- Blueprint enhancement/star rank is a separate system from Gear Tier.
- Blueprint-star caps are rarity-dependent rather than a universal Tier VI: current community references list Green up to 3★, Blue up to 4★, Purple up to 5★, and Gold up to 6★.
- UI labels must say `Gear Tier` and `Blueprint Stars` so Tier V and 6★ cannot be confused.
- The planner must not offer a blueprint-star rank above the selected blueprint item's rarity cap.

## Current weapon calibration blueprint model
Current-game behavior is based on the January 21, 2026 Once Human Version 2.3.1 changes:
- The old weapon Gear Calibration feature was removed.
- Calibration Blueprints are applied when crafting weapons.
- New Calibration Blueprints retain their style attribute.
- New Calibration Blueprints always include one RNG Attack bonus whose range depends on rarity (officially stated up to 50%).
- The previous two random bonus attributes were merged into one RNG bonus attribute.
- The bonus attribute pool includes categories such as Crit Rate, Crit DMG, Elemental DMG, and Weakspot DMG.
- Official example for a new Legendary blueprint: Attack 33%–50% + Elemental DMG 15%–20%.
- Legacy/pre-update items may exist, but the default planner should model the current system; legacy support should be explicitly separated if added later.

## Current mod model
Current-game behavior is based on the January 21, 2026 Mod 2.0 overhaul:
- Regular mods retain their main attribute but now use fixed sub-attributes rather than random sub-attribute combinations.
- Mods have levels 1–17; mod level is derived from the summed sub-attribute levels.
- Lv. 17 is the regular-mod ceiling.
- Shiny Mods are a distinct higher-end version with the same sub-attributes as Lv. 17 but a slightly stronger main attribute.
- Special suffix families such as Crescent, Lunar, and Downstar continue to exist; current seasonal suffix families can also exist.
- Legacy mods may still be usable, but old randomly rolled mod sub-attributes should not be the default model for new builds.

## Planner before calculator
The planner must represent the actual loadout first: weapons, weapon crafting configuration, ammo, current calibration-blueprint instance and RNG rolls, attachments, current Mod 2.0 selections, six armor slots and mods, set activation, cradles, deviation, consumables, metadata, save/clone/import/export/share, and compatibility rules.

Advanced damage/proc math comes after the planner model is stable.
