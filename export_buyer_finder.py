"""Export Buyer Finder teaser (/tools/export-buyer-finder/).

Free part: pick an Indian HSN code → US import snapshot for its HS6 code (total US imports, India's value,
share, rank, 5-year trend, top supplier countries) from UN Comtrade data fetched at build time.
Waitlist: the verified US buyer list (customs-record proof + contacts) is "launching soon"; the email goes
to the same Google Sheet as the Supplier Finder (event = export_waitlist).

Data: data/us_imports/us_imports_hs6.json, made by tools_src/export-buyer-finder/fetch_us_imports.py.
"""
import json, shutil
from pathlib import Path

import supplier_finder as sf

BASE_DIR = Path(__file__).parent
SRC_DIR = BASE_DIR / "tools_src" / "export-buyer-finder"
DATA_FILE = BASE_DIR / "data" / "us_imports" / "us_imports_hs6.json"
TOOL_PATH = "/tools/export-buyer-finder/"

# Comtrade's official names → what readers expect ("Other Asia, nes" is Taiwan in Comtrade).
NAME_FIX = {
    "Other Asia, nes": "Taiwan", "Rep. of Korea": "South Korea", "Türkiye": "Turkey", "Viet Nam": "Vietnam",
    "China, Hong Kong SAR": "Hong Kong", "China, Macao SAR": "Macao", "Russian Federation": "Russia",
    "Dem. People's Rep. of Korea": "North Korea", "Lao People's Dem. Rep.": "Laos", "Rep. of Moldova": "Moldova",
    "United Rep. of Tanzania": "Tanzania", "Bolivia (Plurinational State of)": "Bolivia",
    "Venezuela (Bolivarian Rep. of)": "Venezuela", "Iran (Islamic Rep. of)": "Iran", "Syria": "Syria",
    "Dominican Rep.": "Dominican Republic", "United Arab Emirates": "UAE", "Bosnia Herzegovina": "Bosnia and Herzegovina",
    "Brunei Darussalam": "Brunei", "Dem. Rep. of the Congo": "DR Congo", "Central African Rep.": "Central African Republic",
    "Falkland Isds (Malvinas)": "Falkland Islands", "FS Micronesia": "Micronesia",
}


def _country(name):
    name = NAME_FIX.get(name, name)
    return name.replace(" Isds", " Islands")

SEGMENTS = [
    ("first", "Not exporting yet. I have a product, no buyers"),
    ("small", "Exporting to 1–3 buyers, want more"),
    ("merchant", "Merchant exporter or sourcing agent"),
    ("consultant", "Export consultant or council"),
]


def _version():
    import hashlib
    h = hashlib.sha1()
    for f in (SRC_DIR / "app.js", SRC_DIR / "style.css", sf.SHARED_SRC / "hsn-search.js", sf.SRC_DIR / "style.css"):
        h.update(f.read_bytes())
    if DATA_FILE.exists():
        h.update(str(DATA_FILE.stat().st_mtime).encode())
    return h.hexdigest()[:10]


