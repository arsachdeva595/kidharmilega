"""Expo Finder tool (/tools/expo-finder/).

Free trade-fair and expo finder for small businesses. The user picks their city, what they sell and why they
want to go to a fair (sell to visitors, find dealers, meet export buyers, find suppliers, research), leaves an
email, and gets a report in the browser:
  - live upcoming events in their city (AllEvents widget, same as the city event pages) and a link to the
    KidharMilega city page when one exists
  - the big recurring trade fairs that fit their product and goal, sorted by distance and the next likely month,
    with venue, organiser, who visits, a tip for getting a stall, and the official link
  - exhibition venues near them
  - the government stall subsidy (MSME Procurement & Marketing Support) and other ways to get a cheap stall
  - a stall budget and break-even calculator
  - copy-paste AI prompts to find more fairs, vet an organiser, and plan the stall
  - a before / during / after checklist and the red flags of fake expos

Everything here is data plus one page builder; build.py calls write_expo_finder(). The page is static: matching runs
in the browser (tools_src/expo-finder/app.js), and the lead goes to the same Google Sheet as the other tools
(event = expo_report / expo_search).

Fair dates move. Every fair carries its usual month(s), not a date; the report tells people to confirm on the
official site. Where a next edition has been announced, `next` holds it with the word "announced" or "reported".
Update REVIEWED whenever you re-check the data.
"""
import json, shutil, hashlib
from pathlib import Path

import supplier_finder as sf

BASE_DIR = Path(__file__).parent
SRC_DIR = BASE_DIR / "tools_src" / "expo-finder"
TOOL_PATH = "/tools/expo-finder/"
REVIEWED = "November 2026"

# ── Form options ──────────────────────────────────────────────────────────────
SECTORS = [
    ("food", "Food, spices, snacks, beverages"),
    ("textile", "Textiles, garments, handloom, home furnishing"),
    ("craft", "Handicrafts, home décor, gifts"),
    ("jewel", "Jewellery, gems, fashion jewellery"),
    ("leather", "Leather, footwear, bags"),
    ("furniture", "Furniture, wood, interiors, building material"),
    ("engg", "Engineering, machinery, auto parts, tools"),
    ("electronics", "Electronics, electricals, solar"),
    ("agri", "Agri products, dairy, farm inputs, agri machinery"),
    ("pharma", "Pharma, ayurveda, chemicals"),
    ("consumer", "Consumer products (cosmetics, home care, FMCG)"),
    ("packaging", "Packaging, printing, plastics"),
    ("tech", "Tech, software, startup, services"),
    ("books", "Books, stationery, toys, kids"),
]
GOALS = [
    ("sell", "Sell directly to visitors (retail)"),
    ("trade", "Find dealers, distributors, bulk or corporate buyers"),
    ("export", "Meet export buyers"),
    ("source", "Find suppliers, raw material or machines (as a visitor)"),
    ("learn", "Just visit to study the market before starting"),
]
TRAVEL = [
    ("city", "Only in or near my city (about 60 km)"),
    ("region", "Up to a day's travel (about 600 km)"),
    ("india", "Anywhere in India, if the fair is worth it"),
]

# ── Venues ────────────────────────────────────────────────────────────────────
# key: (name, city, lat, lng, url). Coordinates are approximate; they're only used for distance.
VENUES = {
    "bharat-mandapam": ("Bharat Mandapam (Pragati Maidan)", "New Delhi", 28.6177, 77.2426, ""),
    "yashobhoomi": ("Yashobhoomi (IICC), Dwarka", "New Delhi", 28.5537, 77.0444, "https://www.yashobhoomi.com/"),
    "iem": ("India Expo Centre & Mart", "Greater Noida", 28.4601, 77.5108, ""),
    "dilli-haat": ("Dilli Haat, INA", "New Delhi", 28.5730, 77.2080, ""),
    "surajkund": ("Surajkund Mela Grounds", "Faridabad", 28.4840, 77.2840, ""),
    "nesco": ("Bombay Exhibition Centre (NESCO), Goregaon", "Mumbai", 19.1550, 72.8530, ""),
    "jio": ("Jio World Convention Centre, BKC", "Mumbai", 19.0640, 72.8655, ""),
    "cidco": ("CIDCO Exhibition Centre, Vashi", "Navi Mumbai", 19.0700, 73.0000, ""),
    "biec": ("Bangalore International Exhibition Centre (BIEC)", "Bengaluru", 13.0618, 77.4748, "https://www.biec.in/"),
    "palace": ("Palace Grounds", "Bengaluru", 12.9980, 77.5920, ""),
    "hitex": ("HITEX Exhibition Centre", "Hyderabad", 17.4706, 78.3727, "https://hitex.co.in/"),
    "nampally": ("Nampally Exhibition Grounds", "Hyderabad", 17.3888, 78.4676, ""),
    "ctc": ("Chennai Trade Centre, Nandambakkam", "Chennai", 13.0160, 80.1950, ""),
    "milan-mela": ("Biswa Bangla Mela Prangan (Milan Mela)", "Kolkata", 22.5150, 88.4130, ""),
    "boimela": ("Boimela Prangan, Central Park, Salt Lake", "Kolkata", 22.5790, 88.4220, ""),
    "mahatma-mandir": ("Mahatma Mandir Convention Centre", "Gandhinagar", 23.2290, 72.6470, ""),
    "helipad": ("Helipad Exhibition Centre", "Gandhinagar", 23.2260, 72.6420, ""),
    "piecc": ("PIECC, Moshi", "Pune", 18.6740, 73.8480, ""),
    "autocluster": ("Auto Cluster Exhibition Centre, Chinchwad", "Pune", 18.6460, 73.7900, ""),
    "jecc": ("Jaipur Exhibition & Convention Centre (JECC), Sitapura", "Jaipur", 26.7830, 75.8410, "https://www.jecc.co.in/"),
    "codissia": ("CODISSIA Trade Fair Complex", "Coimbatore", 11.0360, 77.0380, "https://www.codissia.com/"),
    "ikf": ("IKF Complex", "Tiruppur", 11.1510, 77.3430, ""),
    "gwalior": ("Gwalior Mela Ground", "Gwalior", 26.2280, 78.2050, ""),
    "mysuru": ("Dasara Exhibition Grounds", "Mysuru", 12.3020, 76.6600, ""),
    "lucknow": ("Venue announced each year", "Lucknow", 26.8467, 80.9462, ""),
    "amritsar": ("Ranjit Avenue grounds", "Amritsar", 31.6520, 74.8650, ""),
    "pune": ("Venue announced each year", "Pune", 18.5204, 73.8567, ""),
    "nagpur": ("Venue announced each year", "Nagpur", 21.1458, 79.0882, ""),
    "bhubaneswar": ("Venue announced each year", "Bhubaneswar", 20.2961, 85.8245, ""),
    "kolkata": ("Venue announced each year", "Kolkata", 22.5726, 88.3639, ""),
    "varanasi": ("Deendayal Hastkala Sankul (Trade Facilitation Centre)", "Varanasi", 25.3420, 82.9760, ""),
    "indore": ("Brilliant Convention Centre", "Indore", 22.7340, 75.8880, ""),
    "chandigarh": ("Parade Ground, Sector 17", "Chandigarh", 30.7410, 76.7870, ""),
    "guwahati": ("Assam Engineering Institute ground / city venues", "Guwahati", 26.1445, 91.7362, ""),
}

