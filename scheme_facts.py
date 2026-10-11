"""Official central-scheme wording for KidharMilega.

Product pages repeat benefits that were generated once per district. This module
is the single wording for those benefits, checked against the ministry pages
named in SOURCES. build.py applies it while rendering, and the audit script
writes the same wording back into the source data.
"""

from __future__ import annotations

import re

# Official pages used to check the figures below.
SOURCES = {
    "PMEGP": "https://www.msme.gov.in/offerings/schemes-and-services/details/prime-minister-employment-generation-programme-and-other-credit-support-schemes-1-MDMzETMtQWa",
    "MUDRA": "https://www.mudra.org.in/",
    "PMFME": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2239085",
    "PMFME_END": "https://pmfme.mofpi.gov.in/pmfme/newsletters/PMFME_Connect_Monthly_Newsletter_May_2026.pdf",
    "GI": "https://ipindia.gov.in/geographical-indications-before-you-apply-forms",
    "IEC": "https://www.dgft.gov.in/CP/?opt=iec-profile-management",
    "UDYAM": "https://udyamregistration.gov.in/",
    "STANDUP": "https://financialservices.gov.in/stand-india-scheme-supi",
    "CGTMSE": "https://www.cgtmse.in/Home/VS/96",
    "VISH": "https://csc.gov.in/pmvishwakarma",
    "FSSAI": "https://foscos.fssai.gov.in/fee/CL",
    "MAKHANA": "https://apeda.gov.in/sites/default/files/2026-01/MIC_November_Monthly_dashboard_Makhana_311225.pdf",
    "MARKET": "",
}

PMEGP_DESC = (
    "New unit under the December 2023 guidelines: maximum project cost ₹50 lakh for manufacturing "
    "and ₹20 lakh for service or business. Margin-money subsidy is 15% of project cost in urban areas "
    "and 25% in rural areas for the general category, and 25% urban / 35% rural for special categories "
    "(SC, ST, OBC, minorities, women, ex-servicemen, transgender persons, persons with disability, NER, "
    "hill and border areas, and aspirational districts). Own contribution is 10% for general category "
    "and 5% for special categories. Bank finance up to ₹10 lakh is collateral-free under RBI guidelines, "
    "with CGTMSE cover. Apply at pmegp.msme.gov.in (PMEGP 2.0). The scheme was approved through 2025-26; "
    "treat any extension as unconfirmed until the Ministry of MSME publishes it."
)

MUDRA_DESC = (
    "PMMY ceilings: Shishu up to ₹50,000; Kishore above ₹50,000 and up to ₹5 lakh; Tarun above ₹5 lakh "
    "and up to ₹10 lakh; Tarun Plus above ₹10 lakh and up to ₹20 lakh, and only after an earlier Tarun "
    "loan has been repaid. The maximum is ₹20 lakh. The lending bank sets the interest rate; the scheme "
    "does not fix one rate. Apply through a bank, NBFC or MFI, or at udyamimitra.in."
)

PMFME_DESC = (
    "Credit-linked capital subsidy of 35% of the eligible project cost, capped at ₹10 lakh per individual "
    "micro food-processing unit. The Ministry of Food Processing Industries has confirmed the scheme only "
    "until 30 September 2026. Apply via pmfme.mofpi.gov.in."
)

STANDUP_DESC = (
    "Bank loans from ₹10 lakh to ₹1 crore for SC, ST and women entrepreneurs setting up a greenfield "
    "enterprise in manufacturing, services, trading or activities allied to agriculture. The borrower "
    "must bring in at least 10% of the project cost. The Department of Financial Services records the "
    "scheme as operational until 31 March 2025. A replacement has been discussed; do not treat the scheme "
    "as open until financialservices.gov.in says so."
)

CGTMSE_DESC = (
    "A credit guarantee, not a cash subsidy, so a bank can lend without collateral or a third-party "
    "guarantee. From 1 April 2025 the guarantee ceiling is ₹10 crore per borrower. Coverage is generally "
    "75% of the amount in default, and higher for micro enterprises, women, SC/ST, the North East and "
    "similar categories. Separately, PMEGP bank finance up to ₹10 lakh is collateral-free under RBI guidelines."
)

