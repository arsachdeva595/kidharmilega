#!/usr/bin/env python3
import csv, json, os, shutil, re, sys
from pathlib import Path
from datetime import datetime

SITE_URL   = "https://kidharmilega.in"
IG_HANDLE  = "@startupwalebhaia"
BUILD_DATE = datetime.now().strftime("%B %Y")
CSV_URL_DISTRICTS = "YOUR_GOOGLE_SHEET_CSV_URL_HERE"
CSV_URL_VENDORS   = "YOUR_VENDORS_SHEET_CSV_URL_HERE"

# GitHub Pages subfolder = '/kidharmilega'  |  Custom domain or local = ''
BASE_PATH = '' if '--local' in sys.argv else '/kidharmilega'

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

def product_page_slug(d):
    product = (d.get('odop_product_name','') or d.get('district_name','')).replace('/',' ').replace('&',' ')
    district = d.get('district_name','')
    return slug(product) + "-" + slug(district)

def nav(active="home"):
    links = [("Home",p("/index.html"),"home"),("Products",p("/products/index.html"),"products"),
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
    <a href="{p('/products/index.html')}">Products</a>
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

def head(title, desc, canonical="", image=None, extra_head=""):
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
{extra_head}
</head><body>'''

def build_homepage(districts):
    live = [d for d in districts if d.get("page_status","").lower()=="live"]
    enriched = [d for d in live if d.get("step_1_learn","").strip()]
    featured = (enriched + [d for d in live if d not in enriched])[:5]
    feat_cards = ""
    for d in featured:
        pg = product_page_slug(d)
        gi = '<span class="tag tag-green">GI Tag</span>' if d.get("odop_gi_tag","").lower()=="yes" else ""
        feat_cards += f'''<a href="{p('/products/')}{pg}/index.html" class="district-card">
  <div class="district-card-head"><div>
    <div class="district-name">{esc(d.get('odop_product_name',''))}</div>
    <div class="district-name-hin">{esc(d['district_name'])} &middot; {esc(d['state'])}</div>
  </div><span class="district-arrow">&#8594;</span></div>
  <div class="district-desc">{esc((d.get('famous_for_1_line','') or '')[:110])}</div>
  <div class="district-meta"><span class="tag tag-orange">{esc(d.get('odop_category',''))}</span>{gi}</div>
</a>'''
    search_data = json.dumps([{"n": d.get('odop_product_name','') or d['district_name'], "d": d['district_name'], "s": d['state'], "u": p('/products/') + product_page_slug(d) + '/index.html'} for d in live])
    return (
        head("KidharMilega — Find a Business Idea Near You",
             "Stop chasing metro city jobs. Find high-demand ODOP products, verified manufacturers, and profitable business ideas within 50km of your home. 787 districts mapped.", "/") +
        '<div style="background:#111111;color:#fff;text-align:center;padding:10px 20px;font-size:13px">Stop migrating. <strong style="color:#00B4D8">Your district has a goldmine business</strong> &#8212; real data, zero cost to browse.</div>' +
        nav("home") + f'''
<main><div class="container">
  <section class="hero" style="text-align:center">
    <div class="hero-eyebrow">India&#x2019;s Next Manufacturing Revolution is in Your Backyard</div>
    <h1 class="hero-title" style="max-width:760px;margin-left:auto;margin-right:auto">Stop Chasing &#8377;15k Jobs<br>in Metro Cities.<br><em>Start a Business in Your Own District.</em></h1>
    <p class="hero-sub" style="max-width:600px;margin-left:auto;margin-right:auto">You don&#x2019;t need to migrate to build a future. India&#x2019;s next big manufacturing revolution is happening in your backyard. Find high-demand ODOP products, verified manufacturers, and profitable ideas&#8212;all within 50km of your home.</p>
    <div style="position:relative;max-width:580px;margin:32px auto 20px;display:flex;gap:8px;align-items:center">
      <div style="position:relative;flex:1">
        <span class="search-icon">&#128269;</span>
        <input class="search-input" type="text" id="hpSearch" placeholder="Search your District or a Product (e.g., Makhana, Leather, Silk)..." autocomplete="off">
        <div id="hpResults" style="position:absolute;top:calc(100% + 4px);left:0;right:0;background:#fff;border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow-lg);display:none;max-height:260px;overflow-y:auto;z-index:200;text-align:left"></div>
      </div>
      <a href="{p('/products/index.html')}" class="btn btn-primary" style="flex-shrink:0;white-space:nowrap">Find Opportunity</a>
    </div>
    <div class="stat-strip" style="justify-content:center">
      <div class="stat-item"><div class="stat-val">10+</div><div class="stat-label">Years Ground-Level Experience</div></div>
      <div class="stat-item"><div class="stat-val">15K+</div><div class="stat-label">Entrepreneurs Following</div></div>
      <div class="stat-item"><div class="stat-val">{len(live)}</div><div class="stat-label">Districts Mapped &amp; Counting</div></div>
      <div class="stat-item"><div class="stat-val">550+</div><div class="stat-label">ODOP Products Identified</div></div>
    </div>
  </section>
  <section class="section-sm">
    <div class="section-label">Explore India&#x2019;s Manufacturing Map</div>
    <h2 style="font-family:var(--font-display);font-size:clamp(22px,3vw,32px);font-weight:700;color:var(--dark);margin-bottom:8px">Explore India&#x2019;s Manufacturing Map</h2>
    <p style="font-size:15px;color:var(--mid);margin-bottom:24px">From the Zardozi of Bareilly to the Blue Pottery of Jaipur&#8212;your next venture starts here.</p>
    <div class="grid-3" style="margin-bottom:28px">{feat_cards}</div>
    <div style="text-align:center;padding:8px 0">
      <a href="{p('/products/index.html')}" class="btn btn-ghost">View All {len(live)}+ Districts &#8594;</a>
    </div>
  </section>
  <div style="padding:48px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border)">
    <div class="section-label">Why I Say Build Closer to Home</div>
    <h2 style="font-family:var(--font-display);font-size:clamp(22px,3vw,32px);font-weight:700;color:var(--dark);margin-bottom:8px">&#x201C;The Math Doesn&#x2019;t Add Up.&#x201D;</h2>
    <p style="font-size:15px;color:var(--mid);margin-bottom:28px">A quick honest comparison &#8212; before you book that train ticket to Bangalore.</p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:640px">
      <div style="background:#111;border-radius:var(--radius-lg);padding:28px">
        <div style="font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:rgba(255,255,255,0.45);margin-bottom:16px">&#127961; &#8377;25,000 Salary in Bangalore</div>
        <div style="display:flex;flex-direction:column;gap:8px;font-size:14px">
          <div style="display:flex;justify-content:space-between"><span style="color:rgba(255,255,255,0.6)">Rent</span><span style="color:#fff;font-weight:600">&#8722;&#8377;12,000</span></div>
          <div style="display:flex;justify-content:space-between"><span style="color:rgba(255,255,255,0.6)">Commute</span><span style="color:#fff;font-weight:600">&#8722;&#8377;3,000</span></div>
          <div style="display:flex;justify-content:space-between"><span style="color:rgba(255,255,255,0.6)">Food</span><span style="color:#fff;font-weight:600">&#8722;&#8377;6,000</span></div>
          <div style="border-top:1px solid rgba(255,255,255,0.1);padding-top:8px;margin-top:4px;display:flex;justify-content:space-between"><span style="color:rgba(255,255,255,0.6)">Savings</span><span style="color:#ef4444;font-weight:700;font-size:16px">&#8377;0 left</span></div>
        </div>
      </div>
      <div style="background:var(--orange-l);border:2px solid var(--orange-m);border-radius:var(--radius-lg);padding:28px">
        <div style="font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--orange);margin-bottom:16px">&#127968; &#8377;15,000 Profit at Home</div>
        <div style="display:flex;flex-direction:column;gap:8px;font-size:14px">
          <div style="display:flex;justify-content:space-between"><span style="color:var(--mid)">Rent</span><span style="color:var(--green);font-weight:600">Zero</span></div>
          <div style="display:flex;justify-content:space-between"><span style="color:var(--mid)">Commute</span><span style="color:var(--green);font-weight:600">Zero</span></div>
          <div style="display:flex;justify-content:space-between"><span style="color:var(--mid)">Growth Potential</span><span style="color:var(--green);font-weight:600">Unlimited</span></div>
          <div style="border-top:1px solid var(--orange-m);padding-top:8px;margin-top:4px;display:flex;justify-content:space-between"><span style="color:var(--mid)">Actual Wealth</span><span style="color:var(--green);font-weight:700;font-size:16px">Building &#8593;</span></div>
        </div>
      </div>
    </div>
  </div>
  <div style="padding:48px 0;border-bottom:1px solid var(--border)">
    <div class="section-label">Real Talk. No Gas.</div>
    <h2 style="font-family:var(--font-display);font-size:clamp(22px,3vw,32px);font-weight:700;color:var(--dark);margin-bottom:8px">Catch the Latest on Instagram</h2>
    <p style="font-size:15px;color:var(--mid);margin-bottom:28px">Manufacturing hacks, credit card optimisations for business, and startup reality checks &#8212; no fluff.</p>
    <a href="https://instagram.com/startupwalebhaia" target="_blank" style="display:inline-flex;align-items:center;gap:12px;background:#111;color:#fff;border-radius:var(--radius-lg);padding:20px 28px;text-decoration:none" onmouseover="this.style.opacity=&#x27;0.85&#x27;" onmouseout="this.style.opacity=&#x27;1&#x27;">
      <span style="font-size:28px">&#128247;</span>
      <div>
        <div style="font-size:16px;font-weight:600">@startupwalebhaia</div>
        <div style="font-size:13px;color:rgba(255,255,255,0.5);margin-top:2px">15,000+ entrepreneurs following &middot; Real updates daily</div>
      </div>
      <span style="margin-left:8px;color:rgba(255,255,255,0.4);font-size:18px">&#8594;</span>
    </a>
  </div>
  <div class="cta-block" style="margin-top:60px">
    <div>
      <div class="cta-title">Don&#x2019;t Build Alone. Build with the Tribe.</div>
      <div class="cta-sub">Join the KidharMilega Community. Get access to direct manufacturer contacts, subsidy guides, and a network of 1,000+ local entrepreneurs who are tired of the &#x201C;rat race.&#x201D;</div>
      <div style="font-size:13px;color:rgba(255,255,255,0.5);margin-top:12px">It&#x2019;s free to join, but the insights are worth lakhs.</div>
    </div>
    <div class="cta-actions">
      <a href="https://www.facebook.com/groups/kidharmilega" target="_blank" class="btn btn-primary">Join the KidharMilega Community &#8594;</a>
      <a href="https://instagram.com/startupwalebhaia" target="_blank" class="btn" style="background:rgba(255,255,255,0.1);color:#fff;border-color:rgba(255,255,255,0.2)">Follow @startupwalebhaia</a>
    </div>
  </div>
</div></main>''' + f'<script>var HP_DS={search_data};var si=document.getElementById("hpSearch"),sr=document.getElementById("hpResults");si.addEventListener("input",function(){{var v=this.value.toLowerCase().trim();if(v.length<2){{sr.style.display="none";return;}}var m=HP_DS.filter(function(x){{return x.n.toLowerCase().includes(v)||x.d.toLowerCase().includes(v)||x.s.toLowerCase().includes(v);}}).slice(0,6);if(!m.length){{sr.style.display="none";return;}}sr.innerHTML=m.map(function(x){{return\'<a href="\'+x.u+\'" style="display:flex;flex-direction:column;gap:2px;padding:12px 16px;border-bottom:1px solid #eee;text-decoration:none;color:inherit"><span style="font-size:14px;font-weight:600;color:#111">\'+x.n+\'</span><span style="font-size:12px;color:#888">\'+x.d+" · "+x.s+\'</span></a>\';}}  ).join("");sr.style.display="block";}});document.addEventListener("click",function(e){{if(!si.contains(e.target)&&!sr.contains(e.target))sr.style.display="none";}});</script>' + footer() + "</body></html>"
    )

def build_master_page():
    return head("KidharMilega — All Business Resources","Your one-stop for ODOP products, trade events, vendor contacts and business opportunities.") + nav() + f"""
<main><div class="container">
  <div class="page-header">
    <div class="section-label">All Resources</div>
    <h1 class="page-header-title">Everything you need to<br><em>build your business</em></h1>
    <p class="page-header-sub">Three directories. All free. Continuously updated.</p>
  </div>
  <div class="master-modules">
    <a href="{p('/products/index.html')}" class="module-card">
      <div class="module-icon">&#127866;</div>
      <div class="module-title">Business Opportunities</div>
      <div class="module-desc">Har district ka ODOP product mapped &#8212; market data, vendors, step-by-step guide aur business opportunity breakdown.</div>
      <div class="module-link">Sabhi opportunities dekho &#8594;</div>
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
    tabs = '<button class="filter-tab active" onclick="filterODOP(\'all\',this)">Sab categories</button>'
    tabs += "".join(f'<button class="filter-tab" onclick="filterODOP(\'{slug(c)}\',this)">{esc(c)}</button>' for c in cats)
    cards = ""
    for d in live:
        pg = product_page_slug(d)
        gi = '<span class="tag tag-green">GI Tag</span>' if d.get("odop_gi_tag","").lower()=="yes" else ""
        cards += f'''<a href="{p('/products/')}{pg}/index.html" class="district-card" data-cat="{slug(d.get('odop_category',''))}">
  <div class="district-card-head"><div>
    <div class="district-name">{esc(d.get('odop_product_name',''))}</div>
    <div class="district-name-hin">{esc(d['district_name'])} &middot; {esc(d['state'])}</div>
  </div><span class="district-arrow">&#8594;</span></div>
  <div class="district-product">{esc(d.get('production_scale',''))}</div>
  <div class="district-desc" style="margin-top:8px">{esc((d.get('why_this_district','') or '')[:110])}</div>
  <div class="district-meta"><span class="tag tag-orange">{esc(d.get('odop_category',''))}</span>{gi}<span class="tag tag-gray">{esc(d.get('export_potential',''))} export</span></div>
</a>'''
    return head("Business Opportunities by District | KidharMilega","Har district ka ODOP product aur business opportunity — market size, entry cost, step-by-step guide.","/products/") + nav("products") + f'''
<main><div class="container">
  <div class="page-header">
    <div class="section-label">Business opportunities</div>
    <h1 class="page-header-title">Har district mein<br><em>ek goldmine hai</em></h1>
    <p class="page-header-sub">787 districts. Sab ka ek government-recognised product. Real market data, entry cost, export potential aur step-by-step guide.</p>
  </div>
  <div style="margin-bottom:20px">
    <div style="position:relative;max-width:560px;margin-bottom:16px">
      <span class="search-icon">&#128269;</span>
      <input class="search-input" type="text" id="productSearch" placeholder="Search district, product, or state..." autocomplete="off" oninput="applyFilters()" style="padding-right:20px">
    </div>
    <select id="stateFilter" onchange="applyFilters()" style="padding:7px 16px;border:1.5px solid var(--border);border-radius:20px;font-size:13px;font-weight:500;color:var(--mid);background:var(--bg);font-family:var(--font-body);cursor:pointer;outline:none">
      <option value="">All States</option>
    </select>
  </div>
  <div class="filter-tabs">{tabs}</div>
  <div class="grid-3" id="odopGrid">{cards}</div>
</div></main>
<script>
var _odopCat='all';
function filterODOP(cat,btn){{_odopCat=cat;document.querySelectorAll('.filter-tab').forEach(b=>b.classList.remove('active'));btn.classList.add('active');applyFilters();}}
function applyFilters(){{
  var state=document.getElementById('stateFilter').value;
  var search=document.getElementById('productSearch').value.toLowerCase().trim();
  document.querySelectorAll('#odopGrid .district-card').forEach(function(c){{
    var catOk=_odopCat==='all'||c.dataset.cat===_odopCat;
    var stEl=c.querySelector('.district-name-hin');
    var cardState=stEl?stEl.textContent.split('·')[1]?.trim()||'':'';
    var stateOk=!state||cardState===state;
    var searchOk=!search||c.textContent.toLowerCase().includes(search);
    c.style.display=(catOk&&stateOk&&searchOk)?'':'none';
  }});
}}
document.addEventListener('DOMContentLoaded',function(){{
  var states=new Set();
  document.querySelectorAll('#odopGrid .district-card .district-name-hin').forEach(function(el){{
    var p=el.textContent.split('·');
    if(p[1])states.add(p[1].trim());
  }});
  var sel=document.getElementById('stateFilter');
  [...states].sort().forEach(function(s){{var o=document.createElement('option');o.value=s;o.textContent=s;sel.appendChild(o);}});
}});
</script>''' + footer() + "</body></html>"

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
    return head("Vendor Directory | KidharMilega","Find verified suppliers for every ODOP product.","/vendors/") + nav("vendors") + '''
<main><div class="container">
  <div class="page-header">
    <div class="section-label">Vendor Directory</div>
    <h1 class="page-header-title">Coming<br><em>soon</em></h1>
    <p class="page-header-sub">Verified supplier directory aa raha hai. Tab tak, direct connect karo.</p>
  </div>
  <div style="max-width:560px;margin:0 auto;text-align:center;padding:60px 0 80px">
    <div style="font-size:56px;margin-bottom:24px">&#128274;</div>
    <h2 style="font-family:var(--font-display);font-size:28px;font-weight:700;color:var(--dark);margin-bottom:12px">Vendor Directory &#8212; Work in Progress</h2>
    <p style="font-size:16px;color:var(--mid);line-height:1.7;margin-bottom:32px">Hum verified suppliers ka database bana rahe hain &#8212; har ODOP product ke liye, har district ke liye. Abhi ke liye, <strong>@startupwalebhaia</strong> ke through directly contact karo ya Facebook group join karo.</p>
    <div style="display:flex;flex-direction:column;gap:12px;align-items:center">
      <a href="https://instagram.com/startupwalebhaia" target="_blank" class="btn btn-primary" style="width:260px;justify-content:center">Follow @startupwalebhaia &#8594;</a>
      <a href="https://www.facebook.com/groups/kidharmilega" target="_blank" class="btn btn-ghost" style="width:260px;justify-content:center">Join Facebook Group &#8594;</a>
    </div>
    <p style="font-size:13px;color:var(--light);margin-top:24px">Manufacturers, suppliers, aur raw material contacts &#8212; sab wahan milega.</p>
  </div>
</div></main>''' + footer() + "</body></html>"

def build_district_page(d, vendors, all_districts=[]):
    pg = product_page_slug(d)
    dv = [v for v in vendors if v.get("district_slug","")==d["url_slug"]]

    # Related districts — computed, no new data needed
    same_state = [x for x in all_districts if x.get('state','')==d.get('state','') and x.get('district_name','')!=d.get('district_name','') and x.get('page_status','').lower()=='live'][:4]
    same_cat   = [x for x in all_districts if x.get('odop_category','')==d.get('odop_category','') and x.get('state','')!=d.get('state','') and x.get('page_status','').lower()=='live'][:4]

    # ── Snapshot ──
    snap = [("Population",d.get("population","")),("Area",(d.get("area_km2","")+" km²") if d.get("area_km2","") else ""),
            ("Literacy",(d.get("literacy_rate","")+"%" ) if d.get("literacy_rate","") else ""),
            ("Language",(d.get("main_languages","") or "").split(",")[0].strip()),
            ("City Tier",d.get("city_tier","")),("State",d.get("state",""))]
    snap_html = "".join(f'<div class="snapshot-item"><div class="snapshot-val">{esc(v)}</div><div class="snapshot-key">{esc(k)}</div></div>' for k,v in snap if v)

    # ── Alert strip (new field, skip if empty) ──
    alert = d.get('alert_stat','').strip()
    alert_html = f'<div class="alert-strip">{esc(alert)}</div>' if alert else ''

    # ── For-badge (who this is for) ──
    suitable = d.get('suitable_for','').strip()
    for_badge = f'<div class="for-badge">&#128204; {esc(suitable[:80])} — yeh page tumhare liye hai</div>' if suitable else ''

    # ── Geo anchor (AI-crawlable dense paragraph) ──
    geo = (d.get('geo_anchor','') or d.get('why_this_district','')).strip()
    geo_html = f'<p class="geo-anchor">{esc(geo)}</p>' if geo else ''

    # ── Dark stat bar (key numbers) ──
    kstats = []
    if d.get('production_scale',''): kstats.append((d.get('production_scale','')[:18],'Market'))
    if d.get('gross_margin_d2c',''): kstats.append((d.get('gross_margin_d2c',''),'D2C Margin'))
    if d.get('breakeven_timeline',''): kstats.append((d.get('breakeven_timeline',''),'Breakeven'))
    if d.get('export_potential',''): kstats.append((d.get('export_potential',''),'Export'))
    if d.get('city_tier',''): kstats.append(('Tier '+d.get('city_tier',''),'City'))
    stat_bar_html = ('<div class="stat-bar-dark">'+"".join(f'<div class="stat-bar-item"><span class="sv">{esc(v)}</span><span class="sk">{esc(k)}</span></div>' for v,k in kstats[:5])+'</div>') if kstats else ''

    # ── Opportunity score ring ──
    opp_html = ''
    opp_score = d.get('opportunity_score','').strip()
    if opp_score:
        try:
            deg = float(opp_score)/10*360
            pills = "".join(f'<span class="opp-pill g">&#10003; {esc(d.get(f"relevant_central_scheme_{i}","").split("—")[0].strip()[:40])}</span>' for i in range(1,3) if d.get(f"relevant_central_scheme_{i}",""))
            opp_html = f'<div class="opp-card"><div class="opp-ring" style="background:conic-gradient(var(--orange) {deg:.0f}deg,#2d3a50 0)"><div class="opp-ring-num">{esc(opp_score)}<small>/10</small></div></div><div><div class="opp-label">Opportunity Score &mdash; {esc(d.get("odop_product_name",""))}, {esc(d["district_name"])}</div><div class="opp-title">{esc(d.get("famous_for_1_line","")[:80])}</div><div class="opp-pills">{pills}</div></div></div>'
        except: pass

    # ── ODOP detail table ──
    odop_rows = [("Product",d.get("odop_product_name","")),("Category",d.get("odop_category","")),
                 ("GI Tag",d.get("odop_gi_tag","")+(f' (since {d.get("gi_tag_year","")})' if d.get("gi_tag_year","") else "")),
                 ("Market Size",d.get("production_scale","")),("Export",d.get("export_potential","")),
                 ("Export Markets",d.get("export_countries","")),("Raw Materials",d.get("odop_raw_materials",""))]
    odop_html = "".join(f'<div class="odop-detail-row"><div class="odop-detail-key">{esc(k)}</div><div class="odop-detail-val">{esc(v)}</div></div>' for k,v in odop_rows if v and str(v).strip())

    # ── Business numbers card ──
    biz_rows = []
    if d.get('min_setup_cost',''): biz_rows.append(('Setup cost',f'&#8377;{esc(d.get("min_setup_cost",""))} &ndash; &#8377;{esc(d.get("max_setup_cost",""))}',''))
    if d.get('gross_margin_d2c',''): biz_rows.append(('D2C gross margin',esc(d.get('gross_margin_d2c','')),' g'))
    if d.get('gross_margin_wholesale',''): biz_rows.append(('Wholesale margin',esc(d.get('gross_margin_wholesale','')),''))
    if d.get('breakeven_timeline',''): biz_rows.append(('Breakeven',esc(d.get('breakeven_timeline','')),''))
    biz_html = "".join(f'<div class="biz-row"><span class="bk">{esc(k)}</span><span class="bv{cls}">{v}</span></div>' for k,v,cls in biz_rows)

    # ── Success story ──
    ss_html = ''
    if d.get('success_story_name','').strip():
        ss_nums = "".join(f'<div class="ss-num"><span class="sv">{esc(d.get(f"success_story_{f}",""))}</span><span class="sk">{lbl}</span></div>' for f,lbl in [('cost','Project Cost'),('subsidy','Govt Subsidy'),('employees','Employees')] if d.get(f'success_story_{f}',''))
        src = f'<div class="ss-source">Source: {esc(d.get("success_story_source",""))}</div>' if d.get('success_story_source','') else ''
        ss_html = f'<div class="success-box"><div class="ss-label">&#10003; Verified Success Story</div><div class="ss-name">{esc(d.get("success_story_name",""))}</div><p class="ss-body">{esc(d.get("success_story_desc",""))}</p><div class="ss-nums">{ss_nums}</div>{src}</div>'

    # ── Photo ──
    photo = d.get("odop_photo","").strip()
    photo_html = f'<div class="odop-photo-wrap"><img src="{esc(photo)}" alt="{esc(d.get("odop_product_name",""))} from {esc(d["district_name"])}" class="odop-photo" loading="lazy" onerror="this.parentElement.style.display=\'none\'"></div>' if photo else ""
    gi_badge = f'<span class="tag tag-green" style="font-size:13px;padding:5px 12px">&#10003; GI Certified {esc(d.get("gi_tag_year",""))}</span>' if d.get("odop_gi_tag","").lower()=="yes" else ""

    # ── Revenue flow (contextual from revenue_stream_N fields) ──
    _sm  = [d.get('gross_margin_d2c','').strip(), d.get('gross_margin_wholesale','').strip(), d.get('export_margin','').strip()]
    _rss = [d.get(f'revenue_stream_{i}','').strip() for i in range(1,6)]
    _rss = [rs for rs in _rss if rs]
    rev_html = ''
    if _rss:
        _rows = ''
        for _i, _rs in enumerate(_rss):
            _sp    = _rs.split(' — ', 1) if ' — ' in _rs else (_rs.split(' - ', 1) if ' - ' in _rs else None)
            _label = _sp[0].strip()[:55] if _sp else ' '.join(_rs.split()[:5])
            _desc  = (_sp[1].strip() if len(_sp) > 1 else _rs)[:100] if _sp else _rs[:100]
            _mgn   = _sm[_i] if _i < len(_sm) else ''
            _is_p  = _i == 0
            _s_sty = '' if _is_p else ' style="background:var(--border);color:var(--mid)"'
            _r_cls = ' primary' if _is_p else ''
            _m_sty = '' if _is_p else ' style="color:var(--mid)"'
            _m_htm = f'<div class="rev-margin"{_m_sty}>{esc(_mgn)}</div>' if _mgn else ''
            _rows += f'<div class="rev-row{_r_cls}"><div class="rev-step"{_s_sty}>{_i+1}</div><div><div class="ri-name">{esc(_label)}</div><div class="ri-desc">{esc(_desc)}</div></div>{_m_htm}</div>'
            if _i < len(_rss) - 1:
                _rows += '<div class="rev-arr">&#8595;</div>'
        rev_html = f'<div class="rev-flow">{_rows}</div>'

    # ── Steps (dark numbered boxes) ──
    step_labels = ["Learn / Research","Source Raw Materials","Produce / Partner","Brand &amp; Register","First Sale","Scale"]
    step_keys   = ["step_1_learn","step_2_source","step_3_produce","step_4_brand","step_5_sell","step_6_scale"]
    steps_html  = "".join(f'<div class="step-row"><div class="step-num-dark">{i+1}</div><div class="step-content"><div class="step-title">{step_labels[i]}</div><div class="step-desc">{esc(d.get(k,""))}</div></div></div>' for i,k in enumerate(step_keys) if d.get(k,''))

    # ── Logistics (new field: pipe-separated "Label: detail") ──
    log_html = ''
    log_raw = d.get('logistics_info','').strip()
    if log_raw:
        icons = {'airport':'&#9992;','port':'&#9875;','seaport':'&#9875;','road':'&#128739;','rail':'&#128644;','power':'&#9889;','raw':'&#128230;'}
        items = ''
        for item in log_raw.split('|'):
            if ':' in item:
                key, val = item.split(':',1)
                icon = next((v for k,v in icons.items() if k in key.strip().lower()), '&#128205;')
                items += f'<div class="log-card"><div class="log-icon">{icon}</div><div class="log-name">{esc(key.strip())}</div><div class="log-detail">{esc(val.strip())}</div></div>'
        if items: log_html = f'<div class="log-grid">{items}</div>'

    # ── Industrial parks (new fields: industrial_park_N_name/desc/tag) ──
    parks_html = ''
    park_items = ''
    for i in range(1,4):
        pn = d.get(f'industrial_park_{i}_name','').strip()
        if pn:
            pd_ = d.get(f'industrial_park_{i}_desc','').strip()
            pt  = d.get(f'industrial_park_{i}_tag','Industrial').strip()
            park_items += f'<div class="park-row"><div><div class="park-name">{esc(pn)}</div><div class="park-desc">{esc(pd_)}</div></div><span class="park-tag">{esc(pt)}</span></div>'
    if park_items: parks_html = f'<div class="park-list">{park_items}</div>'

    # ── Clusters (district product map — new fields) ──
    cluster_html = ''
    if d.get('cluster_2_name','').strip():
        c1 = f'<div class="cluster-card active"><div class="cc-town">{esc(d.get("district_name",""))}</div><div class="cc-name">{esc(d.get("odop_product_name",""))}</div><ul class="cc-facts">{"".join(f"<li>{esc(f)}</li>" for f in [d.get("production_scale",""),d.get("export_potential","")] if f)}</ul></div>'
        cx = "".join(f'<div class="cluster-card"><div class="cc-town">{esc(d.get(f"cluster_{i}_town",""))}</div><div class="cc-name">{esc(d.get(f"cluster_{i}_name",""))}</div><div style="font-size:12px;color:var(--mid);margin-top:4px">{esc(d.get(f"cluster_{i}_desc",""))}</div></div>' for i in range(2,4) if d.get(f'cluster_{i}_name',''))
        cluster_html = f'''<section class="page-section">
  <div class="section-label">District Product Map</div>
  <h2 class="section-title">Sirf ek product nahi &#8212; yeh sab hota hai yahan</h2>
  <div class="cluster-grid">{c1}{cx}</div>
</section><hr class="sec-divider">'''

    # ── FAQ accordion (new fields: faq_N = "Question|||Answer") ──
    faq_items = ''
    for i in range(1,7):
        fv = d.get(f'faq_{i}','').strip()
        if fv and '|||' in fv:
            q,a = fv.split('|||',1)
            faq_items += f'<div class="faq-item"><button class="faq-btn" onclick="toggleFaq(this)">{esc(q.strip())}<span class="faq-icon">+</span></button><div class="faq-body">{esc(a.strip())}</div></div>'
    faq_html = f'<div class="faq-list">{faq_items}</div>' if faq_items else ''

    # ── Schemes ──
    schemes_html = ""
    for key in ["relevant_central_scheme_1","relevant_central_scheme_2","relevant_state_scheme_1","relevant_state_scheme_2"]:
        val = d.get(key,"")
        if val:
            icon = "&#127963;" if "central" in key else "&#127962;"
            parts = val.split("—",1)
            t2 = parts[0].strip(); ds = parts[1].strip() if len(parts)>1 else ""
            schemes_html += f'<div class="scheme-item"><div class="scheme-icon">{icon}</div><div><div class="scheme-title">{esc(t2)}</div><div class="scheme-desc">{esc(ds)}</div></div></div>'

    # ── Vendors ──
    vendors_html = ""
    for v in dv:
        is_p = v.get("listing_type","").lower()=="premium"
        wa = f'<a href="https://wa.me/91{esc(v["contact_whatsapp"])}" class="btn btn-sm btn-primary" target="_blank">WhatsApp</a>' if v.get("contact_whatsapp","") else ""
        vendors_html += f'<div class="vendor-card{" premium" if is_p else ""}">{"<span class=\"tag tag-orange\" style=\"display:inline-block;margin-bottom:8px\">Premium</span><br>" if is_p else ""}<div class="vendor-name">{esc(v.get("vendor_name",""))}</div><div class="vendor-cat">{esc(v.get("category",""))} &middot; {esc(v.get("city",""))}</div><div class="vendor-desc" style="margin:8px 0">{esc(v.get("description",""))}</div><div class="vendor-actions">{wa}</div></div>'
    # DM message is shown permanently as section footer; fallback grid can be empty
    if not vendors_html:
        vendors_html = ''

    # ── Brand names + marketing ──
    names_html = "".join(f'<div class="name-card">{esc(d.get(f"brand_name_idea_{i}",""))}</div>' for i in range(1,6) if d.get(f"brand_name_idea_{i}",""))
    mkt_html   = "".join(f'<li style="margin-bottom:10px;font-size:14px;color:var(--mid)">{esc(d.get(f"marketing_idea_{i}",""))}</li>' for i in range(1,6) if d.get(f"marketing_idea_{i}",""))

    # ── Related districts ──
    rd_html = ''
    if same_state or same_cat:
        sc = "".join(f'<a href="{p("/products/")}{product_page_slug(x)}/index.html" class="rd-chip">{esc(x["district_name"])}<span class="rd-p">{esc(x.get("odop_product_name","")[:28])}</span><span class="rd-s">{esc(x["state"])}</span></a>' for x in same_state)
        cc = "".join(f'<a href="{p("/products/")}{product_page_slug(x)}/index.html" class="rd-chip">{esc(x["district_name"])}<span class="rd-p">{esc(x.get("odop_product_name","")[:28])}</span><span class="rd-s">{esc(x["state"])}</span></a>' for x in same_cat)
        rd_html = '<section class="page-section">'
        if sc: rd_html += f'<div class="rd-label">{esc(d["state"])} ke aur districts</div><div class="rd-grid">{sc}</div>'
        if cc: rd_html += f'<div class="rd-label" style="margin-top:20px">Same category &#8212; {esc(d.get("odop_category",""))}</div><div class="rd-grid">{cc}</div>'
        rd_html += '</section><hr class="sec-divider">'

    market_eyebrow = d.get('production_scale','') or f'{d.get("odop_category","")} &middot; {d.get("state","")}'

    body = f'''
<main><div class="container">
  <section class="district-hero">
    <div class="breadcrumb"><a href="{p('/index.html')}">Home</a> &#8594; <a href="{p('/products/index.html')}">Products</a> &#8594; {esc(d["state"])} &#8594; {esc(d["district_name"])}</div>
    {for_badge}
    <div class="district-hero-top"><div>
      <div class="hero-eyebrow">{esc(market_eyebrow)}</div>
      <h1 class="district-page-title">{esc(d.get("odop_product_name",""))} ki<br>opportunity, <span>{esc(d["district_name"])}</span> mein.</h1>
      {geo_html}
    </div>{gi_badge}</div>
    {stat_bar_html}
    <div class="snapshot-grid">{snap_html}</div>
    {opp_html}
  </section>
  <hr class="sec-divider">
  {cluster_html}
  <section class="page-section">
    <div class="section-label">ODOP Product</div>
    <h2 class="section-title">{esc(d.get("odop_product_name",""))}</h2>
    {photo_html}
    <div class="odop-block">
      <div class="odop-detail-list">{odop_html}</div>
      <div>
        <div class="biz-card"><div class="biz-label">Business Numbers</div>{biz_html}</div>
        <div style="background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius-lg);padding:18px;margin-top:14px">
          <div style="font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--mid);margin-bottom:8px">Suitable For</div>
          <p style="font-size:13px;color:var(--dark)">{esc(d.get("suitable_for",""))}</p>
          {"<p style='font-size:12px;color:var(--light);margin-top:6px'>Not for: "+esc(d.get("not_suitable_for",""))+"</p>" if d.get("not_suitable_for","") else ""}
        </div>
      </div>
    </div>
    {ss_html}
  </section>
  {"<hr class='sec-divider'><section class='page-section'><div class='section-label'>Revenue Streams</div><h2 class='section-title'>Paise kaise aayenge — revenue roadmap</h2><p class='section-sub'>Sequence matter karta hai. Pehle margin validate karo, tab volume.</p><div style='max-width:600px'>"+rev_html+"</div></section>" if rev_html else ""}
  <hr class="sec-divider">
  <section class="page-section">
    <div class="section-label">Step-by-Step Roadmap</div>
    <h2 class="section-title">Zero se pehli sale tak &#8212; actual kaam</h2>
    <p class="section-sub">Har step realistic hai &#8212; {esc(d["district_name"])} ke liye, as is.</p>
    <div class="steps-list">{steps_html}</div>
  </section>
  {"<hr class='sec-divider'><section class='page-section'><div class='section-label'>Logistics &amp; Connectivity</div><h2 class='section-title'>Manufacturer ke liye zaroori info</h2>"+log_html+"</section>" if log_html else ""}
  {"<hr class='sec-divider'><section class='page-section'><div class='section-label'>Where to Set Up</div><h2 class='section-title'>Infrastructure ready hai &#8212; plot lo aur shuru karo</h2>"+parks_html+"</section>" if parks_html else ""}
  {"<hr class='sec-divider'><section class='page-section'><div class='section-label'>Government Schemes</div><h2 class='section-title'>Woh paisa jo tujhe pata nahi tha</h2><div class='scheme-list' style='margin-bottom:20px'>"+schemes_html+"</div><div class='info-box info-neutral'><strong>Pehla step:</strong> udyamregistration.gov.in &#8212; free, 10 minute. Bina iske koi scheme apply nahi hogi.</div></section>" if schemes_html else ""}
  <hr class="sec-divider">
  <section class="page-section">
    <div class="section-label">Events &amp; Expos</div>
    <h2 class="section-title">Kahan dikhna hai &#8212; buyers yahan milte hain</h2>
    {ae_events_section(d["district_name"], d.get("state",""), d.get("odop_category",""))}
  </section>
  <hr class="sec-divider">
  <section class="page-section">
    <div class="section-label">Vendors &amp; Suppliers</div>
    <h2 class="section-title">Sourcing aur vendors ki tension mat lo</h2>
    {f'<div class="grid-2">{vendors_html}</div>' if vendors_html else ''}
    <p style="margin-top:16px;font-size:14px;color:var(--mid)">Raw material suppliers chahiye for starting this business? <a href="https://instagram.com/startupwalebhaia" style="color:var(--orange);font-weight:600" target="_blank">Instagram pe seedha DM karo &#8594;</a> &#8212; reply milega.</p>
  </section>
  {"<hr class='sec-divider'><section class='page-section'><div class='section-label'>Frequently Asked Questions</div><h2 class='section-title'>Seedhe sawaal, seedhe jawab</h2>"+faq_html+"</section>" if faq_html else ""}
  {"<hr class='sec-divider'><section class='page-section'><div class='section-label'>Brand Name Ideas</div><h2 class='section-title'>Pehle product validate karo, phir brand banao</h2><div class='names-grid'>"+names_html+"</div></section>" if names_html else ""}
  {"<hr class='sec-divider'><section class='page-section'><div class='section-label'>Marketing</div><h2 class='section-title'>Ye marketing ideas try karna mat bhulna</h2><ul style='list-style:none;margin-top:16px'>"+mkt_html+"</ul></section>" if mkt_html else ""}
  <hr class="sec-divider">
  {rd_html}
  <div class="cta-block">
    <div><div class="cta-title">{esc(d["district_name"])} se ho, ya jaane ka plan hai?</div>
    <div class="cta-sub">Is district ke aur founders se connect karo. Sawaal karo, contacts dhundo, community mein shaamil ho.</div></div>
    <div class="cta-actions">
      <a href="https://www.facebook.com/groups/startupwalebhaia" class="btn btn-primary" target="_blank">Find like minded entrepreneurs &#8594;</a>
      <a href="{p('/products/index.html')}" class="btn btn-ghost">Aur districts dekho</a>
    </div>
  </div>
</div></main>'''

    faq_js = '<script>function toggleFaq(btn){var item=btn.closest(".faq-item");var open=item.classList.contains("open");document.querySelectorAll(".faq-item.open").forEach(function(el){el.classList.remove("open")});if(!open)item.classList.add("open");}</script>'

    # ── Schema JSON-LD ──
    schema_parts = []
    schema_parts.append(json.dumps({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":"Home","item":f"{SITE_URL}{BASE_PATH}/"},
        {"@type":"ListItem","position":2,"name":"Products","item":f"{SITE_URL}{BASE_PATH}/products/"},
        {"@type":"ListItem","position":3,"name":d.get("odop_product_name",""),"item":f"{SITE_URL}/products/{pg}/"},
    ]}, ensure_ascii=False))

    prod_s = {"@context":"https://schema.org","@type":"Product","name":d.get("odop_product_name",""),"description":d.get("why_this_district","") or d.get("famous_for_1_line",""),"areaServed":{"@type":"AdministrativeArea","name":d.get("district_name","")+", "+d.get("state","")}}
    if photo: prod_s["image"] = photo
    if d.get("min_setup_cost","") and d.get("max_setup_cost",""): prod_s["offers"] = {"@type":"AggregateOffer","priceCurrency":"INR","lowPrice":d.get("min_setup_cost",""),"highPrice":d.get("max_setup_cost","")}
    schema_parts.append(json.dumps(prod_s, ensure_ascii=False))

    how_steps = [{"@type":"HowToStep","name":step_labels[i],"text":d.get(k,"")} for i,k in enumerate(step_keys) if d.get(k,"")]
    if how_steps: schema_parts.append(json.dumps({"@context":"https://schema.org","@type":"HowTo","name":f"How to start a {d.get('odop_product_name','')} business in {d.get('district_name','')}","description":f"Step-by-step roadmap for {d.get('odop_product_name','')} in {d.get('district_name','')}, {d.get('state','')}","step":how_steps}, ensure_ascii=False))

    faq_entities = [{"@type":"Question","name":d.get(f"faq_{i}","").split("|||")[0].strip(),"acceptedAnswer":{"@type":"Answer","text":d.get(f"faq_{i}","").split("|||")[1].strip()}} for i in range(1,7) if d.get(f"faq_{i}","").strip() and "|||" in d.get(f"faq_{i}","")]
    if faq_entities: schema_parts.append(json.dumps({"@context":"https://schema.org","@type":"FAQPage","mainEntity":faq_entities}, ensure_ascii=False))

    extra_head = "\n".join(f'<script type="application/ld+json">{s}</script>' for s in schema_parts)

    return head(d.get("seo_title","") or f'{d.get("odop_product_name","")} Business in {d["district_name"]} | KidharMilega',
                d.get("meta_description","") or f'{d["district_name"]} mein {d.get("odop_product_name","")} business guide — market size, entry cost, vendors, schemes aur step-by-step roadmap.',
                f'/products/{pg}/', image=photo or None, extra_head=extra_head) + alert_html + nav("products") + body + faq_js + footer() + AE_SCRIPT + "</body></html>"

def build():
    print(f"\n KidharMilega Builder  [BASE_PATH='{BASE_PATH}']")
    print("="*50)
    if DIST_DIR.exists(): shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)
    for d in ["assets","products","events","vendors"]: (DIST_DIR/d).mkdir()

    # Write CSS inline (no external file needed)
    css_content = """*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}img{max-width:100%;display:block}a{color:inherit;text-decoration:none}:root{--orange:#00B4D8;--orange-l:#E6F8FD;--orange-m:#7DD8EE;--dark:#111111;--mid:#555555;--light:#888888;--border:#E2EEF2;--bg:#FFFFFF;--bg-2:#F5FBFD;--bg-3:#EAF5F9;--green:#2D7D46;--green-l:#EAF4EE;--blue:#0077A8;--blue-l:#E0F2FA;--radius:10px;--radius-lg:16px;--shadow:0 1px 4px rgba(0,0,0,0.08),0 4px 16px rgba(0,0,0,0.04);--shadow-lg:0 2px 8px rgba(0,0,0,0.10),0 8px 32px rgba(0,0,0,0.06);--font-display:'Fraunces',Georgia,serif;--font-body:'DM Sans',system-ui,sans-serif;--max-w:1120px}body{font-family:var(--font-body);color:var(--dark);background:var(--bg);line-height:1.6;-webkit-font-smoothing:antialiased}h1,h2,h3,h4{font-family:var(--font-display);line-height:1.15}p{color:var(--mid)}.container{max-width:var(--max-w);margin:0 auto;padding:0 24px}.section{padding:80px 0}.section-sm{padding:48px 0}.site-nav{position:sticky;top:0;z-index:100;background:rgba(255,255,255,0.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}.nav-inner{max-width:var(--max-w);margin:0 auto;padding:0 24px;height:60px;display:flex;align-items:center;gap:32px}.nav-logo{display:flex;align-items:center;gap:10px;flex-shrink:0}.logo-mark{background:var(--orange);color:#fff;font-family:var(--font-body);font-weight:700;font-size:11px;letter-spacing:1px;padding:4px 7px;border-radius:4px}.logo-mark.small{font-size:10px;padding:3px 6px}.logo-text{font-family:var(--font-body);font-size:15px;font-weight:400;color:var(--dark)}.logo-text strong{color:var(--orange);font-weight:600}.nav-logo-img{height:36px;width:auto}.nav-links{display:flex;gap:4px;flex:1}.nav-links a{font-size:14px;color:var(--mid);padding:6px 12px;border-radius:6px;transition:all 0.15s}.nav-links a:hover,.nav-links a.active{color:var(--dark);background:var(--bg-3)}.nav-links a.active{color:var(--orange)}.nav-ig{font-size:13px;color:var(--orange);font-weight:500;flex-shrink:0}.nav-ig:hover{text-decoration:underline}.site-footer{border-top:1px solid var(--border);padding:40px 0;background:var(--bg-2);margin-top:80px}.footer-inner{max-width:var(--max-w);margin:0 auto;padding:0 24px;display:flex;align-items:center;gap:32px;flex-wrap:wrap}.footer-brand{display:flex;align-items:center;gap:8px;font-weight:600;font-size:14px}.footer-links{display:flex;gap:20px;flex:1}.footer-links a{font-size:13px;color:var(--mid)}.footer-links a:hover{color:var(--dark)}.footer-meta{font-size:12px;color:var(--light)}.footer-meta a{color:var(--orange)}.btn{display:inline-flex;align-items:center;gap:6px;padding:12px 22px;border-radius:var(--radius);font-size:14px;font-weight:500;font-family:var(--font-body);cursor:pointer;transition:all 0.15s;border:1.5px solid transparent;text-decoration:none}.btn-primary{background:var(--orange);color:#fff;border-color:var(--orange)}.btn-primary:hover{background:#0096B8;border-color:#0096B8}.btn-ghost{background:transparent;color:var(--dark);border-color:var(--border)}.btn-ghost:hover{background:var(--bg-3);border-color:var(--dark)}.btn-sm{padding:8px 14px;font-size:13px}.tag{display:inline-block;font-size:11px;font-weight:500;padding:3px 9px;border-radius:20px;letter-spacing:0.3px}.tag-orange{background:var(--orange-l);color:var(--orange)}.tag-green{background:var(--green-l);color:var(--green)}.tag-blue{background:var(--blue-l);color:var(--blue)}.tag-gray{background:var(--bg-3);color:var(--mid)}.card{background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-lg);padding:24px;transition:box-shadow 0.2s,transform 0.2s}.card:hover{box-shadow:var(--shadow-lg);transform:translateY(-2px)}.grid-2{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:20px}.grid-3{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}.grid-4{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}.hero{padding:80px 0 60px}.hero-eyebrow{font-size:12px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--orange);margin-bottom:20px}.hero-title{font-family:var(--font-display);font-size:clamp(40px,6vw,72px);font-weight:900;line-height:1.05;color:var(--dark);margin-bottom:20px}.hero-title em{font-style:italic;color:var(--orange)}.hero-sub{font-size:18px;color:var(--mid);max-width:560px;line-height:1.7;margin-bottom:36px}.hero-actions{display:flex;gap:12px;flex-wrap:wrap}.stat-strip{display:flex;gap:40px;flex-wrap:wrap;padding:32px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);margin:40px 0}.stat-item{display:flex;flex-direction:column;gap:4px}.stat-val{font-family:var(--font-display);font-size:32px;font-weight:900;color:var(--orange)}.stat-label{font-size:13px;color:var(--light)}.district-card{display:flex;flex-direction:column;gap:14px;padding:24px;border:1px solid var(--border);border-radius:var(--radius-lg);transition:all 0.2s;background:var(--bg);text-decoration:none}.district-card:hover{border-color:var(--orange-m);box-shadow:var(--shadow-lg);transform:translateY(-2px)}.district-card-head{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}.district-name{font-family:var(--font-display);font-size:20px;font-weight:600;color:var(--dark)}.district-name-hin{font-size:14px;color:var(--light);margin-top:2px}.district-product{font-size:14px;font-weight:500;color:var(--orange);margin-top:4px}.district-desc{font-size:13px;color:var(--mid);line-height:1.6}.district-meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:auto;padding-top:12px;border-top:1px solid var(--border)}.district-arrow{font-size:18px;color:var(--border);transition:color 0.2s}.district-card:hover .district-arrow{color:var(--orange)}.district-hero{padding:60px 0 40px;border-bottom:1px solid var(--border)}.district-hero-top{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;flex-wrap:wrap;margin-bottom:24px}.breadcrumb{font-size:13px;color:var(--light);margin-bottom:16px}.breadcrumb a{color:var(--orange)}.district-page-title{font-family:var(--font-display);font-size:clamp(32px,5vw,56px);font-weight:900;color:var(--dark);line-height:1.1}.district-page-title span{color:var(--orange);font-style:italic}.district-tagline{font-size:17px;color:var(--mid);margin-top:12px;max-width:600px;line-height:1.7}.snapshot-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:12px;margin-top:32px}.snapshot-item{background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);padding:16px}.snapshot-val{font-family:var(--font-display);font-size:20px;font-weight:700;color:var(--dark)}.snapshot-key{font-size:12px;color:var(--light);margin-top:4px}.page-section{padding:48px 0;border-bottom:1px solid var(--border)}.page-section:last-of-type{border-bottom:none}.section-label{font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--orange);margin-bottom:12px}.section-title{font-family:var(--font-display);font-size:28px;font-weight:700;color:var(--dark);margin-bottom:8px}.section-sub{font-size:15px;color:var(--mid);margin-bottom:28px;line-height:1.7}.odop-block{display:grid;grid-template-columns:1fr 1fr;gap:40px;align-items:start}@media(max-width:700px){.odop-block{grid-template-columns:1fr}}.odop-detail-list{display:flex;flex-direction:column}.odop-detail-row{display:flex;padding:12px 0;border-bottom:1px solid var(--border);gap:16px}.odop-detail-row:last-child{border-bottom:none}.odop-detail-key{font-size:13px;color:var(--light);min-width:130px;flex-shrink:0}.odop-detail-val{font-size:14px;color:var(--dark);font-weight:500}.steps-list{display:flex;flex-direction:column}.step-row{display:flex;gap:20px;padding:20px 0;border-bottom:1px solid var(--border)}.step-row:last-child{border-bottom:none}.step-num{width:36px;height:36px;background:var(--orange);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;flex-shrink:0;margin-top:2px}.step-content{flex:1}.step-title{font-size:15px;font-weight:600;color:var(--dark);margin-bottom:4px}.step-desc{font-size:14px;color:var(--mid);line-height:1.6}.names-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px}.name-card{background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);padding:14px 16px;font-family:var(--font-display);font-size:16px;font-weight:600;color:var(--dark)}.vendor-card{background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-lg);padding:20px}.vendor-card.premium{border-color:var(--orange-m);background:var(--orange-l)}.vendor-name{font-size:16px;font-weight:600;color:var(--dark);margin-bottom:4px}.vendor-cat{font-size:13px;color:var(--mid);margin-bottom:12px}.vendor-desc{font-size:13px;color:var(--mid);line-height:1.6;margin-bottom:14px}.vendor-actions{display:flex;gap:8px;flex-wrap:wrap}.scheme-list{display:flex;flex-direction:column;gap:12px}.scheme-item{display:flex;gap:16px;padding:16px;background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);align-items:flex-start}.scheme-icon{width:36px;height:36px;background:var(--orange-l);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}.scheme-title{font-size:14px;font-weight:600;color:var(--dark);margin-bottom:3px}.scheme-desc{font-size:13px;color:var(--mid)}.cta-block{background:linear-gradient(135deg,#0077A8 0%,#00B4D8 100%);border-radius:var(--radius-lg);padding:48px;display:flex;gap:32px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-top:60px}.cta-title{font-family:var(--font-display);font-size:28px;font-weight:700;color:#fff;margin-bottom:8px}.cta-sub{font-size:15px;color:rgba(255,255,255,0.6)}.cta-actions{display:flex;gap:12px;flex-shrink:0;flex-wrap:wrap}.search-wrap{position:relative;max-width:480px}.search-input{width:100%;padding:14px 20px 14px 46px;border:1.5px solid var(--border);border-radius:40px;font-size:15px;font-family:var(--font-body);background:var(--bg);color:var(--dark);outline:none;transition:border-color 0.2s}.search-input:focus{border-color:var(--orange)}.search-icon{position:absolute;left:16px;top:50%;transform:translateY(-50%);color:var(--light);font-size:18px;pointer-events:none}.filter-tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:32px}.filter-tab{padding:7px 16px;border-radius:20px;border:1.5px solid var(--border);font-size:13px;font-weight:500;color:var(--mid);cursor:pointer;transition:all 0.15s;background:var(--bg);font-family:var(--font-body)}.filter-tab:hover,.filter-tab.active{border-color:var(--orange);color:var(--orange);background:var(--orange-l)}.events-placeholder{background:var(--bg-2);border:1.5px dashed var(--border);border-radius:var(--radius-lg);padding:40px;text-align:center}.events-placeholder h3{font-family:var(--font-display);font-size:20px;margin-bottom:8px}.page-header{padding:48px 0 32px;border-bottom:1px solid var(--border);margin-bottom:40px}.page-header-title{font-family:var(--font-display);font-size:clamp(28px,4vw,44px);font-weight:900;color:var(--dark);margin-bottom:8px}.page-header-title em{font-style:italic;color:var(--orange)}.page-header-sub{font-size:16px;color:var(--mid);max-width:520px}.master-modules{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:24px;margin-bottom:60px}.module-card{border:1px solid var(--border);border-radius:var(--radius-lg);padding:28px;display:flex;flex-direction:column;gap:16px;transition:all 0.2s;text-decoration:none}.module-card:hover{border-color:var(--orange-m);box-shadow:var(--shadow-lg);transform:translateY(-2px)}.module-icon{font-size:28px}.module-title{font-family:var(--font-display);font-size:22px;font-weight:700;color:var(--dark)}.module-desc{font-size:14px;color:var(--mid);line-height:1.7}.module-link{font-size:13px;color:var(--orange);font-weight:500;margin-top:auto}.odop-photo-wrap{margin-bottom:28px;border-radius:var(--radius-lg);overflow:hidden;border:1px solid var(--border)}.odop-photo{width:100%;max-height:380px;object-fit:cover;display:block}.ae-section-label{font-size:12px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--mid);margin-bottom:12px}.ae-primary,.ae-fallback{border-radius:var(--radius-lg);overflow:hidden}.sec-divider{border:none;border-top:1px solid var(--border);margin:0}.alert-strip{background:#111;color:#fff;text-align:center;padding:10px 24px;font-size:13px;font-weight:500;letter-spacing:0.2px}.for-badge{background:var(--orange-l);color:var(--orange);border-radius:20px;padding:7px 16px;font-size:13px;font-weight:500;display:inline-block;margin-bottom:16px}.geo-anchor{font-size:15px;color:var(--mid);line-height:1.8;margin:12px 0 0;max-width:620px}.stat-bar-dark{background:#111;border-radius:var(--radius-lg);padding:18px 28px;display:flex;gap:32px;flex-wrap:wrap;margin:24px 0}.stat-bar-item{display:flex;flex-direction:column;gap:4px}.stat-bar-item .sv{font-family:var(--font-display);font-size:22px;font-weight:900;color:#fff}.stat-bar-item .sk{font-size:11px;color:rgba(255,255,255,0.45);text-transform:uppercase;letter-spacing:1px}.opp-card{display:flex;gap:28px;align-items:center;background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius-lg);padding:24px;margin:24px 0;flex-wrap:wrap}.opp-ring{width:100px;height:100px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0}.opp-ring-num{background:var(--bg);border-radius:50%;width:76px;height:76px;display:flex;align-items:center;justify-content:center;font-family:var(--font-display);font-size:24px;font-weight:900;color:var(--dark)}.opp-ring-num small{font-size:13px;color:var(--light);margin-left:2px}.opp-label{font-size:11px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--light);margin-bottom:6px}.opp-title{font-family:var(--font-display);font-size:18px;font-weight:600;color:var(--dark);margin-bottom:10px}.opp-pills{display:flex;gap:8px;flex-wrap:wrap}.opp-pill{background:var(--green-l);color:var(--green);border-radius:20px;padding:4px 12px;font-size:12px;font-weight:500}.biz-card{background:#111;border-radius:var(--radius-lg);padding:20px 24px}.biz-label{font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:rgba(255,255,255,0.45);margin-bottom:14px}.biz-row{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid rgba(255,255,255,0.08);font-size:14px}.biz-row:last-child{border-bottom:none}.bk{color:rgba(255,255,255,0.55)}.bv{color:#fff;font-weight:600}.bv.g{color:#4ade80}.success-box{background:var(--bg-2);border:1px solid var(--border);border-left:3px solid var(--green);border-radius:var(--radius-lg);padding:24px;margin-top:28px}.ss-label{font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--green);margin-bottom:8px}.ss-name{font-family:var(--font-display);font-size:20px;font-weight:700;color:var(--dark);margin-bottom:8px}.ss-body{font-size:14px;color:var(--mid);line-height:1.7;margin-bottom:16px}.ss-nums{display:flex;gap:28px;flex-wrap:wrap;margin-bottom:8px}.ss-num{display:flex;flex-direction:column;gap:4px}.ss-num .sv{font-family:var(--font-display);font-size:20px;font-weight:800;color:var(--dark)}.ss-num .sk{font-size:12px;color:var(--light)}.ss-source{font-size:12px;color:var(--light);font-style:italic}.rev-flow{display:flex;flex-direction:column;gap:4px;margin-top:20px}.rev-row{display:flex;align-items:center;gap:18px;padding:16px 20px;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg)}.rev-row.primary{background:var(--orange-l);border-color:var(--orange-m)}.rev-row>div:nth-child(2){flex:1}.rev-arr{color:var(--light);font-size:18px;padding:2px 0;line-height:1;padding-left:48px}.rev-step{width:32px;height:32px;background:var(--orange);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0}.rev-step-b{background:#111;color:#fff}.ri-name{font-size:14px;font-weight:600;color:var(--dark);margin-bottom:2px}.ri-desc{font-size:12px;color:var(--mid)}.rev-margin{font-family:var(--font-display);font-size:16px;font-weight:800;color:var(--orange);white-space:nowrap;flex-shrink:0}.step-num-dark{width:38px;height:38px;background:#111;color:#fff;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:15px;flex-shrink:0;margin-top:2px}.log-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin-top:20px}.log-card{background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);padding:16px}.log-icon{font-size:22px;margin-bottom:8px}.log-name{font-size:11px;font-weight:700;color:var(--light);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px}.log-detail{font-size:14px;color:var(--dark);font-weight:500}.park-list{display:flex;flex-direction:column;gap:10px;margin-top:20px}.park-row{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;padding:16px 20px;background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius)}.park-name{font-size:15px;font-weight:600;color:var(--dark);margin-bottom:4px}.park-desc{font-size:13px;color:var(--mid)}.park-tag{background:var(--orange-l);color:var(--orange);border-radius:20px;padding:4px 12px;font-size:11px;font-weight:600;white-space:nowrap;flex-shrink:0}.faq-list{border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden;margin-top:20px}.faq-item{border-bottom:1px solid var(--border)}.faq-item:last-child{border-bottom:none}.faq-btn{width:100%;display:flex;justify-content:space-between;align-items:center;padding:16px 20px;background:var(--bg);border:none;font-size:14px;font-weight:600;color:var(--dark);cursor:pointer;font-family:var(--font-body);text-align:left;gap:16px}.faq-btn:hover{background:var(--bg-2)}.faq-icon{font-size:18px;color:var(--light);flex-shrink:0;transition:transform 0.2s}.faq-item.open .faq-btn{background:var(--bg-2);color:var(--orange)}.faq-item.open .faq-icon{transform:rotate(45deg)}.faq-body{display:none;padding:0 20px 16px;font-size:14px;color:var(--mid);line-height:1.7}.faq-item.open .faq-body{display:block}.rd-label{font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--light);margin-bottom:12px}.rd-grid{display:flex;gap:10px;flex-wrap:wrap}.rd-chip{display:flex;flex-direction:column;gap:3px;padding:12px 16px;border:1px solid var(--border);border-radius:var(--radius);text-decoration:none;transition:all 0.15s;background:var(--bg);min-width:140px}.rd-chip:hover{border-color:var(--orange-m);background:var(--orange-l)}.rd-p{font-size:13px;font-weight:600;color:var(--dark)}.rd-s{font-size:11px;color:var(--light)}.cluster-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;margin-top:20px}.cluster-card{background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius-lg);padding:20px}.cluster-card.active{border-color:var(--orange-m);background:var(--orange-l)}.cc-town{font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--light);margin-bottom:4px}.cc-name{font-family:var(--font-display);font-size:17px;font-weight:700;color:var(--dark);margin-bottom:8px}.cc-facts{list-style:none}.cc-facts li{font-size:12px;color:var(--mid);padding:3px 0}.info-box{border-radius:var(--radius);padding:14px 18px;font-size:14px;line-height:1.6}.info-neutral{background:var(--bg-2);border:1px solid var(--border);color:var(--mid)}@media(max-width:640px){.container{padding:0 16px}.nav-links{display:none}.section{padding:48px 0}.cta-block{padding:28px}.stat-strip{gap:24px}}"""
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
    (DIST_DIR/"products"/"index.html").write_text(build_odop_page(districts))
    (DIST_DIR/"events"/"index.html").write_text(build_events_page())
    (DIST_DIR/"vendors"/"index.html").write_text(build_vendors_page(vendors, districts))
    print("✓ Directory pages")

    live = [d for d in districts if d.get("page_status","").lower()=="live"]
    for d in live:
        page_dir = DIST_DIR/"products"/product_page_slug(d)
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir/"index.html").write_text(build_district_page(d, vendors, districts))
    print(f"✓ {len(live)} district pages")

    (DIST_DIR/".nojekyll").write_text("")
    total = len(list(DIST_DIR.rglob("*.html")))
    print(f"\n✅ Done → docs/ ({total} HTML files)")
    print(f"   BASE_PATH = '{BASE_PATH}'")
    if BASE_PATH:
        print("   When you switch to custom domain: set BASE_PATH = '' and rebuild\n")

if __name__ == "__main__":
    build()
