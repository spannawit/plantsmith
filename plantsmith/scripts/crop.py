#!/usr/bin/env python3
"""Crop a region of a rendered PNG into a new PNG, so small text can be read at full size.

Stdlib only (zlib + the PNG filters). Reads 8-bit, non-interlaced PNGs: greyscale, RGB,
palette, greyscale+alpha and RGBA, which covers what PlantUML writes.

  python scripts/crop.py diagram.png --tile 1          # top-left quarter of a 2x2 grid
  python scripts/crop.py diagram.png --box 0,400,900,600 --out zoom.png

Tiles 1-4 run left to right, top to bottom, and overlap their neighbours by 32 px so a line
of text on a tile edge is whole on one of them. Without --out the crop goes to
<name>.crop.png (or <name>.tile<n>.png) beside the source. Exit 0 on success, 1 on failure.
"""
from __future__ import annotations

import argparse
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}  # colour type -> bytes per pixel at bit depth 8
TILE_OVERLAP_PX = 32
GRID = 2


class CropError(Exception):
    """A failure the user must see; the message is printed as-is."""


@dataclass(frozen=True)
class Image:
    width: int
    height: int
    colour_type: int
    rows: list[bytes]  # unfiltered scanlines
    extra_chunks: tuple[tuple[bytes, bytes], ...]  # PLTE / tRNS to carry over


def read_chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    if not data.startswith(PNG_MAGIC):
        raise CropError("not a PNG (magic bytes missing)")
    chunks, pos = [], len(PNG_MAGIC)
    while pos + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        chunks.append((kind, data[pos + 8:pos + 8 + length]))
        pos += 12 + length
        if kind == b"IEND":
            break
    return chunks


def paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def unfilter(raw: bytes, width: int, height: int, bpp: int, last_row: int) -> list[bytes]:
    """Undo the per-row PNG filters for rows 0..last_row (later rows depend on earlier ones)."""
    stride = width * bpp
    rows: list[bytes] = []
    prior = bytearray(stride)
    for y in range(min(last_row + 1, height)):
        start = y * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        if kind == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif kind == 2:
            line = bytearray((x + p) & 0xFF for x, p in zip(line, prior))
        elif kind == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prior[i]) >> 1)) & 0xFF
        elif kind == 4:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                up_left = prior[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + paeth(left, prior[i], up_left)) & 0xFF
        elif kind != 0:
            raise CropError(f"unknown PNG filter type {kind} on row {y}")
        rows.append(bytes(line))
        prior = line
    return rows


def decode(data: bytes, last_row: int) -> Image:
    chunks = read_chunks(data)
    if not chunks or chunks[0][0] != b"IHDR":
        raise CropError("PNG has no IHDR header")
    width, height, depth, colour_type, _, _, interlace = struct.unpack(">IIBBBBB", chunks[0][1])
    if depth != 8 or colour_type not in CHANNELS:
        raise CropError(f"unsupported PNG: bit depth {depth}, colour type {colour_type} (need 8-bit)")
    if interlace:
        raise CropError("interlaced PNGs are not supported")
    raw = zlib.decompress(b"".join(body for kind, body in chunks if kind == b"IDAT"))
    rows = unfilter(raw, width, height, CHANNELS[colour_type], last_row)
    extra = tuple((kind, body) for kind, body in chunks if kind in (b"PLTE", b"tRNS"))
    return Image(width, height, colour_type, rows, extra)


def chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)


def encode(width: int, height: int, colour_type: int, rows: list[bytes], extra: tuple) -> bytes:
    header = struct.pack(">IIBBBBB", width, height, 8, colour_type, 0, 0, 0)
    payload = b"".join(b"\x00" + row for row in rows)  # filter type 0 on every row
    parts = [PNG_MAGIC, chunk(b"IHDR", header)]
    parts += [chunk(kind, body) for kind, body in extra]
    parts += [chunk(b"IDAT", zlib.compress(payload, 9)), chunk(b"IEND", b"")]
    return b"".join(parts)


def png_size(data: bytes) -> tuple[int, int]:
    chunks = read_chunks(data)
    if not chunks or chunks[0][0] != b"IHDR":
        raise CropError("PNG has no IHDR header")
    return struct.unpack(">II", chunks[0][1][:8])


def tile_box(width: int, height: int, tile: int) -> tuple[int, int, int, int]:
    """Quarter `tile` (1-4) of a 2x2 grid, widened by the overlap and clamped to the image."""
    if not 1 <= tile <= GRID * GRID:
        raise CropError(f"--tile must be 1 to {GRID * GRID}")
    col, row = (tile - 1) % GRID, (tile - 1) // GRID
    cell_w, cell_h = -(-width // GRID), -(-height // GRID)
    x0, y0 = max(col * cell_w - TILE_OVERLAP_PX, 0), max(row * cell_h - TILE_OVERLAP_PX, 0)
    x1 = min((col + 1) * cell_w + TILE_OVERLAP_PX, width)
    y1 = min((row + 1) * cell_h + TILE_OVERLAP_PX, height)
    return x0, y0, x1 - x0, y1 - y0


def crop_bytes(data: bytes, box: tuple[int, int, int, int]) -> bytes:
    x, y, w, h = box
    width, height = png_size(data)
    if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > width or y + h > height:
        raise CropError(f"box {x},{y},{w},{h} is outside the {width}x{height} image")
    image = decode(data, y + h - 1)
    bpp = CHANNELS[image.colour_type]
    rows = [row[x * bpp:(x + w) * bpp] for row in image.rows[y:y + h]]
    return encode(w, h, image.colour_type, rows, image.extra_chunks)


def parse_box(text: str) -> tuple[int, int, int, int]:
    try:
        x, y, w, h = (int(part) for part in text.split(","))
    except ValueError as exc:
        raise CropError(f"--box needs four integers x,y,w,h, got {text!r}") from exc
    return x, y, w, h


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Crop a PNG region (stdlib only) to read small text.")
    parser.add_argument("png", type=Path, help="rendered PNG")
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--box", help="x,y,w,h in pixels from the top-left corner")
    where.add_argument("--tile", type=int, help="1-4: quarter of a 2x2 grid (with a 32 px overlap)")
    parser.add_argument("--out", type=Path, help="output PNG (default: beside the source)")
    args = parser.parse_args(argv)
    try:
        data = args.png.read_bytes()
        width, height = png_size(data)
        box = parse_box(args.box) if args.box else tile_box(width, height, args.tile)
        suffix = f".tile{args.tile}.png" if args.tile else ".crop.png"
        out = args.out or args.png.with_name(args.png.stem + suffix)
        out.write_bytes(crop_bytes(data, box))
    except (CropError, OSError, zlib.error) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"wrote: {out} ({box[2]}x{box[3]} px from {width}x{height}, box {box[0]},{box[1]},{box[2]},{box[3]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
