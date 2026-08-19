# Dead Signal — Normal GPT Handoff: Evidence-First Miner

Updated 2026-08-18 America/Phoenix after release of Miner `v1.5.14.64`.

## Start here

Work directly on canonical `main` in:

`C:\Users\mikea\Documents\Codex\2026-08-12\check-the-ai-continuity-on-girhub`

Canonical repository:

`https://github.com/raiinman/dead-signal`

Canonical generated Miner output:

`C:\Users\mikea\Documents\Dead Signal Miner`

The user's packaged Miner is updated through the stable GitHub updater. Do not edit generated output or the packaged installation as a substitute for canonical source changes.

## Current release

- stable Miner: `v1.5.14.64`
- release source commit: `a5ba1ec` — evidence-first Miner shell
- manifest-last commit: `350ec1b` — verified `.64` updater publication
- release workflow `32223541598`: success
- 213 source tests: pass after Evidence Graph Expansion Phase 0
- Windows build: pass
- packaged self-test: pass
- public ZIP checksum and byte size: verified
- updater manifest: published last

The `.63` release contained the new Weapon Identity Trace workspace, but it was nested inside Data Intelligence. The user correctly flagged that the main Miner still looked unchanged. `.64` fixes that product-level mistake.

## What the Miner does now

The Miner is evidence-first rather than pipeline-first:

- it launches directly into **Evidence Graph**;
- **Evidence Graph** is the first-class sidebar destination;
- **Run Pipeline** remains available as supporting infrastructure;
- the primary screen loads the source-derived 130-weapon corpus from the completed local snapshot;
- the default SOCR - The Last Valor trace runs asynchronously on launch;
- installations without a completed snapshot fail closed and direct the user to Run Pipeline.

The trace workspace displays:

- Item ID → Blueprint owner → Gun profile identity spine;
- Effect, Attachments, Calibration, Ammo, Crafting, and Progression branches;
- cyan `PROVEN`, red `UNRESOLVED`, and gray `NOT APPLICABLE` states;
- clickable Evidence Inspector with source table, source record, selector, layer, and provenance chain;
- automated recomputation checks;
- human-review queue for relationships missing an exact typed owner.

Primary implementation files:

- `tools/miner/src/dead_signal_miner.py`
- `tools/miner/src/dead_signal_trace_workspace.py`
- `tools/miner/src/dead_signal_intelligence_advanced.py`
- `tools/miner/src/dead_signal_evidence_graph.py`
- `tools/miner/src/dead_signal_weapon_schema_trace.py`

Packaging explicitly includes `dead_signal_trace_workspace` in `tools/miner/build.ps1`.

## Evidence doctrine

The interface explains evidence; it does not create evidence.

Maintain this exact boundary:

```text
player-facing claim
→ exact installed identity
→ typed owner
→ exact source record
→ selector / consumer
→ provenance chain
→ PROVEN / PARTIAL / UNRESOLVED / NOT APPLICABLE
```

Never promote fuzzy matches, spelling guesses, bare-number collisions, external catalog counts, or AI confidence into proof. Do not turn the graph into an automatic publication authority. Missing paths remain unresolved.

The design direction was reinforced by the PROVE IT evidence-graph demonstration: evidence health should name the missing link rather than produce a reassuring paragraph. Dead Signal should retain field-level states instead of hiding critical gaps behind a single percentage.

## Weapons state

Weapons v1 remains schema-locked:

- 130 source-derived identities: 117 standard-blueprint, 7 nonstandard-blueprint, 6 special-equipped;
- the count is observed output, never a hard-coded universal count;
- attachment compatibility is exact and four-state;
- calibration compatibility is exact and four-state;
- ranged selectable ammo is projected through exact typed owners;
- ten melee recipes have exact seasonal formula owners but absent retained material bodies;
- Morgan has an exact one-level Blueprint Star owner while gear-tier ownership remains unresolved;
- special/scenario activation remains unresolved without exact activation evidence.

Do not reopen the old 120-count architecture problem or ownerless fixed-skill branch unless new installed-game evidence changes the state.

## Immediate next boundary

Evidence Graph Expansion Phase 0 is complete. Read `HANDOFF-2026-08-18-EVIDENCE-GRAPH-EXPANSION-PHASE-0.md` and begin Phase 1 generalized contracts next. Preserve the committed Weapons v1 compatibility baseline.

Also confirm the user has updated from `.63` to `.64` and that Evidence Graph appears immediately at launch. If the visual layout or behavior differs from the approved render, inspect the packaged `.64` application and correct the canonical UI source; do not tell the user the feature is merely nested elsewhere.

After visual acceptance, the next safe Miner enhancement is generalized entity tracing beyond weapons, using the same deterministic evidence contract. Do not broaden the schema merely for visual completeness.

## Repository safety

- `tools/miner.zip` is pre-existing, untracked, protected, and must remain untouched.
- Never commit Miner output, raw snapshots, SQLite indexes, NeoX exports, local paths, or packaged runtimes.
- Production remains copy-only cPanel deployment.
- GitHub source is authoritative; release packages are artifacts.
- Release `latest.json` only after the public package exists and its size/hash are verified.
