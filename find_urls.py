#!/usr/bin/env python3
"""
find_urls.py — Three-layer source discovery for KidharMilega district pages.

Columns in data/odop_urls.csv:
  state, district, url, status, youtube_ids, pdf_urls, google_urls

Layers:
  Layer 1 — Verified ODOP URLs (hardcoded from official sources, never overwritten)
  Layer 2 — Google Search for business research pages (production, export, case studies)
  Layer 3 — YouTube video IDs for transcript extraction in enrich.py

Status values:
  MATCH   — /one-district-one-product/ path found and returned 200
  BASE    — only district homepage reachable
  FAILED  — no working govt URL found

Usage:
  python3 find_urls.py                        # probe unclassified districts (Layer 1)
  python3 find_urls.py --all                  # re-probe everything
  python3 find_urls.py --failed               # retry only FAILED rows
  python3 find_urls.py --google               # Layer 2: Google research URLs
  python3 find_urls.py --youtube              # Layer 3: YouTube video IDs
  python3 find_urls.py --fallbacks            # Layer 2 + 3 together
  python3 find_urls.py --filter "Tiruppur,Lucknow"         # specific districts
  python3 find_urls.py --google --filter "Varanasi,Agra"   # combine flags

Env vars (.env):
  YOUTUBE_API_KEY      — YouTube Data API v3 key
  GOOGLE_SEARCH_CX     — Custom Search Engine ID (programmablesearchengine.google.com)
                         If not set, falls back to googlesearch-python scraping
"""

import csv
import os
import re
import sys
import time
from pathlib import Path

