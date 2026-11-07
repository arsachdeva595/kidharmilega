"""Budget Matcher tool (/tools/budget-matcher/).

"₹50,000 hain, kya business karu?" The user enters how much of their own money they can put in,
their state, whether they will take a loan, and (optionally) the kind of work they like. The page
ranks the 787 ODOP district businesses on KidharMilega by fit:
  - ideas they can start with their own money (min setup cost <= budget)
  - ideas they can reach with a PMEGP loan, where own money only has to cover 10% of the project
    (5% for special categories), up to the ₹50 lakh manufacturing ceiling

Setup cost, margins, break-even and raw materials come from data/districts.csv (the same fields the
product pages show). Rules run in the browser (tools_src/budget-matcher/app.js). The lead goes to the
same Google Sheet as the other tools (event = budget_match).
"""
import json, re, shutil, hashlib
from pathlib import Path

import supplier_finder as sf

BASE_DIR = Path(__file__).parent
SRC_DIR = BASE_DIR / "tools_src" / "budget-matcher"
TOOL_PATH = "/tools/budget-matcher/"
REVIEWED = "November 2026"

# PMEGP (December 2023 guidelines), same figures as scheme_facts.PMEGP_SHORT.
PMEGP = {
    "ownGen": 10, "ownSpecial": 5,          # own contribution, % of project
    "subGenUrban": 15, "subGenRural": 25,   # margin-money subsidy, % of project
    "subSpUrban": 25, "subSpRural": 35,
    "capMfg": 50, "capService": 20,         # max project cost, ₹ lakh
}
# Used only for the rough EMI line. Stated on the page as an assumption.
LOAN_RATE = 11.0
LOAN_YEARS = 5

SECTORS = [
    ("food", "Food, spices & farm produce"),
    ("textile", "Textiles, handloom & garments"),
    ("craft", "Handicrafts, art & home décor"),
    ("industry", "Metal, engineering & industrial"),
]
_KW = {
    "textile": r"silk|saree|sari|textile|garment|cloth|cotton|handloom|powerloom|weav|yarn|shawl|carpet|\bdari|durr|\brug|"
               r"embroider|chikan|zari|zardozi|bandhani|ikat|kalamkari|hosiery|apparel|jute|wool|towel|bedsheet|"
               r"made ?ups|denim|jean|knit|khadi|rumal|phulkari|applique|tie.?dye|fabric|dress|chunri|lungi|mat\b|mats\b|"
               r"print|pashmina|ikkat|booti|doria|kosa|crochet|kasheeda|risha|fanek|phee|gollabama|nettle|fibre|coir",
    "craft": r"craft|art\b|arts\b|painting|toy|bamboo|cane|wood|terracotta|pottery|clay|brass|bell metal|dokra|"
             r"stone|marble|jewel|gem|bangle|lac\b|bead|leather|footwear|jutti|mojari|shoe|musical|incense|agarbatti|"
             r"moonj|sikki\b|basket|idol|sculpt|carving|ceramic|glass|bindi|tikuli|aipan|mask|perfume|attar|candle|"
             r"handicraft|decor|furniture|horn|conch|kalash|lamp|metal ware|utensil|copper|bronze|bidri|zinc|"
             r"chitra|veena|wall hanging|golden grass|leaf based|leaf sheath|sital pati|silver|filigree|pearl|gold|"
             r"wicker|willow|resin|teak",
    "industry": r"engineering|machin|auto|tractor|steel|iron|alumin|plastic|rubber|chemical|pharma|cement|brick|"
                r"refractor|tile|sanitary|electric|electronic|fabricat|forg|foundr|casting|implement|pump|motor|"
                r"tool|hardware|lock|scissor|knife|cutlery|sports|surgical|paper|packag|granite|quartz|mineral|"
                r"feldspar|mica|coal|fmcg|soap|detergent|polymer|pipe|wire|cable|bicycle|component|ship|boat|esdm|"
                r"equipment|fuller|bentonite",
    "food": r"food|spice|chilli|chili|mirch|turmeric|ginger|garlic|onion|rice|wheat|millet|ragi|maize|pulse|dal\b|"
            r"oil|mango|banana|pineapple|orange|apple|litchi|guava|amla|aamla|kiwi|lemon|jackfruit|fruit|vegetable|"
            r"tea\b|coffee|honey|jaggery|gur\b|sugar|cashew|walnut|almond|coconut|cardamom|pepper|cinnamon|clove|"
            r"namkeen|sweet|pickle|papad|bakery|biscuit|dairy|milk|ghee|paneer|fish|marine|prawn|shrimp|poultry|"
            r"meat|egg|mushroom|soya|groundnut|peanut|mustard|makhana|potato|tomato|seed|grain|agri|agro|herb|"
            r"tamarind|hing|asafoetida|saffron|kesar|date|tapioca|sago|cilantro|coriander|jeera|cumin|flower|"
            r"floricultur|aromatic|medicinal|forest produce|beverage|juice|pulp|apricot|areca|gram\b|chilly|corn|"
            r"chikoo|sapota|feni|gooseberry|grape|raisin|chicken|haladi|bean|kodo|kutki|mahua|mentha|menthol|"
            r"papaya|peas\b|pecan|strawberr|melon|toor|daal|chura|mithai|ayurved",
}


