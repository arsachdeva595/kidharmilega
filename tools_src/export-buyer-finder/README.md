# Export Buyer Finder (free tool)

Live page: `/tools/export-buyer-finder/` (built by `export_buyer_finder.py`, called from `build.py`).

**What it does now (free, no signup):** the user picks an Indian HSN code. The page shows the US import market for its
HS6 code: total US imports, imports from India, India's share and rank, India's 5-year trend, and the top 8 supplier
countries. Below that is a locked sample buyer lead and a waitlist form (email, optional WhatsApp, exporter type).

**What's coming (see the PRD):** the verified US buyer list from customs records, 3 free leads, then credits.

## Page sections (in order)

1. **Where India sells this:** India's exports by destination (top 10), trend, top buyer country. `fetch_comtrade.py india_exports`
2. **Canadian companies importing this from India:** named importers, top 10 free, full list after joining. `fetch_canada.py`
3. **The US market in detail:** US imports, India's share, rank and competitors. `fetch_comtrade.py us_imports`
4. Waitlist for the paid US buyer list.

Coming next: UK importers from HMRC trader data (launch chapters 42, 48, 63, 71, 68, 44), refreshed monthly.

## Canadian importers

`fetch_canada.py` downloads the Canadian Importers Database file "Major Importers by HS6, country" (yearly, latest
2024), converts it with LibreOffice, keeps rows where the source country is India and writes
`data/canada_importers/canada_india_hs6.json`. Run it once a year with `--year`. `segments.py` removes couriers and
brokers and tags big chains and luxury brands (shared with the UK list). The list shows who imported, not how much.

## Trade data

`fetch_comtrade.py` (presets `us_imports`, `india_exports`) downloads US-reported imports by HS6 from the UN Comtrade public API (no key needed):
- latest year: every supplier country (top 8 kept, plus India's rank and the supplier count)
- the 4 years before: world total and India only

It writes `data/us_imports/us_imports_hs6.json`. `_cache.json` next to it makes the script resumable. A full run takes
about 45 minutes because of the API rate limit. Re-run it once a year when the new year's US data is out:

    python3 tools_src/export-buyer-finder/fetch_us_imports.py --latest 2026
    python3 build.py

`build.py` splits the data into one file per HS chapter (`docs/tools/export-buyer-finder/us/<chapter>.json`), so a
visitor downloads only the chapter they look up.

If an Indian 8-digit code has no exact US HS6 match, the page sums the 4-digit heading instead and says so.

## Leads

Same Google Sheet and `LEAD_ENDPOINT` as the Supplier Finder (`supplier_finder.py`). Events:
`export_waitlist` (joined the waitlist) and `export_search` (later lookups by someone already on the list).
The `segment` column holds the exporter type. Redeploy the Apps Script after pasting the updated
`tools_src/supplier-finder/apps-script.gs`, which adds that column.
