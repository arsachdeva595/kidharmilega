"""
Local store: shipments, contacts, lookups and run snapshots in one SQLite file.

Shipments come in as CSV files you collected yourself (a vendor export, a
licensed data download, or rows copied by hand). Column names are matched
loosely, so most bill-of-lading exports load without editing.
"""

import csv, hashlib, json, re, sqlite3
from datetime import datetime, date

from . import DB_FILE, ensure_dirs

SCHEMA = """
CREATE TABLE IF NOT EXISTS shipments (
    id INTEGER PRIMARY KEY,
    fingerprint TEXT UNIQUE,
    source TEXT, file TEXT,
    ship_date TEXT,
    shipper TEXT, shipper_address TEXT, shipper_country TEXT,
    consignee TEXT, consignee_address TEXT, consignee_city TEXT,
    consignee_state TEXT, consignee_country TEXT,
    description TEXT, hs_code TEXT,
    weight_kg REAL, quantity TEXT, bol TEXT,
    imported_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_ship_consignee ON shipments(consignee);
CREATE INDEX IF NOT EXISTS ix_ship_shipper   ON shipments(shipper);

CREATE TABLE IF NOT EXISTS contacts (
    company_key TEXT PRIMARY KEY,
    name TEXT, website TEXT, emails TEXT, phones TEXT, socials TEXT,
    decision_maker TEXT, sources TEXT, notes TEXT, enriched_at TEXT
);

CREATE TABLE IF NOT EXISTS lookups (
    company_key TEXT, kind TEXT, looked_up_at TEXT,
    PRIMARY KEY (company_key, kind)
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY, profile TEXT, created_at TEXT, summary TEXT
);
CREATE TABLE IF NOT EXISTS run_leads (
    run_id INTEGER, company_key TEXT, name TEXT, score INTEGER,
    last_date TEXT, matching_shipments INTEGER, data TEXT
);
"""

# Our field -> header spellings seen in common exports (compared lowercase, letters/digits only)
COLUMN_ALIASES = {
    "ship_date":         ["date", "arrivaldate", "arrival", "shipmentdate", "billofladingdate", "bldate", "actualarrivaldate", "estimatedarrivaldate"],
    "shipper":           ["shipper", "shippername", "supplier", "suppliername", "exporter", "exportername", "seller"],
    "shipper_address":   ["shipperaddress", "supplieraddress", "exporteraddress"],
    "shipper_country":   ["shippercountry", "suppliercountry", "exportercountry", "countryoforigin", "origincountry", "country"],
    "consignee":         ["consignee", "consigneename", "buyer", "buyername", "importer", "importername", "customer", "company"],
    "consignee_address": ["consigneeaddress", "buyeraddress", "importeraddress"],
    "consignee_city":    ["consigneecity", "buyercity", "importercity", "city"],
    "consignee_state":   ["consigneestate", "buyerstate", "importerstate", "state"],
    "consignee_country": ["consigneecountry", "buyercountry", "importercountry", "destinationcountry"],
    "description":       ["description", "productdescription", "goodsdescription", "commodity", "product", "cargodescription", "itemdescription"],
    "hs_code":           ["hscode", "hs", "hsn", "hsncode", "htscode", "hts", "harmonizedcode", "tariffcode"],
    "weight_kg":         ["weight", "weightkg", "grossweight", "grossweightkg"],
    "quantity":          ["quantity", "qty", "quantityunit", "packages"],
    "bol":               ["bol", "billofladingnumber", "billoflading", "blnumber", "bolnumber", "masterbol", "housebol"],
}

US_STATES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY "
                "NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC PR".split())

DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%Y", "%d %b %Y", "%b %d, %Y",
                "%B %d, %Y", "%d/%m/%Y", "%Y%m%d"]


def connect():
    ensure_dirs()
    db = sqlite3.connect(DB_FILE)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def _norm_header(h):
    return re.sub(r"[^a-z0-9]", "", (h or "").lower())


def map_columns(headers):
    """Return {our_field: csv_header} for the headers we recognise."""
    normed = {_norm_header(h): h for h in headers}
    mapping = {}
    for field, aliases in COLUMN_ALIASES.items():
        for a in aliases:
            if a in normed and normed[a] not in mapping.values():
                mapping[field] = normed[a]
                break
    return mapping


def parse_date(raw):
    raw = (raw or "").strip()
    if not raw:
        return ""
    raw = raw.split("T")[0].split(" 00:")[0].strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def us_state_from(address):
    """Pull a 2-letter US state out of an address like '..., LANCASTER, PA 17601'."""
    m = re.search(r"\b([A-Z]{2})[\s,]+\d{5}(?:-\d{4})?\b", (address or "").upper())
    if m and m.group(1) in US_STATES:
        return m.group(1)
    return ""


