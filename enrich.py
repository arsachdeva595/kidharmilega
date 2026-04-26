#!/usr/bin/env python3
"""
enrich.py — Fetch live ODOP Google Sheet + AI-enrich each district into data/districts.csv

Usage:
  python3 enrich.py                           # resume — skip already-cached, enrich new rows
  python3 enrich.py --all                     # re-enrich everything from scratch
  python3 enrich.py --limit 20               # process at most 20 new rows this run
  python3 enrich.py --filter "Varanasi,Jaipur"  # enrich only these districts
  python3 enrich.py --limit 10 --filter "Lucknow"  # combine flags
  python3 enrich.py --match-only                    # only MATCH-status districts (verified ODOP pages)
  python3 enrich.py --match-only --force-scrape     # re-scrape + re-enrich all MATCH districts from scratch

After running, rebuild the site with: python3 build.py
"""

import anthropic, csv, io, json, os, re, subprocess, sys, time, urllib.request
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SHEET_URL    = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQbSFSj1EnJyzmw8aAYcib7a0bxU8AFmmSRHltCK5DF04fZI6IYxS7ZytZay2Kt48uULSIa6NWD5HZZ/pub?gid=1455566310&single=true&output=csv"
BASE_DIR     = Path(__file__).parent
CACHE_FILE   = BASE_DIR / "data" / "enrichment_cache.json"
OUT_CSV      = BASE_DIR / "data" / "districts.csv"
ODOP_URL_CSV     = BASE_DIR / "data" / "odop_urls.csv"
SCRAPED_FACTS_FILE = BASE_DIR / "data" / "scraped_facts.json"
REPORT_CSV       = BASE_DIR / "data" / "enrichment_report.csv"

CSV_COLUMNS = [
    "district_id", "state", "district_name", "district_name_hin", "url_slug",
    "population", "area_km2", "literacy_rate", "main_languages", "city_tier",
    "famous_for_1_line", "odop_product_name", "odop_category", "odop_gi_tag", "gi_tag_year",
    "why_this_district", "odop_raw_materials", "production_scale", "export_potential", "export_countries",
    "min_setup_cost", "max_setup_cost", "gross_margin_wholesale", "gross_margin_d2c", "breakeven_timeline",
    "export_margin",
    "revenue_stream_1", "revenue_stream_2", "revenue_stream_3", "revenue_stream_4", "revenue_stream_5",
    "primary_target_audience", "ideal_founder_personality", "suitable_for", "not_suitable_for",
    "opportunity_score", "alert_stat", "geo_anchor",
    "step_1_learn", "step_2_source", "step_3_produce", "step_4_brand", "step_5_sell", "step_6_scale",
    "brand_name_idea_1", "brand_name_idea_2", "brand_name_idea_3", "brand_name_idea_4", "brand_name_idea_5",
    "marketing_idea_1", "marketing_idea_2", "marketing_idea_3",
    "relevant_central_scheme_1", "relevant_central_scheme_2",
    "relevant_state_scheme_1", "relevant_state_scheme_2",
    "success_story_name", "success_story_desc", "success_story_cost", "success_story_subsidy",
    "success_story_employees", "success_story_source",
    "logistics_info",
    "industrial_park_1_name", "industrial_park_1_desc", "industrial_park_1_tag",
    "industrial_park_2_name", "industrial_park_2_desc", "industrial_park_2_tag",
    "industrial_park_3_name", "industrial_park_3_desc", "industrial_park_3_tag",
    "cluster_2_name", "cluster_2_town", "cluster_2_desc", "cluster_2_tag",
    "cluster_3_name", "cluster_3_town", "cluster_3_desc", "cluster_3_tag",
    "faq_1", "faq_2", "faq_3", "faq_4", "faq_5", "faq_6",
    "udyam_registration", "page_status", "tier_priority",
    "seo_title", "meta_description", "primary_keyword",
    "odop_photo",
]

