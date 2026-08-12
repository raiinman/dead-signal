"""Materialize the exact Dead Signal Miner v1.5.7.4 source snapshot.

The snapshot is stored as numbered Base64 text chunks because the GitHub
connector used for the one-time migration could write repository text files
but could not upload an arbitrary binary/release asset. This script fails
closed unless all chunks are present and the reconstructed ZIP matches the
known SHA-256 captured from the locally-built source-only snapshot.
"""

from __future__ import annotations

import base64
import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MINER = ROOT / "tools" / "miner"
IMPORT_DIR = MINER / "imports" / "v1.5.7.4"
EXPECTED_CHUNKS = 15
EXPECTED_SHA256 = "8f307bf54f8da494505d2aaa4a0fd9d11f818b043449489f5df166e80e54e2e6"


def main() -> int:
    parts = sorted(IMPORT_DIR.glob("source-v1.5.7.4.b64.*"))
    if len(parts) != EXPECTED_CHUNKS:
        raise SystemExit(
            f"Expected {EXPECTED_CHUNKS} source snapshot chunks, found {len(parts)}"
        )

    encoded = "".join(part.read_text(encoding="ascii").strip() for part in parts)
    payload = base64.b64decode(encoded, validate=True)
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if actual_sha256 != EXPECTED_SHA256:
        raise SystemExit(
            "Source snapshot SHA-256 mismatch: "
            f"expected {EXPECTED_SHA256}, got {actual_sha256}"
        )

    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary = Path(temporary_directory)
        archive = temporary / "source-v1.5.7.4.zip"
        archive.write_bytes(payload)
        unpacked = temporary / "unpacked"
        with zipfile.ZipFile(archive) as source_zip:
            source_zip.extractall(unpacked)

        for source_name in ("extractor", "neoxtractor"):
            source = unpacked / source_name
            destination = MINER / "src" / source_name
            if not source.is_dir():
                raise SystemExit(f"Snapshot is missing required source tree: {source_name}")
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source, destination)

        docs_source = unpacked / "docs"
        docs_destination = MINER / "docs" / "package-v1.5.7.4"
        if docs_destination.exists():
            shutil.rmtree(docs_destination)
        shutil.copytree(docs_source, docs_destination)

        packaged_readme = unpacked / "README-PACKAGED.md"
        if packaged_readme.is_file():
            shutil.copy2(packaged_readme, docs_destination / "README-PACKAGED.md")

    print(
        "Materialized Dead Signal Miner v1.5.7.4 source snapshot "
        f"(SHA-256 {EXPECTED_SHA256})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
