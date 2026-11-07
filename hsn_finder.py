"""HSN Code Finder tool (/tools/hsn-code-finder/).

Type a product in plain words (Hindi words like "achar", "haldi", "dari" work) or part of a code. Pick a line
and see, with no signup:
  - the 8-digit Indian HSN code, its 6-digit international HS code, heading, chapter and section
  - how many digits to print on a GST invoice, and a link to CBIC's official GST rate page
    (we do not ship GST rates: they changed in September 2025 and we have no checked rate table)
  - India's exports of that HS6 code (UN Comtrade): last year's value, trend, top buyer countries
  - ODOP districts that make products under the same 4-digit heading
  - next steps: Supplier Finder, Export Buyer Finder, UK trade data, Budget Matcher

Everything reuses files other tools already publish: /tools/shared/hsn.json (+ hsn-search.js),
/tools/supplier-finder/districts.json and /tools/export-buyer-finder/in/<chapter>.json. So build.py must call
this after those writers. No lead capture.
"""
import json, re, shutil, hashlib
from collections import defaultdict
from pathlib import Path

import supplier_finder as sf
import export_buyer_finder as ebf

BASE_DIR = Path(__file__).parent
SRC_DIR = BASE_DIR / "tools_src" / "hsn-finder"
TOOL_PATH = "/tools/hsn-code-finder/"
GST_RATES_URL = "https://cbic-gst.gov.in/gst-goods-services-rates.html"
EXAMPLES = ["achar", "haldi", "bedsheet", "saree", "agarbatti", "leather bag", "jute bag", "terracotta",
            "namkeen", "honey", "dari", "brass"]


def _india_meta():
    path = ebf.DATASETS["in"]
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    chapters = sorted({c[:2] for c in data["hs6"]})
    return {"years": data["years"], "fetched": data["fetched"], "source": data["source"], "chapters": chapters,
            "partners": {k: ebf._country(v) for k, v in data["partners"].items()}}


def _odop_table(districts, product_page_slug, headings):
    """ODOP product → 4-digit headings, grouped by product name, for the crawlable list on the page."""
    rows = defaultdict(lambda: {"codes": [], "where": []})
    for d in districts:
        if (d.get("page_status") or "").lower() != "live":
            continue
        prod = (d.get("odop_product_name") or "").strip()
        codes = [c for c in sf.odop_hsn_codes(prod) if c in headings]
        if not prod or not codes:
            continue
        key = re.sub(r"\s+", " ", prod.lower())
        r = rows[key]
        r.setdefault("name", prod)
        for c in codes[:3]:
            if c not in r["codes"]:
                r["codes"].append(c)
        r["where"].append((d.get("district_name", ""), "/products/" + product_page_slug(d) + "/"))
    return sorted(rows.values(), key=lambda r: r["name"].lower())


def config(p, india):
    return {
        "hsnUrl": p(sf.SHARED_PATH + "hsn.json"),
        "districtsUrl": p(sf.TOOL_PATH + "districts.json"),
        "inBase": p(ebf.TOOL_PATH + "in/"),
        "india": india,
        "gstUrl": GST_RATES_URL,
        "paths": {"supplier": p(sf.TOOL_PATH), "export": p(ebf.TOOL_PATH),
                  "budget": p("/tools/budget-matcher/"), "base": p("")},
    }


def _version(cfg):
    h = hashlib.sha1()
    for f in (SRC_DIR / "app.js", SRC_DIR / "style.css", sf.SHARED_SRC / "hsn-search.js", sf.SRC_DIR / "style.css"):
        h.update(f.read_bytes())
    h.update(json.dumps(cfg, sort_keys=True).encode())
    return h.hexdigest()[:10]


