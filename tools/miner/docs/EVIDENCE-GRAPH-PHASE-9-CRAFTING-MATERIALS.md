# Evidence Graph Phase 9 — Crafting + Materials

Phase 9 promotes crafting recipes and their consumed materials into first-class typed Evidence Graph domains.

## Why a new normalized layer was required

Weapons and Armor already carried useful recipe fragments, but there was no canonical cross-domain Crafting or Material dataset. Phase 9 therefore adds `normalize_crafting.py`, which reads the existing Base/Current table corpus and produces:

- `published/data/crafting.json`
- `published/data/materials.json`

This is a normalizer only. It does not mine archives, execute game bytecode, or publish website content.

## Recipe identity

A recipe is the exact `forge_data` record identity:

```text
forge_no + server_no
```

Tuple keys such as `(123, 222)` preserve both values. Simple legacy keys use server `0`; they are not silently promoted to server 222 or any other current value.

Canonical recipe IDs are:

```text
ds-recipe-<forge_no>-<server_no>
```

A bare `forge_no` may be accepted as a lookup alias only when it resolves to exactly one server variant. Multiple variants fail as ambiguous.

## Cost typing

`forge_data.cost_item_list` is not treated as one universal item-ID namespace.

Each cost ID is typed before a relationship is created:

1. exact `forge_choice_material_data.identity` group owner;
2. otherwise exact `item_data` item owner;
3. otherwise unresolved.

Choice-group identity wins when the same scalar also exists as an `item_data` row. Scalar equality alone never creates two meanings.

This is an explicit false-proof safeguard.

## Fixed materials

A fixed-material edge requires an exact cost entry whose ID resolves to `item_data` and does not resolve as a selectable group.

Recipe quantity is preserved directly from `cost_num_list`.

## Selectable material groups

A selectable group requires an exact `forge_choice_material_data.identity` owner.

Each option preserves:

- exact option `item_id`;
- base option quantity from `item_num`;
- recipe multiplier from `forge_data.cost_num_list`;
- resulting recipe quantity;
- source record IDs;
- material-effect text/type codes when present.

Group identity is separate from Material identity. A group is never published or indexed as if it were an item.

## Output identity and formula-map corroboration

`forge_data.item_no` is the direct recipe output owner.

`client_data/forge_formula_map_data.json:ITEM_NO_TO_FORGE_NO_MAP` is independent corroborating evidence. If the formula map points the same recipe identity at a different output item, the result is `CONFLICT`; neither source overwrites the other.

Missing formula-map corroboration remains `UNRESOLVED`. It does not invalidate the direct forge output owner.

## Currency and craft time

Currency uses the exact `forge_data.cost_money_no` reference plus its `money_material_data` owner when present.

Craft time preserves the exact `forge_data.seconds` value, including zero.

## Material identity

A Material is an exact `item_data` item ID that appears in a typed fixed recipe cost or as an option inside a typed selectable group.

Canonical IDs are:

```text
ds-material-<item_id>
```

The Material dataset reverse-projects:

- fixed recipe usage;
- selectable recipe usage;
- selectable group membership.

Only typed recipe relationships create those reverse links.

## Acquisition boundary

Localized `item_data.gain_path` is retained as useful player-facing evidence, but it is not promoted to a typed vendor/drop/reward relationship.

Therefore:

- gain-path text present → `material.acquisition = PARTIAL`;
- no typed acquisition owner → never `PROVEN`.

Later vendor/drop/reward adapters may promote this claim without changing Material identity.

## Adapter claims

### Recipe

- `recipe.exact_identity`
- `recipe.output_item`
- `recipe.formula_map_consistency`
- `recipe.fixed_materials`
- `recipe.selectable_material_groups`
- `recipe.currency_cost`
- `recipe.craft_time`

### Material

- `material.exact_identity`
- `material.recipe_usage`
- `material.choice_group_membership`
- `material.acquisition`
- `material.artwork`

## No global craftability claim

Phase 9 intentionally does not expose a generic `craftable = true/false` field.

Absence from this forge lane does not prove that an item cannot be crafted, transformed, rewarded, composed, season-created, or produced through another game system. Missing recipe evidence is not a non-craftability proof.

## Registry

`recipe` and `material` are registered generalized domains. The registry reads the evidence-layer `published/data/crafting.json` and `published/data/materials.json` directly; no compact website projection is required.

Search aliases are navigation only. Names never create evidence edges.

## Pipeline

The existing compatibility CLI stage already receives Base, Current, and Published paths. After its protected Attachment/Calibration helper completes and Phase 8 Cradle enrichment runs, Phase 9 invokes the pure crafting normalizer against the same extracted table corpus.

This keeps the imported `enrich()` helper backward-compatible while ensuring fresh full Miner runs create the Phase 9 evidence artifacts before final manifest publication.

## False-proof controls

Phase 9 tests cover:

- item ID / choice-group scalar collision;
- choice-group namespace taking precedence over accidental item equality;
- multiple server variants sharing one `forge_no`;
- bare forge lookup failing as ambiguous;
- formula-map output disagreement becoming `CONFLICT`;
- selectable option quantity × recipe multiplier preservation;
- reverse Material recipe usage from typed costs only;
- localized gain-path text staying `PARTIAL`, not proven acquisition;
- group IDs never entering the Material registry as item identities;
- Recipe and Material registry routing without compact web files.

## Publication boundary

`RecipeAdapter` and `MaterialAdapter` are evidence consumers only. They cannot publish website data.

Generated Miner output, raw game exports, local research databases, and `tools/miner.zip` remain outside source control.
