# Evidence Graph Phase 5 — Calibration Graph

Phase 5 promotes Calibration Blueprints into a first-class typed Evidence Graph domain while keeping current Calibration Blueprints separate from unresolved or legacy gear-calibration material.

## Canonical evidence lane

The current Calibration Blueprint lane is grounded in:

- `published/web/calibrations.json` — browse families with exact source variants preserved;
- `published/data/calibrations.json` — normalized exact calibration item/print fields;
- `game_common/data/item_data.json` — item identity, rarity, acquisition, artwork;
- `game_common/data/gun_correct_print_data.json` — current Calibration Blueprint style, weapon type selectors, raw range, affix IDs/weights, group, validity and season fields;
- `game_common/data/gun_correct_common_terms_data.json` — secondary-affix term bodies;
- `published/data/weapons.json` — weapon-side four-state calibration projection used for reverse consistency checks.

Browse family identity is not source-variant identity. The registry exposes exact variants as `ds-cal-var-<source id>` while retaining the family ID only as a search/browse alias.

## Current versus legacy rule

A current Calibration Blueprint requires an exact `gun_correct_print_data` owner and a valid record. Older retained normalized snapshots did not carry an explicit owner-state field, so the shared policy may recognize the owner only when at least one field populated exclusively from that print record is present.

An ownerless subtype-39 item is **UNRESOLVED**. It is never labeled `legacy` merely because no current owner was found.

Legacy gear calibration is not mixed into this adapter. A future legacy lane must identify its own exact owner/table contract.

## Shared four-state compatibility

`dead_signal_calibration_relations.calibration_weapon_relation()` is the single policy used by both weapon-side projection and the Calibration adapter.

States:

- `compatible`
- `incompatible`
- `unresolved`
- `not-applicable`

Rules:

1. Melee is explicitly `not-applicable`.
2. Non-current/owner-unresolved calibration material is `unresolved` for firearm compatibility.
3. Current Calibration Blueprints require both an exact weapon `weapon_type_code` and exact calibration `weapon_type_codes` derived from `gun_correct_print_data.weapon_type_lst`.
4. Equal codes prove compatibility; non-equal codes prove incompatibility only inside that exact typed lane.
5. Names, rarity, style names and family grouping never establish compatibility.

The weapon Build Lab projection no longer filters on the historical nonexistent `status == current` field. It uses the shared exact-owner predicate.

## Reverse graph

For a current Calibration Blueprint:

```text
Calibration variant
→ exact gun_correct_print_data owner
→ style owner
→ weapon_type_lst
→ compatible / incompatible / unresolved / not-applicable weapons
```

The adapter independently inverts each weapon's stored calibration lists. Any forward/reverse disagreement becomes `CONFLICT`; it is never repaired automatically.

## Claims

The adapter declares:

- `calibration.exact_identity`
- `calibration.style_owner`
- `calibration.weapon_types`
- `calibration.weapon_relationship`
- `calibration.compatibility_consistency`
- `calibration.rarity`
- `calibration.attack_range`
- `calibration.secondary_attribute_pool`
- `calibration.acquisition`
- `calibration.system_classification`

## Attack range boundary

The normalized source preserves `gun_correct_print_data.affix_val_range` and its numeric bounds. Existing Miner evidence explicitly marks those bounds as:

`range-proven-combat-application-under-investigation`

Therefore Phase 5 reports the numeric range but keeps `calibration.attack_range` **PARTIAL** until consumer tracing proves what combat quantity the range scales. The adapter does not rename a numeric range into a proven damage multiplier.

## Secondary attribute pool and weights

Affix IDs, raw affix term bodies and `affix_ids_weight` are preserved exactly when present.

- exact affix IDs + exact raw weights → pool claim may be `PROVEN`;
- exact affix IDs without exact weights → `PARTIAL`;
- no exact pool owner → `UNRESOLVED`.

The Evidence Graph does not normalize raw weights into probabilities and does not infer roll odds.

## Compatibility protection

- Weapons v1 remains unchanged.
- Attachment behavior remains unchanged.
- Adapters expose no publish method.
- Family grouping remains browse/search metadata only.
- `tools/miner.zip` and generated Miner outputs are untouched.

## Phase 5 exit criteria

Phase 5 closes only when:

- exact Calibration variants are registry-searchable;
- current/owner-unresolved classification is fail-closed;
- all current Blueprint-to-weapon results use the four-state policy;
- Calibration-to-weapon and weapon-to-Calibration results agree;
- a poisoned reverse relationship becomes `CONFLICT`;
- numeric `affix_val_range` semantics remain partial until consumer proof exists;
- raw affix weights are preserved without inferred probabilities;
- the full Windows Miner workflow is green.
