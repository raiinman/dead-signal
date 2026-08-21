# Evidence Graph Phase 14 — Publication Integration

## Purpose

Phase 14 separates deterministic evidence truth from website publication policy.
A claim being `PROVEN` does not automatically make a website field publishable.
Every evidence-backed player-facing field must have an explicit publication
contract and must pass that contract before a claim-backed projector emits a
value.

## Contract

Each registered field declares:

- website field key;
- accepted claim type;
- minimum deterministic state;
- required evidence requirements;
- conflict policy;
- absence policy;
- `NOT APPLICABLE` policy;
- projection function name.

Unknown fields fail closed. There is no generic semantic publication fallback.

## State policy

- `PROVEN`: eligible only if the field contract also closes its declared evidence requirements.
- `PARTIAL`: blocked.
- `UNRESOLVED`: blocked.
- `CONFLICT`: blocked.
- `NOT APPLICABLE`: never interpreted as missing; a field contract must explicitly publish, omit, or block it.

A claim with a `PROVEN` result but missing/conflicting evidence is blocked.
A claim of the wrong type is blocked.
A missing claim is omitted or blocked according to the field contract; no value is fabricated.

## Lean projector boundary

`dead_signal_publication_contracts.lean_claim()` strips research-graph bulk and
retains only claim type, result, requirements, evidence, missing/conflicts, and
dependencies. `project_field()` consumes that lean result and emits either:

- a value plus explicit publication decision/provenance; or
- `None` plus the exact blockers/absence decision.

Projectors must not consume whole research graphs.

## Snapshot audit

`dead_signal_publication_integration.PublicationIntegration` walks registered
adapter entities and writes a bounded claim-backed audit to:

`published/reports/evidence-publication-contracts.json`

Each audited field contains its registered contract, exact claim type/state,
publication decision, blockers, dependency provenance, and lean evidence.
The audit contains no authority to alter deterministic proof.

## Existing compact publisher boundary

Phase 14 deliberately does not silently rewrite existing compact website datasets.
Those contracts predate the generalized Evidence Graph and are preserved for
backward compatibility until an explicit projector migration is reviewed.

From Phase 14 forward, any new evidence-backed website semantic field must be
registered here first. Migrating an existing field to claim-backed publication is
an explicit reviewed code change, never a side effect of a graph becoming `PROVEN`.

This preserves the rule:

`PROVEN != automatically published`

## Safeguards

- no adapter publishes directly;
- manual Phase 12 review never satisfies deterministic `PROVEN`;
- no AI action can assign publishability;
- no name similarity or scalar collision enters a publication decision;
- unregistered semantic fields are blocked;
- a blocked decision carries no projected value;
- `NOT APPLICABLE` remains distinct from missing evidence;
- claim dependencies/provenance travel with every publishable decision;
- existing public payload changes require explicit projector code changes.

## Regression coverage

`test_evidence_graph_phase14_publication.py` covers:

- unique field contracts;
- `PROVEN` plus required evidence;
- `PROVEN` without contract evidence;
- `PARTIAL`, `UNRESOLVED`, and `CONFLICT` blocking;
- conflicts hidden behind a `PROVEN` label;
- wrong claim type;
- unregistered fields;
- missing claims;
- explicit `NOT APPLICABLE`;
- blocked-value suppression;
- claim/provenance attribution in snapshot audits.

## Exit criteria

Phase 14 is complete when:

1. evidence-backed website fields have explicit registered policy;
2. claim-backed projectors consume lean claim results only;
3. every projected field carries its claim and provenance;
4. insufficient/conflicting states cannot publish silently;
5. publication migration remains an explicit reviewed code change.
