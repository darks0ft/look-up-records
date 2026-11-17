#!/usr/bin/env python3
"""Fill SEO front matter that can't be computed in Liquid before {% seo %} runs.

Usage: .venv/bin/python -I scripts/seo/fill_meta.py
Safe to re-run: it rewrites only the keys below (title/description/date/image) on
tag, category and author pages, releases, and the fest pages that lack a description.
"""
import json, re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
AUTHORS = yaml.safe_load((ROOT / "_data/authors.yml").read_text())
FESTS = {f["url"]: f for f in yaml.safe_load((ROOT / "_data/fests.yml").read_text())}


def split(path):
    t = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n?", t, re.S)
    return m.group(1), t[m.end():]


def set_keys(path, **kv):
    fm, body = split(path)
    for k, v in kv.items():
        line = f"{k}: {json.dumps(v, ensure_ascii=False)}"
        if re.search(rf"^{k}:.*$", fm, re.M):
            fm = re.sub(rf"^{k}:.*$", lambda _: line, fm, count=1, flags=re.M)
        else:
            fm += "\n" + line
    path.write_text(f"---\n{fm}\n---\n{body}")


def sentence(text, limit=155):
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", re.sub(r"\s+", " ", text or "")).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


CATEGORY = {
    "Advice": ("Music industry advice", "Practical advice for independent musicians from Look Up Records: promotion, touring, releasing music, and running a DIY label."),
    "DIY": ("DIY music guides", "Do-it-yourself guides for independent musicians from Look Up Records: recording at home, booking shows, and releasing music on your own."),
    "Event": ("Events", "Look Up Records event announcements, including Look Up Fest lineups, showcases, and calls for submissions."),
    "Local": ("Local music news", "Local music coverage from Look Up Records: Seattle and Pacific Northwest bands, venues, and scene news."),
    "Press Release": ("Press releases", "Look Up Records press releases: new albums, singles, music videos, and tour announcements from the label's artists."),
    "Review": ("Album and song reviews", "Album, EP and single reviews from the Look Up Records blog, covering dream pop, shoegaze, psych, and indie music."),
}

for p in sorted((ROOT / "_category_pages").glob("*.md")):
    fm, _ = split(p)
    cat = yaml.safe_load(fm)["category"]
    title, desc = CATEGORY[cat]
    set_keys(p, title=title, description=desc)

for p in sorted((ROOT / "_tag_pages").glob("*.md")):
    fm, _ = split(p)
    tag = str(yaml.safe_load(fm)["tag"])
    set_keys(p, title=f"Posts tagged “{tag}”",
             description=f"Posts tagged “{tag}” on the Look Up Records blog: reviews, interviews, news, and features from the independent label.")

for p in sorted((ROOT / "_author_pages").glob("*.md")):
    fm, _ = split(p)
    key = yaml.safe_load(fm)["author_key"]
    a = AUTHORS[key]
    if key == "look-up-records":
        desc = "Label news, release announcements, and posts written by the Look Up Records team."
    elif a.get("bio"):
        desc = sentence(a["bio"])
    else:
        desc = f"Posts by {a['name']} on the Look Up Records blog."
    kv = dict(title=f"Posts by {a['name']}", description=desc)
    if a.get("image"):
        kv["image"] = a["image"]
    set_keys(p, **kv)

for p in sorted((ROOT / "_releases").glob("*.md")):
    fm, _ = split(p)
    r = yaml.safe_load(fm)
    fmt = r.get("format") or "release"
    fmt = fmt if fmt.isupper() else fmt.lower()
    when = f"a {r['year']} {fmt}" if r.get("year") else f"a {fmt}"
    cat = f", catalog number {r['catalog_no']}" if r.get("catalog_no") else ""
    desc = f"{r['title']} by {r['artist']}, {when} released on Look Up Records{cat}. Listen on Bandcamp and streaming services."
    kv = dict(description=desc)
    if r.get("release_date") and len(str(r["release_date"])) == 10:
        kv["date"] = str(r["release_date"])
    set_keys(p, **kv)

FEST_DESC = {
    "/look-up-fest-2018": "Look Up Fest 2018, the first Look Up Fest: a sold-out, paranormal-themed mini music festival on September 9, 2018 at Machine House Brewery in Georgetown, Seattle.",
    "/lufu": "Look Up Fest: Underwater, a spooky aquatic mini music festival with 11 dreamy local bands on March 9, 2019 at Fred Wildlife Refuge in Seattle.",
    "/mars": "Look Up Fest: Mars, a space-age mini music festival of dreamy Pacific Northwest bands on September 7, 2019 at Substation in Seattle.",
}
for p in (ROOT / "_pages").glob("*.md"):
    fm, _ = split(p)
    d = yaml.safe_load(fm)
    if d.get("permalink") in FEST_DESC and not d.get("description"):
        set_keys(p, description=FEST_DESC[d["permalink"]])
        if not d.get("image") and d["permalink"] in FESTS:
            set_keys(p, image=FESTS[d["permalink"]]["image"])
print("done")
