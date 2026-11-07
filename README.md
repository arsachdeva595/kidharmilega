# KidharMilega

**India's ODOP business discovery platform — one district, one product, one real opportunity.**

Built by [@startupwalebhaia](https://instagram.com/startupwalebhaia)

---

## The problem this solves

India's central government runs the **ODOP (One District One Product)** scheme — every district has a product it's historically been best at making. Bhagalpur makes silk. Moradabad makes brass. Bikaner makes namkeen. Tiruppur makes hosiery.

The scheme exists. The products exist. The export potential is real.

What doesn't exist is **a single place where a first-generation founder can find out what the actual opportunity looks like** — setup costs, margins, which government schemes apply, where to source raw materials, who the buyers are, and an honest answer to "kya yeh flop bhi ho sakta hai?"

KidharMilega is that place. 787 districts. One page per district. Reads like advice from someone who's been there — not a government report.

---

## How it works

Three scripts run in sequence:

```
find_urls.py  →  enrich.py  →  build.py  →  GitHub Pages
```

### `find_urls.py` — Source discovery

Builds `data/odop_urls.csv` — one row per district with every data source that exists:

- **Layer 1:** Probes official state govt ODOP pages (`district.state.gov.in/one-district-one-product/`)
- **Layer 2:** Finds research articles via DuckDuckGo — PIB press releases, IBEF reports, trade publications
- **Layer 3:** Finds YouTube video IDs for local entrepreneur content and cluster walkthroughs

```bash
python3 find_urls.py            # probe all govt URLs
python3 find_urls.py --google   # find research articles
python3 find_urls.py --youtube  # find YouTube videos
```

### `enrich.py` — AI enrichment

For every district, fetches from **all available sources simultaneously** (govt page + research articles + PDFs + YouTube transcripts), combines them into one research document, and runs two Claude Haiku calls:

1. **Extraction** — pulls only explicitly stated facts from the combined sources
2. **Generation** — uses those verified facts to generate 60+ structured content fields

Output goes into `data/scraped_facts.json` (extracted facts) and `data/enrichment_cache.json` (generated content).

```bash
python3 enrich.py               # enrich new/stale districts
python3 enrich.py --limit 50    # batch mode — process 50 at a time
python3 enrich.py --filter "Varanasi,Lucknow"  # specific districts
python3 enrich.py --force-scrape --filter "Varanasi"  # re-scrape from scratch
```

### `build.py` — Static site generation

Reads `data/districts.csv`, generates one HTML file per live district into `docs/`. No framework. No server. Loads in under a second on 2G.

```bash
python3 build.py           # production build
python3 build.py --local   # local preview build
```

Preview locally:
```bash
cd docs && python3 -m http.server 8080
# open http://localhost:8080
```

---

## Homepage (the hallway)

The homepage asks one question ("Batao, aaj kis kaam se aaye ho?") with six doors. Each door asks one follow-up and routes to a tool, guide, the community or a 1:1 call. Doors and options live in `HALLWAY` in `build.py`. `kidharmilega.in/#idea` (or `#odop`, `#suppliers`, `#buyers`, `#help`, `#guides`) opens a door directly, for reel and bio links. Clicks are sent to GA4 as `hallway_door`, `hallway_route` and `home_cta`.

- **Taaza guides** reads `/blog/feed.xml` in the browser, so a new WriteOut post shows up on the homepage without a rebuild.
- **Taaza reels** reads `docs/reels.json`: a list of reel links, newest first, and the first 3 are embedded. Edit it on GitHub and it is live on the next Pages deploy; `build.py` keeps the file when it rebuilds `docs/`. With an empty list (`[]`) the section stays hidden.

```json
[
  "https://www.instagram.com/reel/XXXXXXXXXXX/",
  "https://www.instagram.com/reel/YYYYYYYYYYY/",
  "https://www.instagram.com/reel/ZZZZZZZZZZZ/"
]
```

## Supplier Finder tool (`/tools/supplier-finder/`)

Free tool: the user picks an 8-digit HSN code and a district, leaves an email, and gets copy-paste AI prompts to find local suppliers (including the Google Maps / GMB step), plus a supplier audit checklist for that product category. `build.py` calls `supplier_finder.py`. Leads go to a Google Sheet through Apps Script. Setup is in `tools_src/supplier-finder/SETUP.md`.

## Scheme Finder tool (`/tools/scheme-finder/`)

Free tool: the user describes their business and themselves, leaves an email, and gets a detailed report of the central and state subsidies, loans and support they qualify for, with estimated subsidy, documents, how to apply and an action plan. `build.py` calls `scheme_finder.py`. Details in `tools_src/scheme-finder/README.md`.

## Budget Matcher tool (`/tools/budget-matcher/`)

Free tool: "₹50,000 mein kaunsa business?" The user enters their own money, state, loan preference and the kind of work they like, leaves an email, and gets ranked district businesses split into "start with your own money" and "with a PMEGP loan" (own money covers the 10% / 5% own contribution, project capped at ₹50 lakh), with setup cost, margins, break-even, rough EMI and links to the product page, Supplier Finder and Scheme Finder. Data comes from `data/districts.csv`; `build.py` calls `budget_matcher.py`, which writes `data.json` next to the page. Link to it with `?budget=50000&state=Uttar%20Pradesh` to prefill the form (handy for reel captions).

## HSN Code Finder tool (`/tools/hsn-code-finder/`)

Free, no signup: type a product in plain words (achar, haldi, bedsheet) or part of a code and get the 8-digit HSN code, its 6-digit international code, heading and chapter, the GST invoice digit rule, India's exports of that code (UN Comtrade), ODOP districts that make it, and links to the Supplier Finder, Export Buyer Finder, uktradeinfo and Budget Matcher. Also a crawlable table of ODOP products and their HSN headings. GST rates are not included (no checked rate table after the September 2025 changes); the page links to CBIC's rate page instead. `build.py` calls `hsn_finder.py` after the Supplier Finder and Export Buyer Finder, whose published data files it reuses. Deep links: `?hsn=09103010` or `?q=achar`.

## Expo Finder tool (`/tools/expo-finder/`)

Free tool: the user picks their city, product and goal (sell to visitors, find dealers, meet export buyers, find suppliers), leaves an email, and gets a report of the trade fairs and expos worth a stall: live events in their city, the big recurring fairs that fit with venue, usual month and who visits, nearby venues, stall subsidies, a budget and break-even calculator, AI prompts and a checklist. `build.py` calls `expo_finder.py`. Details in `tools_src/expo-finder/README.md`.

---

## Folder structure

```
kidharmilega/
├── find_urls.py          ← Source discovery script
├── enrich.py             ← AI enrichment pipeline
├── build.py              ← Static site generator
├── data/
│   ├── odop_urls.csv         ← Source map (7 cols: state, district, url, status, youtube_ids, pdf_urls, google_urls)
│   ├── scraped_facts.json    ← Stage 1 cache — raw extracted facts per district
│   ├── enrichment_cache.json ← Stage 2 cache — AI-generated content per district
│   ├── districts.csv         ← Final merged output read by build.py
│   ├── enrichment_report.csv ← Per-run quality report
│   └── context/              ← Prompt guides, SOP, master template
└── docs/                 ← Generated site (deployed via GitHub Pages)
    ├── index.html
    ├── assets/style.css
    ├── products/
    ├── events/
    └── vendors/
```

---

## Setup

### Requirements

```bash
pip install anthropic python-dotenv ddgs youtube-transcript-api pdfplumber google-api-python-client
```

### Environment variables

Create a `.env` file:

```
ANTHROPIC_API_KEY=sk-ant-...     # required — Claude API
YOUTUBE_API_KEY=AIza...          # optional — YouTube Data API v3
GOOGLE_SEARCH_CX=...             # optional — Google Custom Search (falls back to DuckDuckGo)
```

### First run

```bash
# 1. Discover all sources (one-time, ~45 min total)
python3 find_urls.py
python3 find_urls.py --google
python3 find_urls.py --youtube

# 2. Enrich in batches (repeat until "To process: 0")
python3 enrich.py --limit 100

# 3. Build and deploy
python3 build.py
git add docs/ data/ && git commit -m "Initial enrich" && git push
```

### Incremental updates

```bash
python3 enrich.py --limit 50   # enrich any new/stale districts
python3 build.py
git add docs/ data/ && git commit -m "Enrich update" && git push
```

---

## Deploy

GitHub Pages serves from the `docs/` folder on the `main` branch.

- Settings → Pages → Branch: `main` → Folder: `/docs`
- Custom domain: add `kidharmilega.in` in Pages settings, set `BASE_PATH = ''` in `build.py`

---

## Community

- Instagram: [@startupwalebhaia](https://instagram.com/startupwalebhaia)
- Facebook group: [Kidharmilega Community](https://www.facebook.com/groups/startupwalebhaia)
- Full pipeline docs: `data/context/operating-sop.md`
