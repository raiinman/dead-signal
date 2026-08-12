# Dead Signal Miner v1.5.7.4 source recovery

This record documents the one-time recovery of maintained Miner source from the verified Windows v1.5.7.4 package.

## Verified provenance

- Package: `Dead-Signal-Miner-v1.5.7.4-Raw-Level-Fallback-Source-Fix.zip`
- Package size: 31,452,630 bytes
- Package SHA-256: `dff5a8b5e9602e3964c365f90d219899ca0f86ef196813a1cb4d0a5a6ded88e2`
- Frozen executable SHA-256: `8661ba1b5ede49d9d2f39380721694e80672ca7112419bd4ec3b8401f52cca16`
- Packaged runtime: Python 3.11
- Recovery manifest: `SOURCE-MANIFEST-v1.5.7.4.json`

Fourteen authored engine/parser files and twelve package documents were imported. The executable, `_internal` Python runtime, third-party packages, game files, generated output, and indexes were excluded.

## Transport snapshot correction

The earlier Base64 transport bridge was not lossless despite producing a structurally valid ZIP. Its reconstructed SHA-256 was:

`d6680766d1d9014c14f2c5af6480c37e4748abde2b7cf3e9f52a91b59a0e3400`

That did not match the claimed source snapshot SHA-256:

`8f307bf54f8da494505d2aaa4a0fd9d11f818b043449489f5df166e80e54e2e6`

Comparison with the verified release proved that 25 of 26 files matched and `extractor/weapon_progression.py` alone had systematic byte substitutions. The corrupted file hash was `179da89e7b9fe8152e1e3abbe70988e12c731008b489b720cf0fe79f7f2a0e9d`; the correct release file hash is `b2ad070e1f96fd7dae5a15094ff7d7a9a22ccee2f19703865d77beefffad94df`.

The canonical source tree was therefore recovered directly from the exact verified package with `scripts/import_verified_release.py`. The obsolete Base64 materialization path is retired. Normal source under `tools/miner/src/` is now authoritative and CI only verifies it; CI never writes back to `main`.

## Recovered engine baseline

Recovered extractor modules include normalization for weapons, armor, extended categories, combat resolution, images, progression, NPK extraction, bindict export, and the NeoX bindict parser. Dependencies remain pinned in `requirements.txt`.

The v1.5.7.4 circular-reference fix resolves the exact raw buff level, falls back to level 1 where necessary, and deep-copies the presentation row. Version 1.5.8.0 adds stale serialization-diagnostic cleanup before each combat-resolution pass without changing that extraction design.

## Maintained application source

The verified package did not expose its frozen GUI entrypoint as loose source. Codex restored the project's prior maintained red/black Miner GUI and local pipeline coordinator, connected them to the recovered v1.5.7.4 engine, and added maintained build/updater source. This is a recreation from the project's own earlier GUI foundation, not a claim that the frozen entrypoint was decompiled.

Future work starts from GitHub source. Do not ask the user for another source ZIP unless provenance recovery itself is the explicit task.

