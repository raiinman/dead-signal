# Evidence Graph Phase 4 — Attachment Graph

Phase 4 promotes player weapon attachments from a weapon-side compatibility field into a first-class typed Evidence Graph domain.

## Evidence boundary

The Attachment adapter may prove only relationships supported by the Miner's installed-game-derived contracts. It does not infer weapon IDs from English model names and it has no publication authority.

Canonical source lineage:

- `published/web/attachments.json` — source-derived canonical browse identity.
- `game_common/data/gun_accessory_item_to_accessory_map_data.json` — exact item → accessory mapping.
- `game_common/data/gun_accessory_base_params_data.json` — exact accessory owner and typed compatibility selectors.
- `game_common/data/item_data.json` — item subtype / slot, acquisition text, and item artwork lineage.
- `game_common/data/gun_accessory_attr_data.json` — attachment affix/stat evidence.
- `published/data/weapons.json` — weapon-side four-state relationship projection used for reverse consistency checks.

## Shared four-state relationship policy

`dead_signal_attachment_relations.attachment_weapon_relation()` is the single relationship policy used by both the existing weapon Build Lab projection and the new Attachment adapter.

Allowed player-facing relationship states are:

- `compatible`
- `incompatible`
- `unresolved`
- `not-applicable`

The policy is fail-closed:

1. Melee is explicitly `not-applicable`.
2. Explicit `all weapons` installed wording proves compatibility.
3. Explicit generic weapon categories may prove compatibility and, when no named-model text is mixed in, incompatibility outside those categories.
4. Exact typed weapon item IDs may prove compatible/incompatible relationships.
5. Named-model wording without a typed owner remains `unresolved`.
6. Spelling similarity never establishes identity.

The historical `_attachment_relation()` entry point remains as a compatibility wrapper so existing weapon behavior is preserved.

## Reverse graph

For one attachment the graph walks:

`attachment → exact item/accessory owner → slot → weapon relationships`

The adapter recomputes each relationship with the shared policy and independently inverts the weapon-side compatibility lists. Every weapon must appear in exactly one reverse state and that state must equal the recomputed forward state.

Any disagreement becomes `CONFLICT`. The adapter never repairs, chooses, or averages conflicting directions.

## Claims

The typed adapter declares:

- `attachment.exact_identity`
- `attachment.accessory_owner`
- `attachment.slot_type`
- `attachment.weapon_relationship`
- `attachment.compatibility_consistency`
- `attachment.stat_modifiers`
- `attachment.acquisition`
- `attachment.artwork`

Missing modifier, acquisition, or artwork evidence remains `UNRESOLVED`; absence is not interpreted as proof of no modifier, no acquisition path, or no artwork.

## Registry integration

`AttachmentAdapter` is registered beside `WeaponAdapter` in `DeadSignalGeneralizedGraph`. The existing Phase 3 entity registry already knows the `published/web/attachments.json` source path, so attachment identities become searchable without changing registry core logic.

`DeadSignalGeneralizedGraph.attachment_entity_graph(identity)` is the versioned Phase 4 convenience entry point.

## Compatibility protection

- `DeadSignalEvidenceGraph.weapon_graph(identity)` remains unchanged.
- Weapons v1 payload remains unchanged.
- The generalized weapon adapter remains unchanged.
- Adapters expose no publish method.
- `tools/miner.zip` and generated Miner outputs are not part of this change.

## Phase 4 regression requirements

The Phase 4 tests require:

- a valid typed Attachment adapter contract;
- all four relationship states;
- exact canonical/accessory/item identity lookup;
- valid generalized Attachment graphs;
- forward/reverse agreement in the control fixture;
- an intentionally poisoned reverse relationship to become `CONFLICT`;
- named-model text without a typed owner to remain `UNRESOLVED`;
- stat, acquisition, and artwork claims to fail closed when evidence is absent;
- attachment registration/search through the generalized entity registry.

Phase 4 is complete only when the full Miner workflow is green and the forward/reverse invariant holds.