def build_page(head, nav, footer, esc, p, meta):
    v = _version()
    cfg = {
        "leadEndpoint": sf.LEAD_ENDPOINT,
        "hsnUrl": p(sf.SHARED_PATH + "hsn.json"),
        "dataBase": p(TOOL_PATH + "us/"),
        "meta": meta,
        "supplierFinder": p(sf.TOOL_PATH),
    }
    yr = meta.get("years", [None])[-1] if meta else None
    title = "Export Buyer Finder: US Imports by HSN Code, India's Share & Top Competitors | KidharMilega"
    desc = ("Enter your HSN code to see how much the US imports, how much comes from India, India's rank and the "
            "countries you compete with. Verified US buyer lists from customs records are coming soon.")
    extra = (f'<link rel="stylesheet" href="{p(sf.TOOL_PATH + "style.css")}?v={v}">'
             f'<link rel="stylesheet" href="{p(TOOL_PATH + "style.css")}?v={v}">')
    seg_opts = "".join(f'<option value="{k}">{esc(label)}</option>' for k, label in SEGMENTS)
    return head(title, desc, TOOL_PATH, extra_head=extra) + nav("tools") + f'''
<main class="sf ebf"><div class="container">
  <header class="page-header sf-header">
    <div class="section-label">Free tool · Export Buyer Finder <span class="ebf-beta">Beta</span></div>
    <h1 class="page-header-title">Who buys your product<br><em>in the US?</em></h1>
    <p class="page-header-sub">Start with the numbers. Enter your HSN code to see how much the US imports, how much comes from India, and which countries you're up against. Free, no signup.</p>
  </header>

  <form class="sf-form" id="ebfForm" autocomplete="off" novalidate>
    <section class="sf-step">
      <h2 class="sf-step__title"><span class="sf-step__num">1</span>What do you export (or want to)?</h2>
      <label class="sf-label" for="ebfHsn">HSN code or product name</label>
      <div class="sf-combo">
        <input class="sf-input" id="ebfHsn" type="text" inputmode="search" placeholder="e.g. 48201000 or leather journal" aria-autocomplete="list" aria-controls="ebfHsnList" aria-expanded="false" role="combobox">
        <ul class="sf-list" id="ebfHsnList" role="listbox" hidden></ul>
      </div>
      <p class="sf-hint" id="ebfHsnStatus">Loading 12,600+ HSN codes…</p>
      <div class="sf-picked" id="ebfPicked" hidden></div>
      <div class="sf-submit" style="margin:var(--space-lg) 0 0">
        <button class="btn btn-primary btn-lg" type="submit">Show the US market <span class="btn__arrow" aria-hidden="true">&rarr;</span></button>
        <p class="sf-error" id="ebfError" role="alert"></p>
      </div>
    </section>
  </form>

  <section class="ebf-results" id="ebfResults" hidden aria-live="polite">
    <div class="sf-results__head">
      <div class="section-label">US import market{(" · " + str(yr)) if yr else ""}</div>
      <h2 class="section-title" id="ebfTitle"></h2>
      <p class="section-sub" id="ebfSub"></p>
    </div>
    <div id="ebfMarket"></div>

    <div class="ebf-lock" id="ebfLock">
      <div class="ebf-lock__head">
        <div class="section-label">Coming soon</div>
        <h2 class="section-title">The US companies already buying this from India</h2>
        <p class="section-sub">We read US customs records to find importers of your HSN code from India, with the shipment that proves it, how often they buy, a fit score, and how to reach them.</p>
      </div>
      <div class="ebf-sample" aria-hidden="true">
        <div class="ebf-sample__label">What each buyer lead will look like</div>
        <div class="ebf-row">
          <div><span class="ebf-blur">Company name hidden</span><small>Gift wholesaler · Pennsylvania</small></div>
          <div><b>Score</b><span class="ebf-score">89</span></div>
          <div><b>Proof</b><span>Bill of lading names the product</span></div>
          <div><b>Buys from India</b><span>12 shipments in the last 12 months</span></div>
          <div><b>Contacts</b><span class="ebf-blur">website · email · phone</span></div>
        </div>
        <p class="ebf-sample__note">Sample from a leather-journals test run. The name and contacts unlock with your free leads.</p>
      </div>

      <div class="ebf-wait" id="ebfWait">
        <h3>Get early access, with 3 buyer leads free</h3>
        <p>Join the waitlist. We'll email you when buyers for <strong id="ebfWaitCode">your HSN code</strong> are ready.</p>
        <form id="ebfWaitForm" novalidate>
          <div class="sf-row">
            <div>
              <label class="sf-label" for="ebfEmail">Email</label>
              <input class="sf-input" id="ebfEmail" type="email" inputmode="email" autocomplete="email" required placeholder="you@example.com">
            </div>
            <div>
              <label class="sf-label" for="ebfPhone">WhatsApp <span class="sf-opt">(optional)</span></label>
              <input class="sf-input" id="ebfPhone" type="tel" inputmode="tel" autocomplete="tel" placeholder="10-digit mobile">
            </div>
          </div>
          <label class="sf-label" for="ebfSeg">Where are you in exporting?</label>
          <select class="sf-input" id="ebfSeg" required><option value="">Choose one</option>{seg_opts}</select>
          <p class="sf-error" id="ebfWaitError" role="alert"></p>
          <button class="btn btn-primary" type="submit">Join the waitlist</button>
          <p class="sf-fine" style="text-align:left">By joining you agree to our <a href="{p('/terms-of-service/')}">terms</a>. No spam.</p>
        </form>
        <div class="ebf-done" id="ebfDone" hidden>
          <strong>You're on the list.</strong>
          <p>We'll email <span id="ebfDoneEmail"></span> when US buyers for this code are ready. Look up more HSN codes above. We'll note each one you check.</p>
        </div>
      </div>
    </div>

    <aside class="sf-help">
      <div>
        <strong>Need suppliers or manufacturers first?</strong>
        <p>Find local makers of this product in any Indian district, with an audit checklist.</p>
      </div>
      <a class="btn btn-ghost" id="ebfSfLink" href="{p(sf.TOOL_PATH)}">Open Supplier Finder</a>
    </aside>
  </section>
  <noscript><p class="sf-error">This tool needs JavaScript turned on.</p></noscript>
</div></main>
<script>window.EBF_CONFIG={json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")};</script>
<script src="{p(sf.SHARED_PATH + "hsn-search.js")}?v={v}" defer></script>
<script src="{p(TOOL_PATH + "app.js")}?v={v}" defer></script>
''' + footer() + "</body></html>"


def write_export_buyer_finder(dist_dir, head, nav, footer, esc, p):
    out = Path(dist_dir) / "tools" / "export-buyer-finder"
    (out / "us").mkdir(parents=True, exist_ok=True)
    meta, n = {}, 0
    if DATA_FILE.exists():
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        names = {k: _country(v) for k, v in data["partners"].items()}
        meta = {"years": data["years"], "source": data["source"], "fetched": data["fetched"], "partners": names}
        by_ch = {}
        for code, row in data["hs6"].items():
            by_ch.setdefault(code[:2], {})[code] = row
        meta["chapters"] = sorted(by_ch)
        for ch, rows in by_ch.items():
            (out / "us" / f"{ch}.json").write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")
        n = len(data["hs6"])
    for f in ("app.js", "style.css"):
        shutil.copy(SRC_DIR / f, out / f)
    (out / "index.html").write_text(build_page(head, nav, footer, esc, p, meta), encoding="utf-8")
    return n
