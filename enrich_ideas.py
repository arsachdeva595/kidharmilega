#!/usr/bin/env python3
"""
enrich_ideas.py — Business Ideas Enrichment Pipeline

Stage 1 (scraping): Google Trends, Reddit, city markets
Stage 2 (AI):       Claude Haiku generates 25+ structured fields per idea
                    — FAQs, 6-step roadmap, opportunity score, schemes, success story

Run: python3 enrich_ideas.py              # AI generation only (default)
     python3 enrich_ideas.py --modules trends,reddit,markets  # scraping only
     python3 enrich_ideas.py --all        # scraping + AI
     python3 enrich_ideas.py --force      # re-generate everything from scratch
     python3 enrich_ideas.py --ideas "online-thrift-shop,driving-instructor"

Output: data/ideas_enrichment_cache.json
"""

import anthropic, csv, json, time, re, sys, os, urllib.parse
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR  = Path(__file__).parent
DATA_DIR  = BASE_DIR / "data"
CACHE_FILE = DATA_DIR / "ideas_enrichment_cache.json"

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_csv(path):
    if not path.exists(): return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def load_cache():
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}

def save_cache(cache):
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ Cache saved → {CACHE_FILE} ({len(cache)} ideas)")

def slug(t):
    return re.sub(r"[^a-z0-9-]", "", re.sub(r"\s+", "-", str(t).lower().strip()))

def safe_get(url, headers=None, timeout=10):
    """HTTP GET with retry, returns response text or None."""
    import urllib.request, urllib.error, ssl
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; KidharMilega/1.0)"}
    # Build SSL context — try certifi first, fall back to unverified (read-only public APIs)
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  ⚠ GET {url[:60]}... → {e}")
        return None


# ── Module 1: Google Trends (pytrends) ────────────────────────────────────────

def fetch_trends(keyword, geo="IN", retries=3):
    """Return list of 12 monthly interest values for keyword in India."""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        print("  ℹ pytrends not installed. pip3 install pytrends")
        return []
    for attempt in range(retries):
        try:
            pt = TrendReq(hl="en-IN", tz=330, timeout=(10, 25))
            pt.build_payload([keyword], cat=0, timeframe="today 12-m", geo=geo)
            df = pt.interest_over_time()
            if df.empty:
                return []
            monthly = df[keyword].resample("ME").mean().tolist()
            return [round(v, 1) for v in monthly[-12:]]
        except Exception as e:
            msg = str(e)
            if "429" in msg and attempt < retries - 1:
                wait = 30 * (attempt + 1)
                print(f"  ⚠ Trends 429 — waiting {wait}s before retry {attempt+2}/{retries}...")
                time.sleep(wait)
            else:
                print(f"  ⚠ Trends error for '{keyword}': {e}")
                return []
    return []


# ── Module 2: Reddit public API ───────────────────────────────────────────────

REDDIT_SUBS = ["StartUpIndia", "IndiaInvestments", "IndianStartups", "india"]

def fetch_reddit_stories(idea_title, max_posts=3):
    """Search Reddit public JSON API for success stories about the idea."""
    query = f"{idea_title} India business"
    results = []
    for sub in REDDIT_SUBS[:2]:
        url = (
            f"https://www.reddit.com/r/{sub}/search.json"
            f"?q={urllib.parse.quote(query)}&limit=5&sort=relevance&t=year"
        )
        try:
            text = safe_get(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            })
            if not text: continue
            data = json.loads(text)
            for post in data.get("data", {}).get("children", []):
                pd = post.get("data", {})
                title = pd.get("title", "")
                score = pd.get("score", 0)
                url_p = f"https://reddit.com{pd.get('permalink','')}"
                selftext = pd.get("selftext","")[:300]
                if score > 5 and title:
                    results.append({
                        "title": title,
                        "snippet": selftext or title,
                        "url": url_p,
                        "score": score,
                        "source": "reddit"
                    })
            if results: break
            time.sleep(2)
        except Exception as e:
            print(f"  ⚠ Reddit error: {e}")
    return results[:max_posts]