import cloudscraper

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Layer 1: Verified ODOP URLs ────────────────────────────────────────────────
# These are manually confirmed. probe_district() returns these immediately
# without HTTP probing, and --all can never overwrite them.
VERIFIED_URLS = {
    # Andhra Pradesh
    "andhra pradesh_anantapuramu":              "https://ananthapuramu.ap.gov.in/one-district-one-product/",
    "andhra pradesh_anantapuram (anantapur)":   "https://ananthapuramu.ap.gov.in/one-district-one-product/",
    "andhra pradesh_ananthpuram (anantapur)":   "https://ananthapuramu.ap.gov.in/one-district-one-product/",
    "andhra pradesh_chittoor":                  "https://chittoor.ap.gov.in/one-district-one-product/",
    "andhra pradesh_east godavari":             "https://eastgodavari.ap.gov.in/one-district-one-product/",
    "andhra pradesh_east godavari district":    "https://eastgodavari.ap.gov.in/one-district-one-product/",
    "andhra pradesh_guntur":                    "https://guntur.ap.gov.in/one-district-one-product/",
    "andhra pradesh_kakinada":                  "https://kakinada.ap.gov.in/one-district-one-product/",
    "andhra pradesh_krishna":                   "https://krishna.ap.gov.in/one-district-one-product/",
    "andhra pradesh_kurnool":                   "https://kurnool.ap.gov.in/one-district-one-product/",
    "andhra pradesh_prakasam":                  "https://prakasam.ap.gov.in/one-district-one-product/",
    "andhra pradesh_srikakulam":                "https://srikakulam.ap.gov.in/one-district-one-product/",
    "andhra pradesh_visakhapatnam":             "https://visakhapatnam.ap.gov.in/one-district-one-product/",
    "andhra pradesh_west godavari":             "https://westgodavari.ap.gov.in/one-district-one-product/",
    "andhra pradesh_west godavari district":    "https://westgodavari.ap.gov.in/one-district-one-product/",
    "andhra pradesh_ysr kadapa":                "https://kadapa.ap.gov.in/one-district-one-product/",
    # Bihar
    "bihar_banka":                              "https://banka.bihar.gov.in/one-district-one-product/",
    "bihar_bhagalpur":                          "https://bhagalpur.bihar.gov.in/one-district-one-product/",
    "bihar_darbhanga":                          "https://darbhanga.bihar.gov.in/one-district-one-product/",
    "bihar_gaya":                               "https://gaya.bihar.gov.in/one-district-one-product/",
    "bihar_katihar":                            "https://katihar.bihar.gov.in/one-district-one-product/",
    "bihar_muzaffarpur":                        "https://muzaffarpur.bihar.gov.in/one-district-one-product/",
    "bihar_patna":                              "https://patna.bihar.gov.in/one-district-one-product/",
    # Chhattisgarh
    "chhattisgarh_bastar":                      "https://bastar.cg.gov.in/one-district-one-product/",
    "chhattisgarh_bilaspur":                    "https://bilaspur.cg.gov.in/one-district-one-product/",
    "chhattisgarh_raigarh":                     "https://raigarh.cg.gov.in/one-district-one-product/",
    # Gujarat
    "gujarat_ahmedabad":                        "https://ahmedabad.gujarat.gov.in/one-district-one-product/",
    "gujarat_anand":                            "https://anand.gujarat.gov.in/one-district-one-product/",
    "gujarat_bhavnagar":                        "https://bhavnagar.gujarat.gov.in/one-district-one-product/",
    "gujarat_kachchh":                          "https://kachchh.gujarat.gov.in/one-district-one-product/",
    "gujarat_rajkot":                           "https://rajkot.gujarat.gov.in/one-district-one-product/",
    "gujarat_surat":                            "https://surat.gujarat.gov.in/one-district-one-product/",
    # Haryana
    "haryana_faridabad":                        "https://faridabad.haryana.gov.in/one-district-one-product/",
    "haryana_gurugram":                         "https://gurugram.haryana.gov.in/one-district-one-product/",
    "haryana_karnal":                           "https://karnal.haryana.gov.in/one-district-one-product/",
    "haryana_panipat":                          "https://panipat.haryana.gov.in/one-district-one-product/",
    # Karnataka
    "karnataka_bengaluru urban":                "https://bengaluruurban.karnataka.gov.in/one-district-one-product/",
    "karnataka_chikkamagaluru":                 "https://chikkamagaluru.karnataka.gov.in/one-district-one-product/",
    "karnataka_mysuru":                         "https://mysuru.karnataka.gov.in/one-district-one-product/",
    "karnataka_mysuru (mysore)":               "https://mysuru.karnataka.gov.in/one-district-one-product/",
    "karnataka_udupi":                          "https://udupi.karnataka.gov.in/one-district-one-product/",
    # Kerala
    "kerala_kozhikode":                         "https://kozhikode.kerala.gov.in/one-district-one-product/",
    "kerala_palakkad":                          "https://palakkad.kerala.gov.in/one-district-one-product/",
    "kerala_wayanad":                           "https://wayanad.kerala.gov.in/one-district-one-product/",
    # Madhya Pradesh
    "madhya pradesh_bhopal":                    "https://bhopal.mp.gov.in/one-district-one-product/",
    "madhya pradesh_indore":                    "https://indore.mp.gov.in/one-district-one-product/",
    "madhya pradesh_ratlam":                    "https://ratlam.mp.gov.in/one-district-one-product/",
    "madhya pradesh_ujjain":                    "https://ujjain.mp.gov.in/one-district-one-product/",
    # Maharashtra
    "maharashtra_aurangabad":                   "https://aurangabad.maharashtra.gov.in/one-district-one-product/",
    "maharashtra_kolhapur":                     "https://kolhapur.maharashtra.gov.in/one-district-one-product/",
    "maharashtra_nagpur":                       "https://nagpur.maharashtra.gov.in/one-district-one-product/",
    "maharashtra_nashik":                       "https://nashik.maharashtra.gov.in/one-district-one-product/",
    "maharashtra_pune":                         "https://pune.maharashtra.gov.in/one-district-one-product/",
    # Odisha
    "odisha_cuttack":                           "https://cuttack.odisha.gov.in/one-district-one-product/",
    "odisha_khurda":                            "https://khordha.odisha.gov.in/one-district-one-product/",
    "odisha_khordha":                           "https://khordha.odisha.gov.in/one-district-one-product/",
    "odisha_puri":                              "https://puri.odisha.gov.in/one-district-one-product/",
    # Punjab
    "punjab_amritsar":                          "https://amritsar.punjab.gov.in/one-district-one-product/",
    "punjab_jalandhar":                         "https://jalandhar.punjab.gov.in/one-district-one-product/",
    "punjab_ludhiana":                          "https://ludhiana.punjab.gov.in/one-district-one-product/",
    # Rajasthan
    "rajasthan_bikaner":                        "https://bikaner.rajasthan.gov.in/one-district-one-product/",
    "rajasthan_jaipur":                         "https://jaipur.rajasthan.gov.in/one-district-one-product/",
    "rajasthan_jodhpur":                        "https://jodhpur.rajasthan.gov.in/one-district-one-product/",
    # Tamil Nadu
    "tamil nadu_chennai":                       "https://chennai.tn.gov.in/one-district-one-product/",
    "tamil nadu_coimbatore":                    "https://coimbatore.tn.gov.in/one-district-one-product/",
    "tamil nadu_kancheepuram":                  "https://kancheepuram.tn.gov.in/one-district-one-product/",
    "tamil nadu_tiruppur":                      "https://tiruppur.tn.gov.in/one-district-one-product/",
    # Telangana
    "telangana_hyderabad":                      "https://hyderabad.telangana.gov.in/one-district-one-product/",
    "telangana_karimnagar":                     "https://karimnagar.telangana.gov.in/one-district-one-product/",
    "telangana_warangal":                       "https://warangal.telangana.gov.in/one-district-one-product/",
    "telangana_warangal rural":                 "https://warangal.telangana.gov.in/one-district-one-product/",
    "telangana_warangal urban (hanumakonda)":   "https://warangal.telangana.gov.in/one-district-one-product/",
    # Uttar Pradesh
    "uttar pradesh_agra":                       "https://agra.up.gov.in/one-district-one-product/",
    "uttar pradesh_aligarh":                    "https://aligarh.up.gov.in/one-district-one-product/",
    "uttar pradesh_lucknow":                    "https://lucknow.up.gov.in/one-district-one-product/",
    "uttar pradesh_varanasi":                   "https://varanasi.up.gov.in/one-district-one-product/",
    # West Bengal
    "west bengal_darjeeling":                   "https://darjeeling.wb.gov.in/one-district-one-product/",
    "west bengal_hooghly":                      "https://hooghly.wb.gov.in/one-district-one-product/",
    "west bengal_murshidabad":                  "https://murshidabad.wb.gov.in/one-district-one-product/",
}

