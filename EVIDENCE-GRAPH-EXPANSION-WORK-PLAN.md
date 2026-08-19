# Dead Signal — Evidence Graph Expansion Work Plan

## Objective

Turn the weapon-specific Evidence Graph into a general Once Human evidence workstation covering attachments, calibrations, armor, mods, Cradles, crafting, materials, deviations, and later game systems.

The completed system must answer player-facing questions through exact installed-game evidence while preserving these distinct results:

- `PROVEN`
- `PARTIAL`
- `UNRESOLVED`
- `NOT APPLICABLE`
- `CONFLICT`

No fuzzy joins, spelling guesses, external catalog authority, AI-generated proof, or hard-coded corpus totals are permitted.

Phases are verification boundaries, not stopping points. Continue through the complete sequence unless a genuine evidence or authority blocker prevents progress.

## Phase 0 — Freeze the current graph baseline

Status: **COMPLETE** on 2026-08-18. See `HANDOFF-2026-08-18-EVIDENCE-GRAPH-EXPANSION-PHASE-0.md` and `tools/miner/docs/EVIDENCE-GRAPH-COMPATIBILITY.md`.

Tasks:

- Preserve Weapons v1 as the reference implementation.
- Add snapshot tests for a standard ranged weapon, melee weapon, nonstandard-blueprint weapon, special-equipped weapon, and unresolved effect owner.
- Record current performance and output sizes.
- Define backward compatibility for existing weapon graph payloads.
- Ensure `v1.5.14.64` behavior remains unchanged while internals are generalized.

Exit criteria:

- Existing weapon traces retain equivalent states and provenance after refactoring.

## Phase 1 — Generalized graph schema

Create common entity, claim, edge, and assessment contracts.

Entity contract:

```json
{
  "entity_type": "attachment",
  "canonical_id": "...",
  "name": "...",
  "classification": "...",
  "identity_state": "...",
  "source_records": []
}
```

Claim contract:

```json
{
  "claim_type": "attachment.weapon_compatibility",
  "subject": {},
  "result": "PROVEN",
  "requirements": [],
  "evidence": [],
  "missing": [],
  "conflicts": [],
  "dependencies": []
}
```

Every edge must carry its source and destination, relationship type, source table and record, selector or JSON pointer, layer, authority, state, and dependency fingerprint.

Tasks:

- Add schema versioning and validation.
- Centralize state normalization.
- Reject edges without provenance.
- Migrate Weapons without losing information.

Exit criteria:

- Weapons render through the generalized schema with no evidence regression.

## Phase 2 — Typed domain-adapter framework

Each domain adapter declares:

- identity seeds;
- canonical owner tables;
- allowed outbound fields;
- typed destination tables;
- collision-prone fields;
- blocked generic fields;
- terminal presentation fields;
- supported claims;
- applicability rules.

Target interface:

```python
class EvidenceDomainAdapter:
    entity_type: str

    def identify(...): ...
    def claims(...): ...
    def resolve_claim(...): ...
    def dependencies(...): ...
    def presentation(...): ...
```

Safeguards:

- Bare `id`, `no`, `code`, or equal scalar values cannot establish an edge.
- Collision-prone IDs require explicit destination tables.
- Name similarity may create a discovery lead but never a graph edge.
- Requirements must be machine-readable.
- Adapters cannot publish directly.

Exit criteria:

- Weapons run through a registered `WeaponAdapter`.
- New domains require no core-engine modification.

## Phase 3 — Searchable entity registry

Build a unified registry for:

- weapons;
- attachments;
- calibrations;
- armor pieces;
- armor sets;
- mods;
- Cradle overrides;
- materials;
- recipes;
- deviations.

Registry fields include canonical ID, proven aliases, display name, entity type, category, source owner, identity state, artwork reference, and availability state.

UI requirements:

- entity-type selector;
- exact-ID and indexed-name search;
- recent traces;
- unresolved-only filter;
- direct graph-node navigation.

Exit criteria:

- Every registered entity selects the correct adapter.
- Search aliases are typed and source-proven.