# ── Official govt ODOP page URL lookup ────────────────────────────────────────
# Key format: "{slug(state)}_{slug(district)}"  — verified by hand from state portals
GOVT_ODOP_URLS = {
    # Andhra Pradesh
    "andhra-pradesh_anantapuramu":  "https://ananthapuramu.ap.gov.in/one-district-one-product/",
    "andhra-pradesh_chittoor":      "https://chittoor.ap.gov.in/one-district-one-product/",
    "andhra-pradesh_east-godavari": "https://eastgodavari.ap.gov.in/one-district-one-product/",
    "andhra-pradesh_guntur":        "https://guntur.ap.gov.in/one-district-one-product/",
    "andhra-pradesh_kakinada":      "https://kakinada.ap.gov.in/one-district-one-product/",
    "andhra-pradesh_krishna":       "https://krishna.ap.gov.in/one-district-one-product/",
    "andhra-pradesh_kurnool":       "https://kurnool.ap.gov.in/one-district-one-product/",
    "andhra-pradesh_prakasam":      "https://prakasam.ap.gov.in/one-district-one-product/",
    "andhra-pradesh_srikakulam":    "https://srikakulam.ap.gov.in/one-district-one-product/",
    "andhra-pradesh_visakhapatnam": "https://visakhapatnam.ap.gov.in/one-district-one-product/",
    "andhra-pradesh_west-godavari": "https://westgodavari.ap.gov.in/one-district-one-product/",
    "andhra-pradesh_ysr-kadapa":    "https://kadapa.ap.gov.in/one-district-one-product/",
    # Bihar
    "bihar_banka":       "https://banka.bihar.gov.in/one-district-one-product/",
    "bihar_bhagalpur":   "https://bhagalpur.bihar.gov.in/one-district-one-product/",
    "bihar_darbhanga":   "https://darbhanga.bihar.gov.in/one-district-one-product/",
    "bihar_gaya":        "https://gaya.bihar.gov.in/one-district-one-product/",
    "bihar_katihar":     "https://katihar.bihar.gov.in/one-district-one-product/",
    "bihar_muzaffarpur": "https://muzaffarpur.bihar.gov.in/one-district-one-product/",
    "bihar_patna":       "https://patna.bihar.gov.in/one-district-one-product/",
    # Chhattisgarh
    "chhattisgarh_bastar":   "https://bastar.cg.gov.in/one-district-one-product/",
    "chhattisgarh_bilaspur": "https://bilaspur.cg.gov.in/one-district-one-product/",
    "chhattisgarh_raigarh":  "https://raigarh.cg.gov.in/one-district-one-product/",
    # Gujarat
    "gujarat_ahmedabad": "https://ahmedabad.gujarat.gov.in/one-district-one-product/",
    "gujarat_anand":     "https://anand.gujarat.gov.in/one-district-one-product/",
    "gujarat_bhavnagar": "https://bhavnagar.gujarat.gov.in/one-district-one-product/",
    "gujarat_kachchh":   "https://kachchh.gujarat.gov.in/one-district-one-product/",
    "gujarat_rajkot":    "https://rajkot.gujarat.gov.in/one-district-one-product/",
    "gujarat_surat":     "https://surat.gujarat.gov.in/one-district-one-product/",
    # Haryana
    "haryana_faridabad": "https://faridabad.haryana.gov.in/one-district-one-product/",
    "haryana_gurugram":  "https://gurugram.haryana.gov.in/one-district-one-product/",
    "haryana_karnal":    "https://karnal.haryana.gov.in/one-district-one-product/",
    "haryana_panipat":   "https://panipat.haryana.gov.in/one-district-one-product/",
    # Karnataka
    "karnataka_bengaluru-urban": "https://bengaluruurban.karnataka.gov.in/one-district-one-product/",
    "karnataka_chikkamagaluru":  "https://chikkamagaluru.karnataka.gov.in/one-district-one-product/",
    "karnataka_mysuru":          "https://mysuru.karnataka.gov.in/one-district-one-product/",
    "karnataka_udupi":           "https://udupi.karnataka.gov.in/one-district-one-product/",
    # Kerala
    "kerala_kozhikode": "https://kozhikode.kerala.gov.in/one-district-one-product/",
    "kerala_palakkad":  "https://palakkad.kerala.gov.in/one-district-one-product/",
    "kerala_wayanad":   "https://wayanad.kerala.gov.in/one-district-one-product/",
    # Madhya Pradesh
    "madhya-pradesh_bhopal":  "https://bhopal.mp.gov.in/one-district-one-product/",
    "madhya-pradesh_indore":  "https://indore.mp.gov.in/one-district-one-product/",
    "madhya-pradesh_ratlam":  "https://ratlam.mp.gov.in/one-district-one-product/",
    "madhya-pradesh_ujjain":  "https://ujjain.mp.gov.in/one-district-one-product/",
    # Maharashtra
    "maharashtra_aurangabad": "https://aurangabad.maharashtra.gov.in/one-district-one-product/",
    "maharashtra_kolhapur":   "https://kolhapur.maharashtra.gov.in/one-district-one-product/",
    "maharashtra_nagpur":     "https://nagpur.maharashtra.gov.in/one-district-one-product/",
    "maharashtra_nashik":     "https://nashik.maharashtra.gov.in/one-district-one-product/",
    "maharashtra_pune":       "https://pune.maharashtra.gov.in/one-district-one-product/",
    # Odisha
    "odisha_cuttack": "https://cuttack.odisha.gov.in/one-district-one-product/",
    "odisha_khordha": "https://khordha.odisha.gov.in/one-district-one-product/",
    "odisha_puri":    "https://puri.odisha.gov.in/one-district-one-product/",
    # Punjab
    "punjab_amritsar":  "https://amritsar.punjab.gov.in/one-district-one-product/",
    "punjab_jalandhar": "https://jalandhar.punjab.gov.in/one-district-one-product/",
    "punjab_ludhiana":  "https://ludhiana.punjab.gov.in/one-district-one-product/",
    # Rajasthan
    "rajasthan_bikaner": "https://bikaner.rajasthan.gov.in/one-district-one-product/",
    "rajasthan_jaipur":  "https://jaipur.rajasthan.gov.in/one-district-one-product/",
    "rajasthan_jodhpur": "https://jodhpur.rajasthan.gov.in/one-district-one-product/",
    # Tamil Nadu
    "tamil-nadu_chennai":      "https://chennai.tn.gov.in/one-district-one-product/",
    "tamil-nadu_coimbatore":   "https://coimbatore.tn.gov.in/one-district-one-product/",
    "tamil-nadu_kancheepuram": "https://kancheepuram.tn.gov.in/one-district-one-product/",
    "tamil-nadu_tiruppur":     "https://tiruppur.tn.gov.in/one-district-one-product/",
    # Telangana
    "telangana_hyderabad":  "https://hyderabad.telangana.gov.in/one-district-one-product/",
    "telangana_karimnagar": "https://karimnagar.telangana.gov.in/one-district-one-product/",
    "telangana_warangal":   "https://warangal.telangana.gov.in/one-district-one-product/",
    # Uttar Pradesh
    "uttar-pradesh_agra":     "https://agra.up.gov.in/one-district-one-product/",
    "uttar-pradesh_aligarh":  "https://aligarh.up.gov.in/one-district-one-product/",
    "uttar-pradesh_lucknow":  "https://lucknow.up.gov.in/one-district-one-product/",
    "uttar-pradesh_varanasi": "https://varanasi.up.gov.in/one-district-one-product/",
    # West Bengal
    "west-bengal_darjeeling": "https://darjeeling.wb.gov.in/one-district-one-product/",
    "west-bengal_hooghly":    "https://hooghly.wb.gov.in/one-district-one-product/",
    "west-bengal_murshidabad":"https://murshidabad.wb.gov.in/one-district-one-product/",
}

# States that follow {district}.{code}.gov.in/one-district-one-product/ pattern
# Used to auto-construct URLs for districts NOT in the known list above
STATE_ODOP_PATTERNS = {
    "Andhra Pradesh":  ("ap",          "gov.in"),
    "Bihar":           ("bihar",       "gov.in"),
    "Chhattisgarh":    ("cg",          "gov.in"),
    "Gujarat":         ("gujarat",     "gov.in"),
    "Haryana":         ("haryana",     "gov.in"),
    "Karnataka":       ("karnataka",   "gov.in"),
    "Kerala":          ("kerala",      "gov.in"),
    "Madhya Pradesh":  ("mp",          "gov.in"),
    "Maharashtra":     ("maharashtra", "gov.in"),
    "Odisha":          ("odisha",      "gov.in"),
    "Punjab":          ("punjab",      "gov.in"),
    "Rajasthan":       ("rajasthan",   "gov.in"),
    "Tamil Nadu":      ("tn",          "gov.in"),
    "Telangana":       ("telangana",   "gov.in"),
    "Uttar Pradesh":   ("up",          "gov.in"),
    "West Bengal":     ("wb",          "gov.in"),
}


