"""Find, extract, and convert artwork referenced by Once Human data tables.

This module is deliberately category-agnostic.  A Dead Signal content record is
not complete when its text/stats were captured but its display artwork was not.
The scanner therefore follows image-bearing fields in every table assigned to a
Dead Signal coverage domain, resolves those names through the game's UI texture
map and the resource archive index, and writes both web PNGs and a full audit
trail.  NXPK archives are opened read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import sqlite3
import struct
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Iterable

import texture2ddecoder
import zstandard
from PIL import Image, ImageFile

from npk_extract import Entry, decode_entry


CONVERTER_VERSION = 3
IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tga", ".ico",
    ".tif", ".tiff", ".dds", ".psd", ".pvr", ".ktx", ".ktx_low",
    ".astc", ".cbk",
}
IMAGE_FIELD = re.compile(
    r"(?:icon|image|img|picture|portrait|avatar|thumbnail|thumb|poster|"
    r"cover|banner|background|texture)(?:$|_)", re.IGNORECASE
)
NON_REFERENCE_FIELD = re.compile(
    r"(?:size|width|height|scale|offset|position|pos|color|colour|alpha|"
    r"count|amount|index|id)$", re.IGNORECASE
)
SAFE_REFERENCE = re.compile(r"^[A-Za-z0-9_./\\@+()\- ]+$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    temporary.replace(path)


def norm_path(value: str) -> str:
    return value.replace("\\", "/").strip("/").casefold()


def reference_stem(value: str) -> str:
    filename = PureWindowsPath(value.replace("/", "\\")).name.strip()
    return Path(filename).stem.casefold()


def looks_like_reference(field: str, value: object) -> bool:
    if not isinstance(value, str):
        return False
    value = value.strip()
    if not value or len(value) > 512 or value.isdigit():
        return False
    suffix = Path(PureWindowsPath(value.replace("/", "\\")).name).suffix.casefold()
    if suffix in IMAGE_EXTENSIONS:
        return True
    lowered_field = field.casefold()
    if not IMAGE_FIELD.search(lowered_field) or NON_REFERENCE_FIELD.search(lowered_field):
        return False
    return bool(SAFE_REFERENCE.fullmatch(value) and reference_stem(value))


def walk_references(value: object, path: str = "") -> Iterable[tuple[str, str, str]]:
    """Yield (JSON pointer, field name, raw reference) from one record."""
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            pointer = f"{path}/{key_text.replace('~', '~0').replace('/', '~1')}"
            if looks_like_reference(key_text, child):
                yield pointer, key_text, str(child).strip()
            if isinstance(child, (dict, list)):
                yield from walk_references(child, pointer)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            pointer = f"{path}/{index}"
            if isinstance(child, (dict, list)):
                yield from walk_references(child, pointer)


def load_texture_map(base: Path, current: Path) -> dict[str, str]:
    """Load the game's authoritative texture-name to UI-directory map."""
    result: dict[str, str] = {}
    for root in (base, current):
        path = root / "client_data" / "ui" / "texture_map.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        rows = payload.get("data", payload) if isinstance(payload, dict) else {}
        if not isinstance(rows, dict):
            continue
        for stem, directory in rows.items():
            if isinstance(stem, str) and isinstance(directory, str) and directory:
                result[reference_stem(stem)] = norm_path(directory)
    return result


def catalog_tables(catalog: Path) -> list[tuple[str, str, str, list[str]]]:
    """Return every mined table layer, carrying domain labels when known."""
    connection = sqlite3.connect(catalog)
    try:
        domains: dict[str, list[str]] = defaultdict(list)
        for domain, relative in connection.execute(
            "SELECT domain, relative_path FROM domain_tables ORDER BY domain"
        ):
            domains[str(relative)].append(str(domain))
        rows = []
        for relative, base_path, current_path in connection.execute(
            "SELECT relative_path, base_json_path, current_json_path FROM tables ORDER BY relative_path"
        ):
            relative_text = str(relative)
            # This table is the authoritative name-to-folder resolver.  Its
            # values are directories, not display-image references.
            if norm_path(relative_text).endswith("client_data/ui/texture_map.json"):
                continue
            table_domains = domains.get(relative_text, ["unclassified"])
            if base_path:
                rows.append(("base", relative_text, str(base_path), table_domains))
            if current_path:
                rows.append(("current", relative_text, str(current_path), table_domains))
        return rows
    finally:
        connection.close()


