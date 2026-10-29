"""
F3 + data engine — buyer search over the local shipment store.

Steps (PRD "Data engine"):
  2. Seed exporters: Indian shippers with shipment lines matching the profile.
  3. Snowball, 2 hops: seeds' buyers -> those buyers' other Indian suppliers ->
     their buyers. Only relationships with matching lines count.
  4. Cleanup: merge consignees sharing an address, drop forwarders,
     marketplace intake addresses, parcel services and consultancies.
  5. Tagging: styles a buyer buys and a pitch angle.
  7. Scoring v2: proof 35, recency 15, repeat 15, fit 15, reach 10, market 10.
"""

import re
from collections import Counter, defaultdict
from datetime import date

from .hsn import search_prefixes

MARKETS = {"US": "UNITED STATES"}

# Consignee names that are logistics or intake points, not buyers
NOISE = re.compile(
    r"\b(LOGISTICS?|FREIGHT|FORWARD(ING|ERS?)|SHIPPING|CARGO|EXPRESS|COURIER|CUSTOMS\s+BROKER(AGE)?|"
    r"CONSOLIDAT\w*|NVOCC|LINES?\s+(INC|LLC|LTD)|EXPEDITORS|FLEXPORT|DHL|FEDEX|UPS\s+(SCS|SUPPLY)|"
    r"KUEHNE|SCHENKER|PANALPINA|CEVA|NIPPON\s+EXPRESS|APEX\s+GLOBAL|"
    r"AMAZON(\.COM)?\s*(SERVICES|FULFILLMENT|FBA)?|FBA\b|FULFILLMENT\s+CENT(ER|RE)|3PL|WAREHOUS\w*\s+SERVICES|"
    r"CONSULT(ING|ANCY|ANTS?)|TO\s+(THE\s+)?ORDER(\s+OF)?|SAME\s+AS\s+CONSIGNEE|NOTIFY\s+PARTY)\b", re.I)

SUFFIXES = re.compile(
    r"\b(INCORPORATED|INC|LLC|L\s?L\s?C|LTD|LIMITED|CORP|CORPORATION|CO|COMPANY|PVT|PRIVATE|PLC|LLP|LP|"
    r"THE|DBA|D\s?B\s?A|USA|US|ENTERPRISES?|GROUP|INTL|INTERNATIONAL|HOLDINGS?)\b")

STYLE_WORDS = [
    "leather", "canvas", "cotton", "linen", "jute", "silk", "wool", "velvet", "denim", "kraft", "recycled",
    "handmade", "hand made", "handcrafted", "hand block", "block print", "embroidered", "quilted", "beaded",
    "macrame", "woven", "printed", "tie dye", "vintage", "antique", "rustic", "deckle", "brass", "copper",
    "iron", "wooden", "wood", "mango wood", "sheesham", "marble", "stone", "ceramic", "terracotta", "glass",
    "silver", "gold plated", "enamel", "bone", "horn", "resin", "bamboo", "rattan", "seagrass", "organic",
    "journal", "diary", "notebook", "album", "bag", "pouch", "cushion", "throw", "rug", "quilt", "bedspread",
    "table linen", "napkin", "apron", "lamp", "candle", "box", "tray", "bowl", "vase", "planter", "jewelry",
    "earring", "necklace", "bracelet", "scarf", "stole", "kurta", "dress",
]

CORE_FIELDS = ("score", "route", "proof_level")


def company_key(name):
    s = re.sub(r"[^A-Z0-9 ]", " ", (name or "").upper().replace("&", " AND "))
    s = SUFFIXES.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _address_key(address):
    """Street number + first street word + zip, enough to merge aliases at one address."""
    a = (address or "").upper()
    zip_m = re.search(r"\b(\d{5})(?:-\d{4})?\b", a)
    street_m = re.search(r"\b(\d{1,6})\s+([A-Z]{3,})", a)
    if zip_m and street_m:
        return f"{street_m.group(1)} {street_m.group(2)} {zip_m.group(1)}"
    return ""


