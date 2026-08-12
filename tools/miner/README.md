# Dead Signal Miner

`tools/miner/` is the canonical source for the Dead Signal Once Human Miner. The application reads the user's installed game files locally and produces structured, website-ready snapshots without uploading the game files or spending AI usage on extraction.

## Maintained layout

```text
tools/miner/
├── src/
│   ├── dead_signal_miner.py     Windows GUI and headless entrypoint
│   ├── miner_core.py            local extraction pipeline coordinator
│   ├── update_manager.py        update discovery, download, and verification
│   ├── miner_updater.py         out-of-process Windows update installer
│   ├── extractor/               recovered and maintained extraction engine
│   └── neoxtractor/             data-only bindict parser
├── assets/                      application icon
├── tests/                       updater and source-integrity tests
├── release/latest.json          in-app update manifest
├── build.ps1                    reproducible PyInstaller build
├── package-release.ps1          versioned ZIP and SHA-256 generation
├── setup-build.ps1              isolated Windows build environment
├── VERSION                      one canonical application version
└── MIGRATION-v1.5.7.4.md        recovered-source provenance
```

Generated Miner output, game archives, SQLite indexes, Python runtimes, executables, and release ZIPs are intentionally excluded from Git.

## Run from source

Install `requirements.txt`, then run `Start Dead Signal Miner.cmd` or:

```powershell
$env:PYTHONPATH = 'tools/miner/src;tools/miner/src/extractor;tools/miner/src/neoxtractor'
python tools/miner/src/dead_signal_miner.py
```

The existing interface remains centered on one action: **Mine Complete Database**. It includes all database categories and referenced display artwork. The optional WordPress copy is local-only and does not deploy the production website.

## Verify

```powershell
python -m compileall -q tools/miner/src tools/miner/tests
python -m unittest discover -s tools/miner/tests -v
python tools/miner/src/dead_signal_miner.py --self-test
```

The self-test requires the dependencies and a detectable Once Human installation. It checks the maintained engine files and imports without mining the game.

## Build and release

See `RELEASING.md`. `setup-build.ps1` creates a dedicated build environment, `build.ps1` produces the Miner plus its separate updater helper, and `package-release.ps1` creates the versioned ZIP/checksum. Publish `release/latest.json` only after its exact release asset is online and verified.

The in-app updater accepts only GitHub-hosted HTTPS downloads and verifies declared byte size and SHA-256 before installation. Installation happens in a separate helper after the Miner closes, with rollback for files already being replaced.

## Source and data safety

- GitHub source is authoritative; release ZIPs are artifacts.
- The Miner keeps the existing NPK/PYC extraction design and does not execute transformed game bytecode.
- Do not commit generated snapshots, `reference-tracer.sqlite`, raw game archives, or packaged runtimes.
- Do not turn discovered ratios into calculator formulas without multi-entity evidence and rounding validation.
- Production hosting remains governed by the repository's copy-only cPanel process; Miner work must not modify it.

