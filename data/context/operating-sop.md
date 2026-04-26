# KidharMilega — Operating SOP 5.0

## Overview

Three scripts run in sequence. Each script feeds the next.

```
find_urls.py  →  enrich.py  →  build.py  →  GitHub Pages (docs/)
```

| File | Role |
|------|------|
| `data/odop_urls.csv` | Source discovery — one row per district, 7 columns |
| `data/scraped_facts.json` | Stage 1 output — extracted facts from all combined sources |
| `data/enrichment_cache.json` | Stage 2 output — AI-generated 60+ field content per district |
| `data/districts.csv` | Final merged CSV read by `build.py` |
| `data/enrichment_report.csv` | Per-run quality report |
| `docs/` | Output HTML pages (deployed via GitHub Pages) |

---

## Stage 1 — Source Discovery (`find_urls.py`)

Populates `data/odop_urls.csv` with 7 columns:

```
state, district, url, status, youtube_ids, pdf_urls, google_urls
```

**Run this once before enrichment, and again whenever you want fresher source data.**
`enrich.py` reads everything from this CSV — it does not do its own URL discovery.

### Status values
| Status | Meaning |
|--------|---------|
| `MATCH` | URL has `/one-district-one-product/` path and returned 200 |
| `BASE` | Only the district homepage was reachable |
| `FAILED` | No working govt URL found |

Current counts: **166 MATCH · 480 BASE · 141 FAILED** (total 787)

---

### Layer 1 — Verified ODOP URLs

71 URLs are manually verified and hardcoded in `VERIFIED_URLS` inside `find_urls.py`. These are checked first. **No automated run can overwrite them.**

For the remaining districts, the script probes URL patterns like `{district}.{state-code}.gov.in/one-district-one-product/`.

```bash
python3 find_urls.py              # probe districts with no status
python3 find_urls.py --all        # re-probe everything (verified URLs still protected)
python3 find_urls.py --failed     # retry only FAILED rows
```

---

### Layer 2 — Google / DuckDuckGo Research URLs

Finds business research pages for every district: PIB press releases, IBEF reports, trade publications, case studies. Results stored in `google_urls` column (pipe-separated, up to 5 URLs per district).

Priority domains ranked first: `pib.gov.in`, `ibef.org`, `msme.gov.in`, `odopup.in`, `fibre2fashion.com`, `apparelresources.com`, `dc-msme.gov.in`

Noise domains filtered out: YouTube, Facebook, IndiaMART, Flipkart, Amazon, travel sites.

Uses Google Custom Search API if `GOOGLE_SEARCH_CX` is in `.env`, else falls back to DuckDuckGo (`ddgs` library — no key needed).

```bash
python3 find_urls.py --google                           # all districts
python3 find_urls.py --google --filter "Varanasi,Agra"  # specific districts
```

---

### Layer 3 — YouTube Video IDs

YouTube Data API v3 searches for relevant videos per district. Stored in `youtube_ids` column (comma-separated). **`enrich.py` fetches transcripts for these on every scrape run — not just as a fallback.**

```bash
python3 find_urls.py --youtube                    # all districts
python3 find_urls.py --fallbacks                  # Layer 2 + Layer 3 together
python3 find_urls.py --fallbacks --filter "Agra"  # specific district
```

---

### Full source discovery run

```bash
python3 find_urls.py            # Layer 1: probe all URLs (~10 min)
python3 find_urls.py --google   # Layer 2: find research pages (~15 min)
python3 find_urls.py --youtube  # Layer 3: find YouTube videos (~20 min)
```

---

## Stage 2 — Enrichment (`enrich.py`)

Reads `odop_urls.csv` + Google Sheet, scrapes **all available sources simultaneously**, and generates 60+ content fields per district using Claude (Haiku).

### How the cache works (important)

`enrich.py` maintains two separate caches:

- **`scraped_facts.json`** — extracted facts from the combined multi-source scrape. Preserved across runs unless `--force-scrape`.
- **`enrichment_cache.json`** — AI-generated content from Stage 2. Preserved across runs unless `--all`. Each entry stores `_scraped_quality` to track what source quality was used at generation time.

**A district is queued for processing if any of these are true:**
1. Never been enriched (`key not in cache`)
2. Has been enriched but was never actually scraped (`key not in scraped_facts`)
3. Was scraped since last generation run (`_scraped_quality` is blank in cache but scraped_facts now has real data)
4. `--refresh`: missing new content fields
5. `--force-scrape` or `--all`: forced