# ── Fairs ─────────────────────────────────────────────────────────────────────
# months: usual month(s), 1–12 ([] = dates vary, check the site). venue: VENUES key, or "" with city "Various".
# sectors: SECTORS keys, or ["*"] for general fairs that take most products.
# kind: "b2b" (trade visitors), "b2c" (public buys at the stall), "mixed" (trade days then public days).
# export: foreign buyers come in numbers. url: "" when the official site could not be confirmed (the report
# then gives a search link). next: an announced or reported next edition, with that word in it.
# only: "artisan" (needs a Pehchan card / weaver ID) or "shg" (self-help groups only).
FAIRS = [
    dict(id="iitf", name="India International Trade Fair (IITF)", venue="bharat-mandapam", months=[11],
         sectors=["*"], kind="mixed", export=False, org="ITPO (Ministry of Commerce)", url="https://indiatradefair.com/",
         who="India's biggest general fair. Business days first, then lakhs of public visitors. State pavilions show each state's products.",
         tip="Small units rarely book direct. Your state's industries department, ODOP cell or DIC books space in the state pavilion and the MSME Ministry runs an MSME pavilion; ask them by August."),
    dict(id="upits", name="UP International Trade Show (UPITS)", venue="iem", months=[9],
         sectors=["*"], kind="mixed", export=True, org="Government of Uttar Pradesh", url="https://upinternationaltradeshow.com/",
         who="UP's ODOP and MSME products in one place, with foreign buyers invited by the state. Strong for crafts, textiles, food and leather.",
         tip="UP units get stalls through the state (ODOP cell, DIC, UPEPC). Ask at your DIC in spring; slots go early."),
    dict(id="ihgf-spring", name="IHGF Delhi Fair (Spring)", venue="iem", months=[2, 3],
         sectors=["craft", "furniture", "textile", "jewel"], kind="b2b", export=True, org="EPCH (Export Promotion Council for Handicrafts)",
         url="https://www.ihgfdelhifair.in/", next="15–19 March 2027 (reported)",
         who="Asia's largest handicrafts and gifts fair. Thousands of overseas buyers and big Indian retailers come to place orders.",
         tip="Exhibitors must be EPCH members (needs IEC). Visiting as a trade buyer or newcomer to study the market is the cheaper first step."),
    dict(id="ihgf-autumn", name="IHGF Delhi Fair (Autumn)", venue="iem", months=[10],
         sectors=["craft", "furniture", "textile", "jewel"], kind="b2b", export=True, org="EPCH (Export Promotion Council for Handicrafts)",
         url="https://www.ihgfdelhifair.in/",
         who="Autumn edition of the IHGF: home, lifestyle, gifts, furniture and fashion jewellery for export buyers.",
         tip="Exhibitors must be EPCH members (needs IEC). Book through EPCH months ahead."),
    dict(id="aahar", name="AAHAR – International Food & Hospitality Fair", venue="bharat-mandapam", months=[3],
         sectors=["food", "packaging", "agri"], kind="b2b", export=True, org="ITPO", url="https://indiatradefair.com/",
         who="Food processors, hotel and restaurant buyers, distributors, food machinery and packaging suppliers.",
         tip="Good place to meet distributors and HoReCa buyers. Food machinery and packaging suppliers make it useful even as a visitor."),
    dict(id="wfi", name="World Food India", venue="bharat-mandapam", months=[9],
         sectors=["food", "agri", "packaging"], kind="b2b", export=True, org="Ministry of Food Processing Industries",
         url="https://worldfoodindia.gov.in/",
         who="Food processing companies, investors, foreign delegations, state governments and food tech suppliers.",
         tip="PMFME-supported units and SHGs sometimes get space in ministry or state pavilions. Ask your state's PMFME nodal agency."),
    dict(id="bharat-tex", name="Bharat Tex", venue="bharat-mandapam", months=[2, 7],
         sectors=["textile"], kind="b2b", export=True, org="Bharat Tex Trade Federation (textile export councils)",
         url="https://bharat-tex.com/",
         who="The whole textile chain, fibre to fashion, with global buyers. The 2026 edition ran in July and included the India International Garment Fair.",
         tip="The month has moved between editions. Join your textile export council (AEPC, HEPC, Texprocil…) to get stall offers."),
    dict(id="iigf", name="India International Garment Fair (IIGF)", venue="yashobhoomi", months=[1, 7],
         sectors=["textile"], kind="b2b", export=True, org="AEPC (Apparel Export Promotion Council)", url="https://www.aepcindia.com/",
         who="Garment exporters showing next season's collections to overseas buyers and buying houses.",
         tip="For garment makers who can handle export orders. AEPC membership needed to exhibit."),
    dict(id="iijs-premiere", name="IIJS Premiere (India International Jewellery Show)", venue="nesco", months=[8],
         sectors=["jewel"], kind="b2b", export=True, org="GJEPC", url="https://gjepc.org/",
         who="India's biggest jewellery trade show: retailers from across India and overseas buyers placing orders.",
         tip="Trade only. GJEPC members exhibit; jewellers can register as visitors to meet manufacturers and suppliers."),
    dict(id="iijs-signature", name="IIJS Signature", venue="jio", months=[1],
         sectors=["jewel"], kind="b2b", export=True, org="GJEPC", url="https://gjepc.org/",
         who="GJEPC's second jewellery trade show of the year, for retailers and buyers.",
         tip="Trade only. Check GJEPC for the exact venue and dates of the coming edition."),
    dict(id="jjs", name="Jaipur Jewellery Show (JJS)", venue="jecc", months=[12],
         sectors=["jewel"], kind="mixed", export=False, org="Jaipur Jewellery Show society", url="https://www.jaipurjewelleryshow.org/",
         who="Jewellery and gemstone buyers, retailers and the public.",
         tip="Good fit for coloured gemstones, silver and Jaipur-style jewellery."),
    dict(id="iilf", name="India International Leather Fair (IILF)", venue="ctc", months=[1, 2],
         sectors=["leather"], kind="b2b", export=True, org="Council for Leather Exports and ITPO", url="https://iilf.co.in/",
         who="Leather, footwear, components and machinery, with foreign and domestic buyers.",
         tip="Useful even as a visitor for finding finished-leather and component suppliers."),
    dict(id="imtex", name="IMTEX (machine tools)", venue="biec", months=[1],
         sectors=["engg"], kind="b2b", export=False, org="IMTMA", url="https://www.imtma.in/",
         who="Machine tools, cutting tools, automation and manufacturing tech. Buyers from auto, defence and general engineering.",
         tip="IMTEX and IMTEX Forming alternate years. Best as a visitor to compare machines before you buy."),
    dict(id="electronica", name="electronica India & productronica India", venue="biec", months=[9],
         sectors=["electronics", "engg"], kind="b2b", export=False, org="Messe München India", url="https://electronica-india.com/en/",
         who="Electronic components, PCB and EMS, manufacturing equipment.",
         tip="Check the site: some editions run in Greater Noida instead of Bengaluru."),
    dict(id="cphi", name="CPHI & PMEC India", venue="iem", months=[11],
         sectors=["pharma", "packaging"], kind="b2b", export=True, org="Informa Markets", url="https://www.cphi.com/india/",
         who="Pharma ingredients, contract manufacturing, pharma machinery and packaging.",
         tip="Third-party manufacturers and packaging suppliers make it useful for a new pharma or nutraceutical brand."),
    dict(id="bharat-mobility", name="Bharat Mobility Global Expo", venue="bharat-mandapam", months=[1, 2],
         sectors=["engg", "electronics"], kind="mixed", export=False, org="Ministry of Commerce with industry bodies",
         url="https://www.bharatmobilityexpo.com/",
         who="Vehicles, auto components, EV and batteries, tyres. Includes the Auto Expo and component shows across Delhi venues.",
         tip="Component makers: the auto-components show is where OEM buyers walk. Check which years it runs."),
    dict(id="acetech", name="ACETECH (architecture, building, interiors)", venue="nesco", months=[12],
         sectors=["furniture"], kind="mixed", export=False, org="ACETECH", url="https://www.acetech.co.in/",
         who="Architects, interior designers, builders and dealers looking for building material, fittings and furniture.",
         tip="Also runs in Delhi and Bengaluru in some years. Great for meeting architects who specify products."),
    dict(id="ikf", name="India International Knit Fair (IKF)", venue="ikf", months=[],
         sectors=["textile"], kind="b2b", export=True, org="IKF Association, Tiruppur", url="https://www.ikf.co.in/",
         who="Knitwear exporters from Tiruppur meeting overseas buyers and buying houses.",
         tip="Dates vary by edition. Check the site."),
    dict(id="kisan", name="KISAN Agri Show", venue="piecc", months=[12],
         sectors=["agri"], kind="mixed", export=False, org="KISAN Forum", url="https://www.kisan.in/",
         who="Lakhs of farmers, agri dealers and FPOs. Seeds, irrigation, machinery, inputs, dairy.",
         tip="Ideal if your buyer is a farmer or an agri dealer."),
    dict(id="agri-intex", name="Agri Intex", venue="codissia", months=[7],
         sectors=["agri"], kind="mixed", export=False, org="CODISSIA", url="https://www.codissia.com/",
         who="South India's farmers, dealers and agri machinery buyers.",
         tip="Good for farm machinery, irrigation and inputs aimed at Tamil Nadu and Kerala."),
    dict(id="agrovision", name="Agrovision", venue="nagpur", months=[11, 12],
         sectors=["agri"], kind="mixed", export=False, org="Agrovision Foundation", url="",
         who="Farmers and agri businesses from Vidarbha and central India.",
         tip="Confirm dates and venue on the organiser's announcement."),
    dict(id="numaish", name="Numaish (All India Industrial Exhibition)", venue="nampally", months=[1, 2],
         sectors=["*"], kind="b2c", export=False, org="Exhibition Society, Hyderabad", url="",
         who="About 45 days of huge public footfall. Families come to shop: clothes, crafts, home goods, food.",
         tip="One of the best retail fairs for small sellers. Apply to the Exhibition Society well before the season."),
    dict(id="surajkund", name="Surajkund International Crafts Mela", venue="surajkund", months=[2],
         sectors=["craft", "textile", "food"], kind="b2c", export=False, org="Haryana Tourism with central ministries",
         url="https://surajkundmela.co.in/",
         who="Lakhs of Delhi-NCR visitors buying crafts, handloom and regional food.",
         tip="Craft and handloom stalls go mostly to registered artisans (Pehchan card / weaver ID) through DC Handicrafts, DC Handlooms or state agencies."),
    dict(id="dilli-haat", name="Dilli Haat (INA) stalls", venue="dilli-haat", months=list(range(1, 13)), only="artisan",
         sectors=["craft", "textile", "food"], kind="b2c", export=False, org="Delhi Tourism with DC Handicrafts / Handlooms", url="",
         who="Daily crafts bazaar with tourists and Delhi shoppers. Stalls are given for about two weeks at a time.",
         tip="Stalls are allotted to registered artisans and weavers, usually through the Development Commissioner offices. Get your Pehchan card first."),
    dict(id="gwalior", name="Gwalior Trade Fair (Gwalior Mela)", venue="gwalior", months=[12, 1, 2],
         sectors=["*"], kind="b2c", export=False, org="Gwalior Vyapar Mela Pradhikaran (MP Govt)", url="",
         who="Weeks of public footfall from MP, UP and Rajasthan. Known for vehicle sales, also big for household goods.",
         tip="Shops are allotted by the Mela authority before the season. Ask early."),
    dict(id="mysuru-dasara", name="Mysuru Dasara Exhibition", venue="mysuru", months=[9, 10, 11, 12],
         sectors=["*"], kind="b2c", export=False, org="Karnataka Exhibition Authority", url="https://mysoredasara.gov.in/",
         who="Runs about three months from Dasara. Tourists and Karnataka families shop here.",
         tip="Long run, so plan stock and staff for weeks, not days."),
    dict(id="lucknow-mahotsav", name="Lucknow Mahotsav", venue="lucknow", months=[11, 12],
         sectors=["*"], kind="b2c", export=False, org="District administration, Lucknow", url="https://lucknowmahotsav.in/",
         who="City festival with crafts, food and shopping stalls and big evening crowds.",
         tip="Stalls are booked through the organising committee. Dates move each year."),
    dict(id="pitex", name="Punjab International Trade Expo (PITEX)", venue="amritsar", months=[12],
         sectors=["*"], kind="mixed", export=False, org="PHD Chamber of Commerce", url="https://www.pitex.in/",
         who="North India's big consumer and trade fair. Strong footfall from Punjab and nearby states.",
         tip="Good for home goods, phulkari and textiles, food, furniture."),
    dict(id="bhimthadi", name="Bhimthadi Jatra", venue="pune", months=[12],
         sectors=["food", "craft", "textile", "agri", "consumer"], kind="b2c", export=False, org="Agricultural Development Trust, Baramati",
         url="https://www.bhimthadijatra.com/",
         who="Pune shoppers buying from rural women's groups, SHGs and small producers.",
         tip="Best for women entrepreneurs, SHGs and farm-fresh or homemade food."),
    dict(id="toshali", name="Toshali National Crafts Mela", venue="bhubaneswar", months=[12, 1],
         sectors=["craft", "textile"], kind="b2c", export=False, org="Government of Odisha", url="",
         who="Artisans and weavers from across India selling to the public.",
         tip="Artisan stalls come through state handicraft and handloom agencies."),
    dict(id="hastashilpa", name="Hastashilpa Mela (West Bengal State Handicrafts Expo)", venue="kolkata", months=[11, 12],
         sectors=["craft", "textile"], kind="b2c", export=False, org="Government of West Bengal", url="",
         who="Kolkata shoppers buying Bengal's crafts and handloom.",
         tip="For West Bengal artisans, through the state MSME and textiles department."),
    dict(id="kbf", name="International Kolkata Book Fair", venue="boimela", months=[1, 2],
         sectors=["books"], kind="b2c", export=False, org="Publishers & Booksellers Guild", url="https://www.kolkatabookfair.net/",
         who="One of the world's largest book fairs by footfall.",
         tip="Publishers, stationery and kids' learning products."),
    dict(id="ndwbf", name="New Delhi World Book Fair", venue="bharat-mandapam", months=[1, 2],
         sectors=["books"], kind="mixed", export=False, org="National Book Trust", url="https://www.nbtindia.gov.in/",
         who="Publishers, distributors, schools and readers.",
         tip="Books, stationery, educational toys."),
    dict(id="bts", name="Bengaluru Tech Summit", venue="biec", months=[11],
         sectors=["tech", "electronics"], kind="b2b", export=False, org="Government of Karnataka", url="https://www.bengalurutechsummit.com/",
         who="Tech companies, startups, investors and government buyers.",
         tip="The startup zone usually has subsidised booths for early-stage startups."),
    dict(id="imc", name="India Mobile Congress", venue="yashobhoomi", months=[10],
         sectors=["tech", "electronics"], kind="b2b", export=False, org="DoT and COAI", url="https://www.indiamobilecongress.com/",
         who="Telecom, devices, electronics and deep-tech startups.",
         tip="Has a startup programme with booth space for selected startups."),
    dict(id="startup-mahakumbh", name="Startup Mahakumbh", venue="bharat-mandapam", months=[3, 4],
         sectors=["tech", "consumer", "food", "agri", "electronics", "pharma"], kind="b2b", export=False,
         org="Startup India with industry bodies", url="https://startupmahakumbh.org/",
         who="Startups, investors, incubators and corporates.",
         tip="DPIIT-recognised startups can apply for booths; fundraising and partnerships more than direct sales."),
    dict(id="saras", name="SARAS Aajeevika Mela", venue="", city="Various", months=[], only="shg",
         sectors=["food", "craft", "textile", "consumer", "agri"], kind="b2c", export=False,
         org="Ministry of Rural Development (DAY-NRLM) and state rural livelihood missions", url="",
         who="Rural women's self-help groups selling to city shoppers. Held in different cities through the year, including at IITF.",
         tip="Only for SHG members. Your block's NRLM / state livelihood mission staff nominate groups."),
    dict(id="handloom-expo", name="National Handloom Expo / Gandhi Shilp Bazaar", venue="", city="Various", months=[], only="artisan",
         sectors=["craft", "textile"], kind="b2c", export=False,
         org="DC Handlooms, DC Handicrafts and state agencies", url="",
         who="Government-run weavers' and artisans' bazaars in many cities, with stall rent and travel often supported.",
         tip="Needs a weaver ID or artisan Pehchan card. Ask your nearest Weavers' Service Centre or Handicrafts Service Centre."),
]