# ── Module 3: Instagram oEmbed ─────────────────────────────────────────────────

def fetch_instagram_examples(idea_title):
    """
    Returns placeholder Instagram examples.
    Instagram's oEmbed requires login tokens; use manually curated handles.
    This stub returns empty and can be populated manually in the cache.
    """
    return []


# ── Module 4: JustDial competitor count ───────────────────────────────────────

def fetch_justdial_count(idea_title, city):
    """Scrape JustDial to count businesses matching idea_title in city."""
    try:
        import urllib.parse
        query = urllib.parse.quote(idea_title)
        city_slug = city.lower().replace(" ", "-")
        url = f"https://www.justdial.com/{city_slug}/{query}"
        text = safe_get(url)
        if not text: return None
        # Look for result count pattern
        m = re.search(r'(\d[\d,]+)\s*(?:result|business|listing)', text, re.I)
        if m:
            return int(m.group(1).replace(",", ""))
    except Exception as e:
        print(f"  ⚠ JustDial error: {e}")
    return None


# ── Module 5: Wholesale market lookup (static) ────────────────────────────────

CITY_MARKETS = {
    "delhi":   [
        {"name": "Azadpur Mandi",    "location": "North Delhi",  "speciality": "Vegetables, Fruits"},
        {"name": "INA Market",        "location": "South Delhi",  "speciality": "Organic, Imported goods"},
        {"name": "Khari Baoli",       "location": "Old Delhi",    "speciality": "Spices, Dry Goods"},
        {"name": "Sadar Bazaar",      "location": "Central Delhi","speciality": "Household goods, FMCG"},
    ],
    "mumbai":  [
        {"name": "Crawford Market",  "location": "South Mumbai", "speciality": "Fruits, Vegetables, Dry fruits"},
        {"name": "Dharavi",          "location": "Central Mumbai","speciality": "Leather goods, Recycled materials"},
        {"name": "Masjid Bunder",    "location": "South Mumbai", "speciality": "Spices, Textiles, Chemicals"},
    ],
    "bangalore": [
        {"name": "KR Market",        "location": "Central Bengaluru","speciality": "Flowers, Vegetables, Fruits"},
        {"name": "Shivajinagar",     "location": "Shivajinagar",     "speciality": "Electronics, Clothes"},
    ],
    "chennai": [
        {"name": "Koyambedu",        "location": "Koyambedu",    "speciality": "Fruits, Vegetables"},
        {"name": "Sowcarpet",        "location": "George Town",  "speciality": "FMCG, Groceries, Textiles"},
    ],
    "hyderabad": [
        {"name": "Begum Bazaar",     "location": "Old City",     "speciality": "Spices, Groceries, Sarees"},
        {"name": "Sultan Bazaar",    "location": "Koti",         "speciality": "Electronics, Clothes"},
    ],
    "kolkata": [
        {"name": "Burrabazar",       "location": "Central Kolkata","speciality": "Wholesale groceries, FMCG"},
        {"name": "Hatibagan",        "location": "North Kolkata", "speciality": "Clothes, Sarees"},
    ],
    "pune": [
        {"name": "Market Yard",      "location": "Gultekdi",     "speciality": "Agricultural produce"},
        {"name": "Kasba Peth",       "location": "Old Pune",     "speciality": "Clothes, Electronics"},
    ],
    "ahmedabad": [
        {"name": "Manek Chowk",      "location": "Old City",     "speciality": "Jewellery, Vegetables"},
        {"name": "Raipur Market",    "location": "Raipur Gate",  "speciality": "Textiles, Fabrics"},
    ],
    "jaipur": [
        {"name": "Johari Bazaar",    "location": "Walled City",  "speciality": "Jewellery, Gems"},
        {"name": "Bapu Bazaar",      "location": "Walled City",  "speciality": "Clothes, Handicrafts"},
    ],
    "lucknow": [
        {"name": "Aminabad Market",  "location": "Central Lucknow","speciality": "Chikankari, Clothes, FMCG"},
        {"name": "Alambagh",         "location": "South Lucknow","speciality": "Electronics, Furniture"},
    ],
}