VISH_DESC = (
    "For artisans in the 18 listed trades: a toolkit incentive of up to ₹15,000, and collateral-free "
    "enterprise loans in two tranches of up to ₹1 lakh (18 months) and ₹2 lakh (30 months) at 5% interest, "
    "with a Government of India interest subvention. Basic training carries a stipend of ₹500 per day. "
    "Details are on pmvishwakarma.gov.in."
)

GI_EXISTS = (
    "This product already has a GI registration. A producer files Form GI-3A with the Geographical "
    "Indications Registry (IP India, Chennai) to be entered as an authorised user. The official fee is ₹10. "
    "It is not a Ministry of Textiles filing."
)

GI_ABSENT = (
    "An individual does not buy a GI tag from the Ministry of Textiles. A new Geographical Indication is "
    "filed by an association of producers with the Geographical Indications Registry (IP India). Once a GI "
    "exists, a producer applies as an authorised user on Form GI-3A. The official fee is ₹10."
)

IEC_SENTENCE = "IEC from DGFT (dgft.gov.in); the application fee is ₹500."
UDYAM_SENTENCE = "Udyam registration at udyamregistration.gov.in is free. No fee is payable."
FSSAI_SENTENCE = (
    "FSSAI registration is ₹100 a year; a State licence is typically ₹2,000–₹5,000 a year and a Central "
    "licence is ₹7,500 a year, depending on the kind of business (FoSCoS)."
)

# Compact wording for steps, FAQs and stories. Scheme cards use the full paragraphs above.
PMEGP_SHORT = (
    "PMEGP (December 2023 guidelines, approved through 2025-26): maximum project cost ₹50 lakh for manufacturing "
    "and ₹20 lakh for service; margin-money subsidy 15% urban / 25% rural for the general category and 25% urban / 35% rural "
    "for special categories; own contribution 10% general and 5% special; bank finance up to ₹10 lakh is collateral-free. "
    "Apply at pmegp.msme.gov.in."
)
MUDRA_SHORT = (
    "PMMY: Shishu up to ₹50,000; Kishore up to ₹5 lakh; Tarun up to ₹10 lakh; Tarun Plus up to ₹20 lakh "
    "(maximum ₹20 lakh). The bank sets the interest rate."
)
PMFME_SHORT = (
    "PMFME: 35% credit-linked subsidy, capped at ₹10 lakh per individual micro food unit, confirmed only until "
    "30 September 2026. Apply via pmfme.mofpi.gov.in."
)
STANDUP_SHORT = (
    "Stand-Up India: bank loans from ₹10 lakh to ₹1 crore for SC, ST and women entrepreneurs in a greenfield enterprise, "
    "with at least 10% own contribution. The Department of Financial Services records the scheme as operational until "
    "31 March 2025; do not treat it as open."
)
CGTMSE_SHORT = (
    "CGTMSE is a credit guarantee, not a cash subsidy. From 1 April 2025 the ceiling is ₹10 crore per borrower "
    "(coverage generally 75%). PMEGP bank finance up to ₹10 lakh is separately collateral-free."
)
VISH_SHORT = (
    "PM Vishwakarma: toolkit incentive up to ₹15,000; collateral-free loans up to ₹1 lakh then ₹2 lakh at 5% interest; "
    "training stipend ₹500 per day."
)

TITLES = {
    "PMEGP": "PMEGP (Prime Minister's Employment Generation Programme)",
    "MUDRA": "PM Mudra Yojana (PMMY)",
    "PMFME": "PMFME (Pradhan Mantri Formalisation of Micro Food Processing Enterprises)",
    "STANDUP": "Stand-Up India",
    "CGTMSE": "CGTMSE",
    "VISH": "PM Vishwakarma",
}

