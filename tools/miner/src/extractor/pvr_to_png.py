"""Convert PVR v3 DXT5/BC3 textures to RGBA PNG using only the standard library."""

from __future__ import annotations

import argparse
import binascii
import struct
import zlib
from pathlib import Path


PVR3_MAGIC = 0x03525650
PVR_PIXEL_FORMAT_DXT5 = 11


def rgb565(value: int) -> tuple[int, int, int]:
    red = (value >> 11) & 0x1F
    green = (value >> 5) & 0x3F
    blue = value & 0x1F
    return (
        (red << 3) | (red >> 2),
        (green << 2) | (green >> 4),
        (blue << 3) | (blue >> 2),
    )


def alpha_palette(alpha_0: int, alpha_1: int) -> list[int]:
    if alpha_0 > alpha_1:
        return [
            alpha_0,
            alpha_1,
            (6 * alpha_0 + alpha_1) // 7,
            (5 * alpha_0 + 2 * alpha_1) // 7,
            (4 * alpha_0 + 3 * alpha_1) // 7,
            (3 * alpha_0 + 4 * alpha_1) // 7,
            (2 * alpha_0 + 5 * alpha_1) // 7,
            (alpha_0 + 6 * alpha_1) // 7,
        ]
    return [
        alpha_0,
        alpha_1,
        (4 * alpha_0 + alpha_1) // 5,
        (3 * alpha_0 + 2 * alpha_1) // 5,
        (2 * alpha_0 + 3 * alpha_1) // 5,
        (alpha_0 + 4 * alpha_1) // 5,
        0,
        255,
    ]


def color_palette(color_0: int, color_1: int) -> list[tuple[int, int, int]]:
    first = rgb565(color_0)
    second = rgb565(color_1)
    return [
        first,
        second,
        tuple((2 * first[i] + second[i]) // 3 for i in range(3)),
        tuple((first[i] + 2 * second[i]) // 3 for i in range(3)),
    ]


def decode_dxt5(data: bytes, width: int, height: int) -> bytes:
    blocks_wide = (width + 3) // 4
    blocks_high = (height + 3) // 4
    expected = blocks_wide * blocks_high * 16
    if len(data) < expected:
        raise ValueError(f"DXT5 payload is {len(data)} bytes; expected at least {expected}")

    pixels = bytearray(width * height * 4)
    offset = 0
    for block_y in range(blocks_high):
        for block_x in range(blocks_wide):
            block = data[offset : offset + 16]
            offset += 16
            alphas = alpha_palette(block[0], block[1])
            alpha_bits = int.from_bytes(block[2:8], "little")
            color_0, color_1, color_bits = struct.unpack_from("<HHI", block, 8)
            colors = color_palette(color_0, color_1)

            for local_y in range(4):
                for local_x in range(4):
                    pixel_number = local_y * 4 + local_x
                    x = block_x * 4 + local_x
                    y = block_y * 4 + local_y
                    if x >= width or y >= height:
                        continue
                    color = colors[(color_bits >> (pixel_number * 2)) & 0x03]
                    alpha = alphas[(alpha_bits >> (pixel_number * 3)) & 0x07]
                    pixel_offset = (y * width + x) * 4
                    pixels[pixel_offset : pixel_offset + 4] = bytes((*color, alpha))
    return bytes(pixels)


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", binascii.crc32(body) & 0xFFFFFFFF)


def encode_png(rgba: bytes, width: int, height: int) -> bytes:
    stride = width * 4
    scanlines = b"".join(
        b"\x00" + rgba[row * stride : (row + 1) * stride] for row in range(height)
    )
    return b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)),
            png_chunk(b"IDAT", zlib.compress(scanlines, level=9)),
            png_chunk(b"IEND", b""),
        )
    )


def convert(source: Path, target: Path) -> None:
    raw = source.read_bytes()
    if len(raw) < 52:
        raise ValueError("PVR header is incomplete")
    (
        magic,
        _flags,
        pixel_format,
        _color_space,
        _channel_type,
        height,
        width,
        depth,
        surfaces,
        faces,
        mip_count,
        metadata_size,
    ) = struct.unpack_from("<IIQIIIIIIIII", raw, 0)
    if magic != PVR3_MAGIC:
        raise ValueError(f"Expected a PVR v3 texture, found magic 0x{magic:08x}")
    if pixel_format != PVR_PIXEL_FORMAT_DXT5:
        raise ValueError(f"Only DXT5/BC3 is supported; texture uses pixel format {pixel_format}")
    if depth != 1 or surfaces != 1 or faces != 1:
        raise ValueError("Only a single 2D texture surface is supported")
    if mip_count < 1:
        raise ValueError("Texture contains no mip levels")

    payload_offset = 52 + metadata_size
    rgba = decode_dxt5(raw[payload_offset:], width, height)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(encode_png(rgba, width, height))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    convert(args.source, args.target)
    print(f"Converted {args.source} -> {args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
