# Installed-client proof — Miner v1.5.12.7 — 2026-08-13

Source: user-provided fresh ZIP generated from the installed Once Human client.

## Proven current snapshot

- Overall Miner validation: PASS.
- Weapons: 120.
- Armor: 23 sets / 133 set pieces / 40 Key Armor / 173 total pieces.
- Armor Gear Tier rows: 865 total = 173 pieces × 5 Gear Tiers.
- Armor Tier recovery: all 15 previously missing stat rows recovered; zero unresolved stat-row gaps.
- Blackstone Cold/Heat Tier III crafting-output conflicts remain unresolved acquisition identity and must not be rewritten.
- Attachments: 119 player weapon-slot records; 110 direct localized compatibility statements; 9 unresolved blank-description records.
- Mods: 1,618 source families.
- Deviations: 98 display-name families / 160 source variants.
- Cradles: 120 display-name families / 170 source variants.

## Calibration projector defect exposed by this run

The v1.5.12.7 compact current Calibration projector publishes 59 of the expected 94 families:

- Rare current families: 24 / 24 accepted.
- Epic current families: 0 / 35 accepted.
- Legendary current families: 35 / 35 accepted.
- Ambiguous families: 0.
- Secondary-pool failures: 35, exactly the Epic family count.

The installed normalized Epic Crit Rate maximum is the fractional value `0.14`. The projector scales fractional values to percentage points using binary floating-point arithmetic, producing `14.000000000000002`, then compares it with the proven `14.0` range endpoint using exact equality. This rejects every Epic secondary pool despite the installed-game data matching the proven range.

Replaying the exact uploaded corpus with tolerance-safe percentage comparison resolves the intended current system exactly:

- Current families: 94 / 94.
- Rare: 24.
- Epic: 35.
- Legendary: 35.
- Ambiguous: 0.
- Secondary-pool failures: 0.

Required repair: normalize binary-float representation noise or use tolerance-safe numeric comparison at the Calibration percentage comparison boundary. Do not change any mined roll range or weaken stat-ID/weight/range identity checks.

## Release implication

Do not ask for another installed-client run on v1.5.12.7. The next useful run should be after a verified Miner release containing:

1. the Calibration percentage-comparison repair; and
2. the already-tested Deviation/Cradle source-variant canonical identity changes.
