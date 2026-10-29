"""
F2 — HSN mapper.

Turns an Indian ITC-HS code (4 to 8 digits) and/or a product description into a
search profile: HS6 prefixes, alternate codes the same product ships under, a
keyword set and negative keywords. The profile is saved as editable JSON so you
can confirm or change it before searching.
"""

import json, os, re

from . import PROFILES_DIR, ensure_dirs

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MODEL = os.environ.get("BUYER_FINDER_MODEL", "claude-haiku-5-5")

# Neighbouring codes a product often ships under. Suggestions only: confirm in the profile.
ALTERNATES = {
    "482010": ["420500", "482090"],   # leather / paper journals and diaries
    "420500": ["482010", "420231"],
    "420221": ["420222", "420231"],   # handbags: leather vs textile vs small leather goods
    "420222": ["420221", "420292"],
    "630210": ["630231", "630260"],   # bed linen, cotton bed linen, toilet/kitchen linen
    "630231": ["630210", "630492"],
    "630492": ["630231", "630260"],   # cotton furnishing articles
    "570110": ["570231", "570500"],   # hand-knotted, kilim, other carpets
    "570500": ["570110", "570231"],
    "691390": ["691200", "691110"],   # ceramic ornaments vs tableware
    "711719": ["711790", "711311"],   # imitation jewellery vs silver jewellery
    "442199": ["441990", "442090"],   # wooden articles, tableware, decor boxes
    "940360": ["442199", "940389"],   # wooden furniture
    "741999": ["741810", "830629"],   # brass articles, utensils, statuettes
    "090421": ["090422", "091099"],   # dried chillies, crushed, spice mixes
}

# HS chapter names, used to seed keywords when no API key is set.
CHAPTERS = {
    "09": "spices, tea, coffee", "13": "gums, resins, lac", "19": "biscuits, namkeen, bakery",
    "20": "pickles, preserved fruit", "33": "essential oils, cosmetics", "39": "plastic articles",
    "41": "raw hides, leather", "42": "leather articles, bags, journals", "44": "wooden articles",
    "46": "basketry, wickerwork", "48": "paper, stationery, notebooks", "50": "silk",
    "52": "cotton fabric", "57": "carpets, rugs", "58": "embroidery, lace", "61": "knitted apparel",
    "62": "woven apparel", "63": "home textiles, bed linen, cushions", "64": "footwear",
    "68": "stone articles, marble", "69": "ceramics, pottery", "70": "glassware",
    "71": "jewellery", "73": "iron and steel articles", "74": "brass, copper articles",
    "83": "metal decor, bells, statuettes", "94": "furniture, lamps", "95": "toys",
    "96": "brushes, buttons, misc",
}

MAP_PROMPT = """You help an Indian exporter find US importers of their product in bill-of-lading data.

Indian ITC-HS code: {code}
Product description: {desc}

Return JSON only:
{{
  "product": "short product name",
  "hs6": ["6-digit HS codes this product most likely clears under, best first"],
  "us_hts": ["10-digit US HTS codes, best guess"],
  "alternates": ["other 6-digit codes the same product often ships under"],
  "keywords": ["8-15 lowercase words or short phrases that appear in shipment descriptions of this product, e.g. 'leather journal', 'deckle edge'"],
  "negative_keywords": ["5-10 lowercase words that signal a different product sharing those codes"]
}}
Bill-of-lading descriptions are short and uppercase, so prefer plain trade words over marketing language."""


def digits(code):
    return re.sub(r"\D", "", str(code or ""))


def _llm_map(code, desc):
    """Ask Claude for HS6, HTS and keywords. Returns None when no key or SDK."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
    except ImportError:
        return None
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system="You are a customs classification assistant. Return only valid JSON.",
        messages=[{"role": "user", "content": MAP_PROMPT.format(code=code or "unknown", desc=desc or "unknown")}],
    )
    text = msg.content[0].text.strip()
    text = text[text.find("{"): text.rfind("}") + 1]
    return json.loads(text)


def _fallback_keywords(code, desc):
    """Without the LLM: the description and its head noun, or the chapter's terms if no description."""
    if desc:
        desc = desc.lower().strip()
        words = [desc]
        head = re.findall(r"[a-z]{3,}", desc)
        if len(head) > 1:
            words.append(head[-1])          # "leather journal" -> also "journal"
        return words
    chapter = CHAPTERS.get(digits(code)[:2], "")
    return [w.strip() for w in chapter.split(",") if w.strip()]


def map_hsn(code="", desc=""):
    """Build a search profile dict from a code and/or description."""
    code = digits(code)
    if not code and not desc:
        raise ValueError("Give an HSN code, a product description, or both.")

    ai = None
    try:
        ai = _llm_map(code, desc)
    except Exception as e:                       # mapping still works without the LLM
        print(f"  ! LLM mapping failed ({e}); using built-in tables")

    hs6 = [digits(c)[:6] for c in (ai or {}).get("hs6", []) if len(digits(c)) >= 6]
    if code and len(code) >= 6 and code[:6] not in hs6:
        hs6.insert(0, code[:6])
    alternates = [digits(c)[:6] for c in (ai or {}).get("alternates", []) if len(digits(c)) >= 6]
    for h in hs6:
        alternates += ALTERNATES.get(h, [])
    alternates = [a for i, a in enumerate(alternates) if a not in hs6 and a not in alternates[:i]]

    # 4-digit input: search the whole heading
    prefixes = hs6 or ([code[:4]] if len(code) >= 4 else [])

    return {
        "product":           (ai or {}).get("product") or desc or f"HS {code}",
        "itc_hs":            code,
        "hs_prefixes":       prefixes,
        "alternates":        alternates,
        "use_alternates":    True,
        "us_hts":            (ai or {}).get("us_hts", []),
        "keywords":          [k.lower() for k in (ai or {}).get("keywords", [])] or _fallback_keywords(code, desc),
        "negative_keywords": [k.lower() for k in (ai or {}).get("negative_keywords", [])],
        "market":            "US",
        "seeds":             [],
        "mapped_by":         "llm" if ai else "tables",
    }


def profile_path(name):
    return PROFILES_DIR / f"{re.sub(r'[^a-z0-9-]+', '-', name.lower()).strip('-')}.json"


def save_profile(name, profile):
    ensure_dirs()
    path = profile_path(name)
    path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_profile(name):
    path = profile_path(name)
    if not path.exists():
        raise SystemExit(f"No profile '{name}'. Create it first: python3 -m buyer_finder map <code> --name {name}")
    return json.loads(path.read_text(encoding="utf-8"))


def search_prefixes(profile):
    prefixes = list(profile.get("hs_prefixes", []))
    if profile.get("use_alternates", True):
        prefixes += profile.get("alternates", [])
    return [digits(p) for p in prefixes if digits(p)]
