#!/usr/bin/env python3
"""Check every old Squarespace URL against a live host (GitHub Pages test URL or the real domain).

Usage: .venv/bin/python -I scripts/verify/check_live.py https://darks0ft.github.io/look-up-records

Uses the same old-URL list as check_site.py. For each URL: fetch it (following HTTP redirects),
expect 200, then follow meta-refresh redirect stubs (their targets are root-relative, so they are
re-based onto the host) and expect the final page to be 200 too.
"""
import json, re, sys, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = sys.argv[1].rstrip("/")
ARCH = Path(__file__).resolve().parents[2] / "archive"
UA = {"User-Agent": "look-up-site-check/1.0"}


def old_urls():
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
    return sorted(u for u in set(old) if not u.startswith("/universal/"))


def fetch(path):
    url = BASE + urllib.parse.quote(path, safe="/%+:@!$&'()*,;=-._~")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                return r.status, r.read().decode("utf-8", "ignore"), r.geturl()
        except urllib.error.HTTPError as e:
            return e.code, "", url
        except Exception:
            time.sleep(1 + attempt)
    return 0, "", url


def check(path):
    seen = [path]
    status, body, final = fetch(path)
    while status == 200 and (m := re.search(r'http-equiv="refresh" content="0; url=([^"]+)"', body)):
        target = m.group(1).split("#")[0]
        if target in seen:
            return path, f"LOOP -> {target}"
        seen.append(target)
        status, body, final = fetch(target)
    if status != 200:
        return path, f"{status} at {seen[-1]}"
    return path, "ok" if len(seen) == 1 else "redirect"


urls = old_urls()
with ThreadPoolExecutor(8) as pool:
    results = list(pool.map(check, urls))
bad = [(u, r) for u, r in results if r not in ("ok", "redirect")]
print(f"{BASE}: old URLs {len(urls)} | served {sum(r == 'ok' for _, r in results)} | "
      f"redirected {sum(r == 'redirect' for _, r in results)} | broken {len(bad)}")
for u, r in bad[:60]:
    print("  ", r, "<-", u)
sys.exit(1 if bad else 0)
