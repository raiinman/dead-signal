# Dead Signal — Miner Weapon Identity Trace Workspace

Completed 2026-08-18 (America/Phoenix).

## Outcome

The Data Intelligence **Evidence Graph** tool is now the complete visual Weapon Identity Trace workspace approved in the design render. It replaces the former basic graph canvas and raw-JSON panel.

In `v1.5.14.64`, that evidence engine is promoted into the primary Miner shell:

- the application opens directly on **Evidence Graph**;
- **Evidence Graph** is a first-class sidebar destination;
- **Run Pipeline** remains available as a supporting operation rather than the landing screen;
- the primary workspace automatically loads the local 130-weapon corpus and traces a real subject;
- installations without a completed snapshot fail closed into a clear Run Pipeline call to action.

The workspace includes:

- installed-snapshot, Miner-version, and scan-status telemetry;
- searchable selection across the source-derived 130-weapon Weapons v1 corpus;
- one-click asynchronous exact trace execution;
- visual Item → Blueprint owner → Gun profile identity spine;
- Effect, Attachments, Calibration, Ammo, Crafting, and Progression branches;
- cyan proven, red unresolved, and gray not-applicable graph states;
- clickable Evidence Inspector with source table, record, selector, layer, and provenance chain;
- automated recomputation checks;
- fail-closed human-review queue for branches without an exact typed owner.

## Evidence boundary

The UI does not create or infer relationships. It composes existing exact outputs from:

- `DeadSignalEvidenceGraph.weapon_graph`;
- `DeadSignalWeaponSchemaTrace.trace`;
- locked Weapons v1 `attachment_compatibility`;
- locked Weapons v1 `calibration_compatibility`;
- locked Weapons v1 `ammo_configuration`;
- exact crafting and progression owners.

No fuzzy joins, spelling guesses, external catalog values, or hard-coded weapon count were introduced. Missing paths remain unresolved.

## Source

- `tools/miner/src/dead_signal_trace_workspace.py`
- `tools/miner/src/dead_signal_intelligence_advanced.py`
- `tools/miner/tests/test_data_intelligence_ui.py`

## Validation

- 207 Miner tests pass.
- Live Tk construction against `C:\Users\mikea\Documents\Dead Signal Miner` passes.
- Real snapshot loads 130 weapon choices.
- Default SOCR - The Last Valor trace completes and creates all interactive graph objects.
- `tools/miner.zip` remains untouched and untracked.

## Release boundary

Miner source is versioned `v1.5.14.64`. Pushing the version commit triggers the protected Windows release workflow, which builds and self-tests the package, publishes and re-verifies the GitHub asset, then updates `release/latest.json` last so installed Miners can discover the update safely.