STATE_CODES = {
    "andhra pradesh": "ap",    "arunachal pradesh": "arunachal", "assam": "assam",
    "bihar": "bihar",           "chhattisgarh": "cg",             "goa": "goa",
    "gujarat": "gujarat",       "haryana": "haryana",             "himachal pradesh": "hp",
    "jharkhand": "jharkhand",   "karnataka": "karnataka",         "kerala": "kerala",
    "madhya pradesh": "mp",     "maharashtra": "maharashtra",     "manipur": "manipur",
    "meghalaya": "meghalaya",   "mizoram": "mizoram",             "nagaland": "nagaland",
    "odisha": "odisha",         "punjab": "punjab",               "rajasthan": "rajasthan",
    "sikkim": "sikkim",         "tamil nadu": "tn",               "telangana": "telangana",
    "tripura": "tripura",       "uttar pradesh": "up",            "uttarakhand": "uk",
    "west bengal": "wb",        "jammu & kashmir": "jk",          "ladakh": "ladakh",
    "delhi": "delhi",           "puducherry": "py",
}

INPUT_CSV  = Path("data/districts.csv")
OUTPUT_CSV = Path("data/odop_urls.csv")

FIELDNAMES = ["state", "district", "url", "status", "youtube_ids", "pdf_urls", "google_urls"]


