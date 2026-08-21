# Evidence Graph Phase 1 — Generalized Contracts

Phase 1 introduces a strict, versioned contract layer without changing the protected Weapons v1 `weapon_graph(identity)` payload.

## New entry point

`DeadSignalGeneralizedGraph.weapon_entity_graph(identity)`

This entry point projects the existing authoritative Weapons v1 graph into the generalized schema. The original legacy payload is preserved verbatim under `compatibility.legacy_payload` so the migration cannot silently drop Weapons v1 information.

## Generalized evidence states

The shared state vocabulary is:

- `PROVEN`
- `PARTIAL`
- `UNRESOLVED`
- `NOT APPLICABLE`
- `CONFLICT`

Legacy `VERIFIED` normalizes to `PROVEN`. Unknown state labels are rejected instead of guessed.

## Entity contract

Every entity contains:

- schema version;
- entity type;
- canonical ID;
- display name;
- classification;
- identity state;
- source-record references.

Entities may exist with an empty `source_records` list during migration, but that does not grant publication authority.

## Claim contract

Every claim contains:

- schema version;
- typed claim name;
- subject;
- deterministic result state;
- machine-readable requirements;
- evidence references;
- named missing requirements;
- conflicts;
- dependency fingerprints.

A `PROVEN` claim is invalid without evidence. A `PROVEN` claim is also invalid if it contains missing requirements or conflicts. A `PARTIAL` claim must state what is missing. A `CONFLICT` claim must contain conflict evidence.

## Edge contract

Every generalized edge must contain all of the following:

- source;
- destination;
- relationship type;
- source table;
- source record;
- selector or JSON pointer;
- layer;
- authority;
- evidence state;
- SHA-256 dependency fingerprint.

An edge missing any provenance field is rejected. No validator repairs or guesses incomplete provenance.

Exact reference-tracer occurrences retain the installed table, record, JSON pointer/selector, and layer. Legacy root-to-identity edges are explicitly labeled as migration provenance from the published weapon snapshot and are not misrepresented as newly discovered raw installed-game owners.

## Assessment contract

The graph-level assessment records:

- overall state;
- counts for every shared evidence state;
- missing requirements;
- conflicts.

Assessment is deterministic and derived from claims. It is not an AI confidence score.

## Dependency fingerprints

Each edge receives a stable SHA-256 fingerprint over its endpoints, relationship, provenance, selector, layer, and authority. This creates the Phase 1 foundation for later dependency invalidation without implementing Phase 11 early.

## Compatibility rule

`DeadSignalEvidenceGraph.weapon_graph(identity)` remains unchanged and continues to return `dead-signal-evidence-graph` schema version 5. Phase 1 adds a separate generalized facade rather than silently changing `.64` runtime behavior.

Domain adapters are intentionally not part of Phase 1. Adapter work begins only after these contracts are accepted and validated fail-closed.