**Stage 2 protects existing cache:** if scraping still returns empty AND the district already has cached AI content, the existing content is kept. Nothing gets overwritten with content generated from zero facts.

---

### The aggregate scraping model

For every district, `enrich.py` always collects from **all four sources simultaneously** — it never stops early:

```
P1  Official govt ODOP page          (url from odop_urls.csv / GOVT_ODOP_URLS)
P2  Google research URLs             (google_urls column in odop_urls.csv)
P3  Pre-fetched PDFs                 (pdf_urls column in odop_urls.csv)
P4  YouTube video transcripts        (youtube_ids column in odop_urls.csv)
         ↓
    All raw text combined into one labelled research document
         ↓
    Single Stage 1 extraction call → scraped_facts.json
         ↓
    Stage 2 generation call → enrichment_cache.json
```

**Why aggregate instead of fallback:** A govt page might have artisan counts but no export data. An IBEF article might have export figures but no cluster names. A YouTube transcript might have both. The combined document gives Claude full visibility across all sources in one extraction pass — richer, more accurate facts.

The print line per district shows what each layer returned:

```
[gov:ok] [g:ok] [g:miss] [pdf:miss] [yt:2ok]  → [quality:good]
```

`[gov:ok]` = govt page fetched successfully  
`[g:ok]` / `[g:miss]` = Google URL fetched or empty  
`[pdf:ok]` / `[pdf:miss]` = PDF fetched or unavailable  
`[yt:2ok]` = 2 YouTube transcripts fetched  
`→ [quality:good]` = combined extraction quality

Page quality ratings: `good` (production numbers + artisans + 3+ facts) · `partial` (some numbers) · `empty` (no data found in any source).

**Claude Haiku runs twice per district:**
- **Stage 1 (extraction):** reads the combined multi-source text, returns only explicitly stated facts — no inference, empty string if not found in any source
- **Stage 2 (generation):** uses those verified facts as grounding, generates all 60+ content fields

**Note:** P3 and P4 only use URLs/IDs already stored in `odop_urls.csv`. `enrich.py` does not do live PDF searches or YouTube API searches — that's `find_urls.py`'s job. If those columns are empty, those layers are silently skipped.

---

### Common runs

```bash
# Resume — processes only districts that need work
python3 enrich.py

# Batch — process at most 50 at a time
python3 enrich.py --limit 50

# MATCH districts first (166 verified ODOP pages — highest quality data)
python3 enrich.py --match-only

# Re-scrape + re-enrich specific districts from scratch
python3 enrich.py --filter "Varanasi" --force-scrape

# Re-scrape + re-enrich all MATCH districts from scratch
python3 enrich.py --match-only --force-scrape

# Backfill: re-enrich districts missing newer fields
python3 enrich.py --refresh

# Only run the scraping stage (no AI generation) — pre-populates scraped_facts
python3 enrich.py --scrape-only

# Re-enrich everything from scratch — wipes both caches (slow — 787 × 2 Claude calls)
python3 enrich.py --all
```

---

### Fields generated

| Group | Fields |
|-------|--------|
| Identity | `district_name_hin`, `city_tier`, `famous_for_1_line`, `odop_gi_tag`, `gi_tag_year` |
| Economics | `min_setup_cost`, `max_setup_cost`, `gross_margin_wholesale`, `gross_margin_d2c`, `breakeven_timeline`, `export_margin` |
| Opportunity | `opportunity_score` (1–10), `alert_stat` (striking stat), `geo_anchor` (3-sentence AI-indexed paragraph) |
| Steps | `step_1_learn` through `step_6_scale` (Step 1 always free) |
| Revenue | `revenue_stream_1` through `revenue_stream_5` |
| Schemes | `relevant_central_scheme_1/2`, `relevant_state_scheme_1/2` |
| Success story | `success_story_name/desc/cost/subsidy/employees/source` |
| FAQs | `faq_1` through `faq_6` (format: `Question|||Answer`) |
| Clusters | `industrial_park_1/2/3`, `cluster_2/3` |
| Logistics | `logistics_info` (pipe-separated: Airport/Road/Rail/Seaport/Power) |
| Internal | `_scraped_quality`, `_scraped_source` (used for cache staleness detection) |

