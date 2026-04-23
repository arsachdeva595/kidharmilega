#!/usr/bin/env python3
"""
enrich.py — Fetch live ODOP Google Sheet + AI-enrich each district into data/districts.csv

Usage:
  python3 enrich.py                           # resume — skip already-cached, enrich new rows
  python3 enrich.py --all                     # re-enrich everything from scratch
  python3 enrich.py --limit 20               # process at most 20 new rows this run
  python3 enrich.py --filter "Varanasi,Jaipur"  # enrich only these districts
  python3 enrich.py --limit 10 --filter "Lucknow"  # combine flags

After running, rebuild the site with: python3 build.py
"""

import anthropic, csv, json, os, re, subprocess, sys, time
from pathlib import Path

SHEET_URL  = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQbSFSj1EnJyzmw8aAYcib7a0bxU8AFmmSRHltCK5DF04fZI6IYxS7ZytZay2Kt48uULSIa6NWD5HZZ/pub?gid=1455566310&single=true&output=csv"
BASE_DIR   = Path(__file__).parent
CACHE_FILE = BASE_DIR / "data" / "enrichment_cache.json"
OUT_CSV    = BASE_DIR / "data" / "districts.csv"

CSV_COLUMNS = [
    "district_id", "state", "district_name", "district_name_hin", "url_slug",
    "population", "area_km2", "literacy_rate", "main_languages", "city_tier",
    "famous_for_1_line", "odop_product_name", "odop_category", "odop_gi_tag", "gi_tag_year",
    "why_this_district", "odop_raw_materials", "production_scale", "export_potential", "export_countries",
    "min_setup_cost", "max_setup_cost", "gross_margin_wholesale", "gross_margin_d2c", "breakeven_timeline",
    "revenue_stream_1", "revenue_stream_2", "revenue_stream_3", "revenue_stream_4", "revenue_stream_5",
    "primary_target_audience", "ideal_founder_personality", "suitable_for", "not_suitable_for",
    "step_1_learn", "step_2_source", "step_3_produce", "step_4_brand", "step_5_sell", "step_6_scale",
    "brand_name_idea_1", "brand_name_idea_2", "brand_name_idea_3", "brand_name_idea_4", "brand_name_idea_5",
    "marketing_idea_1", "marketing_idea_2", "marketing_idea_3",
    "relevant_central_scheme_1", "relevant_central_scheme_2",
    "relevant_state_scheme_1", "relevant_state_scheme_2",
    "udyam_registration", "page_status", "tier_priority",
    "seo_title", "meta_description", "primary_keyword",
    "odop_photo",
]

