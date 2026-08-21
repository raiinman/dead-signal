# Evidence Graph Phase 11 — Dependency Invalidation

Phase 11 makes generalized claim proof snapshot-aware.

## Chain

```text
dependency file fingerprint
→ persisted claim dependency
→ dirty-claim plan
→ claim recomputation
→ review queue
→ affected website page key
```

## Persistent state

`catalogs/dead-signal-claim-dependencies.json` stores current claim results, exact declared dependencies, effective dependency fingerprints, claim fingerprints, affected page keys, and bounded proof history.

`reports/claim-invalidation.json` contains the current invalidation/review diagnostics.

Historical `PROVEN` results are audit history only. They are never treated as current proof after an owning dependency changes or disappears.

## Base / Current semantics

Current is a patch layer. Dependency lookup therefore uses:

1. Current table when present;
2. Base table when Current is patch-absent;
3. normalized/published evidence only for dependencies that explicitly live there.

Patch absence alone cannot invalidate a Base-backed claim.

Wildcard dependency declarations are hashed as an ordered set of exact matching files.

## Claim-scoped recomputation

`DependencyInvalidationStore.invalidation_plan()` compares persisted dependency fingerprints to the effective current snapshot before recomputation. It returns only dirty claim keys/entities plus affected website page keys.

`evaluate(..., full_snapshot=False)` updates only supplied recomputed claims. Unchanged sibling claims remain untouched. If a dirty claim no longer resolves, its exact key is passed through `removed_claim_keys`; it is removed from current proof and queued for review as `UNRESOLVED`.

A full snapshot can still be persisted with `full_snapshot=True`, which also detects claims/entities that disappeared from the complete graph set.

## Review and site diagnostics

Every invalidated claim records:

- exact claim key;
- reason;
- changed dependencies;
- previous result;
- current result;
- affected page keys.

Default page keys are stable evidence identifiers (`entity_type:canonical_id`), not assumed production URLs. Phase 14 publication mapping may replace them with reviewed website field/page mappings.

## False-proof safeguards

- Current patch absence never means removed game evidence.
- Removed claim ownership cannot leave stale `PROVEN` current state.
- Claim evidence changing without a file hash change still invalidates the old claim fingerprint.
- Conflict recomputation is queued for review.
- History is bounded and cannot promote itself back into current proof.
- Invalidation never assigns `PROVEN`; only adapters recompute evidence state.

## Phase 11 exit criteria

Covered by `tests/test_evidence_graph_phase11_invalidation.py`:

- one changed source invalidates only dependent claims;
- unrelated claims remain untouched during selective recomputation;
- Base fallback prevents patch-absence false invalidation;
- removed evidence/claims cannot remain current `PROVEN`;
- conflicts enter the review queue;
- proof history remains historical;
- affected website page keys are emitted.
