"""
Buyer Finder CLI.

  python3 -m buyer_finder map 48201000 --desc "leather journal" --name journals
  python3 -m buyer_finder import ~/Downloads/shipments/*.csv --source importyeti-manual
  python3 -m buyer_finder search journals
  python3 -m buyer_finder next journals
  python3 -m buyer_finder enrich journals --top 20
  python3 -m buyer_finder export journals --xlsx
  python3 -m buyer_finder recheck journals
"""

import argparse, json, sys
from datetime import date

from . import hsn, store, engine, export as exporter


def _as_of(args):
    return date.fromisoformat(args.as_of) if getattr(args, "as_of", None) else None


def _run(db, name, args):
    profile = hsn.load_profile(name)
    return profile, engine.find_buyers(db, profile, store.get_contacts(db), today=_as_of(args))


def _print_summary(s):
    print(f"\n{s['profile']} → {s['market']} buyers")
    print(f"  {s['records_in_market']} India→{s['market']} records in store, "
          f"{sum(s['dropped'].values())} dropped as forwarders/intake")
    print(f"  {s['seed_exporters']} seed exporters, {s['exporters_reached']} exporters after snowball")
    print(f"  {s['buyers']} buyers: {s['proof_product']} with product named on the BOL, {s['proof_hs_only']} HS-code only")
    print(f"  {s['outreach_now']} outreach now, {s['nurture']} nurture, {s['verified']} verified (fresh proof + contact)\n")


def _print_table(leads, top):
    print(f"{'#':>3} {'Score':>5}  {'Route':<12} {'Company':<34} {'State':<5} {'Last':<10} {'Ship':>4}  Proof")
    for i, l in enumerate(leads[:top], 1):
        print(f"{i:>3} {l['score']:>5}  {l['route']:<12} {l['name'][:34]:<34} {l['state'] or '':<5} "
              f"{l['last_date'] or '—':<10} {l['matching_total']:>4}  {l['proof_line'][:60]}")
    if len(leads) > top:
        print(f"    … {len(leads) - top} more (use --top or export)")


def _save_run(db, name, result):
    store.save_run(db, name, result)


def _find_lead(result, company):
    key = engine.company_key(company)
    for l in result["leads"]:
        if l["company_key"] == key or company.lower() in l["name"].lower():
            return l
    raise SystemExit(f"No buyer matching '{company}' in this profile's results.")


def cmd_map(db, args):
    profile = hsn.map_hsn(args.code or "", args.desc or "")
    if args.seed:
        profile["seeds"] = args.seed
    name = args.name or (args.code or args.desc)
    path = hsn.save_profile(name, profile)
    print(json.dumps(profile, indent=2, ensure_ascii=False))
    print(f"\nSaved profile '{name}' → {path}")
    print("Check the codes and keywords, edit that file if needed, then run: "
          f"python3 -m buyer_finder search {name}")


def cmd_import(db, args):
    total = 0
    for path in args.files:
        added, dup, mapping, unmapped = store.import_csv(
            db, path, source=args.source, default_market=engine.MARKETS.get(args.market, args.market),
            default_origin="INDIA" if args.origin_india else "")
        total += added
        print(f"{path}: +{added} shipments ({dup} already in store)")
        if args.verbose:
            print(f"  columns: {mapping}\n  ignored: {unmapped}")
    for name in args.looked_up_exporter or []:
        store.mark_lookup(db, engine.company_key(name), "exporter")
    for name in args.looked_up_buyer or []:
        store.mark_lookup(db, engine.company_key(name), "buyer")
    n = db.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
    print(f"Imported {total} new shipments; {n} in store.")


def cmd_search(db, args):
    _, result = _run(db, args.profile, args)
    _print_summary(result["summary"])
    _print_table(result["leads"], args.top)
    _save_run(db, args.profile, result)


def cmd_show(db, args):
    _, result = _run(db, args.profile, args)
    print(json.dumps(_find_lead(result, args.company), indent=2, ensure_ascii=False, default=str))


def cmd_next(db, args):
    _, result = _run(db, args.profile, args)
    exps, buys = engine.next_lookups(result, store.looked_up(db), args.top)
    print("Exporters to look up next (pull their US customers):")
    for k, e in exps:
        print(f"  hop {e['hop']}  {e['name'][:48]:<48} {e['buyers']} known buyers, {e['records']} records")
    print("\nBuyers to look up next (pull their other Indian suppliers):")
    for l in buys:
        print(f"  {l['score']:>3}  {l['name'][:48]:<48} {l['supplier_count']} suppliers known")
    print("\nAfter importing a lookup, mark it done: python3 -m buyer_finder done --exporter \"NAME\" (or --buyer)")


def cmd_done(db, args):
    for name in args.exporter or []:
        store.mark_lookup(db, engine.company_key(name), "exporter")
    for name in args.buyer or []:
        store.mark_lookup(db, engine.company_key(name), "buyer")
    print("Marked.")


def cmd_enrich(db, args):
    from . import enrich
    _, result = _run(db, args.profile, args)
    contacts = store.get_contacts(db)
    todo = [l for l in result["leads"] if args.force or l["company_key"] not in contacts][:args.top]
    print(f"Enriching {len(todo)} buyers…")
    for l in todo:
        found = enrich.enrich_lead(l, delay=args.delay)
        store.save_contact(db, l["company_key"], l["name"], **found)
        print(f"  {l['name'][:40]:<40} {found.get('website', '—'):<34} {', '.join(found.get('emails', [])[:2])}")


