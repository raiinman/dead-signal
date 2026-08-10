# Dead Signal Miner Tools

## Weapon progression probe

`weapon-progression-probe.py` is a static post-extraction investigator for the unresolved weapon progression model:

**Blueprint Stars × Gear Tier I–V = displayed weapon stats**

It does not import or execute Once Human game code. Run it after the existing `script.npk` extractor has produced its raw/normalized JSON output.

```powershell
python tools\miner\weapon-progression-probe.py "C:\path\to\dead-signal-miner-output"
```

If `indexes/reference-tracer.sqlite` exists below the miner output root it is detected automatically. A different tracer can be supplied explicitly:

```powershell
python tools\miner\weapon-progression-probe.py "C:\path\to\miner-output" --tracer "C:\path\to\reference-tracer.sqlite"
```

Outputs are written by default to:

`<miner-output>\investigations\weapon-progression\`

- `weapon-progression-report.md` — human-readable high-value leads and aggregate Tier ratios.
- `weapon-progression-candidates.csv` — sortable evidence rows with source file and JSON path.
- `weapon-progression-investigation.json` — complete machine-readable evidence, Tier inference, and tracer hits.

The probe specifically hunts for:

- the existing five Tier stat rows per weapon;
- Blueprint Star / enhancement / quality fields;
- objects containing both Stars and Tier;
- Attack / Damage / Firepower values associated with either layer;
- numeric arrays that resemble Star/Tier scale, multiplier, coefficient, ratio, enhancement, or quality curves;
- provenance leads in `reference-tracer.sqlite` for likely progression terms.

### Evidence rule

Do not turn a discovered ratio into Dead Signal calculator logic merely because it looks plausible. A candidate model should reproduce multiple weapons across multiple Tier/Star combinations, with any remaining discrepancy explainable by the game's rounding behavior.

### Current integration status

The GitHub repository contains this post-extraction probe, but the Windows/local Game Miner application's source is not stored in this repository. The local miner should invoke this script after normal extraction/normalization, or its logic can be folded directly into that application when its source workspace is open in Codex.
