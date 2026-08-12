# Dead Signal Miner

Dead Signal Miner is a local, read-only Windows app that captures the complete
game-derived data foundation for the Dead Signal website.

## What the one-click run does

1. Finds the Steam installation or uses the folder you select.
2. Fingerprints `script.npk` and `Documents/script.npk` with SHA-256.
3. Finds and validates the matching Zstandard dictionary in `ONCE_HUMAN.exe`.
4. Extracts every readable structured script entry from the base and patch layers.
5. Parses NeoX bindict payloads from `.pyc` files without executing bytecode.
6. Merges English base localization with current patch tables.
7. Builds a queryable catalog spanning every structured table and Dead Signal domain.
8. Builds a reusable SQLite index of roughly two million named resource entries,
   including the archive coordinates needed for exact extraction.
9. Scans every mined structured table for display-art fields and preserves
   the table, record, field, and raw image reference in a searchable audit.
10. Resolves those references through the game's UI texture map and resource
    archives, then converts PVR, KTX, ASTC, DDS, CompBlks, and ordinary image
    formats to website-ready PNG files.
11. Generates website-ready Weapons, Armor, Mods, Calibrations, Ammo,
    Attachments, Cradles, Deviations, Food/Consumables, Buffs, Statuses,
    Keywords, Skills, Stat Definitions, and Progression datasets.
12. Links the exact extracted display image back onto every published record and
    writes a per-category image coverage report.
13. Optionally copies every finished dataset and the complete artwork library into the
    local WordPress Studio plugin.

## Combat-resolution layer

The miner keeps the existing archive extraction system and adds a depth pass over
the finished snapshots. `combat_resolver.py` provides reusable `TableCorpus`,
`ReferenceTracer`, `StatResolver`, `ModApplicabilityResolver`, and
`BuffLogicResolver` components. The pass:

- copies structured buff metadata from the sharded `buff_data*.json` definitions;
- applies per-level dynamic parameters before decoding referenced logic trees;
- resolves common combat nodes into effects and conditions while preserving raw
  unknown nodes and source-table provenance;
- resolves stats, calibration ranges, mod applicability, and mod effects;
- classifies player-facing ammunition, consumables, and Deviations;
- adds exact equipment tier, strengthening, and blueprint progression rows;
- automatically investigates **Blueprint Stars × Gear Tier I–V → displayed weapon stats**, using the mined `strength_lv` progression axis and direct `preset_attack_radio` per-blueprint Attack multiplier while keeping Gear Tier on its separate five-row path;
- scans every extracted PYC for progression operands during table export, persists code-object/disassembly evidence when compatible, and ranks possible multiplication/rounding consumers without executing game bytecode;
- writes `weapon-progression-investigation.json`, `weapon-progression-pyc-consumers.json`, and ranked progression candidate/report files without declaring the final UI rounding rule until it is actually recovered;
- writes a deduplicated `relationships.json` graph;
- builds a cached SQLite reference index over the existing raw table corpus.

Unknown mechanics are marked `partial` or `unresolved`; they are never represented
as empty-but-resolved effects. Ranked audit files are written under
`published/reports/`.

The reference tracer can also be called directly against an existing snapshot:

```powershell
python extractor\combat_resolver.py --base <base-tables> --current <current-tables> --published <published-folder> --trace 589117000
```

No game, Steam, or anti-cheat file is modified. The miner does not upload files
and does not call an AI service.

## Start it

Double-click `Start Dead Signal Miner.cmd`. The packaged release uses
`Dead Signal Miner.exe` instead and does not require opening a terminal.

Every run is a **Complete Dead Signal Harvest**. It captures all structured data
needed for current and future database categories and every display image those
records reference. Artwork is required data; there is no weapon-only switch.
Expect the first run to use several GiB of disk space. Later runs reuse unchanged
archive hashes, resource indexes, and converted artwork.

## Coverage contract

The complete snapshot captures the game-derived foundation for Tech, weapons,
accessories, armor, Deviants, enemies and bosses, items, materials, currencies,
crafting, mods, build components, maps, locations, seasons, scenarios, events,
quests, achievements, vendors, drops, building, furniture, consumables, and
vehicles.

Community loadouts are hybrid records: their equipment facts come from the game,
but the loadout and strategy are written by players. Guides and news are editorial.
Availability and acquisition verification requires dated in-game screenshots or
video. The miner records those boundaries in `catalogs/coverage-contract.json`.

## Output layout

```text
Dead Signal Miner/
|-- dictionaries/        validated Zstandard dictionaries
|-- catalogs/            coverage contract plus table/resource SQLite indexes
|-- manifests/           update and artwork state records
|-- snapshots/
|   `-- full/            complete base and current script snapshots
|-- published/
|   |-- data/            all category JSON + artwork manifest/coverage report
|   |-- indexes/         cached reference-tracer SQLite index
|   |-- reports/         resolution, validation, known-entity, and unresolved audits
|   `-- assets/
|       `-- reference-images/  converted artwork for all covered domains
|-- scratch/             temporary decoded textures
`-- last-run.json        complete provenance for the latest run
```

Unchanged archive hashes and archive-level asset index records are reused, so the
large base layer is not extracted again after every patch.

## Technical credits

The bindict parser and image-format research are from the open-source NeoXtractor
project by MarcosVLl2 and contributors. Dead Signal's NXPK, normalization,
localization, reference resolution, and web-asset pipeline wrap the locally
validated extraction work for this site.
