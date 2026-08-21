# Evidence Graph Phase 2 — Typed Domain Adapters

Phase 2 separates domain knowledge from the generalized Evidence Graph engine.

## Core rule

The core registry routes `entity_type + identity` to a registered adapter. A new domain must be addable by registering an adapter rather than editing graph-engine routing code.

Adapters resolve evidence only. They do not publish website data and may not promote discovery or similarity into proof.

## Required adapter declarations

Every adapter declares:

- identity seeds;
- canonical owner tables;
- allowed outbound fields;
- typed destination tables;
- collision-prone fields;
- blocked generic fields;
- terminal presentation fields;
- supported claims;
- applicability rules.

## Safeguards

- Bare `id`, `no`, and `code` are forbidden as identity seeds or outbound proof fields.
- Collision-prone fields require explicit destination tables.
- Duplicate domain registrations fail closed.
- Unknown entity types fail closed.
- Adapter output is revalidated against the Phase 1 generalized graph contract.
- Adapters expose no publication method.
- Presentation output explicitly carries no publication authority.

## Weapons reference adapter

`WeaponAdapter` is the first registered adapter. It preserves the protected Weapons v1 trace, projects it through the Phase 1 generalized contract, and exposes entity, claims, dependencies, claim resolution, graph, and presentation methods.

The existing `DeadSignalGeneralizedGraph.weapon_entity_graph()` entry point remains available and now routes through the registry. The new generic entry point is:

```python
graph.entity_graph("weapon", identity)
```

## Compatibility

Phase 2 does not alter `DeadSignalEvidenceGraph.weapon_graph(identity)`. The Phase 0 Weapons v1 payload remains the compatibility reference, and Phase 1 remains the generalized schema boundary.

## Next boundary

Phase 3 may build the searchable entity registry on top of typed adapters. Domain expansion must not weaken these adapter safeguards.
