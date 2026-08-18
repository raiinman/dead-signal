# Dead Signal — Weapons v1 Schema Lock

Date: 2026-08-18

Weapons v1 is launch-ready as a fail-closed installed-game contract. Its core identity model is locked; future core changes require new installed-game evidence and a deliberate schema revision. Known unresolved evidence remains visible and is not converted into guessed values.

## Locked identity boundary

- Source-derived identities remain 130: 117 standard-blueprint, 7 nonstandard-blueprint, and 6 special-equipped.
- Identity remains installed `item_data + equip_data`, with blueprint/progression as conditional enrichment.
- No fixed count, external catalog, fuzzy alias, or name-family inference is part of the schema.
- The public compact contract is `dead-signal-weapons` schema version 2 with `schema_contract.name = Weapons v1` and `status = locked`.
- The machine-readable contract is `tools/miner/docs/weapons-v1.schema.json`.

## Attachment compatibility

- 119 player weapon attachments.
- 110 have direct installed-game compatibility wording; 9 have exact accessory owners but no compatibility text or typed selector.
- Exact four-state relationship totals across 130 Weapons:
  - compatible: 4,009
  - incompatible: 5,106
  - unresolved: 3,618
  - not applicable: 2,737
- Generic category wording is projected only when explicit.
- Named-model wording remains literal unless a typed installed-data item selector exists. The current retained layer proves no such typed named-model alias owner; no spelling guesses were promoted.

## Calibration compatibility

- 94 current Calibration Blueprint variants are selectable; 94 legacy variants remain historical/nonselectable.
- Current variants carry exact `gun_correct_print_data.weapon_type` selectors, compared with each Weapon's exact prototype `weapon_type`.
- Exact relationship totals:
  - compatible: 1,285
  - incompatible: 8,773
  - unresolved: 0
  - not applicable: 2,162 (23 melee × 94 current calibrations)

## Selectable ammo

- Ammo selection uses the exact chain: weapon item → gun → `gun_base_params.accessory_seq_no` → slot 8 default accessory → bullet pack → ordered ammo items.
- The resolver now follows `accessory_seq_no` for variant guns instead of assuming the variant gun number owns its slot table.
- It retains exact legacy derived ammo accessory identities when present and falls back to `gun_accessory_item_to_accessory_map_data` only when that derived owner is absent (for example Nail Gun).
- 103 ranged Weapons have proven selectable option lists.
- 23 melee Weapons are not applicable.
- Four Bow / Crossbow Weapons remain unresolved: Compound Bow, Critical Pulse, Recurve Crossbow, and Rustic Crossbow. Their exact slot-8 default exists, but retained tables do not select one exact ordered bullet-pack owner. Do not collapse bow and crossbow packs by category or spelling.

## Acquisition and crafting presentation

- The ten melee formula owners remain exact seasonal owners in `blueprint_recipe_season_data`.
- Their referenced material bodies remain absent from retained `forge_data`.
- Public and site projections now expose recipe ownership per tier separately from material-body availability.
- Presentation state is `exact-owners-material-bodies-unavailable`, never a complete recipe and never a missing owner.

## Pipeline and verification

- `weapon_build_compatibility.py` runs immediately after the canonical combat resolver and before weapon math/configuration exports.
- It writes `published/reports/weapon-build-compatibility.json` and enriches normalized Weapons and Attachments.
- The compact web contract publishes Attachment, Calibration, Ammo, Cradle, and crafting boundaries directly.
- Full Miner suite: 206 tests passing.
- Stable Miner release boundary remains `v1.5.14.62`; no release was cut.
- `tools/miner.zip` remains protected and untouched.

## Post-lock policy

Do not change the Weapons v1 core identity or relationship shape for presentation convenience. New fields or state transitions require exact installed-game evidence, updated tests, and a schema-version decision. Scenario activation, missing forge material bodies, unresolved effect owners/text, the four bow/crossbow ammo pack owners, and the nine blank attachment compatibility owners remain honest evidence boundaries rather than launch blockers for the locked fail-closed schema.
