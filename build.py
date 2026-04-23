#!/usr/bin/env python3
import csv, os, shutil, re, sys
from pathlib import Path
from datetime import datetime

SITE_URL   = "https://kidharmilega.in"
IG_HANDLE  = "@startupwalebhaia"
BUILD_DATE = datetime.now().strftime("%B %Y")
CSV_URL_DISTRICTS = "YOUR_GOOGLE_SHEET_CSV_URL_HERE"
CSV_URL_VENDORS   = "YOUR_VENDORS_SHEET_CSV_URL_HERE"

# GitHub Pages subfolder = '/kidharmilega'  |  Custom domain = ''
BASE_PATH = '/kidharmilega'

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DIST_DIR = BASE_DIR / "docs"

def p(path): return BASE_PATH + path

def load_csv(local_path, remote_url=None):
    if "--live" in sys.argv and remote_url and not remote_url.startswith("YOUR_"):
        import urllib.request
        with urllib.request.urlopen(remote_url) as r:
            return list(csv.DictReader(r.read().decode("utf-8").splitlines()))
    with open(local_path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def esc(t):
    if not t: return ""
    return str(t).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def slug(t):
    return re.sub(r"[^a-z0-9-]","",re.sub(r"\s+","-",str(t).lower().strip()))

def nav(active="home"):
    links = [("Home",p("/index.html"),"home"),("ODOP Directory",p("/odop/index.html"),"odop"),
             ("Events",p("/events/index.html"),"events"),("Vendors",p("/vendors/index.html"),"vendors")]
    items = "".join(f'<a href="{href}"{" class=\"active\"" if k==active else ""}>{label}</a>' for label,href,k in links)
    return f'''<nav class="site-nav"><div class="nav-inner">
  <a href="{p('/index.html')}" class="nav-logo"><img src="{p('/assets/logo.png')}" alt="KidharMilega" class="nav-logo-img"></a>
  <div class="nav-links">{items}</div>
  <a href="https://instagram.com/startupwalebhaia" class="nav-ig" target="_blank">{IG_HANDLE}</a>
</div></nav>'''

def footer():
    return f'''<footer class="site-footer"><div class="footer-inner">
  <div class="footer-brand"><img src="{p('/assets/logo.png')}" alt="KidharMilega" style="height:28px;width:auto"></div>
  <div class="footer-links">
    <a href="{p('/index.html')}">Home</a>
    <a href="{p('/odop/index.html')}">ODOP Directory</a>
    <a href="{p('/events/index.html')}">Events</a>
    <a href="{p('/vendors/index.html')}">Vendors</a>
  </div>
  <div class="footer-meta">Built by <a href="https://instagram.com/startupwalebhaia" target="_blank">{IG_HANDLE}</a> · {BUILD_DATE}</div>
</div></footer>'''

# AllEvents.in widget helpers
# Maps ODOP category → AllEvents category parameter
AE_CATEGORY = {
    "Textiles & Handloom":   "Exhibitions",
    "Handicrafts & Pottery": "Exhibitions",
    "Art & Painting":        "Art",
    "Food & Agriculture":    "Food & Drinks",
    "Metal Craft":           "Exhibitions",
    "Manufacturing":         "Exhibitions",
    "Primary":               "Business",
    "Marine":                "Business",
}

# State → nearest large city for the fallback widget
AE_FALLBACK = {
    "Uttar Pradesh": "Lucknow", "Bihar": "Patna", "Rajasthan": "Jaipur",
    "Gujarat": "Ahmedabad", "Karnataka": "Bengaluru", "Tamil Nadu": "Chennai",
    "Maharashtra": "Mumbai", "West Bengal": "Kolkata", "Andhra Pradesh": "Hyderabad",
    "Telangana": "Hyderabad", "Madhya Pradesh": "Bhopal", "Punjab": "Chandigarh",
    "Haryana": "Delhi", "Himachal Pradesh": "Delhi", "Uttarakhand": "Dehradun",
    "Jharkhand": "Ranchi", "Odisha": "Bhubaneswar", "Chhattisgarh": "Raipur",
    "Assam": "Guwahati", "Kerala": "Kochi", "Goa": "Panaji",
    "Delhi": "Delhi", "Arunachal Pradesh": "Guwahati", "Manipur": "Imphal",
    "Meghalaya": "Shillong", "Mizoram": "Aizawl", "Nagaland": "Dimapur",
    "Sikkim": "Gangtok", "Tripura": "Agartala",
}

AE_SCRIPT = '<script src="https://allevents.in/scripts/public/ae-plugin-embed-lib.js"></script>'

def ae_widget(city, category="Business", height=480):
    """Single AllEvents embed div (script loaded once per page via AE_SCRIPT)."""
    return (
        f'<div class="ae-embed-plugin" data-type="city" data-cityname="{esc(city)}" '
        f'data-category="{esc(category)}" data-height="{height}" data-width="100%" '
        f'data-header="1" data-border="0" data-transparency=""></div>'
    )

def ae_events_section(district, state, odop_category=""):
    """Primary widget for the district + always-visible fallback for the state metro."""
    ae_cat    = AE_CATEGORY.get(odop_category, "Business")
    fb_city   = AE_FALLBACK.get(state, "Delhi")
    return f'''<div class="ae-primary">
  <div class="ae-section-label">Events near {esc(district)}</div>
  {ae_widget(district, ae_cat)}
</div>
<div class="ae-fallback" style="margin-top:32px">
  <div class="ae-section-label">Trade events near {esc(fb_city)} &amp; across India</div>
  {ae_widget(fb_city, "Business")}
</div>'''

def head(title, desc, canonical="", image=None):
    og_image = image if image else f"{SITE_URL}{BASE_PATH}/data/logo.png"
    return f'''<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE_URL}{canonical}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{og_image}">
<meta property="og:type" content="website">
<link rel="icon" type="image/png" href="{p('/assets/logo.png')}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,600;0,9..144,900;1,9..144,300&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{p('/assets/style.css')}">
</head><body>'''

def build_homepage(districts):
    live = [d for d in districts if d.get("page_status","").lower()=="live"]
    states = sorted(set(d["state"] for d in live))
    tabs = '<button class="filter-tab active" onclick="filterDistricts(\'all\',this)">All</button>'
    tabs += "".join(f'<button class="filter-tab" onclick="filterDistricts(\'{slug(st)}\',this)">{esc(st)}</button>' for st in states)
    cards = ""
    for d in live:
        gi = '<span class="tag tag-green">GI Tag</span>' if d.get("odop_gi_tag","").lower()=="yes" else ""
        cards += f'''<a href="{p('/districts/')}{esc(d['url_slug'])}/index.html" class="district-card" data-state="{slug(d['state'])}">
  <div class="district-card-head"><div>
    <div class="district-name">{esc(d['district_name'])}</div>
    <div class="district-name-hin">{esc(d.get('district_name_hin',''))}</div>
    <div class="district-product">{esc(d.get('odop_product_name',''))}</div>
  </div><span class="district-arrow">&#8594;</span></div>
  <div class="district-desc">{esc((d.get('famous_for_1_line','') or '')[:100])}</div>
  <div class="district-meta"><span class="tag tag-orange">{esc(d.get('odop_category',''))}</span>{gi}<span class="tag tag-gray">Tier {esc(d.get('tier_priority',''))}</span></div>
</a>'''
    return head("KidharMilega — Find your business opportunity across India",
                "India's small business discovery platform. ODOP products, vendors, events and guides for every district.","/") + nav("home") + f'''
<main><div class="container">
  <section class="hero">
    <div class="hero-eyebrow">India&#39;s Small Business Discovery Platform</div>
    <h1 class="hero-title">Kidhar<br><em>Milega?</em></h1>
    <p class="hero-sub">Every district in India has a product, a market, and an opportunity waiting. We found them all &#8212; vendors, events, schemes and step-by-step guides &#8212; in one place.</p>
    <div class="hero-actions">
      <a href="{p('/odop/index.html')}" class="btn btn-primary">Browse ODOP Directory</a>
      <a href="https://instagram.com/startupwalebhaia" class="btn btn-ghost" target="_blank">Follow the Journey</a>
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
    <div style="margin-bottom:24px"><div class="search-wrap">
      <span class="search-icon">&#9906;</span>
      <input class="search-input" type="text" placeholder="Search district or product..." oninput="searchDistricts(this.value)">
    </div></div>
    <div class="filter-tabs">{tabs}</div>
    <div class="grid-3" id="districtGrid">{cards}</div>
  </section>
  <div class="cta-block">
    <div><div class="cta-title">Building this live on Instagram</div>
    <div class="cta-sub">Follow {IG_HANDLE} &#8212; every district, every data point, documented in public.</div></div>
    <div class="cta-actions"><a href="https://instagram.com/startupwalebhaia" class="btn btn-primary" target="_blank">Follow {IG_HANDLE}</a></div>
  </div>
</div></main>
<script>
function filterDistricts(state,btn){{document.querySelectorAll('.filter-tab').forEach(b=>b.classList.remove('active'));btn.classList.add('active');document.querySelectorAll('.district-card').forEach(c=>{{c.style.display=(state==='all'||c.dataset.state===state)?'':'none';}});}}
function searchDistricts(q){{q=q.toLowerCase();document.querySelectorAll('.district-card').forEach(c=>{{c.style.display=c.textContent.toLowerCase().includes(q)?'':'none';}});}}
</script>''' + footer() + "</body></html>"

def build_master_page():
    return head("KidharMilega — All Business Resources","Your one-stop for ODOP products, trade events, vendor contacts and business opportunities.") + nav() + f"""
<main><div class="container">
  <div class="page-header">
    <div class="section-label">All Resources</div>
    <h1 class="page-header-title">Everything you need to<br><em>build your business</em></h1>
    <p class="page-header-sub">Three directories. All free. Continuously updated.</p>
  </div>
  <div class="master-modules">
    <a href="{p('/odop/index.html')}" class="module-card">
      <div class="module-icon">&#127866;</div>
      <div class="module-title">ODOP Directory</div>
      <div class="module-desc">Every government-recognised ODOP product mapped to its district &#8212; with vendor data, how-to guides and business opportunity breakdown.</div>
      <div class="module-link">Browse ODOP products &#8594;</div>
    </a>
    <a href="{p('/events/index.html')}" class="module-card">
      <div class="module-icon">&#127914;</div>
      <div class="module-title">Events &amp; Expos</div>
      <div class="module-desc">Trade shows, craft fairs, B2B summits and local haats &#8212; across 100 Indian cities. Real-time data.</div>
      <div class="module-link">Browse upcoming events &#8594;</div>
    </a>
    <a href="{p('/vendors/index.html')}" class="module-card">
      <div class="module-icon">&#127981;</div>
      <div class="module-title">Vendor Directory</div>
      <div class="module-desc">Raw material suppliers, manufacturers and distributors &#8212; mapped to each ODOP product and district.</div>
      <div class="module-link">Find vendors &#8594;</div>
    </a>
  </div>
  <div class="cta-block">
    <div><div class="cta-title">Want the full business playbook?</div>
    <div class="cta-sub">Ebook launching soon &#8212; how to launch an ODOP product as a brand and get your first customers.</div></div>
    <div class="cta-actions"><a href="https://instagram.com/startupwalebhaia" class="btn btn-primary" target="_blank">Notify me on Instagram</a></div>
  </div>
</div></main>""" + footer() + "</body></html>"


def build_odop_page(districts):
    live = [d for d in districts if d.get("page_status","").lower()=="live"]
    cats = sorted(set(d.get("odop_category","") for d in live if d.get("odop_category","")))
    tabs = '<button class="filter-tab active" onclick="filterODOP(\'all\',this)">All Categories</button>'
    tabs += "".join(f'<button class="filter-tab" onclick="filterODOP(\'{slug(c)}\',this)">{esc(c)}</button>' for c in cats)
    cards = ""
    for d in live:
        gi = '<span class="tag tag-green">GI Tag</span>' if d.get("odop_gi_tag","").lower()=="yes" else ""
        cards += f'''<a href="{p('/districts/')}{esc(d['url_slug'])}/index.html" class="district-card" data-cat="{slug(d.get('odop_category',''))}">
  <div class="district-card-head"><div>
    <div class="district-name">{esc(d.get('odop_product_name',''))}</div>
    <div class="district-name-hin">{esc(d['district_name'])} &middot; {esc(d['state'])}</div>
  </div><span class="district-arrow">&#8594;</span></div>
  <div class="district-product">{esc(d.get('production_scale',''))}</div>
  <div class="district-desc" style="margin-top:8px">{esc((d.get('why_this_district','') or '')[:110])}...</div>
  <div class="district-meta"><span class="tag tag-orange">{esc(d.get('odop_category',''))}</span>{gi}<span class="tag tag-gray">{esc(d.get('export_potential',''))} export</span></div>
</a>'''
    return head("ODOP Product Directory | KidharMilega","Browse all One District One Product listings across India.","/odop/") + nav("odop") + f'''
<main><div class="container">
  <div class="page-header">
    <div class="section-label">ODOP Directory</div>
    <h1 class="page-header-title">One District,<br><em>One Product</em></h1>
    <p class="page-header-sub">Every government-recognised ODOP product mapped to its district &#8212; market size, export potential and a step-by-step business guide.</p>
  </div>
  <div class="filter-tabs">{tabs}</div>
  <div class="grid-3" id="odopGrid">{cards}</div>
</div></main>
<script>function filterODOP(cat,btn){{document.querySelectorAll('.filter-tab').forEach(b=>b.classList.remove('active'));btn.classList.add('active');document.querySelectorAll('#odopGrid .district-card').forEach(c=>{{c.style.display=(cat==='all'||c.dataset.cat===cat)?'':'none';}});}}</script>''' + footer() + "</body></html>"

def build_events_page():
    return head("Trade Events & Expos | KidharMilega","Find upcoming trade shows and expos across 100 Indian cities.","/events/") + nav("events") + f'''
<main><div class="container">
  <div class="page-header">
    <div class="section-label">Events &amp; Expos</div>
    <h1 class="page-header-title">Trade shows across<br><em>100 Indian cities</em></h1>
    <p class="page-header-sub">Real-time event listings &#8212; trade fairs, B2B summits, craft expos and local haats.</p>
  </div>
  <div class="ae-section-label" style="margin-bottom:12px">Trade events across India</div>
  {ae_widget("Delhi", "Exhibitions")}
  <div class="ae-section-label" style="margin-top:32px;margin-bottom:12px">Business &amp; B2B events</div>
  {ae_widget("Mumbai", "Business")}
</div></main>''' + footer() + AE_SCRIPT + "</body></html>"

def build_vendors_page(vendors, districts):
    cats = sorted(set(v.get("category","") for v in vendors if v.get("category","")))
    tabs = '<button class="filter-tab active" onclick="filterVendors(\'all\',this)">All</button>'
    tabs += "".join(f'<button class="filter-tab" onclick="filterVendors(\'{slug(c)}\',this)">{esc(c)}</button>' for c in cats)
    cards = ""
    for v in vendors:
        is_p = v.get("listing_type","").lower()=="premium"
        p_badge = '<span class="tag tag-orange" style="display:inline-block;margin-bottom:8px">Premium</span><br>' if is_p else ""
        wa = f'<a href="https://wa.me/91{esc(v["contact_whatsapp"])}" class="btn btn-sm btn-primary" target="_blank">WhatsApp</a>' if v.get("contact_whatsapp","") else ""
        cards += f'''<div class="vendor-card{" premium" if is_p else ""}" data-cat="{slug(v.get('category',''))}">
  {p_badge}<div class="vendor-name">{esc(v.get('vendor_name',''))}</div>
  <div class="vendor-cat">{esc(v.get('category',''))} &middot; {esc(v.get('city',''))}, {esc(v.get('state',''))}</div>
  <div class="vendor-desc">{esc(v.get('description',''))}</div>
  <div class="vendor-actions">{wa}</div></div>'''
    return head("Vendor Directory | KidharMilega","Find verified suppliers for every ODOP product.","/vendors/") + nav("vendors") + f'''
<main><div class="container">
  <div class="page-header">
    <div class="section-label">Vendor Directory</div>
    <h1 class="page-header-title">Find your<br><em>supplier</em></h1>
    <p class="page-header-sub">Verified raw material suppliers and manufacturers &#8212; mapped to each ODOP product and district.</p>
  </div>
  <div style="background:var(--orange-l);border:1px solid var(--orange-m);border-radius:var(--radius);padding:16px 20px;margin-bottom:32px;font-size:14px">
    <strong>Are you a vendor?</strong> Get a premium listing with full contact details.
    <a href="https://instagram.com/startupwalebhaia" target="_blank" style="color:var(--orange);font-weight:600;margin-left:8px">Contact us &#8594;</a>
  </div>
  <div class="filter-tabs">{tabs}</div>
  <div class="grid-3" id="vendorGrid">{cards}</div>
</div></main>
<script>function filterVendors(cat,btn){{document.querySelectorAll('.filter-tab').forEach(b=>b.classList.remove('active'));btn.classList.add('active');document.querySelectorAll('#vendorGrid .vendor-card').forEach(c=>{{c.style.display=(cat==='all'||c.dataset.cat===cat)?'':'none';}});}}</script>''' + footer() + "</body></html>"

def build_district_page(d, vendors):
    dv = [v for v in vendors if v.get("district_slug","")==d["url_slug"]]
    snap = [("Population",d.get("population","")),("Area",(d.get("area_km2","")+" km²") if d.get("area_km2","") else ""),
            ("Literacy",(d.get("literacy_rate","")+"%" ) if d.get("literacy_rate","") else ""),
            ("Language",(d.get("main_languages","") or "").split(",")[0].strip()),("Tier",d.get("city_tier","")),("State",d.get("state",""))]
    snap_html = "".join(f'<div class="snapshot-item"><div class="snapshot-val">{esc(v)}</div><div class="snapshot-key">{esc(k)}</div></div>' for k,v in snap if v)
    odop_rows = [("Product",d.get("odop_product_name","")),("Category",d.get("odop_category","")),
                 ("GI Tag",d.get("odop_gi_tag","")+(f' (since {d.get("gi_tag_year","")})' if d.get("gi_tag_year","") else "")),
                 ("Market Size",d.get("production_scale","")),("Export",d.get("export_potential","")),
                 ("Export Markets",d.get("export_countries","")),("Raw Materials",d.get("odop_raw_materials",""))]
    odop_html = "".join(f'<div class="odop-detail-row"><div class="odop-detail-key">{esc(k)}</div><div class="odop-detail-val">{esc(v)}</div></div>' for k,v in odop_rows if v and str(v).strip())
    steps = [("Learn / Research",d.get("step_1_learn","")),("Source Raw Materials",d.get("step_2_source","")),
             ("Produce / Partner",d.get("step_3_produce","")),("Brand & Register",d.get("step_4_brand","")),
             ("First Sale",d.get("step_5_sell","")),("Scale",d.get("step_6_scale",""))]
    steps_html = "".join(f'<div class="step-row"><div class="step-num">{i}</div><div class="step-content"><div class="step-title">{esc(t)}</div><div class="step-desc">{esc(desc)}</div></div></div>' for i,(t,desc) in enumerate(steps,1) if desc)
    names_html = "".join(f'<div class="name-card">{esc(d.get(f"brand_name_idea_{i}",""))}</div>' for i in range(1,6) if d.get(f"brand_name_idea_{i}",""))
    mkt_html = "".join(f'<li style="margin-bottom:10px;font-size:14px;color:var(--mid)">{esc(d.get(f"marketing_idea_{i}",""))}</li>' for i in range(1,4) if d.get(f"marketing_idea_{i}",""))
    streams_html = "".join(f'<div style="display:flex;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid var(--border)"><span style="width:22px;height:22px;background:var(--orange-l);color:var(--orange);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0">{i+1}</span><span style="font-size:14px;color:var(--dark)">{esc(d.get(f"revenue_stream_{i+1}",""))}</span></div>' for i in range(5) if d.get(f"revenue_stream_{i+1}",""))
    vendors_html = ""
    for v in dv:
        is_p = v.get("listing_type","").lower()=="premium"
        wa = f'<a href="https://wa.me/91{esc(v["contact_whatsapp"])}" class="btn btn-sm btn-primary" target="_blank">WhatsApp</a>' if v.get("contact_whatsapp","") else ""
        vendors_html += f'<div class="vendor-card{" premium" if is_p else ""}">{"<span class=\"tag tag-orange\" style=\"display:inline-block;margin-bottom:8px\">Premium</span><br>" if is_p else ""}<div class="vendor-name">{esc(v.get("vendor_name",""))}</div><div class="vendor-cat">{esc(v.get("category",""))} &middot; {esc(v.get("city",""))}</div><div class="vendor-desc" style="margin:8px 0">{esc(v.get("description",""))}</div><div class="vendor-actions">{wa}</div></div>'
    if not vendors_html:
        vendors_html = f'<p style="font-size:14px;color:var(--mid)">Vendor data coming soon. <a href="https://instagram.com/startupwalebhaia" style="color:var(--orange)">DM us to list your business &#8594;</a></p>'
    schemes_html = ""
    for key in ["relevant_central_scheme_1","relevant_central_scheme_2","relevant_state_scheme_1","relevant_state_scheme_2"]:
        val = d.get(key,"")
        if val:
            icon = "&#127963;" if "central" in key else "&#127962;"
            parts = val.split("&#8212;",1) if "&#8212;" in val else val.split("—",1)
            title = parts[0].strip(); desc = parts[1].strip() if len(parts)>1 else ""
            schemes_html += f'<div class="scheme-item"><div class="scheme-icon">{icon}</div><div><div class="scheme-title">{esc(title)}</div><div class="scheme-desc">{esc(desc)}</div></div></div>'
    gi_badge = f'<span class="tag tag-green" style="font-size:13px;padding:5px 12px">&#10003; GI Certified {esc(d.get("gi_tag_year",""))}</span>' if d.get("odop_gi_tag","").lower()=="yes" else ""
    photo    = d.get("odop_photo","").strip()
    photo_html = f'<div class="odop-photo-wrap"><img src="{esc(photo)}" alt="{esc(d.get("odop_product_name",""))} from {esc(d["district_name"])}" class="odop-photo" loading="lazy" onerror="this.parentElement.style.display=\'none\'"></div>' if photo else ""
    return head(d.get("seo_title","") or f'Start a Business in {d["district_name"]} | KidharMilega',
                d.get("meta_description","") or f'Business guide for {d["district_name"]} &#8212; ODOP product, vendors, events and schemes.',
                f'/districts/{d["url_slug"]}/',
                image=photo or None) + nav() + f'''
<main><div class="container">
  <section class="district-hero">
    <div class="breadcrumb"><a href="{p('/index.html')}">Home</a> &#8594; <a href="{p('/odop/index.html')}">ODOP Directory</a> &#8594; {esc(d['district_name'])}</div>
    <div class="district-hero-top"><div>
      <div class="hero-eyebrow">{esc(d['state'])} &middot; {esc(d.get('city_tier',''))}</div>
      <h1 class="district-page-title">Start a business<br>in <span>{esc(d['district_name'])}</span></h1>
      <p class="district-tagline">{esc(d.get('famous_for_1_line',''))}</p>
    </div>{gi_badge}</div>
    <div class="snapshot-grid">{snap_html}</div>
  </section>
  <section class="page-section">
    <div class="section-label">ODOP Product</div>
    <h2 class="section-title">{esc(d.get('odop_product_name',''))}</h2>
    <p class="section-sub">{esc(d.get('why_this_district',''))}</p>
    {photo_html}
    <div class="odop-block">
      <div class="odop-detail-list">{odop_html}</div>
      <div>
        <div style="background:var(--orange-l);border:1px solid var(--orange-m);border-radius:var(--radius-lg);padding:24px;margin-bottom:20px">
          <div style="font-size:12px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--orange);margin-bottom:12px">Business Opportunity</div>
          <div style="display:flex;flex-direction:column;gap:12px">
            <div><div style="font-size:12px;color:var(--light);margin-bottom:2px">Setup Cost Range</div><div style="font-size:16px;font-weight:600;color:var(--dark)">&#8377;{esc(d.get('min_setup_cost',''))} &#8211; &#8377;{esc(d.get('max_setup_cost',''))}</div></div>
            <div><div style="font-size:12px;color:var(--light);margin-bottom:2px">D2C Gross Margin</div><div style="font-size:16px;font-weight:600;color:var(--green)">{esc(d.get('gross_margin_d2c',''))}</div></div>
            <div><div style="font-size:12px;color:var(--light);margin-bottom:2px">Wholesale Margin</div><div style="font-size:16px;font-weight:600">{esc(d.get('gross_margin_wholesale',''))}</div></div>
            <div><div style="font-size:12px;color:var(--light);margin-bottom:2px">Breakeven</div><div style="font-size:16px;font-weight:600">{esc(d.get('breakeven_timeline',''))}</div></div>
          </div>
        </div>
        <div style="background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius-lg);padding:20px">
          <div style="font-size:12px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--mid);margin-bottom:12px">Ideal For</div>
          <p style="font-size:14px;color:var(--dark);margin-bottom:8px"><strong>{esc(d.get('suitable_for',''))}</strong></p>
          <p style="font-size:13px;color:var(--mid)">Not ideal for: {esc(d.get('not_suitable_for',''))}</p>
        </div>
      </div>
    </div>
  </section>
  <section class="page-section">
    <div class="section-label">Revenue Streams</div>
    <h2 class="section-title">How you&#39;ll make money</h2>
    <p class="section-sub">Primary buyer: {esc(d.get('primary_target_audience',''))}</p>
    <div style="max-width:600px">{streams_html}</div>
  </section>
  <section class="page-section">
    <div class="section-label">Step-by-Step Guide</div>
    <h2 class="section-title">How to start</h2>
    <p class="section-sub">From zero to first sale &#8212; concrete steps for {esc(d['district_name'])}.</p>
    <div class="steps-list">{steps_html}</div>
  </section>
  <section class="page-section">
    <div class="section-label">Events &amp; Expos</div>
    <h2 class="section-title">Where to show up</h2>
    <p class="section-sub">Trade fairs, craft expos and B2B summits &#8212; near {esc(d['district_name'])} and across India.</p>
    {ae_events_section(d['district_name'], d.get('state',''), d.get('odop_category',''))}
  </section>
  <section class="page-section">
    <div class="section-label">Vendors &amp; Suppliers</div>
    <h2 class="section-title">Where to source</h2>
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
    <div class="section-label">Government Schemes</div>
    <h2 class="section-title">Free money you didn&#39;t know about</h2>
    <div class="scheme-list" style="margin-bottom:24px">{schemes_html}</div>
    <div style="background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);padding:16px 20px;font-size:14px">
      <strong>Registration required:</strong> {esc(d.get('udyam_registration','Required &#8212; udyamregistration.gov.in'))}
    </div>
  </section>
  <div class="cta-block">
    <div><div class="cta-title">Want the full business playbook?</div>
    <div class="cta-sub">Ebook: How to launch an ODOP product as a brand and get your first customers.</div></div>
    <div class="cta-actions"><a href="https://instagram.com/startupwalebhaia" class="btn btn-primary" target="_blank">Follow {IG_HANDLE}</a></div>
  </div>
</div></main>''' + footer() + AE_SCRIPT + "</body></html>"

def build():
    print(f"\n KidharMilega Builder  [BASE_PATH='{BASE_PATH}']")
    print("="*50)
    if DIST_DIR.exists(): shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)
    for d in ["assets","districts","odop","events","vendors"]: (DIST_DIR/d).mkdir()

    # Write CSS inline (no external file needed)
    css_content = """*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}img{max-width:100%;display:block}a{color:inherit;text-decoration:none}:root{--orange:#00B4D8;--orange-l:#E6F8FD;--orange-m:#7DD8EE;--dark:#111111;--mid:#555555;--light:#888888;--border:#E2EEF2;--bg:#FFFFFF;--bg-2:#F5FBFD;--bg-3:#EAF5F9;--green:#2D7D46;--green-l:#EAF4EE;--blue:#0077A8;--blue-l:#E0F2FA;--radius:10px;--radius-lg:16px;--shadow:0 1px 4px rgba(0,0,0,0.08),0 4px 16px rgba(0,0,0,0.04);--shadow-lg:0 2px 8px rgba(0,0,0,0.10),0 8px 32px rgba(0,0,0,0.06);--font-display:'Fraunces',Georgia,serif;--font-body:'DM Sans',system-ui,sans-serif;--max-w:1120px}body{font-family:var(--font-body);color:var(--dark);background:var(--bg);line-height:1.6;-webkit-font-smoothing:antialiased}h1,h2,h3,h4{font-family:var(--font-display);line-height:1.15}p{color:var(--mid)}.container{max-width:var(--max-w);margin:0 auto;padding:0 24px}.section{padding:80px 0}.section-sm{padding:48px 0}.site-nav{position:sticky;top:0;z-index:100;background:rgba(255,255,255,0.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}.nav-inner{max-width:var(--max-w);margin:0 auto;padding:0 24px;height:60px;display:flex;align-items:center;gap:32px}.nav-logo{display:flex;align-items:center;gap:10px;flex-shrink:0}.logo-mark{background:var(--orange);color:#fff;font-family:var(--font-body);font-weight:700;font-size:11px;letter-spacing:1px;padding:4px 7px;border-radius:4px}.logo-mark.small{font-size:10px;padding:3px 6px}.logo-text{font-family:var(--font-body);font-size:15px;font-weight:400;color:var(--dark)}.logo-text strong{color:var(--orange);font-weight:600}.nav-logo-img{height:36px;width:auto}.nav-links{display:flex;gap:4px;flex:1}.nav-links a{font-size:14px;color:var(--mid);padding:6px 12px;border-radius:6px;transition:all 0.15s}.nav-links a:hover,.nav-links a.active{color:var(--dark);background:var(--bg-3)}.nav-links a.active{color:var(--orange)}.nav-ig{font-size:13px;color:var(--orange);font-weight:500;flex-shrink:0}.nav-ig:hover{text-decoration:underline}.site-footer{border-top:1px solid var(--border);padding:40px 0;background:var(--bg-2);margin-top:80px}.footer-inner{max-width:var(--max-w);margin:0 auto;padding:0 24px;display:flex;align-items:center;gap:32px;flex-wrap:wrap}.footer-brand{display:flex;align-items:center;gap:8px;font-weight:600;font-size:14px}.footer-links{display:flex;gap:20px;flex:1}.footer-links a{font-size:13px;color:var(--mid)}.footer-links a:hover{color:var(--dark)}.footer-meta{font-size:12px;color:var(--light)}.footer-meta a{color:var(--orange)}.btn{display:inline-flex;align-items:center;gap:6px;padding:12px 22px;border-radius:var(--radius);font-size:14px;font-weight:500;font-family:var(--font-body);cursor:pointer;transition:all 0.15s;border:1.5px solid transparent;text-decoration:none}.btn-primary{background:var(--orange);color:#fff;border-color:var(--orange)}.btn-primary:hover{background:#0096B8;border-color:#0096B8}.btn-ghost{background:transparent;color:var(--dark);border-color:var(--border)}.btn-ghost:hover{background:var(--bg-3);border-color:var(--dark)}.btn-sm{padding:8px 14px;font-size:13px}.tag{display:inline-block;font-size:11px;font-weight:500;padding:3px 9px;border-radius:20px;letter-spacing:0.3px}.tag-orange{background:var(--orange-l);color:var(--orange)}.tag-green{background:var(--green-l);color:var(--green)}.tag-blue{background:var(--blue-l);color:var(--blue)}.tag-gray{background:var(--bg-3);color:var(--mid)}.card{background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-lg);padding:24px;transition:box-shadow 0.2s,transform 0.2s}.card:hover{box-shadow:var(--shadow-lg);transform:translateY(-2px)}.grid-2{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:20px}.grid-3{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}.grid-4{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}.hero{padding:80px 0 60px}.hero-eyebrow{font-size:12px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--orange);margin-bottom:20px}.hero-title{font-family:var(--font-display);font-size:clamp(40px,6vw,72px);font-weight:900;line-height:1.05;color:var(--dark);margin-bottom:20px}.hero-title em{font-style:italic;color:var(--orange)}.hero-sub{font-size:18px;color:var(--mid);max-width:560px;line-height:1.7;margin-bottom:36px}.hero-actions{display:flex;gap:12px;flex-wrap:wrap}.stat-strip{display:flex;gap:40px;flex-wrap:wrap;padding:32px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);margin:40px 0}.stat-item{display:flex;flex-direction:column;gap:4px}.stat-val{font-family:var(--font-display);font-size:32px;font-weight:900;color:var(--orange)}.stat-label{font-size:13px;color:var(--light)}.district-card{display:flex;flex-direction:column;gap:14px;padding:24px;border:1px solid var(--border);border-radius:var(--radius-lg);transition:all 0.2s;background:var(--bg);text-decoration:none}.district-card:hover{border-color:var(--orange-m);box-shadow:var(--shadow-lg);transform:translateY(-2px)}.district-card-head{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}.district-name{font-family:var(--font-display);font-size:20px;font-weight:600;color:var(--dark)}.district-name-hin{font-size:14px;color:var(--light);margin-top:2px}.district-product{font-size:14px;font-weight:500;color:var(--orange);margin-top:4px}.district-desc{font-size:13px;color:var(--mid);line-height:1.6}.district-meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:auto;padding-top:12px;border-top:1px solid var(--border)}.district-arrow{font-size:18px;color:var(--border);transition:color 0.2s}.district-card:hover .district-arrow{color:var(--orange)}.district-hero{padding:60px 0 40px;border-bottom:1px solid var(--border)}.district-hero-top{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;flex-wrap:wrap;margin-bottom:24px}.breadcrumb{font-size:13px;color:var(--light);margin-bottom:16px}.breadcrumb a{color:var(--orange)}.district-page-title{font-family:var(--font-display);font-size:clamp(32px,5vw,56px);font-weight:900;color:var(--dark);line-height:1.1}.district-page-title span{color:var(--orange);font-style:italic}.district-tagline{font-size:17px;color:var(--mid);margin-top:12px;max-width:600px;line-height:1.7}.snapshot-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:12px;margin-top:32px}.snapshot-item{background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);padding:16px}.snapshot-val{font-family:var(--font-display);font-size:20px;font-weight:700;color:var(--dark)}.snapshot-key{font-size:12px;color:var(--light);margin-top:4px}.page-section{padding:48px 0;border-bottom:1px solid var(--border)}.page-section:last-of-type{border-bottom:none}.section-label{font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--orange);margin-bottom:12px}.section-title{font-family:var(--font-display);font-size:28px;font-weight:700;color:var(--dark);margin-bottom:8px}.section-sub{font-size:15px;color:var(--mid);margin-bottom:28px;line-height:1.7}.odop-block{display:grid;grid-template-columns:1fr 1fr;gap:40px;align-items:start}@media(max-width:700px){.odop-block{grid-template-columns:1fr}}.odop-detail-list{display:flex;flex-direction:column}.odop-detail-row{display:flex;padding:12px 0;border-bottom:1px solid var(--border);gap:16px}.odop-detail-row:last-child{border-bottom:none}.odop-detail-key{font-size:13px;color:var(--light);min-width:130px;flex-shrink:0}.odop-detail-val{font-size:14px;color:var(--dark);font-weight:500}.steps-list{display:flex;flex-direction:column}.step-row{display:flex;gap:20px;padding:20px 0;border-bottom:1px solid var(--border)}.step-row:last-child{border-bottom:none}.step-num{width:36px;height:36px;background:var(--orange);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;flex-shrink:0;margin-top:2px}.step-content{flex:1}.step-title{font-size:15px;font-weight:600;color:var(--dark);margin-bottom:4px}.step-desc{font-size:14px;color:var(--mid);line-height:1.6}.names-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px}.name-card{background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);padding:14px 16px;font-family:var(--font-display);font-size:16px;font-weight:600;color:var(--dark)}.vendor-card{background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-lg);padding:20px}.vendor-card.premium{border-color:var(--orange-m);background:var(--orange-l)}.vendor-name{font-size:16px;font-weight:600;color:var(--dark);margin-bottom:4px}.vendor-cat{font-size:13px;color:var(--mid);margin-bottom:12px}.vendor-desc{font-size:13px;color:var(--mid);line-height:1.6;margin-bottom:14px}.vendor-actions{display:flex;gap:8px;flex-wrap:wrap}.scheme-list{display:flex;flex-direction:column;gap:12px}.scheme-item{display:flex;gap:16px;padding:16px;background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);align-items:flex-start}.scheme-icon{width:36px;height:36px;background:var(--orange-l);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}.scheme-title{font-size:14px;font-weight:600;color:var(--dark);margin-bottom:3px}.scheme-desc{font-size:13px;color:var(--mid)}.cta-block{background:linear-gradient(135deg,#0077A8 0%,#00B4D8 100%);border-radius:var(--radius-lg);padding:48px;display:flex;gap:32px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-top:60px}.cta-title{font-family:var(--font-display);font-size:28px;font-weight:700;color:#fff;margin-bottom:8px}.cta-sub{font-size:15px;color:rgba(255,255,255,0.6)}.cta-actions{display:flex;gap:12px;flex-shrink:0;flex-wrap:wrap}.search-wrap{position:relative;max-width:480px}.search-input{width:100%;padding:14px 20px 14px 46px;border:1.5px solid var(--border);border-radius:40px;font-size:15px;font-family:var(--font-body);background:var(--bg);color:var(--dark);outline:none;transition:border-color 0.2s}.search-input:focus{border-color:var(--orange)}.search-icon{position:absolute;left:16px;top:50%;transform:translateY(-50%);color:var(--light);font-size:18px;pointer-events:none}.filter-tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:32px}.filter-tab{padding:7px 16px;border-radius:20px;border:1.5px solid var(--border);font-size:13px;font-weight:500;color:var(--mid);cursor:pointer;transition:all 0.15s;background:var(--bg);font-family:var(--font-body)}.filter-tab:hover,.filter-tab.active{border-color:var(--orange);color:var(--orange);background:var(--orange-l)}.events-placeholder{background:var(--bg-2);border:1.5px dashed var(--border);border-radius:var(--radius-lg);padding:40px;text-align:center}.events-placeholder h3{font-family:var(--font-display);font-size:20px;margin-bottom:8px}.page-header{padding:48px 0 32px;border-bottom:1px solid var(--border);margin-bottom:40px}.page-header-title{font-family:var(--font-display);font-size:clamp(28px,4vw,44px);font-weight:900;color:var(--dark);margin-bottom:8px}.page-header-title em{font-style:italic;color:var(--orange)}.page-header-sub{font-size:16px;color:var(--mid);max-width:520px}.master-modules{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:24px;margin-bottom:60px}.module-card{border:1px solid var(--border);border-radius:var(--radius-lg);padding:28px;display:flex;flex-direction:column;gap:16px;transition:all 0.2s;text-decoration:none}.module-card:hover{border-color:var(--orange-m);box-shadow:var(--shadow-lg);transform:translateY(-2px)}.module-icon{font-size:28px}.module-title{font-family:var(--font-display);font-size:22px;font-weight:700;color:var(--dark)}.module-desc{font-size:14px;color:var(--mid);line-height:1.7}.module-link{font-size:13px;color:var(--orange);font-weight:500;margin-top:auto}.odop-photo-wrap{margin-bottom:28px;border-radius:var(--radius-lg);overflow:hidden;border:1px solid var(--border)}.odop-photo{width:100%;max-height:380px;object-fit:cover;display:block}.ae-section-label{font-size:12px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--mid);margin-bottom:12px}.ae-primary,.ae-fallback{border-radius:var(--radius-lg);overflow:hidden}@media(max-width:640px){.container{padding:0 16px}.nav-links{display:none}.section{padding:48px 0}.cta-block{padding:28px}.stat-strip{gap:24px}}"""
    (DIST_DIR/"assets"/"style.css").write_text(css_content)
    # Copy logo
    logo_src = DATA_DIR / "logo.png"
    if logo_src.exists():
        shutil.copy(logo_src, DIST_DIR / "assets" / "logo.png")
    print("✓ CSS + logo written")

    districts = load_csv(DATA_DIR/"districts.csv", CSV_URL_DISTRICTS)
    vendors   = load_csv(DATA_DIR/"vendors.csv",   CSV_URL_VENDORS)
    print(f"✓ Loaded {len(districts)} districts, {len(vendors)} vendors")

    (DIST_DIR/"index.html").write_text(build_homepage(districts))
    print("✓ Homepage")
    (DIST_DIR/"master.html").write_text(build_master_page())
    (DIST_DIR/"odop"/"index.html").write_text(build_odop_page(districts))
    (DIST_DIR/"events"/"index.html").write_text(build_events_page())
    (DIST_DIR/"vendors"/"index.html").write_text(build_vendors_page(vendors, districts))
    print("✓ Directory pages")

    live = [d for d in districts if d.get("page_status","").lower()=="live"]
    for d in live:
        page_dir = DIST_DIR/"districts"/d["url_slug"]
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir/"index.html").write_text(build_district_page(d, vendors))
    print(f"✓ {len(live)} district pages")

    (DIST_DIR/".nojekyll").write_text("")
    total = len(list(DIST_DIR.rglob("*.html")))
    print(f"\n✅ Done → docs/ ({total} HTML files)")
    print(f"   BASE_PATH = '{BASE_PATH}'")
    if BASE_PATH:
        print("   When you switch to custom domain: set BASE_PATH = '' and rebuild\n")

if __name__ == "__main__":
    build()
