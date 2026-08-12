"""Find embedded Zstandard dictionaries in ordinary installed game files.

The scanner is read-only and skips NPK archives by default so it can search
executables, DLLs, package maps, and metadata without walking 124 GiB of
resource payloads.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


MAGIC = b"\x37\xa4\x30\xec"


def scan_file(path: Path, chunk_size: int = 4 * 1024 * 1024):
    overlap = len(MAGIC) + 4
    tail = b""
    absolute = 0
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            data = tail + chunk
            start = 0
            while True:
                found = data.find(MAGIC, start)
                if found < 0:
                    break
                if found + 8 <= len(data):
                    yield absolute - len(tail) + found, struct.unpack_from(
                        "<I", data, found + 4
                    )[0]
                start = found + 1
            absolute += len(chunk)
            tail = data[-overlap:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--include-npk", action="store_true")
    parser.add_argument("--dict-id", type=int)
    args = parser.parse_args()

    scanned_files = 0
    scanned_bytes = 0
    matches = []
    for path in args.root.rglob("*"):
        if not path.is_file():
            continue
        if not args.include_npk and path.suffix.lower() == ".npk":
            continue
        scanned_files += 1
        scanned_bytes += path.stat().st_size
        for offset, dict_id in scan_file(path):
            if args.dict_id is None or args.dict_id == dict_id:
                matches.append(
                    {
                        "path": str(path),
                        "offset": offset,
                        "dict_id": dict_id,
                    }
                )

    print(
        json.dumps(
            {
                "root": str(args.root.resolve()),
                "scanned_files": scanned_files,
                "scanned_bytes": scanned_bytes,
                "matches": matches,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
