# Dead Signal — Perplexity Coding-Agent Handoff

> This document is for a Perplexity coding/computer agent that will actively work on the Dead Signal repository.
>
> It is not limited to web research. Research is only an optional supporting activity.
>
> Repository: `https://github.com/raiinman/dead-signal`
>
> Canonical branch: `main`
>
> Prepared: 2026-08-14

## 1. Mission

Work directly on the Dead Signal codebase until the assigned task is implemented, validated, committed, pushed to canonical GitHub `main`, and handed off with exact evidence.

Dead Signal is a Once Human workstation/database and build-planning project. Accuracy is more important than filling every field. Installed-game evidence, exact record identity, and fail-closed behavior are core architectural requirements.

You are expected to:

- inspect the repository and current state;
- diagnose problems from code and evidence;
- implement in-scope changes;
- add or update tests where appropriate;
- run the required validation;
- review the final diff;
- commit intentionally;
- push directly to canonical `main` when the assignment is complete and green;
- check relevant GitHub Actions;
- update `AI-CONTINUITY.md` with exact commits, outcomes, remaining blockers, and next steps.

Do not merely return suggestions when the assigned work can safely be completed in the repository.

## 2. Mandatory startup sequence

Before changing anything:

1. Open the repository `raiinman/dead-signal`.
2. Work on canonical branch `main` unless the user explicitly requests otherwise.
3. Fetch `origin/main`.
4. Verify the local branch and exact `HEAD`.
5. Check whether local `main` is behind, ahead, or diverged from `origin/main`.
6. Fast-forward from `origin/main` when safe.
7. Run `git status --short` and preserve all pre-existing/unrelated changes.
8. Read `PROJECT-RULES.md` completely.
9. Read `AI-CONTINUITY.md` completely.
10. Read this document completely.
11. Inspect the files and tests relevant to the assigned task.
12. Restate the exact scope and constraints before implementation.

Never assume the commit recorded in this handoff is still current. GitHub `origin/main` is canonical. At the time this document was prepared, the last known pushed commit was `3baa6156e1395678bf008d3e91445e84eb8b5658`; verify it rather than trusting it.

If the worktree contains unrelated user files or edits, do not delete, reset, stage, commit, or overwrite them.

Known local-only artifact from the originating workstation: `tools/miner.zip`. It is intentionally untracked and must not be committed or modified.

## 3. Authority and evidence policy

Use this evidence hierarchy:

1. Exact installed-game data extracted by the Dead Signal Miner.
2. Direct, dated in-game screenshots/video showing the exact record and claim.
3. Official Once Human sources.
4. Exact code paths, static consumer evidence, and exact reverse references.
5. Reliable third-party sources with inspectable provenance.
6. Community sources as research leads only.
7. Search snippets and AI summaries as non-evidence.

Rules:

- Never invent mechanics, values, formulas, recipes, compatibility, acquisition paths, IDs, descriptions, DPS, rankings, or variant relationships.
- Never fuzzy-promote IDs.
- Never substitute a similar record for a missing exact record.
- `WS1301` is not `WS13101`, `WS130`, or any other similar token.
- Missing recipe evidence does not prove non-craftable.
- A source mentioning a base weapon does not automatically describe its named variants.
- Conflicting, cross-wired, incomplete, or identity-unsafe data must remain visibly unresolved.
- External web research can identify leads, but installed data or direct in-game evidence is required for database promotion unless the field is explicitly editorial/external.

## 4. Repository workflow

### Read and diagnose

- Use fast exact search (`rg`, GitHub code search, or equivalent).
- Inspect current implementations and tests before designing replacements.
- Prefer the smallest change that solves the complete assigned problem.
- Preserve existing architecture and established UI language unless the task requires a broader change.
- Do not treat generated browser payloads as hand-editable source data.

### Edit

- Modify source files, templates, tests, and documentation deliberately.
- Keep generated files and their source pipeline consistent.
- Do not hand-promote a single generated category when an all-seven Miner transaction is required.
- Do not rewrite or reformat unrelated files.
- Do not remove existing user changes.
- Avoid machine-specific absolute paths in committed files.

### Validate

Run tests in proportion to the change. For Weapon/site/Miner work, the expected baseline is:

```powershell
python -m unittest discover -s tools/site/tests -p "test_*.py" -v
node tools/site/tests/test-weapon-public-adapter.js
node --check database/weapons/catalogue.js
git diff --check
git diff --stat
```

For Miner-source changes, configure the project Miner Python path and run:

```powershell
$env:PYTHONPATH = ((Resolve-Path 'tools\miner\src').Path + ';' + (Resolve-Path 'tools\miner\src\extractor').Path + ';' + (Resolve-Path 'tools\miner\src\neoxtractor').Path)
.\.venv-miner\Scripts\python.exe -m unittest discover -s tools\miner\tests -v
```

If the required environment is unavailable, report exactly what was and was not run. Do not claim a test passed when it was skipped.

