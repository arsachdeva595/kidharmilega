"""Combine the CBIC 8-digit HSN list with WCO HS names into one compact JSON for the supplier finder.

Output shape (keys kept short because the browser downloads it):
  s: {section roman numeral: section name}
  c: {2-digit chapter: [name, section]}
  h: {4-digit heading: name}
  x: {6-digit subheading: name}
  t: [[8-digit code, tariff-line detail], ...]   sorted by code

The CBIC descriptions repeat the whole heading text before the tariff-line detail
("BED LINEN, TABLE LINEN ... - OF COTTON - OF HANDLOOM"). We strip the words every line in the
heading shares, which leaves the detail ("Of cotton - of handloom").
"""
import csv, json, re
from pathlib import Path

HSN_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "hsn"

SMALL_WORDS = {"of", "or", "and", "the", "for", "in", "on", "with", "to", "a", "an", "by", "not", "nes"}


def _clean_name(t):
    t = (t or "").strip().strip('"').replace("﻿", "")
    t = re.sub(r"\s+", " ", t)
    return t[:1].upper() + t[1:] if t else t


def _sentence(t):
    """CBIC text is ALL CAPS. Turn it into sentence case and tidy separators."""
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^[\s:;,\-–]+", "", t)
    t = re.sub(r"\s*-{2,}\s*", " – ", t)
    t = re.sub(r"\s+-\s+", " – ", t)
    t = re.sub(r"\s*:\s*", ": ", t)
    t = t.strip(" :;,-–")
    if not t:
        return ""
    low = t.lower()
    # keep obvious acronyms/units upper-case
    low = re.sub(r"\b(inn|iso|cc|mm|kw|kva|led|lcd|pvc|hdpe|ldpe|dna|rna|usb|cd|dvd|tv|ac|dc)\b",
                 lambda m: m.group(1).upper(), low)
    return low[:1].upper() + low[1:]


def _common_prefix_words(texts):
    split = [t.split() for t in texts]
    if not split:
        return 0
    n = min(len(s) for s in split)
    i = 0
    while i < n and all(s[i] == split[0][i] for s in split):
        i += 1
    return i


def compile_hsn():
    sections = {}
    with open(HSN_DIR / "wco_sections.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            sections[row["section"].strip()] = _clean_name(row["name"])

    chapters, headings, subheadings = {}, {}, {}
    with open(HSN_DIR / "wco_hs.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code, lvl, name = row["hscode"].strip(), row["level"].strip(), _clean_name(row["description"])
            if lvl == "2":
                chapters[code] = [name, row["section"].strip()]
            elif lvl == "4":
                headings[code] = name
            elif lvl == "6":
                subheadings[code] = name

    raw = json.loads((HSN_DIR / "cbic_hsn_8digit.json").read_text(encoding="utf-8"))
    by_heading = {}
    lines = {}
    for item in raw:
        code = str(item["code"]).strip().zfill(8)
        if not re.fullmatch(r"\d{8}", code):
            continue
        desc = re.sub(r"\s+", " ", str(item.get("description", ""))).strip()
        lines[code] = desc
        by_heading.setdefault(code[:4], []).append(code)

    tariff = []
    for h4, codes in by_heading.items():
        texts = [lines[c] for c in codes]
        cut = _common_prefix_words(texts) if len(texts) > 1 else 0
        for c in codes:
            words = lines[c].split()
            detail = " ".join(words[cut:]) if len(texts) > 1 else ""
            # Single-line headings: keep whatever follows the first separator, if anything.
            if not detail and len(texts) == 1:
                m = re.search(r"\s-\s(.+)$", lines[c])
                detail = m.group(1) if m else ""
            detail = _sentence(detail)
            if len(detail) > 220:
                detail = detail[:217].rsplit(" ", 1)[0] + "…"
            tariff.append([c, detail])

    # Chapters missing from the CBIC file (e.g. 97, works of art): fall back to 6-digit subheadings
    # so a craft seller can still pick their product. Marked by a 6-digit code.
    have = {c for c, _ in tariff}
    have_ch = {c[:2] for c in have}
    for x6 in subheadings:
        if x6[:2] not in have_ch and x6[:2] != "77":
            tariff.append([x6, ""])

    tariff.sort(key=lambda r: r[0])
    # Headings that the CBIC list uses but WCO 2022 dropped/renamed: name them from the CBIC text.
    for c, _ in tariff:
        h4 = c[:4]
        if h4 not in headings:
            first = lines.get(by_heading.get(h4, [c])[0], "")
            headings[h4] = _sentence(" ".join(first.split()[:_common_prefix_words([lines[x] for x in by_heading.get(h4, [])]) or 12]))
        if len(c) == 8 and c[:6] not in subheadings:
            subheadings[c[:6]] = ""

    return {"s": sections, "c": chapters, "h": headings, "x": {k: v for k, v in subheadings.items() if v}, "t": tariff}


if __name__ == "__main__":
    d = compile_hsn()
    print(len(d["t"]), "lines,", len(d["h"]), "headings,", len(d["x"]), "subheadings")
    for code in ["63022110", "63021010", "84021990", "52064400", "09042110", "71131910", "95030010", "970110", "44201100", "57011000"]:
        row = next((r for r in d["t"] if r[0] == code), None)
        print(code, "|", d["h"].get(code[:4]), "|", d["x"].get(code[:6]), "|", row and row[1])
    js = json.dumps(d, separators=(",", ":"), ensure_ascii=False)
    print("size", len(js) // 1024, "KB")