DESCS = {
    "PMEGP": PMEGP_DESC,
    "MUDRA": MUDRA_DESC,
    "PMFME": PMFME_DESC,
    "STANDUP": STANDUP_DESC,
    "CGTMSE": CGTMSE_DESC,
    "VISH": VISH_DESC,
}

SCHEME_FIELDS = {
    "relevant_central_scheme_1",
    "relevant_central_scheme_2",
    "relevant_state_scheme_1",
    "relevant_state_scheme_2",
}

SKIP_FIELDS = {
    "district_id", "state", "district_name", "district_name_hin", "url_slug",
    "population", "area_km2", "literacy_rate", "main_languages", "city_tier",
    "odop_product_name", "odop_category", "odop_gi_tag", "gi_tag_year",
    "page_status", "tier_priority", "primary_keyword", "odop_photo",
    "opportunity_score", "export_potential", "min_setup_cost", "max_setup_cost",
    "success_story_cost", "success_story_employees",
}

MARKET_LINE = "Not published here"

# Phrases that cite a rupee market, a unit count, or an export share we could not
# match to an official source. Replacements stay non-numeric except the APEDA price.
MAKHANA_FIXES = [
    (
        r"₹\s*3,000\s*Crore current India market size;?\s*expected ₹\s*6,000\+\s*Crore within 2[–-]3 years;?",
        "A rupee market-size forecast is not shown because it was not verified against an official source.",
        "MARKET",
    ),
    (
        r"Bihar alone produces 85[–-]90%\s*of India's total makhana;?",
        "Bihar is the main makhana-growing state.",
        "MARKET",
    ),
    (
        r"over 25,000 metric tonnes exported annually",
        "an export-tonnage figure is not repeated here",
        "MARKET",
    ),
    (
        r"collectively managing over 25,000 metric tonnes in annual exports[^.]{0,80}",
        "the belt handles a large share of India's makhana trade",
        "MARKET",
    ),
    (
        r"1,100 registered exporters and 547 active Indian exporters",
        "registered exporters (the earlier headcount was not re-checked against an official source)",
        "MARKET",
    ),
    (
        r"800\+\s*units;?\s*",
        "",
        "MARKET",
    ),
    (
        r"60%\s*of Bihar's makhana exports originate here",
        "much of the state's makhana trade is associated with this belt",
        "MARKET",
    ),
    (
        r"USD\s*8[–-]12/kg(?:\s*\(₹670[–-]1,000/kg\))?",
        "about USD 13–26/kg by destination (APEDA dashboard: UAE about USD 13.3/kg, Germany about USD 26/kg)",
        "MAKHANA",
    ),
    (
        r"USA alone buys 2,000 tonnes/year;?\s*market is 70%\s*undersupplied\.?",
        "The United States is a major buyer. A tonne-count and an undersupplied percentage are not repeated because they were not verified against an official source.",
        "MARKET",
    ),
    (
        r"4,855 shipments exported in (?:the )?last 12 months[^.]*",
        "shipment counts from an unverified tally are not repeated",
        "MARKET",
    ),
    (
        r"the US market alone consumes 2,000 tonnes annually while Bihar exported only 600 tonnes in 2024 — a 70% untapped gap",
        "the United States is a major buyer; a gap percentage is not stated because those tonne figures were not verified against an official source",
        "MARKET",
    ),
    (
        r"producing over 85%\s*of the nation['’]s fox nuts",
        "producing much of the nation's fox nuts",
        "MARKET",
    ),
    (
        r"Bihar supplies over 85%\s*of India['’]s makhana and accounts for 90%\s*of domestic production",
        "Bihar is the main makhana-growing state",
        "MARKET",
    ),
    (
        r"accounts for 90%\s*of domestic production",
        "accounts for most domestic production",
        "MARKET",
    ),
    (
        r"With 1,100 exporters and a projected industry growth rate of 9\.7%\s*CAGR through 2032",
        "Exporter headcounts and growth forecasts are not repeated here",
        "MARKET",
    ),
    (
        r"\b1,100 exporters\b",
        "exporters",
        "MARKET",
    ),
    (
        r"revenue ₹3,35,000[–-]5,00,000",
        "a revenue figure calculated from the old price is not repeated",
        "MARKET",
    ),
    (
        r"FOB export at about USD 13–26/kg by destination \(APEDA dashboard: UAE about USD 13\.3/kg, Germany about USD 26/kg\) \(₹670[–-]1,000/kg\)",
        "FOB export at about USD 13–26/kg by destination (APEDA dashboard: UAE about USD 13.3/kg, Germany about USD 26/kg)",
        "MAKHANA",
    ),
]


