#!/usr/bin/env python3
"""Convert the archived Squarespace site (archive/) into Jekyll source files.

Usage (from the repo root):
    .venv/bin/python -I scripts/convert/convert.py archive/ .

Writes (overwriting what it generated before):
    _posts/              151 published posts (Markdown + front matter)
    _drafts/             unpublished posts from the WordPress export
    _data/authors.yml    byline authors (team bios from the WordPress export)
    _tag_pages/          /blog/tag/<Tag> pages (same URLs as Squarespace)
    _category_pages/     /blog/category/<Category> pages
    _releases/           /catalog/... release pages
    _legacy/             redirect stubs for retired URLs
    _pages/              core pages, as raw converted content (redesigned in Phase 2)
    _unpublished/        pages that were never public on Squarespace (reference only, not built)
    scripts/convert/out/ images.json (registry for images.py) and report.json
"""
import json, re, sys, html, shutil, urllib.parse, xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from sqs import Converter, Images, slugify, text_of  # noqa: E402

if "--force" not in sys.argv:
    sys.exit("Refusing to run: since Phase 2 the generated files are edited by hand, and this would overwrite them.\n"
             "Re-run with --force only if you really want to regenerate everything from archive/.")
ARCH = Path(sys.argv[1]).resolve()
ROOT = Path(sys.argv[2]).resolve()
TZ = ZoneInfo("America/Los_Angeles")
WP = {"wp": "http://wordpress.org/export/1.2/", "content": "http://purl.org/rss/1.0/modules/content/",
      "excerpt": "http://wordpress.org/export/1.2/excerpt/", "dc": "http://purl.org/dc/elements/1.1/"}

images = Images(ARCH)
report = defaultdict(list)


def load(p):
    return json.loads((ARCH / p).read_text())


def write_doc(path: Path, fm: dict, body: str = ""):
    path.parent.mkdir(parents=True, exist_ok=True)
    y = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=1000)
    path.write_text(f"---\n{y}---\n" + (("\n" + body) if body else ""))


def fresh(*dirs):
    for d in dirs:
        p = ROOT / d
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)


def ts(ms):
    return datetime.fromtimestamp(int(ms) / 1000, TZ)


# ------------------------------------------------------------------ inputs
posts = load("blog-all.json")
wp = ET.parse(ARCH / "admin/wordpress-export-2026-11-16.xml").getroot()
wp_items = list(wp.iter("item"))
wp_att = {i.findtext("wp:post_id", namespaces=WP): i.findtext("wp:attachment_url", namespaces=WP)
          for i in wp_items if i.findtext("wp:post_type", namespaces=WP) == "attachment"}
sitemap_paths = [re.sub(r"^https?://[^/]+", "", u) for u in re.findall(r"<loc>([^<]+)</loc>", (ARCH / "sitemap.xml").read_text())]

ALBUMS = {  # deleted album pages -> artist page
    "/darksoft/meltdown": "/darksoft", "/darksoft/brain": "/darksoft", "/darksoft/cryo": "/darksoft",
    "/darksoft/beigeification": "/darksoft", "/sealife/a-paler-shade-of-white": "/sealife",
    "/sealife/tan-camel": "/sealife", "/swym/strange-hallucinations": "/swym", "/swym/mirror-box": "/swym",
    "/elephants-and-dogs/you-wont-be-seeing-me-around": "/elephants-and-dogs",
}
TEASERS = {"/state-birds-teaser": "state-birds", "/elephants-and-dogs-teaser": "elephants-and-dogs",
           "/stacking-pennies-teaser": "stacking-pennies", "/swym-teaser": "swym", "/sealife-teaser": "sealife",
           "/banadu-teaser": "banadu", "/pure-mood-teaser": "pure-mood", "/sightings-teaser": "sightings",
           "/andreas-schwarzwald": "andreas-schwarzwald", "/pure-mood": "pure-mood", "/state-birds": "state-birds"}
