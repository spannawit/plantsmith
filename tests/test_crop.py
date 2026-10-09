"""Plain-Python tests for crop.py. Run: python tests/test_crop.py"""
from __future__ import annotations

import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = next(ROOT.glob("*/scripts/crop.py")).parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import crop  # noqa: E402
import render  # noqa: E402

SKIPPED: list[str] = []


def pixel(x: int, y: int) -> bytes:
    return bytes(((x * 7 + y) % 256, (y * 5) % 256, (x + y * 3) % 256))


def filtered_png(width: int, height: int) -> bytes:
    """An RGB PNG whose rows cycle through all five filter types, built independently of crop.py."""
    bpp, rows, prior = 3, [], bytes(width * 3)
    for y in range(height):
        line = b"".join(pixel(x, y) for x in range(width))
        kind = y % 5
        out = bytearray()
        for i, value in enumerate(line):
            left = line[i - bpp] if i >= bpp else 0
            up, up_left = prior[i], (prior[i - bpp] if i >= bpp else 0)
            predictor = (0, left, up, (left + up) >> 1, crop.paeth(left, up, up_left))[kind]
            out.append((value - predictor) & 0xFF)
        rows.append(bytes([kind]) + bytes(out))
        prior = line
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    body = zlib.compress(b"".join(rows))
    return crop.PNG_MAGIC + crop.chunk(b"IHDR", header) + crop.chunk(b"IDAT", body) + crop.chunk(b"IEND", b"")


def test_crop_undoes_every_filter_type() -> None:
    data = crop.crop_bytes(filtered_png(40, 30), (5, 7, 20, 11))
    image = crop.decode(data, 10)
    assert (image.width, image.height) == (20, 11)
    for y in range(11):
        expected = b"".join(pixel(x + 5, y + 7) for x in range(20))
        assert image.rows[y] == expected, y


def test_tiles_cover_the_image_with_overlap() -> None:
    boxes = [crop.tile_box(3309, 1224, tile) for tile in (1, 2, 3, 4)]
    assert boxes[0][:2] == (0, 0) and boxes[3][0] + boxes[3][2] == 3309 and boxes[3][1] + boxes[3][3] == 1224
    assert boxes[0][0] + boxes[0][2] > boxes[1][0], "neighbouring tiles overlap"
    try:
        crop.tile_box(100, 100, 5)
    except crop.CropError:
        return
    raise AssertionError("tile 5 accepted")


def test_box_outside_the_image_is_refused() -> None:
    try:
        crop.crop_bytes(filtered_png(10, 10), (5, 5, 10, 10))
    except crop.CropError:
        return
    raise AssertionError("box outside the image accepted")


def test_crop_box_writes_valid_png_from_a_real_render() -> None:
    try:
        render.resolve_command()
    except render.RenderError:
        SKIPPED.append("test_crop_box_writes_valid_png_from_a_real_render (plantuml not found)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, str(SCRIPTS / "render.py"), str(FIXTURES / "clean.puml"), "--out-dir", tmp],
                       capture_output=True, check=True)
        png = Path(tmp) / "clean.png"
        result = subprocess.run([sys.executable, str(SCRIPTS / "crop.py"), str(png), "--tile", "1"],
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        width, height = render.verify_png(Path(tmp) / "clean.tile1.png")
        full_w, full_h = render.verify_png(png)
        assert width <= full_w and height <= full_h and width > full_w // 2 - 1, (width, full_w)


def main() -> int:
    tests = [(name, fn) for name, fn in globals().items() if name.startswith("test_") and callable(fn)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
    for skip in SKIPPED:
        print(f"SKIP {skip}")
    print(f"{len(tests) - failed - len(SKIPPED)}/{len(tests)} passed, {len(SKIPPED)} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