_OFFICIAL_BLOBS = (
    PMEGP_DESC,
    PMEGP_SHORT,
    MUDRA_DESC,
    MUDRA_SHORT,
    PMFME_DESC,
    PMFME_SHORT,
    STANDUP_DESC,
    STANDUP_SHORT,
    CGTMSE_DESC,
    CGTMSE_SHORT,
    VISH_DESC,
    VISH_SHORT,
    GI_EXISTS,
    GI_ABSENT,
    IEC_SENTENCE,
    UDYAM_SENTENCE,
    FSSAI_SENTENCE,
)


def _is_official_fragment(span: str, canonical: str = "") -> bool:
    """A later pass splits official multi-sentence wording at the first period,
    or matches a scheme name inside a sentence that is already correct.
    That fragment must not be rewritten."""
    s = " ".join(span.split()).strip().strip(" .")
    if len(s) < 40:
        return False
    blobs = [canonical] if canonical else []
    blobs.extend(_OFFICIAL_BLOBS)
    for c in blobs:
        c = " ".join(c.split()).strip()
        if not c:
            continue
        if s in c or c in s:
            return True
        for sent in re.split(r"(?<=[.।])\s+", c):
            sent = sent.strip().strip(".")
            if len(sent) > 40 and sent in s:
                return True
    return False


def _nums(span: str) -> list[int]:
    found = []
    for n in re.findall(r"(?:₹|Rs\.?)\s*([\d,]+)", span, flags=re.I):
        digits = n.replace(",", "")
        if digits.isdigit():
            found.append(int(digits))
    return found


def _pmegp_ok(span: str) -> bool:
    low = span.lower()
    return (
        "50 lakh" in low
        and "20 lakh" in low
        and "15%" in span
        and "35%" in span
        and "pmegp.msme.gov.in" in low
    )


def _pmegp_wrong(span: str) -> bool:
    if _pmegp_ok(span):
        return False
    if re.search(r"upgradation|2nd loan|second loan|second financial", span, flags=re.I):
        return False
    return bool(re.search(r"₹|%|\d+\s*lakh|\d+\s*L\b", span))


def _mudra_ok(span: str) -> bool:
    low = span.lower()
    return "50,000" in span and "5 lakh" in low and "10 lakh" in low and "20 lakh" in low


def _mudra_wrong(span: str) -> bool:
    if _mudra_ok(span) and not re.search(r"\d+(?:\.\d+)?\s*%\s*interest|0\.5%\s*concession", span, flags=re.I):
        return False
    if _is_official_fragment(span):
        return False
    # Any rupee or percent attached to Mudra that is not the four official ceilings.
    return bool(re.search(r"₹|%|\d+(?:\.\d+)?\s*L\b|\d+\s*lakh", span, flags=re.I))


def _pmfme_ok(span: str) -> bool:
    return "35%" in span and re.search(r"10\s*lakh", span, flags=re.I) and "30 September 2026" in span


def _pmfme_wrong(span: str) -> bool:
    if _pmfme_ok(span):
        return False
    return bool(re.search(r"₹|%|lakh|subsidy|grant", span, flags=re.I))


def _vish_ok(span: str) -> bool:
    low = span.lower()
    return "15,000" in span and "1 lakh" in low and "2 lakh" in low and "5%" in span and "500 per day" in low


def _vish_wrong(span: str) -> bool:
    if _vish_ok(span):
        return False
    return bool(re.search(r"₹|%|lakh|stipend|interest|cashback|toolkit|loan|credit", span, flags=re.I))


