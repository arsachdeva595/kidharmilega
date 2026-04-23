#!/usr/bin/env python3
"""
KidharMilega Static Site Builder
----------------------------------
Reads data/districts.csv and data/vendors.csv
Generates all HTML pages into dist/

To use with Google Sheets:
  1. File > Share > Publish to web > CSV format
  2. Replace CSV_URL_DISTRICTS and CSV_URL_VENDORS below with your sheet URLs
  3. Run: python build.py --live   (fetches from Google Sheets)
  4. Run: python build.py          (uses local CSV files)
"""

import csv, os, shutil, re, sys
from pathlib import Path
from datetime import datetime

# ── CONFIG ──────────────────────────────────────────────────────────────────
SITE_NAME     = "KidharMilega"
SITE_TAGLINE  = "India's Small Business Discovery Platform"
SITE_URL      = "https://kidharmilega.in"
IG_HANDLE     = "@startupwalebhaiya"
BUILD_DATE    = datetime.now().strftime("%B %Y")

CSV_URL_DISTRICTS = "YOUR_GOOGLE_SHEET_CSV_URL_HERE"
CSV_URL_VENDORS   = "YOUR_VENDORS_SHEET_CSV_URL_HERE"

BASE_DIR  = Path(__file__).parent
DATA_DIR  = BASE_DIR / "data"
DIST_DIR  = BASE_DIR / "dist"
SRC_DIR   = BASE_DIR / "src"

# ── FETCH OR READ DATA ───────────────────────────────────────────────────────
def load_csv(local_path, remote_url=None):
    use_remote = "--live" in sys.argv and remote_url and not remote_url.startswith("YOUR_")
    if use_remote:
        import urllib.request
        print(f"  Fetching {remote_url[:60]}...")
        with urllib.request.urlopen(remote_url) as r:
            content = r.read().decode("utf-8")
        return list(csv.DictReader(content.splitlines()))
    else:
        print(f"  Reading {local_path}...")
        with open(local_path, encoding="utf-8") as f:
            return list(csv.DictReader(f))

# ── HELPERS ──────────────────────────────────────────────────────────────────
def esc(text):
    if not text: return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def slug(text):
    return re.sub(r"[^a-z0-9-]", "", re.sub(r"\s+", "-", str(text).lower().strip()))

def nav(active="home"):
    links = [
        ("Home", "index.html", "home"),
        ("ODOP Directory", "odop/index.html", "odop"),
        ("Events", "events/index.html", "events"),
        ("Vendors", "vendors/index.html", "vendors"),
    ]
    items = ""
    for label, href, key in links:
        cls = ' class="active"' if key == active else ''
        items += f'<a href="/{href}"{cls}>{label}</a>'
    return f"""
<nav class="site-nav">
  <div class="nav-inner">
    <a href="/index.html" class="nav-logo">
      <span class="logo-mark">KMG</span>
      <span class="logo-text">kidhar<strong>milega</strong></span>
    </a>
    <div class="nav-links">{items}</div>
    <a href="https://instagram.com/startupwalebhaiya" class="nav-ig" target="_blank">{IG_HANDLE}</a>
  </div>
</nav>"""

def footer():
    return f"""
<footer class="site-footer">
  <div class="footer-inner">
    <div class="footer-brand">
      <span class="logo-mark small">KMG</span>
      <span>kidharMilega.in</span>
    </div>
    <div class="footer-links">
      <a href="/index.html">Home</a>
      <a href="/odop/index.html">ODOP Directory</a>
      <a href="/events/index.html">Events</a>
      <a href="/vendors/index.html">Vendors</a>
    </div>
    <div class="footer-meta">
      Built by <a href="https://instagram.com/startupwalebhaiya" target="_blank">{IG_HANDLE}</a> · {BUILD_DATE}
    </div>
  </div>
</footer>"""

def head(title, desc, canonical=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE_URL}{canonical}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,600;0,9..144,900;1,9..144,300&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>"""

# ── CSS ──────────────────────────────────────────────────────────────────────
CSS = """
/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
img { max-width: 100%; display: block; }
a { color: inherit; text-decoration: none; }

/* ── Tokens ── */
:root {
  --orange:     #E8521A;
  --orange-l:   #FDF0EB;
  --orange-m:   #F5C4A8;
  --dark:       #111111;
  --mid:        #555555;
  --light:      #888888;
  --border:     #E8E8E4;
  --bg:         #FFFFFF;
  --bg-2:       #FAFAF8;
  --bg-3:       #F3F2EF;
  --green:      #2D7D46;
  --green-l:    #EAF4EE;
  --blue:       #1A5FA8;
  --blue-l:     #E8F1FB;
  --radius:     10px;
  --radius-lg:  16px;
  --shadow:     0 1px 4px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.04);
  --shadow-lg:  0 2px 8px rgba(0,0,0,0.10), 0 8px 32px rgba(0,0,0,0.06);
  --font-display: 'Fraunces', Georgia, serif;
  --font-body:    'DM Sans', system-ui, sans-serif;
  --max-w: 1120px;
}

/* ── Base ── */
body { font-family: var(--font-body); color: var(--dark); background: var(--bg); line-height: 1.6; -webkit-font-smoothing: antialiased; }
h1,h2,h3,h4 { font-family: var(--font-display); line-height: 1.15; }
p { color: var(--mid); }

/* ── Layout ── */
.container { max-width: var(--max-w); margin: 0 auto; padding: 0 24px; }
.section { padding: 80px 0; }
.section-sm { padding: 48px 0; }