def get_city_markets(city_name):
    key = city_name.lower()
    return CITY_MARKETS.get(key, CITY_MARKETS.get("delhi"))  # fallback to Delhi


# ── AI Generation (Stage 2) ───────────────────────────────────────────────────

IDEAS_AI_PROMPT = """\
You are a business researcher for KidharMilega — India's startup discovery platform.

A real first-generation Indian founder is going to read this page and decide whether to start this business. Make every field specific, honest, and actionable.

KNOWN DATA about this idea:
Title: {title}
Description: {desc}
Target Audience: {audience}
Revenue Model: {revenue}
Typical Margins: {margins}
Investment Required: {investment}
Daily Operations: {daily}
Key Stakeholders: {stakeholders}
Sourcing/Supplies: {supplies}
Marketing Strategies: {marketing}
Content Ideas: {content}
Personality Fit: {mbti} — {mbti_why}

CONTENT RULES (follow strictly):
1. NEVER use: vibrant, testament, tapestry, realm, burgeoning, bustling, thriving, rich heritage, embark, delve, unlock, showcase, elevate, leverage, foster, beacon, kaleidoscope.
2. Steps must read like a WhatsApp message from a founder — plain, specific, zero fluff. Name real platforms, real markets, real costs.
3. Step 1 must be doable at ₹0 this week — call someone, research online, visit a place, watch videos.
4. suitable_for must name a real person type with capital range: "Someone with ₹50K–2L savings and 3 months to experiment" — not "passionate entrepreneurs".
5. idea_hook: 3 dense sentences for AI search indexing. Include market size data, India context, who this is for, and why now.
6. alert_stat: one striking number about this business category in India. E.g. "India's online thrift market is growing 35% YoY — Depop and ThredUp don't exist here yet."
7. All scheme names must be real central schemes: PMEGP, MUDRA Loan, Startup India, PM Vishwakarma, Stand-Up India, Atal Innovation Mission.
8. FAQ answers must be plain, honest. If something is risky, say so.
9. opportunity_score: integer 1–10. Base it on: market size (3pts), low competition (2pts), low investment needed (2pts), digital/remote-friendly (2pts), India-specific tailwind (1pt).
10. Return ONLY valid JSON. No markdown. No prose before or after.

Return a JSON object with ALL of these fields:

{{
  "opportunity_score": "integer 1-10",
  "alert_stat": "one striking statistic sentence about this business in India — specific numbers",
  "idea_hook": "3 dense sentences: who this is for, India market context, why now — information-dense for AI indexing",
  "suitable_for": "specific founder profile with capital range and time commitment",
  "not_suitable_for": "who should skip this — be honest about the hard parts",
  "min_setup_cost": "digits only — realistic minimum in INR",
  "max_setup_cost": "digits only — realistic maximum in INR",
  "breakeven_timeline": "e.g. 4-8 months",
  "revenue_stream_1": "primary channel — specific platform or buyer type",
  "revenue_stream_2": "second channel — specific",
  "revenue_stream_3": "third channel — specific",
  "revenue_stream_4": "fourth channel or empty string",
  "revenue_stream_5": "fifth channel or empty string",
  "step_1_learn": "Zero-cost action this week: watch X, call Y, visit Z — free, doable in 2 days",
  "step_2_setup": "What to register/set up first — Udyam, GST, FSSAI etc. Exact cost and time.",
  "step_3_source": "Where exactly to source in India — market names, platforms, MOQ, cost range",
  "step_4_brand": "Branding steps — name, logo, Instagram handle, packaging. Cost range.",
  "step_5_sell": "First sale: which exact platform, first batch size, expected first-month revenue range",
  "step_6_scale": "How to grow: what changes at ₹1L/month revenue, who to hire first, where to expand",
  "relevant_central_scheme_1": "Scheme name — exact benefit: e.g. PMEGP — up to 35% subsidy on project cost up to ₹25L",
  "relevant_central_scheme_2": "Scheme name — exact benefit",
  "success_story_name": "Real Indian business or founder name in this category (leave empty string if unsure)",
  "success_story_desc": "What they built and how — 1-2 sentences, specific numbers if known",
  "success_story_cost": "Their reported setup cost in INR or empty string",
  "faq_1": "Kitna paisa chahiye shuru karne ke liye?|||{{specific cost range for this idea}}",
  "faq_2": "Kya experience chahiye?|||{{honest answer — what skills actually matter}}",
  "faq_3": "Government se kya help milti hai?|||{{specific scheme names and amounts}}",
  "faq_4": "Pehla customer kahan se milega?|||{{exact first customer acquisition strategy}}",
  "faq_5": "Is business mein competition kitna hai?|||{{honest competition assessment for India}}",
  "faq_6": "Agar flop hua toh?|||{{honest downside — what you lose, how to exit}}"
}}"""


