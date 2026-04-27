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
