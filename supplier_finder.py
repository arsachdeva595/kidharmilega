"""Supplier Finder tool (/tools/supplier-finder/).

The user picks an 8-digit HSN code and a district, leaves an email, and gets:
  1. copy-ready AI prompts (find suppliers -> build a sheet -> the Google Maps / GMB hack -> GSTIN -> outreach)
  2. a supplier audit checklist: general checks + checks for the product's HSN category

Everything here is data plus one page builder; build.py calls write_supplier_finder(). The page is static:
the browser loads hsn.json and districts.json, fills the prompt templates, and posts the lead to a
Google Apps Script web app (see tools_src/supplier-finder/SETUP.md).
"""
import json, re, shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent
SRC_DIR = BASE_DIR / "tools_src" / "supplier-finder"

# Paste the Apps Script web-app URL here (ends in /exec). Empty = leads are not saved, the tool still works.
LEAD_ENDPOINT = ""
# "Need help?" call booking. Swap for the dedicated Topmate product link when it exists.
BOOK_CALL_URL = "https://topmate.io/arsachdeva"

TOOL_PATH = "/tools/supplier-finder/"


# ── ODOP product → HSN mapping ────────────────────────────────────────────────
# Each rule: (regex on the ODOP product name, [4-digit headings or 2-digit chapters]).
# All matching rules apply. Used to suggest "districts known for this product" for an HSN code.
ODOP_RULES = [
    # Textiles: silk, sarees, handloom
    (r"silk|tasar|kosa|muga|\beri\b|banka|kharsawan", ["5004", "5006", "5007", "6214"]),
    (r"sare|sari\b|gollabama", ["5007", "5208", "5209"]),
    (r"handloom|ikat|ikkat|bomkai|jamdani|chanderi|kota doria|bandha|tangail|shantipore|dhaniakhali|pochampalli|"
     r"venkatagiri|uppada|ilkal|narayanpet|ponduru|molakalmuru|bawan booti|wangkhei|fanek|risha|single ikat|patta", ["5007", "5208", "5209", "5407"]),
    (r"kalamkari|bagh print|batik|farrukhabad|bandhani|prints?\b", ["5208", "5209", "6214", "6302"]),
    (r"shawl|pashmina|kani\b|crewal|woollen product", ["6214", "6117", "5111", "5112"]),
    (r"carpet|dar[ir]|durrie|panja", ["5701", "5702", "5703", "5705"]),
    (r"embroider|chikan|kasheeda|phulkari|applique|patch ?work|lambani|chamba rumal|sequence|crochet", ["5810", "6214", "6211", "6117"]),
    (r"zari|zardo", ["5605", "5810"]),
    (r"garment|apparel|readymade|ready-made|ready made|hosiery|jacket|jean|denim|clothes|tailoring|bags & garments", ["6109", "6110", "6201", "6203", "6204", "6205", "6206", "6211"]),
    (r"denim|jean", ["5209"]),
    (r"made ups|made-ups|home furnishing|bedsheet|towel|terry|home made ups", ["6302", "6304", "6303"]),
    (r"gauze|cotton products \(balls", ["3005", "5601", "5803"]),
    (r"cotton yarn|textile \(yarn\)", ["5205", "5206"]),
    (r"cotton bales|ginning|^cotton$|cotton & agri|cotton based", ["5201", "5203"]),
    (r"cotton seed oil|cotton and cotton seed", ["1512", "5201"]),
    (r"^textiles?$|powerloom|textile products|textiles and|garments & textiles|handloom and textiles|textile and apparels", ["5208", "5407", "5513", "6302"]),
    (r"jute", ["5303", "5310", "6305", "4602"]),
    (r"coir", ["5305", "5702", "5705"]),
    (r"natural fibre|banana fib|nettle", ["5305", "5311", "4602"]),
    # Leather & footwear
    (r"leather", ["4202", "4203", "4205", "4107"]),
    (r"footwear|shoes", ["6403", "6404", "6405", "6406"]),
    # Metal craft
    (r"brass|bell metal|dhokra|dokra|moradabad metal|ghungroo|bells|copper|bidari|metal craft|metal utensils", ["7418", "7419", "8306"]),
    (r"zinc utensils", ["7907"]),
    (r"stainless steel|kitchen ware", ["7323"]),
    (r"aluminium ingot", ["7601"]),
    (r"steel and allied|tmt|steel-", ["7213", "7214", "7308"]),
    (r"steel furniture", ["9403"]),
    # Jewellery
    (r"jewel|jewll|filigree|tarkashi|tarakashi|thewa|gems", ["7113", "7117", "7103"]),
    (r"pearl", ["7101"]),
    (r"agate|bead necklace", ["7103", "7117"]),
    (r"lac bangles", ["7117"]),
    (r"^lac|lac products|lac &", ["1301", "7117"]),
    (r"bindi|tikuli", ["3304", "9615"]),
    # Wood, bamboo, grass
    (r"wood|teak|sankheda|lacquerware|temple imit|flute and wooden|udayagiri", ["4420", "4419", "4421", "9403"]),
    (r"teak", ["4403", "4407"]),
    (r"furniture", ["9403", "9401"]),
    (r"toy|laiphadibi", ["9503"]),
    (r"bamboo|cane", ["4602", "4601", "4421", "9403"]),
    (r"wicker|willow|moonj|golden grass|sital pati|wheat stalk|sabai", ["4602", "4601"]),
    (r"areca leaf|arecanut leaf|sal leaf", ["4823", "1404"]),
    # Clay, stone, glass
    (r"terracotta|pottery|ceramic product", ["6912", "6913", "6914"]),
    (r"ceramic tiles|sanitary ware|sanitary goods", ["6907", "6910"]),
    (r"refractory", ["6902", "6903"]),
    (r"glass", ["7013", "7018"]),
    (r"stone|granite|marble|sandstone|slate|stale stone|kota stone|gaura|shazar|durgi|allagadda", ["6802", "2515", "2516", "6801"]),
    (r"cement", ["2523"]),
    (r"coal", ["2701"]),
    (r"mica", ["2525", "6814"]),
    (r"quartz|feldspar", ["2506", "2529"]),
    (r"fullers earth|betonitte|bentonite", ["2508"]),
    (r"mineral based", ["25"]),
    # Art, handicraft, music, sport
    (r"painting|madhubani|madhubhani|patachitra|pattachitra|sohrai|paithkar|aipan|wall hanging", ["9701", "4911"]),
    (r"handmade paper", ["4802", "4823"]),
    (r"handicraft|tribal craft|bastar|decorative|home decorative", ["4420", "6913", "8306", "4602", "9701"]),
    (r"horn bone", ["9601"]),
    (r"musical|dholak|flute|veena", ["9202", "9206", "9205"]),
    (r"sports", ["9506", "9504"]),
    # Chemicals, pharma, cosmetics, plastics
    (r"perfume|kannauj", ["3303", "3301"]),
    (r"aromatic plants|lemon ?grass|natural oils|oil - agar|agarwood|oleo raisins|oleoresin", ["3301", "1211"]),
    (r"mentha|menthol", ["3301", "2906"]),
    (r"ayurved|herbal|biopharma|wellness|sonamukhi", ["3004", "1211", "3304"]),
    (r"pharma", ["3004", "3003", "2941", "3002"]),
    (r"chemical", ["28", "29", "38"]),
    (r"plastic", ["3923", "3924", "3926"]),
    (r"rubber", ["4016", "4011", "4008"]),
    (r"corrugated|packaging", ["4819", "4808"]),
    (r"resin$", ["1301"]),
    # Engineering
    (r"auto|automobile|tractor|diesel engine|rim and axle", ["8708", "8714", "8701", "8408", "8409"]),
    (r"engineering|machine tool|machineries|mining & crushing", ["8466", "8459", "8474", "8479", "7326"]),
    (r"fastner|fastener", ["7318"]),
    (r"forged|foundry|metal casting", ["7325", "7326"]),
    (r"lock & hardware", ["8301", "8302"]),
    (r"motor pumps", ["8413"]),
    (r"farm equipment|agri - implements|agriculture implements|agriculture & dairy", ["8432", "8433", "8201", "8434"]),
    (r"scientific equipment", ["9027", "9023", "9031"]),
    (r"esdm", ["85"]),
    (r"sanitary fittings", ["8481", "7324"]),
    # Food & agri
    (r"rice|basmati|matta|kalanamak|sonachur|chakao|jiraphul|chinnaur|tulai panji|aromatic rice|scented", ["1006"]),
    (r"poha|rice based", ["1904", "1006"]),
    (r"millet|ragi|kodo|kutki|nagali|buck ?wheat", ["1008", "1102"]),
    (r"maize|corn", ["1005", "1108", "1904"]),
    (r"pulses|dal\b|daal|gram|masoor|arhar|toor|kholar|kidney beans|^peas$", ["0713"]),
    (r"chil+i|chilly|mircha|jholokia|marcha", ["0904"]),
    (r"turmeric|haladi", ["0910"]),
    (r"ginger", ["0910"]),
    (r"garlic|onion", ["0703", "0712"]),
    (r"coriander|cilantro", ["0909", "0709"]),
    (r"cardamom", ["0908"]),
    (r"saffron", ["0910"]),
    (r"hing|asafoetida", ["1301"]),
    (r"spices|pan meethi", ["0904", "0909", "0910"]),
    (r"dry fruits", ["0802", "0813"]),
    (r"mango", ["0804", "2007", "2008"]),
    (r"banana", ["0803", "2008"]),
    (r"^(?!.*custard).*apple", ["0808"]),
    (r"custard apple", ["0810", "2008"]),
    (r"apricot", ["0809", "0813"]),
    (r"guava|litchi|dragon fruit|kiwi|strawberr|jackfruit|chikoo|sapota", ["0810", "0804", "2008"]),
    (r"pineapple", ["0804", "2008", "2009"]),
    (r"orange|mandarin|kinnow|citrus|lemon", ["0805", "2009"]),
    (r"papaya|watermelon", ["0807"]),
    (r"grapes|raisins", ["0806"]),
    (r"amla|aamla|gooseberry|seabuckthorn", ["0811", "0813", "2008"]),
    (r"pickle", ["2001"]),
    (r"tomato", ["0702", "2002"]),
    (r"vegetable$|vegetables|potato|dehydrated", ["0701", "0709", "0712", "2004", "2005"]),
    (r"mushroom", ["0709", "0712", "2003"]),
    (r"cashew", ["0801"]),
    (r"walnut|pecan|chirounji", ["0802"]),
    (r"^areca ?nut$|^arecanut$", ["0802"]),
    (r"groundnut|peanut", ["1202", "2008"]),
    (r"makhana|foxnut", ["0802", "2008"]),
    (r"coconut", ["0801", "1513", "5305"]),
    (r"coffee", ["0901"]),
    (r"\btea\b", ["0902"]),
    (r"honey", ["0409"]),
    (r"dairy|milk|ghee", ["0401", "0402", "0405", "0406"]),
    (r"bal mithai", ["1704", "2106"]),
    (r"namkeen", ["2106", "1904"]),
    (r"bakery|biscuit|confectionery", ["1905", "1704"]),
    (r"jaggery|sugarcane|cane sugar", ["1701"]),
    (r"sesame", ["1207", "1704"]),
    (r"mustard", ["1207", "1514"]),
    (r"edible oil|vegetable oil|chulli", ["1512", "1514", "1515"]),
    (r"de-oiled cake", ["2304", "2306"]),
    (r"soya", ["1201", "1507", "2304"]),
    (r"poultry feed", ["2309", "0207"]),
    (r"kadaknath", ["0105", "0207"]),
    (r"fish|marine|shrimp|prawn|trout|seafood", ["0302", "0303", "0306", "1605"]),
    (r"mahua", ["1212", "1211"]),
    (r"tamarind", ["0813", "2008"]),
    (r"minor forest", ["1211", "1301"]),
    (r"feni", ["2208"]),
    (r"floriculture|orchid|flowers", ["0603", "0602"]),
    (r"potato", ["0701"]),
    (r"food processing|agro|agricultural products|food products|fmcg", ["19", "20", "21"]),
]
# "X products" / "X processing" of a fruit, vegetable or nut also belong in the prepared-food headings.
PROCESSED_RE = re.compile(r"product|processing|processed|based|jelly|pulp|extract", re.I)