# ── Ways to get a cheaper stall ──────────────────────────────────────────────
SUPPORT = [
    dict(id="pms", name="MSME Procurement & Marketing Support (PMS) scheme",
         who="Micro and small units with Udyam, at domestic fairs approved under the scheme",
         benefit="Reimburses 80% of stall (space) rent, or 100% for women, SC/ST, North East, divyang and aspirational-district units, commonly capped at ₹30,000 per fair or the actual rent, whichever is lower. Travel support is also listed for some categories.",
         how="Check the approved fair list and apply through your nearest MSME Development & Facilitation Office (MSME-DFO) before the fair, then claim with the rent receipt and photos.",
         url="https://www.dcmsme.gov.in/", needs="udyam"),
    dict(id="state", name="State pavilions and ODOP cells",
         who="Units in that state, especially ODOP products",
         benefit="States book large spaces at IITF, UPITS and other fairs and give small units a stall at a low or subsidised rate.",
         how="Ask your District Industries Centre (DIC) or ODOP cell which fairs they're booking for this year. Go 3–4 months before the fair.",
         url="", needs=""),
    dict(id="artisan", name="Handicrafts and handloom marketing support",
         who="Artisans with a Pehchan card and weavers with a weaver ID",
         benefit="DC Handicrafts and DC Handlooms run and fund crafts bazaars, Gandhi Shilp Bazaars and handloom expos, often covering stall rent and some travel.",
         how="Register for the Pehchan card or weaver ID, then ask your Handicrafts or Weavers' Service Centre about upcoming events.",
         url="", needs="craft"),
    dict(id="sc-st-hub", name="National SC-ST Hub",
         who="SC and ST entrepreneurs with Udyam",
         benefit="Support for taking part in domestic and international fairs, on top of training and vendor development.",
         how="Contact the National SC-ST Hub office in your state (run through NSIC).",
         url="https://scsthub.in/", needs="scst"),
    dict(id="epc", name="Export promotion councils and MAI",
         who="Exporters with IEC and RCMC",
         benefit="Councils (EPCH, AEPC, GJEPC, CLE and others) book India pavilions and subsidise stalls for members, at home and abroad, under the Market Access Initiative.",
         how="Join the council for your product. Ask for their fair calendar and subsidy rules for new members.",
         url="", needs="export"),
]

