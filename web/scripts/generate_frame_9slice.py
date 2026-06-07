#!/usr/bin/env python3
"""Generate square CSS border-image 9-slice wooden frame assets."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parents[1] / "public" / "assets" / "living-room"

WOOD_DARK = (62, 40, 28, 255)
WOOD_MID = (98, 64, 42, 255)
WOOD_LIGHT = (128, 88, 58, 255)
HIGHLIGHT = (148, 108, 72, 255)
SHADOW = (42, 26, 18, 255)


def wood_rgba(x: int, y: int, axis: str = "h") -> tuple[int, int, int, int]:
    t = y if axis == "h" else x
    grain = math.sin(t * 0.22 + math.sin((x + y) * 0.04) * 2.0) * 0.5 + 0.5
    ring = math.sin(t * 0.08) * 0.5 + 0.5
    mix = grain * 0.65 + ring * 0.35
    if mix < 0.35:
        base = WOOD_DARK
    elif mix < 0.65:
        base = WOOD_MID
    elif mix < 0.85:
        base = WOOD_LIGHT
    else:
        base = HIGHLIGHT
    edge = min(x % 8, 7 - x % 8, y % 8, 7 - y % 8) / 8.0
    r = int(base[0] * (0.88 + edge * 0.12))
    g = int(base[1] * (0.88 + edge * 0.12))
    b = int(base[2] * (0.88 + edge * 0.12))
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)), 255)


def make_9slice(size: int, slice_px: int, filename: str) -> None:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = im.load()
    inner = slice_px

    for y in range(size):
        for x in range(size):
            in_border = x < inner or x >= size - inner or y < inner or y >= size - inner
            if not in_border:
                continue
            if y < inner or y >= size - inner:
                axis = "h"
            elif x < inner or x >= size - inner:
                axis = "v"
            else:
                axis = "h"
            px[x, y] = wood_rgba(x, y, axis)

    draw = ImageDraw.Draw(im)
    draw.rectangle([1, 1, size - 2, size - 2], outline=HIGHLIGHT)
    draw.rectangle([inner, inner, size - inner - 1, size - inner - 1], outline=SHADOW)

    path = OUT_DIR / filename
    im.save(path, "PNG")
    print(f"Wrote {path} ({size}x{size}, slice={slice_px})")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    make_9slice(256, 48, "frame-hero-9slice.png")
    make_9slice(128, 24, "frame-strip-9slice.png")


if __name__ == "__main__":
    main()
