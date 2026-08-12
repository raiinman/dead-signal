"""Read-only extractor for unencrypted NeoX NXPK archives.

The script never modifies the source archive. It supports the compression
types used by the installed Once Human patch archive and can filter entries
by their original path before extracting them.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path, PureWindowsPath

import lz4.block
import zstandard


@dataclass
class Entry:
    index: int
    signature: int
    offset: int
    compressed_size: int
    original_size: int
    compressed_crc: int
    original_crc: int
    compression: int
    encryption: int
    path: str = ""


def read_archive(archive_path: Path) -> tuple[dict[str, int | str], list[Entry]]:
    with archive_path.open("rb") as source:
        header_bytes = source.read(24)
        if len(header_bytes) != 24:
            raise ValueError("Archive header is incomplete")
        magic, file_count, var1, encrypt_mode, hash_mode, index_offset = struct.unpack(
            "<4s5I", header_bytes
        )
        if magic != b"NXPK":
            raise ValueError(f"Expected NXPK, found {magic!r}")

        info_size = 28
        source.seek(index_offset)
        index_bytes = source.read(file_count * info_size)
        if len(index_bytes) != file_count * info_size:
            raise ValueError("Archive index is incomplete")

        entries: list[Entry] = []
        for index in range(file_count):
            values = struct.unpack_from("<6I2H", index_bytes, index * info_size)
            entries.append(Entry(index, *values))

        names_offset = index_offset + (file_count * info_size)
        source.seek(names_offset)
        names_header = source.read(16)
        if names_header[:4] == b"NXFN":
            _, _, names_size, names_size_2 = struct.unpack("<4s3I", names_header)
            if names_size != names_size_2:
                raise ValueError("NXFN filename table lengths disagree")
            names = [
                item.decode("utf-8", errors="replace")
                for item in source.read(names_size).split(b"\x00")
                if item
            ]
            if len(names) != file_count:
                raise ValueError(
                    f"NXFN contains {len(names)} paths for {file_count} entries"
                )
            for entry, name in zip(entries, names, strict=True):
                entry.path = name

    metadata: dict[str, int | str] = {
        "archive": str(archive_path),
        "magic": magic.decode("ascii"),
        "file_count": file_count,
        "var1": var1,
        "encrypt_mode": encrypt_mode,
        "hash_mode": hash_mode,
        "index_offset": index_offset,
        "named_entries": sum(bool(entry.path) for entry in entries),
    }
    return metadata, entries


def decode_entry(
    source, entry: Entry, zstd_dictionary: zstandard.ZstdCompressionDict | None = None
) -> bytes:
    if entry.encryption != 0:
        raise ValueError(
            f"Entry {entry.index} is encrypted; this extractor intentionally will not bypass it"
        )
    source.seek(entry.offset)
    payload = source.read(entry.compressed_size)
    if entry.compression == 0:
        decoded = payload
    elif entry.compression == 1:
        decoded = zlib.decompress(payload)
    elif entry.compression in (2, 5):
        decoded = lz4.block.decompress(
            payload, uncompressed_size=entry.original_size
        )
    elif entry.compression == 3:
        decoded = zstandard.ZstdDecompressor().decompress(
            payload, max_output_size=entry.original_size
        )
    elif entry.compression == 10:
        if zstd_dictionary is None:
            raise ValueError(
                "Compression flag 10 requires the game's shared Zstandard dictionary"
            )
        decoded = zstandard.ZstdDecompressor(dict_data=zstd_dictionary).decompress(
            payload, max_output_size=entry.original_size
        )
    else:
        raise ValueError(f"Unsupported compression flag {entry.compression}")
    if len(decoded) != entry.original_size:
        raise ValueError(
            f"Entry {entry.index} decoded to {len(decoded)} bytes; expected {entry.original_size}"
        )
    return decoded


def safe_output_path(output_root: Path, archive_name: str) -> Path:
    parts = [part for part in PureWindowsPath(archive_name).parts if part not in ("\\", "/")]
    if not parts or any(part in (".", "..") for part in parts):
        raise ValueError(f"Unsafe archive path: {archive_name!r}")
    target = output_root.joinpath(*parts).resolve()
    root = output_root.resolve()
    if root not in target.parents and target != root:
        raise ValueError(f"Archive path escapes output directory: {archive_name!r}")
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--match", default=".", help="Case-insensitive regex matched against archive paths")
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--list-only", action="store_true")
    parser.add_argument(
        "--zstd-dictionary",
        type=Path,
        help="Shared Zstandard dictionary for compression flag 10 entries",
    )
    args = parser.parse_args()

    metadata, entries = read_archive(args.archive)
    matcher = re.compile(args.match, re.IGNORECASE)
    selected = [entry for entry in entries if matcher.search(entry.path)]

    inventory = {
        "metadata": metadata,
        "match": args.match,
        "matched_entries": len(selected),
        "entries": [asdict(entry) for entry in selected],
    }
    if args.inventory:
        args.inventory.parent.mkdir(parents=True, exist_ok=True)
        args.inventory.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    print(json.dumps({**metadata, "matched_entries": len(selected)}, indent=2))
    for entry in selected[:100]:
        print(
            f"{entry.index:5d}  {entry.original_size:9d}  "
            f"zip={entry.compression} enc={entry.encryption}  {entry.path}"
        )
    if len(selected) > 100:
        print(f"... {len(selected) - 100} more matches")

    if args.list_only:
        return 0

    zstd_dictionary = None
    if args.zstd_dictionary:
        zstd_dictionary = zstandard.ZstdCompressionDict(
            args.zstd_dictionary.read_bytes()
        )

    args.output.mkdir(parents=True, exist_ok=True)
    with args.archive.open("rb") as source:
        for entry in selected:
            target = safe_output_path(args.output, entry.path or f"{entry.signature:08x}.bin")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(decode_entry(source, entry, zstd_dictionary))
    print(f"Extracted {len(selected)} entries to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
