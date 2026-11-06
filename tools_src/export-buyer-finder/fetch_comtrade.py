"""Download trade values by HS6 from the UN Comtrade public preview API (no key) for the Export Buyer Finder.

Presets:
  us_imports     US imports by supplier country; trend for World + India      → data/us_imports/us_imports_hs6.json
  india_exports  India's exports by destination country; trend for World       → data/india_exports/india_exports_hs6.json

    python3 tools_src/export-buyer-finder/fetch_comtrade.py india_exports            # resumes from its cache
    python3 tools_src/export-buyer-finder/fetch_comtrade.py us_imports --latest 2026

The preview API allows 1 year and 500 rows per call and about 1 call a second, so a full run takes 45–75 minutes.
Re-run each preset once a year when the new year's data is out, then run build.py.

Output per HS6 code:
  w:   value with the world, USD, one value per year in YEARS (null = no data)
  i:   value with the focus partner (India for us_imports), same years; omitted when the preset has no focus
  top: [[partner code, USD], ...] the largest partners in the latest year (8 for us_imports, 10 for india_exports)
  n:   number of partner countries in the latest year
  r:   focus partner's rank in the latest year (us_imports only)
"""
import csv, json, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
API = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
WORLD = 0

PRESETS = {
    "us_imports": {"reporter": 842, "flow": "M", "focus": 699, "top": 8, "batch": 8,
                   "dir": "us_imports", "file": "us_imports_hs6.json",
                   "source": "UN Comtrade (public API), reporter: USA, flow: imports, value in USD"},
    "india_exports": {"reporter": 699, "flow": "X", "focus": None, "top": 10, "batch": 3,
                      "dir": "india_exports", "file": "india_exports_hs6.json",
                      "source": "UN Comtrade (public API), reporter: India, flow: exports, value in USD"},
}

PRESET = PRESETS[sys.argv[1]] if len(sys.argv) > 1 and sys.argv[1] in PRESETS else sys.exit("usage: fetch_comtrade.py us_imports|india_exports [--latest YEAR]")
LATEST = int(sys.argv[sys.argv.index("--latest") + 1]) if "--latest" in sys.argv else 2025
YEARS = list(range(LATEST - 4, LATEST + 1))
OUT_DIR = ROOT / "data" / PRESET["dir"]
CACHE = OUT_DIR / "_cache.json"
BASE = {"reporterCode": PRESET["reporter"], "flowCode": PRESET["flow"]}


def hs6_codes():
    with open(ROOT / "data" / "hsn" / "wco_hs.csv", encoding="utf-8-sig") as f:
        return sorted(r["hscode"] for r in csv.DictReader(f) if r["level"] == "6")


def get(params, tries=10):
    url = API + "?" + "&".join(f"{k}={v}" for k, v in {**BASE, **params}.items())
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


def plain(x):
    """Keep plain totals; skip partner2 / mode-of-transport / customs-procedure splits."""
    return x.get("partner2Code") in (0, None) and x.get("motCode") in (0, None) and x.get("customsCode") in ("C00", None)


def load_cache():
    return json.loads(CACHE.read_text()) if CACHE.exists() else {"latest": {}, "hist": {}}


def save_cache(c):
    CACHE.write_text(json.dumps(c, separators=(",", ":")))


def fetch_latest_all_partners(codes, cache):
    todo = [c for c in codes if c not in cache["latest"]]
    print(f"{LATEST} all partners: {len(todo)} codes to fetch", flush=True)

    def run(batch):
        d = get({"period": LATEST, "cmdCode": ",".join(batch)})
        rows = d.get("data") or []
        if len(rows) >= 500 and len(batch) > 1:
            mid = len(batch) // 2
            run(batch[:mid]); run(batch[mid:]); return
        got = {c: {} for c in batch}
        for x in rows:
            if plain(x):
                got.setdefault(x["cmdCode"], {})[str(x["partnerCode"])] = x.get("primaryValue")
        cache["latest"].update(got)

    B = PRESET["batch"]
    for i in range(0, len(todo), B):
        run(todo[i:i + B])
        if (i // B) % 10 == 0:
            save_cache(cache)
            print(f"  {i + B}/{len(todo)}", flush=True)
    save_cache(cache)


def fetch_history(codes, cache):
    partners = [WORLD] + ([PRESET["focus"]] if PRESET["focus"] else [])
    # The preview API quietly answers only part of a very long cmdCode list (480 codes gave ~55%), so keep it short.
    per_call = min(200, 480 // len(partners))
    for y in YEARS[:-1]:
        have = cache["hist"].setdefault(str(y), {})
        todo = [c for c in codes if c not in have]
        print(f"{y} history: {len(todo)} codes", flush=True)
        def run(batch):
            d = get({"period": y, "cmdCode": ",".join(batch), "partnerCode": ",".join(map(str, partners))})
            rows = d.get("data") or []
            if len(rows) >= 500 and len(batch) > 1:  # hit the preview cap: rows were cut off, so split
                mid = len(batch) // 2
                run(batch[:mid]); run(batch[mid:]); return
            for c in batch:
                have.setdefault(c, {})
            for x in rows:
                if plain(x):
                    have.setdefault(x["cmdCode"], {})[str(x["partnerCode"])] = x.get("primaryValue")

        for i in range(0, len(todo), per_call):
            run(todo[i:i + per_call])
            save_cache(cache)


def assemble(codes, cache):
    focus = PRESET["focus"]
    out = {}
    for c in codes:
        latest = cache["latest"].get(c, {})
        partners = sorted(((int(p), v) for p, v in latest.items() if int(p) != WORLD and v), key=lambda t: -t[1])
        w, i = [], []
        for y in YEARS:
            src = latest if y == LATEST else cache["hist"].get(str(y), {}).get(c, {})
            w.append(round(src[str(WORLD)]) if src.get(str(WORLD)) else None)
            if focus:
                i.append(round(src[str(focus)]) if src.get(str(focus)) else None)
        if not any(w):
            continue
        row = {"w": w, "top": [[p, round(v)] for p, v in partners[:PRESET["top"]]], "n": len(partners)}
        if focus:
            row["i"] = i
            row["r"] = next((k + 1 for k, (p, _) in enumerate(partners) if p == focus), None)
        out[c] = row
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
    fetch_history(codes, cache)
    data = assemble(codes, cache)
    used = {str(p) for v in data.values() for p, _ in v["top"]} | ({str(PRESET["focus"])} if PRESET["focus"] else set())
    names = {k: v for k, v in partner_names().items() if k in used}
    result = {"source": PRESET["source"], "years": YEARS, "fetched": time.strftime("%Y-%m-%d"), "partners": names, "hs6": data}
    (OUT_DIR / PRESET["file"]).write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
    print(f"done: {len(data)} HS6 codes", flush=True)