# Cities for the picker: (name, state, lat, lng). Approximate centres; pick the nearest if yours isn't listed.
CITIES = [
    ("Agartala", "Tripura", 23.8315, 91.2868), ("Agra", "Uttar Pradesh", 27.1767, 78.0081),
    ("Ahmedabad", "Gujarat", 23.0225, 72.5714), ("Aizawl", "Mizoram", 23.7271, 92.7176),
    ("Ajmer", "Rajasthan", 26.4499, 74.6399), ("Aligarh", "Uttar Pradesh", 27.8974, 78.0880),
    ("Allahabad (Prayagraj)", "Uttar Pradesh", 25.4358, 81.8463), ("Amravati", "Maharashtra", 20.9374, 77.7796),
    ("Amritsar", "Punjab", 31.6340, 74.8723), ("Anand", "Gujarat", 22.5645, 72.9289),
    ("Aurangabad (Chh. Sambhajinagar)", "Maharashtra", 19.8762, 75.3433), ("Bareilly", "Uttar Pradesh", 28.3670, 79.4304),
    ("Belgaum (Belagavi)", "Karnataka", 15.8497, 74.4977), ("Bengaluru", "Karnataka", 12.9716, 77.5946),
    ("Bhagalpur", "Bihar", 25.2425, 86.9842), ("Bhavnagar", "Gujarat", 21.7645, 72.1519),
    ("Bhilwara", "Rajasthan", 25.3407, 74.6313), ("Bhopal", "Madhya Pradesh", 23.2599, 77.4126),
    ("Bhubaneswar", "Odisha", 20.2961, 85.8245), ("Bikaner", "Rajasthan", 28.0229, 73.3119),
    ("Bilaspur", "Chhattisgarh", 22.0797, 82.1409), ("Chandigarh", "Chandigarh", 30.7333, 76.7794),
    ("Chennai", "Tamil Nadu", 13.0827, 80.2707), ("Coimbatore", "Tamil Nadu", 11.0168, 76.9558),
    ("Cuttack", "Odisha", 20.4625, 85.8830), ("Darbhanga", "Bihar", 26.1542, 85.8918),
    ("Dehradun", "Uttarakhand", 30.3165, 78.0322), ("Delhi", "Delhi", 28.6139, 77.2090),
    ("Dhanbad", "Jharkhand", 23.7957, 86.4304), ("Dimapur", "Nagaland", 25.9063, 93.7276),
    ("Durgapur", "West Bengal", 23.5204, 87.3119), ("Erode", "Tamil Nadu", 11.3410, 77.7172),
    ("Faridabad", "Haryana", 28.4089, 77.3178), ("Firozabad", "Uttar Pradesh", 27.1592, 78.3957),
    ("Gandhinagar", "Gujarat", 23.2156, 72.6369), ("Gangtok", "Sikkim", 27.3389, 88.6065),
    ("Ghaziabad", "Uttar Pradesh", 28.6692, 77.4538), ("Goa (Panaji)", "Goa", 15.4909, 73.8278),
    ("Gorakhpur", "Uttar Pradesh", 26.7606, 83.3732), ("Greater Noida", "Uttar Pradesh", 28.4744, 77.5040),
    ("Gurugram", "Haryana", 28.4595, 77.0266), ("Guntur", "Andhra Pradesh", 16.3067, 80.4365),
    ("Guwahati", "Assam", 26.1445, 91.7362), ("Gwalior", "Madhya Pradesh", 26.2183, 78.1828),
    ("Haridwar", "Uttarakhand", 29.9457, 78.1642), ("Hisar", "Haryana", 29.1492, 75.7217),
    ("Hubballi-Dharwad", "Karnataka", 15.3647, 75.1240), ("Hyderabad", "Telangana", 17.3850, 78.4867),
    ("Imphal", "Manipur", 24.8170, 93.9368), ("Indore", "Madhya Pradesh", 22.7196, 75.8577),
    ("Itanagar", "Arunachal Pradesh", 27.0844, 93.6053), ("Jabalpur", "Madhya Pradesh", 23.1815, 79.9864),
    ("Jaipur", "Rajasthan", 26.9124, 75.7873), ("Jalandhar", "Punjab", 31.3260, 75.5762),
    ("Jammu", "Jammu and Kashmir", 32.7266, 74.8570), ("Jamnagar", "Gujarat", 22.4707, 70.0577),
    ("Jamshedpur", "Jharkhand", 22.8046, 86.2029), ("Jhansi", "Uttar Pradesh", 25.4484, 78.5685),
    ("Jodhpur", "Rajasthan", 26.2389, 73.0243), ("Kakinada", "Andhra Pradesh", 16.9891, 82.2475),
    ("Kanpur", "Uttar Pradesh", 26.4499, 80.3319), ("Kannur", "Kerala", 11.8745, 75.3704),
    ("Karnal", "Haryana", 29.6857, 76.9905), ("Kochi", "Kerala", 9.9312, 76.2673),
    ("Kolhapur", "Maharashtra", 16.7050, 74.2433), ("Kolkata", "West Bengal", 22.5726, 88.3639),
    ("Kota", "Rajasthan", 25.2138, 75.8648), ("Kozhikode", "Kerala", 11.2588, 75.7804),
    ("Lucknow", "Uttar Pradesh", 26.8467, 80.9462), ("Ludhiana", "Punjab", 30.9010, 75.8573),
    ("Madurai", "Tamil Nadu", 9.9252, 78.1198), ("Mangaluru", "Karnataka", 12.9141, 74.8560),
    ("Mathura", "Uttar Pradesh", 27.4924, 77.6737), ("Meerut", "Uttar Pradesh", 28.9845, 77.7064),
    ("Moradabad", "Uttar Pradesh", 28.8386, 78.7733), ("Morbi", "Gujarat", 22.8173, 70.8370),
    ("Mumbai", "Maharashtra", 19.0760, 72.8777), ("Muzaffarpur", "Bihar", 26.1209, 85.3647),
    ("Mysuru", "Karnataka", 12.2958, 76.6394), ("Nagpur", "Maharashtra", 21.1458, 79.0882),
    ("Nashik", "Maharashtra", 19.9975, 73.7898), ("Navi Mumbai", "Maharashtra", 19.0330, 73.0297),
    ("Nellore", "Andhra Pradesh", 14.4426, 79.9865), ("Noida", "Uttar Pradesh", 28.5355, 77.3910),
    ("Panipat", "Haryana", 29.3909, 76.9635), ("Patiala", "Punjab", 30.3398, 76.3869),
    ("Patna", "Bihar", 25.5941, 85.1376), ("Puducherry", "Puducherry", 11.9416, 79.8083),
    ("Pune", "Maharashtra", 18.5204, 73.8567), ("Raipur", "Chhattisgarh", 21.2514, 81.6296),
    ("Rajkot", "Gujarat", 22.3039, 70.8022), ("Ranchi", "Jharkhand", 23.3441, 85.3096),
    ("Rourkela", "Odisha", 22.2604, 84.8536), ("Saharanpur", "Uttar Pradesh", 29.9680, 77.5552),
    ("Salem", "Tamil Nadu", 11.6643, 78.1460), ("Shillong", "Meghalaya", 25.5788, 91.8933),
    ("Shimla", "Himachal Pradesh", 31.1048, 77.1734), ("Siliguri", "West Bengal", 26.7271, 88.3953),
    ("Solapur", "Maharashtra", 17.6599, 75.9064), ("Srinagar", "Jammu and Kashmir", 34.0837, 74.7973),
    ("Surat", "Gujarat", 21.1702, 72.8311), ("Thane", "Maharashtra", 19.2183, 72.9781),
    ("Thiruvananthapuram", "Kerala", 8.5241, 76.9366), ("Thrissur", "Kerala", 10.5276, 76.2144),
    ("Tiruchirappalli", "Tamil Nadu", 10.7905, 78.7047), ("Tirunelveli", "Tamil Nadu", 8.7139, 77.7567),
    ("Tirupati", "Andhra Pradesh", 13.6288, 79.4192), ("Tiruppur", "Tamil Nadu", 11.1085, 77.3411),
    ("Udaipur", "Rajasthan", 24.5854, 73.7125), ("Ujjain", "Madhya Pradesh", 23.1765, 75.7885),
    ("Vadodara", "Gujarat", 22.3072, 73.1812), ("Varanasi", "Uttar Pradesh", 25.3176, 82.9739),
    ("Vellore", "Tamil Nadu", 12.9165, 79.1325), ("Vijayawada", "Andhra Pradesh", 16.5062, 80.6480),
    ("Visakhapatnam", "Andhra Pradesh", 17.6868, 83.2185), ("Warangal", "Telangana", 17.9689, 79.5941),
]

