#!/usr/bin/env python3
"""Replace filename-style alt text (alt="IMG_9205.jpg", ![DSC_0012.png](...)) with
"Photo from <page title>" so images describe their context instead of a camera filename.
Usage: .venv/bin/python -I scripts/seo/fix_alts.py   (safe to re-run)
"""
import re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
FILENAME = r"[^\"\]\n]*\.(?:jpe?g|png|gif|webp|heic)|(?:img|dsc|image|photo)[-_ ]?\d+[^\"\]\n]*"
total = 0
for f in list((ROOT / "_pages").glob("*.md")) + list((ROOT / "_posts").glob("*.md")):
    t = f.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    title = str(yaml.safe_load(m.group(1)).get("title", "Look Up Records")).replace('"', "”")
    alt = f"Photo from {title}"
    new, n1 = re.subn(rf'alt="(?:{FILENAME})"', f'alt="{alt}"', t, flags=re.I)
    new, n2 = re.subn(rf"!\[(?:{FILENAME})\]\(", f"![{alt}](", new, flags=re.I)
    if n1 + n2:
        f.write_text(new)
        total += n1 + n2
        print(f"{f.name}: {n1 + n2}")
print("total", total)
