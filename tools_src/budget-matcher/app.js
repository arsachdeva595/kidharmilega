/* KidharMilega Budget Matcher: budget + state + interests → email gate → ranked district businesses.
 * Rows come from data.json (written by budget_matcher.py from data/districts.csv); settings from window.BM_CONFIG. */
(function () {
  "use strict";
  var C = window.BM_CONFIG || {}, BASE = window.BM_BASE || "";
  var $ = function (id) { return document.getElementById(id); };
  var LS_LEAD = "sf_lead_v1", LS_FORM = "bm_form_v1";   // same lead key as the other tools: one email per browser
  var SHOW = 6;

  var form = $("bmForm"), errEl = $("bmError"), gate = $("bmGate"), report = $("bmReport");
  var profile = null, ROWS = null;
  var dataReady = fetch(window.BM_DATA).then(function (r) { return r.json(); }).then(function (d) { ROWS = d; return d; });

  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function store(key, val) {
    try { if (val === undefined) return JSON.parse(localStorage.getItem(key) || "null"); localStorage.setItem(key, JSON.stringify(val)); }
    catch (e) { return null; }
  }
  function track(name, params) { try { if (window.gtag) window.gtag("event", name, params || {}); } catch (e) {} }
  function rs(x) {   // rupees, Indian style
    x = Math.max(0, Math.round(x));
    if (x >= 1e7) return "₹" + (x / 1e7).toLocaleString("en-IN", { maximumFractionDigits: 2 }) + " crore";
    if (x >= 1e5) return "₹" + (x / 1e5).toLocaleString("en-IN", { maximumFractionDigits: 2 }) + " lakh";
    return "₹" + x.toLocaleString("en-IN");
  }
  function round(x, to) { return Math.round(x / to) * to; }

  // ── Form ────────────────────────────────────────────────────────────────────
  function readForm() {
    var loan = form.querySelector('input[name="loan"]:checked');
    var b = $("bmBudget").value.trim();
    return {
      budget: b === "" ? null : Math.max(0, parseFloat(b)),
      loan: loan ? loan.value === "yes" : true,
      area: $("bmArea").value, special: $("bmSpecial").value === "1",
      state: $("bmState").value, onlyState: $("bmOnlyState").checked,
      sectors: Array.prototype.map.call(form.querySelectorAll('input[name="sector"]:checked'), function (i) { return i.value; }),
      exp: $("bmExport").checked
    };
  }
  function writeForm(f) {
    if (!f) return;
    if (f.budget != null) $("bmBudget").value = f.budget;
    var r = form.querySelector('input[name="loan"][value="' + (f.loan === false ? "no" : "yes") + '"]'); if (r) r.checked = true;
    if (f.area) $("bmArea").value = f.area;
    $("bmSpecial").value = f.special ? "1" : "0";
    if (f.state != null) $("bmState").value = f.state;
    $("bmOnlyState").checked = !!f.onlyState;
    form.querySelectorAll('input[name="sector"]').forEach(function (i) { i.checked = (f.sectors || []).indexOf(i.value) >= 0; });
    $("bmExport").checked = !!f.exp;
  }
  function syncUi() {
    var f = readForm();
    $("bmLoanBox").hidden = !f.loan;
    $("bmOnlyState").disabled = !f.state;
    $("bmBudgetWords").textContent = f.budget ? "= " + rs(f.budget) + (f.loan ? " · with PMEGP this can back a project of up to " + rs(reach(f)) : "") : "";
    form.querySelectorAll(".bm-amt").forEach(function (b) { b.classList.toggle("is-on", +b.getAttribute("data-v") === f.budget); });
  }
  function validate(f) {
    errEl.textContent = "";
    if (f.budget == null || !(f.budget > 0)) { errEl.textContent = "Enter how much money you can put in (step 1)."; $("bmBudget").focus(); return false; }
    if (f.budget < 5000) { errEl.textContent = "Enter at least ₹5,000. (Tip: ₹50,000 is 50000.)"; $("bmBudget").focus(); return false; }
    return true;
  }

  // ── PMEGP maths ─────────────────────────────────────────────────────────────
  function ownPct(f) { return f.special ? C.pmegp.ownSpecial : C.pmegp.ownGen; }
  function subPct(f) {
    var g = C.pmegp, rural = f.area === "rural";
    return f.special ? (rural ? g.subSpRural : g.subSpUrban) : (rural ? g.subGenRural : g.subGenUrban);
  }
  function reach(f) { return Math.min(f.budget * 100 / ownPct(f), C.pmegp.capMfg * 1e5); }
  function emi(principal) {
    var r = C.loanRate / 1200, n = C.loanYears * 12;
    return principal * r * Math.pow(1 + r, n) / (Math.pow(1 + r, n) - 1);
  }
  function money(lo, f) {   // the cheapest version of this business, funded through PMEGP
    var own = lo * ownPct(f) / 100, sub = lo * subPct(f) / 100, loan = lo - own;
    return { own: own, sub: sub, loan: loan, emi: emi(Math.max(0, loan - sub)) };
  }

  // ── Matching ────────────────────────────────────────────────────────────────
  function rank(row, f) {
    var s = (row.sc || 6) * 10;
    if (f.state && row.s === f.state) s += 25;
    if (f.exp && row.x === "High") s += 8;
    if (row.gi) s += 3;
    s += Math.min(6, Math.log(Math.max(1, f.budget / row.lo)) / Math.LN2 * 1.5);   // a little headroom is good
    return s;
  }
  function match(f) {
    var lim = f.loan ? reach(f) : f.budget;
    var pool = ROWS.filter(function (r) {
      if (f.onlyState && f.state && r.s !== f.state) return false;
      if (f.sectors.length && f.sectors.indexOf(r.c) < 0) return false;
      return true;
    });
    var own = [], loan = [], near = [];
    pool.forEach(function (r) {
      var item = { r: r, score: rank(r, f) };
      if (r.lo <= f.budget) own.push(item);
      else if (f.loan && r.lo <= lim) loan.push(item);
      else if (r.lo <= lim * 2.5) near.push(item);
    });
    var by = function (a, b) { return b.score - a.score || a.r.lo - b.r.lo; };
    own.sort(by); loan.sort(by);
    near.sort(function (a, b) { return a.r.lo - b.r.lo; });
    return { own: own, loan: loan, near: near, pool: pool.length, lim: lim };
  }

  // ── Report ──────────────────────────────────────────────────────────────────
  function href(path) { return BASE + path; }
  function card(it, f, kind) {
    var r = it.r, tags = [];
    if (f.state && r.s === f.state) tags.push('<span class="scf-badge">In your state</span>');
    if (r.gi) tags.push('<span class="scf-badge is-state">GI tag</span>');
    if (r.x === "High") tags.push('<span class="scf-badge bm-b-exp">Export: high</span>');
    if (C.sectors[r.c]) tags.push('<span class="scf-kind">' + esc(C.sectors[r.c]) + '</span>');
    var stats = [
      ["Setup cost", rs(r.lo) + (r.hi > r.lo ? " – " + rs(r.hi) : "")],
      r.mw ? ["Margin (wholesale)", r.mw] : null,
      r.md ? ["Margin (selling direct)", r.md] : null,
      r.be ? ["Break-even", r.be] : null
    ].filter(Boolean).map(function (s) { return '<div><dt>' + esc(s[0]) + '</dt><dd>' + esc(s[1]) + '</dd></div>'; }).join("");
    var fund = "";
    if (kind === "loan") {
      var m = money(r.lo, f);
      fund = '<div class="bm-fund"><strong>Start at ' + rs(r.lo) + ' with PMEGP:</strong> ' +
        'your share ' + rs(m.own) + ' · bank loan ' + rs(m.loan) + ' · subsidy about ' + rs(m.sub) +
        ' · EMI roughly ' + rs(round(m.emi, 100)) + '/month</div>';
    } else if (kind === "own") {
      var left = f.budget - r.lo;
      fund = '<div class="bm-fund is-own"><strong>Fits your money.</strong> ' +
        (left >= 5000 ? rs(left) + ' left over for stock and running costs at the smallest setup.' : 'Just enough for the smallest setup; keep some working capital aside.') + '</div>';
    } else {
      var gap = r.lo - (f.loan ? f.budget * 100 / ownPct(f) : f.budget);
      fund = '<div class="bm-fund is-near"><strong>A little out of reach.</strong> Smallest setup ' + rs(r.lo) +
        (f.loan ? ', which needs about ' + rs(r.lo * ownPct(f) / 100) + ' of your own money with PMEGP.' : ', about ' + rs(gap) + ' more than you have.') + '</div>';
    }
    var sup = r.h ? href(C.paths.supplier) + "?hsn=" + encodeURIComponent(r.h) + "&state=" + encodeURIComponent(r.s) + "&district=" + encodeURIComponent(r.d.replace(/\s*\(.*\)\s*/g, "").trim()) : "";
    return '<article class="scf-card bm-card">' +
      '<div class="scf-card__meta">' + tags.join("") + '</div>' +
      '<h4 class="scf-card__title">' + esc(r.p) + '</h4>' +
      '<p class="bm-where">' + esc(r.d) + ', ' + esc(r.s) + '</p>' +
      (r.a ? '<p class="bm-fact">' + esc(r.a) + '</p>' : '') +
      '<dl class="bm-stats">' + stats + '</dl>' + fund +
      (r.r || r.f ? '<details class="bm-more"><summary>Raw material and who it suits</summary>' +
        (r.r ? '<p><strong>Raw material:</strong> ' + esc(r.r) + '</p>' : '') +
        (r.f ? '<p><strong>Suits:</strong> ' + esc(r.f) + '</p>' : '') + '</details>' : '') +
      '<div class="bm-links">' +
        '<a class="btn btn-primary btn-sm" href="' + esc(href(C.paths.product) + r.u + "/") + '" data-t="guide">Full guide &rarr;</a>' +
        (sup ? '<a class="btn btn-ghost btn-sm" href="' + esc(sup) + '" data-t="supplier">Find suppliers</a>' : '') +
        '<a class="btn btn-ghost btn-sm" href="' + esc(href(C.paths.scheme) + "?state=" + encodeURIComponent(r.s)) + '" data-t="scheme">Check subsidies</a>' +
      '</div></article>';
  }
  function list(id, items, f, kind) {
    if (!items.length) return "";
    var first = items.slice(0, SHOW).map(function (it) { return card(it, f, kind); }).join("");
    var rest = items.slice(SHOW);
    return '<div class="scf-cards" id="' + id + '">' + first + '</div>' +
      (rest.length ? '<button type="button" class="btn btn-ghost bm-moreBtn" data-list="' + id + '" data-kind="' + kind + '">Show ' + Math.min(rest.length, 12) + ' more of ' + rest.length + '</button>' : '');
  }

  function render(f) {
    var m = match(f), html = "";
    var where = f.state ? (f.onlyState ? "in " + f.state : "across India, " + f.state + " first") : "across India";
    var picked = f.sectors.length ? f.sectors.map(function (s) { return C.sectors[s].split(",")[0].split(" &")[0]; }).join(", ") : "";
    html += '<div class="section-label">Your matches</div>';
    html += '<h2 class="scf-title">' + rs(f.budget) + ' se kya shuru ho sakta hai</h2>';
    html += '<div class="scf-chips"><span>Own money: ' + rs(f.budget) + '</span><span>' + esc(where) + '</span>' +
      (picked ? '<span>' + esc(picked) + '</span>' : '') + '<span>' + (f.loan ? "Open to a loan" : "No loan") + '</span></div>';

    // Headline tiles
    html += '<div class="bm-tiles">' +
      '<div class="bm-tile"><b>' + m.own.length + '</b><span>businesses you can start with your own ' + rs(f.budget) + '</span></div>' +
      (f.loan ? '<div class="bm-tile is-blue"><b>+' + m.loan.length + '</b><span>more with a PMEGP loan (project up to ' + rs(m.lim) + ')</span></div>' : '') +
      '</div>';

    if (f.loan) {
      var sp = subPct(f), op = ownPct(f);
      html += '<div class="sf-tip bm-pmegp"><strong>How ' + rs(f.budget) + ' becomes ' + rs(m.lim) + ':</strong> under PMEGP you only put in ' + op +
        '% of the project cost' + (f.special ? ' (special category)' : '') + '. The bank lends the rest, and the government adds a ' + sp +
        '% subsidy (' + (f.area === "rural" ? "rural" : "urban") + ' rate)' + (m.lim >= C.pmegp.capMfg * 1e5 ? '. Manufacturing projects are capped at ' + rs(C.pmegp.capMfg * 1e5) : '') +
        '. You need a project report and a bank that says yes. <a href="' + esc(href(C.paths.scheme)) + (f.state ? "?state=" + encodeURIComponent(f.state) : "") + '">See every scheme you qualify for &rarr;</a></div>';
    }

    html += '<div class="scf-actions">' +
      '<button class="btn btn-ghost btn-sm" type="button" id="bmEdit">Change answers</button>' +
      '<a class="btn btn-ghost btn-sm" id="bmWa" target="_blank" rel="noopener" href="https://wa.me/?text=' + encodeURIComponent(rs(f.budget) + " mein kaunsa business karein? Ye free tool district-wise real options dikhata hai: " + location.origin + location.pathname + "?budget=" + Math.round(f.budget)) + '">Share on WhatsApp</a>' +
      '<button class="btn btn-ghost btn-sm" type="button" id="bmPrint">Save as PDF</button></div>';

    if (m.own.length) {
      html += '<section class="scf-sec"><h3 class="scf-h">Start with your own money <span>' + m.own.length + '</span></h3>' +
        '<p class="scf-sub">The smallest version of these costs ' + rs(f.budget) + ' or less. No loan, lowest risk. Best ranked first.</p>' +
        list("bmOwn", m.own, f, "own") + '</section>';
    }
    if (f.loan && m.loan.length) {
      html += '<section class="scf-sec"><h3 class="scf-h">With a PMEGP loan <span>' + m.loan.length + '</span></h3>' +
        '<p class="scf-sub">Your money covers the ' + ownPct(f) + '% own contribution. EMI is a rough guide at ' + C.loanRate + '% over ' + C.loanYears + ' years after the subsidy is adjusted.</p>' +
        list("bmLoan", m.loan, f, "loan") + '</section>';
    }
    if (!m.own.length && !(f.loan && m.loan.length)) {
      html += '<section class="scf-sec"><h3 class="scf-h">Nothing fits this budget yet</h3>' +
        '<p class="scf-sub">' + (m.pool ? "None of the " + m.pool + " businesses that match your filters start this low." : "No businesses match these filters.") +
        (f.loan ? "" : " Try turning on the PMEGP loan option: it lets a small budget back a 10x bigger project.") +
        (f.onlyState ? " Or untick ‘only my state’." : "") + (f.sectors.length ? " Or clear the kind-of-work filter." : "") + '</p></section>';
    }
    if (m.near.length && m.own.length + m.loan.length < 6) {
      html += '<section class="scf-sec"><h3 class="scf-h">Almost within reach <span>' + m.near.length + '</span></h3>' +
        '<p class="scf-sub">Cheapest businesses just above your budget. Save a bit more, partner with someone, or start as a trader first.</p>' +
        list("bmNear", m.near, f, "near") + '</section>';
    }

    html += '<aside class="sf-help"><div><strong>Confused between two ideas?</strong><p>Book a 1:1 call and we\'ll pick one and plan the first 90 days together.</p></div>' +
      '<a class="btn btn-cyan" href="' + esc(C.bookCallUrl) + '" target="_blank" rel="noopener" id="bmBook">Book a call</a></aside>';
    html += '<p class="scf-fine scf-disclaimer">Data updated ' + esc(C.reviewed) + '. Setup costs, margins and break-even are estimates from KidharMilega\'s district research, not quotes: check prices with suppliers in that district before you spend. PMEGP figures follow the December 2023 guidelines; the bank and the implementing agency decide every loan and subsidy. No government body is connected with KidharMilega.</p>';

    report.innerHTML = html;
    report.hidden = false;
    report.scrollIntoView({ behavior: "smooth", block: "start" });

    var lists = { bmOwn: m.own, bmLoan: m.loan, bmNear: m.near };
    report.querySelectorAll(".bm-moreBtn").forEach(function (btn) {
      btn.onclick = function () {
        var id = btn.getAttribute("data-list"), box = $(id), items = lists[id], have = box.children.length;
        box.insertAdjacentHTML("beforeend", items.slice(have, have + 12).map(function (it) { return card(it, f, btn.getAttribute("data-kind")); }).join(""));
        var left = items.length - box.children.length;
        if (left > 0) btn.textContent = "Show " + Math.min(left, 12) + " more of " + left; else btn.remove();
        track("bm_more", { list: id });
      };
    });
    report.addEventListener("click", function (e) {
      var a = e.target.closest && e.target.closest("a[data-t]");
      if (a) track("bm_click", { to: a.getAttribute("data-t") });
    });
    $("bmPrint").onclick = function () { report.querySelectorAll("details").forEach(function (d) { d.open = true; }); track("bm_pdf", {}); window.print(); };
    $("bmEdit").onclick = function () { form.scrollIntoView({ behavior: "smooth", block: "start" }); };
    $("bmWa").onclick = function () { track("bm_share", { app: "whatsapp" }); };
    $("bmBook").onclick = function () { track("bm_book_call", {}); };
    return m;
  }

  // ── Leads ───────────────────────────────────────────────────────────────────
  function sendLead(event, f, m) {
    var lead = store(LS_LEAD);
    if (!C.leadEndpoint || !lead) return;
    var qs = new URLSearchParams(location.search);
    var top = m.own.concat(m.loan).slice(0, 5).map(function (it) { return it.r.u; });
    var body = {
      event: event, email: lead.email, phone: lead.phone || "", product: "Budget " + Math.round(f.budget),
      state: f.state, district: "", segment: f.loan ? "loan" : "own",
      hsn_name: m.own.length + " own / " + m.loan.length + " loan",
      details: JSON.stringify({ b: f.budget, loan: f.loan, area: f.area, sp: f.special, only: f.onlyState, sec: f.sectors, exp: f.exp, top: top }),
      page: location.href.split("#")[0], referrer: document.referrer || "",
      utm_source: qs.get("utm_source") || "", utm_medium: qs.get("utm_medium") || "", utm_campaign: qs.get("utm_campaign") || ""
    };
    try {
      fetch(C.leadEndpoint, { method: "POST", mode: "no-cors", headers: { "Content-Type": "text/plain;charset=utf-8" }, body: JSON.stringify(body), keepalive: true });
    } catch (e) {}
  }

  function openGate() {
    gate.hidden = false; document.body.classList.add("sf-noscroll");
    var lead = store(LS_LEAD); if (lead) { $("bmEmail").value = lead.email || ""; $("bmPhone").value = lead.phone || ""; }
    setTimeout(function () { $("bmEmail").focus(); }, 30);
  }
  function closeGate() { gate.hidden = true; document.body.classList.remove("sf-noscroll"); }
  function show(f, event) {
    dataReady.then(function () { var m = render(f); sendLead(event, f, m); })
      .catch(function () { errEl.textContent = "Couldn't load the business list. Check your connection and try again."; });
  }

  // ── Wiring ──────────────────────────────────────────────────────────────────
  form.addEventListener("input", syncUi);
  form.addEventListener("change", syncUi);
  form.querySelectorAll(".bm-amt").forEach(function (b) {
    b.addEventListener("click", function () { $("bmBudget").value = b.getAttribute("data-v"); syncUi(); });
  });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var f = readForm();
    if (!validate(f)) return;
    profile = f; store(LS_FORM, f);
    var lead = store(LS_LEAD);
    if (lead && lead.email) { show(f, "budget_search"); track("bm_generate", { returning: true, budget: f.budget, state: f.state }); }
    else openGate();
  });
  $("bmGateForm").addEventListener("submit", function (e) {
    e.preventDefault();
    var email = $("bmEmail").value.trim(), phone = $("bmPhone").value.replace(/[\s-]/g, ""), ge = $("bmGateError");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) { ge.textContent = "Enter a valid email."; $("bmEmail").focus(); return; }
    if (phone && !/^(\+?91)?[6-9]\d{9}$/.test(phone)) { ge.textContent = "Enter a 10-digit Indian mobile number, or leave it empty."; $("bmPhone").focus(); return; }
    ge.textContent = "";
    store(LS_LEAD, { email: email, phone: phone });
    closeGate();
    show(profile, "budget_match");
    track("bm_lead", { budget: profile.budget, state: profile.state }); track("generate_lead", { method: "budget_matcher" });
  });
  $("bmGateClose").addEventListener("click", closeGate);
  gate.addEventListener("click", function (e) { if (e.target === gate) closeGate(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !gate.hidden) closeGate(); });

  // Prefill: saved answers, then ?budget=&state= (for reel links and product pages)
  writeForm(store(LS_FORM));
  var qs = new URLSearchParams(location.search);
  var qb = parseFloat((qs.get("budget") || "").replace(/[^\d.]/g, ""));
  if (qb > 0) $("bmBudget").value = Math.round(qb);
  if (qs.get("state")) { var opt = Array.prototype.some.call($("bmState").options, function (o) { return o.value === qs.get("state"); }); if (opt) $("bmState").value = qs.get("state"); }
  syncUi();
})();