def odop_hsn_codes(product):
    p = (product or "").lower()
    codes = []
    for rx, heads in ODOP_RULES:
        if re.search(rx, p):
            for h in heads:
                if h not in codes:
                    codes.append(h)
    if PROCESSED_RE.search(p):
        extra = []
        if any(c.startswith("08") for c in codes):
            extra += ["2007", "2008", "2009"]   # jams/jellies, prepared fruit & nuts, juices
        if any(c.startswith("07") for c in codes):
            extra += ["2004", "2005"]           # prepared vegetables
        for h in extra:
            if h not in codes:
                codes.append(h)
    return codes


def build_districts_json(districts, product_page_slug):
    out = []
    for d in districts:
        if (d.get("page_status") or "").lower() != "live":
            continue
        prod = (d.get("odop_product_name") or "").strip()
        out.append({
            "s": d.get("state", "").strip(),
            "d": d.get("district_name", "").strip(),
            "p": prod,
            "u": "/products/" + product_page_slug(d) + "/",
            "h": odop_hsn_codes(prod),
        })
    out.sort(key=lambda r: (r["s"], r["d"]))
    return out


# ── Prompts ───────────────────────────────────────────────────────────────────
# {product} {hsn} {hsnName} {place} {district} {state} are filled in by the page.
PROMPTS = [
    {
        "id": "find",
        "step": "Step 1",
        "title": "Find the suppliers",
        "why": "Gives you a first, generic list pulled from JustDial, IndiaMART and similar sites.",
        "text": (
            "I want to buy {product} directly from manufacturers and wholesalers in {place}, India.\n"
            "Product: {product}\n"
            "HSN code: {hsn} ({hsnName})\n\n"
            "Search the web for suppliers of this product located in {district} district or within 50 km of it. "
            "Check JustDial, IndiaMART, TradeIndia, ExportersIndia, the District Industries Centre (DIC) and ODOP pages "
            "for {district}, state MSME and handicraft/handloom portals, local trade associations and news articles.\n"
            "Also search using the local trade names for this product, including Hindi and regional-language terms.\n\n"
            "Give me at least 25 suppliers. For each one: business name, type (manufacturer / wholesaler / trader / "
            "artisan or cluster), town or area, what exactly they make, and the source link where you found them.\n"
            "Put manufacturers first. Only list businesses you actually found a source for. Do not invent names. "
            "If you find fewer than 25, tell me how many you found."
        ),
    },
    {
        "id": "sheet",
        "step": "Step 2",
        "title": "Turn it into a sheet",
        "why": "When you open this sheet you will see most names have no number, email or website. That is normal. Step 3 fixes it.",
        "text": (
            "Put this supplier list into a spreadsheet I can download (Excel or CSV) with these columns:\n"
            "#, Business name, Type, Town/Area, Products, Phone, WhatsApp, Email, Website, Google Maps link, "
            "Google rating, Number of reviews, GSTIN, Source link, Notes.\n\n"
            "Fill only what you have verified from a source. Leave a cell empty if you don't know it. "
            "Do not guess phone numbers, emails or websites."
        ),
    },
    {
        "id": "gmb",
        "step": "Step 3 · The hack",
        "title": "Get their Google Maps profiles",
        "why": "Local suppliers are on Google Maps even when they have no website. Their Google Business Profile has the address, phone, website, sometimes an email, and real reviews.",
        "text": (
            "Now take every business in the sheet and search for it on Google Maps in {place}, "
            "using the business name plus its town or area.\n"
            "Find its Google Business Profile and fill in: the Google Maps link to the profile, full address, phone number, "
            "website, email (if listed), Google rating, number of reviews, the business category shown on the profile, "
            "and roughly how old the profile is (date of the oldest review or photo).\n\n"
            "Rules:\n"
            "- Write \"Not found\" if there is no profile.\n"
            "- Write \"Possible match\" if the name or area doesn't match exactly, so I can check it myself.\n"
            "- Do not fill anything you did not see on the profile.\n\n"
            "Then sort the sheet by number of reviews, highest first, and give me the updated file."
        ),
    },
    {
        "id": "gst",
        "step": "Bonus",
        "title": "Find their GSTINs",
        "why": "You need the GSTIN to run the audit checks below on the official GST portal.",
        "text": (
            "For each business in the sheet, find its GSTIN (15-character GST number). Look on its IndiaMART/TradeIndia "
            "listing, its website footer or contact page, and its Google Business Profile.\n"
            "Add it to the GSTIN column and put the link where you found it in Notes.\n"
            "Leave the cell empty if you can't find it. Do not make up or guess a GSTIN. I will verify each one on the "
            "GST portal myself."
        ),
    },
    {
        "id": "outreach",
        "step": "Bonus",
        "title": "Write the first message",
        "why": "A short, specific first message gets replies. A vague \"send price list\" gets ignored.",
        "text": (
            "Write a short first WhatsApp message (under 80 words, simple English, polite) that I can send to these "
            "suppliers of {product} in {district}. In it, ask for:\n"
            "1. their catalogue or product photos with prices,\n"
            "2. minimum order quantity and price at 2-3 quantity slabs,\n"
            "3. whether they manufacture themselves or trade,\n"
            "4. sample cost and delivery time,\n"
            "5. their GSTIN.\n"
            "Also give me a Hindi version of the same message."
        ),
    },
]