def _standup_ok(span: str) -> bool:
    low = span.lower()
    return "10 lakh" in low and "1 crore" in low and "31 March 2025" in span


def _standup_wrong(span: str) -> bool:
    if _standup_ok(span):
        return False
    if re.search(r"does(?:n['’]t| not) apply|not applicable|ineligible", span, flags=re.I):
        return False
    return bool(re.search(r"₹|lakh|crore|loan|subsidy", span, flags=re.I))


def _cgtmse_wrong(span: str) -> bool:
    low = span.lower()
    if "10 crore" in low and "1 april 2025" in low:
        return False
    if re.search(r"₹\s*50\s*lakh|₹\s*50\s*L\b", span, flags=re.I):
        return True
    if re.search(r"\bCGTM?SE\b", span, flags=re.I) and re.search(r"₹|lakh|crore|%", span, flags=re.I):
        return "10 crore" not in low
    return False


def _gi_wrong(span: str) -> bool:
    if "Form GI-3A" in span or re.search(r"official fee is ₹\s*10\b", span):
        return False
    if re.search(r"not a Ministry of Textiles", span):
        return False
    if re.search(r"ministry of textile", span, flags=re.I):
        return True
    nums = _nums(span)
    if nums and any(n != 10 for n in nums):
        return True
    if re.search(r"₹\s*25\s*[–-]\s*40|25-40\s*k|40k fee|40,000", span, flags=re.I):
        return True
    return False


def _iec_wrong(span: str) -> bool:
    has_500 = bool(re.search(r"₹\s*500\b", span))
    has_wrong = bool(re.search(
        r"₹\s*0\b|\bfree\b|no (?:cost|fee)|zero[- ]cost|₹\s*5,?000|₹\s*2,?000|₹\s*1,?000|₹\s*10,?000",
        span,
        flags=re.I,
    ))
    if has_500 and not has_wrong:
        return False
    return has_wrong


def _udyam_wrong(span: str) -> bool:
    # State schemes with "Udyam" in the name (Udyam Kranti, Udyam Sakhi) are not the registration fee.
    if re.search(r"kranti|sakhi|yojana|scheme", span, flags=re.I) and not re.search(
        r"udyamregistration|udyam registration fee|register(?:ing)? (?:on |for )?udyam", span, flags=re.I
    ):
        return False
    if re.search(r"print|sticker|certificate printed", span, flags=re.I):
        return False
    if re.search(r"fee waiver", span, flags=re.I):
        return True
    if re.search(r"₹\s*[1-9]", span) and re.search(r"udyam registration|registration fee", span, flags=re.I):
        return True
    return False


def _fssai_ok(span: str) -> bool:
    if re.search(r"lab test", span, flags=re.I):
        return True
    nums = _nums(span)
    if not nums:
        return not bool(re.search(r"\bfree\b|₹\s*0\b", span, flags=re.I))
    allowed = {100, 2000, 3000, 5000, 7500}
    return all(n in allowed for n in nums)


def _fssai_wrong(span: str) -> bool:
    if re.search(r"lab test", span, flags=re.I):
        return False
    # A free training video is not the licence fee.
    if re.search(r"training|youtube|video|course", span, flags=re.I) and not re.search(
        r"licen[cs]e|registration", span, flags=re.I
    ):
        return False
    return not _fssai_ok(span) and bool(re.search(r"₹|\bfree\b|fee", span, flags=re.I))


def _primary_scheme(title: str) -> str | None:
    head = title.lower()[:56]
    checks = [
        ("pmfme", "PMFME"),
        ("micro food", "PMFME"),
        ("formalisation of micro food", "PMFME"),
        ("formalization of micro food", "PMFME"),
        ("vishwakarma", "VISH"),
        ("pmegp", "PMEGP"),
        ("employment generation", "PMEGP"),
        ("stand-up", "STANDUP"),
        ("standup", "STANDUP"),
        ("cgtmse", "CGTMSE"),
        ("cgtsme", "CGTMSE"),
        ("mudra", "MUDRA"),
        ("pmmy", "MUDRA"),
    ]
    for key, code in checks:
        if key in head:
            return code
    return None


