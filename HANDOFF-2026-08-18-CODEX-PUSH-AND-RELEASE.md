# Dead Signal — Codex Push + Release Handoff

> **Canonical repo:** `raiinman/dead-signal`
> **Branch:** `main`
> **Date:** 2026-08-18 America/Phoenix
> **Purpose:** Finish the local Miner infrastructure work, push the actual source commits, then cut the next packaged Miner release only after the full release gate passes.

## Read first

Before changing or pushing anything, read completely:

1. `HANDOFF-CURRENT.md`
2. `AI-CONTINUITY.md`
3. `PROJECT-RULES.md`
4. `HANDOFF-2026-08-18-CODEX-LOCAL-TAKEOVER.md`
5. this file

The most recent pushed results documentation is commit:

`0947b0b95fa47b2227e844190a08cff06342ae6c` — `Record local Intelligence takeover results`

That commit documents the local implementation results, but **the actual Miner source commits remain local and unpushed**.

---

# Immediate objective

Complete the local-to-canonical transition cleanly.

Do **not** start a new research lane yet.

First:

```text
inspect local git state
→ identify all local Miner commits not on origin/main
→ review their diffs
→ run validation again
→ push coherent source commits to main
→ verify GitHub canonical state
→ package/release next Miner version
→ publish updater manifest last
```

Only after this boundary is clean should Cradle applicability or other new research continue.

---

# Known local implementation results

The local Codex session already implemented and validated the Intelligence export fixes documented in `HANDOFF-2026-08-18-CODEX-LOCAL-TAKEOVER.md`.

Expected local source work includes, at minimum:

- explicit shareable Intelligence artifact allowlist
- exclusion of SQLite/DuckDB/local indexes/raw snapshot data from shareable ZIP
- bundle manifest with member-level uncompressed byte accounting
- absolute local path redaction from shared compiled summaries
- compiler schema version 8
- snapshot diff schema version 2
- bounded snapshot diff output
- truncation metadata and local evidence pointers
- regression tests for bundle exclusion/redaction/accounting/bounded values

Real local validation already reported:

- old extracted forensic workspace: ~7.88 GB
- old snapshot diff: ~849.7 MB
- new bounded snapshot diff: 531,890 bytes (~519 KB)
- new shareable ZIP: 2,031,475 bytes compressed (~1.94 MiB)
- shareable payload: 16 allowlisted evidence artifacts plus compiled summary + manifest
- no SQLite/DuckDB entries in shareable ZIP
- no detected `C:\\Users\\...` or `C:/Users/...` paths in shareable ZIP
- focused tests: 7 passed
- full Miner source suite: 184 passed
- `git diff --check`: clean except expected Windows line-ending notices
- `tools/miner.zip` remains untouched

Treat those as expected results to re-verify from the local filesystem before pushing.

---

# Step 1 — Inspect local git state before any push

Use the local repository directly.

Record:

- `git status --short`
- current branch
- local HEAD
- `origin/main`
- commits in `origin/main..HEAD`
- commits in `HEAD..origin/main`
- changed/untracked files

Do not assume all local commits belong in the push merely because they are ahead of `origin/main`.

Review every local-only commit and classify it as:

- Miner architecture / Intelligence export work intended for canonical `main`
- unrelated local work that must remain unpushed
- generated artifact / machine-local output that must never be committed

Do not push generated Miner outputs, local snapshots, databases, ZIPs, build artifacts, or machine-specific files.

Do not touch the pre-existing untracked `tools/miner.zip`.

---

# Step 2 — Review local source diffs

Before pushing, verify the actual local source code matches the documented result.

Specifically inspect the changed Miner files responsible for:

- `_bundle_members` / shareable bundle selection
- bundle manifest generation
- compiled-summary redaction
- snapshot diff bounding/truncation
- schema version changes
- tests

Check for accidental collateral changes from the large Miner UI/architecture work already on `main`.

Do not mix unrelated website, Build Lab, landing-page, hosting, or design changes into these commits.

If a local commit mixes unrelated changes, split/rewrite locally into coherent commits before pushing.

---

# Step 3 — Re-run validation locally

Run the relevant source validation again before pushing.

At minimum:

```text
python -m compileall -q tools/miner/src tools/miner/tests
python -m unittest discover -s tools/miner/tests -v
git diff --check
```

Also rerun the focused Intelligence compiler/snapshot-diff tests if they are separately invokable.

Using the existing completed local snapshot, verify without performing an unnecessary new full mine:

