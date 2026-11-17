# Look Up Records: Squarespace → GitHub Pages

Revised 2026-11-16. The goal is to keep look-up-records.com as a historic archive and as the label for ongoing personal releases, with a new design and no loss of SEO. Hosting moves to GitHub Pages and uses the same Jekyll stack as the Darksoft site (`~/code/website`).

**Cost after the move:** $20/yr for the domain (stays at Squarespace Domains, renews Aug), down from $220/yr.

## Decisions

| Topic | Decision |
|---|---|
| Album pages and audio (9 albums, 80 MP3s, 686 MB) | **Drop.** Don't download them. Redirect the album and track URLs to the artist pages. |
| Contact form | **Remove.** Don't replace it. |
| Newsletter | Reuse the Darksoft Mailchimp signup, with a hidden "Look Up" tag so you can tell where a signup came from. |
| `/team-database/*` (already 404) | Don't rebuild these pages. |
| Author bylines | **Keep, done properly:** an `_data/authors.yml` file (name, photo, short bio) and a byline card in the post layout, filled from each post's `author:` front matter. |
| Date-based post URLs (28) | **Retire.** Move them to `/blog/<slug>` and redirect the old URLs. |
| Domain | Keep it at Squarespace Domains and point its DNS to GitHub Pages. Transferring it out is optional, later. |
| Analytics | The current tracking is dead Universal Analytics. Either set up GA4 fresh or drop analytics. |

## URL map (433 URLs in the sitemap, plus 80 track URLs)

| Group | Count | Treatment |
|---|---|---|
| Blog posts at `/blog/<slug>` | 123 | Kept exactly as they are |
| Blog posts at `/blog/YYYY/M/D/<slug>` | 28 | Moved to `/blog/<slug>` (no collisions, checked), with redirects from the old URLs |
| Duplicate post `.../sealife-single-to-be-released-9-3-j5t9f` | 1 | Redirected to its twin |
| Category pages `/blog/category/*` | 6 | Kept, generated automatically |
| Tag pages `/blog/tag/*` | 245 | Kept, generated automatically (test that the `+` in these URLs works on GitHub Pages) |
| Core pages (about, artists, catalog, artist pages, the fest pages, newsletter, code of conduct) | about 25 | Kept, redesigned |
| `/home`, `/blog-home`, `/thank-you`, `/contact`, `/events` | 5 | Redirected to the best new page |
| Album pages `/artist/album` | 9 | Redirected to the artist page |
| Track pages `/artist/album/track` | 80 | Redirected to the artist page (generated from the JSON) |

GitHub Pages redirects are `jekyll-redirect-from` meta-refresh pages with a canonical tag. Google treats them as permanent. If real 301s are ever needed, put Cloudflare (free) in front of the site later.

## Phases

### Phase 0: archive before Nov 22 ✅ done 2026-11-16
- [x] Script: save `?format=json` and the rendered HTML for every sitemap URL, with no audio.
- [x] Script: download original images (about 975, about 870 MB) to a local archive outside the repo.
- [x] Admin: Settings → Import/Export → WordPress XML (a backup that includes the 17 drafts).
- [x] Admin: record URL Mappings, Code Injection, and any store products (3 posts contain product blocks).
- [x] Admin: copy **every DNS record**, especially any MX/TXT records for email on the domain.
- [x] Admin: delete the album pages so the audio comes off the public site now.
- [x] Billing: the site plan is cancelled at the end of its term and expires Nov 22, 2026 (no renewal charge).

### Phase 1: scaffold and convert content ✅ done 2026-11-16
- [x] New repo, Jekyll setup copied from the Darksoft site (config, includes, Mailchimp signup include).
- [x] Converter script: JSON → `_posts/*.md` with front matter (title, date, author, categories, tags, cover image, permalink, redirect_from).
- [x] Clean the Squarespace block HTML; standardize embeds (Spotify, YouTube, SoundCloud, Bandcamp) as includes; remove the old byline blocks.
- [x] Images: convert to WebP at about 1600px wide (about 100–150 MB) and rewrite every URL to point to the local copies.
- [x] `_data/authors.yml` with the 8 bylined writers, plus 14 author names taken from the posts.

### Phase 2: design (1–2 sessions)
- Built around the label: home (latest release + news), artists (current and past), catalog/discography with links to listen and buy, a journal (the blog), a Look Up Fest archive (Mars, Portals…), about, code of conduct, and newsletter.

### Phase 3: URL check and launch (1 session)
- [ ] Script: every old URL returns 200 or a correct redirect on the local build. Check internal links and images.
- [ ] Sitemap, RSS at `/blog?format=rss` (it will serve `/blog`, so add a new feed path), canonicals, OG tags.
- [ ] DNS: point the 4 A records and the `www` CNAME to GitHub Pages, keep the MX/TXT records, turn on HTTPS.
- [ ] Search Console: submit the new sitemap. Then cancel the Squarespace site plan and keep the domain.

## Open items found in Phase 1
- **Test on real GitHub Pages first:** `/blog` (from `blog.html`) next to the `blog/` folder of posts, and the same for `/catalog`, `/darksoft`, `/sealife` and `/swym`. The local server redirects `/blog` to `/blog/`. If GitHub Pages does the same, fall back to serving index pages from `<dir>/index.html` and accept the 301 to a trailing slash.
- Test the `+` in tag URLs and the case-alias stubs on GitHub Pages (both only happen on its case-sensitive build).
- The Mailchimp tag ID for Look Up signups is in `_data/newsletter.yml` (TODO).
- Dropped during conversion: 22 SubmitHub widgets, 3 dead store product blocks, 1 audio player, 1 Spotify "follow" button.
- RSS: Squarespace's `/blog?format=rss` can't be reproduced, because GitHub Pages ignores query strings. The new feed is `/feed.xml`.
