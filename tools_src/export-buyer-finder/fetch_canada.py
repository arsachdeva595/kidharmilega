"""Canadian companies importing from India, by HS6 code, from the Canadian Importers Database (ISED, open data).

    python3 tools_src/export-buyer-finder/fetch_canada.py            # latest year below
    python3 tools_src/export-buyer-finder/fetch_canada.py --year 2025

Downloads "Major Importers by HS6, country" (binary Excel, ~22 MB), converts it to CSV with LibreOffice (Python
Excel readers drop its text cells), keeps the rows where the source country is India, removes couriers and
brokers, tags segments, and writes data/canada_importers/canada_india_hs6.json:

  {"year": 2024, "hs6": {"482010": [[name, city, province, segment, outside_canada, related], ...]}}

related = how many other HS6 codes in the same chapter the company also imports from India (a proxy for being a
real buyer of the category: the file has no values or shipment counts). Rows are sorted best first.
Licence: Open Government Licence – Canada.
"""
import csv, json, shutil, subprocess, sys, tempfile, urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from segments import classify, SEGMENT_RANK  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "data" / "canada_importers" / "canada_india_hs6.json"
YEAR = int(sys.argv[sys.argv.index("--year") + 1]) if "--year" in sys.argv else 2024
URL = f"https://ised-isde.canada.ca/site/ised/sites/default/files/documents/cid-bdic-majorimportersbyhs6bycountry{YEAR}.xls"

PROVINCES = {"Alberta": "AB", "British Columbia": "BC", "Manitoba": "MB", "New Brunswick": "NB",
             "Newfoundland and Labrador": "NL", "Nova Scotia": "NS", "Northwest Territories": "NT", "Nunavut": "NU",
             "Ontario": "ON", "Prince Edward Island": "PE", "Quebec": "QC", "Saskatchewan": "SK", "Yukon": "YT"}


def to_csv(work):
    xlsb = work / "hs6country.xlsb"  # the .xls URL is really Excel binary; the extension lets LibreOffice pick the filter
    print("downloading", URL, flush=True)
    with urllib.request.urlopen(URL, timeout=600) as r, open(xlsb, "wb") as f:
        shutil.copyfileobj(r, f)
    office = shutil.which("soffice") or shutil.which("libreoffice")
    if not office:
        sys.exit("LibreOffice (soffice) is needed to read the Canadian Excel file")
    subprocess.run([office, "--headless", "--convert-to", "csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,false,false,false,-1",
                    "--outdir", str(work), str(xlsb)], check=True, capture_output=True, timeout=1200)
    out = [p for p in work.glob("*.csv")]
    if not out:
        sys.exit("conversion produced no CSV")
    return out[0]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        path = to_csv(Path(tmp))
        with open(path, encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r["COUNTRY"] == "India"]
    print(f"{len(rows)} rows with India as source country", flush=True)

    by_company = defaultdict(set)
    for r in rows:
        by_company[r["COMPANY-ENTREPRISE"].strip()].add(r["HS6-SH6"].strip())

    hs6 = defaultdict(list)
    dropped = 0
    for r in rows:
        name, code = r["COMPANY-ENTREPRISE"].strip(), r["HS6-SH6"].strip().zfill(6)
        seg = classify(name)
        if seg is None:
            dropped += 1
            continue
        prov_name = r["PROVINCE_ENG"].strip()
        prov = PROVINCES.get(prov_name, prov_name)
        outside = 0 if prov_name in PROVINCES else 1
        related = sum(1 for c in by_company[name] if c[:2] == code[:2] and c != code)
        hs6[code].append([name, r["CITY-VILLE"].strip(), prov, seg, outside, related])

    for code, lst in hs6.items():
        seen, uniq = set(), []
        for x in lst:
            if x[0] not in seen:
                seen.add(x[0]); uniq.append(x)
        uniq.sort(key=lambda x: (-SEGMENT_RANK[x[3]], x[4], -min(x[5], 10), x[0]))
        hs6[code] = uniq

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"year": YEAR, "source": "Canadian Importers Database, Innovation, Science and Economic Development Canada",
                               "licence": "Contains information licensed under the Open Government Licence – Canada.",
                               "hs6": dict(sorted(hs6.items()))}, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"done: {sum(len(v) for v in hs6.values())} importer rows across {len(hs6)} HS6 codes; {dropped} courier/broker rows removed")


if __name__ == "__main__":
    main()