STATIC_REDIRECTS = {
    "/home": "/", "/blog-home": "/blog", "/contact": "/about", "/thank-you": "/newsletter",
    "/events": "/look-up-fest", "/artists/banadu": "/darksoft", "/store": "/catalog",
}
# Squarespace URL mappings (archive/admin/url-mappings.txt). /MARS and /LUFU are left out: on a
# case-insensitive disk they'd overwrite the real /mars and /lufu pages in local builds.
URL_MAPPINGS = {
    "/look-up-fest-underwater": "/lufu", "/LUFUISREAL": "/lufu", "/underwater": "/lufu",
    "/M": "/mars", "/MA": "/mars", "/MAR": "/mars", "/lufm": "/mars", "/LUFM": "/mars",
    "/blog/13-small-capacity-venues-in-seattle-for-touring-bands": "/blog/15-small-capacity-venues-in-seattle-for-touring-bands",
    "/blog/14-small-capacity-venues-in-seattle-for-touring-bands": "/blog/15-small-capacity-venues-in-seattle-for-touring-bands",
}

# ------------------------------------------------------------------ post URLs
post_url = {}      # old fullUrl -> new permalink
DUPES = {}
slugs = Counter(p["fullUrl"].rsplit("/", 1)[1] for p in posts)
for p in posts:
    old = p["fullUrl"]
    slug = old.rsplit("/", 1)[1]
    post_url[old] = f"/blog/{slug}"
assert all(c == 1 for c in slugs.values()), "slug collision"

# The -j5t9f post looked like a duplicate of its twin, but it's a separate announcement (different
# title and date), so both are kept. DUPES stays as a hook in case a real duplicate turns up.
by_url = {p["fullUrl"]: p for p in posts}
dup = "/blog/2018/8/23/sealife-single-to-be-released-9-3-j5t9f"
twin = "/blog/2018/8/23/sealife-single-to-be-released-9-3"
if dup in by_url and twin in by_url:
    if text_of(by_url[dup]["body"])[:400] == text_of(by_url[twin]["body"])[:400]:
        DUPES[dup] = post_url[twin]
    else:
        report["notes"].append("j5t9f post differs from its twin; kept both")

# album track URLs, from the archived album JSON
tracks = {}
for album, artist in ALBUMS.items():
    f = ARCH / "pages" / (album.strip("/") + ".json")
    if f.exists():
        for t in json.loads(f.read_text()).get("items", []):
            tracks[t["fullUrl"]] = artist


def link_map(path):
    path = path if path == "/" else path.rstrip("/")
    if path.startswith("/team-database"):
        return None
    if path in DUPES:
        return DUPES[path]
    if path in post_url:
        return post_url[path]
    if path in ALBUMS:
        return ALBUMS[path]
    if path in tracks:
        return tracks[path]
    for a, artist in ALBUMS.items():
        if path.startswith(a + "/"):
            return artist
    if path in TEASERS:
        return f"/artists#{TEASERS[path]}"
    if path in STATIC_REDIRECTS:
        return STATIC_REDIRECTS[path]
    if path in URL_MAPPINGS:
        return URL_MAPPINGS[path]
    if path.startswith("/s/"):  # Squarespace-hosted files (old one-sheet PDFs): not carried over
        report["squarespace_file_links"].append(path)
        return None
    return path


# ------------------------------------------------------------------ authors
fresh("_posts", "_drafts", "_case_aliases", "_tag_pages", "_category_pages", "_releases", "_legacy", "_pages", "_unpublished")
(ROOT / "_data").mkdir(exist_ok=True)

authors = {}
name_to_key = {}
for it in wp_items:
    link = it.findtext("link") or ""
    if "/team-database" not in link:
        continue
    name = re.sub(r"\s+", " ", it.findtext("title") or "").strip()
    key = link.rstrip("/").rsplit("/", 1)[1]
    key = {"maxschoenfeld": "max-schoenfeld", "bill-darksoft": "darksoft", "chriss-goossens": "chris-goossens"}.get(key, key)
    meta = {m.findtext("wp:meta_key", namespaces=WP): m.findtext("wp:meta_value", namespaces=WP)
            for m in it.findall("wp:postmeta", namespaces=WP)}
    photo = wp_att.get(meta.get("_thumbnail_id"))
    conv = Converter(images, link_map)
    bio = conv.body(it.findtext("content:encoded", namespaces=WP) or "").strip()
    first_img = re.search(r"!\[[^\]]*\]\(([^)]+)\)|<img src=\"([^\"]+)\"", bio)
    bio = re.sub(r"<figure>.*?</figure>|!\[[^\]]*\]\([^)]+\)", "", bio).strip()  # photo is shown separately
    bio = re.sub(r"\n{3,}", "\n\n", bio)
    img = images.local(photo) if photo else ((first_img.group(1) or first_img.group(2)) if first_img else None)
    authors[key] = {"name": name, "bio": bio or None, "image": img}
    name_to_key[name] = key
