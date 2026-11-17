#!/usr/bin/env python3
"""Build /assets/img/ from the archived originals listed in scripts/convert/out/images.json.

Usage: .venv/bin/python -I scripts/convert/images.py [--force]

JPEG/PNG/HEIC/TIFF/WebP -> WebP (quality 80, max 1600px wide, no upscaling) via cwebp (`brew install webp`),
using sips (macOS) to read widths and to decode formats cwebp can't. GIF/SVG/ICO are copied as-is.
Skips outputs that already exist unless --force is given. Prints totals and any failures.
"""
import json, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REG = json.loads((ROOT / "scripts/convert/out/images.json").read_text())
FORCE = "--force" in sys.argv
MAXW = 1600


def width(src):
    r = subprocess.run(["sips", "-g", "pixelWidth", str(src)], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if "pixelWidth" in line:
            return int(line.split()[-1])
    return None


def build(item):
    url, src = item
    src = Path(src)
    dest = ROOT / url.lstrip("/")
    if dest.exists() and not FORCE:
        return url, "cached", dest.stat().st_size
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.suffix in (".gif", ".svg", ".ico"):
        shutil.copyfile(src, dest)
        return url, "copied", dest.stat().st_size
    inp = src
    tmp = None
    if src.suffix.lower() in (".heic", ".tif", ".tiff", ".bin", ".webp"):
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        subprocess.run(["sips", "-s", "format", "png", str(src), "--out", tmp.name], capture_output=True)
        inp = Path(tmp.name)
    w = width(inp)
    cmd = ["cwebp", "-quiet", "-q", "80", "-metadata", "none", "-mt"]
    if w and w > MAXW:
        cmd += ["-resize", str(MAXW), "0"]
    r = subprocess.run(cmd + [str(inp), "-o", str(dest)], capture_output=True, text=True)
    if tmp:
        Path(tmp.name).unlink(missing_ok=True)
    if r.returncode != 0 or not dest.exists():
        return url, "FAILED " + (r.stderr.strip()[:200] or "cwebp error"), 0
    return url, "converted", dest.stat().st_size


with ThreadPoolExecutor(6) as ex:
    results = list(ex.map(build, sorted(REG.items())))
ok = [r for r in results if not r[1].startswith("FAILED")]
print(f"images: {len(ok)}/{len(results)} ok, {sum(r[2] for r in ok)/1e6:.0f} MB in assets/img")
for r in results:
    if r[1].startswith("FAILED"):
        print("  ", r[0], r[1])
