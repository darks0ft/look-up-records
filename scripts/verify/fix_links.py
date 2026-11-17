#!/usr/bin/env python3
"""Repair dead, moved and hijacked external links in the site's source, using a
check_links.py report.

Usage: .venv/bin/python -I scripts/verify/fix_links.py report.json [--apply]

For each problem URL, in order:
  1. EXPLICIT below: a known replacement, None (drop the link, keep its text) or EMBED (remove
     the dead player).
  2. Dead, hijacked or erroring links: the Wayback Machine snapshot closest to when the page was
     written (status 200 only), so the citation still shows what was meant.
  3. No snapshot: drop the link, keep its text (button links are removed outright).
Dry run by default; prints what it would do.
"""
import html, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = json.loads(Path(sys.argv[1]).read_text())
APPLY = "--apply" in sys.argv
EMBED = "EMBED"
AP = "https://music.apple.com/us/album/"

EXPLICIT = {
    # malformed in the Squarespace export
    "https://Get 10% off CD or merch orders with AtomicDisc using our code LookUpRecords.": "https://www.atomicdisc.com/?bg_ref=is13kGgPQR",
    "http://the_fruit_juice_show": None,
    # moved by their owners
    "https://itunes.apple.com/us/album/a-paler-shade-of-white/1434123148": AP + "a-paler-shade-of-white/1434123148",
    "https://artists.youtube.com/": "https://artists.youtube/",
    "https://www.deezer-blog.com/press/deezer-is-now-the-fastest-growing-music-streaming-app-in-mexico/": "https://newsroom-deezer.com/2020/12/deezer-is-now-the-fastest-growing-music-streaming-app-in-mexico/",
    "https://www.socialchamp.io/comparison/buffer-alternatives/": "https://www.socialchamp.com/buffer-alternatives/",
    "https://www.duplication.ca": "https://www.duplication.com/",
    "https://www.cassetteclub.co": "https://spiritgoth.com/pages/cassette-club",
    "https://geo.music.apple.com/us/album/_/1794374201?mt=1&app=music&ls=1&at=1000lHKX&ct=odesli_http&itscg=30200&itsct=odsl_m": AP + "rationalism/1794374201",
    "https://apple.co/3HUbKxO": "https://artists.apple.com/",
    "https://www.thompsonspoint.com/calendar": "https://www.thompsonspoint.com/",
    "https://timslivemusic.com/contactbooking": "https://timslivemusic.com/",
    "https://www.venuepilot.co/events/74995/orders/new?fbclid=IwAR2EP4VIIkwfdduI3n_4ZEDNZsSETAy7u-wpivyZ3eZxt1VqSnNsgyB--Ig": "https://tickets.venuepilot.com/e/adam-spry-2023-05-30-ivy-room-albany-0aedb2",
    # albums re-delivered under new Apple IDs (matched by title, artist and release date)
    AP + "a-jazz/1604835629": AP + "a-jazz/1857286932",
    AP + "tan-camel/1496842916": AP + "tan-camel/1857273962",
    AP + "with-good-friends/1558316912": AP + "with-good-friends/6766298148",
    AP + "you-wont-be-seeing-me-around-ep/1551639892": AP + "you-wont-be-seeing-me-around-ep/1800565657",
    AP + "everybodys-smiling-nobodys-happy/1636550206": AP + "everybodys-smiling-nobodys-happy/1811087257",
    "https://apple.co/3bup6De": "https://music.apple.com/us/artist/elephants-and-dogs/1551639893",
    # same music, still online elsewhere
    "https://sg63.fanlink.to/darksoft-grayscale": "https://darks0ft.bandcamp.com/album/grayscale",
    "https://soundcloud.com/darks0ft/mydoom": "https://open.spotify.com/track/21AWPeMpbHxar2nPBea5RK",
    "https://statebirdsmusic.bandcamp.com/": "https://statebirds.bandcamp.com/",
    "https://statebirdsmusic.bandcamp.com/album/state-birds": "https://statebirds.bandcamp.com/album/state-birds",
    # gone services with nothing worth archiving
    "https://ar.napster.com/artist/the-sea-life": None,
    "https://soundcloud.com/you/insights/overview": None,
}
HIJACKED = ("leftbankmag.com", "comeherefloyd.com", "caferacerseattle.com")   # now redirect to spam
KEEP_MOVED = ("eventbrite.com", "therendezvous.rocks", "studio.youtube.com")    # redirect to the right place