# ── Slug helpers ───────────────────────────────────────────────────────────────

def slugify(text):
    return text.lower().replace(" ", "").replace("-", "").strip()


def clean_for_domain(name):
    """Strip parentheticals and honorifics before building a URL slug."""
    name = re.sub(r"\s*\(.*?\)", "", name)
    name = re.sub(r"^dr\.?\s+", "", name.strip(), flags=re.IGNORECASE)
    name = re.sub(r"[^a-zA-Z0-9\s]", "", name)
    return name.strip()


# ── Layer 1: URL probing ───────────────────────────────────────────────────────

def probe_district(scraper, state, district_raw, url_slug):
    """Return (url, status). Checks VERIFIED_URLS first — never probes HTTP for those."""
    vkey = f"{state.lower()}_{district_raw.lower()}"
    if vkey in VERIFIED_URLS:
        return VERIFIED_URLS[vkey], "MATCH"

    state_code = STATE_CODES.get(state.lower(), "")
    clean_name = clean_for_domain(district_raw)
    d_slug     = url_slug.replace("-", "") if url_slug else slugify(clean_name)

    candidates = []
    if state_code:
        candidates += [
            f"https://{d_slug}.{state_code}.gov.in/one-district-one-product/",
            f"https://{d_slug}.nic.in/one-district-one-product/",
            f"https://{d_slug}.{state_code}.gov.in",
            f"https://{d_slug}.nic.in",
        ]
    candidates += [
        f"https://{d_slug}.gov.in/one-district-one-product/",
        f"https://{d_slug}.gov.in",
    ]

    for url in candidates:
        try:
            r = scraper.get(url, timeout=10)
            if r.status_code == 200:
                status = "MATCH" if "/one-district-one-product" in url else "BASE"
                return url, status
        except Exception:
            pass

    return "", "FAILED"


def load_products():
    """Load {state_district: product_name} from districts.csv (enrich.py output)."""
    products = {}
    if INPUT_CSV.exists():
        try:
            for row in csv.DictReader(open(INPUT_CSV, encoding="utf-8")):
                s = row.get("state", "").strip().lower()
                d = row.get("district_name", "").strip().lower()
                p = row.get("odop_product_name", "").strip()
                if s and d and p:
                    products[f"{s}_{d}"] = p
        except Exception:
            pass
    return products


# ── Layer 2: Google research URLs ─────────────────────────────────────────────

# Prefer these high-signal domains when ranking Google results
PRIORITY_DOMAINS = {
    "pib.gov.in", "ibef.org", "msme.gov.in", "dc-msme.gov.in",
    "mofpi.gov.in", "fibre2fashion.com", "indiastat.com",
    "economictimes.indiatimes.com", "business-standard.com",
    "thehindu.com", "indianretailer.com", "exportimportdata.in",
    "apeda.gov.in", "craftcouncil.in", "vikaspedia.in",
}

# Skip these low-signal domains
SKIP_DOMAINS = {
    "youtube.com", "facebook.com", "instagram.com", "twitter.com",
    "wikipedia.org", "justdial.com", "indiamart.com", "amazon.in",
    "flipkart.com", "maps.google.com", "tripadvisor.com",
}


def _domain(url):
    m = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1).lower() if m else ""


def _rank_urls(urls):
    """Sort: priority domains first, then others, skip noise."""
    priority, others = [], []
    for url in urls:
        d = _domain(url)
        if any(skip in d for skip in SKIP_DOMAINS):
            continue
        if any(prio in d for prio in PRIORITY_DOMAINS):
            priority.append(url)
        else:
            others.append(url)
    return priority + others