def _kw_regex(words):
    words = [w.strip() for w in words if w and w.strip()]
    if not words:
        return None
    alts = "|".join(re.escape(w).replace(r"\ ", r"[\s\-]+") for w in sorted(words, key=len, reverse=True))
    return re.compile(rf"\b({alts})(e?s)?\b", re.I)


def match_level(desc, hs_code, kw_re, neg_re, prefixes):
    """'product' if the line names the product, 'hs' if only the HS code matches, else None."""
    desc = desc or ""
    if neg_re and neg_re.search(desc):
        return None
    if kw_re and kw_re.search(desc):
        return "product"
    # HS codes from the HS column, plus dotted codes or "HS 482010" written in the description
    codes = re.findall(r"\d{4,10}", hs_code or "")
    codes += re.findall(r"\b\d{4}\.\d{2}(?:\.\d{2,4})?\b", desc)
    codes += re.findall(r"\b(?:HS|HTS|HSN)(?:\s*CODE)?[\s:#.]*(\d{6,10})\b", desc, re.I)
    for c in codes:
        c = c.replace(".", "")
        if any(c.startswith(p) or (len(c) >= 6 and p.startswith(c)) for p in prefixes):
            return "hs"
    return None


def _months_ago(iso, today):
    if not iso:
        return None
    y, m, d = map(int, iso.split("-"))
    return (today - date(y, m, d)).days / 30.44


def _buyer_type(name, descs):
    n = (name or "").upper()
    blob = " ".join(descs).upper()
    if re.search(r"GIFT", n):
        return "Gift wholesaler"
    if re.search(r"WHOLESALE|DISTRIBUT|IMPORT|TRADING|SUPPLY", n):
        return "Importer / wholesaler"
    if re.search(r"BOUTIQUE|STORE|SHOP|RETAIL|MARKET|MART|OUTLET", n):
        return "Retailer"
    if re.search(r"HOME|DECOR|FURNISH|INTERIOR|LIVING", n):
        return "Home decor brand"
    if re.search(r"PAPER|STATIONER|PRESS|BOOK", n) or "STATIONERY" in blob:
        return "Stationery brand"
    if re.search(r"DESIGN|STUDIO|COLLECTION|BRAND|ATELIER|CRAFT", n):
        return "Brand"
    return "Importer"


def _tags(lines, vocab_re):
    if not vocab_re:
        return []
    c = Counter(re.sub(r"[\s\-]+", " ", m.group(1).lower()) for line in lines for m in vocab_re.finditer(line))
    ranked = [t for t, _ in c.most_common()]
    # "journal" adds nothing next to "leather journal"
    return [t for t in ranked if not any(t != o and t in o for o in ranked)][:4]


def _city_from(address):
    m = re.search(r",\s*([A-Za-z .'-]+),\s*[A-Z]{2}[\s,]+\d{5}", address or "")
    return m.group(1).strip().title() if m else ""


def _pitch(lead):
    parts = []
    if lead["last_months"] is not None and lead["last_months"] > 12:
        parts.append("Lapsed India buyer: ask what changed and offer fresh designs")
    elif lead["supplier_count"] >= 2:
        parts.append(f"Already buys from {lead['supplier_count']} Indian suppliers: pitch as a faster-sampling second source")
    elif lead["matching_12m"] >= 3:
        parts.append("Repeat buyer with one Indian supplier: pitch supply backup and a price check")
    else:
        parts.append("Has imported this from India: lead with samples and MOQ flexibility")
    if lead["tags"]:
        parts.append("open with " + " and ".join(lead["tags"][:2]))
    return "; ".join(parts)


def score_lead(lead, contact, market):
    proof = 35 if lead["proof_level"] == "product" else 22
    lm = lead["last_months"]
    recency = 3 if lm is None else 15 if lm <= 3 else 12 if lm <= 6 else 9 if lm <= 12 else 5 if lm <= 24 else 2 if lm <= 36 else 0
    n12 = lead["matching_12m"]
    repeat = 15 if n12 >= 12 else 12 if n12 >= 6 else 9 if n12 >= 3 else 6 if n12 == 2 else 3 if n12 == 1 or lead["matching_total"] >= 3 else 0
    ratio = lead["matching_total"] / max(lead["india_total"], 1)
    fit = 15 if ratio >= 0.6 else 11 if ratio >= 0.3 else 7 if ratio >= 0.1 else 3
    reach = (4 if contact.get("website") else 0) + (4 if contact.get("emails") else 0) + (2 if contact.get("phones") else 0)
    mkt = 10 if market == "US" else 6
    parts = {"proof": proof, "recency": recency, "repeat": repeat, "fit": fit, "reach": reach, "market": mkt}
    total = sum(parts.values())
    if lm is not None and lm > 36:
        route = "Stale"
    else:
        route = "Outreach now" if total >= 80 else "Nurture" if total >= 60 else "Watch"
    return total, route, parts


