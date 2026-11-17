#!/usr/bin/env python3
"""Check a built site (_site or /tmp/look-up-site) against every old Squarespace URL.

Usage: .venv/bin/python -I scripts/verify/check_site.py /tmp/look-up-site [--local]

1. Every URL in archive/sitemap.xml + archive/pages-manifest.json (+ album track URLs) must resolve the
   way GitHub Pages resolves it (/x -> x.html, / -> index.html) to a page, or to a redirect stub
   whose target resolves. URLs that returned 404 on Squarespace are skipped.
2. Every internal href/src in the built HTML must resolve (pages, assets, anchors are ignored).
--local: case-alias stubs are off in local builds, so URLs differing only by case are reported, not failed.
"""
import json, re, sys, urllib.parse
from pathlib import Path

SITE = Path(sys.argv[1])
LOCAL = "--local" in sys.argv
ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "archive"


def resolve(path):
    """Return the file GitHub Pages would serve for a URL path, or None."""
    p = urllib.parse.unquote(path.split("#")[0].split("?")[0])
    if p in ("", "/"):
        f = SITE / "index.html"
        return f if f.exists() else None
    rel = p.lstrip("/")
    for cand in (SITE / rel, SITE / (rel + ".html"), SITE / rel / "index.html"):
        if cand.is_file():
            return cand
    return None


def redirect_target(f):
    m = re.search(r'http-equiv="refresh" content="0; url=([^"]+)"', f.read_text(errors="ignore"))
    return m.group(1) if m else None


def check(path):
    f = resolve(path)
    if not f:
        return "MISSING"
    seen = {path}
    while (t := redirect_target(f)):
        t = t.split("#")[0]
        if t in seen:
            return f"LOOP -> {t}"
        seen.add(t)
        f = resolve(t)
        if not f:
            return f"REDIRECT TARGET MISSING -> {t}"
    return "ok" if len(seen) == 1 else f"redirect -> {t}"


old = [re.sub(r"^https?://[^/]+", "", u) or "/" for u in re.findall(r"<loc>([^<]+)</loc>", (ARCH / "sitemap.xml").read_text())]
man = json.loads((ARCH / "pages-manifest.json").read_text())
old += [u for u, v in man.items() if v["html"] == 200]
for album in ARCH.glob("pages/*/*.json"):
    try:
        old += [t["fullUrl"] for t in json.loads(album.read_text()).get("items", []) if t.get("recordTypeLabel") == "audio"]
    except Exception:
        pass
for line in (ARCH / "admin/url-mappings.txt").read_text().splitlines():
    if line.startswith("/"):
        old.append(line.split()[0])
old = sorted(u for u in set(old) if not u.startswith("/universal/"))

lower = {}
for f in SITE.rglob("*.html"):
    lower.setdefault(str(f.relative_to(SITE)).lower(), f)

counts, bad, case_only = {"ok": 0, "redirect": 0}, [], []
for u in old:
    r = check(u)
    if r == "ok":
        counts["ok"] += 1
    elif r.startswith("redirect"):
        counts["redirect"] += 1
    else:
        rel = urllib.parse.unquote(u).lstrip("/") + ".html"
        if LOCAL and rel.lower() in lower:
            case_only.append(u)
        else:
            bad.append((u, r))

print(f"old URLs: {len(old)} | served: {counts['ok']} | redirected: {counts['redirect']} | broken: {len(bad)}"
      + (f" | case-alias (off locally): {len(case_only)}" if LOCAL else ""))
for u, r in bad[:40]:
    print("  ", r, u)

# internal links + assets in built HTML
broken = {}
for f in SITE.rglob("*.html"):
    t = f.read_text(errors="ignore")
    if 'http-equiv="refresh"' in t:
        continue
    for ref in re.findall(r'(?:href|src)="(/[^"#?]*)', t):
        if ref.startswith("//") or ref == "/":
            continue
        if not resolve(ref):
            rel = urllib.parse.unquote(ref).lstrip("/") + ".html"
            if LOCAL and rel.lower() in lower:
                continue
            broken.setdefault(ref, set()).add("/" + str(f.relative_to(SITE)).removesuffix(".html"))
print(f"internal links/assets that don't resolve: {len(broken)}")
for ref, pages in sorted(broken.items())[:40]:
    print("  ", ref, "<-", ", ".join(sorted(pages)[:3]))
sys.exit(1 if bad or broken else 0)
