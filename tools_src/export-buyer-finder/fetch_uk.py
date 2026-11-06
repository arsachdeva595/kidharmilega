"""UK importers by HS6 from HMRC's trader data (uktradeinfo OData API, no key), for the launch chapters.

    python3 tools_src/export-buyer-finder/fetch_uk.py                 # chapters below, from Jan of last year
    python3 tools_src/export-buyer-finder/fetch_uk.py --chapters 42,48

Meant to run monthly (HMRC adds a month and drops traders who ask to be removed, so each run rebuilds the lists
from scratch; only the per-code raw cache is reused within a run). Writes data/uk_importers/uk_importers_hs6.json:

  {"months": [first, last], "hs6": {"482010": [[name, town, postcode, segment, months_active, last_month, related], ...]}}

related = how many other HS6 codes in the same chapter the company imported (e.g. notebooks plus leather goods),
a sign of a real buyer of the category rather than a one-off.

HMRC lists who imported a CN8 code in a month, with no source country and no value, so these are importers of the
product from anywhere, never "buyers from India". Rows are cleaned (couriers, brokers, and addresses shared by many
traders such as Amazon's AB10 1ZP intake address) and sorted best first; at most MAX_PER_CODE kept per HS6.
Licence: Open Government Licence v3.0.
"""
import json, sys, time, urllib.error, urllib.parse, urllib.request
from collections import defaultdict, Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from segments import classify, SEGMENT_RANK  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "data" / "uk_importers" / "uk_importers_hs6.json"
RAW = ROOT / "data" / "uk_importers" / "_raw"          # per-CN8 cache (gitignored), cleared at the start of each month
API = "https://api.uktradeinfo.com"
CHAPTERS = (sys.argv[sys.argv.index("--chapters") + 1].split(",") if "--chapters" in sys.argv
            else ["42", "48", "63", "71", "68", "44"])
FROM_MONTH = int(time.strftime("%Y")) * 100 - 99      # January of last year, e.g. 202501 in 2026
SHARED_POSTCODE = 15                                   # more traders than this at one postcode = an agent's address
MAX_PER_CODE = 150


def get(url, tries=8):
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "kidharmilega-export-tool"})
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read().decode()
            time.sleep(2)
            return json.loads(body)
        except (OSError, json.JSONDecodeError) as e:  # HTTPError, URLError, timeouts and connection resets
            wait = 15 * (t + 1)
            print(f"  retry in {wait}s ({getattr(e, 'code', e)})", flush=True)
            time.sleep(wait)
    raise RuntimeError("gave up on " + url)


def q(path, params):
    return f"{API}/{path}?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


def cn8_codes(ch):
    d = get(q("Commodity", {"$filter": f"startswith(cast(CommodityId,Edm.String),'{ch}')", "$select": "CommodityId"}))
    # CommodityId is a number, so "starts with 71" also matches 7-digit ids of chapter 07 (0712xxxx → 712xxxx).
    codes = (str(x["CommodityId"]).zfill(8) for x in d.get("value", []))
    return sorted(c for c in codes if len(c) == 8 and c[:2] == ch)


def imports(cn8):
    cache = RAW / f"{cn8}_{FROM_MONTH}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    url = q("Import", {"$filter": f"CommodityId eq {int(cn8)} and MonthId ge {FROM_MONTH}", "$expand": "Trader"})
    rows = []
    while url:
        d = get(url)
        for r in d.get("value", []):
            t = r.get("Trader") or {}
            town = next((t.get(k) for k in ("Address4", "Address3", "Address2") if t.get(k)), "")
            rows.append([r["TraderId"], r["MonthId"], (t.get("CompanyName") or "").strip(), town.strip(), (t.get("PostCode") or "").strip()])
        url = d.get("@odata.nextLink")
    cache.write_text(json.dumps(rows))
    return rows


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    traders, per_hs6 = {}, defaultdict(lambda: defaultdict(lambda: {"months": set(), "codes": set()}))
    last_month = 0
    for ch in CHAPTERS:
        codes = cn8_codes(ch)
        print(f"chapter {ch}: {len(codes)} CN8 codes", flush=True)
        for i, cn8 in enumerate(codes):
            rows = imports(cn8)
            for tid, month, name, town, pc in rows:
                traders[tid] = (name, town, pc)
                e = per_hs6[cn8[:6]][tid]
                e["months"].add(month); e["codes"].add(cn8)
                last_month = max(last_month, month)
            if i % 10 == 0:
                print(f"  {ch}: {i + 1}/{len(codes)} codes, {sum(len(v) for v in per_hs6.values())} importer-product pairs", flush=True)

    hs6_by_trader = defaultdict(set)
    for hs6, by_trader in per_hs6.items():
        for tid in by_trader:
            hs6_by_trader[tid].add(hs6)
    shared = {pc for pc, n in Counter(pc for _, _, pc in traders.values() if pc).items() if n > SHARED_POSTCODE}
    out, dropped = {}, 0
    for hs6, by_trader in per_hs6.items():
        rows = []
        for tid, e in by_trader.items():
            name, town, pc = traders[tid]
            seg = classify(name)
            if seg is None or pc in shared:
                dropped += 1
                continue
            related = sum(1 for h in hs6_by_trader[tid] if h[:2] == hs6[:2] and h != hs6)
            rows.append([name, town.title(), pc, seg, len(e["months"]), max(e["months"]), related])
        recent = last_month - 2
        rows.sort(key=lambda r: (-SEGMENT_RANK[r[3]], -(r[4] + (6 if r[5] >= recent else 0)), -min(r[6], 15), r[0]))
        if rows:
            out[hs6] = rows[:MAX_PER_CODE] + ([["+", len(rows) - MAX_PER_CODE]] if len(rows) > MAX_PER_CODE else [])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"months": [FROM_MONTH, last_month], "chapters": CHAPTERS,
                               "source": "HMRC UK trade data (uktradeinfo.com), traders by commodity code",
                               "licence": "Contains HMRC data licensed under the Open Government Licence v3.0.",
                               "hs6": dict(sorted(out.items()))}, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"done: {len(out)} HS6 codes, {sum(len(v) for v in out.values())} rows kept, {dropped} removed, "
          f"{len(shared)} shared agent postcodes, data to {last_month}", flush=True)


if __name__ == "__main__":
    main()
