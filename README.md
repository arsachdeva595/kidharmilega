# KidharMilega — Static Site

India's Small Business Discovery Platform  
Built by @startupwalebhaiya

---

## How this works

```
Your Google Sheets  →  Run build.py  →  Push dist/ to GitHub  →  Live on GitHub Pages
```

You never touch HTML. You update your spreadsheet, run one command, and the site updates.

---

## Folder structure

```
kidharmilega/
├── build.py          ← The build script (run this to regenerate all pages)
├── data/
│   ├── districts.csv ← Your district data (or connects to Google Sheets)
│   └── vendors.csv   ← Your vendor data (or connects to Google Sheets)
└── dist/             ← Generated site (push this folder to GitHub Pages)
    ├── index.html
    ├── master.html
    ├── assets/style.css
    ├── odop/index.html
    ├── events/index.html
    ├── vendors/index.html
    └── districts/
        ├── varanasi/index.html
        ├── lucknow/index.html
        └── ...
```

---

## Setup: One-time

### 1. Install Python (if not already)
Download from python.org — version 3.8 or higher.

### 2. Create a GitHub repository
- Go to github.com → New repository
- Name it: `kidharmilega` (or your preferred name)
- Set to Public (required for free GitHub Pages)

### 3. Enable GitHub Pages
- Go to your repo → Settings → Pages
- Source: Deploy from a branch
- Branch: `main` → folder: `/dist`
- Click Save

### 4. Add custom domain (optional)
- In GitHub Pages settings, add `kidharmilega.in`
- Uncomment the CNAME line in build.py
- Add a CNAME record in your domain DNS: `kidharmilega.in → yourusername.github.io`

---

## Connect to Google Sheets

### Step 1: Prepare your Google Sheets
Your sheets need these columns (matching the CSV headers exactly):
- **Districts sheet**: district_id, state, district_name, url_slug, odop_product_name... (see data/districts.csv for all columns)
- **Vendors sheet**: vendor_id, vendor_name, category, district_slug... (see data/vendors.csv)

### Step 2: Publish your sheets as CSV
1. Open your Google Sheet
2. File → Share → Publish to web
3. Select the specific sheet tab
4. Change format to **CSV**
5. Click Publish
6. Copy the URL — it looks like:
   `https://docs.google.com/spreadsheets/d/SHEET_ID/pub?gid=0&single=true&output=csv`

### Step 3: Add URLs to build.py
Open `build.py` and replace these two lines near the top:

```python
CSV_URL_DISTRICTS = "YOUR_GOOGLE_SHEET_CSV_URL_HERE"
CSV_URL_VENDORS   = "YOUR_VENDORS_SHEET_CSV_URL_HERE"
```

With your actual URLs:
```python
CSV_URL_DISTRICTS = "https://docs.google.com/spreadsheets/d/abc123/pub?gid=0&single=true&output=csv"
CSV_URL_VENDORS   = "https://docs.google.com/spreadsheets/d/xyz789/pub?gid=0&single=true&output=csv"
```

---

## Build and deploy

### Build locally (using local CSV files)
```bash
python build.py
```

### Build from Google Sheets (live data)
```bash
python build.py --live
```

### Preview locally before pushing
```bash
cd dist
python -m http.server 8000
# Open http://localhost:8000 in your browser
```

### Deploy to GitHub Pages
```bash
cd dist
git init
git add .
git commit -m "Update site"
git branch -M main
git remote add origin https://github.com/YOURUSERNAME/kidharmilega.git
git push -f origin main
```

**After the first deploy**, just run these three commands every time you update your sheet:
```bash
python build.py --live
cd dist && git add . && git commit -m "Update" && git push
```

---

## Adding new districts

1. Add a new row to your Google Sheet (or districts.csv)
2. Fill all columns — especially `url_slug` (no spaces, lowercase, hyphens only)
3. Set `page_status` = `Live`
4. Run `python build.py --live`
5. Push to GitHub

The new district page appears automatically at `/districts/your-slug/`

---

## Adding AllEvents widget

1. Get your embed code from AllEvents
2. Open `build.py`
3. Find the function `build_events_page()`
4. Replace the `events-placeholder` div with your embed code
5. Rebuild and push

For district-level event filtering, also find `build_district_page()` and replace the events section placeholder.

---

## Adding/updating vendors

1. Add a row to your vendors Google Sheet
2. Set `district_slug` to match the district's `url_slug` exactly (e.g., `varanasi`)
3. Set `listing_type` to `premium` for highlighted listings
4. Rebuild and push

---

## Page status field

In your districts sheet, the `page_status` column controls which pages are built:
- `Live` → page is generated and linked from homepage
- `Draft` → page is NOT generated (safe to work on)
- `Review` → page is NOT generated
- `Ready` → page is NOT generated until you change to Live

---

## Column reference

### Key columns in districts.csv

| Column | What it does |
|--------|-------------|
| url_slug | URL path: `/districts/varanasi/` — no spaces, lowercase |
| page_status | `Live` to publish, anything else = draft |
| tier_priority | 1/2/3 — used for filtering |
| odop_gi_tag | `Yes` shows GI badge on the page |
| step_1_learn through step_6_scale | The how-to guide steps |
| brand_name_idea_1 through _5 | Brand name suggestions |
| marketing_idea_1 through _3 | Marketing tactics |
| relevant_central_scheme_1, _2 | Central govt schemes |
| relevant_state_scheme_1, _2 | State govt schemes |

---

## Questions?

DM @startupwalebhaiya on Instagram.