# Sentence end, or a comma that introduces the next scheme. Passing mentions such as
# "with CGTMSE cover" must not split a sentence that is already the official wording.
# re.IGNORECASE makes \b match inside "dgftiec", so scheme names use explicit letter lookarounds.
_NM = r"(?<![A-Za-z])(?:PMEGP|MUDRA|PMMY|PMFME|Vishwakarma|SFURTI|Stand[- ]?Up|FSSAI|IEC|Udyam)(?![A-Za-z])|GI certification|GI registration"
_SCHEME_AHEAD = _NM
_NEXT_BOUNDARY = re.compile(
    rf"[.।!?](?:\s|$)|,\s*(?={_SCHEME_AHEAD})|(?={_SCHEME_AHEAD})",
    flags=re.I,
)
_PREFIX = re.compile(
    r"(?:₹[\d,]+(?:\s*[–\-]\s*₹?[\d,]+)?\s+from\s+)?"
    r"(?:Apply for |Apply PM |apply for |Apply |File for |File |Get |Obtain |PM )$",
    flags=re.I,
)


def _span_bounds(text: str, match_start: int, match_end: int) -> tuple[int, int]:
    """Start just before the scheme name (drop a short 'PM' / 'Apply for' prefix and a rupee amount
    glued to it). End at the next sentence break or the next scheme name, so one fix does not eat the next claim."""
    back = text[max(0, match_start - 60):match_start]
    pre = _PREFIX.search(back)
    start = match_start - len(pre.group(0)) if pre and pre.group(0).strip() else match_start
    window = text[match_end:match_end + 420]
    end_at = None
    for m in _NEXT_BOUNDARY.finditer(window):
        # A sentence break is always a boundary. Another scheme name is a boundary only
        # once we have moved past the keyword we already matched.
        if m.start() == 0 and not re.match(r"[.।!?]", m.group(0)):
            continue
        end_at = match_end + m.end()
        # If we stopped on the next scheme name, do not consume that name.
        if not re.match(r"[.।!?]", m.group(0)):
            end_at = match_end + m.start()
        break
    if end_at is None:
        end_at = min(len(text), match_end + 220)
    return start, max(end_at, match_end)


_NEXT_SCHEME = re.compile(_NM, flags=re.I)


def _tighten(text: str, match_end: int, hard_end: int) -> int:
    """Include the fee clause after a scheme name, including a second parenthetical
    such as 'IEC (Import-Export Code) ... (₹0)'. Stop before the next scheme."""
    limit = min(hard_end, match_end + 160)
    nxt = _NEXT_SCHEME.search(text, match_end, limit)
    if nxt:
        limit = nxt.start()
    i = match_end
    while i < limit:
        if text[i] == "(":
            close = text.find(")", i, limit + 50)
            if close == -1 or close >= limit:
                break
            i = close + 1
            if re.search(r"₹|Rs\.?|\bfree\b|\bfee\b", text[text.rfind("(", match_end, i):i], flags=re.I):
                return i
            continue
        if text[i] in ".।!?;":
            break
        if re.match(r"free\b", text[i:], flags=re.I):
            return i + 4
        i += 1
    fee = re.search(r"\([^)]*(?:₹|Rs\.?|\bfree\b)[^)]*\)", text[match_end:limit], flags=re.I)
    if fee and match_end + fee.start() < limit:
        return match_end + fee.end()
    return min(i, limit)