# ── Audit checklist ───────────────────────────────────────────────────────────
# General checks apply to every supplier. Category packs are picked by HSN chapter.
GENERAL_CHECKS = [
    {
        "group": "Desk checks (do these before you call)",
        "items": [
            ["Check the GSTIN is real and active",
             "On the GST portal (services.gst.gov.in → Search Taxpayer → Search by GSTIN), status must be Active. "
             "Suspended or Cancelled means stop."],
            ["Match the legal name and address",
             "The legal or trade name and principal place of business on GST should match the name and address on their Google profile and quotes."],
            ["Check how old the GST registration is",
             "Registered for less than a year is not a deal-breaker, but go slower: smaller first order, more checks."],
            ["Check their return filing",
             "Use \"Show filing table\" on the GST portal. GSTR-1 and GSTR-3B should be filed regularly for the last 6–12 months. "
             "If they don't file, you can't claim input tax credit."],
            ["Check the taxpayer type",
             "A Composition taxpayer can't charge GST on the invoice, so you get no input tax credit. Fine for small buys, not for resale at scale."],
            ["Check they deal in your HSN",
             "The GST record lists their main goods/HSN and business activity (manufacturer, wholesaler, trader). It should match your product."],
            ["Verify the Udyam registration (if they give one)",
             "udyamregistration.gov.in → Verify Udyam. Check enterprise type and that the activity matches your product."],
            ["Company or LLP? Check MCA",
             "For a Pvt Ltd or LLP, check status Active and the directors on the MCA portal (View Company/LLP Master Data)."],
            ["Read the Google profile properly",
             "How long the profile has existed, rating, review count, the 1–2 star reviews (payment, quality, delay complaints), "
             "and real photos of the unit, not stock images."],
            ["Watch for fake review bursts",
             "Many 5-star reviews posted in the same few weeks, from accounts with no other reviews, is a red flag."],
            ["Search their name with \"fraud\" or \"complaint\"",
             "Google \"<business name> <city> fraud\" and \"… complaint\". Also look at their IndiaMART/JustDial listing age and GST-verified badge."],
        ],
    },
    {
        "group": "Call and video check",
        "items": [
            ["Manufacturer or trader?",
             "Ask directly. A trader isn't bad, but a manufacturer gives better price and control. Ask what they make in-house."],
            ["Get the basics in writing",
             "MOQ, price at 2–3 quantity slabs, monthly capacity, lead time, sample cost, and packaging."],
            ["Live video walk-through of the unit",
             "A live video call, not recorded clips. Ask to see machines or workers, raw material stock, and finished goods."],
            ["Ask for 2–3 current buyers and call them",
             "Ask them about quality consistency, delivery dates, and how problems were handled."],
            ["Ask for the product certificates (see your category below)",
             "Verify each certificate number on the issuing body's portal. Never trust a PDF or photo alone."],
        ],
    },
    {
        "group": "Sample and quality",
        "items": [
            ["Order a paid sample first",
             "Compare it against what was promised: size, weight, material, finish, packaging."],
            ["Write down the spec and keep a \"golden sample\"",
             "Agree on dimensions, material, finish, tolerance and packaging in writing. Keep the approved sample to compare bulk orders against."],
            ["Lab test if the claim matters",
             "For purity, material or safety claims (pure silk, food safety, metal grade), test at a NABL-accredited lab."],
        ],
    },
    {
        "group": "Payment and paperwork",
        "items": [
            ["Bank account name = GST legal name",
             "Check the account holder name (UPI name or a ₹1 penny-drop shows it). A personal account that doesn't match the firm is a red flag."],
            ["Never 100% advance to a new supplier",
             "Start with a small trial order. Use 30% advance and the balance against dispatch photos or delivery."],
            ["Get a proper proforma and tax invoice",
             "With GSTIN, HSN, rate and tax shown. For goods above ₹50,000 in value, the consignment needs an e-way bill."],
            ["Confirm they report your invoice",
             "After purchase, check your GSTR-2B shows their invoice. If not, they didn't file it and you lose the credit."],
            ["Agree delivery terms",
             "Ex-works or delivered? Who pays freight? Who bears transit damage? What happens with defective pieces?"],
        ],
    },
    {
        "group": "Before a big order",
        "items": [
            ["Visit in person (or send someone local)",
             "The address should match the GST record. See production happening, not just a showroom."],
            ["Do a second order before scaling",
             "One good order can be luck. Two consistent orders build trust."],
        ],
    },
]

