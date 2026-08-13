# Dead Signal — AI Continuity / Handoff

> Canonical current-state handoff. Read this file and `PROJECT-RULES.md` before changing anything.
>
> Updated **2026-08-13 — Day Shift + live preview**.

## Rules that must not drift

- Repo: `raiinman/dead-signal`; canonical branch: **`main` only**.
- Static database + Build Lab. **No WordPress runtime.**
- cPanel stays **copy-only**.
- Installed-game/Miner evidence is canonical; external databases are reference material only.
- Never invent mechanics, compatibility, recipes, proc behavior, DPS, rankings, or multiplier semantics.
- Landing page and Official Once Human X feed remain frozen unless there is a concrete bug.
- Unfinished categories remain `SOON` until their verified compact data is ready.

## Current checkpoint

Latest functional code HEAD before the handoff-only commits:

`16e08dc087ee3f5585b0bd5fb8f95596e1cac16d` — **Syntax-check global workstation shell**

Recent milestones:

- Weapons compact integrity and progression guards landed and are tested.
- Armor IDs are variant-aware: `ds-a-{suit_id}-{blueprint_id}`; materializer/audit/tests exist.
- Calibrations now use the real v2 current-system contract and a dedicated standalone renderer.
- Mods, Attachments, Deviations, and Cradle Overrides have prepared fail-closed database routes.
- Build Lab has canonical-category readiness, mapping, and variant guards so ambiguous data cannot silently replace the compatibility corpus.
- `eb1af76a791094ac91b6a3d1b81cb950ca3bb2fa` fails closed on invalid Weapons public data.
- `2b42a302cb5277a2ad0287a02b8af9b485242401` adds Build Lab contract-readiness gating.
- `fd7a7fe692f01617cc357caa03464a1e5bb81981` shows the current Miner version in the workstation shell.
- `16e08dc087ee3f5585b0bd5fb8f95596e1cac16d` adds shell syntax coverage.

## Live development preview

Review current `main` here:

`https://raw.githack.com/raiinman/dead-signal/main/preview/live/index.html`

Source hub: `preview/live/index.html` (`8f7650b01c949e4e122c21b19d11fe99b89804cb`).

The hub links to Landing, Weapons, Armor, Calibrations, Mods, Attachments, Deviations, Cradles, and the Build Lab shell. It is a low-traffic development preview, not production hosting.

**Build Lab preview boundary:** two old compatibility files remain hosting-installed only and are not in Git:

- `preview/build-lab/data/community-data.js`
- `preview/build-lab/app.js`

Therefore the Git preview proves the current shell/overlays, but not full picker/application behavior.

## Miner release boundary

Currently released Miner: **v1.5.12.2**.

SHA-256: `26a4d3013cd1eb991366da58f2d7714e1c4fc1a8f5edb46eb1549ed9cefa728d`.

The extended compact publisher and current Calibration projector were added after v1.5.12.2 shipped. **The next useful full-data release must therefore be v1.5.12.3 or later.** A new v1.5.12.2 mine is not sufficient for the full Day Shift migration.

`tools/miner/src/miner_entry.py` is the intended entrypoint for the next package and includes the extended compact publication step plus current Calibration projection. Do not bump VERSION until the Windows package path is proven to use it and the new publisher modules are included/tested.

After v1.5.12.3 is released, run it against the user's real Once Human install and inspect the fresh reports/contracts before materializing website data.

## Weapons

Last complete accessible snapshot proved:

- 120 weapons = 95 ranged + 25 melee;
- 600 Gear Tier rows;
- 545 Blueprint-Star rows;
- 2,725 legal Tier × Star combinations;
- 120/120 artwork;
- 95/95 firearm profiles resolved.

The player-facing Weapons vertical now has catalogue, details, Compare, legal Tier × Stars, Base Attack trace, proven static stats, acquisition/crafting evidence, provenance, and Build Lab handoff.

Remaining evidence queue from the last snapshot:

- 76/120 weapon effects resolved; 44 unresolved/absent, including 29 Common;
- unresolved Legendary examples include G17 — Cash Only, DBSG — Format, HAMR — Hannya, MPS7 — Chaos Domain;
- 14 missing Tier recipes, all melee; missing recipe evidence is **not** proof of non-craftable;
- `short_description` remains untrusted because of the observed Kukri/fish-text cross-wire.

## Armor & Sets

Armor stays `SOON` until a fresh v1.5.12.3+ snapshot proves collision-free real output. Set-centric route, audit, materializer, and identity tests are ready.

## Current Calibrations

Canonical current contract:

- schema `dead-signal-calibrations`;
- schema_version `2`;
- publication_status `ready-current-system` only at exactly 94 unambiguous current families;
- exactly one current variant per family; legacy rows remain audit-only.

Proven Weapon DMG ranges: Rare 18–25%, Epic 26–33%, Legendary 34–50%. My Gear uses exact numeric inputs; no sliders.

Do not reintroduce the obsolete `dead-signal-calibrations-current` schema.

## Mods / Attachments / Deviations / Cradles

- Mods: preserve mined variants; current Mod 2.0 player-selectable identity still needs fresh proof.
- Attachments: player weapon slots only — Sight, Muzzle, Tactical, Magazine. Last verified player-facing count was 119 = 30 / 36 / 36 / 17; raw 202 is not the picker target.
- Deviations / Cradles: preserve source variants. Variant guard blocks planner promotion when identity is ambiguous.

## Next exact sequence

1. Finish and prove the v1.5.12.3 Windows Miner package path.
2. Release v1.5.12.3 through the existing version-driven workflow.
3. Run v1.5.12.3 against the real Once Human install.
4. Audit/materialize Weapons and browser-verify the full vertical.
5. Use fresh evidence to investigate unresolved non-Common weapon effects, unsafe descriptions, and missing melee recipes.
6. Verify/materialize Armor.
7. Materialize/test the 94-family current Calibration contract.
8. Prove current Mod 2.0 variant identity.
9. Reconcile/materialize player-selectable Attachments and compatibility.
10. Resolve Deviation/Cradle variant semantics or provide explicit variant choice.
11. Remove old Build Lab compatibility pools only after canonical end-to-end verification.
12. After the core is broadly complete, audit current competitor UX/features and implement evidence-backed differentiators.

## Read first next session

`PROJECT-RULES.md`, `preview/live/index.html`, `tools/miner/release/latest.json`, `tools/miner/src/miner_entry.py`, `publish_extended_web_data.py`, `publish_current_calibrations.py`, `normalize_weapons.py`, `normalize_armor.py`, `tools/site/materialize-weapons-web.py`, `materialize-armor-web.py`, `materialize-extended-contract.py`, `database/calibrations/index.html`, `preview/build-lab/canonical-category-bridge.js`, `canonical-category-variant-guard.js`, `.github/workflows/test-site-tools.yml`, `.cpanel.yml`.
