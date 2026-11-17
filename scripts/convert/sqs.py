"""Shared helpers: turn Squarespace 7.0 block HTML into clean Markdown, and track images.

Used by convert.py. All input comes from archive/ (see archive/README.md).
"""
import hashlib, html, json, re, unicodedata, urllib.parse
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Comment
from markdownify import MarkdownConverter

SITE_HOSTS = ("look-up-records.com", "www.look-up-records.com", "look-up-records.squarespace.com")


def slugify(s, maxlen=60):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s[:maxlen].strip("-") or "x"


def text_of(html_str):
    t = BeautifulSoup(html_str or "", "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


# ---------------------------------------------------------------- images

class Images:
    """Maps Squarespace CDN URLs to archived originals and to their new /assets/img/ paths."""

    EXT = re.compile(r"\.(jpe?g|png|gif|webp|svg|ico|tiff?|heic)$", re.I)

    def __init__(self, archive: Path):
        self.archive = archive
        man = json.loads((archive / "images-manifest.json").read_text())
        self.files = {}
        for u, v in man.items():
            if v.get("file"):
                self.files[self.norm(u)] = archive / v["file"]
        self.used = {}      # new url -> archived source file
        self.missing = set()

    @staticmethod
    def norm(u):
        u = html.unescape(u).strip().split("?")[0].split("#")[0]
        if u.startswith("//"):
            u = "https:" + u
        u = u.replace("http://", "https://")
        u = re.sub(r"(/image-asset\.\w+)/img\.\w+$", r"\1", u)  # alias of the same asset
        return urllib.parse.unquote(u)

    @staticmethod
    def is_cdn(u):
        return bool(u) and ("squarespace-cdn.com" in u or "static1.squarespace.com" in u)

    def local(self, u):
        """Return the new site path for a CDN image URL (or the URL unchanged if not a CDN image)."""
        if not self.is_cdn(u):
            return u
        key = self.norm(u)
        src = self.files.get(key)
        if not src:
            self.missing.add(key)
            return u
        base = re.sub(r"\.\w+$", "", src.name)
        if base.lower() in ("image-asset", "img", "image"):
            base = src.parent.name.split("-", 1)[-1]
        ext = src.suffix.lower()
        out_ext = ext if ext in (".gif", ".svg", ".ico") else ".webp"
        name = f"{slugify(base, 50)}-{hashlib.sha1(key.encode()).hexdigest()[:6]}{out_ext}"
        url = f"/assets/img/{name}"
        self.used[url] = str(src)
        return url

    @staticmethod
    def alt_from(u):
        name = urllib.parse.unquote(u.split("?")[0].rsplit("/", 1)[-1]).replace("+", " ")
        name = re.sub(r"\.\w+$", "", name)
        if re.fullmatch(r"(image-asset|img|image|IMG[_ ]?\d+|DSC\w*|\w{8}-\w{4}.*)", name, re.I):
            return ""
        return re.sub(r"[-_]+", " ", name).strip()


# ---------------------------------------------------------------- embeds

def embed_html(src, title="", height=None):
    """Normalize an iframe src into a responsive, lazy-loaded embed. Returns '' for dropped widgets."""
    src = html.unescape(src or "").strip()
    if src.startswith("//"):
        src = "https:" + src
    if "cdn.embedly.com" in src:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(src).query)
        inner = (q.get("src") or q.get("url") or [""])[0]
        return embed_html(inner, title or (q.get("display_name") or [""])[0], height)
    if "submithub.com" in src or "spotify.com/follow" in src:
        return ""
    m = re.search(r"(?:youtube(?:-nocookie)?\.com/(?:embed/|watch\?v=)|youtu\.be/)([\w-]{11})", src)
    if m:
        t = html.escape(title or "YouTube video", quote=True)
        return (f'<div class="embed embed-video"><iframe src="https://www.youtube-nocookie.com/embed/{m.group(1)}" '
                f'title="{t}" loading="lazy" allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; web-share" '
                f'referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>')
    m = re.search(r"vimeo\.com/(?:video/)?(\d+)", src)
    if m:
        return (f'<div class="embed embed-video"><iframe src="https://player.vimeo.com/video/{m.group(1)}" '
                f'title="{html.escape(title or "Vimeo video", quote=True)}" loading="lazy" allowfullscreen></iframe></div>')
    m = re.search(r"(track|album|playlist|artist|episode|show)[:/]([A-Za-z0-9]{22})", src) if "spotify" in src else None
    if m:
        kind, sid = m.groups()
        h = 152 if kind in ("track", "episode") else 352
        return (f'<div class="embed embed-spotify"><iframe src="https://open.spotify.com/embed/{kind}/{sid}" '
                f'title="Spotify {kind}" height="{h}" loading="lazy" '
                f'allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"></iframe></div>')
    if "soundcloud.com" in src:
        return (f'<div class="embed embed-soundcloud"><iframe src="{html.escape(src, quote=True)}" title="SoundCloud player" '
                f'height="{height or 166}" loading="lazy" allow="autoplay"></iframe></div>')
    if "bandcamp.com" in src:
        h = height or (120 if "size=small" not in src else 42)
        return (f'<div class="embed embed-bandcamp"><iframe src="{html.escape(src, quote=True)}" title="Bandcamp player" '
                f'height="{h}" loading="lazy"></iframe></div>')
    if not src:
        return ""
    return (f'<div class="embed"><iframe src="{html.escape(src, quote=True)}" title="{html.escape(title or "Embedded content", quote=True)}" '
            f'loading="lazy"></iframe></div>')


