# Evidence Graph Phase 15 — False-Proof Benchmark

Phase 15 turns the anti-guessing rules accumulated through Phases 0–14 into one cross-domain release benchmark.

## Primary metric

```text
False PROVEN results = 0
```

The benchmark does not assign evidence state and does not repair adapters. It consumes explicit regression observations and fails closed when an adversarial case is absent or incorrectly promoted.

## Required adversarial scenarios

Every registered adapter domain is covered by the same twelve scenario classes:

1. equal scalar in an unrelated table;
2. same name with a different owner;
3. missing owner;
4. stale Base evidence;
5. conflicting Current records;
6. shared translation handle;
7. inactive legacy record;
8. wrong subtype;
9. unresolved named-model wording;
10. removed dependency;
11. valid `NOT APPLICABLE` relationship;
12. partial chain with a missing consumer.

The matrix size is derived from the registered adapter set. With the current ten domains this produces 120 required domain/scenario cases. The benchmark does not hard-code 120 as a corpus constant.

## Registered domains

The current generalized graph registers:

- weapon;
- attachment;
- calibration;
- armor;
- armor_set;
- mod;
- cradle;
- recipe;
- material;
- deviation.

New adapter types automatically increase the required benchmark matrix.

## What the benchmark verifies

For every observation the benchmark checks:

- the scenario exists;
- the domain is registered;
- the state is one of the scenario's allowed fail-closed states;
- an adversarial result is never `PROVEN`;
- non-`NOT APPLICABLE` results name an actionable missing requirement;
- provenance is present;
- per-case runtime stays within the Phase-15 safety bound;
- duplicate domain/scenario rows fail closed;
- every required domain/scenario pair is present;
- ordering is deterministic.

`conflicting-current-records` must resolve to `CONFLICT`.

`valid-not-applicable-relationship` must resolve to `NOT APPLICABLE` and is not treated as missing evidence.

## Adapter contract audit

Phase 15 also audits the actual registered adapter contracts. It fails if an adapter:

- uses a generic/bare identity seed;
- exposes a bare generic outbound field;
- leaves a collision-prone outbound field without a typed destination;
- fails its own `AdapterContract.validate()` checks;
- exposes a callable `publish` method.

This reinforces the separation between evidence resolution and Phase-14 publication.

## Behavioral regression sources

The benchmark records the existing domain-level regression suites as the behavioral probes beneath the cross-domain metric. Examples include:

- Weapons: schema-trace owner policy, typed-seed locality, dependency invalidation;
- Attachments: Phase-4 typed attachment and relationship tests;
- Calibrations: Phase-5 current/legacy and compatibility tests;
- Armor/sets: Phase-6 reused-blueprint, shared-handle, conflict and provenance tests;
- Mods: Phase-7 identity/frame/entry false-proof tests;
- Cradles: Phase-8 active/inactive, selector, applicability and conflict tests;
- Recipe/material: Phase-9 namespace collision, compound identity and choice-group tests;
- Deviations: Phase-10 same-name variant and raw-handle tests.

Phase 15 does not weaken or replace those tests. CI runs them together with the benchmark.

## Harness self-test

The Phase-15 test suite deliberately injects:

- one false `PROVEN` result;
- one missing matrix case;
- missing provenance;
- a missing actionable reason;
- the wrong state for a Current conflict;
- an over-budget case;
- reversed input ordering.

The first six must fail the benchmark. Reversed ordering must produce the same stable output ordering.

## Authority boundary

The benchmark has no publication authority and no manual-verification authority. A failure is a release blocker/research signal; it is never permission to rewrite evidence state.

## Exit criteria

Phase 15 closes only when:

- every registered domain is represented;
- all domain behavioral regression sources remain present;
- the complete required adversarial matrix passes;
- correct states, missing requirements and provenance are preserved;
- ordering is stable and runtime bounded;
- **false `PROVEN` results remain exactly zero** in the full Windows source gate.