def parse_json_response(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > start:
        text = text[start:end]
    return json.loads(text)


def generate_idea_content(client, idea):
    """Stage 2: Claude Haiku generates 25+ structured fields for one idea."""
    prompt = IDEAS_AI_PROMPT.format(
        title      = idea.get("title", ""),
        desc       = idea.get("desc", ""),
        audience   = idea.get("audience", ""),
        revenue    = idea.get("revenue", ""),
        margins    = idea.get("margins", ""),
        investment = idea.get("investment", ""),
        daily      = idea.get("daily", ""),
        stakeholders = idea.get("stakeholders", ""),
        supplies   = idea.get("supplies", ""),
        marketing  = idea.get("marketing", ""),
        content    = idea.get("content", ""),
        mbti       = idea.get("mbti", ""),
        mbti_why   = idea.get("mbti_why", ""),
    )
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system="You are a business data researcher. Return only valid JSON — no markdown, no prose.",
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_json_response(msg.content[0].text)


# ── Main enrichment loop ───────────────────────────────────────────────────────

TOP_CITIES = [
    "delhi","mumbai","bangalore","chennai","hyderabad",
    "pune","ahmedabad","kolkata","jaipur","lucknow",
    "surat","indore","bhopal","nagpur","visakhapatnam",
    "kochi","chandigarh","coimbatore","vadodara","agra",
    "rajkot","patna","guwahati","thiruvananthapuram",
    "srinagar","amritsar","jodhpur","ranchi","raipur",
]

def enrich_scraping(ideas, cache, force=False, modules=None):
    """Stage 1: scraping modules — Trends, Reddit, city markets."""
    if modules is None:
        modules = []
    total = len(ideas)

    for i, idea in enumerate(ideas):
        title = idea.get("title", "").strip()
        isl   = slug(title)
        if not title:
            continue

        print(f"\n[{i+1}/{total}] {title}")

        if isl not in cache:
            cache[isl] = {}
        entry = cache[isl]

        if "trends" in modules:
            if force or "trends_monthly" not in entry:
                print("  → Fetching Google Trends...")
                vals = fetch_trends(title)
                entry["trends_monthly"] = vals
                time.sleep(3)
            else:
                print("  ✓ Trends cached")

        if "reddit" in modules:
            if force or "reddit_stories" not in entry:
                print("  → Fetching Reddit stories...")
                try:
                    import urllib.parse
                    stories = fetch_reddit_stories(title)
                    entry["reddit_stories"] = stories
                except Exception as e:
                    print(f"  ⚠ Reddit: {e}")
                    entry["reddit_stories"] = []
                time.sleep(2)
            else:
                print("  ✓ Reddit cached")

        if "markets" in modules:
            if force or "city_sourcing" not in entry:
                print("  → Building city market data...")
                entry["city_sourcing"] = {
                    city: {"markets": get_city_markets(city), "competitor_count": None}
                    for city in TOP_CITIES
                }
            else:
                print("  ✓ Markets cached")

        if "justdial" in modules:
            print("  → Fetching JustDial counts (top 5 cities)...")
            for city in TOP_CITIES[:5]:
                entry.setdefault("city_sourcing", {}).setdefault(city, {"markets": get_city_markets(city)})
                entry["city_sourcing"][city]["competitor_count"] = fetch_justdial_count(title, city)
                time.sleep(4)

        cache[isl] = entry
        save_cache(cache)

    return cache


def enrich_ai(ideas, cache, force=False):
    """Stage 2: Claude Haiku generates 25+ structured fields per idea."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set. Add it to your .env file.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    total  = len(ideas)
    done   = 0

    for i, idea in enumerate(ideas):
        title = idea.get("title", "").strip()
        isl   = slug(title)
        if not title:
            continue

        entry = cache.get(isl, {})

        # Skip if already AI-enriched and not forcing
        if not force and entry.get("opportunity_score"):
            print(f"  [{i+1}/{total}] {title} — ✓ cached")
            continue

        print(f"  [{i+1}/{total}] {title} ...", end=" ", flush=True)
        try:
            ai = generate_idea_content(client, idea)
            # Merge into existing entry (preserves scraping data)
            entry.update(ai)
            cache[isl] = entry
            save_cache(cache)
            score = ai.get("opportunity_score", "?")
            print(f"✓  score={score}/10")
            done += 1
        except anthropic.AuthenticationError:
            print("\n❌ Invalid ANTHROPIC_API_KEY")
            sys.exit(1)
        except Exception as e:
            print(f"SKIP ({type(e).__name__}: {e})")

        time.sleep(0.5)

    print(f"\n✅ AI enrichment done. {done} ideas generated, {len(cache)} total in cache.")
    return cache


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Enrich business ideas with AI + public data")
    parser.add_argument("--force",   action="store_true", help="Re-generate even if cached")
    parser.add_argument("--all",     action="store_true", help="Run scraping modules + AI generation")
    parser.add_argument("--modules", default="",
                        help="Scraping modules to run (comma-separated): trends,reddit,markets,justdial")
    parser.add_argument("--ideas",   default=None,
                        help="Comma-separated idea slugs to process (default: all)")
    args = parser.parse_args()

    ideas_csv = DATA_DIR / "business_ideas.csv"
    if not ideas_csv.exists():
        print(f"❌ {ideas_csv} not found.")
        sys.exit(1)

    all_ideas = load_csv(ideas_csv)

    if args.ideas:
        wanted    = set(args.ideas.split(","))
        all_ideas = [i for i in all_ideas if slug(i.get("title", "")) in wanted]

    cache   = load_cache()
    modules = [m.strip() for m in args.modules.split(",") if m.strip()]

    # --all enables default scraping modules too
    if args.all and not modules:
        modules = ["trends", "reddit", "markets"]

    print(f"\n⚡ Business Ideas Enrichment")
    print(f"   Ideas: {len(all_ideas)}  |  Cache: {CACHE_FILE}")
    print(f"   Scraping modules: {modules or 'none'}")
    print(f"   AI generation: yes  |  Force: {args.force}")
    print("   Ctrl+C to stop — progress saved after each idea.\n")

    # Stage 1: scraping (only if modules requested)
    if modules:
        cache = enrich_scraping(all_ideas, cache, force=args.force, modules=modules)

    # Stage 2: AI generation (always runs unless only --modules passed with no AI intent)
    cache = enrich_ai(all_ideas, cache, force=args.force)

    print(f"\nRun 'python3 build.py' to rebuild idea pages with enriched content.")
