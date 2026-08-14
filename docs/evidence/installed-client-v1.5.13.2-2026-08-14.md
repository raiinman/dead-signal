# Installed-client proof — Miner v1.5.13.2 — 2026-08-14

This note records the fresh installed Once Human snapshot delivered as `data(6).zip`. The archive itself is not stored in Git.

## Archive identity

- Miner version: `1.5.13.2`
- Archive SHA-256: `fb7425d596b764d8d7630319e45554f86eddfc5ca8030fef5fd84a6b5d6a9385`
- Archive size: `27,613,301` bytes
- Miner validation: PASS
- Validation generated UTC: `2026-08-14T08:04:27.356562+00:00`
- Data-quality overall status: `PARTIAL`

## Compact browser contract hashes

| Contract | SHA-256 | Bytes | Current proof |
|---|---|---:|---|
| `web/weapons.json` | `5227d0120013c4de5fbb6395d1dcc2fa729f989b9758a8420a3af82f6917997f` | 13,097,472 | 120 weapons; evidence classifications present |
| `web/armor.json` | `23369d9fab8e637cea911adcd466c393a5bccd1c26b31697133c789bc07e136d` | 6,794,064 | 23 sets / 133 set pieces / 40 Key Armor / 173 pieces |
| `web/calibrations.json` | `3feb64ec3bdc807eedbfcdfe879ab9c8d7067a2c785b2f0ef3db29d85863bc71` | 1,272,827 | 94 current families; ready-current-system |
| `web/mods.json` | `fafc7fe6b3f097e0773ab2a2f75b520d03475e8d55349e520c39681212a66084` | 8,387,499 | 1,618 families / 1,618 variants; frame evidence complete |
| `web/attachments.json` | `ccbe15c1ed80b2602c156eecd0489e0fea210260fa08c150e4c4b5e66d9ac533` | 156,512 | 119 player attachments; 110 direct / 9 unresolved compatibility |
| `web/deviations.json` | `5d4bd8f6af97734f949da879eddc7b11a222e79bd376a98ea1ebdf29e289af5b` | 198,480 | 98 families / 160 variants / 60 multi-variant families |
| `web/cradles.json` | `cbf8f3e51e383e915bb2086a3f77e4cfa4d1ca234a3ade1d88a9ebec08fa10c7` | 144,768 | 120 families / 170 variants / 32 multi-variant families |

Additional report hashes:

- `reports/validation.json`: `de3ce25a31b26392146967cd1d3aba0792e25ea40d2fde2f9f6a70e3f98daa41`
- `reports/data-quality.json`: `59f63b94d512ac07e8f49552f2a1061ee47681da1dc201bb32323a04092d127d`
- `snapshot-manifest.json`: `a209b04c9e18d368a5cf4e7aca386103b1ab3b999efb28c841d2eec44ba5ea96`

## Weapon mechanic evidence

The v1.5.13.2 compact Weapons contract now separates previously generic missing-effect cases:

- `resolved-player-facing-effect`: **76**
- `exact-fixed-skill-record-missing`: **14**
- `no-fixed-skill-reference`: **30**
- `weapon_evidence_missing_exact_identity`: **0**

The 14 exact missing-skill records are:

| Weapon | Exact fixed skill |
|---|---|
| OIC-8 - Last Carnival | `WS2001` |
| SOCR - Sand Dancer | `WS1402` |
| MG4 - Sandstorm | `WS1601` |
| DE.50 - Goshawk | `WS1101` |
| G17 - Cash Only | `WS2001` |
| DBSG - Format | `WS15203` |
| HAMR - Hannya | `WS15502` |
| SN700 - Dark Snowflake | `WS1501` |
| SR2000 - Die Another Day | `WS14503` |
| SR2000 - Jungle Camouflage | `WS1001` |
| MPS7 - Chaos Domain | `WS15304` |
| MPS7 - Focus | `WS1301` |
| MPS7 - Urban Ninja | `WS1301` |
| R500 - Interfade | `WS2001` |

Exact-ID policy remains fail-closed. Similar `WS...` identifiers are research leads only and must never be promoted as matches.

## Short-description provenance

Weapon short-description evidence statuses:

- `no-short-description-handle`: **106**
- `translation-handle-resolves-consistently`: **14**

The fresh provenance layer proves that some unrelated player-facing weapons share the same installed `item_data.short_desc` source handle. Notably:

- Frozen Northern Pike
- Kukri
- The Fabled Masamune

all point to the same source short-description handle. Base/current English translation layers resolve that handle consistently, so the Kukri cross-wire is not explained by Dead Signal selecting the wrong English translation layer. The incorrect association exists at or before the installed item-data handle assignment. Dead Signal must continue withholding these suspect flavor descriptions from publication.

Other shared short-description handle groups observed in the current weapon corpus include:

- Baseball Bat / Metal Baseball Bat / Old Baseball Bat
- Camping Knife / Machete / Old Machete / Rusted Blade

Shared-handle evidence is diagnostic only; it does not authorize publishing the shared text for every item.

## Mod frame evidence

The v1.5.13.2 Mod compact contract reports:

- 1,618 Mod families
- 1,618 source variants
- 1,618 variants with complete frame evidence
- 0 unresolved frame-evidence variants
- 31 used frame codes in this snapshot
- 79 used sub-entry families
- evidence status: `proven-entry-identities-positional-level-mapping-unresolved`

The four ordered frame sub-entry identities are proven. Their positional mapping to `frame_lv_1..4` remains unproven and must stay fail-closed.

## Publication decision

This snapshot is the next canonical installed-client proof candidate. Production browser payloads must still be promoted using the repository's transactional all-seven materialization path. Do not hand-promote Weapons or Mods separately around the transaction.