For UI changes, perform a local browser smoke test when possible. Check the actual rendered text/state and browser console rather than relying only on static inspection.

### Commit and push

When the assignment is implemented and green:

1. Review `git diff` and `git diff --stat`.
2. Confirm only intended files are staged.
3. Commit with a concise, accurate message.
4. Push directly to `origin/main` unless the user explicitly requested a branch/PR.
5. Check the relevant GitHub Actions runs.
6. If CI fails, inspect the failure, fix it in scope, retest, commit, push, and recheck.
7. Update `AI-CONTINUITY.md` with the exact implementation commit SHA, current HEAD, tests, CI run IDs/outcomes, findings, unresolved evidence, and next steps.
8. Push the continuity follow-up.

Do not rewrite published history, force-push, reset hard, or discard work to make the branch clean.

## 5. Generated-data transaction rule

Dead Signal has seven browser payload categories:

1. Weapons
2. Armor
3. Calibrations
4. Mods
5. Attachments
6. Deviations
7. Cradles

When materializing a fresh Miner snapshot, validate and materialize all seven together transactionally. Never hand-copy or hand-promote one category around a failing category.

Preferred ZIP workflow:

```powershell
python tools/site/materialize-miner-zip.py "path\to\snapshot.zip" --repository-root .
```

For a local Miner `published/` directory:

```powershell
python tools/site/materialize-published-snapshot.py "path\to\published" --repository-root . --dry-run
python tools/site/materialize-published-snapshot.py "path\to\published" --repository-root .
```

If any contract fails validation, stop before repository payload replacement, diagnose the source/pipeline problem, and fix it at the correct layer. Do not weaken a validator solely to make bad data pass.

Generated `database/*/*-data.js` files must come from the validated materializer. Do not hand-edit them.

## 6. Miner safety

The Miner reads installed Once Human data. It must remain read-only toward game files and anti-cheat files.

Never:

- modify the Once Human installation;
- execute extracted game bytecode;
- commit snapshots, raw archives, local SQLite indexes, PYC reports, builds, or packaged runtimes;
- publish `reference-tracer.sqlite`;
- upload raw evidence bundles to external services;
- infer runtime mechanics from a symbol name alone.

Permitted investigation uses exact table records, exact references, bounded static token context, and non-executing analysis.

## 7. Current canonical Weapon state

The following work is already landed. Do not redo or revert it.

### Fresh v1.5.13.2 transaction

- Fresh Miner transaction payload commit: `2e23cac443733337fb99fa3ab582251bead0dcda`.
- Continuity follow-up: `e032db6e2ac30a4d8a2db322797f9cfad295650e`.
- Database website CI run `31784533095`: SUCCESS.
- 120 Weapon records.
- 1,618 complete Mod frame-evidence variants.
- All seven payloads were transactionally materialized.

### Weapon mechanics

- 76 resolved player-facing mechanics.
- 14 Weapon records reference an exact skill record missing from installed `passive_skill_data`.
- Those 14 records cover 11 unique exact `WS...` IDs.
- 30 Weapon records contain no fixed-skill reference.
- Do not present the missing-record and no-reference states as the same problem.

### Exact missing skill records

| Weapon | Exact missing ID |
|---|---|
| OIC-8 - Last Carnival | `WS2001` |
| SOCR - Sand Dancer | `WS1402` |
| MG4 - Sandstorm | `WS1601` |
| DE.50 - Goshawk | `WS1101` |
| G17 - Cash Only | `WS2001` |
| DBSG - Format | `WS15203` |
| HAMR - Hannya | `WS15502` |
| SN700 - Dark Snowflake | `WS1501` |
| SR2000 - Die Another Day | `WS14503` |
| SR2000 - Jungle Camouflage | `WS1001` |
| MPS7 - Chaos Domain | `WS15304` |
| MPS7 - Focus | `WS1301` |
| MPS7 - Urban Ninja | `WS1301` |
| R500 - Interfade | `WS2001` |

The 11 unique exact IDs are:

`WS1001`, `WS1101`, `WS1301`, `WS1402`, `WS14503`, `WS1501`, `WS15203`, `WS15304`, `WS15502`, `WS1601`, `WS2001`.

Exact Research Console work already found only `gun_blueprint_attr_data.fixed_skill_code` references and no exact installed passive-skill records. Similar IDs are not solutions.

### Flavor descriptions

- 106 Weapon records have no short-description handle.
- 14 translation handles resolve consistently but remain withheld because identity/cross-wire safety is not proven.
- Kukri, Frozen Northern Pike, and The Fabled Masamune exposed a shared/cross-wired description-handle problem in installed item data.
- Never repair descriptions by choosing plausible text or by name similarity.

### Ratings and projectile formatting

Implementation commit: `9debce2929ee217302c0c38a56c1890372895bff`.

