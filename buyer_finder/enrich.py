"""
Enrichment — website lookup, then public business emails, phones and socials
from that website's own home, contact and about pages.

Only public business contacts are collected (PRD "Privacy and contact rules").
robots.txt is respected and requests are spaced out. Website lookup uses
DuckDuckGo via `ddgs` when installed; otherwise set a website by hand with
`python3 -m buyer_finder contact <profile> <company> --website ...`.
"""

import re, time, urllib.request, urllib.robotparser
from datetime import date
from urllib.parse import urljoin, urlparse

UA = "Mozilla/5.0 (compatible; KidharMilega-BuyerFinder/1.0; personal research)"

# Domains that list companies but are not the company's own site
DIRECTORY_DOMAINS = {
    "importyeti.com", "panjiva.com", "volza.com", "importgenius.com", "zauba.com", "seair.co.in",
    "linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com", "pinterest.com",
    "yelp.com", "bbb.org", "bloomberg.com", "dnb.com", "zoominfo.com", "opencorporates.com", "manta.com",
    "buzzfile.com", "bizapedia.com", "crunchbase.com", "mapquest.com", "yellowpages.com", "amazon.com",
    "etsy.com", "ebay.com", "wikipedia.org", "glassdoor.com", "indeed.com", "rocketreach.co", "apollo.io",
    "faire.com", "alibaba.com", "indiamart.com", "tradeindia.com", "exportgenius.in", "eximpedia.app",
}

CONTACT_PATHS = ["", "contact", "contact-us", "pages/contact", "pages/contact-us", "about", "about-us",
                 "pages/about", "pages/about-us", "wholesale", "pages/wholesale"]

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
BAD_EMAIL = re.compile(r"\.(png|jpe?g|gif|webp|svg|css|js)$|sentry|wixpress|example\.|domain\.com|"
                       r"yourname|email@|user@|godaddy|cloudflare|@2x", re.I)
PHONE_RE = re.compile(r"(?:tel:|\+1[\s.-]?)?\(?\b([2-9]\d{2})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})\b")
SOCIAL_RE = re.compile(r"https?://(?:www\.)?(instagram\.com|facebook\.com|linkedin\.com/company|pinterest\.com)"
                       r"/[A-Za-z0-9_.\-/]+", re.I)


def _domain(url):
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _is_directory(url):
    d = _domain(url)
    return any(d == x or d.endswith("." + x) for x in DIRECTORY_DOMAINS)


def find_website(name, city="", state=""):
    """Best guess at a company's own website via DuckDuckGo. Returns '' if unsure."""
    try:
        from ddgs import DDGS
    except ImportError:
        return ""
    query = " ".join(x for x in (f'"{name}"', city, state) if x)
    tokens = [t for t in re.findall(r"[a-z0-9]{3,}", name.lower()) if t not in ("inc", "llc", "ltd", "the", "and", "company", "corp")]
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=8))
    except Exception:
        return ""
    for r in results:
        url = r.get("href") or r.get("url") or ""
        if not url or _is_directory(url):
            continue
        host = _domain(url).replace("-", "")
        # The domain should carry part of the company name, or we skip it
        if any(t in host for t in tokens):
            p = urlparse(url)
            return f"{p.scheme}://{p.netloc}"
    return ""


_robots = {}

def _allowed(url):
    base = "{0.scheme}://{0.netloc}".format(urlparse(url))
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser(base + "/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = None
        _robots[base] = rp
    rp = _robots[base]
    return rp is None or rp.can_fetch(UA, url)


def _fetch(url, timeout=12):
    if not _allowed(url):
        return ""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if "html" not in resp.headers.get("Content-Type", "html"):
                return ""
            return resp.read(600_000).decode("utf-8", errors="replace")
    except Exception:
        return ""


def scrape_contacts(website, delay=1.0):
    """Public emails, phones and social links from a site's own pages."""
    emails, phones, socials, sources = [], [], [], []
    site_domain = _domain(website)
    for path in CONTACT_PATHS:
        url = urljoin(website.rstrip("/") + "/", path)
        html = _fetch(url)
        time.sleep(delay)
        if not html:
            continue
        found = False
        for e in EMAIL_RE.findall(html.replace("%40", "@")):
            e = e.lower().strip(".")
            if not BAD_EMAIL.search(e) and e not in emails:
                emails.append(e)
                found = True
        for m in PHONE_RE.finditer(html):
            p = f"({m.group(1)}) {m.group(2)}-{m.group(3)}"
            if p not in phones and len(phones) < 3:
                phones.append(p)
        for m in SOCIAL_RE.finditer(html):
            s = m.group(0).rstrip("/").split("?")[0]
            if s not in socials and not re.search(r"/(sharer|share|plugins|tr|dialog)\b", s):
                socials.append(s)
        if found:
            sources.append(url)
    # Prefer emails on the company's own domain
    emails.sort(key=lambda e: (not e.endswith("@" + site_domain), e))
    return {"emails": emails[:5], "phones": phones, "socials": socials[:4], "sources": sources}


def enrich_lead(lead, delay=1.0):
    website = lead.get("website") or find_website(lead["name"], lead.get("city", ""), lead.get("state", ""))
    if not website:
        return {"notes": "website not found", "enriched_at": date.today().isoformat()}
    found = scrape_contacts(website, delay=delay)
    return {"website": website, **found, "enriched_at": date.today().isoformat()}