# Food words that would otherwise trip a craft keyword ("cane" in sugarcane, "horn" in seabuckthorn).
_FOOD_FIRST = r"sugar|jaggery|cardamom|seabuckthorn|jholokia|grams|kholar|sonamukhi|mandarin|orange"
_CRAFT_FIRST = r"bidar|wooden|paper art"


def sector_of(product):
    t = (product or "").lower()
    if re.search(_FOOD_FIRST, t):
        return "food"
    if re.search(_CRAFT_FIRST, t):
        return "craft"
    for key in ("textile", "industry", "craft", "food"):
        if re.search(_KW[key], t):
            return key
    return "other"


def _num(v):
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _cut(s, n):
    s = re.sub(r"\s+", " ", (s or "")).strip()
    if len(s) <= n:
        return s
    s = s[:n].rsplit(" ", 1)[0].rstrip(",;:—-")
    return s + "…"


def _first_sentence(s, n=220):
    s = re.sub(r"\s+", " ", (s or "")).strip()
    m = re.match(r"(.+?[.!?])(\s|$)", s)
    return _cut(m.group(1) if m else s, n)


def build_data(districts, product_page_slug):
    """Compact rows for the browser. Skips districts with no usable setup cost."""
    out = []
    for d in districts:
        if d.get("page_status", "live") != "live":
            continue
        lo, hi = _num(d.get("min_setup_cost")), _num(d.get("max_setup_cost"))
        if not lo or lo <= 0:
            continue
        if not hi or hi < lo:
            hi = lo
        prod = d.get("odop_product_name", "") or ""
        codes = sf.odop_hsn_codes(prod)
        out.append({
            "p": prod,
            "d": d.get("district_name", ""),
            "s": d.get("state", ""),
            "u": product_page_slug(d),
            "lo": lo, "hi": hi,
            "mw": d.get("gross_margin_wholesale", "") or "",
            "md": d.get("gross_margin_d2c", "") or "",
            "be": d.get("breakeven_timeline", "") or "",
            "x": (d.get("export_potential", "") or "").strip(),
            "sc": _num(d.get("opportunity_score")) or 0,
            "gi": 1 if (d.get("odop_gi_tag", "") or "").strip().lower().startswith("y") else 0,
            "c": sector_of(prod),
            "r": _cut(d.get("odop_raw_materials", ""), 110),
            "a": _first_sentence(d.get("alert_stat", "") or d.get("famous_for_1_line", ""), 200),
            "f": _cut(d.get("suitable_for", ""), 180),
            "h": codes[0] if codes else "",
        })
    return out


def config():
    return {
        "leadEndpoint": sf.LEAD_ENDPOINT,
        "bookCallUrl": sf.BOOK_CALL_URL,
        "reviewed": REVIEWED,
        "pmegp": PMEGP,
        "loanRate": LOAN_RATE, "loanYears": LOAN_YEARS,
        "sectors": dict(SECTORS),
        "paths": {
            "product": "/products/", "supplier": sf.TOOL_PATH, "scheme": "/tools/scheme-finder/",
        },
    }


