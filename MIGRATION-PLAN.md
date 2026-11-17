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

### Phase 2: design ✅ built 2026-11-17 (waiting on your review)
- Built around the label: home (latest release + news), artists (current and past), catalog/discography with links to listen and buy, a journal (the blog), a Look Up Fest archive (Mars, Portals…), about, code of conduct, and newsletter.

### Phase 3: URL check and launch (done 2026-11-17)
- [x] Every old URL returns 200 or a correct redirect: 539/539 on the local build, the GitHub test host and the live domain (`scripts/verify/check_live.py`).
- [x] Sitemap at `/sitemap.xml`, feed at `/feed.xml` (Squarespace's `/blog?format=rss` can't be reproduced), canonicals and OG tags via jekyll-seo-tag.
- [x] Repo `darks0ft/look-up-records` (public), Pages from `main` at the root, custom domain `www.look-up-records.com`. Unpublished `_drafts/` stay local and were scrubbed from history.
- [x] DNS: the domain was delegated to an old 2017 NS1 zone (`dns1-4.p04.nsone.net`), so the Squarespace DNS page wasn't live. Added GitHub's A records (185.199.108-111.153) and `www` CNAME `darks0ft.github.io` there, then switched to Squarespace nameservers. Google MX/SPF kept; Mailchimp DKIM and DMARC are live for the first time.
- [ ] HTTPS: enforce once GitHub issues the certificate.
- [ ] Search Console: submit `https://www.look-up-records.com/sitemap.xml`. The Squarespace site plan is already cancelled (expires Nov 22); the domain stays.

## Open items found in Phase 1
- **Test on real GitHub Pages first:** `/blog` (from `blog.html`) next to the `blog/` folder of posts, and the same for `/catalog`, `/darksoft`, `/sealife` and `/swym`. The local server redirects `/blog` to `/blog/`. If GitHub Pages does the same, fall back to serving index pages from `<dir>/index.html` and accept the 301 to a trailing slash.
- Test the `+` in tag URLs and the case-alias stubs on GitHub Pages (both only happen on its case-sensitive build).
- The Mailchimp tag ID for Look Up signups is in `_data/newsletter.yml` (TODO).
- Dropped during conversion: 22 SubmitHub widgets, 3 dead store product blocks, 1 audio player, 1 Spotify "follow" button.
- RSS: Squarespace's `/blog?format=rss` can't be reproduced, because GitHub Pages ignores query strings. The new feed is `/feed.xml`.

## To confirm after Phase 2
- **Catalog:** 6 releases were added that the old catalog was missing: A Jazz, Everybody's Smiling Nobody's Happy, Liebe ist Tot, State Birds, Everydayness, and A Mixtape for Martian Colonists. Darksoft's Spirit Goth albums (Grayscale, Rationalism) and the singles taken from albums are left out.
- **Catalog numbers:** `catalog_no` (LUR-001 to LUR-022) and release dates come from the "LOOK UP RECORDS CATALOG" sheet in Google Drive (ISRC tab). Beat Queen (LUR-012) was added from it. LUR-004 "First Light" and LUR-005 "Lost Time" (Close Encounter) are intentionally left off, and their old posts stay unpublished in `_drafts/`. Singles that never got an LUR number show no number.
- **Still undated:** Banadu & Pure Mood's "Cool Lover" isn't in the sheet. Add `release_date` in `_releases/` if you know it.
- **Peach Beach:** the sheet lists a one-track single on 2020-03-13; the site keeps the EP date of 2020-05-01.
- **Links:** the Spotify/Bandcamp links on releases were pulled from each announcement post. Spot-check them.
- **Look Up Fest:** `/look-up-fest` is now a hub linking all four fests (data in `_data/fests.yml`). The 2018 page it used to hold moved to `/look-up-fest-2018`. The hub copy is adapted from the "About Look Up Fest" section of the Portals page.
- **Homepage copy:** the hero line is "Indie aliens from the underground.", and the intro calls Look Up "Darksoft's DIY weirdo music label and blog."
- The old Squarespace /newsletter page's signup block had no storage set ("needs a storage option"), so it never saved signups.