# ---------------------------------------------------------------- markdown

class MD(MarkdownConverter):
    def convert_img(self, el, text, *args, **kw):
        alt = (el.get("alt") or "").replace("]", "")
        return f"![{alt}]({el.get('src', '')})"


def to_md(fragment_html):
    md = MD(heading_style="ATX", bullets="-", strong_em_symbol="*", escape_misc=False).convert(fragment_html)
    md = re.sub(r"[ \t]+\n", lambda m: "  \n" if m.group(0).startswith("  ") else "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


KEEP_ATTRS = {"a": ("href", "title"), "img": ("src", "alt"), "iframe": ("src", "title", "height"), "th": ("colspan",), "td": ("colspan",)}


class Converter:
    """Converts one Squarespace body (or page mainContent) to Markdown, rewriting links and images."""

    def __init__(self, images: Images, link_map=None):
        self.images = images
        self.link_map = link_map or (lambda path: path)
        self.log = []          # notes about dropped content
        self.links = set()     # internal links found (after rewriting)

    # -- links
    def rewrite_href(self, href):
        href = html.unescape(href or "").strip()
        if not href or href.startswith(("javascript:", "#")):
            return href
        p = urllib.parse.urlparse(href)
        if p.netloc in SITE_HOSTS or (not p.netloc and href.startswith("/")):
            path = urllib.parse.unquote(p.path) or "/"
            if Images.is_cdn(href):
                return self.images.local(href)
            new = self.link_map(path)
            if new is None:
                return None  # drop the link, keep the text
            out = new + (("#" + p.fragment) if p.fragment else "")
            self.links.add(new)
            return out
        if Images.is_cdn(href):
            return self.images.local(href)
        return href

    # -- cleaning
    def clean(self, node):
        for t in node.find_all(["script", "style", "noscript", "svg", "button", "form", "input"]):
            t.decompose()
        for c in node.find_all(string=lambda s: isinstance(s, Comment)):
            c.extract()
        for img in node.find_all("img"):
            src = img.get("data-src") or img.get("data-image") or img.get("src") or ""
            img.attrs = {"src": self.images.local(src), "alt": img.get("alt") or Images.alt_from(src)}
        for a in node.find_all("a"):
            new = self.rewrite_href(a.get("href"))
            if new is None or new == "":
                a.unwrap()
                continue
            a.attrs = {"href": new}
        for t in node.find_all(True):
            if t.name in ("span", "font", "u", "section", "article", "figure", "header", "footer", "o:p"):
                if t.name == "u" or t.name != "figure":
                    t.unwrap()
                    continue
            keep = KEEP_ATTRS.get(t.name, ())
            t.attrs = {k: v for k, v in t.attrs.items() if k in keep}
        for h1 in node.find_all("h1"):
            h1.name = "h2"
        for p in node.find_all("p"):
            if not p.get_text(strip=True).replace("\xa0", "") and not p.find(["img", "iframe"]):
                p.decompose()
        return node

    def fragment(self, node):
        """Generic HTML -> Markdown, pulling iframes out as embed blocks."""
        parts = []
        node = self.clean(node)
        iframes = node.find_all("iframe")
        if not iframes:
            return to_md(str(node))
        # split around iframes, preserving order
        for f in iframes:
            marker = NavigableString(f"\n\nEMBED_{len(parts)}\n\n")
            parts.append(embed_html(f.get("src"), f.get("title", ""), f.get("height")))
            if not parts[-1]:
                self.log.append(f"dropped widget iframe {f.get('src', '')[:80]}")
            f.replace_with(marker)
        md = to_md(str(node))
        for i, e in enumerate(parts):
            md = md.replace(f"EMBED\\_{i}", e).replace(f"EMBED_{i}", e)
        return md

    # -- blocks
    def block(self, b):
        cls = " ".join(b.get("class", []))
        content = b.select_one(".sqs-block-content") or b
        if "summary-block" in cls or "summary-v2-block" in cls:
            return ""  # bylines (now from front matter) and empty "related" widgets
        if "horizontalrule-block" in cls:
            return "* * *"
        if "image-block" in cls:
            return self.image_block(content)
        if "gallery-block" in cls:
            figs = []
            for slide in content.select(".slide, .image-slide-anchor, img"):
                img = slide if slide.name == "img" else slide.find("img")
                if not img:
                    continue
                src = img.get("data-src") or img.get("data-image") or img.get("src")
                if src and Images.is_cdn(src):
                    figs.append(f'<img src="{self.images.local(src)}" alt="{html.escape(img.get("alt") or Images.alt_from(src), quote=True)}" loading="lazy">')
            figs = list(dict.fromkeys(figs))
            return '<div class="gallery">' + "".join(figs) + "</div>" if figs else ""
        if "video-block" in cls:
            holder = content.select_one("[data-html]")
            src = ""
            title = ""
            if holder:
                inner = BeautifulSoup(holder["data-html"], "html.parser").find("iframe")
                if inner:
                    src, title = inner.get("src", ""), inner.get("title", "")
            if not src:
                f = content.find("iframe")
                src = f.get("src", "") if f else ""
            if not src:
                u = content.select_one("[data-url]")
                src = u.get("data-url", "") if u else ""
            out = embed_html(src, title)
            cap = content.select_one(".video-caption")
            if cap and cap.get_text(strip=True):
                out += "\n\n" + self.fragment(cap)
            if not out:
                self.log.append("video block without a source")
            return out
        if "embed-block" in cls:
            f = content.find("iframe")
            if f:
                return embed_html(f.get("src"), f.get("title", ""), f.get("height"))
            holder = content.select_one("[data-html]")
            if holder:
                return self.fragment(BeautifulSoup(holder["data-html"], "html.parser"))
            return ""
        if "button-block" in cls:
            a = content.find("a")
            if not a:
                return ""
            href = self.rewrite_href(a.get("href"))
            label = a.get_text(" ", strip=True)
            if href is None:
                self.log.append(f"dropped button to a retired file: {label}")
                return ""
            if not href:
                return label
            return f'BUTTON|{href}|{label}'
        if "quote-block" in cls:
            q = content.find("blockquote")
            src = content.find("figcaption")
            text = re.sub(r'^[“"]+|[”"]+$', "", q.get_text(" ", strip=True)) if q else ""
            out = "> " + text
            if src and src.get_text(strip=True):
                out += "\n>\n> — " + src.get_text(" ", strip=True).lstrip("—– ")
            return out
        if "marquee-block" in cls:
            a = content.find("a", class_="Marquee-hitbox") or content.find("a")
            txt = content.select_one(".v6-visually-hidden")
            label = txt.get_text(" ", strip=True).replace("〰️", "").strip() if txt else ""
            href = self.rewrite_href(a.get("href")) if a else ""
            return f'<p class="callout"><a href="{href}">{html.escape(label)}</a></p>' if href else label
        if "audio-block" in cls:
            self.log.append("dropped audio player")
            return ""
        if "product" in (b.get("data-definition-name") or "") or "product-block" in str(content)[:400]:
            self.log.append("dropped store product block")
            return ""
        # html-block, markdown-block, code-block and anything else
        return self.fragment(content)

    def image_block(self, content):
        img = content.find("img")
        if not img:
            return ""
        src = img.get("data-src") or img.get("data-image") or img.get("src") or ""
        url = self.images.local(src)
        alt = img.get("alt") or Images.alt_from(src)
        a = content.find("a", href=True)
        href = self.rewrite_href(a["href"]) if a else None
        cap = content.find("figcaption")
        cap_html = ""
        if cap and cap.get_text(strip=True):
            # Squarespace captions can have a title and a description: render as "<strong>Title</strong> — description"
            t = cap.select_one(".image-title")
            d = cap.select_one(".image-caption, .image-subtitle")
            if t and t.get_text(strip=True) and d and d.get_text(strip=True):
                strong = BeautifulSoup(f"<strong>{html.escape(t.get_text(' ', strip=True).rstrip(':').strip())}</strong> — ", "html.parser")
                t.replace_with(strong)
            cap = self.clean(cap)
            cap_html = "".join(str(c) for c in cap.contents).strip()
            cap_html = re.sub(r"</?(div|p)>", " ", cap_html).strip()
            cap_html = re.sub(r"\s+", " ", cap_html)
        img_tag = f'<img src="{url}" alt="{html.escape(alt, quote=True)}" loading="lazy">'
        if href:
            img_tag = f'<a href="{href}">{img_tag}</a>'
        if cap_html:
            return f"<figure>{img_tag}<figcaption>{cap_html}</figcaption></figure>"
        if href:
            return f"<figure>{img_tag}</figure>"
        return f"![{alt.replace(']', '')}]({url})"

    def body(self, body_html):
        soup = BeautifulSoup(body_html or "", "html.parser")
        blocks = soup.select(".sqs-block")
        if not blocks:
            return self.join([self.fragment(soup)])
        out = []
        for b in blocks:
            if b.find_parent(class_="sqs-block"):
                continue
            out.append(self.block(b))
        return self.join(out)

    @staticmethod
    def join(chunks):
        out, buttons = [], []

        def flush():
            if buttons:
                links = " ".join(f'<a class="button" href="{h}">{html.escape(l)}</a>' for h, l in buttons)
                out.append(f'<p class="buttons">{links}</p>')
                buttons.clear()

        for c in chunks:
            c = (c or "").strip()
            if not c:
                continue
            if c.startswith("BUTTON|"):
                _, h, l = c.split("|", 2)
                buttons.append((h, l))
                continue
            flush()
            out.append(c)
        flush()
        # drop the old "AUTHOR" heading that sat above the byline widget (bylines now come from front matter)
        while out and re.fullmatch(r"(#+\s*)?\**(about the )?author:?\**|(\* \* \*)", out[-1].strip(), re.I):
            out.pop()
        md = "\n\n".join(out)
        md = re.sub(r"(?m)^#{1,6}\s*$\n?", "", md)  # empty headings
        md = re.sub(r"(?im)^(#{1,6}\s*)?\**(about the )?author:?\**\s*$\n?", "", md)  # old byline headings
        md = re.sub(r"(\* \* \*\s*\n\s*)+\* \* \*", "* * *", md)
        md = re.sub(r"(?is)(\s*(#{1,6}\s*)?\**(about the )?author:?\**\s*|\s*\* \* \*\s*)+$", "", md)
        md = re.sub(r"(\* \* \*\n\n)+\* \* \*", "* * *", md)
        md = re.sub(r"^(\* \* \*\s*)+|(\s*\* \* \*)+$", "", md.strip())
        if "{{" in md or "{%" in md:
            md = "{% raw %}\n" + md + "\n{% endraw %}"
        return md.strip() + "\n"