def _replace_spans(text: str, start_re: str, is_wrong, replacement: str, audit, page: str, field: str, source_key: str, tight: bool = False) -> str:
    if not text or not re.search(start_re, text, flags=re.I):
        return text
    out = []
    last = 0
    for m in re.finditer(start_re, text, flags=re.I):
        if m.start() < last:
            continue
        start, end = _span_bounds(text, m.start(), m.end())
        if tight:
            end = _tighten(text, m.end(), end)
        if start < last:
            start = last
        span = text[start:end]
        if _is_official_fragment(span, replacement) or not is_wrong(span):
            continue
        out.append(text[last:start])
        repl = replacement if replacement.endswith((".", "।")) else replacement + "."
        if out and out[-1] and out[-1][-1].isalnum():
            out.append(" ")
        if repl.endswith(".") and text[end:end + 1] == ",":
            end += 1
            if text[end:end + 1] == " ":
                end += 1
        if repl.endswith(".") and (text[end:end + 1].isalnum() or text[end:end + 1] == "("):
            repl += " "
        out.append(repl)
        if audit is not None:
            audit(page, field, span.strip(), repl, SOURCES.get(source_key, ""))
        last = end
    out.append(text[last:])
    return "".join(out)


def _window_sub(text, pattern, is_wrong, replacement, audit, page, field, source_key):
    if not text:
        return text

    def repl(m):
        span = m.group(0)
        if not is_wrong(span):
            return span
        if audit is not None:
            audit(page, field, span.strip(), replacement, SOURCES.get(source_key, ""))
        return replacement

    return re.sub(pattern, repl, text, flags=re.I)