RED_FLAGS = [
    "GSTIN suspended, cancelled, or the name doesn't match",
    "Refuses a live video call or a visit",
    "Only a mobile number, no address you can find on Maps",
    "Asks for 100% advance, or payment to a personal account",
    "Price far below everyone else",
    "Brand-new Google profile full of 5-star reviews",
    "Pushes you to decide fast (\"stock is ending today\")",
]

# Category packs. "ch" lists 2-digit chapters; "heads" lists 4-digit headings (more specific, matched first).
CATEGORY_CHECKS = [
    {
        "id": "food", "label": "Food & agri products", "ch": [f"{i:02d}" for i in range(1, 25)],
        "items": [
            ["FSSAI licence or registration",
             "Verify the 14-digit number on FoSCoS (foscos.fssai.gov.in → FBO search). It must be valid and cover this food category and the manufacturing address."],
            ["Lab report for the batch",
             "Ask for a recent NABL lab report: moisture, contaminants and pesticide residue, plus aflatoxin for nuts, spices and grains."],
            ["Label and packaging rules",
             "Packed goods need FSSAI logo and number, net quantity, MRP, batch, date of manufacture or best-before, and the manufacturer's address (Legal Metrology)."],
            ["Organic claim? Verify it",
             "Only NPOP (India Organic) or PGS-India certified products can be sold as organic. Check the certificate on the certifying body's database."],
            ["Shelf life and storage",
             "Ask the harvest or manufacture date and how stock is stored (cold storage, fumigation, pest control)."],
        ],
    },
    {"id": "fish", "label": "Fish & marine", "heads": ["03", "1603", "1604", "1605"], "items": [
        ["Cold chain",
         "Ask how product is frozen and stored (−18°C), how it's transported, and about ice-glazing percentage (affects real net weight)."],
        ["Export? MPEDA registration",
         "Exporters of marine products need MPEDA registration. EU and US buyers also need an EIC-approved processing plant."],
    ]},
    {"id": "spice", "label": "Spices", "heads": ["0904", "0905", "0906", "0907", "0908", "0909", "0910"], "items": [
        ["Spices Board registration (for export)",
         "Spice exporters need a Spices Board Certificate of Registration as Exporter (CRES). Ask for the number."],
        ["Adulteration check",
         "Ask for colour, starch and Sudan dye test results for chilli and turmeric powder."],
    ]},
    {"id": "teacoffee", "label": "Tea & coffee", "heads": ["0901", "0902"], "items": [
        ["Tea Board or Coffee Board registration",
         "Tea manufacturers and exporters register with the Tea Board, and coffee exporters with the Coffee Board. Darjeeling tea also carries a GI logo."],
    ]},
    {"id": "rice", "label": "Rice & grains", "heads": ["1006", "1001", "1005", "1008"], "items": [
        ["Grade and variety proof",
         "Ask for the grain length, broken percentage and moisture spec. For basmati or GI rice (Kalanamak, Matta, etc.), check GI authorised-user status."],
        ["Export? APEDA RCMC",
         "Exporters of rice and most agri products need APEDA registration (RCMC)."],
    ]},
    {"id": "alcohol", "label": "Alcoholic beverages", "heads": ["2203", "2204", "2205", "2206", "2207", "2208"], "items": [
        ["Excise licence",
         "Making, storing and selling alcohol needs a state excise licence. Ask for it and verify it with the state excise department."],
    ]},
    {
        "id": "pharma", "label": "Pharma, ayurvedic & cosmetics", "ch": ["30", "33"], "heads": ["1211", "3301"],
        "items": [
            ["Drug or AYUSH manufacturing licence",
             "Allopathic medicines need a state drug manufacturing licence. Ayurvedic, Siddha and Unani products need an AYUSH licence from the state licensing authority. The licence number must be printed on the label."],
            ["Cosmetics licence",
             "Cosmetics made in India need a manufacturing licence from the state authority under CDSCO rules. Check the number on the label."],
            ["GMP certificate",
             "Ask for a GMP (or WHO-GMP) certificate for the unit. For essential oils and herbs, ask for a GC-MS or purity report for the batch."],
        ],
    },
    {
        "id": "chem", "label": "Chemicals", "ch": ["28", "29", "31", "32", "34", "35", "36", "37", "38"],
        "items": [
            ["Safety data sheet (SDS/MSDS) and COA",
             "Ask for the SDS and a certificate of analysis for the batch you'll buy."],
            ["Pollution control consent",
             "The unit should hold a valid Consent to Operate from the state pollution control board."],
            ["Pesticides need CIB&RC registration",
             "Insecticides and pesticides (heading 3808) can only be made and sold with a CIB&RC registration number."],
            ["BIS where mandatory",
             "Some chemicals and fertilisers are under BIS Quality Control Orders. Check the product on the BIS website."],
        ],
    },
    {
        "id": "plastic", "label": "Plastic & rubber", "ch": ["39", "40"],
        "items": [
            ["Virgin or recycled material",
             "Ask what grade of raw material is used, and whether the product is virgin or recycled. Get it on the invoice."],
            ["Food-contact grade (if it touches food)",
             "Ask for a food-grade or migration test certificate for containers, bottles or packaging."],
            ["Plastic packaging EPR registration",
             "Plastic packaging producers and brand owners need EPR registration on the CPCB portal. Check if it applies to your buy."],
            ["BIS where mandatory",
             "Tyres, some pipes and other rubber/plastic items need BIS (ISI) marking. Check the licence on the BIS site."],
        ],
    },
    {
        "id": "leather", "label": "Leather goods & footwear", "ch": ["41", "42", "43", "64"],
        "items": [
            ["Genuine leather or PU?",
             "Ask the leather type (cow, buffalo, goat, sheep) and tanning (chrome or vegetable). Check the sample: cut edge and smell."],
            ["Footwear needs BIS",
             "Many types of footwear sold in India must carry BIS marking under the footwear Quality Control Order. Check the supplier's BIS licence."],
            ["Export: chemical tests",
             "EU and US buyers ask for chrome VI and azo-dye test reports. Ask whether the supplier has done these before."],
            ["Tannery consent",
             "If they tan in-house, the unit needs pollution board consent. This matters in clusters like Kanpur and Vellore."],
        ],
    },
    {
        "id": "wood", "label": "Wood, bamboo, cane & paper", "ch": ["44", "45", "46", "47", "48", "49"], "heads": ["9403", "9401"],
        "items": [
            ["Wood species and seasoning",
             "Ask for the wood type, and whether it is kiln-dried, with moisture content below 12–14%. Unseasoned wood cracks and warps after delivery."],
            ["Legal source of timber",
             "For timber such as teak, sheesham or sandalwood, ask for a transit pass or purchase bill showing a legal source."],
            ["Treatment and finish",
             "Anti-termite or borer treatment, and a food-safe finish for kitchen or serving items."],
            ["Export: fumigation and ISPM-15",
             "Wooden goods and wooden packaging need fumigation and an ISPM-15 mark for most export markets."],
            ["Furniture: check BIS",
             "Some furniture now falls under BIS Quality Control Orders. Check whether your item is covered before buying at scale."],
        ],
    },
    {
        "id": "textile", "label": "Textiles, handloom & apparel", "ch": [f"{i}" for i in range(50, 64)],
        "items": [
            ["Fibre composition",
             "Get the exact blend (e.g. 100% cotton, silk-cotton, viscose) in writing. Burn-test the sample or lab-test it."],
            ["Pure silk? Look for Silk Mark",
             "Real silk sellers can be Silk Mark authorised users (Silk Mark Organisation of India). Ask for the Silk Mark label or test the sample."],
            ["Handloom claim? Check the mark",
             "Real handloom carries a Handloom Mark or India Handloom Brand label. Powerloom copies are common in saree clusters."],
            ["GI product? Check the authorised user",
             "For GI products (Banarasi, Pochampally, Chanderi, Pashmina, Kota Doria etc.), check that the maker is a registered authorised user in the GI registry."],
            ["Quality specs",
             "GSM or thread count, colour fastness (ask for a wash test), shrinkage, and size chart with tolerance."],
            ["Export: azo-free dyes",
             "Export buyers often ask for azo-free or OEKO-TEX style test reports. Ask if they have one."],
        ],
    },
    {
        "id": "carpet", "label": "Carpets & rugs", "heads": ["5701", "5702", "5703", "5704", "5705"], "items": [
            ["Hand-knotted vs tufted vs machine",
             "Ask the construction and knots per square inch. Hand-knotted is priced very differently from tufted."],
            ["Kaleen / child-labour-free label",
             "Export buyers often need a child-labour-free certification (e.g. GoodWeave or Kaleen). Ask if the supplier is covered."],
        ],
    },
    {
        "id": "stone", "label": "Stone, ceramics & glass", "ch": ["25", "68", "69", "70"],
        "items": [
            ["Check a slab or tile sample",
             "Check thickness, finish, colour variation between batches, and water absorption for tiles."],
            ["Legal mining source (stone)",
             "Stone suppliers should have royalty paid or mining lease papers. Illegal stone can be seized in transit."],
            ["Food-safe glaze (pottery)",
             "Pottery and terracotta used for food or water must use a lead-free glaze. Ask for a test, especially for export."],
            ["BIS where mandatory",
             "Ceramic tiles, sanitary ware and some glass products need BIS marking. Check the licence."],
            ["Breakage packing",
             "Agree on how fragile goods are packed and who pays for breakage in transit before you order."],
        ],
    },
    {
        "id": "jewel", "label": "Jewellery, gems & precious metals", "ch": ["71"],
        "items": [
            ["Gold jewellery must be hallmarked",
             "Gold jewellery must carry a BIS hallmark with a 6-digit HUID. Check each HUID on the BIS CARE app."],
            ["Silver hallmarking",
             "Silver hallmarking with HUID is available but voluntary. Ask for it anyway, or test the purity yourself."],
            ["Gem certificates",
             "For stones above a small value, ask for a lab certificate (e.g. GJEPC GTL, IGI, GII), and check it on the lab's website."],
            ["Imitation jewellery: metal and plating",
             "Ask the base metal and plating thickness, and whether it's lead- and nickel-free (matters for export and skin allergies)."],
        ],
    },
    {
        "id": "metal", "label": "Metal products & handicrafts", "ch": [f"{i}" for i in range(72, 84)],
        "items": [
            ["Metal grade",
             "Get the exact alloy in writing: brass ratio, stainless 304 vs 202, aluminium grade. Test with a magnet or at a lab if price depends on it."],
            ["Food-contact safety",
             "Utensils for cooking or serving should be lead-free. Brass and copper used with food need tinning (kalai) or a food-safe coating."],
            ["Weight and finish tolerance",
             "Agree the weight per piece (many metal crafts are priced by weight), lacquer or antique finish, and how much variation is acceptable."],
            ["BIS where mandatory",
             "Many steel products, pressure cookers and some utensils need BIS (ISI) marking. Check the product on the BIS site."],
        ],
    },
    {
        "id": "machine", "label": "Machinery & electricals", "ch": ["84", "85"],
        "items": [
            ["BIS / ISI or CRS registration",
             "Many electrical and electronic items (and some machinery) need BIS certification or CRS registration. Check the licence or R-number on the BIS site."],
            ["Test certificate and warranty",
             "Ask for a test or inspection report for your unit, warranty terms in writing, and who honours the warranty."],
            ["Spares and service",
             "Who supplies spare parts, and how quickly? Is there a service person near you?"],
            ["Energy rating (BEE)",
             "Products like motors, pumps and appliances may need a BEE star label. Check if yours is covered."],
        ],
    },
    {
        "id": "auto", "label": "Auto parts & vehicles", "ch": ["86", "87", "88", "89"],
        "items": [
            ["OEM-grade quality systems",
             "If you'll supply to OEMs, ask for IATF 16949 or ISO 9001 certification."],
            ["BIS / AIS where mandatory",
             "Tyres, helmets, safety glass, brake parts and some other auto components need BIS marking or AIS approval. Check if your part is covered."],
            ["Drawings and tolerances",
             "Share a drawing or reference part, and get an inspection report (dimensions, hardness) with the first lot."],
        ],
    },
    {
        "id": "instrument", "label": "Instruments & musical instruments", "ch": ["90", "91", "92"],
        "items": [
            ["Calibration certificate",
             "Measuring instruments should come with a calibration certificate, preferably from an NABL lab."],
            ["Medical devices need CDSCO registration",
             "Medical devices need a CDSCO licence or registration. Check the number on the label."],
            ["Musical instruments: seasoning and tuning",
             "Ask about wood seasoning and the skin or string quality, and play or record a sample before bulk."],
        ],
    },
    {
        "id": "toys", "label": "Toys, sports & misc. goods", "ch": ["94", "95", "96"],
        "items": [
            ["Toys must have BIS",
             "All toys sold in India must carry the BIS (ISI) mark under the Toys Quality Control Order, and that includes wooden and handmade toys. Craft toys can use a special artisan scheme, so ask the supplier how they comply."],
            ["Safe paints",
             "Paints on toys, kids' items and kitchenware should be non-toxic and lead-free. Ask for a test report."],
            ["Sports goods specs",
             "Ask for the material, weight and size spec, and any federation approval if you sell for competitions."],
        ],
    },
    {
        "id": "art", "label": "Art & handicrafts", "ch": ["97"], "heads": ["4420", "4602", "6913", "8306", "9601", "9701"],
        "items": [
            ["Check the artisan card",
             "Real artisans often hold an Artisan Identity Card (Pehchan) from the Development Commissioner (Handicrafts). Ask for it. It also helps you get schemes and exhibitions."],
            ["GI craft? Check the authorised user",
             "For GI crafts (Madhubani, Channapatna toys, Moradabad brass, Pattachitra etc.), check the maker is a registered GI authorised user."],
            ["Handmade or machine-made?",
             "Ask for a video of the making process. Prices and story value depend on it."],
            ["Consistency across pieces",
             "Handmade pieces vary. Agree on how much variation in size and colour is acceptable, and approve a set of photos before dispatch."],
            ["Export: EPCH registration",
             "Handicraft exporters usually register with EPCH (Export Promotion Council for Handicrafts) for RCMC and fair participation."],
        ],
    },
]


