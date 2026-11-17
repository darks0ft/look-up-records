#!/usr/bin/env python3
"""Check every external link on a built site and report what's dead.

Usage: .venv/bin/python -I scripts/verify/check_links.py /tmp/look-up-site [out.json]

Spotify, YouTube and SoundCloud are checked through their public oEmbed endpoints, which
also return the item's title (so release links can be checked for relevance, not just life).
Facebook, Instagram, X/Twitter and Amazon block automated requests; they're reported as
"unverifiable", not dead.
"""
import json, re, socket, sys, urllib.error, urllib.parse, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from bs4 import BeautifulSoup

SITE = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else None
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
BLOCKS_BOTS = ("facebook.com", "fb.me", "instagram.com", "twitter.com", "x.com", "amazon.", "amzn.", "linkedin.com", "tiktok.com")


def collect():
    links = defaultdict(set)
    for f in SITE.rglob("*.html"):
        t = f.read_text(errors="ignore")
        if 'http-equiv="refresh"' in t:
            continue
        page = "/" + str(f.relative_to(SITE)).removesuffix(".html")
        for el in BeautifulSoup(t, "html.parser").find_all(["a", "iframe"]):
            u = (el.get("href") or el.get("src") or "").split("#")[0]
            if u.startswith("http") and "look-up-records.com" not in urllib.parse.urlparse(u).netloc:
                links[u].add(page)
    return links


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.geturl(), r.read(400_000).decode("utf-8", "ignore")


def oembed_target(url):
    p = urllib.parse.urlparse(url)
    host = p.netloc.removeprefix("www.")
    if host == "open.spotify.com":
        path = p.path.replace("/embed/", "/").replace("/embed-podcast/", "/")
        return "spotify", "https://open.spotify.com/oembed?url=" + urllib.parse.quote("https://open.spotify.com" + path, safe="")
    yt = None
    if host in ("youtube.com", "youtube-nocookie.com", "m.youtube.com"):
        q = urllib.parse.parse_qs(p.query)
        if "v" in q:
            yt = q["v"][0]
        elif m := re.match(r"/embed/([\w-]{11})", p.path):
            yt = m.group(1)
    elif host == "youtu.be":
        yt = p.path.strip("/")[:11]
    if yt:
        return "youtube", "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(f"https://www.youtube.com/watch?v={yt}", safe="")
    if host == "w.soundcloud.com":
        inner = urllib.parse.parse_qs(p.query).get("url", [""])[0]
        return "soundcloud", "https://soundcloud.com/oembed?format=json&url=" + urllib.parse.quote(inner, safe="")
    if host == "soundcloud.com":
        return "soundcloud", "https://soundcloud.com/oembed?format=json&url=" + urllib.parse.quote(url, safe="")
    return None, None


def check(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    kind, oe = oembed_target(url)
    try:
        if oe:
            _, _, body = fetch(oe)
            return {"status": "ok", "via": kind, "title": json.loads(body).get("title", "")}
        if any(b in host for b in BLOCKS_BOTS):
            return {"status": "unverifiable"}
        if host == "web.archive.org":
            return {"status": "archived"}   # snapshots were confirmed when added; don't hammer the archive
        code, final, body = fetch(url)
        title = ""
        if m := re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]*)"', body) or re.search(r"<title[^>]*>([^<]*)", body):
            title = m.group(1).strip()
        res = {"status": "ok", "code": code, "title": title}
        if urllib.parse.urlparse(final).netloc.removeprefix("www.") != host.removeprefix("www."):
            res.update(status="moved", final=final)
        return res
    except urllib.error.HTTPError as e:
        if oe and kind == "youtube" and e.code in (401, 403) and "/embed/" not in url:
            return {"status": "ok", "via": kind, "title": "(embedding disabled; watch link works)"}
        if oe and e.code in (400, 401, 403, 404):
            return {"status": "dead", "code": e.code, "via": kind}
        if e.code in (404, 410):
            return {"status": "dead", "code": e.code}
        return {"status": "blocked", "code": e.code}   # 403/429/5xx: alive but unhappy with bots
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
        reason = str(getattr(e, "reason", e))
        dns = any(s in reason for s in ("nodename", "Name or service", "getaddrinfo", "No address"))
        return {"status": "dead" if dns else "error", "error": reason[:120]}
    except Exception as e:
        return {"status": "error", "error": str(e)[:120]}


def main():
    links = collect()
    with ThreadPoolExecutor(12) as pool:
        results = dict(zip(links, pool.map(check, links)))
    by = defaultdict(list)
    for u, r in results.items():
        by[r["status"]].append(u)
    print(f"{len(links)} external links: " + ", ".join(f"{k} {len(v)}" for k, v in sorted(by.items())))
    for k in ("dead", "moved", "error", "blocked"):
        for u in sorted(by[k]):
            r = results[u]
            print(f"  {k.upper():7} {r.get('code') or ''} {u}  -> {r.get('final') or r.get('error') or ''}  [{', '.join(sorted(links[u])[:2])}]")
    if OUT:
        OUT.write_text(json.dumps({u: {**results[u], "pages": sorted(links[u])} for u in links}, indent=1))


if __name__ == "__main__":
    main()
