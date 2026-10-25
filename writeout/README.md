# writeout/

Blog posts for kidharmilega.in/blog/, published by WriteOut. Don't edit by hand; change the post in WriteOut and republish.

`build.py` deletes and rebuilds `docs/` on every run. This folder is the copy that survives: `publish_blog()` copies
`writeout/blog/` into `docs/blog/`, fills in the markers below, and adds the posts to `sitemap.xml`.

## Layout

```
writeout/blog/index.html          /blog/ listing (until it exists, build.py serves a noindex placeholder)
writeout/blog/feed.xml            /blog/feed.xml RSS feed
writeout/blog/<slug>/index.html   one post, served at /blog/<slug>/
writeout/blog/<slug>/<file>       images or other files for that post (copied as they are)
```

Slugs are lowercase `a-z`, `0-9` and `-`. Never rename one; update the same files instead.

## Markers

Every page under `writeout/blog/` carries three markers. `build.py` replaces them with the site's own markup:

| Marker | Where | Becomes |
|---|---|---|
| `<!--KM:HEAD-->` | inside `<head>`, after the page's own title and meta tags | analytics tag, favicon, fonts, versioned `/assets/style.css` |
| `<!--KM:NAV-->` | first thing in `<body>` | site nav |
| `<!--KM:FOOTER-->` | last thing before `</body>` | site footer |

Don't link `/assets/style.css` yourself; the head block does. Post-specific CSS can go inline.

Each post also needs:

- `<link rel="canonical" href="https://kidharmilega.in/blog/<slug>/">`
- `<meta property="article:modified_time" content="YYYY-MM-DD">`, used as the sitemap `lastmod`

A post with `<meta name="robots" content="noindex...">` is published but left out of the sitemap.

## Publishing a post (one commit on `main`)

1. Write `writeout/blog/<slug>/index.html` with the markers.
2. Write `docs/blog/<slug>/index.html` with the markers already filled in, so the post is live before the next build.
   Take the fill-ins from `docs/assets/km-partials.json` (`head`, `nav`, `footer`), which `build.py` regenerates on
   every build.
3. Do the same for `blog/index.html` and `blog/feed.xml` in both folders.
4. In `docs/sitemap.xml`, add or update the post's `<url>` entry (and `/blog/`'s `lastmod`) just before `</urlset>`.
   The next build regenerates this from `writeout/`, so this edit only has to last until then.

To take a post down, delete `writeout/blog/<slug>/`, `docs/blog/<slug>/` and its sitemap entry.

WriteOut touches only `writeout/`, `docs/blog/` and `docs/sitemap.xml`.
