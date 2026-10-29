"""
Buyer Finder web app — one private account, mobile-first.

Wraps the same engine the CLI uses. Login is a single username + password
whose hash lives in DATA_DIR/auth.json (set it with `python3 -m buyer_finder.web
set-password`). Sessions last 30 days so the phone stays signed in.

Run locally:  BF_INSECURE_COOKIES=1 python3 -m buyer_finder.web run
In Docker:    see buyer_finder/web/DEPLOY.md
"""

import json, os, secrets, threading, time
from datetime import timedelta
from functools import wraps
from pathlib import Path

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   send_file, session, url_for)
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from .. import DATA_DIR, PROFILES_DIR, ensure_dirs
from .. import hsn, store, engine, export as exporter

AUTH_FILE   = DATA_DIR / "auth.json"
SECRET_FILE = DATA_DIR / "secret_key"
UPLOADS_DIR = DATA_DIR / "uploads"

MAX_FAILS, LOCK_SECONDS = 5, 15 * 60
_fails = {}            # ip -> [count, first_fail_time]
_jobs = {}             # profile -> enrichment progress
_jobs_lock = threading.Lock()


def _secret_key():
    if os.environ.get("BF_SECRET_KEY"):
        return os.environ["BF_SECRET_KEY"]
    ensure_dirs()
    if not SECRET_FILE.exists():
        SECRET_FILE.write_text(secrets.token_hex(32))
        SECRET_FILE.chmod(0o600)
    return SECRET_FILE.read_text().strip()


def _auth():
    if not AUTH_FILE.exists():
        return None
    return json.loads(AUTH_FILE.read_text())


app = Flask(__name__)
app.config.update(
    SECRET_KEY=_secret_key(),
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=not os.environ.get("BF_INSECURE_COOKIES"),
    MAX_CONTENT_LENGTH=50 * 1024 * 1024,
)


# ── plumbing ────────────────────────────────────────────────────────────────

def db():
    if "db" not in g:
        g.db = store.connect()
    return g.db


@app.teardown_appcontext
def _close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


@app.after_request
def _headers(resp):
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    resp.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:"
    return resp


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def _csrf():
    if request.method == "POST":
        sent = request.form.get("csrf", "")
        if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
            abort(400, "Form expired. Go back, refresh and try again.")


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not session.get("user"):
            return redirect(url_for("login", next=request.path))
        return fn(*a, **kw)
    return wrapper


def _profiles():
    ensure_dirs()
    return sorted(p.stem for p in PROFILES_DIR.glob("*.json"))


def _profile(name):
    if name not in _profiles():
        abort(404)
    return hsn.load_profile(name)


def _result(name):
    return engine.find_buyers(db(), _profile(name), store.get_contacts(db()))


def _lead(result, key):
    for l in result["leads"]:
        if l["company_key"] == key:
            return l
    abort(404)


def _save_run(name, result):
    store.save_run(db(), name, result)


def _split(text):
    return [x.strip() for x in (text or "").replace("\n", ",").split(",") if x.strip()]


# ── auth ────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    auth = _auth()
    if not auth:
        return render_template("message.html", title="Set a password first",
                               body="Run  python3 -m buyer_finder.web set-password  on the server, then reload.")
    # Caddy appends the real client IP last; earlier entries can be forged
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[-1].strip()
    count, since = _fails.get(ip, [0, 0])
    if count >= MAX_FAILS and time.time() - since < LOCK_SECONDS:
        return render_template("login.html", error="Too many attempts. Try again in 15 minutes."), 429
    if request.method == "POST":
        user = request.form.get("username", "").strip()
        pw = request.form.get("password", "")
        if secrets.compare_digest(user.lower(), auth["username"].lower()) and check_password_hash(auth["hash"], pw):
            _fails.pop(ip, None)
            session.clear()
            session.permanent = True
            session["user"] = auth["username"]
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("home"))
        if time.time() - since >= LOCK_SECONDS:
            count, since = 0, time.time()
        _fails[ip] = [count + 1, since or time.time()]
        time.sleep(1)
        return render_template("login.html", error="Wrong username or password."), 401
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/healthz")
def healthz():
    return "ok"


