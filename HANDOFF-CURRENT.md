# Dead Signal — Current Handoff

Current operational handoff:

- `HANDOFF-2026-08-21-EVIDENCE-GRAPH-PHASE-16.md`

Approved implementation plan:

- `EVIDENCE-GRAPH-EXPANSION-WORK-PLAN.md`

Read order for a new engineering/research session:

1. `PROJECT-RULES.md`
2. `AI-CONTINUITY.md`
3. `EVIDENCE-GRAPH-EXPANSION-WORK-PLAN.md`
4. `HANDOFF-2026-08-21-EVIDENCE-GRAPH-PHASE-16.md`
5. `HANDOFF-2026-08-18-NORMAL-GPT-EVIDENCE-FIRST-MINER.md`
6. `HANDOFF-2026-08-17-MINER-ARCHITECTURE-UPGRADE.md`
7. Historical phase/domain handoffs as needed for evidence rationale.

## Current state

The generalized Evidence Graph expansion has progressed through Phases 0–16 at the implementation level. Phase 16 is the current authority for runtime/release work.

Supported generalized domains are weapon, attachment, calibration, armor, armor_set, mod, cradle, recipe, material, and deviation.

Core boundaries remain unchanged:

- installed-game/Miner evidence is authoritative for mechanics and numbers;
- discovery, fuzzy/name similarity, scalar collisions, and external catalog wording never create proof;
- allowed states are PROVEN, PARTIAL, UNRESOLVED, NOT APPLICABLE, and CONFLICT;
- `PROVEN` is not automatic publication;
- Phase 14 publication contracts are fail-closed;
- Phase 15 release metric is zero false PROVEN results;
- cache/history/manual review have no deterministic proof or publication authority;
- never execute game bytecode;
- never publish raw research/full NeoX exports;
- never touch `tools/miner.zip`.

## Phase 16 release boundary

Do not call the expansion release-complete merely because Phase 16 code is merged. The final gates must be observed in order:

1. complete source suite;
2. real-snapshot smoke tests;
3. false-proof benchmark;
4. cold/warm trace and memory diagnostics;
5. Windows build;
6. packaged self-test;
7. public ZIP hash/size verification;
8. release asset verification;
9. updater manifest publication last.

The existing stable manifest remains `tools/miner/release/latest.json` until a newer ZIP has already passed all asset checks. Never publish a manifest ahead of its release asset.

For the detailed runtime cache, performance diagnostic, release audit, and closeout rules, use `HANDOFF-2026-08-21-EVIDENCE-GRAPH-PHASE-16.md`.