# AllEvents widget city name, when it differs from the picker label.
AE_CITY = {"Allahabad (Prayagraj)": "Allahabad", "Aurangabad (Chh. Sambhajinagar)": "Aurangabad",
           "Belgaum (Belagavi)": "Belgaum", "Goa (Panaji)": "Panaji", "Gurugram": "Gurgaon",
           "Mangaluru": "Mangalore", "Mysuru": "Mysore", "Hubballi-Dharwad": "Hubli"}

PROMPTS = {
    "find": ("Find fairs in the next 6 months",
             "You are a trade-fair researcher for Indian small businesses.\n\n"
             "List every trade fair, exhibition, B2B expo, buyer-seller meet and consumer mela that is happening in or within {radius} of {city}, India, between {from} and {to}, that would suit a business selling {sector}. My goal: {goal}.\n\n"
             "For each event give: name, dates, venue, city, organiser, official website, whether it is trade-only or open to the public, last edition's visitor and exhibitor numbers if published, and who to contact for a stall.\n\n"
             "Rules:\n- Use only the organiser's own site, ITPO (indiatradefair.com), export promotion councils, state government or DIC notices, and news from the last 12 months. Use 10times.com or tradeindia.com only to discover events, then confirm on the organiser's site.\n- Mark anything you could not confirm on an official page as UNCONFIRMED.\n- Do not invent events, dates or numbers.\n\nOutput a table sorted by date, then a 3-line recommendation of the two best events for my goal and why."),
    "vet": ("Check an expo before you pay for a stall",
            "I'm a small {sector} business from {city}. An organiser is offering me a stall at this event: [EVENT NAME, DATES, VENUE, ORGANISER, LINK].\n\n"
             "Help me decide if it's worth it. Research and tell me:\n"
             "1. Is the organiser real and how many past editions have they run? Link the evidence.\n"
             "2. Past footfall and exhibitor numbers, and whether independent sources (news, photos, videos, exhibitor posts) support them.\n"
             "3. Who actually visits: trade buyers, the public, students? Does that match my goal ({goal})?\n"
             "4. Reviews or complaints from past exhibitors (Google reviews, Reddit, LinkedIn, YouTube, consumer forums).\n"
             "5. Red flags: no fixed venue booking, no past exhibitor list, pressure to pay full amount upfront, 'guaranteed buyers', a fake government logo, unclear refund terms.\n"
             "6. 10 questions I should ask the organiser before paying.\n\nEnd with a verdict: Book / Visit first / Avoid, with one line why."),
    "negotiate": ("Message to the organiser",
                  "Write a short, polite WhatsApp message (English with simple Hindi words is fine) from me, a small {sector} business from {city}, to an expo organiser. Ask for:\n"
                  "- stall sizes and rates (shell scheme and bare space), what's included (walls, fascia name, table, chairs, lights, power socket)\n"
                  "- last edition's visitor and exhibitor numbers, and a past exhibitor list\n"
                  "- a floor plan with free stalls marked, and which spots get the most walk-by\n"
                  "- any discount for first-time exhibitors, MSMEs, women entrepreneurs or early payment\n"
                  "- whether the fair is approved for the MSME Ministry's stall-rent reimbursement\n"
                  "- payment schedule, GST invoice, and refund policy if the event is postponed\n"
                  "Keep it under 120 words."),
    "plan": ("Plan your stall and follow-up",
             "I'm exhibiting {sector} at a fair. My goal: {goal}. Budget about ₹{budget}. Help me plan:\n"
             "1. One clear offer for visitors (a fair-only price, sample pack or dealer scheme) that fits my goal.\n"
             "2. Stall layout for a 3m x 3m booth: what goes on the back wall, the counter, and what the visitor touches first.\n"
             "3. A 10-second pitch my staff can say to every visitor.\n"
             "4. A simple lead form (5 fields max) and how to tag hot / warm / cold leads.\n"
             "5. A follow-up plan: what to send within 24 hours, day 3, day 7 and day 30, with WhatsApp message drafts.\n"
             "6. How to measure if the fair paid back: cost per lead and cost per order."),
}