def correct_text(text: str, *, gi_yes: bool = False, field: str = "", page: str = "", audit=None) -> str:
    """Return text with wrong scheme figures replaced. Identity fields are not passed here."""
    if text is None:
        return text
    text = str(text)
    if not text.strip():
        return text
    original = text

    if field == "production_scale":
        if text.strip() == MARKET_LINE:
            return text
        if re.search(r"\d", text):
            if audit is not None:
                audit(
                    page,
                    field,
                    text.strip(),
                    MARKET_LINE,
                    SOURCES["MARKET"],
                )
            return MARKET_LINE
        return text

    if field in SCHEME_FIELDS:
        parts = re.split(r"\s+[—–-]\s+", text, maxsplit=1)
        title = parts[0].strip()
        code = _primary_scheme(title)
        if code:
            new = f"{TITLES[code]} — {DESCS[code]}"
            if new != text and audit is not None:
                audit(page, field, text.strip(), new, SOURCES[code])
            return new if new != text else text

    gi_sentence = GI_EXISTS if gi_yes else GI_ABSENT

    def _gi_repl(span: str) -> str:
        if gi_yes or re.search(r"already", span, flags=re.I):
            return GI_EXISTS
        return gi_sentence

    text = _replace_spans(
        text,
        r"GI(?:\s+tag)?\s+(?:certification|registration)|GI Mark licen[cs]e|authorised user|authorized user|Ministry of Textiles?(?=[^.]{0,80}(?:₹|Rs\.?|\bfee\b))",
        _gi_wrong,
        gi_sentence,
        audit, page, field, "GI",
    )
    text = _replace_spans(
        text,
        r"(?<![A-Za-z])PMEGP(?![A-Za-z])|Prime Minister(?:'s|’s)? Employment Generation Programme|Pradhan Mantri Employment Generation",
        _pmegp_wrong,
        PMEGP_SHORT,
        audit, page, field, "PMEGP",
    )
    text = _replace_spans(
        text,
        r"(?<![A-Za-z])MUDRA(?![A-Za-z])|(?<![A-Za-z])PMMY(?![A-Za-z])|Mudra Yojana|Mudra Loan",
        _mudra_wrong,
        MUDRA_SHORT,
        audit, page, field, "MUDRA",
    )
    text = _replace_spans(
        text,
        r"(?<![A-Za-z])PMFME(?![A-Za-z])|PM\s+MFPEU|PM\s+Micro\s+Food|Micro Food Processing|Formalisation of Micro Food|Formalization of Micro Food",
        _pmfme_wrong,
        PMFME_SHORT,
        audit, page, field, "PMFME",
    )
    text = _replace_spans(
        text,
        r"(?<![A-Za-z])Vishwakarma(?![A-Za-z])",
        _vish_wrong,
        VISH_SHORT,
        audit, page, field, "VISH",
    )
    text = _replace_spans(
        text,
        r"Stand[- ]?Up India",
        _standup_wrong,
        STANDUP_SHORT,
        audit, page, field, "STANDUP",
    )
    text = _replace_spans(
        text,
        r"(?<![A-Za-z])CGTMSE(?![A-Za-z])|(?<![A-Za-z])CGTSME(?![A-Za-z])",
        _cgtmse_wrong,
        CGTMSE_SHORT,
        audit, page, field, "CGTMSE",
    )

    text = _replace_spans(
        text,
        r"(?<![A-Za-z])IEC(?![A-Za-z])",
        _iec_wrong,
        IEC_SENTENCE,
        audit, page, field, "IEC",
        tight=True,
    )
    text = _replace_spans(
        text,
        r"(?<![A-Za-z])Udyam registration(?![A-Za-z])|(?<![A-Za-z])Udyam portal(?![A-Za-z])|register(?:ing)? (?:on |for )?Udyam",
        _udyam_wrong,
        UDYAM_SENTENCE,
        audit, page, field, "UDYAM",
        tight=True,
    )
    text = _replace_spans(
        text,
        r"(?<![A-Za-z])FSSAI(?![A-Za-z])",
        _fssai_wrong,
        FSSAI_SENTENCE,
        audit, page, field, "FSSAI",
        tight=True,
    )

    def total_sub(m):
        span = m.group(0)
        if not re.search(r"₹|\d", span):
            return span
        repl = "A combined subsidy total is not stated here; each scheme portal lists its own cap."
        if audit is not None:
            audit(page, field, span.strip(), repl, SOURCES["PMEGP"])
        return repl

    text = re.sub(
        r"Total (?:(?:possible|potential|govt|government|combined)\s+){0,3}(?:support|subsidy|help)[^.]{0,180}",
        total_sub,
        text,
        flags=re.I,
    )
    def reg_sub(m):
        span = m.group(0)
        repl = "Each licence has its own official fee, listed above."
        if audit is not None:
            audit(page, field, span.strip(), repl, SOURCES["FSSAI"])
        return repl

    text = re.sub(
        r"Total (?:regulatory|formal) cost:\s*₹[^.]{0,80}",
        reg_sub,
        text,
        flags=re.I,
    )

    text = re.sub(r"https?://(?:www\.)?pmegp\.gov\.in\S*", "https://pmegp.msme.gov.in", text, flags=re.I)
    text = re.sub(r"\bpmegp\.gov\.in\b", "pmegp.msme.gov.in", text, flags=re.I)

    for pattern, repl, key in MAKHANA_FIXES:
        new_text, n = re.subn(pattern, repl, text, flags=re.I)
        if n and audit is not None:
            audit(page, field, pattern, repl, SOURCES.get(key, ""))
        text = new_text

    # Export-share percentages (not margin ranges such as "45-60% FOB").
    if field not in {"gross_margin_wholesale", "gross_margin_d2c", "export_margin", "breakeven_timeline"}:
        def share_sub(m):
            span = m.group(0)
            repl = "a share not verified against an official source"
            if audit is not None:
                audit(page, field, span.strip(), repl, SOURCES["MARKET"])
            return repl

        text = re.sub(
            r"(?:about |over |nearly |around )?[\d,.]+\s*(?:%|percent)\s+of\s+(?:India(?:['’]s)?|the nation(?:['’]s)?|national|world(?:['’]s)?|global|Bihar(?:['’]s)?|total exports|exports)\b[^.;]{0,80}",
            share_sub,
            text,
            flags=re.I,
        )

    if text == original:
        return text
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +([,;.])", r"\1", text)
    return text.strip() if field in SCHEME_FIELDS else text


def correct_mapping(row: dict, *, gi_yes: bool, page: str, audit=None, skip=None) -> dict:
    """Correct every textual field on a district or idea record. Returns a new dict."""
    skip = SKIP_FIELDS if skip is None else skip
    out = dict(row)
    for key, value in row.items():
        if key in skip or not isinstance(value, str):
            continue
        out[key] = correct_text(value, gi_yes=gi_yes, field=key, page=page, audit=audit)
    return out
