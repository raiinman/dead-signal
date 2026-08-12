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