CHECKLIST = [
    ("Before you book", [
        "Visit the fair once as a visitor before you exhibit. Count how many people stop at stalls like yours.",
        "Ask the organiser for last year's exhibitor list and call two of them.",
        "Check the visitor type: trade-only fairs bring buyers who order later; public fairs bring buyers who pay now.",
        "Get stall size, rate, what's included, and the payment and refund terms in writing, with a GST invoice.",
        "Ask if the fair is on the MSME-DFO approved list for stall-rent reimbursement, and apply before the fair.",
        "Book corner or aisle-facing stalls near the entrance or food court when you can.",
    ]),
    ("Get ready", [
        "Decide one goal: cash sales, dealer leads, export enquiries or supplier contacts. Everything else follows from it.",
        "Make one fair-only offer, a price list, and a dealer or bulk rate sheet.",
        "Print a big, readable banner: what you make, in five words. Add a WhatsApp QR code.",
        "Carry stock for walk-in sales, samples, a card machine or UPI QR, a receipt book, extension cords and tape.",
        "Set up a digital business card and a lead form on your phone. Brief your team on the 10-second pitch.",
        "Book travel and stay early. Hotels near big venues fill up fast.",
    ]),
    ("At the fair", [
        "Stand at the front of the stall, not behind the table. Greet everyone who slows down.",
        "Collect a phone number from every serious visitor and tag them hot, warm or cold.",
        "Walk the fair: note competitors' prices, packaging and offers, and meet suppliers.",
        "Photograph your stall and crowd for social media and for the subsidy claim.",
    ]),
    ("After the fair", [
        "Message every lead within 24 hours while they still remember you.",
        "Send samples or quotations to hot leads within 3 days; call warm leads within a week.",
        "Work out cost per lead and cost per order. Decide whether to come back next year.",
        "File your stall-rent reimbursement claim with receipts and photos on time.",
    ]),
]