def checklist_data():
    return {"general": GENERAL_CHECKS, "redFlags": RED_FLAGS, "categories": CATEGORY_CHECKS}


def categories_for(code):
    """Category packs for an HSN code: specific heading packs first, then chapter packs."""
    code = str(code)
    out = []
    for c in CATEGORY_CHECKS:
        heads = c.get("heads", [])
        if any(code.startswith(h) for h in heads):
            out.append(c)
    for c in CATEGORY_CHECKS:
        if c in out:
            continue
        if code[:2] in c.get("ch", []):
            out.append(c)
    return out


# ── Page ──────────────────────────────────────────────────────────────────────
def build_page(head, nav, footer, esc, p):
    cfg = {
        "leadEndpoint": LEAD_ENDPOINT,
        "bookCallUrl": BOOK_CALL_URL,
        "hsnUrl": p(TOOL_PATH + "hsn.json"),
        "districtsUrl": p(TOOL_PATH + "districts.json"),
        "prompts": PROMPTS,
        "checklist": checklist_data(),
    }
    title = "Supplier Finder by HSN Code: AI Prompts + Supplier Audit Checklist | KidharMilega"
    desc = ("Enter your 8-digit HSN code and district. Get copy-paste AI prompts to find local manufacturers, "
            "pull their Google Maps profiles, and a checklist to audit each supplier before you pay.")
    ld = {
        "@context": "https://schema.org", "@type": "WebApplication", "name": "KidharMilega Supplier Finder",
        "url": "https://kidharmilega.in" + TOOL_PATH, "applicationCategory": "BusinessApplication",
        "operatingSystem": "Any", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "INR"},
        "description": desc,
    }
    extra = (f'<link rel="stylesheet" href="{p(TOOL_PATH + "style.css")}?v={_asset_version()}">'
             f'<script type="application/ld+json">{json.dumps(ld)}</script>')
    return head(title, desc, TOOL_PATH, extra_head=extra) + nav("tools") + f'''
<main class="sf"><div class="container">
  <header class="page-header sf-header">
    <div class="section-label">Free tool · Supplier Finder</div>
    <h1 class="page-header-title">Find real local suppliers<br><em>for your HSN code.</em></h1>
    <p class="page-header-sub">Go past IndiaMART. Get the exact AI prompts to list manufacturers in any district, pull their Google Maps profiles (phone, address, reviews), and a checklist to audit each one before you pay.</p>
    <ol class="sf-how" aria-label="How it works">
      <li><span>1</span>Pick your HSN code</li>
      <li><span>2</span>Pick the district</li>
      <li><span>3</span>Copy the prompts into Claude or ChatGPT</li>
      <li><span>4</span>Audit the suppliers with the checklist</li>
    </ol>
  </header>

  <form class="sf-form" id="sfForm" autocomplete="off" novalidate>
    <section class="sf-step" aria-labelledby="sfStep1">
      <h2 class="sf-step__title" id="sfStep1"><span class="sf-step__num">1</span>What do you want to buy?</h2>
      <label class="sf-label" for="sfHsn">HSN code or product name</label>
      <div class="sf-combo">
        <input class="sf-input" id="sfHsn" type="text" inputmode="search" placeholder="e.g. 63022110 or cotton bedsheet" aria-autocomplete="list" aria-controls="sfHsnList" aria-expanded="false" role="combobox">
        <ul class="sf-list" id="sfHsnList" role="listbox" hidden></ul>
      </div>
      <p class="sf-hint" id="sfHsnStatus">Loading 12,600+ HSN codes…</p>
      <div class="sf-picked" id="sfPicked" hidden></div>
      <div id="sfProductWrap" hidden>
        <label class="sf-label" for="sfProduct">How your market says it <span class="sf-opt">(edit this)</span></label>
        <input class="sf-input" id="sfProduct" type="text" maxlength="120">
        <p class="sf-hint">The official HSN name is often clumsy. Write the product the way buyers and sellers say it, like "cotton bedsheets" or "brass diyas". This goes into your prompts.</p>
      </div>
    </section>

    <section class="sf-step" aria-labelledby="sfStep2">
      <h2 class="sf-step__title" id="sfStep2"><span class="sf-step__num">2</span>Where do you want suppliers?</h2>
      <div class="sf-row">
        <div>
          <label class="sf-label" for="sfState">State</label>
          <select class="sf-input" id="sfState"><option value="">Select state</option></select>
        </div>
        <div>
          <label class="sf-label" for="sfDistrict">District or city</label>
          <input class="sf-input" id="sfDistrict" type="text" list="sfDistrictList" placeholder="e.g. Panipat">
          <datalist id="sfDistrictList"></datalist>
        </div>
      </div>
      <div class="sf-suggest" id="sfSuggest" hidden>
        <div class="sf-suggest__label">ODOP districts known for this product. Tap to use one:</div>
        <div class="sf-chips" id="sfChips"></div>
      </div>
    </section>

    <div class="sf-submit">
      <button class="btn btn-primary btn-lg" type="submit" id="sfGo">Get my prompts &amp; checklist <span class="btn__arrow" aria-hidden="true">&rarr;</span></button>
      <p class="sf-error" id="sfError" role="alert"></p>
    </div>
  </form>

  <div class="sf-gate" id="sfGate" hidden>
    <div class="sf-gate__card" role="dialog" aria-modal="true" aria-labelledby="sfGateTitle">
      <button class="sf-gate__close" type="button" id="sfGateClose" aria-label="Close">&times;</button>
      <h2 id="sfGateTitle">Where should we send updates?</h2>
      <p>Your prompts and checklist open right after this. We'll only email you useful sourcing tips.</p>
      <form id="sfGateForm" novalidate>
        <label class="sf-label" for="sfEmail">Email</label>
        <input class="sf-input" id="sfEmail" type="email" inputmode="email" autocomplete="email" required placeholder="you@example.com">
        <label class="sf-label" for="sfPhone">WhatsApp number <span class="sf-opt">(optional)</span></label>
        <input class="sf-input" id="sfPhone" type="tel" inputmode="tel" autocomplete="tel" placeholder="10-digit mobile">
        <p class="sf-error" id="sfGateError" role="alert"></p>
        <button class="btn btn-primary" type="submit" style="width:100%">Show my prompts</button>
        <p class="sf-fine">By continuing you agree to our <a href="{p('/terms-of-service/')}">terms</a>. No spam.</p>
      </form>
    </div>
  </div>

  <section class="sf-results" id="sfResults" hidden aria-live="polite">
    <div class="sf-results__head">
      <div class="section-label">Your sourcing kit</div>
      <h2 class="section-title" id="sfResultsTitle"></h2>
      <p class="section-sub" id="sfResultsSub"></p>
    </div>

    <div class="sf-tip">
      <strong>Before you start:</strong> open Claude (claude.ai) or ChatGPT, turn on web search, and paste the prompts one by one <em>in the same chat</em>. Each prompt builds on the answer before it.
    </div>

    <div class="sf-prompts" id="sfPrompts"></div>

    <div class="sf-audit" id="sfAudit">
      <div class="sf-audit__head">
        <h2 class="section-title">Supplier audit checklist</h2>
        <p class="section-sub">Run these checks for every supplier on your shortlist before you pay a single rupee. Ticks are saved in this browser.</p>
        <button class="btn btn-ghost btn-sm" type="button" id="sfPrint">Print / save as PDF</button>
      </div>
      <div id="sfChecklist"></div>
    </div>

    <aside class="sf-help">
      <div>
        <strong>Stuck, or want help auditing a supplier?</strong>
        <p>Book a 1:1 call and we'll go through your shortlist together.</p>
      </div>
      <a class="btn btn-cyan" href="{esc(BOOK_CALL_URL)}" target="_blank" rel="noopener" id="sfBook">Book a call</a>
    </aside>
  </section>

  <noscript><p class="sf-error">This tool needs JavaScript turned on.</p></noscript>
</div></main>
<script>window.SF_CONFIG={json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")};</script>
<script src="{p(TOOL_PATH + "app.js")}?v={_asset_version()}" defer></script>
''' + footer() + "</body></html>"


