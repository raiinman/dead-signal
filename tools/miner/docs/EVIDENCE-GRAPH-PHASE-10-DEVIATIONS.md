# Evidence Graph Phase 10 — Deviations

Phase 10 promotes Deviations into a first-class typed Evidence Graph domain without treating display names, community catalog rows, or unresolved raw IDs as proof.

## Identity

- Canonical Deviation identity is the exact source record ID from `game_common/data/deviation_base_data.json`.
- Generalized canonical IDs use `ds-dev-<source-id>`.
- Display names are browse aliases only.
- Multiple source IDs with the same display name remain separate variants.
- A bare display name is never accepted by `DeviationAdapter.graph()` as identity proof.

The searchable registry indexes exact normalized variants directly from `published/data/deviations.json`. It does not require the compact `published/web/deviations.json` projection.

## Supported claims

### `deviation.exact_identity`

PROVEN from the exact `deviation_base_data` source record. Type code, unit ID/type, and collection value are preserved as source metadata but are not promoted into unrelated typed edges.

### `deviation.variant_family`

PROVEN as a browse grouping only. Same-name source variants are returned together in family evidence, while the exact source ID remains canonical identity.

### `deviation.abilities`

- PROVEN when `deviation_base_data.skill_ids` resolves to exact `deviation_skills_data` source IDs.
- PARTIAL when only embedded player-facing skill text exists without an exact skill ID owner.
- UNRESOLVED when neither lane yields an ability owner.

Only exact skill-ID ownership creates a graph edge.

### `deviation.containment`

Preserves the exact containment fields already normalized from `deviation_base_data`, including base, maximum, work threshold, and recovery values when present.

### `deviation.mood_power`

Preserves mood, temperature, quality coefficients, power coefficients, and balance coefficients directly from the source record. Phase 10 does not invent formulas beyond those stored values.

### `deviation.trait_ownership`

Raw `territory_effects` and `meme_ids` are retained as evidence, but remain PARTIAL until their typed player-facing definition owners are traced. Raw scalar equality is never enough to create a trait edge.

### `deviation.acquisition`

UNRESOLVED until an exact vendor/drop/reward/acquisition owner is traced from installed-game data. Community acquisition descriptions and localized prose do not become PROVEN relationships by themselves.

### `deviation.scenario_availability`

UNRESOLVED until an exact scenario/season owner is traced. `meme_ids` are explicitly not treated as scenario proof.

### `deviation.artwork`

PROVEN only when a source-derived Deviation artwork reference exists; otherwise UNRESOLVED.

## False-proof controls

Phase 10 regression tests require:

- same-name source variants remain distinct exact entities;
- adapter lookup by display name fails closed;
- exact skill IDs may create ability edges;
- embedded skill text without IDs remains PARTIAL;
- raw territory/meme IDs cannot become player-facing trait proof;
- meme IDs cannot prove scenario availability;
- acquisition remains UNRESOLVED without a typed owner;
- registry search may return multiple same-name variants without collapsing them;
- presentation retains `publication_authority: False`.

## Publication boundary

`DeviationAdapter` has no publication authority. The existing compact web contract may group records by display name for browsing, but that grouping remains presentation-only and cannot alter canonical source identity.

## Phase 10 result

The generalized Evidence Graph can now search and trace Deviation source variants with exact identity, exact skill ownership where available, source-preserved containment/mood/power data, explicit variant families, and named unresolved gaps for traits, acquisition, and scenario availability.