authors["look-up-records"] = {"name": "Look Up Records", "bio": None, "image": None}
name_to_key["Look Up Records"] = "look-up-records"


def _n(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())




def author_key(name):
    name = re.sub(r"\s+", " ", name or "").strip()
    if "@" in name:  # Squarespace login emails (draft authors): never write them into the site
        return "look-up-records"
    for known, key in list(name_to_key.items()):
        if _n(known) == _n(name):
            return key
    if name not in name_to_key:
        k = slugify(name)
        authors[k] = {"name": name, "bio": None, "image": None}
        name_to_key[name] = k
        report["authors_without_bio"].append(name)
    return name_to_key[name]


# ------------------------------------------------------------------ posts
# Tags that differ only by case are merged into the most-used spelling; the other spellings'
# URLs become case-alias redirects (see _case_aliases below).
raw_tags = Counter(t for p in posts for t in (p.get("tags") or []))
canon_tag = {}
for t in raw_tags:
    group = [x for x in raw_tags if x.lower() == t.lower()]
    canon_tag[t] = sorted(group, key=lambda x: (-raw_tags[x], x))[0]
tag_count, cat_count = Counter(), Counter()
for p in posts:
    if p["fullUrl"] in DUPES:
        continue
    conv = Converter(images, link_map)
    body = conv.body(p["body"])
    d = ts(p["publishOn"])
    slug = p["fullUrl"].rsplit("/", 1)[1]
    fm = {
        "title": html.unescape(p["title"]).strip(),
        "date": d.strftime("%Y-%m-%d %H:%M:%S %z"),
        "author": author_key((p.get("author") or {}).get("displayName")),
        "categories": p.get("categories") or [],
        "tags": list(dict.fromkeys(canon_tag[t] for t in (p.get("tags") or []))),
    }
    if p.get("assetUrl"):
        fm["image"] = images.local(p["assetUrl"])
    ex = text_of(p.get("excerpt"))
    if ex:
        fm["excerpt"] = ex
    fm["permalink"] = post_url[p["fullUrl"]]
    if p["fullUrl"] != fm["permalink"]:
        fm["legacy_url"] = p["fullUrl"]
    fm["squarespace_id"] = p["id"]
    tag_count.update(fm["tags"])
    cat_count.update(fm["categories"])
    write_doc(ROOT / "_posts" / f"{d:%Y-%m-%d}-{slug}.md", fm, body)
    for n in conv.log:
        report["dropped"].append(f"{slug}: {n}")

# ------------------------------------------------------------------ drafts (WordPress export)
for it in wp_items:
    if it.findtext("wp:post_type", namespaces=WP) != "post" or it.findtext("wp:status", namespaces=WP) == "publish":
        continue
    link = it.findtext("link") or ""
    if "/team-database" in link:
        continue
    slug = link.rstrip("/").rsplit("/", 1)[1] or slugify(it.findtext("title") or "draft")
    conv = Converter(images, link_map)
    body = conv.body(it.findtext("content:encoded", namespaces=WP) or "")
    cats = [c.text for c in it.findall("category") if c.get("domain") == "category"]
    tags = [c.text for c in it.findall("category") if c.get("domain") == "post_tag"]
    fm = {"title": html.unescape(it.findtext("title") or "").strip(),
          "author": author_key(it.findtext("dc:creator", namespaces=WP)),
          "categories": cats, "tags": tags, "permalink": f"/blog/{slug}",
          "squarespace_status": it.findtext("wp:status", namespaces=WP),
          "squarespace_date": it.findtext("wp:post_date", namespaces=WP)}
    write_doc(ROOT / "_drafts" / f"{slug}.md", fm, body)