# ── pages ───────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def home():
    rows = []
    for name in _profiles():
        last = db().execute("SELECT created_at, summary FROM runs WHERE profile = ? ORDER BY id DESC LIMIT 1",
                            (name,)).fetchone()
        rows.append({"name": name, "product": hsn.load_profile(name).get("product", name),
                     "last": dict(last) if last else None,
                     "summary": json.loads(last["summary"]) if last else None})
    n = db().execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
    return render_template("home.html", profiles=rows, shipments=n)


@app.route("/profiles", methods=["POST"])
@login_required
def create_profile():
    code, desc = request.form.get("code", "").strip(), request.form.get("desc", "").strip()
    name = request.form.get("name", "").strip() or desc or code
    if not (code or desc):
        flash("Give an HSN code or a product description.")
        return redirect(url_for("home"))
    profile = hsn.map_hsn(code, desc)
    path = hsn.save_profile(name, profile)
    flash("Profile created. Check the codes and keywords, then save.")
    return redirect(url_for("edit_profile", name=path.stem))


@app.route("/p/<name>/edit", methods=["GET", "POST"])
@login_required
def edit_profile(name):
    profile = _profile(name)
    if request.method == "POST":
        f = request.form
        profile.update({
            "product":           f.get("product", "").strip() or profile.get("product"),
            "hs_prefixes":       [hsn.digits(x) for x in _split(f.get("hs_prefixes")) if hsn.digits(x)],
            "alternates":        [hsn.digits(x) for x in _split(f.get("alternates")) if hsn.digits(x)],
            "use_alternates":    bool(f.get("use_alternates")),
            "keywords":          [x.lower() for x in _split(f.get("keywords"))],
            "negative_keywords": [x.lower() for x in _split(f.get("negative_keywords"))],
            "seeds":             [x.strip() for x in f.get("seeds", "").splitlines() if x.strip()],
        })
        hsn.save_profile(name, profile)
        flash("Saved.")
        return redirect(url_for("profile", name=name))
    return render_template("edit.html", name=name, p=profile)


@app.route("/p/<name>")
@login_required
def profile(name):
    result = _result(name)
    leads = result["leads"]
    route, status, q = request.args.get("route", ""), request.args.get("status", ""), request.args.get("q", "").lower()
    if route:
        leads = [l for l in leads if l["route"] == route]
    if status:
        leads = [l for l in leads if l["status"] == status]
    if q:
        leads = [l for l in leads if q in l["name"].lower() or q in (l["state"] or "").lower()
                 or q in l["proof_line"].lower()]
    with _jobs_lock:
        job = dict(_jobs.get(name, {}))
    return render_template("profile.html", name=name, s=result["summary"], leads=leads,
                           total=len(result["leads"]), route=route, status=status, q=q, job=job,
                           product=_profile(name).get("product", name))


@app.route("/p/<name>/b/<path:key>", methods=["GET", "POST"])
@login_required
def lead(name, key):
    result = _result(name)
    l = _lead(result, key)
    if request.method == "POST":
        existing = store.get_contacts(db()).get(key, {})
        f = request.form
        store.save_contact(db(), key, l["name"],
                           website=f.get("website", "").strip(),
                           emails=_split(f.get("emails")) or existing.get("emails", []),
                           phones=_split(f.get("phones")) or existing.get("phones", []),
                           decision_maker=f.get("decision_maker", "").strip(),
                           notes=f.get("notes", "").strip(),
                           sources=sorted(set(existing.get("sources", []) + ["manual"])))
        flash("Contact saved.")
        return redirect(url_for("lead", name=name, key=key))
    notes = store.get_contacts(db()).get(key, {}).get("notes", "")
    return render_template("lead.html", name=name, l=l, notes=notes)


@app.route("/p/<name>/b/<path:key>/enrich", methods=["POST"])
@login_required
def enrich_one(name, key):
    from .. import enrich
    l = _lead(_result(name), key)
    found = enrich.enrich_lead(l)
    store.save_contact(db(), key, l["name"], **found)
    flash(f"Found {len(found.get('emails', []))} emails" if found.get("website") else "Website not found; add it by hand.")
    return redirect(url_for("lead", name=name, key=key))