AI_PROMPT = """\
You are a business researcher for KidharMilega — India's district-level business discovery platform.

Your job: generate verified, specific, founder-ready data for this ODOP entry. A real person from this district is going to read this and decide whether to start this business. Make every field count.

KNOWN DATA:
State: {state}
District: {district}
Product: {product}
Category: {category}
Sector: {sector}
Description: {description}
GI Status: {gi_status}
Ministry: {ministry}

VERIFIED FACTS — extracted from the official govt ODOP page for this district.
Use every number here verbatim. Do not round, change, or contradict these figures.
If a field below is non-empty, it came from the official page — treat it as ground truth.
---
{verified_facts}
---

CONTENT RULES (follow strictly):
1. NEVER use these words: vibrant, testament, tapestry, realm, burgeoning, bustling, brimming, symphony, kaleidoscope, landscape, embark, delve, unlock, showcase, elevate, leverage, foster, beacon, thriving, rich heritage, treasure trove, nestled.
2. Steps must read like a WhatsApp message from an experienced founder — plain, specific, zero fluff. Use real cluster names, real market names, real platform names.
3. Step 1 must be doable at ₹0 — visit a cluster, call a supplier, register on Udyam (free), attend a local haat. No money required in step 1.
4. suitable_for must name a real person type: "First-gen founder with ₹3-5L savings and 6 months runway" — not "passionate entrepreneurs".
5. geo_anchor: 3 sentences, dense with facts. Mention geography, raw material proximity, cluster size, buyer markets. This paragraph will be indexed by AI search engines — make it information-dense.
6. alert_stat: one striking number or fact about this product/district. E.g. "Anantapuram produces 60,000 jeans daily — more than most cities in India."
7. All scheme names must be real and currently active (PMEGP, SFURTI, PM Vishwakarma, MUDRA, One District One Product scheme, GI registration support, etc.).
8. FAQ answers must be plain answers a local would give — not corporate speak.
9. opportunity_score: integer 1-10. Base it on: market size (3pts), export potential (2pts), raw material access (2pts), govt support (2pts), founder-friendliness (1pt).
10. Return ONLY valid JSON. No markdown fences. No prose before or after.

Return a JSON object with ALL of these string-valued fields:

{{
  "district_name_hin": "district name in native script",
  "population": "digits only",
  "area_km2": "digits only",
  "literacy_rate": "decimal e.g. 77.08",
  "main_languages": "top 2-3, comma-separated",
  "city_tier": "Tier 1, Tier 2, or Tier 3",
  "famous_for_1_line": "one factual hook — what the district is known for producing",
  "gi_tag_year": "4-digit year if GI awarded, else empty string",
  "why_this_district": "2-3 sentences: geography, raw material access, artisan base, buyer proximity — facts only",
  "odop_raw_materials": "comma-separated list",
  "production_scale": "e.g. ₹420 Cr annual market, 800 units/day",
  "export_potential": "High, Medium, or Low",
  "export_countries": "top countries, comma-separated",
  "min_setup_cost": "digits only — realistic minimum in INR",
  "max_setup_cost": "digits only — realistic maximum in INR",
  "gross_margin_wholesale": "e.g. 25-35%",
  "gross_margin_d2c": "e.g. 55-70%",
  "breakeven_timeline": "e.g. 8-14 months",
  "export_margin": "e.g. 40-55% FOB margin",
  "suitable_for": "specific founder profile with capital range and time commitment",
  "not_suitable_for": "who should skip this — be honest",
  "primary_target_audience": "who buys this and where",
  "ideal_founder_personality": "2-3 trait words",
  "opportunity_score": "integer 1-10",
  "alert_stat": "one striking statistic sentence about this product/district — specific numbers",
  "geo_anchor": "3 dense sentences: geography, cluster size, raw material source, buyer markets, production numbers",
  "revenue_stream_1": "D2C channel — specific platform",
  "revenue_stream_2": "Wholesale — specific buyers",
  "revenue_stream_3": "Export — specific markets",
  "revenue_stream_4": "B2B institutional — specific buyers",
  "revenue_stream_5": "ancillary stream",
  "step_1_learn": "Zero-cost action: visit X cluster, call Y market, attend Z haat — free, doable this week",
  "step_2_source": "Where exactly to source, first-batch cost, supplier area name",
  "step_3_produce": "How to start — rent a unit vs artisan partnership, cost range",
  "step_4_brand": "Udyam + GI registration + IEC if export — specific steps, costs, timelines",
  "step_5_sell": "First sale: specific platform, first order size, expected first-month revenue",
  "step_6_scale": "How to grow: what changes at ₹10L/month, who to hire, where to exhibit",
  "brand_name_idea_1": "creative brand name",
  "brand_name_idea_2": "creative brand name",
  "brand_name_idea_3": "creative brand name",
  "brand_name_idea_4": "creative brand name",
  "brand_name_idea_5": "creative brand name",
  "marketing_idea_1": "specific tactic: platform + content type + hook",
  "marketing_idea_2": "specific tactic: platform + content type + hook",
  "marketing_idea_3": "specific tactic: platform + content type + hook",
  "relevant_central_scheme_1": "Scheme name — exact benefit amount or percentage",
  "relevant_central_scheme_2": "Scheme name — exact benefit amount or percentage",
  "relevant_state_scheme_1": "{state} scheme name — exact benefit",
  "relevant_state_scheme_2": "{state} scheme name — exact benefit",
  "success_story_name": "Name of a real business or entrepreneur from this district/product (leave empty if unknown)",
  "success_story_desc": "What they built, how — 1-2 sentences, specific numbers if known",
  "success_story_cost": "Their reported setup cost in INR",
  "success_story_subsidy": "Govt subsidy they received if any",
  "success_story_employees": "How many people employed",
  "success_story_source": "Where this info comes from (e.g. PIB press release, Ministry ODOP report 2023)",
  "logistics_info": "pipe-separated: Airport: nearest airport + km|Road: NH number + connectivity|Rail: nearest railhead|Seaport: nearest port if relevant|Power: grid status",
  "industrial_park_1_name": "Name of nearest industrial estate or MSME cluster",
  "industrial_park_1_desc": "What's available there — plot size, existing tenants",
  "industrial_park_1_tag": "MSME Cluster or SEZ or Industrial Estate or Craft Village",
  "industrial_park_2_name": "Second option if exists, else empty",
  "industrial_park_2_desc": "",
  "industrial_park_2_tag": "",
  "industrial_park_3_name": "",
  "industrial_park_3_desc": "",
  "industrial_park_3_tag": "",
  "cluster_2_name": "Name of a nearby complementary product cluster in this district",
  "cluster_2_town": "Town/tehsil where it's concentrated",
  "cluster_2_desc": "1 line on what's produced there",
  "cluster_2_tag": "e.g. Textiles or Food or Handicrafts",
  "cluster_3_name": "Third cluster if exists, else empty",
  "cluster_3_town": "",
  "cluster_3_desc": "",
  "cluster_3_tag": "",
  "faq_1": "Kitna paisa chahiye shuru karne ke liye?|||{{write specific cost range here}}",
  "faq_2": "Kya mujhe experience chahiye?|||{{honest answer for this specific product}}",
  "faq_3": "Government se kya help milti hai?|||{{specific scheme names and benefit amounts}}",
  "faq_4": "Pehla customer kahan se milega?|||{{specific platform or market or buyer type}}",
  "faq_5": "Kya yeh export ho sakta hai?|||{{honest answer with destination countries and basic process}}",
  "faq_6": "Agar flop hua toh?|||{{honest downside assessment and exit option}}",
  "tier_priority": "1, 2, or 3"
}}"""


