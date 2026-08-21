# Evidence Graph Phase 16 — Performance and Release Hardening

Phase 16 closes the Evidence Graph expansion with runtime hardening and explicit release gates. It does not weaken evidence semantics, change publication authority, or publish a release by itself.

## Runtime cache

`dead_signal_graph_runtime.AdapterResultCache` stores validated generalized graphs under `catalogs/dead-signal-adapter-cache.json`.

A cache entry is reusable only when all exact claim dependencies retain the same Phase-11 effective Current-over-Base fingerprints. Any changed, removed, or newly resolved owner forces a cache miss. Cache content is research/runtime acceleration only and may be deleted at any time.

The cache is bounded to 512 entries by default and evicts least-recently-used entries by recorded use time.

## Bounded generalized traces

`DeadSignalGeneralizedGraph.entity_graph()` now supports:

- dependency-aware cache use;
- cooperative cancellation tokens;
- progress callbacks;
- a default 30-second trace bound;
- per-call cache bypass for cold measurements.

Generalized entity search is capped at 1,000 results even if a larger limit is requested.

Cancellation is deliberately described as cooperative. A legacy synchronous adapter cannot be forcibly terminated in the middle of one blocking read; however, a cancelled/superseded request is rejected at the facade boundary and must not be treated as a completed current trace.

## Performance diagnostics

`dead_signal_performance_release.benchmark_real_snapshot()` writes:

`reports/phase16-performance.json`

It samples exact registry entities and records:

- cold trace time;
- cache-seeding trace time;
- warm cache-hit time;
- cold Python allocation peak from `tracemalloc`;
- warm cache-hit status.

The sample size is bounded. Corpus totals are never hard-coded.

## Release asset audit

`audit_release_asset(zip_path, manifest_path)` is a fail-closed prepublication check. It requires:

- a real public ZIP asset;
- exact SHA-256 agreement with the manifest;
- exact byte-size agreement with the manifest;
- a manifest timestamp after the verified ZIP;
- the asset not to be protected `tools/miner.zip`.

This diagnostic never uploads or publishes anything.

## Final release sequence

The required order is:

1. Complete source suite passes.
2. Real-snapshot smoke tests pass.
3. Measure cold/warm trace performance and inspect memory report.
4. Build the Windows executable/package.
5. Packaged self-test passes.
6. Produce the public release ZIP.
7. Compute and independently verify ZIP SHA-256 and byte size.
8. Publish/verify the release asset.
9. Run the release-asset audit.
10. Update/publish `tools/miner/release/latest.json` **last**.

The updater manifest must never lead the asset.

## Protected boundaries

Phase 16 does not:

- execute game bytecode;
- change adapter evidence rules;
- promote fuzzy/name/scalar matches;
- grant publication authority to adapters or caches;
- publish raw research bundles;
- touch `tools/miner.zip`;
- claim CI, real-snapshot, packaged, or release gates passed before they are actually observed.

## Exit criteria

Phase 16 is code-complete when runtime caching, cancellation/progress, bounded queries, performance diagnostics, release-asset verification, regression tests, and handoff documentation are merged.

The Evidence Graph expansion is release-complete only after the external validation gates are observed:

- complete source suite passes;
- real-snapshot smoke tests pass;
- packaged self-test passes;
- public ZIP hash and size match;
- manifest is published after verified asset publication;
- `tools/miner.zip` remains untouched.
