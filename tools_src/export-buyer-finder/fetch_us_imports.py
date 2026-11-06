"""Download US import values by HS6 from UN Comtrade (public preview API, no key) into
data/us_imports/us_imports_hs6.json. Run once a year after the new year's data lands (US annual data
usually appears by mid-year).

    python3 tools_src/export-buyer-finder/fetch_us_imports.py            # resumes from cache
    python3 tools_src/export-buyer-finder/fetch_us_imports.py --latest 2025

Output per HS6 code:
  w:   US imports from the world, USD, one value per year in YEARS (null = no data)
  i:   US imports from India, same years
  top: [[partner code, USD], ...] the 8 largest suppliers in the latest year
  n:   number of supplier countries in the latest year
  r:   India's rank among suppliers in the latest year (null = India didn't ship)
Values are Comtrade "primaryValue" (US reports imports at CIF value).
"""
import csv, json, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "data" / "us_imports"
CACHE = OUT_DIR / "_cache.json"
API = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
US, INDIA, WORLD = 842, 699, 0

LATEST = int(sys.argv[sys.argv.index("--latest") + 1]) if "--latest" in sys.argv else 2025
YEARS = list(range(LATEST - 4, LATEST + 1))


def hs6_codes():
    with open(ROOT / "data" / "hsn" / "wco_hs.csv", encoding="utf-8-sig") as f:
        return sorted(r["hscode"] for r in csv.DictReader(f) if r["level"] == "6")


def get(params, tries=8):
    url = API + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    for t in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                d = json.loads(r.read().decode())
            time.sleep(1.6)
            return d
        except urllib.error.HTTPError as e:
            wait = 5 * (t + 1) if e.code == 429 else 3 * (t + 1)
            print(f"  HTTP {e.code}, retry in {wait}s", flush=True)
            time.sleep(wait)
        except Exception as e:  # network blip
            print(f"  {e}, retry", flush=True)
            time.sleep(5 * (t + 1))
    raise RuntimeError("gave up on " + url)


def load_cache():
    return json.loads(CACHE.read_text()) if CACHE.exists() else {"latest": {}, "wi": {}}


def save_cache(c):
    CACHE.write_text(json.dumps(c, separators=(",", ":")))


def fetch_latest_all_partners(codes, cache):
    """Latest year, every partner, a few codes per call; split a batch if it hits the 500-row cap."""
    todo = [c for c in codes if c not in cache["latest"]]
    print(f"{LATEST} all partners: {len(todo)} codes to fetch", flush=True)

    def run(batch):
        d = get({"reporterCode": US, "flowCode": "M", "period": LATEST, "cmdCode": ",".join(batch)})
        rows = d.get("data") or []
        if len(rows) >= 500 and len(batch) > 1:
            mid = len(batch) // 2
            run(batch[:mid]); run(batch[mid:]); return
        got = {c: {} for c in batch}
        for x in rows:
            # Skip partner2/mode-of-transport splits if any; keep plain totals.
            if x.get("partner2Code") not in (0, None) or x.get("motCode") not in (0, None) or x.get("customsCode") not in ("C00", None):
                continue
            got.setdefault(x["cmdCode"], {})[str(x["partnerCode"])] = x.get("primaryValue")
        cache["latest"].update(got)

    B = 8
    for i in range(0, len(todo), B):
        run(todo[i:i + B])
        if (i // B) % 10 == 0:
            save_cache(cache)
            print(f"  {i + B}/{len(todo)}", flush=True)
    save_cache(cache)


def fetch_world_india_history(codes, cache):
    for y in YEARS[:-1]:
        key = str(y)
        have = cache["wi"].setdefault(key, {})
        todo = [c for c in codes if c not in have]
        print(f"{y} world+India: {len(todo)} codes", flush=True)
        for i in range(0, len(todo), 240):
            batch = todo[i:i + 240]
            d = get({"reporterCode": US, "flowCode": "M", "period": y, "cmdCode": ",".join(batch),
                     "partnerCode": f"{WORLD},{INDIA}"})
            for c in batch:
                have.setdefault(c, {})
            for x in d.get("data") or []:
                if x.get("partner2Code") not in (0, None) or x.get("motCode") not in (0, None):
                    continue
                have.setdefault(x["cmdCode"], {})[str(x["partnerCode"])] = x.get("primaryValue")
            save_cache(cache)


def assemble(codes, cache):
    out = {}
    for c in codes:
        latest = cache["latest"].get(c, {})
        partners = sorted(((int(p), v) for p, v in latest.items() if int(p) != WORLD and v),
                          key=lambda t: -t[1])
        w, i = [], []
        for y in YEARS:
            src = latest if y == LATEST else cache["wi"].get(str(y), {}).get(c, {})
            w.append(round(src[str(WORLD)]) if src.get(str(WORLD)) else None)
            i.append(round(src[str(INDIA)]) if src.get(str(INDIA)) else None)
        if not any(w):
            continue
        rank = next((k + 1 for k, (p, _) in enumerate(partners) if p == INDIA), None)
        out[c] = {"w": w, "i": i, "top": [[p, round(v)] for p, v in partners[:8]], "n": len(partners), "r": rank}
    return out


def partner_names():
    with urllib.request.urlopen("https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json", timeout=60) as r:
        d = json.loads(r.read().decode())
    return {str(x["id"]): x["text"] for x in d["results"]}


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    codes = hs6_codes()
    cache = load_cache()
    fetch_latest_all_partners(codes, cache)
    fetch_world_india_history(codes, cache)
    data = assemble(codes, cache)
    used = {str(p) for v in data.values() for p, _ in v["top"]} | {str(INDIA)}
    names = {k: v for k, v in partner_names().items() if k in used}
    result = {"source": "UN Comtrade (public API), reporter: USA, flow: imports, value in USD",
              "years": YEARS, "fetched": time.strftime("%Y-%m-%d"), "partners": names, "hs6": data}
    (OUT_DIR / "us_imports_hs6.json").write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
    print(f"done: {len(data)} HS6 codes with US import data", flush=True)