def _country(value, address, default=""):
    v = (value or "").strip().upper()
    if v in ("IN", "IND"):
        return "INDIA"
    if v in ("US", "USA", "UNITED STATES OF AMERICA", "U.S.A."):
        return "UNITED STATES"
    if v:
        return v
    addr = (address or "").upper()
    if re.search(r"\bINDIA\b", addr):
        return "INDIA"
    if us_state_from(addr):
        return "UNITED STATES"
    return default


def _fingerprint(row):
    key = "|".join(str(row.get(k, "")).strip().upper() for k in
                   ("bol", "ship_date", "shipper", "consignee", "description", "hs_code"))
    return hashlib.sha1(key.encode()).hexdigest()


def import_csv(db, path, source="manual", default_market="UNITED STATES", default_origin=""):
    """Load one CSV. Returns (added, skipped_duplicates, unmapped_columns)."""
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        mapping = map_columns(headers)
        if "consignee" not in mapping or ("description" not in mapping and "hs_code" not in mapping):
            raise SystemExit(f"{path}: need at least a consignee/buyer column and a description or HS code column.\n"
                             f"  Headers found: {headers}")
        added = skipped = 0
        now = datetime.now().isoformat(timespec="seconds")
        for raw in reader:
            row = {field: (raw.get(col) or "").strip() for field, col in mapping.items()}
            if not row.get("consignee"):
                continue
            row["ship_date"] = parse_date(row.get("ship_date"))
            row["shipper_country"] = _country(row.get("shipper_country"), row.get("shipper_address"), default_origin)
            row["consignee_country"] = _country(row.get("consignee_country"), row.get("consignee_address"), default_market)
            if not row.get("consignee_state"):
                row["consignee_state"] = us_state_from(row.get("consignee_address"))
            try:
                row["weight_kg"] = float(re.sub(r"[^\d.]", "", row.get("weight_kg", "")) or 0)
            except ValueError:
                row["weight_kg"] = 0.0
            row["hs_code"] = re.sub(r"[^\d,; ]", "", row.get("hs_code", ""))
            fp = _fingerprint(row)
            cur = db.execute(
                """INSERT OR IGNORE INTO shipments (fingerprint, source, file, ship_date, shipper, shipper_address,
                   shipper_country, consignee, consignee_address, consignee_city, consignee_state, consignee_country,
                   description, hs_code, weight_kg, quantity, bol, imported_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (fp, source, str(path), row["ship_date"], row.get("shipper", ""), row.get("shipper_address", ""),
                 row["shipper_country"], row["consignee"], row.get("consignee_address", ""),
                 row.get("consignee_city", ""), row["consignee_state"], row["consignee_country"],
                 row.get("description", ""), row["hs_code"], row["weight_kg"], row.get("quantity", ""),
                 row.get("bol", ""), now))
            if cur.rowcount:
                added += 1
            else:
                skipped += 1
        db.commit()
    unmapped = [h for h in headers if h not in mapping.values()]
    return added, skipped, mapping, unmapped


def mark_lookup(db, company_key, kind):
    db.execute("INSERT OR REPLACE INTO lookups VALUES (?,?,?)",
               (company_key, kind, date.today().isoformat()))
    db.commit()


def looked_up(db):
    return {(r["company_key"], r["kind"]) for r in db.execute("SELECT company_key, kind FROM lookups")}


def get_contacts(db):
    out = {}
    for r in db.execute("SELECT * FROM contacts"):
        d = dict(r)
        for k in ("emails", "phones", "socials", "sources"):
            d[k] = json.loads(d[k]) if d.get(k) else []
        out[d["company_key"]] = d
    return out


def save_contact(db, company_key, name, **fields):
    existing = get_contacts(db).get(company_key, {})
    merged = {**existing, **{k: v for k, v in fields.items() if v not in (None, "", [])}}
    db.execute(
        """INSERT OR REPLACE INTO contacts (company_key, name, website, emails, phones, socials,
           decision_maker, sources, notes, enriched_at) VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (company_key, name, merged.get("website", ""),
         json.dumps(merged.get("emails", [])), json.dumps(merged.get("phones", [])),
         json.dumps(merged.get("socials", [])), merged.get("decision_maker", ""),
         json.dumps(merged.get("sources", [])), merged.get("notes", ""),
         merged.get("enriched_at", date.today().isoformat())))
    db.commit()