def find_buyers(db, profile, contacts=None, today=None, max_hops=2):
    """Run the engine for one profile. Returns {'leads': [...], 'summary': {...}, 'exporters': {...}}."""
    today = today or date.today()
    contacts = contacts or {}
    market = profile.get("market", "US").upper()
    market_country = MARKETS.get(market, market)
    prefixes = search_prefixes(profile)
    kw_re = _kw_regex(profile.get("keywords", []))
    neg_re = _kw_regex(profile.get("negative_keywords", []))
    vocab_re = _kw_regex(STYLE_WORDS + profile.get("keywords", []))

    rows = [dict(r) for r in db.execute(
        "SELECT * FROM shipments WHERE consignee_country = ? AND shipper_country = 'INDIA'", (market_country,))]

    # Cleanup: drop noise consignees, merge aliases sharing an address
    dropped = Counter()
    clean = []
    for r in rows:
        if NOISE.search(r["consignee"]):
            dropped["forwarder / intake"] += 1
            continue
        r["ckey"] = company_key(r["consignee"])
        r["skey"] = company_key(r["shipper"])
        if not r["ckey"]:
            continue
        clean.append(r)

    parent = {}
    def find(k):
        while parent.get(k, k) != k:
            k = parent[k]
        return k
    by_addr = {}
    for r in clean:
        ak = _address_key(r["consignee_address"])
        if not ak:
            continue
        if ak in by_addr and find(by_addr[ak]) != find(r["ckey"]):
            parent[find(r["ckey"])] = find(by_addr[ak])
        else:
            by_addr.setdefault(ak, r["ckey"])
    for r in clean:
        r["ckey"] = find(r["ckey"])
        r["level"] = match_level(r["description"], r["hs_code"], kw_re, neg_re, prefixes)

    by_buyer = defaultdict(list)
    by_exporter = defaultdict(list)
    for r in clean:
        by_buyer[r["ckey"]].append(r)
        if r["skey"]:
            by_exporter[r["skey"]].append(r)

    # Seeds and 2-hop snowball
    seed_names = {company_key(s) for s in profile.get("seeds", []) if s}
    matching_exporters = {r["skey"] for r in clean if r["level"] and r["skey"]}
    frontier = (seed_names & set(by_exporter)) or matching_exporters
    exporter_hop = {e: 0 for e in frontier}
    buyer_hop = {}
    for hop in range(1, max_hops + 1):
        new_buyers = {r["ckey"] for e in frontier for r in by_exporter[e] if r["level"]} - set(buyer_hop)
        for b in new_buyers:
            buyer_hop[b] = hop
        frontier = {r["skey"] for b in new_buyers for r in by_buyer[b] if r["skey"]} - set(exporter_hop)
        for e in frontier:
            exporter_hop[e] = hop
        if not frontier:
            break

    leads = []
    for bkey, hop in buyer_hop.items():
        recs = by_buyer[bkey]
        match = [r for r in recs if r["level"]]
        if not match:
            continue
        match.sort(key=lambda r: r["ship_date"] or "", reverse=True)
        name = Counter(r["consignee"] for r in recs).most_common(1)[0][0]
        # Proof line: the line naming the most keywords, newest first on ties
        best = max(match, key=lambda r: (r["level"] == "product",
                                         len(kw_re.findall(r["description"] or "")) if kw_re else 0,
                                         r["ship_date"] or ""))
        last = match[0]["ship_date"]
        last_months = _months_ago(last, today)
        india_12m = [r for r in recs if r["ship_date"] and _months_ago(r["ship_date"], today) <= 12]
        matching_12m = [r for r in match if r["ship_date"] and _months_ago(r["ship_date"], today) <= 12]
        suppliers = Counter(r["shipper"] for r in match if r["shipper"])
        loc = next((r for r in recs if r["consignee_address"] or r["consignee_state"]), recs[0])
        lead = {
            "company_key":     bkey,
            "name":            name,
            "aliases":         sorted({r["consignee"] for r in recs} - {name}),
            "buyer_type":      _buyer_type(name, [r["description"] for r in match]),
            "address":         loc["consignee_address"],
            "city":            loc["consignee_city"] or _city_from(loc["consignee_address"]),
            "state":           loc["consignee_state"],
            "proof_level":     "product" if any(r["level"] == "product" for r in match) else "hs",
            "proof_line":      (best["description"] or f"HS {best['hs_code']}")[:200],
            "proof_ref":       " / ".join(x for x in (best["bol"], best["ship_date"], best["source"]) if x),
            "last_date":       last,
            "last_months":     last_months,
            "first_date":      min((r["ship_date"] for r in match if r["ship_date"]), default=""),
            "matching_total":  len(match),
            "matching_12m":    len(matching_12m),
            "india_total":     len(recs),
            "india_12m":       len(india_12m),
            "suppliers":       [s for s, _ in suppliers.most_common()],
            "supplier_count":  len(suppliers),
            "all_suppliers":   sorted({r["shipper"] for r in recs if r["shipper"]}),
            "tags":            _tags([r["description"] for r in match], vocab_re),
            "hop":             hop,
        }
        lead["pitch"] = _pitch(lead)
        contact = contacts.get(bkey, {})
        lead["website"] = contact.get("website", "")
        lead["emails"] = contact.get("emails", [])
        lead["phones"] = contact.get("phones", [])
        lead["socials"] = contact.get("socials", [])
        lead["decision_maker"] = contact.get("decision_maker", "")
        lead["contact_sources"] = contact.get("sources", [])
        lead["score"], lead["route"], lead["score_parts"] = score_lead(lead, contact, market)
        fresh = last_months is not None and last_months <= 36
        reachable = bool(lead["website"] or lead["emails"])
        lead["status"] = ("verified" if fresh and reachable else
                          "stale (>36 months)" if not fresh else "needs contacts")
        leads.append(lead)

    leads.sort(key=lambda l: (l["score"], l["last_date"] or ""), reverse=True)
    summary = {
        "profile":            profile.get("product"),
        "market":             market,
        "records_in_market":  len(rows),
        "dropped":            dict(dropped),
        "seed_exporters":     sum(1 for h in exporter_hop.values() if h == 0),
        "exporters_reached":  len(exporter_hop),
        "buyers":             len(leads),
        "proof_product":      sum(1 for l in leads if l["proof_level"] == "product"),
        "proof_hs_only":      sum(1 for l in leads if l["proof_level"] == "hs"),
        "verified":           sum(1 for l in leads if l["status"] == "verified"),
        "outreach_now":       sum(1 for l in leads if l["route"] == "Outreach now"),
        "nurture":            sum(1 for l in leads if l["route"] == "Nurture"),
    }
    exporters = {e: {"hop": h, "name": Counter(r["shipper"] for r in by_exporter[e]).most_common(1)[0][0],
                     "buyers": len({r["ckey"] for r in by_exporter[e] if r["ckey"] in buyer_hop}),
                     "records": len(by_exporter[e])}
                 for e, h in exporter_hop.items()}
    return {"leads": leads, "summary": summary, "exporters": exporters}


def next_lookups(result, done, limit=15):
    """
    What to look up next to grow the data (the snowball done by hand):
    exporters whose US customers you haven't pulled, and buyers whose Indian
    suppliers you haven't pulled. `done` is a set of (company_key, kind).
    """
    exps = [(k, v) for k, v in result["exporters"].items() if (k, "exporter") not in done]
    exps.sort(key=lambda kv: (kv[1]["buyers"], -kv[1]["hop"]), reverse=True)
    buys = [l for l in result["leads"] if (l["company_key"], "buyer") not in done]
    return exps[:limit], buys[:limit]
