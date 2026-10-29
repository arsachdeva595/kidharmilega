# buyer_finder/

Personal export-lead tool: HSN code in, scored list of US buyers out, each backed by a customs record.
Built from the Export Buyer Finder PRD, cut down to the engine — no signup, credits or payments, since
this is for my own outreach. It is not part of the site: `build.py` never reads it, and everything it
stores lives in `data/buyer_finder/`, which is gitignored.

## Data rule

The tool does **not** scrape ImportYeti or any trade-data site. ImportYeti's terms allow personal,
non-commercial use but forbid automated scraping, so shipment records come in as CSV files collected
by hand (a vendor export, a licensed download, or rows copied from a page you opened yourself).
The `next` command tells you which company pages are worth opening next.

Contact enrichment only fetches the buyer's own website (home, contact, about, wholesale pages),
respects `robots.txt`, waits 1 second between requests, and keeps public business contacts only.

## Flow

```bash
# 1. HSN mapper (F2): code and/or description -> editable profile
python3 -m buyer_finder map 48201000 --desc "leather journal" --name journals
#    edit data/buyer_finder/profiles/journals.json: hs_prefixes, alternates, keywords, negative_keywords, seeds

# 2. Load shipment CSVs (columns are matched loosely: date, shipper, consignee, address, description, HS code, BOL...)
python3 -m buyer_finder import ~/Downloads/journal-shipments/*.csv --source importyeti-manual
python3 -m buyer_finder import sample-exporter.csv --looked-up-exporter "Sample Leather Crafts Pvt Ltd"

# 3. Buyer search (F3): seeds -> 2-hop snowball -> cleanup -> tagging -> scoring v2
python3 -m buyer_finder search journals
python3 -m buyer_finder show journals "Maple Lane"

# 4. Grow the data by hand: who to look up next
python3 -m buyer_finder next journals
python3 -m buyer_finder done --exporter "Demo Exports India"      # after importing their customer list

# 5. Contacts: website lookup (needs `pip install ddgs`) + public emails/phones/socials
python3 -m buyer_finder enrich journals --top 20
python3 -m buyer_finder contact journals "Maple Lane" --website https://... --email sales@... --decision-maker "Name, Buyer"

# 6. Export (F7) and monthly re-check (F8)
python3 -m buyer_finder export journals --xlsx      # data/buyer_finder/exports/journals-YYYY-MM-DD.xlsx
python3 -m buyer_finder recheck journals            # new buyers and new shipments since the last run
```

Try it on the fictional sample first: `python3 -m buyer_finder import buyer_finder/sample/shipments_sample.csv`.
Set `BUYER_FINDER_DATA=/some/dir` to keep a test store separate from the real one.

## Web app (phone access)

`buyer_finder/web/` is a private, single-login web version of the same flow: searches, buyer cards with proof
and contacts, CSV upload, "look up next", contact finding, XLSX/CSV export and re-check. It runs on your VPS
behind HTTPS; see [`web/DEPLOY.md`](web/DEPLOY.md).

## How a lead is built

| Step | What happens |
|---|---|
| Match | A shipment line has **product** proof if it names a keyword, **hs** proof if only the HS code matches the profile's prefixes or alternates. Negative keywords veto both. Only India → US records count. |
| Seeds | Profile `seeds` if set, else every Indian shipper with a matching line. |
| Snowball | Seeds' buyers (hop 1) → those buyers' other Indian suppliers → their matching buyers (hop 2). |
| Cleanup | Consignees at the same street number + street + ZIP are merged; forwarders, customs brokers, Amazon/FBA intake, 3PLs, consultancies and "to order" consignees are dropped. |
| Tagging | Styles from the matching lines (leather, canvas, deckle, block print...) and a rule-based pitch angle. |
| Score | Proof 35 (product) or 22 (HS only), recency 15, repeat buying 15, fit (matching share of their India shipments) 15, reach 10 (website 4, email 4, phone 2), market 10. Outreach now at 80+, nurture 60–79, watch below, stale if the last match is over 36 months old. |
| Status | `verified` = matching record in the last 36 months and a website or email. |

The HSN mapper uses Claude (`ANTHROPIC_API_KEY`, model override `BUYER_FINDER_MODEL`) to propose HS6/HTS
codes and keywords; without a key it falls back to the description and a small alternates table.

## Files

```
buyer_finder/
├── __main__.py   CLI
├── hsn.py        F2 mapper and profiles
├── store.py      SQLite store and CSV import
├── engine.py     snowball, cleanup, tagging, scoring
├── enrich.py     website lookup and contact scraping
├── export.py     CSV / XLSX
├── web/          Flask app, templates, Dockerfile, Caddy, DEPLOY.md
└── sample/shipments_sample.csv   fictional test data
data/buyer_finder/  (gitignored) buyer_finder.db, profiles/, exports/
```
