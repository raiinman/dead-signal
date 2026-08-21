# Dead Signal — Evidence Graph Expansion Phase 16 Handoff

Date: 2026-08-21

## Status

The Evidence Graph expansion implementation sequence has reached Phase 16.

Phases 0–15 are merged. Phase 16 adds runtime caching, bounded trace controls, real-snapshot performance diagnostics, release-asset verification, tests, and final handoff documentation.

At the time this handoff was written, Phase 16 code still requires the external validation gates below. Do not claim the expansion is release-complete until those gates are actually observed.

## Canonical rules

Read `PROJECT-RULES.md` and `AI-CONTINUITY.md` first.

Installed-game/Miner evidence is authoritative for numbers and mechanics. Discovery, names, external websites, AI summaries, scalar collisions, and fuzzy matches never create proof.

Evidence states remain PROVEN, PARTIAL, UNRESOLVED, NOT APPLICABLE, and CONFLICT.

`PROVEN` is not automatic publication. Phase 14 publication contracts remain a separate fail-closed boundary.

## Expansion summary

- Phase 0 — Weapons v1 freeze and compatibility baseline.
- Phase 1 — generalized evidence contracts.
- Phase 2 — typed domain-adapter framework.
- Phase 3 — searchable entity registry and selector UI.
- Phase 4 — Attachments graph.
- Phase 5 — Calibration graph.
- Phase 6 — Armor and Armor Set graph.
- Phase 7 — current Mod 2.0 graph.
- Phase 8 — Cradle graph.
- Phase 9 — Crafting Recipe and Material graph.
- Phase 10 — Deviation graph.
- Phase 11 — dependency invalidation and evidence freshness.
- Phase 12 — evidence assessment and review queue.
- Phase 13 — generalized Miner intelligence interface.
- Phase 14 — claim-backed publication integration.
- Phase 15 — cross-domain false-proof benchmark.
- Phase 16 — performance and release hardening.

## Supported generalized domains

weapon, attachment, calibration, armor, armor_set, mod, cradle, recipe, material, deviation.

Do not hard-code corpus counts from one snapshot.

## Phase 16 runtime changes

`tools/miner/src/dead_signal_graph_runtime.py` adds a persistent bounded adapter-result cache. Cache acceptance requires unchanged exact Phase-11 dependency fingerprints; changed or removed owners force recomputation. It also adds cooperative cancellation, progress callbacks, a default bounded trace duration, and validation before cache reuse. Cache content has no publication authority.

`DeadSignalGeneralizedGraph.entity_graph()` routes through that runtime. Entity search is bounded to 1,000 rows.

## Performance diagnostics

`tools/miner/src/dead_signal_performance_release.py`

`benchmark_real_snapshot(output)` writes `reports/phase16-performance.json` with bounded samples of cold trace time, cache-seed time, warm-hit time, and Python allocation peak.

Use the user's local completed Miner snapshot for the real-snapshot gate. Do not ask the user to upload the multi-gigabyte corpus when local Codex has it.

## Release audit

`audit_release_asset(zip_path, manifest_path)` verifies that the public ZIP exists, its exact SHA-256 and byte size match the manifest, the manifest is newer than the verified ZIP, and protected `tools/miner.zip` is never treated as a release asset. This function is diagnostic only and performs no publication.

## Mandatory release gates

Before publishing a new stable Miner release, observe all of these:

1. complete source suite passes;
2. real-snapshot smoke tests pass;
3. Phase 15 false-PROVEN benchmark passes;
4. cold/warm performance report is generated and reviewed;
5. Windows build succeeds;
6. packaged self-test passes;
7. public ZIP exists and its SHA-256 and byte size are independently verified;
8. release asset is published and verified;
9. updater manifest is published last;
10. `tools/miner.zip` remains untouched.

If any gate fails, stop release publication and fix the failure. Do not rewrite `latest.json` to point at an unverified or nonexistent asset.

## Updater manifest

Current stable manifest before the Phase 16 release remains `tools/miner/release/latest.json`.

Do not modify it until a new public release ZIP has already passed hash/size verification and asset publication verification.

## Completion definition

The expansion is complete when any supported entity can return exact identity, typed evidence chain, source provenance, deterministic state, named missing/conflicting evidence, reverse relationships where supported, dependency-aware recomputation, safe publication decision, and the Phase 15 benchmark remains at zero false PROVEN results.

Phase 16 code merge alone is not the same as release completion. External source/real-snapshot/build/package/asset/manifest gates remain authoritative.
