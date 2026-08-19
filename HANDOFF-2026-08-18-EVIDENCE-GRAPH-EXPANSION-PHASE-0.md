# Dead Signal — Evidence Graph Expansion Phase 0 Complete

Completed 2026-08-18 America/Phoenix.

## Outcome

Phase 0 of `EVIDENCE-GRAPH-EXPANSION-WORK-PLAN.md` is complete. The current Weapons v1 Evidence Graph is frozen as the compatibility reference before generalized schemas and domain adapters begin.

No publication schema, website data, Miner output, or player-facing relationship was changed.

## Delivered

- `tools/miner/src/dead_signal_graph_baseline.py`
  - validates the legacy weapon graph contract;
  - rejects missing roots, missing policy statements, invalid counts, and non-authoritative edges;
  - produces deterministic canonical graph hashes;
  - measures representative traces without treating performance as a semantic gate.
- `tools/miner/baselines/weapon-evidence-graph-phase-0.json`
  - captures the current real-snapshot observation;
  - contains five required cohorts;
  - records node, edge, occurrence, time, hash-prefix, and artifact-size observations.
- `tools/miner/docs/EVIDENCE-GRAPH-COMPATIBILITY.md`
  - defines the protected Weapons v1 payload and Phase 1 migration rule.
- `tools/miner/tests/test_evidence_graph_phase0_baseline.py`
  - adds five compatibility and fail-closed tests.

## Representative controls

- SOCR - The Last Valor — standard ranged;
- Baseball Bat — melee;
- Morgan — nonstandard blueprint;
- Ultra Force — special equipped;
- AKM — no fixed-skill reference.

These are exact regression subjects, not hard-coded corpus membership rules.

## Real-snapshot baseline

Observed from `C:\Users\mikea\Documents\Dead Signal Miner`:

- 130 published weapon identities;
- `weapons.json`: 20,361,695 bytes;
- `relationship-graph.json`: 332,132 bytes;
- `reference-tracer.sqlite`: 227,663,872 bytes;
- five representative traces complete successfully;
- individual observed trace time in repeated validation: approximately 220–420 ms.

Timing, counts, hashes, and sizes are snapshot observations. They are not universal constants and are not used as CI pass thresholds.

## Validation

- five new Phase 0 tests pass;
- complete Miner suite: 213 tests pass;
- real local five-cohort baseline measurement passes;
- all exact graph edges remain authoritative;
- `tools/miner.zip` remains untouched and untracked.

## Phase 1 boundary

Proceed next with Phase 1: generalized entity, claim, edge, and assessment contracts.

Requirements:

- legacy `weapon_graph(identity)` remains compatible;
- new generalized entry points must be versioned;
- every edge retains provenance;
- no adapter work begins until the shared contracts validate fail-closed;
- incompatible changes require explicit schema migration notes and approval.

No new Miner release was required for Phase 0 because it adds development baselines and tests without changing the packaged UI or runtime behavior.