def search_google_api(district, product, state, api_key, cx, max_results=5):
    """Google Custom Search API. Requires GOOGLE_SEARCH_CX in .env."""
    try:
        from googleapiclient.discovery import build as g_build
        svc = g_build("customsearch", "v1", developerKey=api_key)
    except Exception:
        return []

    queries = [
        f'"{product}" "{district}" production market size annual',
        f'"{product}" India export margin "crore" OR "lakh" OR "USD"',
        f'ODOP "{district}" "{product}" case study OR report',
    ]
    found = []
    for q in queries:
        try:
            res = svc.cse().list(q=q, cx=cx, num=min(max_results, 10)).execute()
            for item in res.get("items", []):
                url = item.get("link", "")
                if url and url not in found:
                    found.append(url)
            if len(found) >= max_results:
                break
        except Exception:
            pass
        time.sleep(0.5)
    return _rank_urls(found)[:max_results]


def search_ddgs(district, product, state, max_results=5):
    """DuckDuckGo search via ddgs library (no API key needed)."""
    try:
        from ddgs import DDGS
    except ImportError:
        return []

    queries = [
        f"{product} {district} production scale annual market crore",
        f"{product} India export business startup margin guide",
        f"ODOP {district} {product} India case study report",
    ]
    found = []
    try:
        with DDGS() as ddgs:
            for q in queries:
                try:
                    results = list(ddgs.text(q, max_results=max_results))
                    for r in results:
                        url = r.get("href", "")
                        if url and url not in found:
                            found.append(url)
                    if len(found) >= max_results:
                        break
                except Exception:
                    pass
                time.sleep(1)
    except Exception:
        pass
    return _rank_urls(found)[:max_results]


def search_google_urls(district, product, state):
    """Layer 2: find business research URLs. Uses Custom Search API if configured, else ddgs."""
    api_key = os.environ.get("YOUTUBE_API_KEY", "")  # same Google Cloud key
    cx      = os.environ.get("GOOGLE_SEARCH_CX", "")

    if api_key and cx:
        results = search_google_api(district, product, state, api_key, cx)
    else:
        results = search_ddgs(district, product, state)

    return "|".join(results)


# ── Layer 3: YouTube video IDs ─────────────────────────────────────────────────

def search_youtube_ids(district, product, api_key, max_results=5):
    """YouTube Data API v3 search. Returns comma-separated video IDs or ''."""
    try:
        from googleapiclient.discovery import build as yt_build
        yt = yt_build("youtube", "v3", developerKey=api_key)
    except Exception:
        return ""

    queries = [
        f"{product} {district} business manufacturing",
        f"ODOP {product} {district} India",
        f"{product} {district} export startup Hindi",
    ]
    ids = []
    for q in queries:
        try:
            res = yt.search().list(
                q=q, part="id", type="video",
                maxResults=max_results, relevanceLanguage="hi"
            ).execute()
            for item in res.get("items", []):
                vid = item["id"].get("videoId", "")
                if vid and vid not in ids:
                    ids.append(vid)
        except Exception:
            pass
        if len(ids) >= 5:
            break
    return ",".join(ids[:5])


# ── Layer 2b: PDF search (subset of Google) ───────────────────────────────────