def build_page(head, nav, footer, esc, p, cfg, table, headings):
    v = _version(cfg)
    title = "HSN Code Finder: Find the HSN Code for Any Product in Hindi or English (Free) | KidharMilega"
    desc = ("Type your product in simple words (achar, haldi, bedsheet, agarbatti) and get its 8-digit HSN code, "
            "the 6-digit export code, which ODOP districts make it, and where India exports it. Free, no signup.")
    ld = [{
        "@context": "https://schema.org", "@type": "WebApplication", "name": "KidharMilega HSN Code Finder",
        "url": "https://kidharmilega.in" + TOOL_PATH, "applicationCategory": "BusinessApplication",
        "operatingSystem": "Any", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "INR"},
        "description": desc,
    }, {
        "@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ],
    }]
    extra = (f'<link rel="stylesheet" href="{p(sf.TOOL_PATH + "style.css")}?v={v}">'
             f'<link rel="stylesheet" href="{p(TOOL_PATH + "style.css")}?v={v}">'
             + "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld))
    chips = "".join(f'<button type="button" class="sf-chip hf-ex" data-q="{esc(q)}">{esc(q)}</button>' for q in EXAMPLES)

    def trow(r):
        codes = ", ".join(f'<a href="?hsn={c}">{c}</a> <span>{esc(headings[c][:70])}</span>' for c in r["codes"])
        where = ", ".join(f'<a href="{p(u)}">{esc(n)}</a>' for n, u in r["where"][:4])
        more = f" +{len(r['where']) - 4} more" if len(r["where"]) > 4 else ""
        return f'<tr><th scope="row">{esc(r["name"])}</th><td class="hf-tcodes">{codes}</td><td>{where}{more}</td></tr>'

    faq_html = "".join(f'<details class="hf-faq"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in FAQ)
    return head(title, desc, TOOL_PATH, extra_head=extra) + nav("tools") + f'''
<main class="sf hf"><div class="container">
  <header class="page-header sf-header">
    <div class="section-label">Free tool · HSN Code Finder</div>
    <h1 class="page-header-title">Apne product ka<br><em>HSN code nikalo.</em></h1>
    <p class="page-header-sub">Type the product the way you'd say it: "achar", "haldi", "bedsheet", "agarbatti". Get the 8-digit HSN code for GST and shipping, the 6-digit code buyers abroad use, which districts make it, and where India sells it. No signup.</p>
  </header>

  <section class="sf-step hf-search">
    <label class="sf-label" for="hfInput">Product name or code</label>
    <div class="sf-combo">
      <input class="sf-input" id="hfInput" type="text" inputmode="search" placeholder="e.g. achar, jute bag or 0910" aria-autocomplete="list" aria-controls="hfList" aria-expanded="false" role="combobox" autocomplete="off">
      <ul class="sf-list" id="hfList" role="listbox" hidden></ul>
    </div>
    <p class="sf-hint" id="hfStatus" aria-live="polite">Loading 12,000+ HSN codes…</p>
    <div class="sf-suggest"><p class="sf-suggest__label">Try one:</p><div class="sf-chips">{chips}</div></div>
  </section>

  <section class="hf-result" id="hfResult" hidden aria-live="polite"></section>

  <section class="hf-sec">
    <h2 class="hf-h2">HSN codes for ODOP products</h2>
    <p class="sf-hint">The 4-digit HSN heading for each One District One Product item on KidharMilega. Tap a code to see every 8-digit line under it. Headings are our mapping: always pick the exact 8-digit line for your invoice.</p>
    <div class="hf-tablewrap"><table class="hf-table">
      <thead><tr><th scope="col">Product</th><th scope="col">HSN heading</th><th scope="col">Made in</th></tr></thead>
      <tbody>{"".join(trow(r) for r in table)}</tbody>
    </table></div>
  </section>

  <section class="hf-sec">
    <h2 class="hf-h2">HSN code: common questions</h2>
    {faq_html}
  </section>
  <noscript><p class="sf-error">The search needs JavaScript turned on. The table above works without it.</p></noscript>
</div></main>
<script>window.HF_CONFIG={json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")};</script>
<script src="{p(sf.SHARED_PATH + "hsn-search.js")}?v={v}" defer></script>
<script src="{p(TOOL_PATH + "app.js")}?v={v}" defer></script>
''' + footer() + "</body></html>"


FAQ = [
    ("What is an HSN code?",
     "HSN (Harmonized System of Nomenclature) is the worldwide product code system. The first 6 digits are the same in "
     "every country; India adds 2 more digits, making an 8-digit code. You need it for GST invoices, GST returns, "
     "shipping bills and to look up trade data."),
    ("How many HSN digits do I need on a GST invoice?",
     "Under CBIC notification 78/2020: if your turnover last year was up to ₹5 crore, print at least 4 digits on B2B "
     "invoices (optional on B2C). Above ₹5 crore, print at least 6 digits on every invoice. Exporters use the full 8 "
     "digits on the shipping bill."),
    ("Where do I find the GST rate for my HSN code?",
     "GST rates were restructured from 22 September 2025, so use the official CBIC rate page "
     "(cbic-gst.gov.in, 'GST Goods and Services Rates') and search by the 4-digit heading. If you are unsure, ask "
     "your CA before you invoice."),
    ("What if two codes look right for my product?",
     "Pick the one that describes what the product is made of and how it is made, not what it is used for. When in "
     "doubt, look at what similar sellers use on their invoices or ask a customs broker; a wrong code can mean the "
     "wrong GST rate or a held shipment."),
    ("Is the 6-digit code the same abroad?",
     "Yes. The first 6 digits are global, so use them on sites like uktradeinfo, UN Comtrade or a foreign buyer's "
     "import data. Countries add their own extra digits after that."),
]


def write_hsn_finder(dist_dir, districts, product_page_slug, head, nav, footer, esc, p):
    out = Path(dist_dir) / "tools" / "hsn-code-finder"
    out.mkdir(parents=True, exist_ok=True)
    shared = json.loads((Path(dist_dir) / "tools" / "shared" / "hsn.json").read_text(encoding="utf-8"))
    headings = shared["h"]
    india = _india_meta()
    cfg = config(p, india)
    table = _odop_table(districts, product_page_slug, headings)
    for f in ("app.js", "style.css"):
        shutil.copy(SRC_DIR / f, out / f)
    (out / "index.html").write_text(build_page(head, nav, footer, esc, p, cfg, table, headings), encoding="utf-8")
    return len(shared["t"]), len(table)