def build_tools_index(head, nav, footer, esc, p):
    return head("Free Tools for Small Business Founders | KidharMilega",
                "Free tools for first-time founders in India: find local suppliers by HSN code and audit them before you buy.",
                "/tools/") + nav("tools") + f'''
<main><div class="container">
  <div class="page-header">
    <div class="section-label">Free tools</div>
    <h1 class="page-header-title">Tools that do<br><em>the boring part.</em></h1>
    <p class="page-header-sub">Built for first-time founders sourcing and selling from small-town India.</p>
  </div>
  <div class="grid-2">
    <a class="card" href="{p(TOOL_PATH)}" style="display:block">
      <div class="section-label">Sourcing</div>
      <h2 style="font-size:1.4rem;margin-bottom:8px">Supplier Finder by HSN code</h2>
      <p>Copy-paste AI prompts to find local manufacturers in any district, pull their Google Maps profiles, and a checklist to audit each supplier.</p>
      <p style="margin-top:14px;font-weight:600;color:var(--color-link)">Open the tool &rarr;</p>
    </a>
  </div>
</div></main>''' + footer() + "</body></html>"


_VERSION = None


def _asset_version():
    global _VERSION
    if _VERSION is None:
        import hashlib
        h = hashlib.sha1()
        for f in ("app.js", "style.css"):
            h.update((SRC_DIR / f).read_bytes())
        h.update(json.dumps([PROMPTS, checklist_data(), LEAD_ENDPOINT, BOOK_CALL_URL]).encode())
        _VERSION = h.hexdigest()[:10]
    return _VERSION


def write_supplier_finder(dist_dir, districts, product_page_slug, head, nav, footer, esc, p):
    import sys
    sys.path.insert(0, str(SRC_DIR))
    from hsn_compile import compile_hsn

    out = Path(dist_dir) / "tools" / "supplier-finder"
    out.mkdir(parents=True, exist_ok=True)
    hsn = compile_hsn()
    (out / "hsn.json").write_text(json.dumps(hsn, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    dj = build_districts_json(districts, product_page_slug)
    (out / "districts.json").write_text(json.dumps(dj, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    for f in ("app.js", "style.css"):
        shutil.copy(SRC_DIR / f, out / f)
    (out / "index.html").write_text(build_page(head, nav, footer, esc, p), encoding="utf-8")
    (Path(dist_dir) / "tools" / "index.html").write_text(build_tools_index(head, nav, footer, esc, p), encoding="utf-8")
    mapped = sum(1 for d in dj if d["h"])
    return len(hsn["t"]), mapped, len(dj)