def _version(cfg, data):
    h = hashlib.sha1()
    for f in ("app.js", "style.css"):
        h.update((SRC_DIR / f).read_bytes())
    h.update((sf.SRC_DIR / "style.css").read_bytes())
    h.update(json.dumps([cfg, data], sort_keys=True).encode())
    return h.hexdigest()[:10]


BUDGETS = [(25000, "₹25k"), (50000, "₹50k"), (100000, "₹1 lakh"), (200000, "₹2 lakh"),
           (500000, "₹5 lakh"), (1000000, "₹10 lakh"), (2500000, "₹25 lakh")]


def build_page(head, nav, footer, esc, p, data, version):
    cfg = config()
    states = sorted({r["s"] for r in data})
    n = len(data)
    title = "₹50,000 Mein Kaunsa Business Karu? Free Budget Business Finder (787 Districts) | KidharMilega"
    desc = (f"Enter your budget and state. Get real business ideas from {n} Indian districts that fit your money, "
            f"with setup cost, margins, break-even, and how far a PMEGP loan can stretch it. Free.")
    ld = {
        "@context": "https://schema.org", "@type": "WebApplication", "name": "KidharMilega Budget Matcher",
        "url": "https://kidharmilega.in" + TOOL_PATH, "applicationCategory": "BusinessApplication",
        "operatingSystem": "Any", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "INR"},
        "description": desc,
    }
    extra = (f'<link rel="stylesheet" href="{p(sf.TOOL_PATH + "style.css")}?v={version}">'
             f'<link rel="stylesheet" href="{p(TOOL_PATH + "style.css")}?v={version}">'
             f'<script type="application/ld+json">{json.dumps(ld)}</script>')
    chips = "".join(f'<button type="button" class="sf-chip bm-amt" data-v="{v}">{esc(l)}</button>' for v, l in BUDGETS)
    sector_chips = "".join(f'<label class="bm-pill"><input type="checkbox" name="sector" value="{k}"><span>{esc(l)}</span></label>' for k, l in SECTORS)
    state_opts = '<option value="">Anywhere in India</option>' + "".join(f'<option>{esc(s)}</option>' for s in states)
    return head(title, desc, TOOL_PATH, extra_head=extra) + nav("tools") + f'''
<main class="sf bm"><div class="container">
  <header class="page-header sf-header">
    <div class="section-label">Free tool · Budget Matcher</div>
    <h1 class="page-header-title">Itne paise mein<br><em>kaunsa business?</em></h1>
    <p class="page-header-sub">Tell us how much money you have. We match it against real, district-level businesses from {n} districts in India, with setup cost, margins and break-even, and show how far a government PMEGP loan can stretch your budget.</p>
    <ol class="sf-how" aria-label="How it works">
      <li><span>1</span>Your budget</li>
      <li><span>2</span>Where and what</li>
      <li><span>3</span>Get your matches</li>
    </ol>
  </header>

  <form class="sf-form" id="bmForm" autocomplete="off" novalidate>
    <section class="sf-step">
      <h2 class="sf-step__title"><span class="sf-step__num">1</span>Your money</h2>
      <label class="sf-label" for="bmBudget">How much of your own money can you put in? <span class="sf-opt">(₹)</span></label>
      <input class="sf-input" id="bmBudget" type="number" inputmode="numeric" min="0" step="1000" placeholder="e.g. 50000">
      <div class="sf-chips bm-amts" role="group" aria-label="Quick amounts">{chips}</div>
      <p class="sf-hint" id="bmBudgetWords"></p>
      <fieldset class="scf-radios bm-loan"><legend class="sf-label">Are you open to a bank loan?</legend>
        <label class="scf-radio"><input type="radio" name="loan" value="yes" checked><span>Yes, show what a PMEGP loan can add</span></label>
        <label class="scf-radio"><input type="radio" name="loan" value="no"><span>No, only my own money</span></label>
      </fieldset>
      <div id="bmLoanBox">
        <div class="sf-row">
          <div>
            <label class="sf-label" for="bmArea">Where will the unit be?</label>
            <select class="sf-input" id="bmArea"><option value="urban">Town or city</option><option value="rural">Village / rural</option></select>
          </div>
          <div>
            <label class="sf-label" for="bmSpecial">Category</label>
            <select class="sf-input" id="bmSpecial"><option value="0">General</option><option value="1">Woman, SC, ST, OBC, minority, ex-serviceman, person with disability, NE or hill area</option></select>
          </div>
        </div>
        <p class="sf-hint">PMEGP asks for less of your own money (5% instead of 10%) and gives a bigger subsidy to these groups.</p>
      </div>
    </section>

    <section class="sf-step">
      <h2 class="sf-step__title"><span class="sf-step__num">2</span>Where and what <span class="sf-opt">(optional)</span></h2>
      <label class="sf-label" for="bmState">Your state</label>
      <select class="sf-input" id="bmState">{state_opts}</select>
      <label class="scf-check"><input type="checkbox" id="bmOnlyState"><span>Only show businesses in my state</span></label>
      <fieldset class="scf-checks bm-sectors"><legend class="sf-label">Kind of work you'd enjoy <span class="sf-opt">(tick any, or leave blank for all)</span></legend>
        {sector_chips}
      </fieldset>
      <label class="scf-check"><input type="checkbox" id="bmExport"><span>I want to export one day</span></label>
    </section>

    <div class="sf-submit">
      <button class="btn btn-primary btn-lg" type="submit">Show businesses for my budget <span class="btn__arrow" aria-hidden="true">&rarr;</span></button>
      <p class="sf-error" id="bmError" role="alert"></p>
    </div>
  </form>

  <div class="sf-gate" id="bmGate" hidden>
    <div class="sf-gate__card" role="dialog" aria-modal="true" aria-labelledby="bmGateTitle">
      <button class="sf-gate__close" type="button" id="bmGateClose" aria-label="Close">&times;</button>
      <h2 id="bmGateTitle">Your matches are ready</h2>
      <p>Where should we send new district ideas and scheme updates for your budget?</p>
      <form id="bmGateForm" novalidate>
        <label class="sf-label" for="bmEmail">Email</label>
        <input class="sf-input" id="bmEmail" type="email" inputmode="email" autocomplete="email" required placeholder="you@example.com">
        <label class="sf-label" for="bmPhone">WhatsApp number <span class="sf-opt">(optional)</span></label>
        <input class="sf-input" id="bmPhone" type="tel" inputmode="tel" autocomplete="tel" placeholder="10-digit mobile">
        <p class="sf-error" id="bmGateError" role="alert"></p>
        <button class="btn btn-primary" type="submit" style="width:100%">Show my matches</button>
        <p class="sf-fine">By continuing you agree to our <a href="{p('/terms-of-service/')}">terms</a>. No spam.</p>
      </form>
    </div>
  </div>

  <section class="scf-report bm-report" id="bmReport" hidden aria-live="polite"></section>
  <noscript><p class="sf-error">This tool needs JavaScript turned on.</p></noscript>
</div></main>
<script>window.BM_CONFIG={json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")};window.BM_BASE={json.dumps(p(""))};window.BM_DATA="__BM_DATA_URL__";</script>
<script src="{p(TOOL_PATH + "app.js")}?v={version}" defer></script>
''' + footer() + "</body></html>"


def write_budget_matcher(dist_dir, districts, product_page_slug, head, nav, footer, esc, p):
    out = Path(dist_dir) / "tools" / "budget-matcher"
    out.mkdir(parents=True, exist_ok=True)
    data = build_data(districts, product_page_slug)
    v = _version(config(), data)
    (out / "data.json").write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    for f in ("app.js", "style.css"):
        shutil.copy(SRC_DIR / f, out / f)
    html = build_page(head, nav, footer, esc, p, data, v).replace("__BM_DATA_URL__", p(TOOL_PATH + "data.json") + "?v=" + v)
    (out / "index.html").write_text(html, encoding="utf-8")
    return len(data)
