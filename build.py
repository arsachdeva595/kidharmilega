#!/usr/bin/env python3
import csv, json, os, shutil, re, sys, markdown as md_lib
from pathlib import Path
from datetime import datetime

SITE_URL   = "https://kidharmilega.in"
IG_HANDLE  = "@startupwalebhaia"
BUILD_DATE = datetime.now().strftime("%B %Y")
CSV_URL_DISTRICTS = "YOUR_GOOGLE_SHEET_CSV_URL_HERE"
CSV_URL_VENDORS   = "YOUR_VENDORS_SHEET_CSV_URL_HERE"

# Custom domain: always root. Pass --subfolder only if testing on raw github.io URL.
BASE_PATH = '/kidharmilega' if '--subfolder' in sys.argv else ''

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
    links = [
        ("Home",       p("/index.html"),          "home"),
        ("Products",   p("/products/index.html"),  "products"),
        ("Events",     p("/events/index.html"),    "events"),
        ("Why ODOP?",  p("/what-is-odop/index.html"), "odop-guide"),
        ("About Us",   p("/about-us/index.html"),  "about"),
        ("Contact",    p("/contact/index.html"),   "contact"),
    ]
    items = "".join(f'<a href="{href}"{" class=\"active\"" if k==active else ""}>{label}</a>' for label,href,k in links)
    return f'''<nav class="site-nav" id="siteNav"><div class="nav-inner">
  <a href="{p('/index.html')}" class="nav-logo"><img src="{p('/assets/logo.png')}" alt="KidharMilega" class="nav-logo-img"></a>
  <div class="nav-links" id="navLinks">{items}</div>
  <a href="https://instagram.com/startupwalebhaia" class="nav-ig" target="_blank">{IG_HANDLE}</a>
  <button class="nav-hamburger" id="navHamburger" aria-label="Menu" onclick="(function(){{var n=document.getElementById('navLinks');var b=document.getElementById('navHamburger');var open=n.classList.toggle('nav-open');b.innerHTML=open?'&#10005;':'&#9776;';b.setAttribute('aria-expanded',open);}})()">&#9776;</button>
</div></nav>'''

def footer():
    return f'''<footer class="site-footer"><div class="footer-inner">
  <div class="footer-brand"><img src="{p('/assets/logo.png')}" alt="KidharMilega" style="height:28px;width:auto"></div>
  <div class="footer-links">
    <a href="{p('/index.html')}">Home</a>
    <a href="{p('/products/index.html')}">Products</a>
    <a href="{p('/events/index.html')}">Events</a>
    <a href="{p('/what-is-odop/index.html')}">Why ODOP?</a>
    <a href="{p('/about-us/index.html')}">About Us</a>
    <a href="{p('/team/index.html')}">Team</a>
    <a href="{p('/contact/index.html')}">Contact</a>
    <a href="{p('/terms-of-service/index.html')}">Terms</a>
  </div>
  <div class="footer-meta">Built by <a href="https://instagram.com/startupwalebhaia" target="_blank">{IG_HANDLE}</a> · {BUILD_DATE} · &copy; Rupantran Biz Pvt Ltd</div>
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

EXHIBITION_SLUGS = [
    'exhibitions-in-agra','business-events-in-srinagar','business-events-in-kolkata',
    'exhibitions-in-tiruchirappalli','exhibitions-in-meerut','exhibitions-in-mumbai',
    'exhibitions-in-chandigarh','business-events-in-mumbai','business-events-in-vadodara',
    'exhibitions-in-jodhpur','business-events-in-ahmedabad','business-events-in-kalyan-dombivali',
    'exhibitions-in-gurgaon','business-events-in-delhi','exhibitions-in-vijayawada',
    'exhibitions-in-kalyan-dombivali','business-events-in-chennai','exhibitions-in-ahmedabad',
    'business-events-in-allahabad','business-events-in-indore','exhibitions-in-kanpurup-india',
    'exhibitions-in-vadodara','exhibitions-in-haora','exhibitions-in-pune',
    'exhibitions-in-allahabad','business-events-in-gurgaon','business-events-in-kanpurup-india',
    'events-in-india','business-events-in-jalandhar','exhibitions-in-hyderabad',
    'exhibitions-in-chennai','exhibitions-in-surat','business-events-in-guwahati',
    'exhibitions-in-aligarh','exhibitions-in-belgaum','business-events-in-jaipur',
    'business-events-in-pune','business-events-in-bhopal','business-events-in-surat',
    'business-events-in-pimpri-chinchwad','exhibitions-in-ghaziabad','exhibitions-in-nashik',
    'exhibitions-in-thane','business-events-in-ludhiana','business-events-in-patna',
    'exhibitions-in-mangalore','business-events-in-chandigarh','exhibitions-in-jammu',
    'exhibitions-in-lucknow','exhibitions-in-guwahati','exhibitions-in-dehradun',
    'exhibitions-in-pimpri-chinchwad','business-events-in-navi-mumbai','exhibitions-in-solapur',
    'exhibitions-in-kota','business-events-in-visakhapatnam','business-events-in-aurangabad',
]

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

def gdrive_img(url):
    """Convert Google Drive uc?export=view URLs to thumbnail API format for reliable embedding."""
    if not url:
        return url
    m = re.search(r'[?&]id=([^&]+)', url)
    return f'https://drive.google.com/thumbnail?id={m.group(1)}&sz=w800' if m else url

def parse_wp_shortcode(content):
    """Extract city and category from [city-events city='X' category='Y']."""
    m = re.search(r"\[city-events city='([^']+)' category='([^']+)'", content)
    return (m.group(1), m.group(2)) if m else (None, None)

def strip_wp_blocks(content):
    """Remove WP block comment wrappers and shortcode blocks, return clean HTML."""
    content = re.sub(r'<!-- wp:shortcode -->\s*\[[^\]]*\]\s*<!-- /wp:shortcode -->', '', content, flags=re.DOTALL)
    content = re.sub(r'<!-- wp:shortcode /-->', '', content)
    content = re.sub(r'<!-- /?wp:[^>]*-->', '', content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content.strip()

def head(title, desc, canonical="", image=None, extra_head="", noindex=False):
    og_image = image if image else f"{SITE_URL}{BASE_PATH}/data/logo.png"
    robots_tag = '<meta name="robots" content="noindex, follow">\n' if noindex else ''
    return f'''<!DOCTYPE html><html lang="en"><head>