AI_PROMPT = """\
You are a business research assistant for KidharMilega — India's small business discovery platform.

Generate accurate, specific, actionable business data for this ODOP (One District One Product) entry.

KNOWN DATA:
State: {state}
District: {district}
Product: {product}
Category: {category}
Sector: {sector}
Description: {description}
GI Status: {gi_status}
Ministry: {ministry}

Return ONLY a valid JSON object with these exact string-valued fields:

{{
  "district_name_hin": "district name in native script (Hindi/regional language)",
  "population": "latest census population — digits only, no commas",
  "area_km2": "district area in km² — digits only",
  "literacy_rate": "literacy rate as decimal e.g. 77.08",
  "main_languages": "top 2-3 spoken languages, comma-separated",
  "city_tier": "Tier 1, Tier 2, or Tier 3 based on economic/population size",
  "famous_for_1_line": "one punchy line — what makes this district/product iconic",
  "gi_tag_year": "year GI was awarded (4 digits) if GI Status = GI, else empty string",
  "why_this_district": "2-3 sentences on why this district is uniquely suited for this product",
  "odop_raw_materials": "key raw materials needed, comma-separated",
  "production_scale": "annual market size e.g. ₹500 Cr annual market",
  "export_potential": "High, Medium, or Low",
  "export_countries": "top export destination countries, comma-separated",
  "min_setup_cost": "minimum startup cost in rupees — digits only",
  "max_setup_cost": "maximum startup cost in rupees — digits only",
  "gross_margin_wholesale": "wholesale gross margin range e.g. 25-35%",
  "gross_margin_d2c": "D2C gross margin range e.g. 55-70%",
  "breakeven_timeline": "breakeven timeline e.g. 8-14 months",
  "suitable_for": "1 line — ideal founder profile for this product",
  "not_suitable_for": "1 line — who should avoid this business",
  "primary_target_audience": "primary customer description",
  "ideal_founder_personality": "2-3 trait words e.g. Creative & Patient",
  "revenue_stream_1": "primary revenue channel",
  "revenue_stream_2": "second revenue channel",
  "revenue_stream_3": "third revenue channel",
  "revenue_stream_4": "fourth revenue channel",
  "revenue_stream_5": "fifth revenue channel",
  "step_1_learn": "Step 1 Learn/Research: specific action, mention real clusters/markets",
  "step_2_source": "Step 2 Source Raw Materials: where to source, approximate first-batch cost",
  "step_3_produce": "Step 3 Produce/Partner: how to start production or find artisan partners",
  "step_4_brand": "Step 4 Brand & Register: Udyam + IEC + brand setup specifics",
  "step_5_sell": "Step 5 First Sale: specific platforms and tactics",
  "step_6_scale": "Step 6 Scale: how to grow after first 6 months",
  "brand_name_idea_1": "creative brand name for this product",
  "brand_name_idea_2": "creative brand name for this product",
  "brand_name_idea_3": "creative brand name for this product",
  "brand_name_idea_4": "creative brand name for this product",
  "brand_name_idea_5": "creative brand name for this product",
  "marketing_idea_1": "specific marketing tactic with platform and approach",
  "marketing_idea_2": "specific marketing tactic with platform and approach",
  "marketing_idea_3": "specific marketing tactic with platform and approach",
  "relevant_central_scheme_1": "Real central scheme name — specific benefit (e.g. PMEGP — up to ₹25L grant)",
  "relevant_central_scheme_2": "Real central scheme name — specific benefit",
  "relevant_state_scheme_1": "Real {state} state scheme name — specific benefit for this sector",
  "relevant_state_scheme_2": "Real {state} state scheme name — specific benefit for this sector",
  "tier_priority": "1 for nationally prominent product, 2 for regionally known, 3 for emerging"
}}

Rules:
- All values must be strings, no nulls
- Steps must be specific and actionable — mention real places, real costs, real platforms
- Schemes must be real Indian government schemes (PMEGP, SFURTI, PM Vishwakarma, MUDRA, etc.)
- Return ONLY the JSON object, nothing else, no markdown fences"""


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


def call_claude(client, row):
    prompt = AI_PROMPT.format(
        state=row.get("State", ""),
        district=row.get("District", ""),
        product=row.get("Product", ""),
        category=row.get("Category", ""),
        sector=row.get("Sector", ""),
        description=row.get("Description", ""),
        gi_status=row.get("GI Status", ""),
        ministry=row.get("Ministry/ Department", ""),
    )
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system="You are a business data researcher. Return only valid JSON — no markdown, no prose.",
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def build_row(sheet_row, ai, idx):
    district = sheet_row.get("District", "").strip()
    state    = sheet_row.get("State", "").strip()
    product  = sheet_row.get("Product", "").strip()
    gi_raw   = sheet_row.get("GI Status", "").strip().lower()
    gi_tag   = "Yes" if "gi" in gi_raw and gi_raw != "no" else "No"

    photo = drive_url(sheet_row.get("Photo", "").strip())

    url_s   = slug(district)
    dist_id = f"{slug(state)[:2].upper()}-{slug(district)[:3].upper()}-{idx:04d}"

    seo_title  = f"Start a Business in {district} 2026 | {product} Guide | KidharMilega"
    meta_desc  = f"Complete guide to starting a {product} business in {district} — ODOP product, vendors, events, costs and government schemes."
    primary_kw = f"start a business in {district.lower()}"

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
        "revenue_stream_1":     ai.get("revenue_stream_1", ""),
        "revenue_stream_2":     ai.get("revenue_stream_2", ""),
        "revenue_stream_3":     ai.get("revenue_stream_3", ""),
        "revenue_stream_4":     ai.get("revenue_stream_4", ""),
        "revenue_stream_5":     ai.get("revenue_stream_5", ""),
        "primary_target_audience": ai.get("primary_target_audience", ""),
        "ideal_founder_personality": ai.get("ideal_founder_personality", ""),
        "suitable_for":         ai.get("suitable_for", ""),
        "not_suitable_for":     ai.get("not_suitable_for", ""),
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
        "udyam_registration":   "Required — udyamregistration.gov.in",
        "page_status":          "live",
        "tier_priority":        ai.get("tier_priority", "2"),
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


