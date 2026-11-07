# Expo Finder (free tool)

Live page: `/tools/expo-finder/` (built by `expo_finder.py`, called from `build.py`).

**What it does:** the user picks their city, what they make or sell, their goal (sell to visitors, find dealers,
meet export buyers, find suppliers, research) and how far they'll travel, ticks a few subsidy flags (Udyam, woman-owned,
SC/ST, artisan card, SHG, IEC), leaves an email, and gets a report in the browser:

1. Summary tiles: fairs that fit, the next one up, the stall-rent subsidy they can claim
2. Live upcoming events in their city (AllEvents widget, same as the city event pages) and a link to the
   KidharMilega city events page when one exists
3. Recurring fairs that fit: near them, worth the trip (only fairs made for their product), and government bazaars
   held in many cities. Each card: usual month and next likely month, venue and distance, who visits, a tip for
   getting a stall, an eligibility warning (artisan / SHG only), the official link and a "find this year's dates" search
4. Exhibition venues near them
5. Ways to get a cheaper stall: MSME PMS stall-rent reimbursement, state pavilions and ODOP cells, handicrafts and
   handloom support, National SC-ST Hub, export councils and MAI
6. A stall budget and break-even calculator (live, editable)
7. Four copy-paste AI prompts: find fairs in the next 6 months, vet an expo, message the organiser, plan the stall
8. Before / during / after checklist and the red flags of fake expos
9. Download PDF (print), WhatsApp share, book a call

Matching runs in the browser (`app.js`); nothing is computed on a server.

## Data (`expo_finder.py`)

- `FAIRS`: one dict per recurring fair. Keys are documented above the list. Months are the usual months, not dates;
  `next` holds an announced or reported next edition. `url` is empty when the official site could not be confirmed
  from the build machine (the card then shows only the search link).
- `VENUES`: name, city and approximate coordinates (used only for straight-line distance).
- `CITIES`: the city picker, with coordinates. `AE_CITY` maps picker names to the AllEvents city name.
- `SUPPORT`, `PROMPTS`, `CHECKLIST`, `RED_FLAGS`.
- `REVIEWED`: shown in the report footer. Update it whenever you re-check the data.

**Re-check before relying on it:** fair months (Bharat Tex, IIGF and Bharat Mobility have moved between editions),
the PMS reimbursement rates and the ₹30,000 cap (commonly published figures; confirm with the MSME-DFO), and URLs
left empty because several sites (mostly `.gov.in`) could not be reached from the build machine.

## Leads

Same Google Sheet and `LEAD_ENDPOINT` as the Supplier Finder. Events: `expo_report` (first report, email given)
and `expo_search` (later reports from the same browser). Columns used: `product` = sector, `state`,
`district` = city, `segment` = goal, `hsn_name` = number of fairs, `details` = JSON of the flags, travel and matched
fair ids.

## Deep links

`/tools/expo-finder/?city=Pune&sector=food&goal=sell` pre-selects the city, sector and goal. Every exhibition and
business-events city page links here with its city, and the `/events/` hub links here.