def prepare_audit(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS occurrences (
            occurrence_id INTEGER PRIMARY KEY,
            layer TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            domains TEXT NOT NULL,
            record_id TEXT NOT NULL,
            json_pointer TEXT NOT NULL,
            field_name TEXT NOT NULL,
            raw_reference TEXT NOT NULL,
            stem TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS occurrences_stem_idx ON occurrences(stem);
        CREATE INDEX IF NOT EXISTS occurrences_table_idx ON occurrences(relative_path);
        CREATE TABLE IF NOT EXISTS assets (
            stem TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            candidate_count INTEGER NOT NULL,
            archive_path TEXT,
            entry_index INTEGER,
            internal_path TEXT,
            output_path TEXT,
            web_path TEXT,
            width INTEGER,
            height INTEGER,
            error TEXT
        );
        """
    )
    connection.execute("DELETE FROM occurrences")
    connection.execute("DELETE FROM assets")
    connection.execute("DELETE FROM metadata")
    connection.commit()
    return connection


def scan_tables(
    table_catalog: Path,
    audit: sqlite3.Connection,
    log,
) -> dict[str, dict]:
    references: dict[str, dict] = {}
    pending = []
    tables = catalog_tables(table_catalog)
    for number, (layer, relative, file_name, domains) in enumerate(tables, start=1):
        try:
            payload = json.loads(Path(file_name).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as error:
            log(f"Artwork scan skipped unreadable table {relative}: {error}")
            continue
        records = payload.get("data", payload) if isinstance(payload, dict) else payload
        if isinstance(records, dict):
            record_rows = records.items()
        elif isinstance(records, list):
            record_rows = enumerate(records)
        else:
            record_rows = (("root", records),)
        domain_text = ",".join(sorted(domains))
        for record_id, record in record_rows:
            for pointer, field, raw_reference in walk_references(record):
                stem = reference_stem(raw_reference)
                if not stem:
                    continue
                item = references.setdefault(
                    stem,
                    {
                        "stem": stem,
                        "occurrences": 0,
                        "raw_references": set(),
                        "fields": set(),
                        "domains": set(),
                    },
                )
                item["occurrences"] += 1
                item["raw_references"].add(raw_reference)
                item["fields"].add(field)
                item["domains"].update(domains)
                pending.append(
                    (
                        layer,
                        relative,
                        domain_text,
                        str(record_id),
                        f"/data/{record_id}{pointer}",
                        field,
                        raw_reference,
                        stem,
                    )
                )
                if len(pending) >= 5000:
                    audit.executemany(
                        """
                        INSERT INTO occurrences (
                            layer, relative_path, domains, record_id, json_pointer,
                            field_name, raw_reference, stem
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        pending,
                    )
                    audit.commit()
                    pending.clear()
        if number % 500 == 0:
            log(
                f"Scanned artwork references in {number:,} of {len(tables):,} "
                f"classified table layers..."
            )
    if pending:
        audit.executemany(
            """
            INSERT INTO occurrences (
                layer, relative_path, domains, record_id, json_pointer,
                field_name, raw_reference, stem
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            pending,
        )
        audit.commit()
    return references


def _dds_dxgi_fallback(data: bytes) -> Image.Image:
    if len(data) < 148 or data[:4] != b"DDS ":
        raise ValueError("Not a DDS file")
    if int.from_bytes(data[4:8], "little") != 124 or data[84:88] != b"DX10":
        raise NotImplementedError("Unsupported DDS header")
    height = int.from_bytes(data[12:16], "little")
    width = int.from_bytes(data[16:20], "little")
    dxgi_format = int.from_bytes(data[128:132], "little")
    pixels = data[148:]
    expected = width * height * 4
    if len(pixels) < expected:
        raise ValueError("DDS pixel data is truncated")
    if dxgi_format in (87, 91):
        return Image.frombytes("RGBA", (width, height), pixels[:expected], "raw", "BGRA")
    if dxgi_format in (88, 93):
        return Image.frombytes("RGBX", (width, height), pixels[:expected], "raw", "BGRX").convert("RGBA")
    raise NotImplementedError(f"Unsupported DDS DXGI format {dxgi_format}")


def decode_blocks(
    fmt: str,
    data: bytes,
    width: int,
    height: int,
    block_x: int = 4,
    block_y: int = 4,
) -> Image.Image:
    if width <= 0 or height <= 0 or width > 32768 or height > 32768:
        raise ValueError(f"Invalid texture size {width}x{height}")
    if fmt == "ASTC":
        required = math.ceil(width / block_x) * math.ceil(height / block_y) * 16
        if len(data) < required:
            raise ValueError(f"ASTC payload truncated: expected {required}, got {len(data)}")
        decoded = texture2ddecoder.decode_astc(data[:required], width, height, block_x, block_y)
    elif fmt == "BC1":
        decoded = texture2ddecoder.decode_bc1(data, width, height)
    elif fmt == "BC3":
        decoded = texture2ddecoder.decode_bc3(data, width, height)
    elif fmt == "BC4":
        decoded = texture2ddecoder.decode_bc4(data, width, height)
    elif fmt == "BC5":
        decoded = texture2ddecoder.decode_bc5(data, width, height)
    elif fmt == "BC6":
        decoded = texture2ddecoder.decode_bc6(data, width, height)
    elif fmt == "BC7":
        decoded = texture2ddecoder.decode_bc7(data, width, height)
    elif fmt == "ETC1":
        decoded = texture2ddecoder.decode_etc1(data, width, height)
    elif fmt == "ETC2":
        decoded = texture2ddecoder.decode_etc2(data, width, height)
    elif fmt == "ETC2A1":
        decoded = texture2ddecoder.decode_etc2a1(data, width, height)
    elif fmt == "ETC2A8":
        decoded = texture2ddecoder.decode_etc2a8(data, width, height)
    elif fmt == "PVRTC":
        decoded = texture2ddecoder.decode_pvrtc(data, width, height, False)
    elif fmt == "RGBA8":
        return Image.frombytes("RGBA", (width, height), data, "raw", "RGBA")
    else:
        raise ValueError(f"Unsupported block format {fmt}")
    return Image.frombytes("RGBA", (width, height), decoded, "raw", "BGRA")


def pvr_image(data: bytes) -> Image.Image:
    if len(data) < 52:
        raise ValueError("PVR header is incomplete")
    version, _flags, pixel_format, _space, _channel, height, width, _depth, _surfaces, _faces, _mips, metadata_size = struct.unpack_from(
        "<IIQ9I", data, 0
    )
    if version != 0x03525650:
        raise ValueError(f"Unsupported PVR version {version:#x}")
    image_data = data[52 + metadata_size :]
    channel_format = pixel_format.to_bytes(8, "little")
    channels, bits = channel_format[:4], channel_format[4:]
    if channels in (b"rgba", b"bgra") and bits == b"\x08\x08\x08\x08":
        expected = width * height * 4
        if len(image_data) < expected:
            raise ValueError("Uncompressed PVR RGBA8 payload is truncated")
        raw_mode = "RGBA" if channels == b"rgba" else "BGRA"
        return Image.frombytes("RGBA", (width, height), image_data[:expected], "raw", raw_mode)
    if channels in (b"rgba", b"bgra") and bits == b"\x10\x10\x10\x10":
        expected = width * height * 8
        if len(image_data) < expected:
            raise ValueError("Uncompressed PVR RGBA16 payload is truncated")
        # Website PNGs are 8-bit RGBA. Preserve the most significant byte of
        # each little-endian 16-bit channel instead of rejecting the texture.
        reduced = bytearray(width * height * 4)
        source_order = (0, 1, 2, 3) if channels == b"rgba" else (2, 1, 0, 3)
        for pixel in range(width * height):
            source = pixel * 8
            target = pixel * 4
            for output_channel, input_channel in enumerate(source_order):
                reduced[target + output_channel] = image_data[source + input_channel * 2 + 1]
        return Image.frombytes("RGBA", (width, height), bytes(reduced), "raw", "RGBA")
    formats = {
        3: ("PVRTC", 4, 4),
        7: ("BC1", 4, 4),
        8: ("BC3", 4, 4),
        9: ("BC3", 4, 4),
        10: ("BC3", 4, 4),
        11: ("BC3", 4, 4),
        12: ("BC4", 4, 4),
        13: ("BC5", 4, 4),
        14: ("BC6", 4, 4),
        15: ("BC7", 4, 4),
        22: ("ETC2", 4, 4),
        23: ("ETC2A8", 4, 4),
        24: ("ETC2A1", 4, 4),
        27: ("ASTC", 4, 4), 28: ("ASTC", 5, 4),
        29: ("ASTC", 5, 5), 30: ("ASTC", 6, 5),
        31: ("ASTC", 6, 6), 32: ("ASTC", 8, 5),
        33: ("ASTC", 8, 6), 34: ("ASTC", 8, 8),
        35: ("ASTC", 10, 5), 36: ("ASTC", 10, 6),
        37: ("ASTC", 10, 8), 38: ("ASTC", 10, 10),
        39: ("ASTC", 12, 10), 40: ("ASTC", 12, 12),
    }
    if pixel_format not in formats:
        raise ValueError(f"Unsupported PVR pixel format {pixel_format}")
    fmt, block_x, block_y = formats[pixel_format]
    return decode_blocks(fmt, image_data, width, height, block_x, block_y)


def ktx_image(data: bytes) -> Image.Image:
    identifier = b"\xABKTX 11\xBB\r\n\x1A\n"
    if len(data) < 68 or data[:12] != identifier:
        raise ValueError("Unsupported or incomplete KTX file")
    values = struct.unpack_from("<13I", data, 12)
    if values[0] != 0x04030201:
        raise ValueError("Big-endian KTX files are not supported")
    internal_format, width, height, key_bytes = values[4], values[6], values[7], values[12]
    offset = 64 + key_bytes
    image_size = struct.unpack_from("<I", data, offset)[0]
    image_data = data[offset + 4 : offset + 4 + image_size]
    formats = {
        0x8058: ("RGBA8", 4, 4), 0x8D64: ("ETC1", 4, 4),
        0x9274: ("ETC2", 4, 4), 0x9276: ("ETC2A1", 4, 4),
        0x9278: ("ETC2A8", 4, 4),
    }
    astc_blocks = ((4, 4), (5, 4), (5, 5), (6, 5), (6, 6), (8, 5), (8, 6), (8, 8), (10, 5), (10, 6), (10, 8), (10, 10), (12, 10), (12, 12))
    for base in (0x93B0, 0x93D0):
        for index, block in enumerate(astc_blocks):
            formats[base + index] = ("ASTC", *block)
    if internal_format not in formats:
        raise ValueError(f"Unsupported KTX format {internal_format:#x}")
    fmt, block_x, block_y = formats[internal_format]
    return decode_blocks(fmt, image_data, width, height, block_x, block_y)


def astc_image(data: bytes) -> Image.Image:
    if len(data) < 16 or data[:4] != b"\x13\xAB\xA1\x5C":
        raise ValueError("ASTC header is incomplete")
    block_x, block_y = data[4], data[5]
    width = int.from_bytes(data[7:10], "little")
    height = int.from_bytes(data[10:13], "little")
    return decode_blocks("ASTC", data[16:], width, height, block_x, block_y)


def cbk_image(data: bytes) -> Image.Image:
    if len(data) < 28:
        raise ValueError("CompBlks header is incomplete")
    fmt = data[8:10]
    width = int.from_bytes(data[16:18], "little")
    height = int.from_bytes(data[18:20], "little")
    names = {b"\xF3\x83": "BC3", b"\x78\x92": "ETC2A8", b"\x74\x92": "ETC2"}
    if fmt not in names:
        raise ValueError(f"Unsupported CompBlks format {fmt.hex()}")
    return decode_blocks(names[fmt], data[28:], width, height)


def convert_to_png(data: bytes, extension: str, target: Path) -> tuple[int, int]:
    extension = extension.casefold().lstrip(".")
    # Some NXPK entries carry a stale extension. Trust the actual file magic
    # first so PNG/DDS/KTX/ASTC payloads are not sent through the PVR decoder.
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        image = Image.open(io.BytesIO(data))
    elif data.startswith(b"DDS "):
        try:
            image = Image.open(io.BytesIO(data))
            image.load()
        except (NotImplementedError, OSError):
            image = _dds_dxgi_fallback(data)
    elif data.startswith(b"\xABKTX 11\xBB\r\n\x1A\n"):
        image = ktx_image(data)
    elif data.startswith(b"\x13\xAB\xA1\x5C"):
        image = astc_image(data)
    elif extension == "pvr":
        image = pvr_image(data)
    elif extension in ("ktx", "ktx_low"):
        image = ktx_image(data)
    elif extension == "astc":
        image = astc_image(data)
    elif extension == "cbk":
        image = cbk_image(data)
    else:
        try:
            image = Image.open(io.BytesIO(data))
            image.load()
        except NotImplementedError:
            if extension == "dds":
                image = _dds_dxgi_fallback(data)
            else:
                raise
    if isinstance(image, ImageFile.ImageFile):
        image.load()
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, "PNG", compress_level=6)
    return int(image.width), int(image.height)


def score_candidate(row: sqlite3.Row, stem: str, texture_dir: str, raw_paths: set[str]) -> tuple[int, int, str]:
    internal = norm_path(row["internal_path"])
    without_ext = norm_path(str(PureWindowsPath(row["internal_path"]).with_suffix("")))
    score = 0
    if texture_dir and without_ext.endswith(f"{texture_dir}/{stem}"):
        score += 10_000
    if any(without_ext.endswith(norm_path(str(PureWindowsPath(raw).with_suffix("")))) for raw in raw_paths if "/" in raw or "\\" in raw):
        score += 5_000
    if norm_path(row["filename"]) in {norm_path(PureWindowsPath(raw).name) for raw in raw_paths}:
        score += 500
    archive_name = norm_path(str(row["archive_path"]))
    if archive_name.startswith("documents/") or "/documents/" in archive_name:
        score += 100
    if "/ui/" in f"/{internal}" or "icon" in internal:
        score += 25
    return score, int(row["original_size"]), internal


def candidate_rows(connection: sqlite3.Connection, stem: str) -> list[sqlite3.Row]:
    placeholders = ",".join("?" for _ in IMAGE_EXTENSIONS)
    return list(
        connection.execute(
            f"""
            SELECT archive_path, entry_index, internal_path, filename, extension,
                   original_size, compression, encryption, signature, offset,
                   compressed_size, compressed_crc, original_crc
            FROM entries
            WHERE stem = ? AND encryption = 0 AND extension IN ({placeholders})
            """,
            (stem, *sorted(IMAGE_EXTENSIONS)),
        )
    )


def safe_name(stem: str) -> str:
    cleaned = re.sub(r"[^a-z0-9._-]+", "-", stem.casefold()).strip("-._")
    return (cleaned or "image")[:100]


def extract_assets(
    install: Path,
    resource_index: Path,
    references: dict[str, dict],
    texture_map: dict[str, str],
    output: Path,
    dictionary_path: Path | None,
    audit: sqlite3.Connection,
    log,
) -> list[dict]:
    resource = sqlite3.connect(resource_index)
    resource.row_factory = sqlite3.Row
    dictionary = None
    if dictionary_path and dictionary_path.is_file():
        dictionary = zstandard.ZstdCompressionDict(dictionary_path.read_bytes())
    results = []
    archive_handles = {}
    extracted: dict[tuple[str, int], tuple[str, int, int]] = {}
    try:
        total = len(references)
        for number, (stem, meta) in enumerate(sorted(references.items()), start=1):
            rows = candidate_rows(resource, stem)
            raw_paths = {str(value) for value in meta["raw_references"]}
            ranked = sorted(
                rows,
                key=lambda row: score_candidate(row, stem, texture_map.get(stem, ""), raw_paths),
                reverse=True,
            )
            result = {
                "stem": stem,
                "raw_references": sorted(raw_paths),
                "fields": sorted(meta["fields"]),
                "domains": sorted(meta["domains"]),
                "occurrences": int(meta["occurrences"]),
                "candidate_count": len(rows),
                "status": "unresolved",
            }
            selected = ranked[0] if ranked else None
            if selected is None:
                result["error"] = "No readable image entry with this stem was found in the resource index"
            else:
                selected_score = score_candidate(selected, stem, texture_map.get(stem, ""), raw_paths)
                tied = [row for row in ranked if score_candidate(row, stem, texture_map.get(stem, ""), raw_paths)[:2] == selected_score[:2]]
                archive_relative = str(selected["archive_path"])
                internal = str(selected["internal_path"])
                key = (archive_relative, int(selected["entry_index"]))
                digest = hashlib.sha1(f"{archive_relative}\0{internal}".encode("utf-8")).hexdigest()[:12]
                shard = (stem[:2] or "_").replace(".", "_")
                relative_output = Path("assets") / "reference-images" / shard / f"{safe_name(stem)}-{digest}.png"
                target = output / relative_output
                try:
                    if key in extracted and (output / extracted[key][0]).is_file():
                        web_path, width, height = extracted[key]
                    else:
                        archive_path = install / Path(archive_relative)
                        handle = archive_handles.get(archive_relative)
                        if handle is None:
                            handle = archive_path.open("rb")
                            archive_handles[archive_relative] = handle
                        entry = Entry(
                            int(selected["entry_index"]), int(selected["signature"]),
                            int(selected["offset"]), int(selected["compressed_size"]),
                            int(selected["original_size"]), int(selected["compressed_crc"]),
                            int(selected["original_crc"]), int(selected["compression"]),
                            int(selected["encryption"]), internal,
                        )
                        payload = decode_entry(handle, entry, dictionary)
                        width, height = convert_to_png(payload, str(selected["extension"]), target)
                        web_path = relative_output.as_posix()
                        extracted[key] = (web_path, width, height)
                    result.update(
                        {
                            "status": "resolved-ambiguous" if len(tied) > 1 else "resolved",
                            "archive": archive_relative,
                            "archive_entry": int(selected["entry_index"]),
                            "archive_path": internal,
                            "source_extension": str(selected["extension"]),
                            "asset": web_path,
                            "width": width,
                            "height": height,
                        }
                    )
                    if len(tied) > 1:
                        result["review_note"] = f"{len(tied)} equally ranked candidates; deterministic best candidate was retained"
                except Exception as error:  # Preserve every failure in the audit.
                    result["status"] = "conversion-failed"
                    result["error"] = f"{type(error).__name__}: {error}"
            audit.execute(
                """
                INSERT INTO assets (
                    stem, status, candidate_count, archive_path, entry_index,
                    internal_path, output_path, web_path, width, height, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stem, result["status"], result["candidate_count"],
                    result.get("archive"), result.get("archive_entry"),
                    result.get("archive_path"), str((output / result["asset"]).resolve()) if result.get("asset") else None,
                    result.get("asset"), result.get("width"), result.get("height"), result.get("error"),
                ),
            )
            results.append(result)
            if number % 250 == 0:
                audit.commit()
                log(f"Resolved and converted {number:,} of {total:,} referenced artwork names...")
        audit.commit()
        return results
    finally:
        for handle in archive_handles.values():
            handle.close()
        resource.close()


def run(args: argparse.Namespace) -> dict:
    log = print
    audit = prepare_audit(args.audit)
    try:
        log("Scanning every Dead Signal data domain for referenced artwork...")
        references = scan_tables(args.table_catalog, audit, log)
        log(f"Found {len(references):,} distinct referenced artwork names.")
        texture_map = load_texture_map(args.base, args.current)
        log(f"Loaded {len(texture_map):,} authoritative UI texture locations.")
        assets = extract_assets(
            args.install, args.resource_index, references, texture_map,
            args.output, args.zstd_dictionary, audit, log,
        )
        counts: dict[str, int] = defaultdict(int)
        for asset in assets:
            counts[str(asset["status"])] += 1
        manifest = {
            "schema_version": 2,
            "converter_version": CONVERTER_VERSION,
            "created_utc": utc_now(),
            "scope": "All image-bearing fields in every structured table captured by the complete Dead Signal snapshot",
            "audit_database": str(args.audit.resolve()),
            "counts": {
                "table_occurrences": int(audit.execute("SELECT COUNT(*) FROM occurrences").fetchone()[0]),
                "distinct_references": len(assets),
                **dict(sorted(counts.items())),
            },
            "lookup": {
                asset["stem"]: asset["asset"]
                for asset in assets
                if asset.get("asset")
            },
            "assets": assets,
        }
        write_json(args.manifest, manifest)
        audit.executemany(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            {
                "schema_version": "2",
                "converter_version": str(CONVERTER_VERSION),
                "created_utc": manifest["created_utc"],
                "manifest": str(args.manifest.resolve()),
            }.items(),
        )
        audit.commit()
        log(
            "Referenced artwork complete: "
            f"{counts.get('resolved', 0) + counts.get('resolved-ambiguous', 0):,} converted, "
            f"{counts.get('unresolved', 0):,} unresolved, "
            f"{counts.get('conversion-failed', 0):,} conversion failures."
        )
        return manifest
    finally:
        audit.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract all game artwork referenced by Dead Signal data")
    parser.add_argument("--install", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--table-catalog", type=Path, required=True)
    parser.add_argument("--resource-index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--zstd-dictionary", type=Path)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
