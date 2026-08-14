#!/usr/bin/env python3
"""Safely materialize one complete Dead Signal Miner ZIP into the repository.

Developer-side helper only. It does not run on cPanel and does not change the
copy-only deployment architecture. The archive is extracted to a temporary
directory, every member path is checked against traversal, and the existing
all-seven transactional materializer remains the authority for validation and
repository writes.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import zipfile
from pathlib import Path
from types import ModuleType


def _load_materializer(site_dir: Path) -> ModuleType:
    path = site_dir / "materialize-published-snapshot.py"
    spec = importlib.util.spec_from_file_location("dead_signal_snapshot_materializer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load transactional materializer: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _safe_destination(root: Path, member: str) -> Path:
    destination = (root / member).resolve()
    try:
        destination.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"Archive member escapes extraction root: {member!r}") from error
    return destination


def _extract_archive(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as source:
        for info in source.infolist():
            member = info.filename.replace("\\", "/")
            if not member or member.endswith("/"):
                _safe_destination(destination, member).mkdir(parents=True, exist_ok=True)
                continue
            target = _safe_destination(destination, member)
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open(info, "r") as input_stream, target.open("wb") as output_stream:
                while True:
                    block = input_stream.read(1024 * 1024)
                    if not block:
                        break
                    output_stream.write(block)


def _published_root(extracted: Path) -> Path:
    if (extracted / "web").is_dir():
        return extracted
    candidates = [path.parent for path in extracted.rglob("web/weapons.json")]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError("Miner ZIP does not contain web/weapons.json")
    raise ValueError(f"Miner ZIP contains multiple candidate published roots: {candidates}")


def materialize_zip(
    archive: Path,
    *,
    repository_root: Path,
    dry_run: bool = False,
) -> dict:
    archive = archive.expanduser().resolve()
    if not archive.is_file():
        raise FileNotFoundError(f"Miner ZIP not found: {archive}")
    if not zipfile.is_zipfile(archive):
        raise ValueError(f"Not a valid ZIP archive: {archive}")

    site_dir = Path(__file__).resolve().parent
    materializer = _load_materializer(site_dir)
    repository_root = repository_root.expanduser().resolve()

    with tempfile.TemporaryDirectory(prefix="dead-signal-miner-zip-") as folder:
        extracted = Path(folder)
        _extract_archive(archive, extracted)
        published = _published_root(extracted)
        report = materializer.ingest_snapshot(
            published,
            repository_root=repository_root,
            dry_run=dry_run,
        )
    report["archive"] = str(archive)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safely validate/materialize all seven Dead Signal web contracts from a Miner ZIP"
    )
    parser.add_argument("archive", type=Path, help="Fresh Miner ZIP")
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=None,
        help="Dead Signal repository root (default: inferred from this script)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate all seven contracts without replacing outputs")
    parser.add_argument("--report", type=Path, default=None, help="Optional JSON receipt path")
    args = parser.parse_args()

    repository_root = (
        args.repository_root.expanduser().resolve()
        if args.repository_root
        else Path(__file__).resolve().parents[2]
    )
    report = materialize_zip(args.archive, repository_root=repository_root, dry_run=args.dry_run)
    encoded = json.dumps(report, indent=2, sort_keys=True)
    if args.report:
        report_path = args.report.expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