## Phase 4 — Attachment graph

Claims:

- attachment identity;
- accessory owner;
- slot type;
- compatible and incompatible weapons;
- unresolved relationships;
- stat modifiers;
- acquisition;
- artwork.

Reverse graph:

```text
Attachment
→ accessory owner
→ slot
→ compatible / incompatible weapons
```

Exact named-model owners and explicit generic categories may be proven. Unresolved description wording stays unresolved. Spelling resemblance is ignored.

Exit criteria:

- All attachments produce four-state weapon relationships.
- Forward and reverse compatibility agree.

## Phase 5 — Calibration graph

Claims:

- identity and style owner;
- compatible weapon types and weapons;
- rarity;
- Attack range;
- secondary attribute pool;
- acquisition;
- current versus legacy classification.

Do not mix current Calibration Blueprints with legacy gear calibration or infer roll probabilities without exact weights.

Exit criteria:

- Calibration-to-weapon and weapon-to-calibration results agree.
- Every compatibility result uses the four-state model.

## Phase 6 — Armor and set graph

Armor-piece claims:

- item and equipment owner;
- armor slot;
- rarity and base attributes;
- crafting and acquisition;
- artwork and set membership.

Armor-set claims:

- set identity and pieces;
- activation thresholds;
- set bonuses and effect owners;
- Key Armor membership and effects.

Test reused blueprint IDs, pieces without sets, Key Armor ownership, and shared handles.

Exit criteria:

- Every published armor piece has exact slot and membership states.
- Set activation claims name exact owners and thresholds.

## Phase 7 — Mod 2.0 graph

Claims:

- mod identity and slot compatibility;
- family and main attribute;
- fixed sub-attributes;
- levels 1–17;
- Shiny classification;
- suffix/frame family;
- acquisition and effect ownership.

Keep current Mod 2.0, Shiny Mods, suffix families, and legacy randomly rolled mods explicitly separated.

Exit criteria:

- Current relationships are exact and typed.
- Legacy records are isolated.
- Every unresolved effect names its missing owner or consumer.

## Phase 8 — Cradle graph

Claims:

- Cradle identity and slot;
- effect owner;
- positive, negative, and unresolved applicability;
- scenario availability;
- artwork.

Reuse the exact 87-active-Cradle corpus. Prevent inactive legacy leakage and preserve unresolved scenario activation.

Exit criteria:

- Weapon-to-Cradle and Cradle-to-weapon results agree.
- Scenario state remains separately gated.

## Phase 9 — Crafting, recipes, and materials graph

Shared graph:

```text
Craftable entity
→ recipe/formula owner
→ material body
→ material requirements
→ currency
→ station
→ output item
```

Claims cover formula ownership, material-body availability, quantities, currency, tier, station, output, seasonal ownership, and acquisition.

Presentation must distinguish:

- exact owner plus body: complete recipe;
- exact owner with absent retained body: owner proven, materials unavailable;
- no owner: unresolved;
- missing recipe evidence: never proof of non-craftability.

Exit criteria:

- Weapons and armor use the shared graph.
- Ten melee seasonal owners remain accurate without fabricated bodies.
- Materials expose reverse `used by` relationships.

## Phase 10 — Deviation graph

Claims:

- identity;
- role and classification;
- skill owner;
- power or mood conditions;
- acquisition;
- scenario availability;
- artwork.

Runtime timing, procs, hidden multipliers, and scenario activation remain unresolved without exact owners and consumers.

Exit criteria:

- Identity and acquisition remain separate from runtime behavior.
- Every runtime claim declares an exact evidence requirement.

## Phase 11 — Dependency invalidation

Dependency chain:

```text
table fingerprint
→ source record
→ edge
→ claim
→ published field
→ affected website page
```

Tasks:

- Persist claim dependencies.
- Recompute only changed claims.
- Invalidate removed or conflicting evidence.
- Queue invalidated claims for review.
- Generate site-delta diagnostics and affected-page lists.
- Preserve proof history without treating it as current proof.