def page_date(pages):
    for p in pages:
        if m := re.search(r"/blog/", p):
            src = list((ROOT / "_posts").glob("*-" + p.rsplit("/", 1)[1] + ".md"))
            if src:
                return src[0].name[:10].replace("-", "")
    return "2020"


def wayback(url, when):
    api = "https://archive.org/wayback/available?" + urllib.parse.urlencode({"url": url, "timestamp": when})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(api, timeout=30) as r:
                snap = json.loads(r.read()).get("archived_snapshots", {}).get("closest")
            if snap and snap.get("available") and snap.get("status") == "200":
                return snap["url"].replace("http://", "https://", 1)
            return None
        except Exception:
            time.sleep(2 + attempt * 3)
    return None


def plan():
    actions = {}
    for url, r in REPORT.items():
        st = r["status"]
        host = urllib.parse.urlparse(url).netloc
        if url in EXPLICIT:
            actions[url] = EXPLICIT[url]
        elif st == "dead" and r.get("via") in ("youtube", "soundcloud") and ("embed" in url or "w.soundcloud.com/player" in url):
            actions[url] = EMBED
        elif st in ("dead", "error") or (st == "moved" and not any(k in host for k in KEEP_MOVED)) or any(h in host for h in HIJACKED):
            if st == "blocked":
                continue
            actions[url] = wayback(url, page_date(r["pages"])) or None
            time.sleep(1)
    return actions


def variants(url):
    return {url, url.replace("&", "&amp;"), html.unescape(url)}


def rewrite(text, url, new):
    n = 0
    for u in variants(url):
        e = re.escape(u)
        if new == EMBED:
            text, k = re.subn(rf'<div class="embed[^"]*">\s*<iframe[^>]*src="{e}"[^>]*>\s*</iframe>\s*</div>\n?', "", text); n += k
        elif new is None:
            text, k = re.subn(rf'<a class="button[^"]*"[^>]*href="{e}"[^>]*>.*?</a>\s*', "", text, flags=re.S); n += k
            text, k = re.subn(rf'<a\b[^>]*href="{e}"[^>]*>(.*?)</a>', r"\1", text, flags=re.S); n += k
            text, k = re.subn(rf'\[([^\]]*)\]\({e}(?:\s+"[^"]*")?\)', r"\1", text); n += k
            text = re.sub(r'<p class="buttons">\s*</p>\n?', "", text)
        else:
            # whole-URL matches only, so https://x.org never rewrites inside https://x.org/contact
            rep = new if u == url else new.replace("&", "&amp;")
            text, k = re.subn(rf'{e}(?=["\')\s<\]]|$)', lambda _: rep, text, flags=re.M); n += k
    return text, n


def main():
    actions = plan()
    files = [*ROOT.glob("_posts/*.md"), *ROOT.glob("_pages/*.md"), *ROOT.glob("_pages/*.html"), *ROOT.glob("_releases/*.md"), *ROOT.glob("_data/*.yml")]
    touched = {}
    for f in files:
        t = orig = f.read_text()
        for url, new in actions.items():
            t, n = rewrite(t, url, new)
            if n:
                touched.setdefault(url, []).append(f.name)
        if APPLY and t != orig:
            f.write_text(t)
    for url, new in sorted(actions.items(), key=lambda kv: str(kv[1])):
        label = "REMOVE EMBED" if new == EMBED else ("UNLINK" if new is None else ("ARCHIVE" if "web.archive.org" in new else "REPLACE"))
        print(f"{label:12} {url[:90]}\n{'':13}-> {new if new not in (None, EMBED) else ''}  in {touched.get(url, ['(not found in source)'])}")
    print(("APPLIED" if APPLY else "DRY RUN"), len(actions), "urls")


if __name__ == "__main__":
    main()