---

## Stage 3 — Build (`build.py`)

Reads `data/districts.csv`, generates one HTML file per district into `docs/`.

```bash
python3 build.py           # production build (BASE_PATH = /kidharmilega)
python3 build.py --local   # local preview build (BASE_PATH = '')
```

For local preview, serve with:
```bash
cd docs && python3 -m http.server 8080
# open http://localhost:8080
```

Push to deploy:
```bash
git add docs/ data/districts.csv data/enrichment_cache.json data/odop_urls.csv
git commit -m "Enrich: describe what changed"
git push
```

---

## Recommended Workflows

### Full pipeline from scratch

```bash
# 1. Discover all sources (run once, or when refreshing source data)
python3 find_urls.py
python3 find_urls.py --google
python3 find_urls.py --youtube

# 2. Enrich in batches (each run processes new/stale districts using all available sources)
python3 enrich.py --limit 100
python3 enrich.py --limit 100   # repeat until "To process: 0"

# 3. Build and ship
python3 build.py && git add docs/ data/ && git commit -m "Full enrich" && git push
```

### Daily / incremental run

```bash
python3 enrich.py --limit 50   # new or stale districts only, all 4 sources per district
python3 build.py
```

### Re-enrich specific districts after fixing a source URL

```bash
python3 enrich.py --filter "DistrictName" --force-scrape
python3 build.py
```

### Refresh source data before a re-enrich run

```bash
python3 find_urls.py --google --filter "Varanasi,Lucknow"   # refresh Google URLs
python3 find_urls.py --youtube --filter "Varanasi,Lucknow"  # refresh YouTube IDs
python3 enrich.py --filter "Varanasi,Lucknow" --force-scrape
python3 build.py
```

### Adding a new verified ODOP URL

1. Add to `VERIFIED_URLS` in `find_urls.py` (key: `"state_district"` lowercase)
2. Add to `GOVT_ODOP_URLS` in `enrich.py` (same format)
3. `python3 find_urls.py --filter "DistrictName"` — updates CSV
4. `python3 enrich.py --filter "DistrictName" --force-scrape` — re-enriches with new URL

### Adding a new content field

1. Add field name to `CSV_COLUMNS` in `enrich.py`
2. Add field to the Stage 2 JSON prompt in `enrich.py`
3. Add field to `_REFRESH_FIELDS` (so `--refresh` backfills it)
4. Add rendering to `master-template.md` + `build.py`
5. `python3 enrich.py --refresh`

---

## Environment Variables (`.env`)

```
ANTHROPIC_API_KEY=sk-ant-...     # Claude API — required
YOUTUBE_API_KEY=AIza...          # YouTube Data API v3 (same Google Cloud project)
GOOGLE_SEARCH_CX=...             # Custom Search Engine ID (optional — falls back to DuckDuckGo)
```

---

## Architecture Rules

1. **Hardcoded URLs always win.** `VERIFIED_URLS` (find_urls.py) and `GOVT_ODOP_URLS` (enrich.py) override any auto-discovered or CSV-stored URLs. Edit the dicts — never the CSV — to change a verified URL.

2. **`find_urls.py` discovers, `enrich.py` enriches.** `enrich.py` never does live URL search, PDF search, or YouTube API calls. It only uses what is already in `odop_urls.csv`. Run `find_urls.py` to refresh sources, then run `enrich.py --force-scrape` to re-enrich with the updated sources.

3. **All sources are always tried.** `enrich.py` no longer stops at the first source that returns data. It fetches from all four layers (govt page + Google URLs + PDFs + YouTube) and combines them before running extraction. Better data in any single source improves the final output.

4. **Two separate caches, two separate triggers.** `scraped_facts.json` (Stage 1) and `enrichment_cache.json` (Stage 2) are independent. `--force-scrape` only resets Stage 1. `--all` resets both. The `_scraped_quality` field in the cache entry links them — if a district was cached without real facts, a normal run will detect and regenerate it once real facts arrive.

5. **Never overwrite cache with empty facts.** If all sources return nothing AND the district already has cached AI content, the existing cache entry is kept. Use `--force-scrape` to explicitly wipe and redo.

6. **FAQ format is `Question|||Answer`.** The `|||` separator is parsed by `build.py` to split Q and A in the rendered HTML. Never change this separator.