<!-- Google tag (gtag.js) --><script async src="https://www.googletagmanager.com/gtag/js?id=G-WP8DXGKB1F"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-WP8DXGKB1F');</script>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{robots_tag}<link rel="canonical" href="{SITE_URL}{canonical}">
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
<script>
(function(){{
  // Disable right-click
  document.addEventListener('contextmenu',function(e){{e.preventDefault();}});
  // Disable copy, cut, select-all
  document.addEventListener('copy',function(e){{e.preventDefault();}});
  document.addEventListener('cut',function(e){{e.preventDefault();}});
  // Block DevTools shortcuts and View Source
  document.addEventListener('keydown',function(e){{
    var k=e.key||'';
    // F12
    if(k==='F12'){{e.preventDefault();return false;}}
    // Ctrl/Cmd + Shift + I/J/C (DevTools)
    if((e.ctrlKey||e.metaKey)&&e.shiftKey&&(k==='I'||k==='i'||k==='J'||k==='j'||k==='C'||k==='c')){{e.preventDefault();return false;}}
    // Ctrl/Cmd + U (View Source)
    if((e.ctrlKey||e.metaKey)&&(k==='U'||k==='u')){{e.preventDefault();return false;}}
    // Ctrl/Cmd + S (Save page)
    if((e.ctrlKey||e.metaKey)&&(k==='S'||k==='s')){{e.preventDefault();return false;}}
    // Ctrl/Cmd + A (Select All)
    if((e.ctrlKey||e.metaKey)&&(k==='A'||k==='a')){{e.preventDefault();return false;}}
    // Ctrl/Cmd + P (Print)
    if((e.ctrlKey||e.metaKey)&&(k==='P'||k==='p')){{e.preventDefault();return false;}}
  }});
  // Detect DevTools open via size diff (basic)
  var _dv=false;setInterval(function(){{
    if(window.outerWidth-window.innerWidth>160||window.outerHeight-window.innerHeight>160){{
      if(!_dv){{_dv=true;document.body.innerHTML='<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;font-size:18px;color:#555">Please close DevTools to continue.</div>';}}
    }}else{{_dv=false;}}
  }},1000);
}})();
</script>
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
    hp_schema = json.dumps([
        {"@context":"https://schema.org","@type":"WebSite","name":"KidharMilega","url":f"{SITE_URL}/",
         "description":"Find business opportunities near you — ODOP products, market data, and step-by-step guides for every district in India.",
         "potentialAction":{"@type":"SearchAction","target":{"@type":"EntryPoint","urlTemplate":f"{SITE_URL}/products/?q={{search_term_string}}"},"query-input":"required name=search_term_string"}},
        {"@context":"https://schema.org","@type":"Organization","name":"KidharMilega","url":f"{SITE_URL}/",
         "logo":f"{SITE_URL}/assets/logo.png",
         "sameAs":["https://instagram.com/startupwalebhaia","https://www.facebook.com/groups/startupwalebhaia/"]},
    ], ensure_ascii=False)
    hp_extra_head = f'<script type="application/ld+json">{hp_schema}</script>'
    return (
        head("KidharMilega — Find a Business Idea Near You",
             "Stop chasing metro city jobs. Find high-demand ODOP products, verified manufacturers, and profitable business ideas within 50km of your home. 787 districts mapped.", "/",
             extra_head=hp_extra_head) +
        '<div style="background:#111111;color:#fff;text-align:center;padding:10px 20px;font-size:13px">Stop migrating. <strong style="color:#00B4D8">Your district has a goldmine business</strong> &#8212; real data, zero cost to browse.</div>' +
        nav("home") + f'''
<main><div class="container">
  <section class="hero" style="text-align:center">
    <div class="hero-eyebrow">India&#x2019;s Next Manufacturing Revolution is in Your Backyard</div>
    <h1 class="hero-title" style="max-width:760px;margin-left:auto;margin-right:auto">Stop Chasing &#8377;50k Jobs<br>in Metro Cities.<br><em>Start a Business in Your Own District.</em></h1>
    <p class="hero-sub" style="max-width:600px;margin-left:auto;margin-right:auto">You don&#x2019;t need to migrate to build a future. India&#x2019;s next big manufacturing revolution is happening in your backyard. Find high-demand ODOP products, verified manufacturers, and profitable ideas&#8212;all within 50km of your home.</p>
    <div class="hero-search-row" style="max-width:580px;margin:32px auto 20px">
      <div style="position:relative;flex:1;min-width:0">
        <span class="search-icon">&#128269;</span>
        <input class="search-input" type="text" id="hpSearch" placeholder="Search your District or a Product (e.g., Makhana, Leather, Silk)..." autocomplete="off">
        <div id="hpResults" style="position:absolute;top:calc(100% + 4px);left:0;right:0;background:#fff;border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow-lg);display:none;max-height:260px;overflow-y:auto;z-index:200;text-align:left"></div>
      </div>
      <a href="{p('/products/index.html')}" class="btn btn-primary hero-search-btn">Find Opportunity</a>
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
    <div class="math-grid">
      <div style="background:#111;border-radius:var(--radius-lg);padding:28px">
        <div style="font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:rgba(255,255,255,0.45);margin-bottom:16px">&#127961; &#8377;80,000 Salary in Bangalore</div>
        <div style="display:flex;flex-direction:column;gap:8px;font-size:14px">
          <div style="display:flex;justify-content:space-between"><span style="color:rgba(255,255,255,0.6)">Rent (PG/flat)</span><span style="color:#fff;font-weight:600">&#8722;&#8377;25,000</span></div>
          <div style="display:flex;justify-content:space-between"><span style="color:rgba(255,255,255,0.6)">Commute</span><span style="color:#fff;font-weight:600">&#8722;&#8377;8,000</span></div>
          <div style="display:flex;justify-content:space-between"><span style="color:rgba(255,255,255,0.6)">Food</span><span style="color:#fff;font-weight:600">&#8722;&#8377;15,000</span></div>
          <div style="display:flex;justify-content:space-between"><span style="color:rgba(255,255,255,0.6)">Misc/lifestyle</span><span style="color:#fff;font-weight:600">&#8722;&#8377;15,000</span></div>
          <div style="border-top:1px solid rgba(255,255,255,0.1);padding-top:8px;margin-top:4px;display:flex;justify-content:space-between"><span style="color:rgba(255,255,255,0.6)">Left over</span><span style="color:#ef4444;font-weight:700;font-size:16px">&#8377;17k &#8212; no growth</span></div>
        </div>
      </div>
      <div style="background:var(--orange-l);border:2px solid var(--orange-m);border-radius:var(--radius-lg);padding:28px">
        <div style="font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--orange);margin-bottom:16px">&#127968; &#8377;30k+ Profit at Home</div>
        <div style="display:flex;flex-direction:column;gap:8px;font-size:14px">
          <div style="display:flex;justify-content:space-between"><span style="color:var(--mid)">Rent</span><span style="color:var(--green);font-weight:600">Zero</span></div>
          <div style="display:flex;justify-content:space-between"><span style="color:var(--mid)">Commute</span><span style="color:var(--green);font-weight:600">Zero</span></div>
          <div style="display:flex;justify-content:space-between"><span style="color:var(--mid)">Growth potential</span><span style="color:var(--green);font-weight:600">Unlimited</span></div>
          <div style="border-top:1px solid var(--orange-m);padding-top:8px;margin-top:4px;display:flex;justify-content:space-between"><span style="color:var(--mid)">Actual wealth</span><span style="color:var(--green);font-weight:700;font-size:16px">Building &#8593;</span></div>
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
      <a href="https://www.facebook.com/groups/startupwalebhaia/" target="_blank" class="btn btn-primary">Join the KidharMilega Community &#8594;</a>
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
    states = sorted(set(d['state'] for d in live if d.get('state','')))

    # Sidebar: category checkboxes
    cat_checks = "".join(
        f'<label class="filter-check"><input type="checkbox" class="fcb-cat" value="{slug(c)}" onchange="applyFilters()"><span>{esc(c)}</span></label>'
        for c in cats)

    # Sidebar: state checkboxes (scrollable)
    state_checks = "".join(
        f'<label class="filter-check"><input type="checkbox" class="fcb-state" value="{esc(s)}" onchange="applyFilters()"><span>{esc(s)}</span></label>'
        for s in states)

    # Sidebar: investment radios
    inv_opts = [('','Any Budget'),('u1','Under ₹1L'),('1to5','₹1L – ₹5L'),('5to20','₹5L – ₹20L'),('20plus','₹20L+')]
    inv_radios = "".join(
        f'<label class="filter-check"><input type="radio" name="fInv" value="{v}" onchange="applyFilters()"{" checked" if v=="" else ""}><span>{l}</span></label>'
        for v,l in inv_opts)

    # Sidebar: score radios
    score_opts = [('','Any Score'),('high','High (8–10)'),('mid','Medium (5–7)'),('early','Early Stage (1–4)')]
    score_radios = "".join(
        f'<label class="filter-check"><input type="radio" name="fScore" value="{v}" onchange="applyFilters()"{" checked" if v=="" else ""}><span>{l}</span></label>'
        for v,l in score_opts)

    sidebar = f'''<aside class="filter-sidebar" id="filterSidebar">
  <div class="fsb-head"><span class="fsb-title">Filters</span><button class="fsb-clear" onclick="clearFilters()">Clear all</button></div>
  <div class="filter-group"><div class="fgrp-label">Category</div><div class="fcheck-list">{cat_checks}</div></div>
  <div class="filter-group"><div class="fgrp-label">State</div><div class="fcheck-list fcheck-scroll">{state_checks}</div></div>
  <div class="filter-group"><div class="fgrp-label">Min. Investment</div><div class="fcheck-list">{inv_radios}</div></div>
  <div class="filter-group" style="border-bottom:none"><div class="fgrp-label">Opportunity Score</div><div class="fcheck-list">{score_radios}</div></div>
</aside>'''

    cards = ""
    for d in live:
        pg = product_page_slug(d)
        gi = '<span class="tag tag-green">GI Tag</span>' if d.get("odop_gi_tag","").lower()=="yes" else ""
        min_cost = d.get('min_setup_cost','0') or '0'
        score_val = d.get('opportunity_score','0') or '0'
        cards += f'''<a href="{p('/products/')}{pg}/index.html" class="district-card" data-cat="{slug(d.get('odop_category',''))}" data-state="{esc(d['state'])}" data-min-cost="{min_cost}" data-score="{score_val}">
  <div class="district-card-head"><div>
    <div class="district-name">{esc(d.get('odop_product_name',''))}</div>
    <div class="district-name-hin">{esc(d['district_name'])} &middot; {esc(d['state'])}</div>
  </div><span class="district-arrow">&#8594;</span></div>
  <div class="district-product">{esc(d.get('production_scale',''))}</div>
  <div class="district-desc" style="margin-top:8px">{esc((d.get('why_this_district','') or '')[:110])}</div>
  <div class="district-meta"><span class="tag tag-orange">{esc(d.get('odop_category',''))}</span>{gi}<span class="tag tag-gray">{esc(d.get('export_potential',''))} export</span></div>
</a>'''

    item_list_schema = json.dumps({"@context":"https://schema.org","@type":"ItemList",
        "name":"ODOP Business Opportunities by District — India",
        "description":"One District One Product business opportunities across all districts of India",
        "numberOfItems":len(live),
        "itemListElement":[{"@type":"ListItem","position":i+1,
            "name":f"{d.get('odop_product_name','')} — {d['district_name']}, {d['state']}",
            "url":f"{SITE_URL}/products/{product_page_slug(d)}/"}
            for i,d in enumerate(live[:100])]}, ensure_ascii=False)
    odop_extra_head = f'<script type="application/ld+json">{item_list_schema}</script>'
    return head("Business Opportunities by District | KidharMilega","Har district ka ODOP product aur business opportunity — market size, entry cost, step-by-step guide.","/products/",
                extra_head=odop_extra_head) + nav("products") + f'''
<main><div class="container">
  <div class="page-header">
    <div class="section-label">Business opportunities</div>
    <h1 class="page-header-title">Har district mein<br><em>ek goldmine hai</em></h1>
    <p class="page-header-sub">787 districts. Sab ka ek government-recognised product. Real market data, entry cost, export potential aur step-by-step guide.</p>
  </div>
  <div class="products-topbar">
    <div style="position:relative;flex:1;max-width:520px">
      <span class="search-icon">&#128269;</span>
      <input class="search-input" type="text" id="productSearch" placeholder="Search district, product, or state..." autocomplete="off" oninput="applyFilters()">
    </div>
    <button class="fsb-mobile-toggle" id="fsbToggle" onclick="toggleSidebar()">&#9776; Filters <span class="filter-badge" id="filterBadge" style="display:none">0</span></button>
  </div>
  <div class="products-layout">
    {sidebar}
    <div class="products-main">
      <div class="result-count" id="resultCount"></div>
      <div class="grid-3" id="odopGrid">{cards}</div>
    </div>
  </div>
</div></main>
<script>
function applyFilters(){{
  var search=document.getElementById('productSearch').value.toLowerCase().trim();
  var cats=[...document.querySelectorAll('.fcb-cat:checked')].map(function(x){{return x.value;}});
  var sts=[...document.querySelectorAll('.fcb-state:checked')].map(function(x){{return x.value;}});
  var inv=(document.querySelector('input[name="fInv"]:checked')||{{}}).value||'';
  var sc=(document.querySelector('input[name="fScore"]:checked')||{{}}).value||'';
  var vis=0;
  document.querySelectorAll('#odopGrid .district-card').forEach(function(c){{
    var catOk=cats.length===0||cats.indexOf(c.dataset.cat)>-1;
    var stOk=sts.length===0||sts.indexOf(c.dataset.state)>-1;
    var mc=parseInt(c.dataset.minCost||'0');
    var invOk=true;
    if(inv==='u1')invOk=mc<100000;
    else if(inv==='1to5')invOk=mc>=100000&&mc<500000;
    else if(inv==='5to20')invOk=mc>=500000&&mc<2000000;
    else if(inv==='20plus')invOk=mc>=2000000;
    var sv=parseInt(c.dataset.score||'0');
    var scOk=true;
    if(sc==='high')scOk=sv>=8;
    else if(sc==='mid')scOk=sv>=5&&sv<=7;
    else if(sc==='early')scOk=sv>=1&&sv<=4;
    var srOk=!search||c.textContent.toLowerCase().indexOf(search)>-1;
    var show=catOk&&stOk&&invOk&&scOk&&srOk;
    c.style.display=show?'':'none';
    if(show)vis++;
  }});
  var rc=document.getElementById('resultCount');
  if(rc)rc.textContent=vis+' opportunities found';
  var active=cats.length+sts.length+(inv?1:0)+(sc?1:0);
  var badge=document.getElementById('filterBadge');
  if(badge){{badge.textContent=active;badge.style.display=active>0?'inline-flex':'none';}}
}}
function clearFilters(){{
  document.querySelectorAll('.fcb-cat,.fcb-state').forEach(function(c){{c.checked=false;}});
  var fi=document.querySelector('input[name="fInv"]');if(fi)fi.checked=true;
  var fs=document.querySelector('input[name="fScore"]');if(fs)fs.checked=true;
  document.getElementById('productSearch').value='';
  applyFilters();
}}
function toggleSidebar(){{
  document.getElementById('filterSidebar').classList.toggle('fsb-open');
}}
document.addEventListener('DOMContentLoaded',function(){{applyFilters();}});
</script>''' + footer() + "</body></html>"

def build_events_page(exhibition_posts=None):
    posts = exhibition_posts or []
    cards_html = ''
    for post in posts:
        sv    = post['post_name']
        title = post['post_title']
        raw   = post['post_content']
        first_p = re.search(r'<p[^>]*>(.*?)</p>', raw, re.DOTALL)
        desc    = re.sub(r'<[^>]+>', '', first_p.group(1).strip())[:120] if first_p else ''
        ae_city, _ = parse_wp_shortcode(raw)
        if 'exhibitions' in sv:
            dtype, tlabel, tcls = 'exhibitions', 'Exhibitions', 'tag-orange'
        elif 'business-events' in sv:
            dtype, tlabel, tcls = 'business', 'Business Events', 'tag-blue'
        else:
            dtype, tlabel, tcls = 'general', 'Events', 'tag-gray'
        cards_html += f'''<a href="{p('/')}{sv}/index.html" class="district-card" data-type="{dtype}">
  <div class="district-card-head"><div>
    <div class="district-name">{esc(title)}</div>
    {f'<div class="district-name-hin">{esc(ae_city)}</div>' if ae_city else ''}
  </div><span class="district-arrow">&#8594;</span></div>
  {f'<div class="district-desc">{esc(desc)}</div>' if desc else ''}
  <div class="district-meta"><span class="tag {tcls}">{tlabel}</span></div>
</a>'''
    ftabs = '<button class="filter-tab active" onclick="filterEv(\'all\',this)">All Cities</button><button class="filter-tab" onclick="filterEv(\'exhibitions\',this)">Exhibitions</button><button class="filter-tab" onclick="filterEv(\'business\',this)">Business Events</button>'
    city_section = (f'<div><div class="section-label">Browse by City</div>'
        f'<h2 style="font-family:var(--font-display);font-size:clamp(22px,3vw,32px);font-weight:700;color:var(--dark);margin-bottom:16px">Find Events in Your City</h2>'
        f'<div class="filter-tabs">{ftabs}</div><div class="grid-3" id="evGrid">{cards_html}</div></div>'
        f'<script>function filterEv(t,btn){{document.querySelectorAll(".filter-tab").forEach(b=>b.classList.remove("active"));btn.classList.add("active");document.querySelectorAll("#evGrid .district-card").forEach(function(c){{c.style.display=(t==="all"||c.dataset.type===t)?"":"none";}});}}</script>'
    ) if cards_html else ''
    return head("Trade Events & Expos | KidharMilega","Find upcoming trade shows and expos across 100 Indian cities.","/events/") + nav("events") + f'''
<main><div class="container">
  <div class="page-header">
    <div class="section-label">Events &amp; Expos</div>
    <h1 class="page-header-title">Trade shows across<br><em>100 Indian cities</em></h1>
    <p class="page-header-sub">Real-time event listings &#8212; trade fairs, B2B summits, craft expos and local haats.</p>
  </div>
  {city_section}
</div></main>''' + footer() + AE_SCRIPT + "</body></html>"

def build_exhibition_page(post):
    sv      = post['post_name']
    title   = post['post_title']
    raw     = post['post_content']
    ae_city, ae_cat = parse_wp_shortcode(raw)
    if not ae_cat:
        ae_cat = 'Exhibitions' if 'exhibitions' in sv else 'Business'
    if not ae_city:
        ae_city = 'Delhi'
    clean   = strip_wp_blocks(raw)
    first_p = re.search(r'<p[^>]*>(.*?)</p>', clean, re.DOTALL)
    tagline  = first_p.group(1).strip() if first_p else ''
    body_html = clean[first_p.end():].strip() if first_p else clean
    if 'exhibitions' in sv:
        eyebrow = 'Trade Shows &amp; Exhibitions'
    elif 'business-events' in sv:
        eyebrow = 'Business Events &amp; B2B'
    else:
        eyebrow = 'Events &amp; Expos'
    meta_desc = re.sub(r'<[^>]+>', '', tagline)[:155] or f'Find upcoming {title} — trade shows, exhibitions and business events in India.'
    content_section = (f'<hr class="sec-divider"><section class="page-section"><div class="exhibition-content">{body_html}</div></section>'
                       ) if body_html.strip() else ''
    body = f'''<main><div class="container">
  <section class="district-hero">
    <div class="breadcrumb"><a href="{p('/index.html')}">Home</a> &#8594; <a href="{p('/events/index.html')}">Events &amp; Expos</a> &#8594; {esc(title)}</div>
    <div class="hero-eyebrow">{eyebrow}</div>
    <h1 class="district-page-title">{esc(title)}</h1>
    {f'<p class="district-tagline">{tagline}</p>' if tagline else ''}
  </section>
  <hr class="sec-divider">
  <section class="page-section">
    <div class="section-label">Upcoming Events</div>
    <h2 class="section-title">Events in {esc(ae_city)}</h2>
    <div style="margin-top:16px">{ae_widget(ae_city, ae_cat)}</div>
  </section>
  {content_section}
  <div class="cta-block" style="margin-top:60px">
    <div>
      <div class="cta-title">Explore all city events</div>
      <div class="cta-sub">Browse trade shows, exhibitions and B2B events across 50+ Indian cities.</div>
    </div>
    <div class="cta-actions">
      <a href="{p('/events/index.html')}" class="btn btn-primary">All Events &amp; Cities &#8594;</a>
      <a href="https://www.facebook.com/groups/startupwalebhaia/" target="_blank" class="btn" style="background:rgba(255,255,255,0.1);color:#fff;border-color:rgba(255,255,255,0.2)">Join Community</a>
    </div>
  </div>
</div></main>'''
    return head(f'{title} | KidharMilega', meta_desc, f'/{sv}/') + nav('events') + body + footer() + AE_SCRIPT + '</body></html>'

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
    return head("Vendor Directory | KidharMilega","Find verified suppliers for every ODOP product.","/vendors/",noindex=True) + nav("vendors") + '''
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
      <a href="https://www.facebook.com/groups/startupwalebhaia/" target="_blank" class="btn btn-ghost" style="width:260px;justify-content:center">Join Facebook Group &#8594;</a>
    </div>
    <p style="font-size:13px;color:var(--light);margin-top:24px">Manufacturers, suppliers, aur raw material contacts &#8212; sab wahan milega.</p>
  </div>
</div></main>''' + footer() + "</body></html>"

def build_district_page(d, vendors, all_districts=[], odop_urls=None):
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
    photo = gdrive_img(d.get("odop_photo","").strip())
    photo_html = f'<div class="odop-photo-wrap"><img src="{esc(photo)}" alt="{esc(d.get("odop_product_name",""))} from {esc(d["district_name"])}" class="odop-photo" loading="lazy"></div>' if photo else ""
    gi_badge = f'<span class="tag tag-green" style="font-size:13px;padding:5px 12px">&#10003; GI Certified {esc(d.get("gi_tag_year",""))}</span>' if d.get("odop_gi_tag","").lower()=="yes" else ""

    # ── YouTube + News from odop_urls ──
    url_row    = (odop_urls or {}).get((d.get('state',''), d.get('district_name','')), {})
    yt_ids     = [x.strip() for x in url_row.get('youtube_ids','').split(',') if x.strip()][:2]
    news_links = [x.strip() for x in url_row.get('google_urls','').split('|') if x.strip()][:4]

    yt_html = ''
    if yt_ids:
        iframes = ''.join(
            f'<div class="yt-embed-wrap"><iframe src="https://www.youtube.com/embed/{esc(vid)}" '
            f'title="YouTube video" frameborder="0" allow="accelerometer; autoplay; clipboard-write; '
            f'encrypted-media; gyroscope; picture-in-picture" allowfullscreen loading="lazy"></iframe></div>'
            for vid in yt_ids
        )
        yt_html = (f'<hr class="sec-divider"><section class="page-section">'
            f'<div class="section-label">Video Resources</div>'
            f'<h2 class="section-title">Watch: How It\'s Made &amp; Sold</h2>'
            f'<p class="section-sub">Real process, real margins &#8212; see how this product is actually made and sold before you invest a rupee.</p>'
            f'<div class="yt-grid">{iframes}</div></section>')

    _PUBLISHERS = {
        'timesofindia':'Times of India','economictimes':'Economic Times',
        'thehindu':'The Hindu','hindustantimes':'Hindustan Times',
        'indianexpress':'Indian Express','newindianexpress':'New Indian Express',
        'ndtv':'NDTV','livemint':'Mint','businessstandard':'Business Standard',
        'financialexpress':'Financial Express','pib.gov':'PIB — Govt. of India',
        'india.gov':'India.gov.in','msme.gov':'MSME Ministry',
        'startupindia':'Startup India','investindia':'Invest India',
        'vikaspedia':'Vikaspedia','makingindia':'Make in India',
    }
    def _publisher(url):
        m = re.search(r'https?://(?:www\.)?([^/?]+)', url)
        domain = m.group(1) if m else ''
        for key, name in _PUBLISHERS.items():
            if key in domain:
                return name
        parts = domain.split('.')
        if parts and parts[0] in ('www','en','m','blog'):
            parts = parts[1:]
        return parts[0].replace('-',' ').title() if parts else domain

    def _title(url):
        path = re.sub(r'https?://[^/]+', '', url).rstrip('/')
        # Try each path segment from right to left, pick first meaningful one
        segments = [p for p in path.split('/') if p]
        seg = ''
        for s in reversed(segments):
            s = s.split('?')[0]
            s = re.sub(r'\.(html?|php|aspx|jsp|pdf)$', '', s, flags=re.I)
            if s and not s.isdigit() and len(s) >= 5 and not re.fullmatch(r'[a-z]{1,3}(\..*)?', s, re.I):
                seg = s
                break
        if not seg:
            return 'Read Article'
        # Split CamelCase (e.g. PressReleasePage → Press Release Page)
        seg = re.sub(r'([A-Z][a-z]+)', r' \1', re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', seg)).strip()
        # Hyphens/underscores → spaces, then title case
        title = re.sub(r'[-_]+', ' ', seg).strip()
        title = ' '.join(w.capitalize() for w in title.split())
        return (title[:72] + '…') if len(title) > 72 else title

    news_html = ''
    if news_links:
        cards = ''.join(
            f'<a href="{esc(u)}" class="news-card" target="_blank" rel="noopener">'
            f'<div class="news-source">{esc(_publisher(u))}</div>'
            f'<div class="news-title">{esc(_title(u))}</div>'
            f'<span class="news-arrow">&#8594;</span></a>'
            for u in news_links
        )
        news_html = (f'<hr class="sec-divider"><section class="page-section">'
            f'<div class="section-label">Market Intelligence</div>'
            f'<h2 class="section-title">What\'s Happening in This Market</h2>'
            f'<p class="section-sub">Industry reports and news &#8212; understand the market before you enter it.</p>'
            f'<div class="news-grid">{cards}</div></section>')

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
  {yt_html}
  {"<hr class='sec-divider'><section class='page-section'><div class='section-label'>Revenue Streams</div><h2 class='section-title'>Paise kaise aayenge — revenue roadmap</h2><p class='section-sub'>Sequence matter karta hai. Pehle margin validate karo, tab volume.</p><div style='max-width:600px'>"+rev_html+"</div></section>" if rev_html else ""}
  {news_html}
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
    <h2 class="section-title">Apna brand dikhao &#8212; buyers yahan milte hain</h2>
    <p class="section-sub">Trade fairs aur B2B summits hi woh jagah hai jahan ek sahi deal tumhara business badal sakti hai. Pehli baar jao research ke liye, doosri baar order leke aao. Neeche apna city select karo aur upcoming exhibitions dekho.</p>
    {ae_widget(AE_FALLBACK.get(d.get("state",""), d["district_name"]), AE_CATEGORY.get(d.get("odop_category",""), "Business"))}
  </section>
  <hr class="sec-divider">
  <section class="page-section">
    <div class="section-label">Vendors &amp; Suppliers</div>
    <h2 class="section-title">Sourcing aur vendors ki tension mat lo</h2>
    <p style="font-size:14px;color:var(--mid)">Raw material suppliers chahiye for starting this business? <a href="https://instagram.com/startupwalebhaia" style="color:var(--orange);font-weight:600" target="_blank">Instagram pe seedha DM karo &#8594;</a> &#8212; reply milega.</p>
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

def build_about_page():
    return head("About KidharMilega — Explore Local, Build Global", "Hum kaun hain? KidharMilega ka mission, philosophy, aur proof of concept.", "/about-us/") + nav("about") + '''
<main><div class="container">
  <div class="page-header">
    <div class="section-label">About Us</div>
    <h1 class="page-header-title">Explore Local,<br><em>Build Global.</em></h1>
    <p class="page-header-sub">India ke har district mein ek goldmine chhupi hai. Hum tumhe woh dikhate hain.</p>
  </div>
  <div class="prose-section">
    <div class="prose-block">
      <div class="section-label">The Mission</div>
      <h2 class="section-title">Why We Exist</h2>
      <blockquote class="site-blockquote">"Ek jhooth jo sabko becha gaya hai: Bada aadmi banna hai toh metro city jaana padega. Par mein, tumhe Bheed ka Hissa nahi, kissa banane ke liye zidd pakad kar baitha hu&hellip;"<br><span style="font-size:13px;color:var(--light);display:block;margin-top:8px">— Anmol Ratan Sachdeva, @startupwalebhaia</span></blockquote>
      <p>Most of India's youth is trapped in a Metro-City Rat Race. We are told that success only lives in Bangalore, Gurgaon, or Mumbai. At KidharMilega, we believe that after AI, the service industry is broken, and every desk job is either low-paying or high-intensity.</p>
      <p>Our philosophy is simple: <strong>Explore Local, Build Global.</strong> India has always been a hub for outsourcing services — now it is time to become the world's hub for Exports. Instead of importing white-labeled products from China, we want you to discover the "gold" in your own district: local crafts, unique produce, and manufacturing secrets that have been hidden for decades.</p>
    </div>
    <hr class="sec-divider" style="margin:40px 0">
    <div class="prose-block">
      <div class="section-label">Proof of Concept</div>
      <h2 class="section-title">Hum hawa mein baatein nahi karte.</h2>
      <div class="success-box">
        <div class="ss-label">&#10003; Real Story — August 2025</div>
        <div class="ss-name">17 साल का student. 15 दिन. ₹5 Lakh/month.</div>
        <p class="ss-body">In August 2025, a 17-year-old student worked with us for just 15 days. He identified a local handicraft product in his city, launched it globally via Etsy, and as of today he is generating over ₹5 Lakhs in monthly revenue. He didn't need a fancy degree — he just needed the right information and a local network. That's exactly what KidharMilega provides.</p>
      </div>
    </div>
    <hr class="sec-divider" style="margin:40px 0">
    <div class="prose-block">
      <div class="section-label">Who We Are</div>
      <h2 class="section-title">KidharMilega &mdash; Rupantran Biz Pvt Ltd</h2>
      <p>KidharMilega is an initiative by <strong>Rupantran Biz Pvt Ltd</strong>, led by Startup Wale Bhaia and a team of specialists dedicated to business automation and digital discoverability. Our one goal: aapko dhandhe ka sahi rasta dikhana.</p>
      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:28px">
        <a href="/team/index.html" class="btn btn-ghost">Meet the Team &rarr;</a>
        <a href="https://instagram.com/startupwalebhaia" class="btn btn-primary" target="_blank">Follow @startupwalebhaia</a>
      </div>
    </div>
  </div>
</div></main>''' + footer() + "</body></html>"

def build_team_page():
    team = [
        ("Anmol Ratan Sachdeva", "Founder", "Known as Startup Wale Bhaia, Anmol is a content marketer and consultant who believes in Profit-First businesses. He built KidharMilega to help you skip the rat race.", "https://instagram.com/startupwalebhaia"),
        ("Anshulika", "AI Video Lead Editor", "The wizard behind our product storytelling. Anshulika uses AI to create process videos that show the world how local Indian products are made.", None),
        ("Manish", "Data Entry & Operations", "The Groundwork King. Every single data point — from district names to product categories — passes through Manish's lens to ensure accuracy.", None),
        ("Kshitij", "Lead, Partnerships & Outreach", "The bridge-builder. Kshitij collaborates with creators (some with 20M+ followers) to ensure that local ODOP products get the national spotlight they deserve.", None),
    ]
    cards = ""
    for name, role, bio, link in team:
        initials = "".join(w[0] for w in name.split()[:2]).upper()
        cta = f'<a href="{esc(link)}" class="btn btn-sm btn-ghost" target="_blank" style="margin-top:12px">Instagram &rarr;</a>' if link else ""
        cards += f'''<div class="team-card">
  <div class="team-avatar">{initials}</div>
  <div class="team-name">{esc(name)}</div>
  <div class="team-role">{esc(role)}</div>
  <p class="team-bio">{esc(bio)}</p>
  {cta}
</div>'''
    return head("Our Team | KidharMilega", "Meet the people mapping India's 787 districts — and building the tools to help you find your business.", "/team/") + nav() + f'''
<main><div class="container">
  <div class="page-header">
    <div class="section-label">The Team</div>
    <h1 class="page-header-title">People behind<br><em>the platform</em></h1>
    <p class="page-header-sub">787 districts map karna aasaan kaam nahi. Meet the people who are doing it.</p>
  </div>
  <div class="team-grid">{cards}</div>
</div></main>''' + footer() + "</body></html>"

def build_odop_guide_page():
    raw = (BASE_DIR / "data" / "page content" / "what-is-odop.md").read_text(encoding="utf-8")
    # Strip the frontmatter-style lines at top (URL Slug, Meta Description, ---)
    raw = re.sub(r'^\*\*URL Slug:\*\*.*\n', '', raw)
    raw = re.sub(r'^\*\*Meta Description:\*\*.*\n', '', raw)
    raw = re.sub(r'^---\n', '', raw, count=2)
    html_body = md_lib.markdown(raw, extensions=['tables', 'extra'])
    return head(
        "ODOP Kya Hai? Your First ₹50k Business Idea Is Already Government-Approved | KidharMilega",
        "One District One Product — India's biggest business cheat code. Apne district ka goldmine product, government subsidies, aur pehla ₹50k kaise kamayein.",
        "/what-is-odop/"
    ) + nav("odop-guide") + f'''
<main><div class="container">
  <div class="page-header">
    <div class="section-label">ODOP Guide</div>
    <h1 class="page-header-title">Your first ₹50k business idea<br><em>is government-approved.</em></h1>
    <p class="page-header-sub">Stop migrating. Your district already has a goldmine — you just haven&rsquo;t looked.</p>
  </div>
  <div class="prose-article">{html_body}</div>
  <div class="cta-block" style="margin-top:60px">
    <div>
      <div class="cta-title">Apna district ka product dhundo</div>
      <div class="cta-sub">787 districts. 550+ products. Market data, entry cost, aur step-by-step guide — sab free.</div>
    </div>
    <div class="cta-actions">
      <a href="/products/index.html" class="btn btn-primary">Browse All Districts &rarr;</a>
    </div>
  </div>
</div></main>''' + footer() + "</body></html>"

def build_contact_page():
    return head("Contact KidharMilega", "Partnerships, business queries, or just want to say hello — reach us here.", "/contact/") + nav("contact") + '''
<main><div class="container">
  <div class="page-header">
    <div class="section-label">Contact Us</div>
    <h1 class="page-header-title">Let&rsquo;s talk<br><em>business.</em></h1>
    <p class="page-header-sub">Partnerships, outreach, or just want to connect — we&rsquo;re reachable.</p>
  </div>
  <div class="grid-2" style="max-width:760px;margin-top:40px">
    <div class="contact-card">
      <div class="contact-icon">&#9993;</div>
      <div class="contact-label">Partnerships &amp; Business</div>
      <a href="mailto:contact@kidharmilega.in" class="contact-value">contact@kidharmilega.in</a>
    </div>
    <div class="contact-card">
      <div class="contact-icon">&#128247;</div>
      <div class="contact-label">Community &amp; Direct</div>
      <a href="https://instagram.com/startupwalebhaia" target="_blank" class="contact-value">@startupwalebhaia</a>
    </div>
  </div>
  <div class="contact-address">
    <div class="contact-label" style="margin-bottom:8px">Registered Office</div>
    <p style="font-size:15px;color:var(--dark);font-weight:500">Rupantran Biz Pvt Ltd</p>
    <p style="font-size:14px;color:var(--mid)">First Floor, 56B, Chitrakoot Nagar<br>Udaipur — 313001, Rajasthan</p>
  </div>
</div></main>''' + footer() + "</body></html>"

def build_terms_page():
    return head("Terms of Service | KidharMilega", "The KidharMilega disclaimer and terms of use — plain language, no legalese.", "/terms-of-service/") + nav() + '''
<main><div class="container">
  <div class="page-header">
    <div class="section-label">Terms &amp; Disclaimer</div>
    <h1 class="page-header-title">The &ldquo;Bhaia&rdquo;<br><em>Disclaimer</em></h1>
    <p class="page-header-sub">Think of us as your Bhaia who guides you in the right direction. You are the one who has to run the business.</p>
  </div>
  <div class="prose-section" style="max-width:720px">
    <div class="prose-block">
      <h2 class="section-title">Our Commitment to You</h2>
      <div class="terms-list">
        <div class="terms-item"><div class="terms-icon">&#128683;</div><div><strong>No Guarantees</strong><p>We provide information based on public government research and our own data gathering. We do not guarantee profits, subsidies, or loan approvals.</p></div></div>
        <div class="terms-item"><div class="terms-icon">&#129330;</div><div><strong>Your Responsibility</strong><p>If you invest money based on information found here, you must practice your own due diligence. We are not liable for any business losses.</p></div></div>
        <div class="terms-item"><div class="terms-icon">&#128176;</div><div><strong>No Fees for Info</strong><p>We do not ask for money in exchange for this information. We don&#x27;t sell insurance, loans, or specific financial products.</p></div></div>
      </div>
    </div>
    <hr class="sec-divider" style="margin:40px 0">
    <div class="prose-block">
      <h2 class="section-title">Terms of Service</h2>
      <p>KidharMilega is an entity under <strong>Rupantran Biz Pvt Ltd</strong>. By using this site, you agree that:</p>
      <div class="terms-list">
        <div class="terms-item"><div class="terms-icon">&#128218;</div><div><strong>Educational Use Only</strong><p>All content is for educational and discovery purposes only.</p></div></div>
        <div class="terms-item"><div class="terms-icon">&#128274;</div><div><strong>No Scraping</strong><p>You will not scrape or copy our database for commercial gain. Our data team has spent considerable effort building this resource.</p></div></div>
      </div>
    </div>
  </div>
</div></main>''' + footer() + "</body></html>"

def build_sitemap(districts):
    live = [d for d in districts if d.get("page_status","").lower()=="live"]
    today = datetime.now().strftime("%Y-%m-%d")
    def u(loc, freq, pri):
        return f'  <url>\n    <loc>{loc}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>{freq}</changefreq>\n    <priority>{pri}</priority>\n  </url>'
    entries = [
        u(f"{SITE_URL}/",                    "weekly",  "1.0"),
        u(f"{SITE_URL}/products/",           "weekly",  "0.9"),
        u(f"{SITE_URL}/events/",             "daily",   "0.8"),
        u(f"{SITE_URL}/what-is-odop/",       "monthly", "0.7"),
        u(f"{SITE_URL}/about-us/",           "monthly", "0.6"),
        u(f"{SITE_URL}/team/",               "monthly", "0.5"),
        u(f"{SITE_URL}/contact/",            "monthly", "0.6"),
        u(f"{SITE_URL}/terms-of-service/",   "monthly", "0.3"),
    ]
    for sv in EXHIBITION_SLUGS:
        entries.append(u(f"{SITE_URL}/{sv}/", "weekly", "0.7"))
    for d in live:
        pg  = product_page_slug(d)
        pri = "0.8" if d.get("step_1_learn","").strip() else "0.6"
        entries.append(u(f"{SITE_URL}/products/{pg}/", "monthly", pri))
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(entries) + "\n</urlset>"

def build_robots():
    return f"""User-agent: *
Allow: /
Disallow: /master.html

Sitemap: {SITE_URL}/sitemap.xml
"""

def build():
    print(f"\n KidharMilega Builder  [BASE_PATH='{BASE_PATH}']")
    print("="*50)
    if DIST_DIR.exists(): shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)
    for d in ["assets","products","events","vendors"]: (DIST_DIR/d).mkdir()

    # Write CSS inline (no external file needed)
    css_content = """*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}img{max-width:100%;display:block}a{color:inherit;text-decoration:none}:root{--orange:#00B4D8;--orange-l:#E6F8FD;--orange-m:#7DD8EE;--dark:#111111;--mid:#555555;--light:#888888;--border:#E2EEF2;--bg:#FFFFFF;--bg-2:#F5FBFD;--bg-3:#EAF5F9;--green:#2D7D46;--green-l:#EAF4EE;--blue:#0077A8;--blue-l:#E0F2FA;--radius:10px;--radius-lg:16px;--shadow:0 1px 4px rgba(0,0,0,0.08),0 4px 16px rgba(0,0,0,0.04);--shadow-lg:0 2px 8px rgba(0,0,0,0.10),0 8px 32px rgba(0,0,0,0.06);--font-display:'Fraunces',Georgia,serif;--font-body:'DM Sans',system-ui,sans-serif;--max-w:1120px}body{font-family:var(--font-body);color:var(--dark);background:var(--bg);line-height:1.6;-webkit-font-smoothing:antialiased;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none}h1,h2,h3,h4{font-family:var(--font-display);line-height:1.15}p{color:var(--mid)}.container{max-width:var(--max-w);margin:0 auto;padding:0 24px}.section{padding:80px 0}.section-sm{padding:48px 0}.site-nav{position:sticky;top:0;z-index:100;background:rgba(255,255,255,0.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}.nav-inner{max-width:var(--max-w);margin:0 auto;padding:0 24px;height:60px;display:flex;align-items:center;gap:32px}.nav-logo{display:flex;align-items:center;gap:10px;flex-shrink:0}.logo-mark{background:var(--orange);color:#fff;font-family:var(--font-body);font-weight:700;font-size:11px;letter-spacing:1px;padding:4px 7px;border-radius:4px}.logo-mark.small{font-size:10px;padding:3px 6px}.logo-text{font-family:var(--font-body);font-size:15px;font-weight:400;color:var(--dark)}.logo-text strong{color:var(--orange);font-weight:600}.nav-logo-img{height:36px;width:auto}.nav-links{display:flex;gap:4px;flex:1}.nav-links a{font-size:14px;color:var(--mid);padding:6px 12px;border-radius:6px;transition:all 0.15s}.nav-links a:hover,.nav-links a.active{color:var(--dark);background:var(--bg-3)}.nav-links a.active{color:var(--orange)}.nav-ig{font-size:13px;color:var(--orange);font-weight:500;flex-shrink:0}.nav-ig:hover{text-decoration:underline}.nav-hamburger{display:none;background:none;border:none;cursor:pointer;font-size:22px;color:var(--dark);padding:4px 8px;line-height:1;margin-left:8px}.site-footer{border-top:1px solid var(--border);padding:40px 0;background:var(--bg-2);margin-top:80px}.footer-inner{max-width:var(--max-w);margin:0 auto;padding:0 24px;display:flex;align-items:center;gap:32px;flex-wrap:wrap}.footer-brand{display:flex;align-items:center;gap:8px;font-weight:600;font-size:14px}.footer-links{display:flex;gap:20px;flex:1}.footer-links a{font-size:13px;color:var(--mid)}.footer-links a:hover{color:var(--dark)}.footer-meta{font-size:12px;color:var(--light)}.footer-meta a{color:var(--orange)}.btn{display:inline-flex;align-items:center;gap:6px;padding:12px 22px;border-radius:var(--radius);font-size:14px;font-weight:500;font-family:var(--font-body);cursor:pointer;transition:all 0.15s;border:1.5px solid transparent;text-decoration:none}.btn-primary{background:var(--orange);color:#fff;border-color:var(--orange)}.btn-primary:hover{background:#0096B8;border-color:#0096B8}.btn-ghost{background:transparent;color:var(--dark);border-color:var(--border)}.btn-ghost:hover{background:var(--bg-3);border-color:var(--dark)}.btn-sm{padding:8px 14px;font-size:13px}.tag{display:inline-block;font-size:11px;font-weight:500;padding:3px 9px;border-radius:20px;letter-spacing:0.3px}.tag-orange{background:var(--orange-l);color:var(--orange)}.tag-green{background:var(--green-l);color:var(--green)}.tag-blue{background:var(--blue-l);color:var(--blue)}.tag-gray{background:var(--bg-3);color:var(--mid)}.card{background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-lg);padding:24px;transition:box-shadow 0.2s,transform 0.2s}.card:hover{box-shadow:var(--shadow-lg);transform:translateY(-2px)}.grid-2{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:20px}.grid-3{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}.grid-4{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}.hero{padding:80px 0 60px}.hero-eyebrow{font-size:12px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--orange);margin-bottom:20px}.hero-title{font-family:var(--font-display);font-size:clamp(40px,6vw,72px);font-weight:900;line-height:1.05;color:var(--dark);margin-bottom:20px}.hero-title em{font-style:italic;color:var(--orange)}.hero-sub{font-size:18px;color:var(--mid);max-width:560px;line-height:1.7;margin-bottom:36px}.hero-actions{display:flex;gap:12px;flex-wrap:wrap}.stat-strip{display:flex;gap:40px;flex-wrap:wrap;padding:32px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);margin:40px 0}.stat-item{display:flex;flex-direction:column;gap:4px}.stat-val{font-family:var(--font-display);font-size:32px;font-weight:900;color:var(--orange)}.stat-label{font-size:13px;color:var(--light)}.district-card{display:flex;flex-direction:column;gap:14px;padding:24px;border:1px solid var(--border);border-radius:var(--radius-lg);transition:all 0.2s;background:var(--bg);text-decoration:none}.district-card:hover{border-color:var(--orange-m);box-shadow:var(--shadow-lg);transform:translateY(-2px)}.district-card-head{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}.district-name{font-family:var(--font-display);font-size:20px;font-weight:600;color:var(--dark)}.district-name-hin{font-size:14px;color:var(--light);margin-top:2px}.district-product{font-size:14px;font-weight:500;color:var(--orange);margin-top:4px}.district-desc{font-size:13px;color:var(--mid);line-height:1.6}.district-meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:auto;padding-top:12px;border-top:1px solid var(--border)}.district-arrow{font-size:18px;color:var(--border);transition:color 0.2s}.district-card:hover .district-arrow{color:var(--orange)}.district-hero{padding:60px 0 40px;border-bottom:1px solid var(--border)}.district-hero-top{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;flex-wrap:wrap;margin-bottom:24px}.breadcrumb{font-size:13px;color:var(--light);margin-bottom:16px}.breadcrumb a{color:var(--orange)}.district-page-title{font-family:var(--font-display);font-size:clamp(32px,5vw,56px);font-weight:900;color:var(--dark);line-height:1.1}.district-page-title span{color:var(--orange);font-style:italic}.district-tagline{font-size:17px;color:var(--mid);margin-top:12px;max-width:600px;line-height:1.7}.snapshot-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:12px;margin-top:32px}.snapshot-item{background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);padding:16px}.snapshot-val{font-family:var(--font-display);font-size:20px;font-weight:700;color:var(--dark)}.snapshot-key{font-size:12px;color:var(--light);margin-top:4px}.page-section{padding:48px 0;border-bottom:1px solid var(--border)}.page-section:last-of-type{border-bottom:none}.section-label{font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--orange);margin-bottom:12px}.section-title{font-family:var(--font-display);font-size:28px;font-weight:700;color:var(--dark);margin-bottom:8px}.section-sub{font-size:15px;color:var(--mid);margin-bottom:28px;line-height:1.7}.odop-block{display:grid;grid-template-columns:1fr 1fr;gap:40px;align-items:start}@media(max-width:700px){.odop-block{grid-template-columns:1fr}}.odop-detail-list{display:flex;flex-direction:column}.odop-detail-row{display:flex;padding:12px 0;border-bottom:1px solid var(--border);gap:16px}.odop-detail-row:last-child{border-bottom:none}.odop-detail-key{font-size:13px;color:var(--light);min-width:130px;flex-shrink:0}.odop-detail-val{font-size:14px;color:var(--dark);font-weight:500}.steps-list{display:flex;flex-direction:column}.step-row{display:flex;gap:20px;padding:20px 0;border-bottom:1px solid var(--border)}.step-row:last-child{border-bottom:none}.step-num{width:36px;height:36px;background:var(--orange);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;flex-shrink:0;margin-top:2px}.step-content{flex:1}.step-title{font-size:15px;font-weight:600;color:var(--dark);margin-bottom:4px}.step-desc{font-size:14px;color:var(--mid);line-height:1.6}.names-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px}.name-card{background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);padding:14px 16px;font-family:var(--font-display);font-size:16px;font-weight:600;color:var(--dark)}.vendor-card{background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-lg);padding:20px}.vendor-card.premium{border-color:var(--orange-m);background:var(--orange-l)}.vendor-name{font-size:16px;font-weight:600;color:var(--dark);margin-bottom:4px}.vendor-cat{font-size:13px;color:var(--mid);margin-bottom:12px}.vendor-desc{font-size:13px;color:var(--mid);line-height:1.6;margin-bottom:14px}.vendor-actions{display:flex;gap:8px;flex-wrap:wrap}.scheme-list{display:flex;flex-direction:column;gap:12px}.scheme-item{display:flex;gap:16px;padding:16px;background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);align-items:flex-start}.scheme-icon{width:36px;height:36px;background:var(--orange-l);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}.scheme-title{font-size:14px;font-weight:600;color:var(--dark);margin-bottom:3px}.scheme-desc{font-size:13px;color:var(--mid)}.cta-block{background:linear-gradient(135deg,#0077A8 0%,#00B4D8 100%);border-radius:var(--radius-lg);padding:48px;display:flex;gap:32px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-top:60px}.cta-title{font-family:var(--font-display);font-size:28px;font-weight:700;color:#fff;margin-bottom:8px}.cta-sub{font-size:15px;color:rgba(255,255,255,0.6)}.cta-actions{display:flex;gap:12px;flex-wrap:wrap}.hero-search-row{display:flex;gap:8px;align-items:center}.math-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:640px}.search-wrap{position:relative;max-width:480px}.search-input{width:100%;padding:14px 20px 14px 46px;border:1.5px solid var(--border);border-radius:40px;font-size:15px;font-family:var(--font-body);background:var(--bg);color:var(--dark);outline:none;transition:border-color 0.2s}.search-input:focus{border-color:var(--orange)}.search-icon{position:absolute;left:16px;top:50%;transform:translateY(-50%);color:var(--light);font-size:18px;pointer-events:none}.filter-tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:32px}.filter-tab{padding:7px 16px;border-radius:20px;border:1.5px solid var(--border);font-size:13px;font-weight:500;color:var(--mid);cursor:pointer;transition:all 0.15s;background:var(--bg);font-family:var(--font-body)}.filter-tab:hover,.filter-tab.active{border-color:var(--orange);color:var(--orange);background:var(--orange-l)}.events-placeholder{background:var(--bg-2);border:1.5px dashed var(--border);border-radius:var(--radius-lg);padding:40px;text-align:center}.events-placeholder h3{font-family:var(--font-display);font-size:20px;margin-bottom:8px}.page-header{padding:48px 0 32px;border-bottom:1px solid var(--border);margin-bottom:40px}.page-header-title{font-family:var(--font-display);font-size:clamp(28px,4vw,44px);font-weight:900;color:var(--dark);margin-bottom:8px}.page-header-title em{font-style:italic;color:var(--orange)}.page-header-sub{font-size:16px;color:var(--mid);max-width:520px}.master-modules{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:24px;margin-bottom:60px}.module-card{border:1px solid var(--border);border-radius:var(--radius-lg);padding:28px;display:flex;flex-direction:column;gap:16px;transition:all 0.2s;text-decoration:none}.module-card:hover{border-color:var(--orange-m);box-shadow:var(--shadow-lg);transform:translateY(-2px)}.module-icon{font-size:28px}.module-title{font-family:var(--font-display);font-size:22px;font-weight:700;color:var(--dark)}.module-desc{font-size:14px;color:var(--mid);line-height:1.7}.module-link{font-size:13px;color:var(--orange);font-weight:500;margin-top:auto}.odop-photo-wrap{margin-bottom:28px;border-radius:var(--radius-lg);overflow:hidden;border:1px solid var(--border)}.odop-photo{width:100%;max-height:380px;object-fit:cover;display:block}.ae-section-label{font-size:12px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--mid);margin-bottom:12px}.ae-primary,.ae-fallback{border-radius:var(--radius-lg);overflow:hidden}.sec-divider{border:none;border-top:1px solid var(--border);margin:0}.alert-strip{background:#111;color:#fff;text-align:center;padding:10px 24px;font-size:13px;font-weight:500;letter-spacing:0.2px}.for-badge{background:var(--orange-l);color:var(--orange);border-radius:20px;padding:7px 16px;font-size:13px;font-weight:500;display:inline-block;margin-bottom:16px}.geo-anchor{font-size:15px;color:var(--mid);line-height:1.8;margin:12px 0 0;max-width:620px}.stat-bar-dark{background:#111;border-radius:var(--radius-lg);padding:18px 28px;display:flex;gap:32px;flex-wrap:wrap;margin:24px 0}.stat-bar-item{display:flex;flex-direction:column;gap:4px}.stat-bar-item .sv{font-family:var(--font-display);font-size:22px;font-weight:900;color:#fff}.stat-bar-item .sk{font-size:11px;color:rgba(255,255,255,0.45);text-transform:uppercase;letter-spacing:1px}.opp-card{display:flex;gap:28px;align-items:center;background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius-lg);padding:24px;margin:24px 0;flex-wrap:wrap}.opp-ring{width:100px;height:100px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0}.opp-ring-num{background:var(--bg);border-radius:50%;width:76px;height:76px;display:flex;align-items:center;justify-content:center;font-family:var(--font-display);font-size:24px;font-weight:900;color:var(--dark)}.opp-ring-num small{font-size:13px;color:var(--light);margin-left:2px}.opp-label{font-size:11px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--light);margin-bottom:6px}.opp-title{font-family:var(--font-display);font-size:18px;font-weight:600;color:var(--dark);margin-bottom:10px}.opp-pills{display:flex;gap:8px;flex-wrap:wrap}.opp-pill{background:var(--green-l);color:var(--green);border-radius:20px;padding:4px 12px;font-size:12px;font-weight:500}.biz-card{background:#111;border-radius:var(--radius-lg);padding:20px 24px}.biz-label{font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:rgba(255,255,255,0.45);margin-bottom:14px}.biz-row{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid rgba(255,255,255,0.08);font-size:14px}.biz-row:last-child{border-bottom:none}.bk{color:rgba(255,255,255,0.55)}.bv{color:#fff;font-weight:600}.bv.g{color:#4ade80}.success-box{background:var(--bg-2);border:1px solid var(--border);border-left:3px solid var(--green);border-radius:var(--radius-lg);padding:24px;margin-top:28px}.ss-label{font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--green);margin-bottom:8px}.ss-name{font-family:var(--font-display);font-size:20px;font-weight:700;color:var(--dark);margin-bottom:8px}.ss-body{font-size:14px;color:var(--mid);line-height:1.7;margin-bottom:16px}.ss-nums{display:flex;gap:28px;flex-wrap:wrap;margin-bottom:8px}.ss-num{display:flex;flex-direction:column;gap:4px}.ss-num .sv{font-family:var(--font-display);font-size:20px;font-weight:800;color:var(--dark)}.ss-num .sk{font-size:12px;color:var(--light)}.ss-source{font-size:12px;color:var(--light);font-style:italic}.rev-flow{display:flex;flex-direction:column;gap:4px;margin-top:20px}.rev-row{display:flex;align-items:center;gap:18px;padding:16px 20px;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg)}.rev-row.primary{background:var(--orange-l);border-color:var(--orange-m)}.rev-row>div:nth-child(2){flex:1}.rev-arr{color:var(--light);font-size:18px;padding:2px 0;line-height:1;padding-left:48px}.rev-step{width:32px;height:32px;background:var(--orange);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0}.rev-step-b{background:#111;color:#fff}.ri-name{font-size:14px;font-weight:600;color:var(--dark);margin-bottom:2px}.ri-desc{font-size:12px;color:var(--mid)}.rev-margin{font-family:var(--font-display);font-size:16px;font-weight:800;color:var(--orange);white-space:nowrap;flex-shrink:0}.step-num-dark{width:38px;height:38px;background:#111;color:#fff;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:15px;flex-shrink:0;margin-top:2px}.log-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin-top:20px}.log-card{background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);padding:16px}.log-icon{font-size:22px;margin-bottom:8px}.log-name{font-size:11px;font-weight:700;color:var(--light);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px}.log-detail{font-size:14px;color:var(--dark);font-weight:500}.park-list{display:flex;flex-direction:column;gap:10px;margin-top:20px}.park-row{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;padding:16px 20px;background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius)}.park-name{font-size:15px;font-weight:600;color:var(--dark);margin-bottom:4px}.park-desc{font-size:13px;color:var(--mid)}.park-tag{background:var(--orange-l);color:var(--orange);border-radius:20px;padding:4px 12px;font-size:11px;font-weight:600;white-space:nowrap;flex-shrink:0}.faq-list{border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden;margin-top:20px}.faq-item{border-bottom:1px solid var(--border)}.faq-item:last-child{border-bottom:none}.faq-btn{width:100%;display:flex;justify-content:space-between;align-items:center;padding:16px 20px;background:var(--bg);border:none;font-size:14px;font-weight:600;color:var(--dark);cursor:pointer;font-family:var(--font-body);text-align:left;gap:16px}.faq-btn:hover{background:var(--bg-2)}.faq-icon{font-size:18px;color:var(--light);flex-shrink:0;transition:transform 0.2s}.faq-item.open .faq-btn{background:var(--bg-2);color:var(--orange)}.faq-item.open .faq-icon{transform:rotate(45deg)}.faq-body{display:none;padding:0 20px 16px;font-size:14px;color:var(--mid);line-height:1.7}.faq-item.open .faq-body{display:block}.rd-label{font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--light);margin-bottom:12px}.rd-grid{display:flex;gap:10px;flex-wrap:wrap}.rd-chip{display:flex;flex-direction:column;gap:3px;padding:12px 16px;border:1px solid var(--border);border-radius:var(--radius);text-decoration:none;transition:all 0.15s;background:var(--bg);min-width:140px}.rd-chip:hover{border-color:var(--orange-m);background:var(--orange-l)}.rd-p{font-size:13px;font-weight:600;color:var(--dark)}.rd-s{font-size:11px;color:var(--light)}.cluster-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;margin-top:20px}.cluster-card{background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius-lg);padding:20px}.cluster-card.active{border-color:var(--orange-m);background:var(--orange-l)}.cc-town{font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--light);margin-bottom:4px}.cc-name{font-family:var(--font-display);font-size:17px;font-weight:700;color:var(--dark);margin-bottom:8px}.cc-facts{list-style:none}.cc-facts li{font-size:12px;color:var(--mid);padding:3px 0}.info-box{border-radius:var(--radius);padding:14px 18px;font-size:14px;line-height:1.6}.info-neutral{background:var(--bg-2);border:1px solid var(--border);color:var(--mid)}.yt-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:20px;margin-top:20px}.yt-embed-wrap{position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:var(--radius-lg);background:#000}.yt-embed-wrap iframe{position:absolute;top:0;left:0;width:100%;height:100%;border:none;border-radius:var(--radius-lg)}.news-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin-top:20px}.news-card{display:flex;flex-direction:column;gap:8px;padding:16px 18px;background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);text-decoration:none;transition:all 0.15s}.news-card:hover{border-color:var(--orange-m);background:var(--orange-l);transform:translateY(-1px)}.news-source{font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--orange)}.news-title{font-size:14px;font-weight:500;color:var(--dark);line-height:1.5}.news-arrow{font-size:14px;color:var(--light);margin-top:4px}.prose-section{max-width:760px}.prose-block{padding:40px 0}.site-blockquote{border-left:3px solid var(--orange);padding:16px 24px;background:var(--orange-l);border-radius:0 var(--radius) var(--radius) 0;font-family:var(--font-display);font-size:17px;font-style:italic;color:var(--dark);margin:24px 0;line-height:1.7}.team-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:24px;margin-top:8px}.team-card{background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-lg);padding:28px;display:flex;flex-direction:column;gap:8px}.team-avatar{width:52px;height:52px;background:var(--orange);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:var(--font-display);font-size:18px;font-weight:700;flex-shrink:0;margin-bottom:4px}.team-name{font-family:var(--font-display);font-size:18px;font-weight:700;color:var(--dark)}.team-role{font-size:12px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--orange)}.team-bio{font-size:13px;color:var(--mid);line-height:1.7;margin-top:4px}.prose-article{max-width:760px;margin-top:8px}.prose-article h2{font-family:var(--font-display);font-size:24px;font-weight:700;color:var(--dark);margin:40px 0 12px;padding-top:8px;border-top:1px solid var(--border)}.prose-article h2:first-child{border-top:none;margin-top:0}.prose-article h3{font-family:var(--font-display);font-size:18px;font-weight:600;color:var(--dark);margin:24px 0 8px}.prose-article p{font-size:15px;color:var(--mid);line-height:1.8;margin-bottom:16px}.prose-article ul,.prose-article ol{margin:0 0 20px 0;padding-left:20px}.prose-article li{font-size:14px;color:var(--mid);line-height:1.8;margin-bottom:6px}.prose-article strong{color:var(--dark);font-weight:600}.prose-article a{color:var(--orange);text-decoration:underline}.prose-article hr{border:none;border-top:1px solid var(--border);margin:36px 0}.prose-article blockquote{border-left:3px solid var(--orange);padding:12px 20px;background:var(--orange-l);border-radius:0 var(--radius) var(--radius) 0;margin:24px 0}.prose-article table{width:100%;border-collapse:collapse;margin:24px 0;font-size:14px}.prose-article th{background:var(--bg-3);padding:10px 14px;text-align:left;font-weight:600;color:var(--dark);border:1px solid var(--border)}.prose-article td{padding:10px 14px;border:1px solid var(--border);color:var(--mid)}.prose-article tr:nth-child(even) td{background:var(--bg-2)}.contact-card{background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius-lg);padding:28px;display:flex;flex-direction:column;gap:10px}.contact-icon{font-size:28px}.contact-label{font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--light)}.contact-value{font-size:16px;font-weight:600;color:var(--orange)}.contact-address{margin-top:48px;padding-top:32px;border-top:1px solid var(--border)}.terms-list{display:flex;flex-direction:column;gap:16px;margin-top:20px}.terms-item{display:flex;gap:16px;padding:20px;background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius);align-items:flex-start}.terms-icon{font-size:22px;flex-shrink:0;margin-top:2px}.terms-item p{font-size:14px;color:var(--mid);margin-top:4px;line-height:1.7}.exhibition-content h3{font-family:var(--font-display);font-size:20px;font-weight:700;color:var(--dark);margin:28px 0 12px}.exhibition-content p{font-size:15px;color:var(--mid);line-height:1.8;margin-bottom:16px}.exhibition-content ul{list-style:none;margin-bottom:20px;display:flex;flex-direction:column;gap:8px}.exhibition-content li{display:flex;gap:12px;font-size:14px;color:var(--mid);line-height:1.7;padding:12px 16px;background:var(--bg-2);border:1px solid var(--border);border-radius:var(--radius)}.exhibition-content li::before{content:"→";color:var(--orange);flex-shrink:0;font-weight:600;margin-top:1px}.products-topbar{display:flex;align-items:center;gap:12px;margin-bottom:24px;flex-wrap:wrap}.products-layout{display:flex;gap:28px;align-items:flex-start}.filter-sidebar{width:232px;flex-shrink:0;position:sticky;top:72px;max-height:calc(100vh - 88px);overflow-y:auto;border:1px solid var(--border);border-radius:var(--radius-lg);background:var(--bg);padding:0 0 8px}.fsb-head{display:flex;justify-content:space-between;align-items:center;padding:16px 16px 12px;border-bottom:1px solid var(--border);margin-bottom:4px}.fsb-title{font-size:14px;font-weight:700;color:var(--dark)}.fsb-clear{font-size:12px;color:var(--orange);background:none;border:none;cursor:pointer;font-family:var(--font-body);font-weight:500;padding:0}.fsb-clear:hover{text-decoration:underline}.filter-group{padding:14px 16px;border-bottom:1px solid var(--border)}.fgrp-label{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--light);margin-bottom:10px}.fcheck-list{display:flex;flex-direction:column;gap:6px}.fcheck-scroll{max-height:220px;overflow-y:auto;padding-right:4px}.filter-check{display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;color:var(--mid);line-height:1.4}.filter-check input{accent-color:var(--orange);width:14px;height:14px;flex-shrink:0;cursor:pointer}.filter-check:hover span{color:var(--dark)}.products-main{flex:1;min-width:0}.result-count{font-size:13px;color:var(--light);margin-bottom:12px;min-height:20px}.fsb-mobile-toggle{display:none;align-items:center;gap:6px;padding:8px 16px;border:1.5px solid var(--border);border-radius:20px;font-size:13px;font-weight:500;color:var(--mid);background:var(--bg);cursor:pointer;font-family:var(--font-body);white-space:nowrap}.fsb-mobile-toggle:hover{border-color:var(--orange);color:var(--orange)}.filter-badge{background:var(--orange);color:#fff;border-radius:20px;font-size:11px;font-weight:700;padding:1px 7px;min-width:18px;justify-content:center}@media(max-width:640px){.container{padding:0 16px}.site-nav{position:relative}.nav-hamburger{display:flex;align-items:center;justify-content:center;margin-left:auto}.nav-links{display:none;flex-direction:column;position:absolute;top:60px;left:0;right:0;background:#fff;border-bottom:1px solid var(--border);padding:8px 16px 16px;gap:2px;z-index:99;box-shadow:0 8px 24px rgba(0,0,0,0.08)}.nav-links.nav-open{display:flex}.nav-links a{padding:11px 14px;border-radius:var(--radius);font-size:15px}.nav-ig{display:none}.fsb-mobile-toggle{display:inline-flex}.products-layout{flex-direction:column}.filter-sidebar{width:100%;position:static;max-height:none;display:none;border-radius:var(--radius-lg)}.filter-sidebar.fsb-open{display:block}.section{padding:48px 0}.cta-block{padding:24px;flex-direction:column;align-items:stretch}.cta-actions{flex-direction:column;width:100%}.cta-actions .btn{width:100%;justify-content:center}.stat-strip{gap:24px}.hero-search-row{flex-direction:column;align-items:stretch}.hero-search-row>*{width:100% !important;max-width:100% !important}.hero-search-btn{justify-content:center}.math-grid{grid-template-columns:1fr}}"""
    (DIST_DIR/"assets"/"style.css").write_text(css_content)
    # Copy logo
    logo_src = DATA_DIR / "logo.png"
    if logo_src.exists():
        shutil.copy(logo_src, DIST_DIR / "assets" / "logo.png")
    print("✓ CSS + logo written")

    districts = load_csv(DATA_DIR/"districts.csv", CSV_URL_DISTRICTS)
    vendors   = load_csv(DATA_DIR/"vendors.csv",   CSV_URL_VENDORS)
    print(f"✓ Loaded {len(districts)} districts, {len(vendors)} vendors")

    odop_urls = {}
    odop_urls_csv = DATA_DIR / "odop_urls.csv"
    if odop_urls_csv.exists():
        for row in load_csv(odop_urls_csv):
            key = (row.get('state','').strip(), row.get('district','').strip())
            odop_urls[key] = row
    print(f"✓ Loaded {len(odop_urls)} odop URL entries")

    # Load exhibition posts from JSON export
    exhibition_posts = []
    ex_json = DATA_DIR / "posts-exhibition-pages-kidharmilega.json"
    if ex_json.exists():
        raw_json = json.loads(ex_json.read_text(encoding="utf-8"))
        slug_set = set(EXHIBITION_SLUGS)
        for item in raw_json:
            if item.get("type") == "table":
                post_map = {p["post_name"]: p for p in item["data"] if p.get("post_name") in slug_set}
                exhibition_posts = [post_map[s] for s in EXHIBITION_SLUGS if s in post_map]
                break
    print(f"✓ Loaded {len(exhibition_posts)} exhibition posts")

    (DIST_DIR/"index.html").write_text(build_homepage(districts))
    print("✓ Homepage")
    (DIST_DIR/"master.html").write_text(build_master_page())
    (DIST_DIR/"products"/"index.html").write_text(build_odop_page(districts))
    (DIST_DIR/"events"/"index.html").write_text(build_events_page(exhibition_posts))
    (DIST_DIR/"vendors"/"index.html").write_text(build_vendors_page(vendors, districts))
    for slug, builder in [
        ("about-us",        build_about_page),
        ("team",            build_team_page),
        ("what-is-odop",    build_odop_guide_page),
        ("contact",         build_contact_page),
        ("terms-of-service",build_terms_page),
    ]:
        d = DIST_DIR / slug
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(builder())
    (DIST_DIR/"sitemap.xml").write_text(build_sitemap(districts))
    (DIST_DIR/"robots.txt").write_text(build_robots())
    print("✓ Directory pages + sitemap.xml + robots.txt")

    live = [d for d in districts if d.get("page_status","").lower()=="live"]
    for d in live:
        page_dir = DIST_DIR/"products"/product_page_slug(d)
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir/"index.html").write_text(build_district_page(d, vendors, districts, odop_urls))
    print(f"✓ {len(live)} district pages")

    for post in exhibition_posts:
        sv = post["post_name"]
        ex_dir = DIST_DIR / sv
        ex_dir.mkdir(parents=True, exist_ok=True)
        (ex_dir / "index.html").write_text(build_exhibition_page(post))
    print(f"✓ {len(exhibition_posts)} exhibition/event city pages")

    (DIST_DIR/".nojekyll").write_text("")
    # CNAME tells GitHub Pages to serve on the custom domain
    if '--subfolder' not in sys.argv:
        (DIST_DIR/"CNAME").write_text("kidharmilega.in")
    total = len(list(DIST_DIR.rglob("*.html")))
    print(f"\n✅ Done → docs/ ({total} HTML files)")
    print(f"   BASE_PATH = '{BASE_PATH}'")
    if BASE_PATH:
        print("   When you switch to custom domain: set BASE_PATH = '' and rebuild\n")

if __name__ == "__main__":
    build()