# ------------------------------------------------------------------ authors.yml
(ROOT / "_data/authors.yml").write_text(yaml.safe_dump(authors, sort_keys=True, allow_unicode=True, width=1000))

# ------------------------------------------------------------------ tag + category pages (same URLs)
sm_tag = {urllib.parse.unquote_plus(p.split("/blog/tag/", 1)[1]): p for p in sitemap_paths if "/blog/tag/" in p}
sm_cat = {urllib.parse.unquote_plus(p.split("/blog/category/", 1)[1]): p for p in sitemap_paths if "/blog/category/" in p}
case_aliases = {"/MARS": "/mars", "/LUFU": "/lufu"}
for kind, counts, sm, folder in (("tag", tag_count, sm_tag, "_tag_pages"), ("category", cat_count, sm_cat, "_category_pages")):
    canon = canon_tag if kind == "tag" else {}
    for name in sorted(set(counts) | set(sm)):
        url = sm.get(name) or f"/blog/{kind}/" + urllib.parse.quote_plus(name)
        if canon.get(name, name) != name:
            target = canon[name]
            case_aliases[url] = sm.get(target) or f"/blog/{kind}/" + urllib.parse.quote_plus(target)
            continue
        fm = {"layout": kind, kind: name, "title": f"{name}", "permalink": url, "post_count": counts.get(name, 0)}
        write_doc(ROOT / folder / f"{slugify(name, 80)}-{abs(hash(name)) % 10**6}.md", fm)
        if not counts.get(name):
            report["empty_term_pages"].append(url)

# ------------------------------------------------------------------ releases (/catalog/*)
cat = load("pages/catalog.json")
releases = []
for it in cat.get("items", []):
    title = html.unescape(it.get("title") or "").strip() or it["urlId"].rsplit("/", 1)[-1].replace("-", " ").title()
    m = re.search(r"\((\d{4})\)", title)
    tags = it.get("tags") or []
    click = it.get("clickthroughUrl") or ""
    fm = {"title": re.sub(r"\s*\(\d{4}\)\s*$", "", title), "year": int(m.group(1)) if m else None,
          "artist": tags[0] if tags else None, "image": images.local(it.get("assetUrl")) if it.get("assetUrl") else None,
          "artist_page": link_map(click) if click.startswith("/") else None,
          "external_link": click if click.startswith("http") else None,
          "permalink": it["fullUrl"], "order": it.get("displayIndex")}
    desc = Converter(images, link_map).body(it.get("description") or "") if it.get("description") else ""
    write_doc(ROOT / "_releases" / f"{slugify(it['urlId'], 80)}.md", fm, desc)
    releases.append(fm)

# ------------------------------------------------------------------ core pages
PAGES = {  # archived file -> new permalink
    "_root": "/", "about": "/about", "code-of-conduct": "/code-of-conduct", "newsletter": "/newsletter",
    "darksoft": "/darksoft", "sealife": "/sealife", "swym": "/swym", "banadu": "/banadu",
    "elephants-and-dogs": "/elephants-and-dogs", "stacking-pennies": "/stacking-pennies", "sightings": "/sightings",
    "mars": "/mars", "lufu": "/lufu", "look-up-fest": "/look-up-fest", "look-up-fest-portals": "/look-up-fest-portals",
}
for name, url in PAGES.items():
    d = load(f"pages/{name}.json")
    coll = d.get("collection") or {}
    conv = Converter(images, link_map)
    body = conv.body(d.get("mainContent") or "")
    seo = coll.get("seoData") or {}
    fm = {"layout": "page", "title": html.unescape(coll.get("title") or name).strip(), "permalink": url,
          "description": seo.get("seoDescription") or text_of(coll.get("description")) or None,
          "image": images.local(coll["mainImage"]["assetUrl"]) if (coll.get("mainImage") or {}).get("assetUrl") else None,
          "phase1_raw": True}
    fn = "index" if url == "/" else name
    write_doc(ROOT / "_pages" / f"{fn}.md", {k: v for k, v in fm.items() if v is not None}, body)
    report["page_dropped"] += [f"{url}: {n}" for n in conv.log]

