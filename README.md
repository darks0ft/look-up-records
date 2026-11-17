# Look Up Records — website

Source for **https://www.look-up-records.com**, a static Jekyll site for GitHub Pages. It replaces the old Squarespace site (shut down Nov 2026) and keeps every old URL working. See `MIGRATION-PLAN.md` for the migration plan.

## Layout

| Path | What |
|---|---|
| `_posts/` | Blog posts (Markdown). Each one sets `permalink: /blog/<slug>` so URLs match Squarespace exactly |
| `_drafts/` | Never-published Squarespace drafts, kept for reference |
| `_data/authors.yml` | Byline authors; a post's `author:` is a key here (bio and photo show under the post) |
| `_data/artists.yml` | Roster used by `/artists` |
| `_pages/` | Core pages (about, artist pages, Look Up Fest pages…) |
| `_releases/` | Catalog entries at `/catalog/...` |
| `_tag_pages/`, `_category_pages/` | `/blog/tag/<Tag>` and `/blog/category/<Category>` |
| `_legacy/` | Redirect stubs for retired URLs (dated post URLs, album pages, Squarespace URL mappings) |
| `_case_aliases/` | Redirect stubs whose URL differs from a real page only by letter case (built on GitHub Pages, skipped locally) |
| `assets/img/` | Post and page images (WebP, max 1600px wide) |
| `archive/` | (git-ignored) full snapshot of the Squarespace site, the WordPress export and admin notes |
| `scripts/` | Archive, conversion and verification scripts |

## Local preview

```bash
/opt/homebrew/opt/ruby@3.3/bin/bundle exec jekyll serve --config _config.yml,_config.local.yml --port 4002
```

## Re-running the conversion (only needed if the converter changes)

```bash
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
.venv/bin/python -I scripts/convert/convert.py archive/ .
.venv/bin/python -I scripts/convert/images.py
```

The converter overwrites `_posts`, `_drafts`, `_pages`, `_releases`, `_tag_pages`, `_category_pages`, `_legacy`, `_case_aliases` and `_data/authors.yml`/`artists.yml`. Once those files are being edited by hand, stop re-running it.

## Checking URLs

```bash
.venv/bin/python -I scripts/verify/check_site.py /tmp/look-up-site --local
```

This checks every old Squarespace URL (from the archived sitemap and crawl) and every internal link and image in the build.
