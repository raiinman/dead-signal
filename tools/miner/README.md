# Dead Signal Miner

`tools/miner/` is the canonical GitHub home for Dead Signal Game Miner source and miner-side investigation tools.

The goal is to stop exchanging rebuilt ZIPs for every source change. Once the current local Miner source is imported here, future fixes should be made in GitHub and pulled into the local Miner workspace.

## Architecture

```text
Once Human installed game files
        ↓
Dead Signal Miner source (`tools/miner/`)
        ↓
raw / normalized miner output (generated locally; not committed)
        ↓
player-facing normalized Dead Signal data
        ↓
Dead Signal Build Lab / database
```

The production website remains separate from the mining process. `.cpanel.yml` is copy-only and does not deploy `tools/miner/`.

## Canonical source layout

The current packaged Windows Miner ships important Python source under `_internal/extractor/`. During the one-time repository migration, copy the maintained source modules into a clean source tree here rather than committing an entire PyInstaller/package directory.

Target layout:

```text
tools/miner/
├── README.md
├── .gitignore
├── VERSION
├── src/
│   └── extractor/
│       ├── weapon_progression.py
│       ├── normalize_weapons.py
│       ├── combat_resolver.py
│       ├── export_bindict.py
│       ├── normalize_extended.py
│       ├── npk_extract.py
│       └── ...other maintained Miner source modules
├── scripts/
├── tests/
└── weapon-progression-probe.py
```

Do not commit the complete packaged `_internal/` runtime, generated extraction output, raw Once Human archives, large SQLite indexes, packaged EXEs, or release ZIPs.

## Working rule

After the source migration, GitHub becomes the source of truth:

1. Change Miner source in `tools/miner/`.
2. Commit the change to `main`.
3. Pull the repository on the Windows machine.
4. Build/package the Miner locally when an executable release is needed.
5. Run the Miner against the installed game files.
6. Inspect/validate generated output before publishing normalized player data.

A rebuilt ZIP/EXE is a **release artifact**, not the editable source of truth.

## Current proven Miner state

The latest continuity record proves Miner **v1.5.7.4** fixed the prior `buffs.json` circular-reference serialization fault. The real run passed validation with zero `_dead_signal_circular_reference` markers while keeping combat resolution and Calibration localization stable.

Future Miner versions should be derived from the GitHub source after the one-time local source import.

## Weapon progression probe

`weapon-progression-probe.py` is a static post-extraction investigator for weapon progression:

**Blueprint Stars × Gear Tier I–V = displayed weapon stats**

It does not import or execute Once Human game code. Run it after the Miner has produced its raw/normalized JSON output.

```powershell
python tools\miner\weapon-progression-probe.py "C:\path\to\dead-signal-miner-output"
```

If `indexes/reference-tracer.sqlite` exists below the Miner output root it is detected automatically. A different tracer can be supplied explicitly:

```powershell
python tools\miner\weapon-progression-probe.py "C:\path\to\miner-output" --tracer "C:\path\to\reference-tracer.sqlite"
```

Outputs are written by default to:

`<miner-output>\investigations\weapon-progression\`

- `weapon-progression-report.md` — human-readable high-value leads and aggregate Tier ratios.
- `weapon-progression-candidates.csv` — sortable evidence rows with source file and JSON path.
- `weapon-progression-investigation.json` — complete machine-readable evidence, Tier inference, and tracer hits.

### Evidence rule

Do not turn a discovered ratio into Dead Signal calculator logic merely because it looks plausible. A candidate model should reproduce multiple weapons across multiple Tier/Star combinations, with any remaining discrepancy explainable by the game's rounding behavior.
