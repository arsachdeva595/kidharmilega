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
# Two Comtrade datasets (see tools_src/export-buyer-finder/fetch_comtrade.py), served as one file per HS chapter.
DATASETS = {
    "in": BASE_DIR / "data" / "india_exports" / "india_exports_hs6.json",   # India → every destination
    "us": BASE_DIR / "data" / "us_imports" / "us_imports_hs6.json",         # US ← every supplier
}
# Named Canadian importers from India (tools_src/export-buyer-finder/fetch_canada.py).
CANADA = BASE_DIR / "data" / "canada_importers" / "canada_india_hs6.json"
# Named UK importers (any origin) for the launch chapters (tools_src/export-buyer-finder/fetch_uk.py).
UK = BASE_DIR / "data" / "uk_importers" / "uk_importers_hs6.json"
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
    for path in list(DATASETS.values()) + [CANADA, UK]:
        if path.exists():
            h.update(str(path.stat().st_mtime).encode())
    return h.hexdigest()[:10]


def build_page(head, nav, footer, esc, p, meta):
    v = _version()
    cfg = {
        "leadEndpoint": sf.LEAD_ENDPOINT,
        "hsnUrl": p(sf.SHARED_PATH + "hsn.json"),
        "dataBase": p(TOOL_PATH),
        "meta": meta,
        "supplierFinder": p(sf.TOOL_PATH),
    }
    title = "Export Buyer Finder: Which Countries Buy Your HSN Code from India | KidharMilega"
    desc = ("Enter your HSN code to see the top countries buying it from India, India's export trend, the US market "
            "in detail, and the companies in Canada and the UK that import it. Free, no signup.")
    extra = (f'<link rel="stylesheet" href="{p(sf.TOOL_PATH + "style.css")}?v={v}">'
             f'<link rel="stylesheet" href="{p(TOOL_PATH + "style.css")}?v={v}">')
    seg_opts = "".join(f'<option value="{k}">{esc(label)}</option>' for k, label in SEGMENTS)
    return head(title, desc, TOOL_PATH, extra_head=extra) + nav("tools") + f'''
<main class="sf ebf"><div class="container">
  <header class="page-header sf-header">
    <div class="section-label">Free tool · Export Buyer Finder <span class="ebf-beta">Beta</span></div>
    <h1 class="page-header-title">Which countries buy<br><em>your product from India?</em></h1>
    <p class="page-header-sub">Enter your HSN code to see the top countries India sells it to, how fast that's growing, the US market in detail, and the companies abroad that import it. Free, no signup.</p>
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
        <button class="btn btn-primary btn-lg" type="submit">Find markets &amp; buyers <span class="btn__arrow" aria-hidden="true">&rarr;</span></button>
        <p class="sf-error" id="ebfError" role="alert"></p>
      </div>
    </section>
  </form>

  <section class="ebf-results" id="ebfResults" hidden aria-live="polite">
    <div class="sf-results__head">
      <div class="section-label">Export market</div>
      <h2 class="section-title" id="ebfTitle"></h2>
      <p class="section-sub" id="ebfSub"></p>
    </div>
    <div id="ebfMarket"></div>

    <div class="ebf-lock" id="ebfLock">
      <div class="ebf-lock__head">
        <div class="section-label">Coming soon</div>
        <h2 class="section-title">Unlock full buyer details</h2>
        <p class="section-sub">Company names, websites, emails and phone numbers for every buyer above, plus US importers proven from customs records: how often they buy from India and a fit score.</p>
      </div>
      <div class="ebf-sample" id="ebfSample" aria-hidden="true">
        <div class="ebf-sample__label">What each buyer lead looks like</div>
        <div class="ebf-row">
          <div><span class="ebf-blur">Company name hidden</span><small>Gift wholesaler · Pennsylvania</small></div>
          <div><b>Score</b><span class="ebf-score">89</span></div>
          <div><b>Proof</b><span>Bill of lading names the product</span></div>
          <div><b>Buys from India</b><span>12 shipments in the last 12 months</span></div>
          <div><b>Contacts</b><span class="ebf-blur">website · email · phone</span></div>
        </div>
        <p class="ebf-sample__note">Sample from a leather-journals test run.</p>
      </div>

      <div class="ebf-wait" id="ebfWait">
        <h3>Get access first, with 3 buyer leads free</h3>
        <p>Leave your details and we'll email you when full details for <strong id="ebfWaitCode">your HSN code</strong> are ready.</p>
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
          <button class="btn btn-primary" type="submit">Notify me when it's live</button>
          <p class="sf-fine" style="text-align:left">By continuing you agree to our <a href="{p('/terms-of-service/')}">terms</a>. No spam.</p>
        </form>
        <div class="ebf-done" id="ebfDone" hidden>
          <strong>You're on the list.</strong>
          <p>We'll email <span id="ebfDoneEmail"></span> as soon as full buyer details are ready. Look up more HSN codes above. We'll note each one you check.</p>
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


def _mask(rows):
    """Published buyer rows never carry company names: unlocking names is not live yet, and anything in the static
    files is readable by anyone. Each name becomes a short stable id (used to merge a company across codes).
    The ["+", n] "n more" marker rows pass through. Real names stay in data/ for when unlocking launches."""
    import hashlib
    return [r if r[0] == "+" else [hashlib.sha1(r[0].encode("utf-8")).hexdigest()[:10]] + r[1:] for r in rows]


def write_export_buyer_finder(dist_dir, head, nav, footer, esc, p):
    out = Path(dist_dir) / "tools" / "export-buyer-finder"
    meta, counts, names = {}, {}, {}
    for key, path in DATASETS.items():
        (out / key).mkdir(parents=True, exist_ok=True)
        if not path.exists():
            counts[key] = 0
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        names.update({k: _country(v) for k, v in data["partners"].items()})
        by_ch = {}
        for code, row in data["hs6"].items():
            by_ch.setdefault(code[:2], {})[code] = row
        for ch, rows in by_ch.items():
            (out / key / f"{ch}.json").write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")
        meta[key] = {"years": data["years"], "source": data["source"], "fetched": data["fetched"], "chapters": sorted(by_ch)}
        counts[key] = len(data["hs6"])
    meta["partners"] = names
    (out / "ca").mkdir(parents=True, exist_ok=True)
    if CANADA.exists():
        ca = json.loads(CANADA.read_text(encoding="utf-8"))
        by_ch = {}
        for code, rows in ca["hs6"].items():
            by_ch.setdefault(code[:2], {})[code] = _mask(rows)
        for ch, rows in by_ch.items():
            (out / "ca" / f"{ch}.json").write_text(json.dumps(rows, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
        meta["ca"] = {"year": ca["year"], "source": ca["source"], "licence": ca["licence"], "chapters": sorted(by_ch)}
        counts["ca"] = len(ca["hs6"])
    (out / "uk").mkdir(parents=True, exist_ok=True)
    if UK.exists():
        uk = json.loads(UK.read_text(encoding="utf-8"))
        by_ch = {}
        for code, rows in uk["hs6"].items():
            # UK rows: drop the postcode too (with a town it can point to a single firm).
            by_ch.setdefault(code[:2], {})[code] = _mask([r if r[0] == "+" else r[:2] + [""] + r[3:] for r in rows])
        for ch, rows in by_ch.items():
            (out / "uk" / f"{ch}.json").write_text(json.dumps(rows, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
        meta["uk"] = {"months": uk["months"], "source": uk["source"], "licence": uk["licence"],
                      "covered": uk["chapters"], "chapters": sorted(by_ch)}
        counts["uk"] = len(uk["hs6"])
    for f in ("app.js", "style.css"):
        shutil.copy(SRC_DIR / f, out / f)
    (out / "index.html").write_text(build_page(head, nav, footer, esc, p, meta), encoding="utf-8")
    return counts