# artist teasers -> _data/artists.yml (roster for /artists)
roster = []
art = load("pages/artists.json")
for c in art["collection"].get("collections", []):
    key = TEASERS.get(c["fullUrl"]) or c["fullUrl"].strip("/").replace("artists/", "")
    t = ARCH / "pages" / (c["fullUrl"].strip("/") + ".json")
    blurb, img = "", None
    if t.exists():
        td = json.loads(t.read_text())
        conv = Converter(images, link_map)
        blurb = conv.body(td.get("mainContent") or "").strip()
        m = re.search(r"\]\((/assets/img/[^)]+)\)|src=\"(/assets/img/[^\"]+)\"", blurb)
        img = (m.group(1) or m.group(2)) if m else None
    page = f"/{key}" if (ARCH / "pages" / f"{key}.json").exists() and key in [p.strip("/") for p in PAGES.values()] else None
    if c["title"] == "Darksoft":
        page, key = "/darksoft", "darksoft"
    roster.append({"key": key, "name": c["title"], "page": page, "image": img, "teaser_url": c["fullUrl"], "blurb": blurb})
(ROOT / "_data/artists.yml").write_text(yaml.safe_dump(roster, sort_keys=False, allow_unicode=True, width=1000))

# never-public pages from the WordPress export (reference only)
public_titles = {"Home", "About", "Darksoft", "Contact", "Blog-home", "Newsletter", "Look Up Fest", "Sealife", "Thank you",
                 "Code of Conduct", "Banadu", "Events", "SWYM", "Look Up Fest: Mars", "Elephants and Dogs",
                 "Stacking Pennies", "Sightings", "Look Up Fest: Portals", "Look Up Fest: Underwater"}
for it in wp_items:
    if it.findtext("wp:post_type", namespaces=WP) == "page" and (it.findtext("title") or "") not in public_titles:
        title = it.findtext("title") or "page"
        body = Converter(images, link_map).body(it.findtext("content:encoded", namespaces=WP) or "")
        write_doc(ROOT / "_unpublished" / f"{slugify(title)}.md", {"title": title, "squarespace_url": it.findtext("link")}, body)

# ------------------------------------------------------------------ redirect stubs
redirects = {}
for old, new in post_url.items():
    if old != new:
        redirects[old] = new
redirects.update(DUPES)
redirects.update(ALBUMS)
redirects.update(tracks)
redirects.update({k: f"/artists#{v}" for k, v in TEASERS.items()})
redirects.update(STATIC_REDIRECTS)
redirects.update(URL_MAPPINGS)
for i, (old, new) in enumerate(sorted(redirects.items())):
    write_doc(ROOT / "_legacy" / f"{slugify(old, 90)}-{i}.md", {"permalink": old, "redirect_to": new})

for i, (old, new) in enumerate(sorted(case_aliases.items())):
    write_doc(ROOT / "_case_aliases" / f"{slugify(old, 90)}-{i}.md", {"permalink": old, "redirect_to": new})

# ------------------------------------------------------------------ outputs
out = ROOT / "scripts/convert/out"
out.mkdir(parents=True, exist_ok=True)
(out / "images.json").write_text(json.dumps(images.used, indent=1, sort_keys=True))
report["images_missing"] = sorted(images.missing)
summary = {"posts": len(posts) - len(DUPES), "drafts": len(list((ROOT / "_drafts").glob("*.md"))),
           "authors": len(authors), "tags": len(tag_count), "categories": len(cat_count),
           "releases": len(releases), "pages": len(PAGES), "redirects": len(redirects), "case_aliases": len(case_aliases),
           "images": len(images.used), "images_missing": len(images.missing)}
report["summary"] = summary
(out / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True, default=str))
print(json.dumps(summary, indent=1))
for k in ("notes", "authors_without_bio", "squarespace_file_links", "empty_term_pages"):
    if report.get(k):
        print(k, len(report[k]), report[k][:6])
print("dropped:", Counter(re.sub(r"^[^:]+: ", "", d)[:40] for d in report["dropped"]).most_common(8))