RED_FLAGS = [
    "Promises of 'guaranteed buyers' or a set number of orders.",
    "No venue named, or a venue that has no booking for those dates.",
    "Government logos on a private event without the ministry or ITPO listed as organiser.",
    "Full payment upfront to a personal account, no GST invoice, no refund terms.",
    "'International' fairs with no list of foreign buyers or past exhibitors.",
    "Pressure to decide today because 'only two stalls are left'.",
]


def config(city_pages=None):
    venues = {k: {"name": v[0], "city": v[1], "lat": v[2], "lng": v[3], "url": v[4]} for k, v in VENUES.items()}
    return {
        "leadEndpoint": sf.LEAD_ENDPOINT,
        "bookCallUrl": sf.BOOK_CALL_URL,
        "reviewed": REVIEWED,
        "sectors": dict(SECTORS), "goals": dict(GOALS),
        "cities": [list(c) for c in CITIES],
        "aeCity": AE_CITY,
        "cityPages": city_pages or {},
        "venues": venues,
        "fairs": FAIRS,
        "support": SUPPORT,
        "prompts": PROMPTS,
        "checklist": CHECKLIST,
        "redFlags": RED_FLAGS,
        "schemeFinder": "/tools/scheme-finder/",
    }


def _version(cfg):
    h = hashlib.sha1()
    for f in ("app.js", "style.css"):
        h.update((SRC_DIR / f).read_bytes())
    h.update((sf.SRC_DIR / "style.css").read_bytes())
    h.update(json.dumps(cfg, sort_keys=True).encode())
    return h.hexdigest()[:10]


def _opts(items, placeholder=None):
    o = f'<option value="">{placeholder}</option>' if placeholder else ""
    return o + "".join(f'<option value="{k}">{v}</option>' for k, v in items)


def _city_opts(esc):
    by_state = {}
    for name, state, _, _ in CITIES:
        by_state.setdefault(state, []).append(name)
    out = '<option value="">Select your city</option>'
    for state in sorted(by_state):
        out += f'<optgroup label="{esc(state)}">' + "".join(
            f'<option value="{esc(n)}">{esc(n)}</option>' for n in sorted(by_state[state])) + "</optgroup>"
    return out