def parse_args():
    args = sys.argv[1:]
    force_all   = "--all" in args
    limit       = None
    filter_set  = set()
    for i, a in enumerate(args):
        if a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
        if a == "--filter" and i + 1 < len(args):
            filter_set = {s.strip().lower() for s in args[i + 1].split(",")}
    return force_all, limit, filter_set


def main():
    force_all, limit, filter_set = parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set.")
        print("  Get your key at https://console.anthropic.com/settings/keys")
        print("  Then run:  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    print("Fetching ODOP sheet...")
    all_rows = fetch_sheet()
    print(f"Loaded {len(all_rows)} rows from sheet")

    # Deduplicate: keep first occurrence per (state, district) pair
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

    print(f"Unique districts: {len(unique_rows)}")

    cache  = {} if force_all else load_cache()
    client = anthropic.Anthropic()

    # Separate rows that need AI enrichment from already-cached ones
    to_enrich = [
        (idx, key, row) for idx, key, row in unique_rows
        if key not in cache
        and (not filter_set or row.get("District", "").strip().lower() in filter_set)
    ]

    print(f"Cached: {len(unique_rows) - len(to_enrich)}  |  To enrich: {len(to_enrich)}"
          + (f"  |  Limit: {limit}" if limit else ""))
    if not force_all and not filter_set and to_enrich:
        print(f"  Using claude-haiku — estimated {len(to_enrich[:limit or len(to_enrich)])} API calls\n")

    newly_enriched = 0
    cap = min(limit or len(to_enrich), len(to_enrich))
    for idx, key, row in to_enrich:
        if limit is not None and newly_enriched >= limit:
            print(f"\n  Reached --limit {limit}. Run again to continue.")
            break
        district = row.get("District", "").strip()
        state    = row.get("State", "").strip()
        print(f"  [{newly_enriched+1}/{cap}] {district}, {state}...", end=" ", flush=True)
        try:
            ai_data = call_claude(client, row)
            cache[key] = ai_data
            save_cache(cache)
            newly_enriched += 1
            print("✓")
        except anthropic.AuthenticationError:
            print("\n\nERROR: Invalid or missing ANTHROPIC_API_KEY.")
            print("  Set it with:  export ANTHROPIC_API_KEY=sk-ant-...")
            sys.exit(1)
        except Exception as e:
            print(f"SKIP ({type(e).__name__}: {e})")
        time.sleep(0.3)

    # Build CSV from all cached rows (preserves full dataset across runs)
    csv_rows = []
    added    = set()
    for idx, key, row in unique_rows:
        if key in cache and key not in added:
            csv_rows.append(build_row(row, cache[key], idx))
            added.add(key)

    write_csv(csv_rows)
    print(f"\n✅ {OUT_CSV.name} written — {len(csv_rows)} districts, {newly_enriched} newly enriched")
    if csv_rows:
        print("   Run `python3 build.py` to rebuild the site")


if __name__ == "__main__":
    main()
