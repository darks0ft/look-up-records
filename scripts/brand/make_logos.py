#!/usr/bin/env python3
"""Generate the downloadable Look Up logo variants for /logo from the single-color master.

Usage: .venv/bin/python -I scripts/brand/make_logos.py   (needs Pillow in .venv)

The master (archive/admin/look-up-logo-green.png, 1000x1106) is one green with antialiased
alpha; the saucer streaks are cut-outs. Each variant reuses that alpha mask with a new fill.
Transparent variants keep the master's size; background variants are 1400x1400 squares.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "archive/admin/look-up-logo-green.png"
OUT = ROOT / "assets/brand/logo"

GREEN = (193, 219, 148)   # the logo's own green, #c1db94
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

TRANSPARENT = {"green": GREEN, "white": WHITE, "black": BLACK}
ON_BACKGROUND = {               # name: (logo color, background color)
    "green-on-black": (GREEN, BLACK),
    "black-on-green": (BLACK, GREEN),
    "black-on-white": (BLACK, WHITE),
    "white-on-black": (WHITE, BLACK),
}
SQUARE, PAD = 1400, 0.16        # canvas size and padding (fraction of the side)


def recolor(mask, rgb):
    im = Image.new("RGBA", mask.size, rgb + (0,))
    im.putalpha(mask)
    return im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mask = Image.open(SRC).convert("RGBA").getchannel("A")
    for name, rgb in TRANSPARENT.items():
        recolor(mask, rgb).save(OUT / f"look-up-logo-{name}.png", optimize=True)
    inner = int(SQUARE * (1 - 2 * PAD))
    scale = inner / max(mask.size)
    small = mask.resize((round(mask.width * scale), round(mask.height * scale)), Image.LANCZOS)
    for name, (fg, bg) in ON_BACKGROUND.items():
        canvas = Image.new("RGB", (SQUARE, SQUARE), bg)
        logo = recolor(small, fg)
        canvas.paste(logo, ((SQUARE - logo.width) // 2, (SQUARE - logo.height) // 2), logo)
        canvas.save(OUT / f"look-up-logo-{name}.png", optimize=True)
    for f in sorted(OUT.glob("*.png")):
        print(f.name, f.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
