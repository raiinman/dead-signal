# Dead Signal Miner releases

The editable Miner lives in `tools/miner/`. Packaged executables and ZIP files are generated release artifacts and are not committed to the repository.

## Build a Windows package

From PowerShell in `tools/miner/`:

```powershell
.\setup-build.ps1
.\build.ps1
python src\dead_signal_miner.py --self-test
.\dist\Dead Signal Miner\Dead Signal Miner.exe --self-test
.\package-release.ps1
```

The packaging script prints the ZIP's exact byte size and SHA-256 checksum.

## Publish safely

1. Test the unpacked application and its `--self-test` result.
2. Upload the generated ZIP as a GitHub release asset.
3. Confirm the public asset size and checksum match the local values.
4. Update `release/latest.json` last with the new version, HTTPS GitHub asset URL, SHA-256, and byte size.

Publishing the manifest last prevents installed Miners from seeing an update before its verified package exists. The application downloads only GitHub-hosted HTTPS packages and checks both size and SHA-256 before asking the separate updater helper to install anything.
## v1.5.12.0 publishing contract

The source patch may land on `main` before the packaged Windows update. That is intentional. The installed Miner discovers updates only through `release/latest.json`, so keep that manifest on the last verified release until the new ZIP is built, uploaded, and checksum-verified.

For v1.5.12.0 specifically, verify that a completed mine creates `published/web/`, `published/reports/data-quality.json`, `published/reports/change-report.json`, and `published/snapshot-manifest.json` before publishing the updater manifest.

