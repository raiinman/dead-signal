# Dead Signal — Canonical Planner Rules

These are the working constraints for the Ultimate Planner.

## Product direction
- Finish the player-facing database, imagery, and planner workflow before advanced damage math.
- The normalized v1.3 player corpus is the current planner baseline.
- Mined game data is integrated and should be preferred for extractable factual data; community and official references are used to validate, fill gaps, and correct current-patch behavior.
- Do not invent mechanics or numeric relationships that are not verified.

## Deployment architecture
- Production deploys use the existing `main` branch and cPanel Git Version Control workflow only.
- Namecheap shared-hosting deployment must remain **copy-only**.
- Build, normalize, patch, transform, validate, unzip, scan, or generate files before deployment; do not perform those operations inside `.cpanel.yml`.
- `.cpanel.yml` should only create the destination directory, copy already-prepared files into `/public_html/build-planner/`, remove explicitly obsolete presentation files when necessary, and write lightweight status markers.
- Persistent hosted game imagery under `/public_html/build-planner/assets/reference-images/` is not rebuilt or scanned during normal deploys.
- Do not add server-side Python, recursive `find`, archive reconstruction/extraction, external downloads, or other runtime build steps back into normal cPanel deployment.

## Readability / accessibility
- Readability is a product requirement, not optional polish. Do not optimize information density to the point that normal text requires squinting.
- The canonical text-size system lives in `shared/readability.css` and `shared/readability.js`.
- Supported user modes are `compact`, `default`, `large`, and `xlarge`; **Default must remain a comfortable reading size** and Compact is the high-density option.
- The selected mode is stored origin-wide in `localStorage` under `dead-signal-font-size`, so the same preference can follow the user between Dead Signal sections on the same domain.
- New Dead Signal interfaces should map typography onto the shared semantic `--ds-type-*` variables rather than adding arbitrary fixed tiny font sizes.
- The Build Lab exposes the control as `A− / A / A+ / A++` in the left sidebar. Other site sections should use the same setting and shared controller when integrated.
- Text scaling should prioritize typography, not browser-style page zoom; do not unnecessarily enlarge game art or destroy layout proportions.

## Provenance / transparency
- Preserve source provenance internally on records.
- Show plain-text attribution to users when useful (for example: `Source: Wikily`, `Source: OnceHumanDB`, `Source: Once Human Official`).
- Do not add outbound source links or clickable link-backs in the Dead Signal UI.

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
