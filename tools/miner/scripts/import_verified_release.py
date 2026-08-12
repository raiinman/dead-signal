"""Import authored Miner source from the verified v1.5.7.4 Windows release.

This is a one-time recovery tool.  It never imports the frozen executable,
third-party runtime, generated output, or game files.  The package is accepted
only when its size and SHA-256 match the provenance recorded during migration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MINER = ROOT / "tools" / "miner"
EXPECTED_PACKAGE_SIZE = 31_452_630
EXPECTED_PACKAGE_SHA256 = "dff5a8b5e9602e3964c365f90d219899ca0f86ef196813a1cb4d0a5a6ded88e2"
PACKAGE_ROOT = "Dead Signal Miner/"

SOURCE_MEMBERS = (
    "_internal/extractor/normalize_weapons.py",
    "_internal/extractor/export_bindict.py",
    "_internal/extractor/combat_resolver.py",
    "_internal/extractor/link_published_images.py",
    "_internal/extractor/pvr_to_png.py",
    "_internal/extractor/find_zstd_dicts.py",
    "_internal/extractor/export_marshaled_bindict.py",
    "_internal/extractor/normalize_extended.py",
    "_internal/extractor/reference_images.py",
    "_internal/extractor/weapon_progression.py",
    "_internal/extractor/normalize_armor.py",
    "_internal/extractor/npk_extract.py",
    "_internal/neoxtractor/core/bindict/parser.py",
    "_internal/neoxtractor/core/bindict/__init__.py",
)

DOC_MEMBERS = (
    "PATCH-NOTES-v1.5.6-STATIC-WEAPON-STATS.txt",
    "PATCH-NOTES-v1.5.3-D0100-FORMATTER.txt",
    "PATCH-NOTES-Blueprint-Progression.md",
    "PATCH-NOTES-v1.5.7.4-RAW-LEVEL-FALLBACK-FIX.txt",
    "PATCH-NOTES-v1.5.7-CALIBRATION-STYLE-LOCALIZATION.txt",
    "PATCH-NOTES-v1.5.5-D0100-FINAL-DISPLAY.txt",
    "PATCH-NOTES-v1.5.7.3-CIRCULAR-REFERENCE-HOTFIX.txt",
    "PATCH-NOTES-v1.5.2.txt",
    "PATCH-NOTES-v1.5.7.2-EMBEDDED-PREFLIGHT-HOTFIX.txt",
    "PATCH-NOTES-v1.5.2.1-HOTFIX.txt",
    "PATCH-NOTES-v1.5.7.1-SNAPSHOT-FALLBACK-HOTFIX.txt",
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_destination(member: str) -> Path:
    relative = member.removeprefix("_internal/")
    destination = (MINER / "src" / relative).resolve()
    source_root = (MINER / "src").resolve()
    if source_root not in destination.parents:
        raise ValueError(f"Unsafe source destination: {destination}")
    return destination


def doc_destination(member: str) -> Path:
    destination = (MINER / "docs" / "package-v1.5.7.4" / Path(member).name).resolve()
    docs_root = (MINER / "docs" / "package-v1.5.7.4").resolve()
    if docs_root not in destination.parents:
        raise ValueError(f"Unsafe documentation destination: {destination}")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover verified Dead Signal Miner v1.5.7.4 source")
    parser.add_argument("package", type=Path, help="Original v1.5.7.4 Windows release ZIP")
    args = parser.parse_args()
    package = args.package.expanduser().resolve()

    if not package.is_file():
        raise SystemExit(f"Package not found: {package}")
    if package.stat().st_size != EXPECTED_PACKAGE_SIZE:
        raise SystemExit(
            f"Package size mismatch: expected {EXPECTED_PACKAGE_SIZE}, got {package.stat().st_size}"
        )
    package_hash = sha256_file(package)
    if package_hash != EXPECTED_PACKAGE_SHA256:
        raise SystemExit(
            "Package SHA-256 mismatch: "
            f"expected {EXPECTED_PACKAGE_SHA256}, got {package_hash}"
        )

    manifest_files = []
    with zipfile.ZipFile(package) as release:
        names = set(release.namelist())
        required = [PACKAGE_ROOT + member for member in (*SOURCE_MEMBERS, *DOC_MEMBERS)]
        required.append(PACKAGE_ROOT + "_internal/README.md")
        missing = sorted(set(required) - names)
        if missing:
            raise SystemExit("Verified package is missing required authored files: " + ", ".join(missing))

        for member in SOURCE_MEMBERS:
            archive_member = PACKAGE_ROOT + member
            payload = release.read(archive_member)
            destination = source_destination(member)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            manifest_files.append(
                {
                    "path": destination.relative_to(ROOT).as_posix(),
                    "package_member": archive_member,
                    "size": len(payload),
                    "sha256": sha256_bytes(payload),
                }
            )

        for member in DOC_MEMBERS:
            archive_member = PACKAGE_ROOT + member
            payload = release.read(archive_member)
            destination = doc_destination(member)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            manifest_files.append(
                {
                    "path": destination.relative_to(ROOT).as_posix(),
                    "package_member": archive_member,
                    "size": len(payload),
                    "sha256": sha256_bytes(payload),
                }
            )

        packaged_readme = release.read(PACKAGE_ROOT + "_internal/README.md")
        readme_destination = doc_destination("README-PACKAGED.md")
        readme_destination.parent.mkdir(parents=True, exist_ok=True)
        readme_destination.write_bytes(packaged_readme)
        manifest_files.append(
            {
                "path": readme_destination.relative_to(ROOT).as_posix(),
                "package_member": PACKAGE_ROOT + "_internal/README.md",
                "size": len(packaged_readme),
                "sha256": sha256_bytes(packaged_readme),
            }
        )

    manifest = {
        "schema_version": 1,
        "miner_version": "1.5.7.4",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "package": {
            "filename": package.name,
            "size": EXPECTED_PACKAGE_SIZE,
            "sha256": EXPECTED_PACKAGE_SHA256,
        },
        "scope": "Authored source and package documentation only; runtime and executable excluded.",
        "files": sorted(manifest_files, key=lambda row: row["path"]),
    }
    manifest_path = MINER / "SOURCE-MANIFEST-v1.5.7.4.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"Recovered {len(SOURCE_MEMBERS)} authored source files from verified package "
        f"{EXPECTED_PACKAGE_SHA256}."
    )
    print(f"Wrote provenance manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