SCRAPE_PROMPT = """\
You are extracting structured data about an Indian ODOP (One District One Product) district.
The content below may come from multiple sources — official govt pages, IBEF/PIB reports, PDFs, and YouTube transcripts.
Each source block is labelled. Extract the best available fact from any source.

District: {district}
Product: {product}
State: {state}

RESEARCH CONTENT:
{page_content}

Extract ONLY information that is explicitly stated in the content above. Do NOT infer, estimate, or use outside knowledge.
Use empty string "" for any field not found in any source.

Return JSON with exactly these fields:
{{
  "production_scale": "exact annual market or production value from page e.g. '₹450 Cr annual market'",
  "daily_output": "daily production figure if stated e.g. '60,000 units/day'",
  "artisan_count": "number of artisans or skilled workers explicitly mentioned",
  "unit_count": "number of production units or businesses mentioned",
  "employment_total": "total employment (direct + indirect) if stated",
  "cluster_names": "cluster or production zone names mentioned, comma-separated",
  "product_varieties": "specific product types or variants listed on the page",
  "success_story_name": "name of any specific business or entrepreneur featured",
  "success_story_detail": "what they achieved — use numbers from the page",
  "scheme_names": "government schemes mentioned by name, comma-separated",
  "export_countries": "export destination countries if mentioned",
  "export_value": "export turnover or volume if stated",
  "raw_materials": "raw materials explicitly listed",
  "gi_info": "GI tag year or details if mentioned",
  "key_facts": "any other specific numbers or facts — pipe-separated sentences",
  "page_quality": "good (has production numbers + artisans + at least 3 facts) / partial (has some numbers) / empty (no useful data)"
}}"""


def slug(t):
    return re.sub(r"[^a-z0-9-]", "", re.sub(r"\s+", "-", str(t).lower().strip()))


def drive_url(raw):
    """Convert a Google Drive share URL to a direct embeddable image URL."""
    if not raw:
        return ""
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", raw)
    if m:
        return f"https://drive.google.com/uc?export=view&id={m.group(1)}"
    return raw


