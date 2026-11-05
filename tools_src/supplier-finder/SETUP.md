# Supplier Finder: setup

Live page: `/tools/supplier-finder/` (built by `supplier_finder.py`, called from `build.py`).

## 1. Connect the Google Sheet (about 5 minutes, one time)

1. Create a new Google Sheet, e.g. "KidharMilega – Supplier Finder leads".
2. **Extensions → Apps Script**. Delete the sample code and paste all of `apps-script.gs`. Save.
3. **Deploy → New deployment** → gear icon → **Web app**.
   - Description: `Supplier Finder leads`
   - Execute as: **Me**
   - Who has access: **Anyone**
4. Click **Deploy**, allow the permissions, and copy the **Web app URL**. It ends in `/exec`.
5. Paste it into `LEAD_ENDPOINT` at the top of `supplier_finder.py`, then run `python3 build.py` and push.

Test it by opening the tool, entering an email, and checking that a row appears in the `Leads` tab.
The first row is created automatically with the headers.

**If you edit the script later**, use Deploy → Manage deployments → edit (pencil) → Version: *New version*.
That keeps the same URL. A *new deployment* gives a new URL, which you'd have to paste again.

### What gets logged

One row per event:
- `lead`: the first time someone enters their email.
- `search`: each later search by the same browser, which shows what people are sourcing.

Columns: timestamp, event, email, phone (optional), hsn, hsn_name, product (the user's own wording),
state, district, utm_source/medium/campaign, referrer, page.

Add `?utm_source=instagram&utm_campaign=supplier-reel` to the link you share, and it lands in the sheet.

## 2. Other settings (`supplier_finder.py`)

- `BOOK_CALL_URL`: the "Book a call" button. Currently `https://topmate.io/arsachdeva`. Swap it for the dedicated product link when that exists.
- `PROMPTS`: the prompt texts. Placeholders: `{product}` `{hsn}` `{hsnName}` `{district}` `{state}` `{place}`.
- `GENERAL_CHECKS`, `RED_FLAGS`, `CATEGORY_CHECKS`: the audit checklist. Category packs are picked by HSN chapter (`ch`) or heading (`heads`).
- `ODOP_RULES`: maps ODOP product names to HSN headings, for the "ODOP districts known for this product" suggestions.

## 3. Deep links

`/tools/supplier-finder/?hsn=63022110&state=Haryana&district=Panipat` opens with the code and place filled in.
Phase 2 (one SEO page per 4-digit HSN heading) will link to the tool this way.

## Data

See `data/hsn/SOURCES.md`. `hsn_compile.py` merges the CBIC 8-digit list with WCO names into `hsn.json`.