def search_pdf_urls(district, product, state, max_results=3):
    """Search for MoFPI/PMFME handbooks specifically. Returns pipe-separated URLs."""
    queries = [
        f"mofpi.gov.in {product} {district} PDF",
        f"PMFME handbook {product} {district} {state} pdf",
        f"dc-msme.gov.in {product} {district}",
    ]
    found = []
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            for q in queries:
                try:
                    results = list(ddgs.text(q, max_results=max_results))
                    for r in results:
                        url = r.get("href", "")
                        if url and url not in found and (".pdf" in url.lower() or "mofpi" in url or "msme" in url):
                            found.append(url)
                    if found:
                        break
                except Exception:
                    pass
                time.sleep(1)
    except ImportError:
        pass
    return "|".join(found[:max_results])


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    args       = sys.argv[1:]
    force_all  = "--all"       in args
    retry_fail = "--failed"    in args
    do_google  = "--google"    in args or "--fallbacks" in args
    do_youtube = "--youtube"   in args or "--fallbacks" in args
    filter_set = set()
    for i, a in enumerate(args):
        if a == "--filter" and i + 1 < len(args):
            filter_set = {s.strip().lower() for s in args[i + 1].split(",")}

    # Load existing CSV — preserves all columns already discovered
    existing = {}
    if OUTPUT_CSV.exists():
        for row in csv.DictReader(open(OUTPUT_CSV, encoding="utf-8")):
            key = f"{row['state'].lower()}_{row['district'].lower()}"
            existing[key] = row

    districts = list(csv.DictReader(open(INPUT_CSV, encoding="utf-8-sig")))
    print(f"📂 {len(districts)} districts loaded")

    products   = load_products()
    yt_api_key = os.environ.get("YOUTUBE_API_KEY", "")
    results    = dict(existing)
    processed  = 0

    run_probe = not (do_google or do_youtube) or force_all

    # ── Layer 1: URL probing ───────────────────────────────────────────────────
    if run_probe:
        print("\n── Layer 1: Probing official ODOP URLs ──")
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "desktop": True}
        )
        for row in districts:
            state        = row.get("state", "").strip()
            district_raw = row.get("district_name", "").strip()
            url_slug     = row.get("url_slug", "").strip()
            if not state or not district_raw:
                continue
            if filter_set and district_raw.lower() not in filter_set:
                continue

            key  = f"{state.lower()}_{district_raw.lower()}"
            vkey = key  # same format as VERIFIED_URLS

            # Skip if already classified, unless --all or --failed
            if key in existing and not force_all:
                if retry_fail and existing[key].get("status") == "FAILED":
                    pass
                elif vkey in VERIFIED_URLS:
                    # Always apply verified URL even if already classified
                    pass
                else:
                    continue

            # Verified? No HTTP needed
            if vkey in VERIFIED_URLS:
                url, status = VERIFIED_URLS[vkey], "MATCH"
                print(f"  ✅ VERIFIED  {district_raw}, {state}")
            else:
                print(f"  Probing {district_raw}, {state}...", end=" ", flush=True)
                url, status = probe_district(scraper, state, district_raw, url_slug)
                tag = "✅ MATCH" if status == "MATCH" else ("⚠️  BASE" if status == "BASE" else "❌ FAILED")
                print(f"{tag}  {url or '—'}", end="", flush=True)

                # FAILED → immediate PDF + YouTube inline
                if status == "FAILED":
                    product = products.get(key) or district_raw
                    print("  → PDF...", end=" ", flush=True)
                    pdf_str = search_pdf_urls(district_raw, product, state)
                    yt_ids  = ""
                    if yt_api_key:
                        print("YT...", end=" ", flush=True)
                        yt_ids = search_youtube_ids(district_raw, product, yt_api_key)
                    pc = len([u for u in pdf_str.split("|") if u]) if pdf_str else 0
                    yc = len([v for v in yt_ids.split(",") if v]) if yt_ids else 0
                    print(f"[pdf:{pc} yt:{yc}]", end="")
                else:
                    pdf_str = existing.get(key, {}).get("pdf_urls", "")
                    yt_ids  = existing.get(key, {}).get("youtube_ids", "")

                print()

            results[key] = {
                "state":       state,
                "district":    district_raw,
                "url":         url,
                "status":      status,
                "youtube_ids": existing.get(key, {}).get("youtube_ids", "") if vkey in VERIFIED_URLS else yt_ids,
                "pdf_urls":    existing.get(key, {}).get("pdf_urls", "")    if vkey in VERIFIED_URLS else pdf_str,
                "google_urls": existing.get(key, {}).get("google_urls", ""),
            }
            processed += 1
            time.sleep(1.5)

    # ── Layer 2: Google research URLs ─────────────────────────────────────────
    if do_google:
        cx = os.environ.get("GOOGLE_SEARCH_CX", "")
        mode = "Custom Search API" if (yt_api_key and cx) else "DuckDuckGo (ddgs)"
        print(f"\n── Layer 2: Google research URLs ({mode}) ──")
        if not cx:
            print("  ℹ️  GOOGLE_SEARCH_CX not set — add to .env for Custom Search API")

        for row in districts:
            state        = row.get("state", "").strip()
            district_raw = row.get("district_name", "").strip()
            if not state or not district_raw:
                continue
            if filter_set and district_raw.lower() not in filter_set:
                continue

            key   = f"{state.lower()}_{district_raw.lower()}"
            entry = results.get(key, existing.get(key, {}))

            # Skip if already has google_urls (use --all to re-fetch)
            if not force_all and entry.get("google_urls"):
                continue

            product = products.get(key) or district_raw
            print(f"  Searching: {district_raw}, {state} — {product}...", end=" ", flush=True)

            google_str = search_google_urls(district_raw, product, state)
            gc = len([u for u in google_str.split("|") if u]) if google_str else 0
            print(f"[{gc} URLs found]")

            entry_copy = dict(entry)
            entry_copy["google_urls"] = google_str
            results[key] = entry_copy
            processed += 1
            time.sleep(2)

    # ── Layer 3: YouTube video IDs ─────────────────────────────────────────────
    if do_youtube:
        print(f"\n── Layer 3: YouTube video IDs ──")
        if not yt_api_key:
            print("  ⚠️  YOUTUBE_API_KEY not set in .env — skipping")
        else:
            for row in districts:
                state        = row.get("state", "").strip()
                district_raw = row.get("district_name", "").strip()
                if not state or not district_raw:
                    continue
                if filter_set and district_raw.lower() not in filter_set:
                    continue

                key   = f"{state.lower()}_{district_raw.lower()}"
                entry = results.get(key, existing.get(key, {}))

                # Skip if already has youtube_ids (use --all to re-fetch)
                if not force_all and entry.get("youtube_ids"):
                    continue

                product = products.get(key) or district_raw
                print(f"  YouTube: {district_raw}, {state} — {product}...", end=" ", flush=True)

                yt_ids = search_youtube_ids(district_raw, product, yt_api_key)
                yc = len([v for v in yt_ids.split(",") if v]) if yt_ids else 0
                print(f"[{yc} videos]")

                entry_copy = dict(entry)
                entry_copy["youtube_ids"] = yt_ids
                results[key] = entry_copy
                processed += 1
                time.sleep(1)

    # ── Write output ───────────────────────────────────────────────────────────
    seen_keys, final_rows = set(), []
    for row in districts:
        state        = row.get("state", "").strip()
        district_raw = row.get("district_name", "").strip()
        if not state or not district_raw:
            continue
        key = f"{state.lower()}_{district_raw.lower()}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        if key in results:
            r = results[key]
            final_rows.append({f: r.get(f, "") for f in FIELDNAMES})
        else:
            final_rows.append({
                "state": state, "district": district_raw,
                "url": "", "status": "FAILED",
                "youtube_ids": "", "pdf_urls": "", "google_urls": "",
            })

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(final_rows)

    match    = sum(1 for r in final_rows if r["status"] == "MATCH")
    base     = sum(1 for r in final_rows if r["status"] == "BASE")
    failed   = sum(1 for r in final_rows if r["status"] == "FAILED")
    with_yt  = sum(1 for r in final_rows if r.get("youtube_ids"))
    with_pdf = sum(1 for r in final_rows if r.get("pdf_urls"))
    with_g   = sum(1 for r in final_rows if r.get("google_urls"))

    print(f"\n✅ odop_urls.csv updated — {len(final_rows)} districts")
    print(f"   MATCH: {match}  |  BASE: {base}  |  FAILED: {failed}")
    print(f"   Google research: {with_g}  |  YouTube: {with_yt}  |  PDFs: {with_pdf}")
    print(f"   Processed this run: {processed}")


if __name__ == "__main__":
    main()