- Browse, detail, and compare default to Tier I · 1★ rather than maximum Tier V.
- Exact `client_data/bullet_pattern_data.bullet_num` is joined through `gun_base_params_data.bullet_pattern_no`.
- 13 shotguns have proven multi-projectile counts.
- DMG displays the scalar and count, e.g. ACS12 - Netherworld is `32×5` at Tier I · 1★ and `188×5` at Tier V · 1★.
- The raw `weapon_magazine_size_affix_value` is not the final in-game magazine total and is no longer shown as Magazine.
- Exact final magazine aggregation (`get_gun_magazine_size`) remains unresolved. Do not restore Magazine until the formula/consumer is proven.

### Acquisition classification

- 106 Weapons: exact recipes proven for all five Gear Tiers.
- 9 Weapons: direct stronghold-exploration acquisition evidence.
- 5 Weapons: unresolved.

The five unresolved exact names are:

1. Machete
2. Metal Baseball Bat
3. Old Baseball Bat
4. Old Machete
5. Rusted Blade

Missing recipes never justify labeling these non-craftable.

## 8. Armor pipeline state

The canonical Miner runner must call `armor_tier_completion.complete_file` after normal Armor normalization.

This restores:

- 173 player-facing Armor pieces;
- exactly five Tier I–V rows each;
- 865 Tier rows;
- 15 exact recovered Tier rows;
- zero unresolved Armor Tier series;
- two explicit crafting-variant conflicts.

Do not remove or bypass this completion step. An all-seven materializer failure exposed the missing runner call, and it was fixed in commit `9debce2929ee217302c0c38a56c1890372895bff`.

## 9. Other database boundaries

- Armor, Mods, Calibrations, Deviations, and Cradles remain `SOON` until their routes and integrations are genuinely player-ready.
- Build Lab mappings must use canonical identities, not display-name guesses.
- Mod frame arithmetic and frame-library joins are proven, but ordered sub-entry positional consumer semantics remain unproven.
- Deviation and Cradle display-name families can contain multiple source variants; never auto-select variant 1.
- Attachment compatibility preserves direct localized wording; blank compatibility remains unresolved.
- Calibration candidate weight `200` is a raw mined weight, not a percentage probability.

Read the category-specific sections in `AI-CONTINUITY.md` before changing any of these systems.

## 10. Hosting and deployment prohibitions

Do not touch:

- SSL;
- DNS;
- redirects;
- domain configuration;
- cPanel hosting configuration;
- the accepted landing page;
- the Official Once Human X feed;
- copy-only deployment architecture;
- WordPress or a new server runtime.

Do not deploy merely because a repository change is complete. Repository work and deployment are separate scopes unless the user explicitly authorizes deployment.

## 11. Optional web research

Web research is allowed only when it supports the assigned coding/evidence task.

When researching:

- prefer official/primary sources;
- preserve original URLs, titles, dates, quotes, screenshots, and video timestamps;
- distinguish external corroboration from installed-data verification;
- reject search snippets and circular citations;
- do not let community consensus overwrite installed evidence;
- do not upload private Miner artifacts or repository secrets.

Research findings must be brought back into the repository workflow and validated before they change database claims.

## 12. Task execution protocol

For each user assignment, begin with:

```text
Repository HEAD: <exact SHA after synchronization>
Worktree state: <clean or exact pre-existing changes>
Assigned outcome: <one-sentence objective>
Files/systems likely in scope: <list>
Evidence constraints: <list>
Validation planned: <commands/suites>
```

Then execute the task. Do not stop at a plan unless blocked by missing authority, unavailable required evidence, or an external dependency that cannot be safely resolved.

If blocked:

1. exhaust safe read-only inspection;
2. describe the exact blocker;
3. identify what evidence or authorization is missing;
4. preserve the repository in a safe state;
5. do not guess around the blocker.

## 13. Required completion report

At completion, report:

```text
Outcome:
- What now works.

Evidence/findings:
- Exact facts established.
- Exact unresolved facts retained.

Changes:
- Files/systems changed.
- Generated payload transaction, if any.

Validation:
- Every test/check run and its result.
- Local browser result, if applicable.
- GitHub Actions run IDs and conclusions.

Git:
- Implementation commit SHA.
- Continuity commit SHA.
- Final pushed HEAD.
- Branch and remote.
- Remaining untracked/pre-existing files left untouched.

Next work:
- Safest evidence-backed next step.
```

Never say “all green” without listing the checks. Never say “pushed” without providing the exact SHA and remote branch.

## 14. First assignment wrapper

The user will provide a specific assignment after linking this handoff. Execute only that assignment while respecting the whole document.

Recommended format:

```text
ASSIGNMENT
Objective: <concrete outcome>
In scope: <files/features/data categories>
Out of scope: <explicit exclusions>
Required evidence: <installed snapshot, screenshot, exact IDs, or source links>
Required validation: <tests/checks>
Finish condition: <what must be committed/pushed/reported>
```

If the assignment is broad but safely discoverable from the repository, inspect and proceed. Ask the user only when a missing choice would materially change the outcome or authorize a separate external/destructive action.