def cmd_contact(db, args):
    _, result = _run(db, args.profile, args)
    lead = _find_lead(result, args.company)
    existing = store.get_contacts(db).get(lead["company_key"], {})
    store.save_contact(db, lead["company_key"], lead["name"],
                       website=args.website,
                       emails=sorted(set(existing.get("emails", []) + (args.email or []))),
                       phones=sorted(set(existing.get("phones", []) + (args.phone or []))),
                       decision_maker=args.decision_maker, notes=args.notes,
                       sources=existing.get("sources", []) + ["manual"])
    print(f"Saved contact for {lead['name']}.")


def cmd_export(db, args):
    _, result = _run(db, args.profile, args)
    leads = result["leads"] if args.all else [l for l in result["leads"] if l["status"] != "stale (>36 months)"]
    path = exporter.export(hsn.profile_path(args.profile).stem, leads, "xlsx" if args.xlsx else "csv")
    print(f"Wrote {len(leads)} buyers → {path}")


def cmd_recheck(db, args):
    last = db.execute("SELECT id, created_at FROM runs WHERE profile = ? ORDER BY id DESC LIMIT 1",
                      (args.profile,)).fetchone()
    _, result = _run(db, args.profile, args)
    if not last:
        print("No earlier run; saving this one as the baseline.")
        _save_run(db, args.profile, result)
        return
    prev = {r["company_key"]: dict(r) for r in db.execute("SELECT * FROM run_leads WHERE run_id = ?", (last["id"],))}
    new = [l for l in result["leads"] if l["company_key"] not in prev]
    more = [l for l in result["leads"] if l["company_key"] in prev and
            (l["matching_total"] > prev[l["company_key"]]["matching_shipments"] or
             (l["last_date"] or "") > (prev[l["company_key"]]["last_date"] or ""))]
    print(f"Since {last['created_at'][:10]}: {len(new)} new buyers, {len(more)} with new shipments.")
    for l in new:
        print(f"  NEW   {l['score']:>3}  {l['name'][:44]:<44} last {l['last_date']}")
    for l in more:
        print(f"  MORE  {l['score']:>3}  {l['name'][:44]:<44} last {l['last_date']} "
              f"({prev[l['company_key']]['matching_shipments']} → {l['matching_total']} shipments)")
    _save_run(db, args.profile, result)


def main(argv=None):
    p = argparse.ArgumentParser(prog="buyer_finder", description="HSN code → scored overseas buyers with customs proof.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("map", help="HSN code / description → editable search profile")
    s.add_argument("code", nargs="?", help="Indian ITC-HS code, 4 to 8 digits")
    s.add_argument("--desc", help="plain product description")
    s.add_argument("--name", help="profile name (default: the code)")
    s.add_argument("--seed", action="append", help="known Indian exporter to start the snowball from (repeatable)")

    s = sub.add_parser("import", help="load shipment CSVs you collected")
    s.add_argument("files", nargs="+")
    s.add_argument("--source", default="manual", help="where the file came from, kept as proof reference")
    s.add_argument("--market", default="US")
    s.add_argument("--origin-india", action="store_true", help="file has no shipper country; treat all shippers as Indian")
    s.add_argument("--looked-up-exporter", action="append", help="this file is that exporter's customer list")
    s.add_argument("--looked-up-buyer", action="append", help="this file is that buyer's supplier list")
    s.add_argument("-v", "--verbose", action="store_true")

    for name, fn_help in (("search", "run the engine and list buyers"), ("next", "what to look up next to grow the data"),
                          ("export", "write CSV or XLSX"), ("recheck", "what changed since the last run"),
                          ("enrich", "find websites and public contacts"), ("show", "full detail for one buyer"),
                          ("contact", "add a website / email / phone by hand")):
        s = sub.add_parser(name, help=fn_help)
        s.add_argument("profile")
        s.add_argument("--as-of", help="score as if today were YYYY-MM-DD")
        if name in ("search", "next", "enrich"):
            s.add_argument("--top", type=int, default=25 if name != "enrich" else 20)
        if name == "enrich":
            s.add_argument("--delay", type=float, default=1.0, help="seconds between page fetches")
            s.add_argument("--force", action="store_true", help="re-enrich buyers that already have contacts")
        if name == "export":
            s.add_argument("--xlsx", action="store_true")
            s.add_argument("--all", action="store_true", help="include buyers whose proof is older than 36 months")
        if name in ("show", "contact"):
            s.add_argument("company")
        if name == "contact":
            s.add_argument("--website")
            s.add_argument("--email", action="append")
            s.add_argument("--phone", action="append")
            s.add_argument("--decision-maker")
            s.add_argument("--notes")

    s = sub.add_parser("done", help="mark a company as looked up")
    s.add_argument("--exporter", action="append")
    s.add_argument("--buyer", action="append")

    args = p.parse_args(argv)
    db = store.connect()
    {"map": cmd_map, "import": cmd_import, "search": cmd_search, "show": cmd_show, "next": cmd_next,
     "done": cmd_done, "enrich": cmd_enrich, "contact": cmd_contact, "export": cmd_export,
     "recheck": cmd_recheck}[args.cmd](db, args)


if __name__ == "__main__":
    sys.exit(main())
