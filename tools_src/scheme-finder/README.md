# Scheme Finder (free tool)

Live page: `/tools/scheme-finder/` (built by `scheme_finder.py`, called from `build.py`).

**What it does:** the user answers a short form (stage, sector, artisan or not, state, rural/urban, business type,
project cost, turnover, export status, registrations, age, gender, social category, disability, ex-serviceman),
leaves an email, and gets a report in the browser:

1. Summary tiles: schemes matched, biggest likely subsidy (one scheme, not a sum), the ₹20 lakh collateral-free rule
2. A personal action plan (Udyam, FSSAI, IEC, DPIIT, DPR, the top scheme, the bank loan, the DIC)
3. Matched schemes grouped as subsidies and grants / loans and guarantees / export / certification and marketing /
   announced-not-open, each with why it matches, a rupee estimate where the scheme pays cash, a status warning,
   rules, documents, how to apply and the official link
4. Rights every Udyam-registered MSE has (collateral-free loans, 45-day payment, tenders, TReDS, Jan Samarth)
5. A pointer to the state's industrial policy and DIC
6. Schemes the user doesn't match, with the reason
7. Download PDF (print), WhatsApp share, book a call

The rules run in the browser (`app.js`); nothing is computed on a server.

## Data (`scheme_finder.py`)

- `CENTRAL` and `STATE`: one dict per scheme. `rule` says who matches (keys documented above `CENTRAL`), `calc`
  gives the subsidy estimate, `status` is `open`, `check` (continuation or figures not confirmed) or `soon`
  (announced, not open). State entries default to `check`.
- Central wording reuses `scheme_facts.py` where it has checked text (PMEGP, Mudra, PMFME, Stand-Up, CGTMSE,
  PM Vishwakarma, SFURTI, Udyam).
- `RIGHTS`, `DOCS`, `STATE_PORTALS`, `CLASSIFICATION` (MSME limits from 1 April 2025).
- `REVIEWED`: shown in the report footer. Update it whenever you re-check the data.

**Re-check before relying on it:** state scheme figures (the headline amounts were written from published rules but
not each re-verified against the state portal), PMEGP continuation after 2025-26, PMFME after 30 September 2026,
Niryat Protsahan rates and cap, RoDTEP validity, and the official URLs (several Indian government sites could not be
reached from the build machine).

## Leads

Same Google Sheet and `LEAD_ENDPOINT` as the Supplier Finder. Events: `scheme_report` (first report, email given)
and `scheme_search` (later reports from the same browser). Columns used: `product` = sector, `state`,
`district` = rural/urban, `segment` = stage, `hsn_name` = number of matches, `details` = JSON of the profile and
matched scheme ids. `details` is a new column: paste the updated `apps-script.gs`, redeploy as a new version, and
add `details` to the header row of an existing sheet by hand.

## Deep links

`/tools/scheme-finder/?state=Bihar&sector=food` pre-selects the state and sector. Every district page's scheme
section links here with its state.
