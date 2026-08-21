# Dead Signal — Evidence Graph Expansion Phase 3 Complete

Completed 2026-08-20 America/Phoenix.

## Outcome

Phase 3 of `EVIDENCE-GRAPH-EXPANSION-WORK-PLAN.md` is complete.

The generalized Evidence Graph now has a searchable, adapter-backed entity registry and the registry is exposed directly in the first-class Evidence Graph workspace.

Current canonical implementation commit before this documentation closeout:

- `720705f5ac26f1cc6e4b1a45b1820abf604d0629` — complete searchable entity registry UI

Phase 2 remains the typed-adapter boundary and Weapons v1 remains the protected compatibility reference.

## Delivered

Backend from the first Phase 3 merge:

- `tools/miner/src/dead_signal_entity_registry.py`
  - indexes source-derived entities only for registered adapters;
  - exact-ID and indexed-name search;
  - entity-type filtering;
  - unresolved-only filtering;
  - recent selections;
  - direct graph targets;
  - duplicate canonical identities fail closed;
  - aliases are search/navigation metadata only and never evidence proof.
- `tools/miner/src/dead_signal_generalized_graph.py`
  - exposes registry rebuild, search, exact registered-entity lookup, and recent-entity APIs.
- Phase 3 backend tests covering registry behavior.

UI closeout:

- `tools/miner/src/dead_signal_entity_selector.py`
  - entity-type selector;
  - exact-ID / indexed-name search field;
  - unresolved-only filter;
  - entity result selector;
  - recent-entity selector;
  - direct routing through registry `graph_target` values;
  - stale selection clears when a search returns zero matches;
  - future registered entity types fail closed if a renderer has not been enabled yet.
- `tools/miner/src/dead_signal_trace_workspace.py`
  - Evidence Graph title and registry controls are now first-class;
  - existing Weapons v1 graph canvas, evidence inspector, recomputation checks, and review queue are preserved;
  - the current renderer still handles the proven weapon domain only and does not masquerade future domains as weapons.
- `tools/miner/tests/test_evidence_graph_phase3_ui_registry.py`
  - headless selector-model tests for label parsing, entity types, name search, exact-ID search, unresolved filtering, and exact graph-target routing.

## Phase 3 contract now satisfied

The Evidence Graph workspace exposes:

- entity-type selection;
- exact-ID and indexed-name search;
- recent traces;
- unresolved-only filtering;
- direct registered-entity graph navigation.

Every indexed entity must belong to a registered typed adapter. Search aliases cannot establish graph proof.

Current registry population is weapon-backed because `WeaponAdapter` is the only completed domain adapter. Later adapters can extend the registry without changing registry search/routing code.

## Compatibility and evidence safety

Preserved:

- `DeadSignalEvidenceGraph.weapon_graph(identity)` legacy contract;
- Phase 0 Weapons v1 compatibility baseline;
- Phase 1 generalized contracts;
- Phase 2 typed adapter safeguards;
- fail-closed unknown domains;
- no fuzzy/name-similarity evidence joins;
- no adapter publication authority;
- no generated Miner output or raw snapshot changes;
- `tools/miner.zip` remains untouched.

## Validation boundary

Completed during implementation:

- integrated `dead_signal_trace_workspace.py` was syntax-compiled before publication;
- PR #6 was reviewed as a focused three-file UI/test diff;
- PR #6 was mergeable and squash-merged successfully;
- canonical main contains the Phase 3 UI integration commit `720705f5`.

Repository `test-miner.yml` is configured to run on pushes to `main`, but the currently available GitHub connector does not expose the resulting push-triggered run listing. Do not claim a green post-merge Actions run until its run/job result is independently observed.

## Next boundary — Phase 4

Proceed with the Attachment graph.

Attachment claims:

- attachment identity;
- accessory owner;
- slot type;
- compatible and incompatible weapons;
- unresolved relationships;
- stat modifiers;
- acquisition;
- artwork.

Phase 4 must introduce a typed `AttachmentAdapter`, register it with the generalized engine, and allow the existing Phase 3 registry to index/search attachments automatically. Forward and reverse weapon compatibility must agree and spelling/name resemblance must never create an edge.