Exit criteria:

- One changed source invalidates only dependent claims.
- Removed evidence cannot leave stale `PROVEN` results.

## Phase 12 — Evidence assessment and review

Display every requirement individually:

```text
Attachment compatibility — PARTIAL

✓ Attachment identity
✓ Accessory owner
✓ Slot identity
✗ Typed weapon-model selector
```

Review queue capabilities:

- filter by domain;
- order by launch impact;
- group shared missing owners;
- open exact records and consumers;
- record or remove manual verification;
- record conflict;
- export bounded evidence bundles.

AI may summarize, explain, prioritize, and suggest exact identifiers. AI may not assign `PROVEN`, invent edges, override deterministic assessment, or publish automatically.

Exit criteria:

- Every unresolved claim gives an actionable reason.
- Manual reviews remain explicit, attributable, and removable.

## Phase 13 — Generalized Miner interface

Target navigation:

```text
INTELLIGENCE
  Overview
  Evidence Graph
  Review Queue

OPERATIONS
  Run Pipeline
  Resolvers
  Publication
  Reports
```

Evidence Graph includes entity type, search, trace status, graph, inspector, claim assessment, recomputation, review queue, and exact-record/consumer navigation.

Overview includes domain totals, evidence-state totals, invalidated claims, high-impact missing owners, affected website sections, and snapshot fingerprint.

Exit criteria:

- No major graph capability is buried in task hubs.
- Any entity trace is reachable within two actions.

## Phase 14 — Publication integration

Every website field declares:

- accepted claim type;
- minimum state;
- required evidence;
- conflict and absence policies;
- projection function;
- regression tests.

`PROVEN` is not automatic publication. `PARTIAL`, `UNRESOLVED`, and `CONFLICT` never publish silently. `NOT APPLICABLE` is not missing data. Projectors consume lean claim results, not research graphs.

Exit criteria:

- Every published field identifies its claim and provenance.
- Publication changes remain explicit, reviewed code changes.

## Phase 15 — False-proof benchmark

Adversarial cases for every adapter:

- equal scalar in an unrelated table;
- same name with a different owner;
- missing owner;
- stale base evidence;
- conflicting current records;
- shared translation handle;
- inactive legacy record;
- wrong subtype;
- unresolved named-model wording;
- removed dependency;
- valid not-applicable relationship;
- partial chain with a missing consumer.

Primary quality metric:

```text
False PROVEN results = 0
```

Also verify correct state, missing requirement, provenance, invalidation, bounded runtime, and stable ordering.

Exit criteria:

- All domain benchmarks pass.
- No name or scalar similarity can promote a claim.

## Phase 16 — Performance and release hardening

Tasks:

- Cache unchanged adapter results.
- Add bounded queries, cancellation, and progress.
- Keep the UI responsive.
- Measure cold/warm trace time and memory on the real snapshot.
- Run source, real-snapshot, Windows build, and packaged tests.
- Update handoffs.
- Publish the updater manifest last.

Release gates:

- complete source suite passes;
- real-snapshot smoke tests pass;
- packaged self-test passes;
- public ZIP hash and size match;
- manifest follows verified asset publication;
- `tools/miner.zip` remains untouched.

## Delivery sequence

1. Generalized schema and adapter framework.
2. Attachments.
3. Calibrations.
4. Armor and sets.
5. Mods.
6. Cradles.
7. Crafting and materials.
8. Deviations.
9. Dependency invalidation.
10. Generalized review and publication integration.
11. Full benchmark and performance hardening.

Continue through the entire sequence. Releases and phases are validation boundaries, not natural stopping points.

## Definition of complete

The expansion is complete when a user can select any supported game entity, ask a supported player-facing question, and receive:

- an exact identity;
- a typed evidence chain;
- source-table and record provenance;
- a deterministic evidence state;
- clearly named missing or conflicting evidence;
- reverse relationships;
- dependency-aware recomputation;
- a safe publication decision;
- zero false `PROVEN` results across the benchmark suite.