- bounded `published/reports/snapshot-data-diff.json`
- shareable Intelligence ZIP generation
- ZIP contains only the intended allowlisted shareable members
- ZIP contains no `.sqlite`, `.db`, `.duckdb`, snapshots, or raw heavy forensic stores
- ZIP contains no absolute local Windows user paths
- manifest member counts and byte accounting match the archive
- the full local forensic workspace remains available locally and unchanged

If any of these fail, fix locally and rerun validation before pushing.

---

# Step 4 — Push only coherent source commits to canonical main

Once validation is green:

1. update local `main` from `origin/main` safely if needed;
2. resolve divergence without discarding validated local work;
3. push only the intended Miner source/test commits to `main`;
4. do not force-push unless absolutely necessary and explicitly justified;
5. verify the pushed GitHub commits and files after the push.

Expected canonical result:

- GitHub source now contains the actual code that produced the documented compact Intelligence bundle
- generated local data remains uncommitted
- documentation commit `0947b0b...` remains part of history
- source tests remain green

Record the exact pushed commit SHAs in the current takeover handoff.

---

# Step 5 — Prepare the next Miner release

Only after the source commits are on canonical `main` and verified should a new packaged release be cut.

Current stable release boundary before this work is Miner **v1.5.14.61**.

The next release is expected to be **v1.5.14.62** unless current repository/release state proves another version has already been assigned.

Before changing `VERSION`, inspect:

- `tools/miner/VERSION`
- `tools/miner/release/latest.json`
- current GitHub releases/tags
- current `main`

Never overwrite an already-used version/tag.

Release content should include the compact Intelligence export contract and bounded snapshot diff fixes.

Do not bundle unrelated new Cradle research into this release unless it is already part of the validated local commits and clearly intentional.

---

# Step 6 — Full packaged Windows release gate

Use the existing canonical release process.

The release is not complete merely because source tests pass.

Require the established packaged gate:

```text
source tests
→ Windows build
→ packaged Miner self-test
→ release ZIP/package generation
→ SHA-256 + size verification
→ GitHub release asset publication
→ public asset verification
→ updater manifest publication LAST
```

Preserve all existing updater safety rules.

The updater manifest must not point at the new version until the exact release asset is online and verified.

Do not touch `tools/miner.zip`.

If the release workflow fails at any stage, stop publication at that point, diagnose/fix, and rerun. Do not manually fake a successful stable manifest.

---

# Step 7 — Post-release verification

After release publication, verify:

- `tools/miner/VERSION` is correct
- release tag/version matches
- release ZIP is downloadable
- declared byte size matches
- declared SHA-256 matches
- packaged self-test passed
- `tools/miner/release/latest.json` points to the exact verified asset
- updater manifest was the last publication step
- stable users can update from `.61`

Then update the current takeover handoff with:

- pushed source commit SHAs
- release commit SHA
- release workflow/run status
- updater-publication commit SHA
- final ZIP size + SHA-256
- confirmation that the compact shareable Intelligence bundle is now part of the released Miner

---

# Do not reopen closed lanes during this handoff

This handoff is about source canonicalization + release.

Do not spend time reopening:

- the 11 ownerless fixed-skill codes / 14 public ownerless weapon records
- broad description forensics already closed except the one known translation conflict
- arbitrary full-tree corpus rescans

The fixed-skill lane remains closed unless new exact typed evidence appears.

---

# After `.62` is stable

Once the release boundary is clean, continue into the next high-value player-facing blocker using the local persistent architecture.

Priority:

1. **Cradle compatibility/applicability**
2. remaining projectile/default semantics
3. attachment/calibration compatibility cleanup
4. acquisition edge cases
5. melee display semantics

For Cradle work, use the local:

- table registry SQLite
- consumer index SQLite
- typed reference graph SQLite
- analytics warehouse
- current normalized Cradle dataset
- exact client/server PYC consumer scopes already indexed

Do not produce another giant full-corpus Intelligence export. Query the local indexes directly and export only targeted evidence needed for proof/review.

---

# Reporting back

When this handoff is complete, report succinctly:

1. local-only commits reviewed
2. exact source commits pushed
3. tests/validation results
4. packaged release version
5. release workflow result
6. final release ZIP size/SHA-256
7. updater manifest status
8. any blockers that prevented release

Do not claim `.62` stable until the updater manifest is verified to point at the validated release asset.

---

# Operating principle

> **GitHub source must match the code that produced the validated local results before the Miner is released. Package only after source is canonical; publish the updater manifest only after the package is proven.**