def load_odop_urls():
    """Load odop_urls.csv then overlay with hardcoded verified entries (hardcoded always wins)."""
    urls = {}
    if ODOP_URL_CSV.exists():
        with open(ODOP_URL_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                st = row.get("state", "").strip()
                di = row.get("district", "").strip()
                ur = row.get("url", "").strip()
                if st and di and ur:
                    urls[slug(st) + "_" + slug(di)] = ur
    # Manually verified URLs always override auto-discovered ones
    urls.update(GOVT_ODOP_URLS)
    return urls


_ODOP_URLS        = None  # lazy-loaded on first call
_ODOP_STATUSES    = None  # lazy-loaded on first call
_FALLBACK_SOURCES = None  # lazy-loaded on first call


def load_odop_statuses():
    """Load status from odop_urls.csv. Derives from URL if status column is missing."""
    statuses = {}
    if ODOP_URL_CSV.exists():
        with open(ODOP_URL_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                st = row.get("state", "").strip()
                di = row.get("district", "").strip()
                if not st or not di:
                    continue
                key = slug(st) + "_" + slug(di)
                status = row.get("status", "").strip()
                if not status:
                    ur = row.get("url", "").strip()
                    if not ur:
                        status = "FAILED"
                    elif "/one-district-one-product" in ur.rstrip("/"):
                        status = "MATCH"
                    else:
                        status = "BASE"
                statuses[key] = status
    return statuses


def get_odop_status(state, district):
    """Return MATCH / BASE / FAILED / UNKNOWN based on the resolved URL for this district."""
    key = slug(state) + "_" + slug(district)
    # Hardcoded verified entries → derive status from their URL directly
    if key in GOVT_ODOP_URLS:
        url = GOVT_ODOP_URLS[key]
        return "MATCH" if "/one-district-one-product" in url.rstrip("/") else "BASE"
    # Fall back to CSV-derived status
    global _ODOP_STATUSES
    if _ODOP_STATUSES is None:
        _ODOP_STATUSES = load_odop_statuses()
    return _ODOP_STATUSES.get(key, "UNKNOWN")


def load_match_keys():
    """Return set of slug keys whose ODOP URL has /one-district-one-product/ (verified pages)."""
    keys = set()
    # Hardcoded verified entries are all MATCH
    for k, url in GOVT_ODOP_URLS.items():
        if "/one-district-one-product" in url:
            keys.add(k)
    # CSV entries — derive status from URL if status column is blank
    if ODOP_URL_CSV.exists():
        with open(ODOP_URL_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                st = row.get("state", "").strip()
                di = row.get("district", "").strip()
                if not st or not di:
                    continue
                status = row.get("status", "").strip()
                if not status:
                    ur = row.get("url", "").strip()
                    status = "MATCH" if "/one-district-one-product" in ur.rstrip("/") else ""
                if status == "MATCH":
                    keys.add(slug(st) + "_" + slug(di))
    return keys


def load_fallback_sources_all():
    """Load youtube_ids, pdf_urls, and google_urls columns from odop_urls.csv."""
    sources = {}
    if ODOP_URL_CSV.exists():
        with open(ODOP_URL_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                st = row.get("state", "").strip()
                di = row.get("district", "").strip()
                if not st or not di:
                    continue
                key = slug(st) + "_" + slug(di)
                yt_raw      = row.get("youtube_ids", "")
                pdf_raw     = row.get("pdf_urls", "")
                google_raw  = row.get("google_urls", "")
                sources[key] = {
                    "youtube_ids": [v.strip() for v in yt_raw.split(",")  if v.strip()],
                    "pdf_urls":    [u.strip() for u in pdf_raw.split("|") if u.strip()],
                    "google_urls": [u.strip() for u in google_raw.split("|") if u.strip()],
                }
    return sources


def get_fallback_sources(state, district):
    """Return pre-discovered {youtube_ids: [...], pdf_urls: [...]} for a district."""
    global _FALLBACK_SOURCES
    if _FALLBACK_SOURCES is None:
        _FALLBACK_SOURCES = load_fallback_sources_all()
    return _FALLBACK_SOURCES.get(slug(state) + "_" + slug(district), {})


def govt_url_for(state, district):
    """Return verified govt ODOP URL, or auto-construct one, or None."""
    global _ODOP_URLS
    if _ODOP_URLS is None:
        _ODOP_URLS = load_odop_urls()
    key = slug(state) + "_" + slug(district)
    if key in _ODOP_URLS:
        return _ODOP_URLS[key]
    pattern = STATE_ODOP_PATTERNS.get(state)
    if pattern:
        code, tld = pattern
        d_slug = re.sub(r"[^a-z0-9]", "", slug(district))
        return f"https://{d_slug}.{code}.{tld}/one-district-one-product/"
    return None


def fetch_govt_page(url, timeout=15):
    """Fetch URL, strip HTML tags, return plain text (max 5000 chars). Returns '' on failure."""
    try:
        result = subprocess.run(
            ["curl", "-sL", "--max-time", str(timeout),
             "-A", "Mozilla/5.0 (compatible; KidharMilega-bot/1.0; research)",
             url],
            capture_output=True, text=True, timeout=timeout + 5
        )
        if result.returncode != 0 or not result.stdout.strip():
            return ""
        html = result.stdout
        html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<[^>]+>", " ", html)
        html = re.sub(r"&[a-z]{2,6};", " ", html)
        text = re.sub(r"\s+", " ", html).strip()
        return text[:5000] if text else ""
    except Exception:
        return ""


def search_mofpi_pdfs(district, product, state, max_results=3):
    """Search for MoFPI / PMFME handbooks via ddgs. Returns list of URLs."""
    queries = [
        f"mofpi.gov.in {product} {district} PDF",
        f"PMFME handbook {product} {district} {state} pdf",
        f"One District One Product {product} {district} report",
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
    return found[:5]


def extract_pdf_text(pdf_url, max_chars=6000):
    """Download a PDF and return extracted plain text. Returns '' on any failure."""
    try:
        import pdfplumber
        req = urllib.request.Request(
            pdf_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; KidharMilega-bot/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages[:15])
        return text[:max_chars] if text.strip() else ""
    except Exception:
        return ""


def pdf_fallback(client, district, product, state, pre_urls=None):
    """Try pre-discovered PDF URLs first, then search MoFPI. Returns scraped-facts dict or {}."""
    pdf_urls = list(pre_urls or []) or search_mofpi_pdfs(district, product, state)
    for url in pdf_urls:
        text = extract_pdf_text(url)
        if text:
            try:
                facts = scrape_facts(client, text, district, product, state)
                facts["_source"] = f"pdf:{url}"
                return facts
            except Exception:
                pass
    return {}


def search_youtube_videos(district, product, api_key, max_results=5):
    """Search YouTube Data API v3 for relevant videos. Returns list of video IDs."""
    try:
        from googleapiclient.discovery import build as yt_build
        yt = yt_build("youtube", "v3", developerKey=api_key)
    except Exception:
        return []
    queries = [
        f"{product} {district} business manufacturing",
        f"ODOP {product} {district}",
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
    return ids[:5]


def youtube_fallback(client, district, product, state, pre_ids=None):
    """Use pre-discovered video IDs first, then search YouTube API. Returns facts dict or {}."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return {}
    video_ids = list(pre_ids or [])
    if not video_ids:
        api_key = os.environ.get("YOUTUBE_API_KEY", "")
        if not api_key:
            return {}
        video_ids = search_youtube_videos(district, product, api_key)
    if not video_ids:
        return {}
    transcripts = []
    for vid in video_ids:
        try:
            segs = YouTubeTranscriptApi.get_transcript(vid, languages=["hi", "en", "hi-IN"])
            text = " ".join(s["text"] for s in segs)
            transcripts.append(text[:2500])
        except Exception:
            pass
        if len(transcripts) >= 3:
            break
    if not transcripts:
        return {}
    combined = "\n\n---\n".join(transcripts)
    try:
        facts = scrape_facts(client, combined, district, product, state)
        facts["_source"] = "youtube"
        return facts
    except Exception:
        return {}


def fetch_sheet():
    result = subprocess.run(
        ["curl", "-sL", SHEET_URL],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        print(f"ERROR fetching sheet: {result.stderr}")
        sys.exit(1)
    return list(csv.DictReader(result.stdout.splitlines()))


def load_cache():
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache):
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_scraped_facts():
    if SCRAPED_FACTS_FILE.exists():
        return json.loads(SCRAPED_FACTS_FILE.read_text(encoding="utf-8"))
    return {}


def save_scraped_facts(facts):
    SCRAPED_FACTS_FILE.write_text(
        json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def parse_json_response(text):
    """Robustly extract and parse a JSON object from LLM output."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > start:
        text = text[start:end]
    return json.loads(text)


def scrape_facts(client, page_content, district, product, state):
    """Stage 1: extract facts from combined multi-source research content."""
    prompt = SCRAPE_PROMPT.format(
        district=district, product=product, state=state, page_content=page_content[:14000]
    )
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system="Extract only facts explicitly stated on this page. Return only valid JSON.",
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_json_response(msg.content[0].text)


def format_facts(facts, govt_url=""):
    """Convert scraped_facts dict to a readable string for the generation prompt."""
    if not facts:
        return "No official govt page available for this district."
    lines = [f"Source: {govt_url}" if govt_url else "Source: auto-constructed URL"]
    field_labels = {
        "production_scale": "Annual production/market",
        "daily_output":     "Daily output",
        "artisan_count":    "Artisans/workers",
        "unit_count":       "Production units",
        "employment_total": "Total employment",
        "cluster_names":    "Cluster names",
        "product_varieties":"Product varieties",
        "success_story_name": "Success story",
        "success_story_detail": "Success detail",
        "scheme_names":     "Govt schemes mentioned",
        "export_countries": "Export markets",
        "export_value":     "Export value",
        "raw_materials":    "Raw materials",
        "gi_info":          "GI info",
        "key_facts":        "Other facts",
    }
    for field, label in field_labels.items():
        val = facts.get(field, "").strip()
        if val:
            lines.append(f"{label}: {val}")
    if len(lines) == 1:
        return "Page fetched but no structured data found."
    return "\n".join(lines)


def generate_content(client, row, verified_facts_str):
    """Stage 2: generate all content fields, anchored to pre-extracted facts."""
    prompt = AI_PROMPT.format(
        state=row.get("State", ""),
        district=row.get("District", ""),
        product=row.get("Product", ""),
        category=row.get("Category", ""),
        sector=row.get("Sector", ""),
        description=row.get("Description", ""),
        gi_status=row.get("GI Status", ""),
        ministry=row.get("Ministry/ Department", ""),
        verified_facts=verified_facts_str,
    )
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8192,
        system="You are a business data researcher. Return only valid JSON — no markdown, no prose.",
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_json_response(msg.content[0].text)


def build_row(sheet_row, ai, idx):
    district = sheet_row.get("District", "").strip()
    state    = sheet_row.get("State", "").strip()
    product  = sheet_row.get("Product", "").strip()
    gi_raw   = sheet_row.get("GI Status", "").strip().lower()
    gi_tag   = "Yes" if "gi" in gi_raw and gi_raw != "no" else "No"

    photo = drive_url(sheet_row.get("Photo", "").strip())

    url_s   = slug(district)
    dist_id = f"{slug(state)[:2].upper()}-{slug(district)[:3].upper()}-{idx:04d}"

    min_cost_fmt = f"₹{ai.get('min_setup_cost','')} se" if ai.get("min_setup_cost","") else ""
    seo_title  = f"{product} Business in {district} — Real Costs, Steps & Govt Data | KidharMilega"
    meta_desc  = (f"{district} mein {product} ka business: {min_cost_fmt} shuru karo. "
                  f"Market size, raw materials, govt schemes aur step-by-step guide.").strip()
    primary_kw = f"{product.lower()} business {district.lower()}"

    return {
        "district_id":          dist_id,
        "state":                state,
        "district_name":        district,
        "district_name_hin":    ai.get("district_name_hin", ""),
        "url_slug":             url_s,
        "population":           ai.get("population", ""),
        "area_km2":             ai.get("area_km2", ""),
        "literacy_rate":        ai.get("literacy_rate", ""),
        "main_languages":       ai.get("main_languages", ""),
        "city_tier":            ai.get("city_tier", ""),
        "famous_for_1_line":    ai.get("famous_for_1_line", ""),
        "odop_product_name":    product,
        "odop_category":        sheet_row.get("Category", "").strip(),
        "odop_gi_tag":          gi_tag,
        "gi_tag_year":          ai.get("gi_tag_year", ""),
        "why_this_district":    ai.get("why_this_district", ""),
        "odop_raw_materials":   ai.get("odop_raw_materials", ""),
        "production_scale":     ai.get("production_scale", ""),
        "export_potential":     ai.get("export_potential", ""),
        "export_countries":     ai.get("export_countries", ""),
        "min_setup_cost":       ai.get("min_setup_cost", ""),
        "max_setup_cost":       ai.get("max_setup_cost", ""),
        "gross_margin_wholesale": ai.get("gross_margin_wholesale", ""),
        "gross_margin_d2c":     ai.get("gross_margin_d2c", ""),
        "breakeven_timeline":   ai.get("breakeven_timeline", ""),
        "export_margin":        ai.get("export_margin", ""),
        "revenue_stream_1":     ai.get("revenue_stream_1", ""),
        "revenue_stream_2":     ai.get("revenue_stream_2", ""),
        "revenue_stream_3":     ai.get("revenue_stream_3", ""),
        "revenue_stream_4":     ai.get("revenue_stream_4", ""),
        "revenue_stream_5":     ai.get("revenue_stream_5", ""),
        "primary_target_audience": ai.get("primary_target_audience", ""),
        "ideal_founder_personality": ai.get("ideal_founder_personality", ""),
        "suitable_for":         ai.get("suitable_for", ""),
        "not_suitable_for":     ai.get("not_suitable_for", ""),
        "opportunity_score":    str(ai.get("opportunity_score", "")),
        "alert_stat":           ai.get("alert_stat", ""),
        "geo_anchor":           ai.get("geo_anchor", ""),
        "step_1_learn":         ai.get("step_1_learn", ""),
        "step_2_source":        ai.get("step_2_source", ""),
        "step_3_produce":       ai.get("step_3_produce", ""),
        "step_4_brand":         ai.get("step_4_brand", ""),
        "step_5_sell":          ai.get("step_5_sell", ""),
        "step_6_scale":         ai.get("step_6_scale", ""),
        "brand_name_idea_1":    ai.get("brand_name_idea_1", ""),
        "brand_name_idea_2":    ai.get("brand_name_idea_2", ""),
        "brand_name_idea_3":    ai.get("brand_name_idea_3", ""),
        "brand_name_idea_4":    ai.get("brand_name_idea_4", ""),
        "brand_name_idea_5":    ai.get("brand_name_idea_5", ""),
        "marketing_idea_1":     ai.get("marketing_idea_1", ""),
        "marketing_idea_2":     ai.get("marketing_idea_2", ""),
        "marketing_idea_3":     ai.get("marketing_idea_3", ""),
        "relevant_central_scheme_1": ai.get("relevant_central_scheme_1", ""),
        "relevant_central_scheme_2": ai.get("relevant_central_scheme_2", ""),
        "relevant_state_scheme_1":   ai.get("relevant_state_scheme_1", ""),
        "relevant_state_scheme_2":   ai.get("relevant_state_scheme_2", ""),
        "success_story_name":   ai.get("success_story_name", ""),
        "success_story_desc":   ai.get("success_story_desc", ""),
        "success_story_cost":   ai.get("success_story_cost", ""),
        "success_story_subsidy": ai.get("success_story_subsidy", ""),
        "success_story_employees": ai.get("success_story_employees", ""),
        "success_story_source": ai.get("success_story_source", ""),
        "logistics_info":       ai.get("logistics_info", ""),
        "industrial_park_1_name": ai.get("industrial_park_1_name", ""),
        "industrial_park_1_desc": ai.get("industrial_park_1_desc", ""),
        "industrial_park_1_tag":  ai.get("industrial_park_1_tag", ""),
        "industrial_park_2_name": ai.get("industrial_park_2_name", ""),
        "industrial_park_2_desc": ai.get("industrial_park_2_desc", ""),
        "industrial_park_2_tag":  ai.get("industrial_park_2_tag", ""),
        "industrial_park_3_name": ai.get("industrial_park_3_name", ""),
        "industrial_park_3_desc": ai.get("industrial_park_3_desc", ""),
        "industrial_park_3_tag":  ai.get("industrial_park_3_tag", ""),
        "cluster_2_name":       ai.get("cluster_2_name", ""),
        "cluster_2_town":       ai.get("cluster_2_town", ""),
        "cluster_2_desc":       ai.get("cluster_2_desc", ""),
        "cluster_2_tag":        ai.get("cluster_2_tag", ""),
        "cluster_3_name":       ai.get("cluster_3_name", ""),
        "cluster_3_town":       ai.get("cluster_3_town", ""),
        "cluster_3_desc":       ai.get("cluster_3_desc", ""),
        "cluster_3_tag":        ai.get("cluster_3_tag", ""),
        "faq_1":                ai.get("faq_1", ""),
        "faq_2":                ai.get("faq_2", ""),
        "faq_3":                ai.get("faq_3", ""),
        "faq_4":                ai.get("faq_4", ""),
        "faq_5":                ai.get("faq_5", ""),
        "faq_6":                ai.get("faq_6", ""),
        "udyam_registration":   "Required — udyamregistration.gov.in",
        "page_status":          "live",
        "tier_priority":        str(ai.get("tier_priority", "2")),
        "seo_title":            seo_title,
        "meta_description":     meta_desc,
        "primary_keyword":      primary_kw,
        "odop_photo":           photo,
    }


def write_csv(rows):
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(rows)


# ── Report helpers ─────────────────────────────────────────────────────────────

BANNED_WORDS = {"vibrant","testament","tapestry","realm","burgeoning","bustling","brimming",
                "symphony","kaleidoscope","showcase","elevate","leverage","foster","beacon",
                "thriving","nestled","embark","delve","rich heritage","treasure trove"}

REPORT_FIELDS = ["production_scale","alert_stat","geo_anchor","famous_for_1_line",
                 "why_this_district","step_1_learn","step_2_source","suitable_for",
                 "success_story_name","faq_1","logistics_info","opportunity_score"]


def diff_fields(old, new):
    """Return list of field names that changed (or are newly filled) between old and new dicts."""
    changed = []
    for k in REPORT_FIELDS:
        ov = str(old.get(k, "")).strip()
        nv = str(new.get(k, "")).strip()
        if nv and nv != ov:
            changed.append(k)
    return changed


def quality_check(data):
    """Return list of quality warnings for a generated data dict."""
    warnings = []
    all_text = " ".join(str(v) for v in data.values()).lower()
    found_banned = [w for w in BANNED_WORDS if w in all_text]
    if found_banned:
        warnings.append(f"banned_words:{','.join(found_banned[:3])}")
    step1 = data.get("step_1_learn", "").lower()
    if any(x in step1 for x in ["₹", "rs.", "cost", "invest", "spend", "buy", "purchase"]):
        warnings.append("step_1_has_cost")
    suitable = data.get("suitable_for", "").lower()
    if any(x in suitable for x in ["passionate", "enthusiastic", "anyone", "all"]):
        warnings.append("suitable_for_generic")
    if not data.get("faq_1", ""):
        warnings.append("no_faqs")
    return warnings


def write_report(report_rows):
    cols = ["district","state","product","govt_url","url_status","data_source",
            "page_quality","facts_count","fields_changed","key_changes","warnings","enriched_at"]
    with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(report_rows)


def print_report_summary(report_rows):
    if not report_rows:
        return
    print("\n" + "─"*60)
    print(f"  ENRICHMENT REPORT — {len(report_rows)} districts processed")
    print("─"*60)
    good  = sum(1 for r in report_rows if r["page_quality"] == "good")
    part  = sum(1 for r in report_rows if r["page_quality"] == "partial")
    empty = sum(1 for r in report_rows if r["page_quality"] in ("empty","no-url"))
    total_changes = sum(r["fields_changed"] for r in report_rows)
    warned = [r for r in report_rows if r["warnings"]]
    print(f"  Govt page quality: {good} good  {part} partial  {empty} no data")
    print(f"  Fields updated: {total_changes} total across all districts")
    if warned:
        print(f"  Quality warnings ({len(warned)} districts):")
        for r in warned[:5]:
            print(f"    {r['district']}, {r['state']}: {r['warnings']}")
    print(f"  Full report: data/enrichment_report.csv")
    print("─"*60)


# ── Source collector (aggregate all P1–P4 sources) ────────────────────────────

def collect_all_source_texts(district, product, state, govt_url, url_status, sources):
    """
    Fetch raw text from every available source for this district.
    Returns (list of (label, text) tuples, list of log tokens).
    Never stops early — always tries all sources.
    """
    texts = []
    log   = []

    # P1 — Official govt ODOP page
    if govt_url and url_status in ("MATCH", "BASE", "UNKNOWN"):
        raw = fetch_govt_page(govt_url)
        if raw:
            texts.append(("Official Govt ODOP page", raw))
            log.append("[gov:ok]")
        else:
            log.append("[gov:miss]")
    else:
        log.append("[gov:skip]")

    # P2 — Google / DuckDuckGo research URLs (pre-populated by find_urls.py --google)
    for g_url in sources.get("google_urls", [])[:3]:
        raw = fetch_govt_page(g_url)
        if raw:
            texts.append(("Research article", raw))
            log.append("[g:ok]")
        else:
            log.append("[g:miss]")

    # P3 — PDFs pre-discovered by find_urls.py (no live search — use CSV data)
    for pdf_url in sources.get("pdf_urls", [])[:2]:
        raw = extract_pdf_text(pdf_url)
        if raw:
            texts.append(("Government PDF/handbook", raw))
            log.append("[pdf:ok]")
            break
    if not any("[pdf:ok]" in t for t in log):
        if sources.get("pdf_urls"):
            log.append("[pdf:miss]")

    # P4 — YouTube transcripts (pre-discovered by find_urls.py --youtube)
    yt_ids = sources.get("youtube_ids", [])
    if yt_ids:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            yt_texts = []
            for vid in yt_ids[:3]:
                try:
                    segs = YouTubeTranscriptApi.get_transcript(vid, languages=["hi", "en", "hi-IN"])
                    text = " ".join(s["text"] for s in segs)
                    if text.strip():
                        yt_texts.append(text[:2500])
                except Exception:
                    pass
            if yt_texts:
                texts.append(("YouTube video transcripts", "\n\n---\n".join(yt_texts)))
                log.append(f"[yt:{len(yt_texts)}ok]")
            else:
                log.append("[yt:miss]")
        except ImportError:
            log.append("[yt:no-lib]")

    return texts, log


def combine_sources(source_texts):
    """Merge (label, text) pairs into one labelled research document."""
    if not source_texts:
        return ""
    return "\n\n".join(
        f"=== {label.upper()} ===\n{text.strip()}"
        for label, text in source_texts
    )


# ── CLI ────────────────────────────────────────────────────────────────────────

_REFRESH_FIELDS = ["opportunity_score", "alert_stat", "geo_anchor", "faq_1", "faq_2",
                   "logistics_info", "success_story_name", "suitable_for"]


def needs_refresh(cached_data):
    """Return True if a cached entry is missing the new content fields."""
    return any(not str(cached_data.get(f, "")).strip() for f in _REFRESH_FIELDS)


def parse_args():
    args = sys.argv[1:]
    force_all    = "--all" in args
    refresh      = "--refresh" in args       # Re-enrich entries missing new fields (safe — no cache wipe)
    scrape_only  = "--scrape-only" in args
    force_scrape = "--force-scrape" in args
    limit       = None
    filter_set  = set()
    for i, a in enumerate(args):
        if a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
        if a == "--filter" and i + 1 < len(args):
            filter_set = {s.strip().lower() for s in args[i + 1].split(",")}
    return force_all, refresh, scrape_only, force_scrape, limit, filter_set


def main():
    force_all, refresh, scrape_only, force_scrape, limit, filter_set = parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set.")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    print("\n KidharMilega Enrichment Pipeline")
    print("="*50)
    print("Fetching ODOP sheet...")
    all_rows = fetch_sheet()

    # Deduplicate
    seen, unique_rows = set(), []
    for idx, row in enumerate(all_rows, start=1):
        d = row.get("District", "").strip()
        s = row.get("State", "").strip()
        if not d or not s:
            continue
        key = f"{slug(s)}_{slug(d)}"
        if key not in seen:
            seen.add(key)
            unique_rows.append((idx, key, row))
    print(f"Loaded {len(unique_rows)} unique districts")

    cache         = {} if force_all else load_cache()
    scraped_facts = {} if force_scrape else load_scraped_facts()
    client        = anthropic.Anthropic()

    def _stale_cache(key):
        """True if cache entry was generated without real scraped facts but we now have some."""
        if key not in scraped_facts:
            return False
        sf_quality = scraped_facts[key].get("page_quality", "")
        if sf_quality in ("empty", "", None):
            return False  # scraped facts are still empty — nothing to improve on
        cached_quality = cache.get(key, {}).get("_scraped_quality", "none")
        return cached_quality in ("none", "", None, "empty")  # cache predates real facts

    to_process = [
        (idx, key, row) for idx, key, row in unique_rows
        if (force_all or force_scrape
            or key not in cache           # never enriched
            or key not in scraped_facts   # has cache but never actually scraped — needs sourcing
            or _stale_cache(key)          # scraped since last gen run — regenerate with real facts
            or (refresh and needs_refresh(cache.get(key, {}))))
        and (not filter_set or row.get("District","").strip().lower() in filter_set)
    ]
    needs_scrape_count = sum(1 for _, k, _ in to_process if k not in scraped_facts)
    cap = min(limit, len(to_process)) if limit else len(to_process)
    print(f"Cached: {len(unique_rows)-len(to_process)}  |  To process: {cap}"
          + (f"  ({needs_scrape_count} need scraping)" if needs_scrape_count else "")
          + ("  [scrape-only]" if scrape_only else ""))
    print()

    report_rows   = []
    newly_done    = 0

    for idx, key, row in to_process:
        if limit is not None and newly_done >= limit:
            print(f"\n  Reached --limit {limit}. Run again to continue.")
            break

        district = row.get("District", "").strip()
        state    = row.get("State", "").strip()
        product  = row.get("Product", "").strip()
        print(f"  [{newly_done+1}/{cap}] {district}, {state}", end="  ", flush=True)

        # ── Stage 1: Scrape govt page (P1→P2→P3 fallback chain) ───────────
        govt_url   = govt_url_for(state, district)
        url_status = get_odop_status(state, district)
        sources    = get_fallback_sources(state, district)
        facts      = scraped_facts.get(key, {})

        if key not in scraped_facts or force_scrape:
            # Aggregate all sources — always collects P1+P2+P3+P4, never stops early
            source_texts, source_log = collect_all_source_texts(
                district, product, state, govt_url, url_status, sources
            )
            print(" ".join(source_log), end="  ", flush=True)

            combined = combine_sources(source_texts)
            if combined:
                try:
                    facts = scrape_facts(client, combined, district, product, state)
                    facts["_source"] = "|".join(label for label, _ in source_texts)
                    scraped_facts[key] = facts
                    save_scraped_facts(scraped_facts)
                    print(f"→ [quality:{facts.get('page_quality','?')}]", end=" ", flush=True)
                except Exception as e:
                    print(f"[extract-err:{e}]", end=" ", flush=True)
            else:
                print("[no-sources]", end=" ", flush=True)

        if scrape_only:
            newly_done += 1
            print()
            continue

        # ── Stage 2: Generate content ──────────────────────────────────────
        # Skip regeneration if: facts are still empty AND district already has cached content.
        # Never overwrite real cached content with content generated from zero facts.
        has_real_facts = bool(facts and facts.get("page_quality") not in ("empty", "", None))
        already_cached = key in cache
        if not has_real_facts and already_cached and not force_all:
            print(f"(no-facts, keeping cache)")
            newly_done += 1
            continue

        old_data           = cache.get(key, {})
        verified_facts_str = format_facts(facts, govt_url or "")

        try:
            new_data = generate_content(client, row, verified_facts_str)
            # Record what quality facts were used to generate this entry —
            # used by the to_process check to detect stale cache entries
            new_data["_scraped_quality"] = facts.get("page_quality", "none") if facts else "none"
            new_data["_scraped_source"]  = facts.get("_source", "gov") if facts else "none"
            cache[key] = new_data
            save_cache(cache)

            # ── Stage 3: Diff + quality check ─────────────────────────────
            changed  = diff_fields(old_data, new_data)
            warnings = quality_check(new_data)
            facts_count = sum(1 for k, v in facts.items()
                              if v and k not in ("page_quality",) and str(v).strip())
            report_rows.append({
                "district":      district,
                "state":         state,
                "product":       product,
                "govt_url":      govt_url or "",
                "url_status":    url_status,
                "data_source":   facts.get("_source", "gov" if facts else "none"),
                "page_quality":  facts.get("page_quality", "no-url"),
                "facts_count":   facts_count,
                "fields_changed": len(changed),
                "key_changes":   "|".join(changed),
                "warnings":      "|".join(warnings),
                "enriched_at":   time.strftime("%Y-%m-%d %H:%M"),
            })

            newly_done += 1
            warn_tag = f"  ⚠ {warnings[0]}" if warnings else ""
            print(f"✓  {len(changed)} fields updated  pg={facts.get('page_quality','no-url')}{warn_tag}")

        except anthropic.AuthenticationError:
            print("\nERROR: Invalid ANTHROPIC_API_KEY. export ANTHROPIC_API_KEY=sk-ant-...")
            sys.exit(1)
        except Exception as e:
            print(f"SKIP ({type(e).__name__}: {e})")

        time.sleep(0.3)

    # ── Write outputs ──────────────────────────────────────────────────────
    csv_rows = []
    added    = set()
    for idx, key, row in unique_rows:
        if key in cache and key not in added:
            csv_rows.append(build_row(row, cache[key], idx))
            added.add(key)

    write_csv(csv_rows)

    if report_rows:
        write_report(report_rows)
        print_report_summary(report_rows)

    print(f"\n✅ {OUT_CSV.name} — {len(csv_rows)} districts, {newly_done} processed this run")
    if not scrape_only:
        print("   Run `python3 build.py` to rebuild the site\n")


if __name__ == "__main__":
    main()
