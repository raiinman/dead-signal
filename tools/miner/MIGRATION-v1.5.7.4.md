# Dead Signal Miner v1.5.7.4 — GitHub Source Migration

This record documents the one-time migration of the user-supplied Windows Miner package into the canonical GitHub source tree.

## Provenance

- Uploaded package: `Dead-Signal-Miner-v1.5.7.4-Raw-Level-Fallback-Source-Fix(1).zip`
- Original package size: 31,452,630 bytes
- Original package SHA-256: `dff5a8b5e9602e3964c365f90d219899ca0f86ef196813a1cb4d0a5a6ded88e2`
- Frozen executable: `Dead Signal Miner/Dead Signal Miner.exe`
- Executable size: 3,247,010 bytes
- Executable SHA-256: `8661ba1b5ede49d9d2f39380721694e80672ca7112419bd4ec3b8401f52cca16`
- Source-only migration snapshot SHA-256: `8f307bf54f8da494505d2aaa4a0fd9d11f818b043449489f5df166e80e54e2e6`
- Miner version: `1.5.7.4`
- Packaged runtime: Python 3.11

## Recovered maintained source

Fourteen authored Python source files were recovered from the package:

### Extractor engine

- `normalize_weapons.py`
- `export_bindict.py`
- `combat_resolver.py`
- `link_published_images.py`
- `pvr_to_png.py`
- `find_zstd_dicts.py`
- `export_marshaled_bindict.py`
- `normalize_extended.py`
- `reference_images.py`
- `weapon_progression.py`
- `normalize_armor.py`
- `npk_extract.py`

### NeoX bindict parser

- `neoxtractor/core/bindict/parser.py`
- `neoxtractor/core/bindict/__init__.py`

The package also contained patch notes and its packaged `_internal/README.md`; those are preserved under `tools/miner/docs/package-v1.5.7.4/` when the source snapshot is materialized.

## Dependency baseline

The packaged environment identified these application dependencies:

- `Pillow==12.3.0`
- `lz4==4.4.5`
- `texture2ddecoder==1.0.6`
- `zstandard==0.25.0`

They are pinned in `tools/miner/requirements.txt`.

## Important source gap

The Windows GUI/launcher source was **not present as a loose `.py` file** in the supplied package. That entrypoint is frozen inside `Dead Signal Miner.exe`.

This migration therefore establishes the complete recovered extraction/normalization engine as canonical source, but it does not pretend that the existing GUI/launcher source was recovered. The GUI entrypoint must be recovered separately or recreated as maintained source before features such as the planned in-app updater can be implemented cleanly.

## Binary/runtime exclusions

The normal Git tree intentionally does not contain:

- the full PyInstaller `_internal/` runtime
- Python DLLs and third-party runtime baggage
- the 31 MB packaged ZIP
- the frozen EXE
- generated Miner output
- raw game archives
- SQLite tracer/index databases

These are build/runtime/generated artifacts, not the editable source of truth.

## Lossless transport bridge

The GitHub connector available during migration could write repository text files but could not attach an arbitrary local binary file to a GitHub Release. To avoid manually retyping large source modules, a source-only ZIP was Base64-encoded into 15 numbered text chunks under:

`tools/miner/imports/v1.5.7.4/`

`tools/miner/scripts/materialize_source_snapshot.py` reconstructs that ZIP and **fails closed** unless the reconstructed bytes match the expected source snapshot SHA-256 above.

The GitHub Actions materialization workflow then uses Python 3.11 to compile-check the recovered source before committing the materialized tree.

## v1.5.7.4 behavior baseline

The included v1.5.7.4 patch notes identify the circular-reference root cause as `raw_level_definition` pointing back to a normalized parent. The source fix resolves the exact raw level, falls back to level 1 when necessary, and deep-copies the presentation row rather than creating the parent back-reference. The cycle-safe serialization diagnostics remain a defensive layer.

This version is the baseline from which future Miner source changes should be made in GitHub.
