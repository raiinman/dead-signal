# Evidence Graph Phase 13 — Generalized Miner Interface

Phase 13 makes the generalized Evidence Graph the primary Miner intelligence surface without changing evidence truth, adapter semantics, or publication authority.

## Navigation

The desktop shell is reorganized as:

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

The existing Run Pipeline, Explore Data/Data Intelligence, and Publish & Verify workspaces remain the operational implementations beneath the renamed Operations routes. Phase 13 does not rewrite mining, resolver, updater, or publication logic.

## Overview

Overview presents:

- registered entity totals by typed domain;
- persisted claim-state totals from the Phase 11 dependency store;
- invalidated-claim count;
- Phase 12 review-item count;
- high-impact shared missing owners/reasons;
- affected website-page keys;
- snapshot change diagnostics when available.

Overview is informational only. It cannot assign proof or publish.

## Evidence Graph

The Phase 3 registry selector remains the discovery surface, so adapter types are dynamic rather than hard-coded.

Every registered entity routes through:

```text
DeadSignalGeneralizedGraph.entity_graph(entity_type, canonical_id)
```

There is no weapon-only renderer guard.

The generalized trace surface exposes:

- exact entity identity and source owners;
- deterministic claims and states;
- typed edges and destinations;
- Phase 12 requirement-by-requirement assessment;
- claim evidence, missing requirements, conflicts, and dependencies;
- exact-record navigation targets;
- dependency/consumer-search leads;
- recomputation;
- direct Review Queue navigation.

The protected Weapons v1 evidence engine remains intact beneath `WeaponAdapter`; Phase 13 changes presentation, not Weapons v1 proof semantics.

## Review Queue

The queue consumes Phase 12 deterministic review output and Phase 11 invalidation priority.

Capabilities surfaced in the Miner include:

- filter by typed domain;
- launch-impact ordering;
- shared missing-owner grouping;
- claim assessment/provenance detail;
- direct jump to the exact entity in Evidence Graph;
- attributable manual `VERIFIED` / `CONFLICT` overlays;
- removal of manual review overlays.

Manual review still has no deterministic proof override and no publication authority.

## Packaging

`dead_signal_generalized_workspace` and `dead_signal_phase13_shell` are included in the Miner self-test import set so packaged builds fail closed if either module is omitted.

## Safety and compatibility

Phase 13 does not:

- change adapter contracts;
- assign `PROVEN`;
- create evidence edges;
- change Phase 11 invalidation state;
- publish automatically;
- modify installed game data;
- modify generated evidence datasets;
- touch `tools/miner.zip`.

## Exit criteria

Phase 13 is complete when:

1. Overview, Evidence Graph, and Review Queue are first-class Intelligence routes.
2. Run Pipeline, Resolvers, Publication, and Reports are first-class Operations routes.
3. Every registered entity can be selected and traced through its typed adapter without a weapon-only guard.
4. Claim assessment, recomputation, review, and exact provenance/navigation targets are visible from the Evidence Graph.
5. A Review Queue item can jump directly to the exact entity trace.
6. Any entity trace is reachable from the Intelligence navigation within two user actions.
7. The full source and packaged validation gates remain green.