def build_page(head, nav, footer, esc, p, city_pages=None):
    cfg = config(city_pages)
    cfg["schemeFinder"] = p(cfg["schemeFinder"])
    cfg["cityPages"] = {k: p(v) for k, v in cfg["cityPages"].items()}
    v = _version(cfg)
    title = "Trade Fair & Expo Finder: Exhibitions for Your Business, City by City (Free) | KidharMilega"
    desc = (f"Pick your city and product and get a free report of the trade fairs, expos and melas worth a stall: "
            f"{len(FAIRS)} major Indian fairs with venue, month and who visits, live events in your city, stall "
            f"subsidies, a budget calculator and AI prompts to find more.")
    ld = {
        "@context": "https://schema.org", "@type": "WebApplication", "name": "KidharMilega Expo Finder",
        "url": "https://kidharmilega.in" + TOOL_PATH, "applicationCategory": "BusinessApplication",
        "operatingSystem": "Any", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "INR"},
        "description": desc,
    }
    extra = (f'<link rel="stylesheet" href="{p(sf.TOOL_PATH + "style.css")}?v={v}">'
             f'<link rel="stylesheet" href="{p("/tools/export-buyer-finder/style.css")}?v={v}">'
             f'<link rel="stylesheet" href="{p("/tools/scheme-finder/style.css")}?v={v}">'
             f'<link rel="stylesheet" href="{p(TOOL_PATH + "style.css")}?v={v}">'
             f'<script type="application/ld+json">{json.dumps(ld)}</script>')
    radio = lambda name, items: "".join(
        f'<label class="scf-radio"><input type="radio" name="{name}" value="{k}"><span>{esc(l)}</span></label>' for k, l in items)
    return head(title, desc, TOOL_PATH, extra_head=extra) + nav("tools") + f'''
<main class="sf scf exf"><div class="container">
  <header class="page-header sf-header">
    <div class="section-label">Free tool · Expo Finder</div>
    <h1 class="page-header-title">Which trade fairs and expos<br><em>are worth a stall for you?</em></h1>
    <p class="page-header-sub">Tell us your city, what you sell and why you want to go. Get a free report of the fairs that fit, from live events in your city to the {len(FAIRS)} big fairs Indian small businesses use, plus stall subsidies, a budget calculator and how to avoid fake expos.</p>
    <ol class="sf-how" aria-label="How it works">
      <li><span>1</span>Pick your city and product</li>
      <li><span>2</span>Tell us your goal</li>
      <li><span>3</span>Get your expo report</li>
    </ol>
  </header>

  <form class="sf-form" id="exfForm" autocomplete="off" novalidate>
    <section class="sf-step">
      <h2 class="sf-step__title"><span class="sf-step__num">1</span>Where and what</h2>
      <label class="sf-label" for="exfCity">Your city</label>
      <select class="sf-input" id="exfCity">{_city_opts(esc)}</select>
      <p class="sf-hint">Not listed? Pick the nearest big city.</p>
      <label class="sf-label" for="exfSector">What do you make or sell?</label>
      <select class="sf-input" id="exfSector">{_opts(SECTORS, "Choose one")}</select>
    </section>

    <section class="sf-step">
      <h2 class="sf-step__title"><span class="sf-step__num">2</span>Why go to a fair?</h2>
      <fieldset class="scf-radios"><legend class="sf-label">Your main goal</legend>{radio("goal", GOALS)}</fieldset>
      <fieldset class="scf-radios"><legend class="sf-label">How far will you travel?</legend>{radio("travel", TRAVEL)}</fieldset>
    </section>

    <section class="sf-step">
      <h2 class="sf-step__title"><span class="sf-step__num">3</span>Stall subsidies</h2>
      <fieldset class="scf-checks"><legend class="sf-label">Tick what applies <span class="sf-opt">(optional)</span></legend>
        <label class="scf-check"><input type="checkbox" id="exfUdyam"><span>Udyam (MSME) registered</span></label>
        <label class="scf-check"><input type="checkbox" id="exfWomen"><span>Woman-owned</span></label>
        <label class="scf-check"><input type="checkbox" id="exfScst"><span>SC / ST owner</span></label>
        <label class="scf-check"><input type="checkbox" id="exfArtisan"><span>Artisan / weaver card</span></label>
        <label class="scf-check"><input type="checkbox" id="exfShg"><span>Self-help group (SHG)</span></label>
        <label class="scf-check"><input type="checkbox" id="exfIec"><span>Exporter (IEC)</span></label>
      </fieldset>
    </section>

    <div class="sf-submit">
      <button class="btn btn-primary btn-lg" type="submit">Get my free expo report <span class="btn__arrow" aria-hidden="true">&rarr;</span></button>
      <p class="sf-error" id="exfError" role="alert"></p>
    </div>
  </form>

  <div class="sf-gate" id="exfGate" hidden>
    <div class="sf-gate__card" role="dialog" aria-modal="true" aria-labelledby="exfGateTitle">
      <button class="sf-gate__close" type="button" id="exfGateClose" aria-label="Close">&times;</button>
      <h2 id="exfGateTitle">Your expo report is ready</h2>
      <p>Tell us where to send fair alerts. When stall bookings open for fairs that fit you, we'll let you know.</p>
      <form id="exfGateForm" novalidate>
        <label class="sf-label" for="exfEmail">Email</label>
        <input class="sf-input" id="exfEmail" type="email" inputmode="email" autocomplete="email" required placeholder="you@example.com">
        <label class="sf-label" for="exfPhone">WhatsApp number <span class="sf-opt">(optional)</span></label>
        <input class="sf-input" id="exfPhone" type="tel" inputmode="tel" autocomplete="tel" placeholder="10-digit mobile">
        <p class="sf-error" id="exfGateError" role="alert"></p>
        <button class="btn btn-primary" type="submit" style="width:100%">Show my report</button>
        <p class="sf-fine">By continuing you agree to our <a href="{p('/terms-of-service/')}">terms</a>. No spam.</p>
      </form>
    </div>
  </div>

  <section class="scf-report exf-report" id="exfReport" hidden aria-live="polite"></section>
  <noscript><p class="sf-error">This tool needs JavaScript turned on.</p></noscript>
</div></main>
<script>window.EXF_CONFIG={json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")};</script>
<script src="{p(TOOL_PATH + "app.js")}?v={v}" defer></script>
''' + footer() + "</body></html>"


def city_pages_from_posts(posts, parse_shortcode):
    """Map lower-case city name -> KidharMilega events page path, preferring the exhibitions page."""
    out = {}
    for post in posts:
        slug = post["post_name"]
        city, _ = parse_shortcode(post["post_content"])
        if not city or slug == "events-in-india":
            continue
        key = city.strip().lower()
        if key not in out or slug.startswith("exhibitions-"):
            out[key] = f"/{slug}/"
    return out


def write_expo_finder(dist_dir, head, nav, footer, esc, p, city_pages=None):
    out = Path(dist_dir) / "tools" / "expo-finder"
    out.mkdir(parents=True, exist_ok=True)
    for f in ("app.js", "style.css"):
        shutil.copy(SRC_DIR / f, out / f)
    (out / "index.html").write_text(build_page(head, nav, footer, esc, p, city_pages), encoding="utf-8")
    return len(FAIRS), len(CITIES)