def _enrich_job(name, leads):
    from .. import enrich
    conn = store.connect()
    try:
        for l in leads:
            found = enrich.enrich_lead(l)
            store.save_contact(conn, l["company_key"], l["name"], **found)
            with _jobs_lock:
                _jobs[name]["done"] += 1
    finally:
        conn.close()
        with _jobs_lock:
            _jobs[name]["running"] = False


@app.route("/p/<name>/enrich", methods=["POST"])
@login_required
def enrich_many(name):
    with _jobs_lock:
        if _jobs.get(name, {}).get("running"):
            flash("Enrichment already running.")
            return redirect(url_for("profile", name=name))
    top = max(1, min(int(request.form.get("top", 20) or 20), 100))
    contacts = store.get_contacts(db())
    todo = [l for l in _result(name)["leads"] if l["company_key"] not in contacts][:top]
    with _jobs_lock:
        _jobs[name] = {"running": True, "done": 0, "total": len(todo)}
    threading.Thread(target=_enrich_job, args=(name, todo), daemon=True).start()
    flash(f"Finding contacts for {len(todo)} buyers in the background. Refresh to see progress.")
    return redirect(url_for("profile", name=name))


@app.route("/p/<name>/next")
@login_required
def next_lookups(name):
    exps, buys = engine.next_lookups(_result(name), store.looked_up(db()), 25)
    return render_template("next.html", name=name, exps=exps, buys=buys)


@app.route("/done", methods=["POST"])
@login_required
def mark_done():
    store.mark_lookup(db(), request.form["key"], request.form["kind"])
    return redirect(request.form.get("back") or url_for("home"))


@app.route("/p/<name>/export.<fmt>")
@login_required
def export_file(name, fmt):
    if fmt not in ("csv", "xlsx"):
        abort(404)
    leads = [l for l in _result(name)["leads"] if request.args.get("all") or l["status"] != "stale (>36 months)"]
    path = exporter.export(name, leads, fmt)
    return send_file(path, as_attachment=True, download_name=path.name)


@app.route("/p/<name>/recheck", methods=["POST"])
@login_required
def recheck(name):
    last = db().execute("SELECT id, created_at FROM runs WHERE profile = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
    result = _result(name)
    new, more, prev = [], [], {}
    if last:
        prev = {r["company_key"]: dict(r) for r in db().execute("SELECT * FROM run_leads WHERE run_id = ?", (last["id"],))}
        new = [l for l in result["leads"] if l["company_key"] not in prev]
        more = [l for l in result["leads"] if l["company_key"] in prev and
                (l["matching_total"] > prev[l["company_key"]]["matching_shipments"] or
                 (l["last_date"] or "") > (prev[l["company_key"]]["last_date"] or ""))]
    _save_run(name, result)
    return render_template("recheck.html", name=name, last=dict(last) if last else None,
                           new=new, more=more, prev=prev)


@app.route("/import", methods=["GET", "POST"])
@login_required
def import_page():
    profiles = _profiles()
    if request.method == "POST":
        files = [f for f in request.files.getlist("files") if f and f.filename]
        if not files:
            flash("Pick at least one CSV file.")
            return redirect(url_for("import_page"))
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        lines, total = [], 0
        for f in files:
            dest = UPLOADS_DIR / f"{int(time.time())}-{secure_filename(f.filename) or 'upload.csv'}"
            f.save(dest)
            try:
                added, dup, _, _ = store.import_csv(db(), dest, source=request.form.get("source") or "manual",
                                                    default_origin="INDIA" if request.form.get("origin_india") else "")
                total += added
                lines.append(f"{f.filename}: +{added} new, {dup} already in store")
            except SystemExit as e:
                lines.append(f"{f.filename}: {e}")
        if request.form.get("exporter"):
            store.mark_lookup(db(), engine.company_key(request.form["exporter"]), "exporter")
        if request.form.get("buyer"):
            store.mark_lookup(db(), engine.company_key(request.form["buyer"]), "buyer")
        for line in lines:
            flash(line)
        back = request.form.get("back")
        return redirect(url_for("profile", name=back) if back in profiles else url_for("home"))
    return render_template("import.html", profiles=profiles, back=request.args.get("back", ""))


@app.errorhandler(404)
def _404(_e):
    return render_template("message.html", title="Not found", body="That page or buyer doesn't exist."), 404
