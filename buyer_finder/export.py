"""F7 — CSV and XLSX export of a lead list (columns follow the PRD "Buyer list output" table)."""

import csv
from datetime import date

from . import EXPORTS_DIR, ensure_dirs

COLUMNS = [
    ("Score", "score"), ("Route", "route"), ("Status", "status"), ("Company", "name"),
    ("Buyer type", "buyer_type"), ("City", "city"), ("State", "state"), ("Address", "address"),
    ("Proof level", "proof_level"), ("Proof line", "proof_line"), ("Proof ref (BOL / date / source)", "proof_ref"),
    ("Last matching shipment", "last_date"), ("First matching shipment", "first_date"),
    ("Matching shipments", "matching_total"), ("Matching, last 12 months", "matching_12m"),
    ("India shipments, all", "india_total"), ("India shipments, last 12 months", "india_12m"),
    ("Indian suppliers (this product)", "suppliers"), ("All Indian suppliers", "all_suppliers"),
    ("Styles they buy", "tags"), ("Pitch angle", "pitch"),
    ("Website", "website"), ("Emails", "emails"), ("Phones", "phones"), ("Socials", "socials"),
    ("Decision maker", "decision_maker"), ("Contact sources", "contact_sources"),
    ("Also known as", "aliases"), ("Snowball hop", "hop"), ("Score parts", "score_parts"),
]


def _cell(v):
    if isinstance(v, list):
        return "; ".join(str(x) for x in v)
    if isinstance(v, dict):
        return ", ".join(f"{k} {x}" for k, x in v.items())
    return "" if v is None else v


def rows(leads):
    return [[_cell(l.get(key)) for _, key in COLUMNS] for l in leads]


def export(name, leads, fmt="csv"):
    ensure_dirs()
    stem = EXPORTS_DIR / f"{name}-{date.today().isoformat()}"
    header = [h for h, _ in COLUMNS]
    if fmt == "xlsx":
        from openpyxl import Workbook
        from openpyxl.styles import Font
        wb = Workbook()
        ws = wb.active
        ws.title = "Buyers"
        ws.append(header)
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows(leads):
            ws.append(r)
        ws.freeze_panes = "E2"
        ws.auto_filter.ref = ws.dimensions
        for col, width in zip("ABCDEFGHIJ", (7, 13, 15, 32, 20, 16, 7, 36, 11, 60)):
            ws.column_dimensions[col].width = width
        path = stem.with_suffix(".xlsx")
        wb.save(path)
        return path
    path = stem.with_suffix(".csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows(leads))
    return path
