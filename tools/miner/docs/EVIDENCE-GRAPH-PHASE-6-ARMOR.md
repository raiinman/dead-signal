# Evidence Graph Phase 6 — Armor and Set Graph

Phase 6 promotes armor pieces and armor sets into separate typed Evidence Graph domains.

## Source boundary

Canonical armor evidence is projected from the installed-game-derived armor pipeline:

- `game_common/data/equip_data.json` — exact equipment owner, slot, suit membership, tier/data level, blueprint owner.
- `game_common/data/item_data.json` — player-facing item identity, quality, durability, weight, artwork lineage.
- `game_common/data/equip_origin_data.json` — exact tier base-attribute owners.
- `game_common/data/suit_data.json` — exact set identity, activation thresholds, attribute/buff owners.
- `game_common/data/equip_blueprint_data.json` and `game_common/data/forge_data.json` — crafting recipe lineage.
- `game_common/data/equip_blueprint_attr_data.json` — Key Armor fixed-skill owner.
- `game_common/data/passive_skill_data.json` — fixed-skill → buff owner.
- `game_common/data/buff_level_data.json` — Key Armor player-facing effect lineage.
- `published/web/armor.json` — compact source-derived identity projection consumed by the adapters.

No game bytecode is executed.

## Two entity types

Phase 6 registers:

- `armor` — one exact armor piece identity.
- `armor_set` — one exact suit identity.

A set is not modeled as an armor piece. Key Armor is modeled as standalone `armor`, not as an inferred one-piece set.

## Reused blueprint IDs

Blueprint IDs are not globally unique across named armor suit variants. Existing public armor projection therefore uses:

`ds-a-<suit_id>-<blueprint_id>`

for set pieces.

A bare reused blueprint ID is an ambiguous lookup and fails closed. The adapter never chooses a suit by name, rarity, slot, or visual similarity.

Key Armor uses its standalone canonical identity:

`ds-ka-<blueprint_id>`

## Armor-piece claims

The `ArmorAdapter` exposes:

- `armor.exact_identity`
- `armor.equipment_owner`
- `armor.slot`
- `armor.rarity`
- `armor.base_attributes`
- `armor.crafting`
- `armor.acquisition`
- `armor.artwork`
- `armor.set_membership`
- `armor.key_armor_effect`

### Crafting versus acquisition

An exact current forge recipe proves a crafting path. It does not prove that crafting is the only acquisition route.

Therefore:

- exact recipe series → `armor.crafting = PROVEN`;
- the same evidence can make `armor.acquisition = PARTIAL` while non-crafting acquisition channels remain unknown;
- missing recipe evidence remains `UNRESOLVED`, never `non-craftable`.

## Set membership

Set membership requires the exact `equip_data.suit_id` lineage represented by the normalized set piece.

Key Armor is normalized from canonical standalone equipment with no suit owner. For that explicit class, set membership is `NOT APPLICABLE` rather than guessed from names or effects.

## Key Armor effect chain

A Key Armor effect is `PROVEN` only when the projected installed-game chain contains:

`armor blueprint → fixed_skill_code → passive skill → buff_id → player-facing buff text`

A missing link remains `UNRESOLVED`.

Shared `fixed_skill_code`, `buff_id`, effect text, artwork, or names do not merge two Key Armor identities.

## Armor-set claims

The `ArmorSetAdapter` exposes:

- `armor_set.exact_identity`
- `armor_set.pieces`
- `armor_set.activation_thresholds`
- `armor_set.bonus_owners`
- `armor_set.key_armor_membership`

Activation thresholds come from the exact `suit_data.affix_need_num_list` projection. They are never inferred from display order.

A set bonus is fully owner-proven when the normalized suit record carries an exact attribute owner and/or buff owner. Description text by itself is presentation evidence, not effect ownership; such a bonus remains `PARTIAL`.

Key Armor membership on an armor set is explicitly `NOT APPLICABLE`; standalone Key Armor is not attached to a suit through name, slot, skill, buff, or shared localization handles.

## Registry behavior

The Phase 3 entity registry now flattens `published/web/armor.json` in two typed ways:

- set pieces + Key Armor → `armor`;
- suit records → `armor_set`.

Tier item IDs are searchable aliases for the exact armor piece. Reused blueprint IDs may return multiple search results; direct graph routing still requires an exact canonical identity when ambiguous.

## False-proof controls

Phase 6 regression tests require:

- two suit pieces sharing one blueprint ID remain distinct;
- bare reused blueprint lookup fails as ambiguous;
- standalone Key Armor stays out of suit membership;
- two Key Armor records sharing skill/buff handles remain distinct;
- conflicting tier blueprint ownership becomes `CONFLICT`;
- description-only set bonuses do not become owner-proven;
- exact suit thresholds and piece membership remain source-owned;
- generalized registry search routes both `armor` and `armor_set` correctly.

## Compatibility protection

- Weapons v1 is unchanged.
- Attachment and Calibration graph behavior is unchanged.
- No adapter has publication authority.
- Generated Miner outputs and `tools/miner.zip` are untouched.

Phase 6 closes only after the full Windows `Test Miner source` workflow is green.