/* ── Nav ── */
.site-nav { position: sticky; top: 0; z-index: 100; background: rgba(255,255,255,0.92); backdrop-filter: blur(12px); border-bottom: 1px solid var(--border); }
.nav-inner { max-width: var(--max-w); margin: 0 auto; padding: 0 24px; height: 60px; display: flex; align-items: center; gap: 32px; }
.nav-logo { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.logo-mark { background: var(--orange); color: #fff; font-family: var(--font-body); font-weight: 700; font-size: 11px; letter-spacing: 1px; padding: 4px 7px; border-radius: 4px; }
.logo-mark.small { font-size: 10px; padding: 3px 6px; }
.logo-text { font-family: var(--font-body); font-size: 15px; font-weight: 400; color: var(--dark); }
.logo-text strong { color: var(--orange); font-weight: 600; }
.nav-links { display: flex; gap: 4px; flex: 1; }
.nav-links a { font-size: 14px; color: var(--mid); padding: 6px 12px; border-radius: 6px; transition: all 0.15s; }
.nav-links a:hover, .nav-links a.active { color: var(--dark); background: var(--bg-3); }
.nav-links a.active { color: var(--orange); }
.nav-ig { font-size: 13px; color: var(--orange); font-weight: 500; flex-shrink: 0; }
.nav-ig:hover { text-decoration: underline; }

/* ── Footer ── */
.site-footer { border-top: 1px solid var(--border); padding: 40px 0; background: var(--bg-2); margin-top: 80px; }
.footer-inner { max-width: var(--max-w); margin: 0 auto; padding: 0 24px; display: flex; align-items: center; gap: 32px; flex-wrap: wrap; }
.footer-brand { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 14px; }
.footer-links { display: flex; gap: 20px; flex: 1; }
.footer-links a { font-size: 13px; color: var(--mid); }
.footer-links a:hover { color: var(--dark); }
.footer-meta { font-size: 12px; color: var(--light); }
.footer-meta a { color: var(--orange); }

/* ── Buttons ── */
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 12px 22px; border-radius: var(--radius); font-size: 14px; font-weight: 500; font-family: var(--font-body); cursor: pointer; transition: all 0.15s; border: 1.5px solid transparent; text-decoration: none; }
.btn-primary { background: var(--orange); color: #fff; border-color: var(--orange); }
.btn-primary:hover { background: #C94416; border-color: #C94416; }
.btn-ghost { background: transparent; color: var(--dark); border-color: var(--border); }
.btn-ghost:hover { background: var(--bg-3); border-color: var(--dark); }
.btn-sm { padding: 8px 14px; font-size: 13px; }

/* ── Tags / badges ── */
.tag { display: inline-block; font-size: 11px; font-weight: 500; padding: 3px 9px; border-radius: 20px; letter-spacing: 0.3px; }
.tag-orange { background: var(--orange-l); color: var(--orange); }
.tag-green { background: var(--green-l); color: var(--green); }
.tag-blue { background: var(--blue-l); color: var(--blue); }
.tag-gray { background: var(--bg-3); color: var(--mid); }

/* ── Cards ── */
.card { background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 24px; transition: box-shadow 0.2s, transform 0.2s; }
.card:hover { box-shadow: var(--shadow-lg); transform: translateY(-2px); }
.card-link { display: block; }

/* ── Grid ── */
.grid-2 { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
.grid-3 { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
.grid-4 { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }

/* ── Hero ── */
.hero { padding: 80px 0 60px; }
.hero-eyebrow { font-size: 12px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; color: var(--orange); margin-bottom: 20px; }
.hero-title { font-family: var(--font-display); font-size: clamp(40px, 6vw, 72px); font-weight: 900; line-height: 1.05; color: var(--dark); margin-bottom: 20px; }
.hero-title em { font-style: italic; color: var(--orange); }
.hero-sub { font-size: 18px; color: var(--mid); max-width: 560px; line-height: 1.7; margin-bottom: 36px; }
.hero-actions { display: flex; gap: 12px; flex-wrap: wrap; }

/* ── Stat strip ── */
.stat-strip { display: flex; gap: 40px; flex-wrap: wrap; padding: 32px 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); margin: 40px 0; }
.stat-item { display: flex; flex-direction: column; gap: 4px; }
.stat-val { font-family: var(--font-display); font-size: 32px; font-weight: 900; color: var(--orange); }
.stat-label { font-size: 13px; color: var(--light); }

/* ── District card ── */
.district-card { display: flex; flex-direction: column; gap: 14px; padding: 24px; border: 1px solid var(--border); border-radius: var(--radius-lg); transition: all 0.2s; background: var(--bg); text-decoration: none; }
.district-card:hover { border-color: var(--orange-m); box-shadow: var(--shadow-lg); transform: translateY(-2px); }
.district-card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.district-name { font-family: var(--font-display); font-size: 20px; font-weight: 600; color: var(--dark); }
.district-name-hin { font-size: 14px; color: var(--light); margin-top: 2px; }
.district-product { font-size: 14px; font-weight: 500; color: var(--orange); margin-top: 4px; }
.district-desc { font-size: 13px; color: var(--mid); line-height: 1.6; }
.district-meta { display: flex; gap: 8px; flex-wrap: wrap; margin-top: auto; padding-top: 12px; border-top: 1px solid var(--border); }
.district-arrow { font-size: 18px; color: var(--border); transition: color 0.2s; }
.district-card:hover .district-arrow { color: var(--orange); }

/* ── District page ── */
.district-hero { padding: 60px 0 40px; border-bottom: 1px solid var(--border); }
.district-hero-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; flex-wrap: wrap; margin-bottom: 24px; }
.breadcrumb { font-size: 13px; color: var(--light); margin-bottom: 16px; }
.breadcrumb a { color: var(--orange); }
.district-page-title { font-family: var(--font-display); font-size: clamp(32px, 5vw, 56px); font-weight: 900; color: var(--dark); line-height: 1.1; }
.district-page-title span { color: var(--orange); font-style: italic; }
.district-tagline { font-size: 17px; color: var(--mid); margin-top: 12px; max-width: 600px; line-height: 1.7; }
.snapshot-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; margin-top: 32px; }
.snapshot-item { background: var(--bg-2); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; }
.snapshot-val { font-family: var(--font-display); font-size: 20px; font-weight: 700; color: var(--dark); }
.snapshot-key { font-size: 12px; color: var(--light); margin-top: 4px; }

/* ── Page sections ── */
.page-section { padding: 48px 0; border-bottom: 1px solid var(--border); }
.page-section:last-of-type { border-bottom: none; }
.section-label { font-size: 11px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; color: var(--orange); margin-bottom: 12px; }
.section-title { font-family: var(--font-display); font-size: 28px; font-weight: 700; color: var(--dark); margin-bottom: 8px; }
.section-sub { font-size: 15px; color: var(--mid); margin-bottom: 28px; line-height: 1.7; }

/* ── ODOP profile block ── */
.odop-block { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; align-items: start; }
@media (max-width: 700px) { .odop-block { grid-template-columns: 1fr; } }
.odop-detail-list { display: flex; flex-direction: column; gap: 0; }
.odop-detail-row { display: flex; padding: 12px 0; border-bottom: 1px solid var(--border); gap: 16px; }
.odop-detail-row:last-child { border-bottom: none; }
.odop-detail-key { font-size: 13px; color: var(--light); min-width: 130px; flex-shrink: 0; }
.odop-detail-val { font-size: 14px; color: var(--dark); font-weight: 500; }

/* ── Steps ── */
.steps-list { display: flex; flex-direction: column; gap: 0; }
.step-row { display: flex; gap: 20px; padding: 20px 0; border-bottom: 1px solid var(--border); }
.step-row:last-child { border-bottom: none; }
.step-num { width: 36px; height: 36px; background: var(--orange); color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; flex-shrink: 0; margin-top: 2px; }
.step-content { flex: 1; }
.step-title { font-size: 15px; font-weight: 600; color: var(--dark); margin-bottom: 4px; }
.step-desc { font-size: 14px; color: var(--mid); line-height: 1.6; }

/* ── Names grid ── */
.names-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.name-card { background: var(--bg-2); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 16px; font-family: var(--font-display); font-size: 16px; font-weight: 600; color: var(--dark); }

/* ── Vendor card ── */
.vendor-card { background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 20px; }
.vendor-card.premium { border-color: var(--orange-m); background: var(--orange-l); }
.vendor-name { font-size: 16px; font-weight: 600; color: var(--dark); margin-bottom: 4px; }
.vendor-cat { font-size: 13px; color: var(--mid); margin-bottom: 12px; }
.vendor-desc { font-size: 13px; color: var(--mid); line-height: 1.6; margin-bottom: 14px; }
.vendor-actions { display: flex; gap: 8px; flex-wrap: wrap; }

/* ── Scheme pills ── */
.scheme-list { display: flex; flex-direction: column; gap: 12px; }
.scheme-item { display: flex; gap: 16px; padding: 16px; background: var(--bg-2); border: 1px solid var(--border); border-radius: var(--radius); align-items: flex-start; }
.scheme-icon { width: 36px; height: 36px; background: var(--orange-l); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.scheme-title { font-size: 14px; font-weight: 600; color: var(--dark); margin-bottom: 3px; }
.scheme-desc { font-size: 13px; color: var(--mid); }

/* ── CTA block ── */
.cta-block { background: var(--dark); border-radius: var(--radius-lg); padding: 48px; display: flex; gap: 32px; align-items: center; justify-content: space-between; flex-wrap: wrap; margin-top: 60px; }
.cta-title { font-family: var(--font-display); font-size: 28px; font-weight: 700; color: #fff; margin-bottom: 8px; }
.cta-sub { font-size: 15px; color: rgba(255,255,255,0.6); }
.cta-actions { display: flex; gap: 12px; flex-shrink: 0; flex-wrap: wrap; }

/* ── Search ── */
.search-wrap { position: relative; max-width: 480px; }
.search-input { width: 100%; padding: 14px 20px 14px 46px; border: 1.5px solid var(--border); border-radius: 40px; font-size: 15px; font-family: var(--font-body); background: var(--bg); color: var(--dark); outline: none; transition: border-color 0.2s; }
.search-input:focus { border-color: var(--orange); }
.search-icon { position: absolute; left: 16px; top: 50%; transform: translateY(-50%); color: var(--light); font-size: 18px; pointer-events: none; }

/* ── Filter tabs ── */
.filter-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 32px; }
.filter-tab { padding: 7px 16px; border-radius: 20px; border: 1.5px solid var(--border); font-size: 13px; font-weight: 500; color: var(--mid); cursor: pointer; transition: all 0.15s; background: var(--bg); font-family: var(--font-body); }
.filter-tab:hover, .filter-tab.active { border-color: var(--orange); color: var(--orange); background: var(--orange-l); }

/* ── Events placeholder ── */
.events-placeholder { background: var(--bg-2); border: 1.5px dashed var(--border); border-radius: var(--radius-lg); padding: 40px; text-align: center; }
.events-placeholder h3 { font-family: var(--font-display); font-size: 20px; margin-bottom: 8px; }

/* ── Page header (for directory pages) ── */
.page-header { padding: 48px 0 32px; border-bottom: 1px solid var(--border); margin-bottom: 40px; }
.page-header-title { font-family: var(--font-display); font-size: clamp(28px, 4vw, 44px); font-weight: 900; color: var(--dark); margin-bottom: 8px; }
.page-header-title em { font-style: italic; color: var(--orange); }
.page-header-sub { font-size: 16px; color: var(--mid); max-width: 520px; }

/* ── Master nav ── */
.master-modules { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 24px; margin-bottom: 60px; }
.module-card { border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 28px; display: flex; flex-direction: column; gap: 16px; transition: all 0.2s; text-decoration: none; }
.module-card:hover { border-color: var(--orange-m); box-shadow: var(--shadow-lg); transform: translateY(-2px); }
.module-icon { font-size: 28px; }
.module-title { font-family: var(--font-display); font-size: 22px; font-weight: 700; color: var(--dark); }
.module-desc { font-size: 14px; color: var(--mid); line-height: 1.7; }
.module-link { font-size: 13px; color: var(--orange); font-weight: 500; margin-top: auto; }

/* ── Responsive ── */
@media (max-width: 640px) {
  .container { padding: 0 16px; }
  .nav-links { display: none; }
  .section { padding: 48px 0; }
  .odop-block { grid-template-columns: 1fr; }
  .cta-block { padding: 28px; }
  .stat-strip { gap: 24px; }
}
"""

# ── PAGE BUILDERS ────────────────────────────────────────────────────────────

def build_homepage(districts):
    live = [d for d in districts if d.get("page_status","").lower() == "live"]
    # state grouping for filters
    states = sorted(set(d["state"] for d in live))

    state_tabs = '<button class="filter-tab active" onclick="filterDistricts(\'all\', this)">All</button>'
    for st in states:
        state_tabs += f'<button class="filter-tab" onclick="filterDistricts(\'{slug(st)}\', this)">{esc(st)}</button>'

    cards = ""
    for d in live:
        gi_badge = '<span class="tag tag-green">GI Tag</span>' if d.get("odop_gi_tag","").lower() == "yes" else ""
        tier_badge = f'<span class="tag tag-gray">Tier {esc(d.get("tier_priority",""))}</span>'
        cards += f"""
<a href="/districts/{esc(d['url_slug'])}/index.html" class="district-card" data-state="{slug(d['state'])}">
  <div class="district-card-head">
    <div>
      <div class="district-name">{esc(d['district_name'])}</div>
      <div class="district-name-hin">{esc(d.get('district_name_hin',''))}</div>
      <div class="district-product">{esc(d.get('odop_product_name',''))}</div>
    </div>
    <span class="district-arrow">→</span>
  </div>
  <div class="district-desc">{esc(d.get('famous_for_1_line','')[:100])}</div>
  <div class="district-meta">
    <span class="tag tag-orange">{esc(d.get('odop_category',''))}</span>
    {gi_badge}
    {tier_badge}
  </div>
</a>"""

    return head(
        f"KidharMilega — Find your business opportunity across India",
        "India's small business discovery platform. Find ODOP products, trade events, vendors and business ideas for every district.",
        "/"
    ) + nav("home") + f"""
<main>
  <div class="container">
    <section class="hero">
      <div class="hero-eyebrow">India's Small Business Discovery Platform</div>
      <h1 class="hero-title">Kidhar<br><em>Milega?</em></h1>
      <p class="hero-sub">Every district in India has a product, a market, and an opportunity waiting. We found them all — vendors, events, schemes and step-by-step guides — in one place.</p>
      <div class="hero-actions">
        <a href="/odop/index.html" class="btn btn-primary">Browse ODOP Directory</a>
        <a href="https://instagram.com/startupwalebhaiya" class="btn btn-ghost" target="_blank">Follow the Journey</a>
      </div>
      <div class="stat-strip">
        <div class="stat-item"><div class="stat-val">{len(live)}</div><div class="stat-label">Districts live</div></div>
        <div class="stat-item"><div class="stat-val">550+</div><div class="stat-label">ODOP products mapped</div></div>
        <div class="stat-item"><div class="stat-val">100%</div><div class="stat-label">Free to browse</div></div>
        <div class="stat-item"><div class="stat-val">Live</div><div class="stat-label">Event API data</div></div>
      </div>
    </section>

    <section class="section-sm">
      <div class="section-label">Explore by District</div>
      <div style="display:flex; gap:16px; align-items:center; flex-wrap:wrap; margin-bottom:24px;">
        <div class="search-wrap">
          <span class="search-icon">⌕</span>
          <input class="search-input" type="text" placeholder="Search district or product..." oninput="searchDistricts(this.value)" id="searchBox">
        </div>
      </div>
      <div class="filter-tabs">{state_tabs}</div>
      <div class="grid-3" id="districtGrid">{cards}</div>
    </section>

    <div class="cta-block">
      <div>
        <div class="cta-title">Building this live on Instagram</div>
        <div class="cta-sub">Follow {IG_HANDLE} — every district, every data point, documented in public.</div>
      </div>
      <div class="cta-actions">
        <a href="https://instagram.com/startupwalebhaiya" class="btn btn-primary" target="_blank">Follow {IG_HANDLE}</a>
      </div>
    </div>
  </div>
</main>

<script>
function filterDistricts(state, btn) {{
  document.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.district-card').forEach(c => {{
    c.style.display = (state === 'all' || c.dataset.state === state) ? '' : 'none';
  }});
}}
function searchDistricts(q) {{
  q = q.toLowerCase();
  document.querySelectorAll('.district-card').forEach(c => {{
    c.style.display = c.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
</script>
""" + footer() + "</body></html>"


def build_master_page():
    return head(
        "KidharMilega — Business Resources for India",
        "Your one-stop for ODOP products, trade events, vendor contacts and business opportunities across every Indian district.",
        "/master"
    ) + nav() + f"""
<main>
  <div class="container">
    <div class="page-header">
      <div class="section-label">All Resources</div>
      <h1 class="page-header-title">Everything you need to<br><em>build your business</em></h1>
      <p class="page-header-sub">Three directories. All free. Continuously updated. Start with ODOP — it's the most complete.</p>
    </div>

    <div class="master-modules">
      <a href="/odop/index.html" class="module-card">
        <div class="module-icon">🏺</div>
        <div class="module-title">ODOP Directory</div>
        <div class="module-desc">One District One Product — every GI-tagged and government-recognised product mapped to its district. With vendor data, how-to guides and business opportunity breakdown.</div>
        <div class="module-link">Browse ODOP products →</div>
      </a>
      <a href="/events/index.html" class="module-card">
        <div class="module-icon">🎪</div>
        <div class="module-title">Events & Expos</div>
        <div class="module-desc">Trade shows, craft fairs, B2B summits and local haats — across 100 Indian cities. Real-time data. Filter by city, month, industry or product category.</div>
        <div class="module-link">Browse upcoming events →</div>
      </a>
      <a href="/vendors/index.html" class="module-card">
        <div class="module-icon">🏭</div>
        <div class="module-title">Vendor Directory</div>
        <div class="module-desc">Raw material suppliers, manufacturers and distributors — mapped to each ODOP product and district. Find exactly who supplies what and where.</div>
        <div class="module-link">Find vendors →</div>
      </a>
    </div>

    <div class="cta-block">
      <div>
        <div class="cta-title">Want the full business playbook?</div>
        <div class="cta-sub">Ebook launching soon — how to launch an ODOP product as a brand and get your first customers.</div>
      </div>
      <div class="cta-actions">
        <a href="https://instagram.com/startupwalebhaiya" class="btn btn-primary" target="_blank">Notify me on Instagram</a>
      </div>
    </div>
  </div>
</main>
""" + footer() + "</body></html>"


def build_odop_page(districts):
    live = [d for d in districts if d.get("page_status","").lower() == "live"]
    cats = sorted(set(d.get("odop_category","") for d in live if d.get("odop_category","")))

    cat_tabs = '<button class="filter-tab active" onclick="filterODOP(\'all\', this)">All Categories</button>'
    for c in cats:
        cat_tabs += f'<button class="filter-tab" onclick="filterODOP(\'{slug(c)}\', this)">{esc(c)}</button>'

    cards = ""
    for d in live:
        gi = '<span class="tag tag-green">GI Tag</span>' if d.get("odop_gi_tag","").lower() == "yes" else ""
        cards += f"""
<a href="/districts/{esc(d['url_slug'])}/index.html" class="district-card" data-cat="{slug(d.get('odop_category',''))}">
  <div class="district-card-head">
    <div>
      <div class="district-name">{esc(d.get('odop_product_name',''))}</div>
      <div class="district-name-hin">{esc(d['district_name'])} · {esc(d['state'])}</div>
    </div>
    <span class="district-arrow">→</span>
  </div>
  <div class="district-product">{esc(d.get('production_scale',''))}</div>
  <div class="district-desc" style="margin-top:8px">{esc((d.get('why_this_district','') or '')[:110])}...</div>
  <div class="district-meta">
    <span class="tag tag-orange">{esc(d.get('odop_category',''))}</span>
    {gi}
    <span class="tag tag-gray">{esc(d.get('export_potential',''))} export</span>
  </div>
</a>"""

    return head(
        "ODOP Product Directory | KidharMilega",
        "Browse all One District One Product listings across India. Find GI-tagged products, understand market opportunities and discover how to start.",
        "/odop/"
    ) + nav("odop") + f"""
<main>
  <div class="container">
    <div class="page-header">
      <div class="section-label">ODOP Directory</div>
      <h1 class="page-header-title">One District,<br><em>One Product</em></h1>
      <p class="page-header-sub">Every government-recognised ODOP product mapped to its district — with market size, export potential and a step-by-step business guide.</p>
    </div>
    <div class="filter-tabs">{cat_tabs}</div>
    <div class="grid-3" id="odopGrid">{cards}</div>
  </div>
</main>
<script>
function filterODOP(cat, btn) {{
  document.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('#odopGrid .district-card').forEach(c => {{
    c.style.display = (cat === 'all' || c.dataset.cat === cat) ? '' : 'none';
  }});
}}
</script>
""" + footer() + "</body></html>"


def build_events_page():
    return head(
        "Trade Events & Expos | KidharMilega",
        "Find upcoming trade shows, craft fairs and B2B expos across 100 Indian cities. Real-time event data for small business owners.",
        "/events/"
    ) + nav("events") + """
<main>
  <div class="container">
    <div class="page-header">
      <div class="section-label">Events & Expos</div>
      <h1 class="page-header-title">Trade shows across<br><em>100 Indian cities</em></h1>
      <p class="page-header-sub">Real-time event listings — trade fairs, B2B summits, craft expos and local haats. Never miss the right show again.</p>
    </div>
    <div class="events-placeholder">
      <div style="font-size:36px;margin-bottom:16px;">🎪</div>
      <h3>Live Event Listings Coming Here</h3>
      <p style="max-width:480px;margin:12px auto 20px;font-size:14px;">Your AllEvents widget will be embedded here. Paste your AllEvents embed code to activate live event data across all cities and product categories.</p>
      <code style="background:#f3f2ef;padding:8px 16px;border-radius:6px;font-size:12px;display:inline-block;">
        &lt;!-- Paste AllEvents widget embed code here --&gt;
      </code>
    </div>
  </div>
</main>
""" + footer() + "</body></html>"


def build_vendors_page(vendors, districts):
    dist_map = {d["url_slug"]: d["district_name"] for d in districts}
    cats = sorted(set(v.get("category","") for v in vendors if v.get("category","")))

    cat_tabs = '<button class="filter-tab active" onclick="filterVendors(\'all\', this)">All</button>'
    for c in cats:
        cat_tabs += f'<button class="filter-tab" onclick="filterVendors(\'{slug(c)}\', this)">{esc(c)}</button>'

    cards = ""
    for v in vendors:
        is_premium = v.get("listing_type","").lower() == "premium"
        premium_cls = " premium" if is_premium else ""
        premium_badge = '<span class="tag tag-orange" style="margin-bottom:8px">Premium Listing</span><br>' if is_premium else ""
        whatsapp = ""
        if v.get("contact_whatsapp",""):
            whatsapp = f'<a href="https://wa.me/91{esc(v["contact_whatsapp"])}" class="btn btn-sm btn-primary" target="_blank">WhatsApp</a>'
        email_btn = ""
        if v.get("contact_email",""):
            email_btn = f'<a href="mailto:{esc(v["contact_email"])}" class="btn btn-sm btn-ghost">Email</a>'

        cards += f"""
<div class="vendor-card{premium_cls}" data-cat="{slug(v.get('category',''))}">
  {premium_badge}
  <div class="vendor-name">{esc(v.get('vendor_name',''))}</div>
  <div class="vendor-cat">{esc(v.get('category',''))} · {esc(v.get('city',''))}, {esc(v.get('state',''))}</div>
  <div class="vendor-desc">{esc(v.get('description',''))}</div>
  <div class="vendor-actions">{whatsapp}{email_btn}</div>
</div>"""

    return head(
        "Vendor & Supplier Directory | KidharMilega",
        "Find verified raw material suppliers and manufacturers for every ODOP product — mapped by district and product category.",
        "/vendors/"
    ) + nav("vendors") + f"""
<main>
  <div class="container">
    <div class="page-header">
      <div class="section-label">Vendor Directory</div>
      <h1 class="page-header-title">Find your<br><em>supplier</em></h1>
      <p class="page-header-sub">Verified raw material suppliers, manufacturers and distributors — mapped to each ODOP product and district. No cold calls into the void.</p>
    </div>

    <div style="background:var(--orange-l);border:1px solid var(--orange-m);border-radius:var(--radius);padding:16px 20px;margin-bottom:32px;font-size:14px;color:var(--dark);">
      <strong>Are you a vendor or supplier?</strong> Get a premium listing with full contact details, WhatsApp link and product photos.
      <a href="https://instagram.com/startupwalebhaiya" target="_blank" style="color:var(--orange);font-weight:600;margin-left:8px;">Contact us on Instagram →</a>
    </div>

    <div class="filter-tabs">{cat_tabs}</div>
    <div class="grid-3" id="vendorGrid">{cards}</div>
  </div>
</main>
<script>
function filterVendors(cat, btn) {{
  document.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('#vendorGrid .vendor-card').forEach(c => {{
    c.style.display = (cat === 'all' || c.dataset.cat === cat) ? '' : 'none';
  }});
}}
</script>
""" + footer() + "</body></html>"


def build_district_page(d, vendors):
    dist_vendors = [v for v in vendors if v.get("district_slug","") == d["url_slug"]]
    slug_d = d["url_slug"]

    # ── Snapshot ──
    snap_items = [
        ("Population", d.get("population","")),
        ("Area", d.get("area_km2","") + " km²" if d.get("area_km2","") else ""),
        ("Literacy", d.get("literacy_rate","") + "%" if d.get("literacy_rate","") else ""),
        ("Language", (d.get("main_languages","") or "").split(",")[0].strip()),
        ("City Tier", d.get("city_tier","")),
        ("State", d.get("state","")),
    ]
    snapshot_html = ""
    for k, v in snap_items:
        if v:
            snapshot_html += f'<div class="snapshot-item"><div class="snapshot-val">{esc(v)}</div><div class="snapshot-key">{esc(k)}</div></div>'

    # ── ODOP detail ──
    odop_rows = [
        ("Product", d.get("odop_product_name","")),
        ("Category", d.get("odop_category","")),
        ("GI Tag", d.get("odop_gi_tag","") + (" (since " + d.get("gi_tag_year","") + ")" if d.get("gi_tag_year","") else "")),
        ("Market Size", d.get("production_scale","")),
        ("Export Potential", d.get("export_potential","")),
        ("Export Markets", d.get("export_countries","")),
        ("Raw Materials", d.get("odop_raw_materials","")),
    ]
    odop_html = ""
    for k, v in odop_rows:
        if v and v.strip():
            odop_html += f'<div class="odop-detail-row"><div class="odop-detail-key">{esc(k)}</div><div class="odop-detail-val">{esc(v)}</div></div>'

    # ── Steps ──
    steps = [
        ("Learn / Research", d.get("step_1_learn","")),
        ("Source Raw Materials", d.get("step_2_source","")),
        ("Produce / Partner", d.get("step_3_produce","")),
        ("Brand & Register", d.get("step_4_brand","")),
        ("First Sale", d.get("step_5_sell","")),
        ("Scale", d.get("step_6_scale","")),
    ]
    steps_html = ""
    for i, (title, desc) in enumerate(steps, 1):
        if desc:
            steps_html += f'<div class="step-row"><div class="step-num">{i}</div><div class="step-content"><div class="step-title">{esc(title)}</div><div class="step-desc">{esc(desc)}</div></div></div>'

    # ── Brand names ──
    names = [d.get(f"brand_name_idea_{i}","") for i in range(1,6)]
    names_html = "".join(f'<div class="name-card">{esc(n)}</div>' for n in names if n)

    # ── Marketing ──
    mkt = [d.get(f"marketing_idea_{i}","") for i in range(1,4)]
    mkt_html = "".join(f'<li style="margin-bottom:10px;font-size:14px;color:var(--mid)">{esc(m)}</li>' for m in mkt if m)

    # ── Revenue streams ──
    streams = [d.get(f"revenue_stream_{i}","") for i in range(1,6)]
    streams_html = "".join(f'<div style="display:flex;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid var(--border)"><span style="width:22px;height:22px;background:var(--orange-l);color:var(--orange);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0">{i+1}</span><span style="font-size:14px;color:var(--dark)">{esc(s)}</span></div>' for i,s in enumerate(streams) if s)

    # ── Costs ──
    cost_min = d.get("min_setup_cost","")
    cost_max = d.get("max_setup_cost","")
    margin_w = d.get("gross_margin_wholesale","")
    margin_d = d.get("gross_margin_d2c","")
    breakeven = d.get("breakeven_timeline","")

    # ── Vendors ──
    vendors_html = ""
    if dist_vendors:
        for v in dist_vendors:
            is_p = v.get("listing_type","").lower() == "premium"
            p_cls = " premium" if is_p else ""
            p_badge = '<span class="tag tag-orange" style="display:inline-block;margin-bottom:8px">Premium</span><br>' if is_p else ""
            wa = f'<a href="https://wa.me/91{esc(v["contact_whatsapp"])}" class="btn btn-sm btn-primary" target="_blank">WhatsApp</a>' if v.get("contact_whatsapp","") else ""
            vendors_html += f'<div class="vendor-card{p_cls}">{p_badge}<div class="vendor-name">{esc(v.get("vendor_name",""))}</div><div class="vendor-cat">{esc(v.get("category",""))} · {esc(v.get("city",""))}</div><div class="vendor-desc" style="margin:8px 0">{esc(v.get("description",""))}</div><div class="vendor-actions">{wa}</div></div>'
    else:
        vendors_html = '<p style="font-size:14px;color:var(--mid)">Vendor data coming soon. <a href="https://instagram.com/startupwalebhaiya" style="color:var(--orange)">DM us to list your business →</a></p>'

    # ── Schemes ──
    schemes = []
    if d.get("relevant_central_scheme_1",""): schemes.append(("🏛️", d["relevant_central_scheme_1"]))
    if d.get("relevant_central_scheme_2",""): schemes.append(("🏛️", d["relevant_central_scheme_2"]))
    if d.get("relevant_state_scheme_1",""): schemes.append(("🏢", d["relevant_state_scheme_1"]))
    if d.get("relevant_state_scheme_2",""): schemes.append(("🏢", d.get("relevant_state_scheme_2","")))
    schemes_html = ""
    for icon, text in schemes:
        parts = text.split("—", 1)
        title = parts[0].strip()
        desc = parts[1].strip() if len(parts) > 1 else ""
        schemes_html += f'<div class="scheme-item"><div class="scheme-icon">{icon}</div><div><div class="scheme-title">{esc(title)}</div><div class="scheme-desc">{esc(desc)}</div></div></div>'

    gi_badge = '<span class="tag tag-green" style="font-size:13px;padding:5px 12px">✓ GI Certified ' + (d.get("gi_tag_year","") or "") + '</span>' if d.get("odop_gi_tag","").lower() == "yes" else ""

    return head(
        d.get("seo_title","") or f"Start a Business in {d['district_name']} | KidharMilega",
        d.get("meta_description","") or f"Business guide for {d['district_name']} — ODOP product, vendors, events and government schemes.",
        f"/districts/{slug_d}/"
    ) + nav() + f"""
<main>
  <div class="container">

    <section class="district-hero">
      <div class="breadcrumb"><a href="/index.html">Home</a> → <a href="/odop/index.html">ODOP Directory</a> → {esc(d['district_name'])}</div>
      <div class="district-hero-top">
        <div>
          <div class="hero-eyebrow">{esc(d['state'])} · {esc(d.get('city_tier',''))}</div>
          <h1 class="district-page-title">Start a business<br>in <span>{esc(d['district_name'])}</span></h1>
          <p class="district-tagline">{esc(d.get('famous_for_1_line',''))}</p>
        </div>
        {gi_badge}
      </div>
      <div class="snapshot-grid">{snapshot_html}</div>
    </section>

    <section class="page-section">
      <div class="section-label">ODOP Product</div>
      <h2 class="section-title">{esc(d.get('odop_product_name',''))}</h2>
      <p class="section-sub">{esc(d.get('why_this_district',''))}</p>
      <div class="odop-block">
        <div class="odop-detail-list">{odop_html}</div>
        <div>
          <div style="background:var(--orange-l);border:1px solid var(--orange-m);border-radius:var(--radius-lg);padding:24px;margin-bottom:20px;">
            <div style="font-size:12px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--orange);margin-bottom:12px;">Business Opportunity</div>
            <div style="display:flex;flex-direction:column;gap:12px;">
              <div><div style="font-size:12px;color:var(--light);margin-bottom:2px">Setup Cost Range</div><div style="font-size:16px;font-weight:600;color:var(--dark)">₹{esc(cost_min)} – ₹{esc(cost_max)}</div></div>
              <div><div style="font-size:12px;color:var(--light);margin-bottom:2px">D2C Gross Margin</div><div style="font-size:16px;font-weight:600;color:var(--green)">{esc(margin_d)}</div></div>
              <div><div style="font-size:12px;color:var(--light);margin-bottom:2px">Wholesale Margin</div><div style="font-size:16px;font-weight:600;color:var(--dark)">{esc(margin_w)}</div></div>
              <div><div style="font-size:12px;color:var(--light);margin-bottom:2px">Breakeven Timeline</div><div style="font-size:16px;font-weight:600;color:var(--dark)">{esc(breakeven)}</div></div>
            </div>
          </div>
          <div style="background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius-lg);padding:20px;">
            <div style="font-size:12px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--mid);margin-bottom:12px;">Ideal For</div>
            <p style="font-size:14px;color:var(--dark);margin-bottom:8px"><strong>{esc(d.get('suitable_for',''))}</strong></p>
            <p style="font-size:13px;color:var(--mid)">Not ideal for: {esc(d.get('not_suitable_for',''))}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="page-section">
      <div class="section-label">Revenue Streams</div>
      <h2 class="section-title">How you'll make money</h2>
      <p class="section-sub">Primary buyer: {esc(d.get('primary_target_audience',''))}</p>
      <div style="max-width:600px">{streams_html}</div>
    </section>

    <section class="page-section">
      <div class="section-label">Step-by-Step Guide</div>
      <h2 class="section-title">How to start</h2>
      <p class="section-sub">From zero to first sale — concrete steps specific to {esc(d['district_name'])} and {esc(d.get('odop_product_name',''))}.</p>
      <div class="steps-list">{steps_html}</div>
    </section>

    <section class="page-section">
      <div class="section-label">Events & Expos</div>
      <h2 class="section-title">Where to show up</h2>
      <p class="section-sub">Upcoming trade shows and craft expos relevant to {esc(d.get('odop_product_name',''))}.</p>
      <div class="events-placeholder">
        <p style="font-size:14px;color:var(--mid)">Live event listings powered by AllEvents API — embed your widget here.</p>
      </div>
    </section>

    <section class="page-section">
      <div class="section-label">Vendors & Suppliers</div>
      <h2 class="section-title">Where to source</h2>
      <p class="section-sub">Raw material suppliers and manufacturers for {esc(d.get('odop_product_name',''))} in and around {esc(d['district_name'])}.</p>
      <div class="grid-2">{vendors_html}</div>
    </section>

    <section class="page-section">
      <div class="section-label">Brand Name Ideas</div>
      <h2 class="section-title">Name your brand</h2>
      <div class="names-grid" style="margin-bottom:32px">{names_html}</div>
      <div class="section-label" style="margin-top:32px">Marketing Ideas</div>
      <h2 class="section-title">How to get customers</h2>
      <ul style="list-style:none;margin-top:16px">{mkt_html}</ul>
    </section>

    <section class="page-section">
      <div class="section-label">Government Schemes & Funding</div>
      <h2 class="section-title">Free money you didn't know about</h2>
      <div class="scheme-list" style="margin-bottom:24px">{schemes_html}</div>
      <div style="background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);padding:16px 20px;font-size:14px">
        <strong>Registration required:</strong> {esc(d.get('udyam_registration','Required — udyamregistration.gov.in'))}
      </div>
    </section>

    <div class="cta-block">
      <div>
        <div class="cta-title">Want the full business playbook?</div>
        <div class="cta-sub">Ebook: How to launch an ODOP product as a brand and get your first customers.</div>
      </div>
      <div class="cta-actions">
        <a href="https://instagram.com/startupwalebhaiya" class="btn btn-primary" target="_blank">Follow {IG_HANDLE}</a>
      </div>
    </div>

  </div>
</main>
""" + footer() + "</body></html>"


# ── MAIN BUILD ───────────────────────────────────────────────────────────────
def build():
    print("\n🔨 KidharMilega — Static Site Builder")
    print("=" * 40)

    # Clean and recreate dist
    if DIST_DIR.exists(): shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)
    (DIST_DIR / "assets").mkdir()
    (DIST_DIR / "districts").mkdir()
    (DIST_DIR / "odop").mkdir()
    (DIST_DIR / "events").mkdir()
    (DIST_DIR / "vendors").mkdir()

    # Write CSS
    (DIST_DIR / "assets" / "style.css").write_text(CSS)
    print("✓ CSS written")

    # Load data
    districts = load_csv(DATA_DIR / "districts.csv", CSV_URL_DISTRICTS)
    vendors   = load_csv(DATA_DIR / "vendors.csv",   CSV_URL_VENDORS)
    print(f"✓ Loaded {len(districts)} districts, {len(vendors)} vendors")

    # Homepage
    (DIST_DIR / "index.html").write_text(build_homepage(districts))
    print("✓ Homepage built")

    # Master page
    (DIST_DIR / "master.html").write_text(build_master_page())
    print("✓ Master page built")

    # ODOP directory
    (DIST_DIR / "odop" / "index.html").write_text(build_odop_page(districts))
    print("✓ ODOP directory built")

    # Events page
    (DIST_DIR / "events" / "index.html").write_text(build_events_page())
    print("✓ Events page built")

    # Vendors page
    (DIST_DIR / "vendors" / "index.html").write_text(build_vendors_page(vendors, districts))
    print("✓ Vendors directory built")

    # District pages
    live = [d for d in districts if d.get("page_status","").lower() == "live"]
    for d in live:
        s = d["url_slug"]
        page_dir = DIST_DIR / "districts" / s
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(build_district_page(d, vendors))
    print(f"✓ {len(live)} district pages built")

    # 404
    (DIST_DIR / "404.html").write_text(head("Page not found | KidharMilega", "This page doesn't exist.") + nav() + """
<div class="container" style="padding:100px 0;text-align:center">
  <div style="font-size:64px;margin-bottom:24px">🗺️</div>
  <h1 style="font-family:var(--font-display);font-size:36px;margin-bottom:12px">Yahan kuch nahi hai</h1>
  <p style="color:var(--mid);margin-bottom:28px">This page doesn't exist. Let's get you back on track.</p>
  <a href="/index.html" class="btn btn-primary">Back to Home</a>
</div>""" + footer() + "</body></html>")

    # GitHub Pages config
    (DIST_DIR / ".nojekyll").write_text("")

    # CNAME (if using custom domain)
    # (DIST_DIR / "CNAME").write_text("kidharmilega.in")

    print(f"\n✅ Build complete → dist/ ({len(list(DIST_DIR.rglob('*.html')))} HTML files)")
    print("   Run: cd dist && python -m http.server 8000  to preview locally")
    print("   Then push dist/ to GitHub Pages to deploy\n")

if __name__ == "__main__":
    build()
