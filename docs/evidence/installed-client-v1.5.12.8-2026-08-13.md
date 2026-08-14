# Installed-client proof — Dead Signal Miner v1.5.12.8

Date: 2026-08-13 (US/Pacific)

This note records a fresh Miner v1.5.12.8 output supplied by the user from their installed Once Human client. The uploaded archive itself is not stored in Git.

## Archive identity

- Uploaded archive SHA-256: `59a5164d223931963e4383bfb0cbc5439e2b47b457c7bfdb574f9dba0d3df743`
- Size: 27,291,055 bytes
- Miner validation report: PASS
- Miner data-quality overall status: PARTIAL because Weapons still contain unresolved effect/localization queues; Armor is READY.

## Compact web contract identities

| Contract | SHA-256 | Bytes | Proven current count |
| --- | --- | ---: | --- |
| `web/weapons.json` | `f5d525bd3fbbd86f70bd32cd42b0c27495f6271cdf16209c83918ffd19e2be14` | 12,977,244 | 120 weapons |
| `web/armor.json` | `857c8d63c3d9eeeb8d05808d95853c631e050754a3b36c75d86375fb7d911498` | 6,794,064 | 23 sets / 133 set pieces / 40 Key Armor / 173 pieces |
| `web/calibrations.json` | `b4a12f98d75cee1d14c69fe1b478e1605fde19111c729423b97524fdeb4e57b5` | 1,272,827 | 94 current families |
| `web/mods.json` | `57db33ca5eb64d8fcf58efc40446bedbd3783e146c5cc2b1e7ec4b7d81e65f76` | 3,390,045 | 1,618 Mod families |
| `web/attachments.json` | `87e86bf106f1b028f42eb9a8186529dd05abe9d1c5e7b842368745924494731a` | 156,512 | 119 player weapon attachments |
| `web/deviations.json` | `1543610bea58c6fa449aad783a3201512258efba629bb44b1936aa8ab59cecc9` | 198,480 | 98 display-name families / 160 source variants |
| `web/cradles.json` | `9a76c4d8efedbb0168a410c6de4cd792b794e6f7eb1bd3d42240fa91e47000fd` | 144,768 | 120 display-name families / 170 source variants |

Report hashes:

- `reports/validation.json`: `b0a1701df53a8cb3ac7a607c6effd1e165f72d2f1fdf78a8d81b8252bb8b21f4`
- `reports/data-quality.json`: `51f4e7b8055c2432ea1ba9d872f5d5a60679db28e7f8f8b6e953eb7be6f2bea3`

## Armor proof

- 23 Armor Sets.
- 133 set pieces.
- 40 Key Armor.
- 173 total player-facing Armor pieces.
- Exactly five Tier I-V rows per piece = **865 Tier rows**.
- 865 current crafting recipe rows.
- 15 previously missing stat rows are recovered.
- Two Blackstone recipe-output variant conflicts remain explicit and unresolved; they must not be rewritten as exact suit-variant crafting proof.
- Armor data-quality category status is READY.

## Calibration proof

The v1.5.12.8 float comparison repair is proven on the installed-client output:

- 94 current + 94 legacy normalized records.
- 94 compact current families.
- Rare 24 / Epic 35 / Legendary 35.
- 0 ambiguous family IDs.
- 0 secondary-pool failures.
- Variant status: `current-system-selected-from-shared-buff-identity-and-proven-main-plus-secondary-rolls`.
- Main roll remains D0102 / Weapon DMG.
- Exactly one secondary candidate is selected from four mined candidates; source weights remain `[200,200,200,200]` and are not asserted as probability percentages.

The fresh contract exposed a stale repository transactional materializer status gate. Fixed at commit `73bde75ff8f28b31853c87e2923a8e89ea557319`.

## Attachment proof

Exactly 119 player weapon-slot accessories:

- 110 direct localized installed-game compatibility texts.
- 9 unresolved blank-description records.
- No inference from direct English wording into guessed weapon IDs/classes.

## Deviation / Cradle proof

Fresh v1.5.12.8 output contains the new source-variant canonical identities:

- Deviations: 98 families / 160 source variants / 60 multi-variant families.
- Cradles: 120 families / 170 source variants / 32 multi-variant families.
- Source-variant canonical IDs are globally unique and match exact source IDs.
- Display-name family grouping remains separate from player-selectable source identity.

## Weapon star-axis correction discovered by this run

The fresh installed-client contract disproves the repository assumption that rarity always implies the exact maximum Blueprint-Star count.

Observed star-axis distribution:

- Common: 32 weapons with 3 stars.
- Rare: 25 weapons with 4 stars.
- Rare: **Metal Baseball Bat** with 3 stars.
- Epic: 26 weapons with 5 stars.
- Legendary: 36 weapons with 6 stars.

For every weapon:

1. `progression.blueprint_stars.semantic_status` is `validated-source-axis`;
2. the mined star rows form a contiguous `1..N` axis;
3. `N` does not exceed the rarity cap;
4. all five Tier × Star matrix rows exactly match that weapon's mined star axis.

Therefore rarity is an upper bound, not a universal exact star count. The fix is generic and evidence-driven; there is no Metal Baseball Bat special case.

Repository fixes:

- `9efde702380dd456695931de178ac3f47daf66e6` — transactional Weapons materializer validates the mined source star axis and uses rarity only as a cap.
- `7e5af6cfabbe6f7a69c07638347883389b0651c8` — browser Weapons guard uses the same rule.
- `ae0b01c2c81a126817dd16d0d5dcda390979ec1d` / `9bb3d28f9fe2e9457ed02addd5ee630bf3278df8` — executable browser/Python regressions include sub-cap Rare-star coverage.
- Site CI `31762139671` SUCCESS.

## Transaction decision

After the Calibration status-gate fix and mined Weapon star-axis fix, all seven fresh compact contracts satisfy the repository's strict validation semantics:

- Weapons: 120
- Armor: 173
- Calibrations: 94
- Mods: 1,618
- Attachments: 119
- Deviations: 98 families / 160 source variants
- Cradles: 120 families / 170 source variants

The remaining blocker is transport/materialization, not data validity: the fresh archive exists in the current assistant sandbox, while the large browser payloads are not directly available to the GitHub connector as repository files. Do not claim the seven production JS payloads are materialized until the transactional repository tool actually writes all seven together.
