/* KidharMilega Scheme Finder: business profile → email gate → detailed scheme report.
 * Scheme data and rules come from window.SCF_CONFIG, written by scheme_finder.py. */
(function () {
  "use strict";
  var C = window.SCF_CONFIG || {};
  var $ = function (id) { return document.getElementById(id); };
  var LS_LEAD = "sf_lead_v1", LS_FORM = "scf_form_v1";   // same lead key as Supplier Finder: one email per browser

  var form = $("scfForm"), errEl = $("scfError"), gate = $("scfGate"), report = $("scfReport");
  var profile = null;

  var SOCIAL = { gen: "General", obc: "OBC", sc: "SC", st: "ST", min: "Minority" };
  var STAGE_SHORT = { idea: "idea stage", "new": "a business under 3 years old", running: "a running business (3+ years)" };
  var GROUPS = [
    ["money", "Subsidies and grants", "Money you don't pay back. Usually released through a bank loan, so the loan comes first."],
    ["loans", "Loans, guarantees and interest support", "Cheaper or collateral-free credit."],
    ["export", "Export support", "Refunds, insurance and cheaper credit for exporters."],
    ["support", "Certification, marketing and IP support", "Reimbursements that cut the cost of growing."],
    ["watch", "Announced, not open yet", "Keep an eye on these."]
  ];
  var EXPORT_IDS = { niryat: 1, dgft: 1, ecgc: 1, ic: 1 };

  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function store(key, val) {
    try { if (val === undefined) return JSON.parse(localStorage.getItem(key) || "null"); localStorage.setItem(key, JSON.stringify(val)); }
    catch (e) { return null; }
  }
  function track(name, params) { try { if (window.gtag) window.gtag("event", name, params || {}); } catch (e) {} }
  function num(id) { var v = $(id).value.trim(); return v === "" ? null : Math.max(0, parseFloat(v)); }
  function lakh(x) {
    if (x >= 100) return "₹" + (Math.round(x) / 100).toLocaleString("en-IN", { maximumFractionDigits: 2 }) + " crore";
    if (x < 1) return "₹" + Math.round(x * 100000).toLocaleString("en-IN");
    return "₹" + (Math.round(x * 100) / 100).toLocaleString("en-IN", { maximumFractionDigits: 2 }) + " lakh";
  }

  // ── Profile ─────────────────────────────────────────────────────────────────
  function readForm() {
    var st = form.querySelector('input[name="stage"]:checked');
    return {
      stage: st ? st.value : "", sector: $("scfSector").value, artisan: $("scfArtisan").checked,
      state: $("scfState").value, area: $("scfArea").value, entity: $("scfEntity").value || "prop",
      proj: num("scfProj"), turn: num("scfTurn"), exp: $("scfExport").value,
      udyam: $("scfUdyam").checked, gst: $("scfGst").checked, iec: $("scfIec").checked, dpiit: $("scfDpiit").checked, fssai: $("scfFssai").checked,
      age: num("scfAge"), gender: $("scfGender").value, social: $("scfSocial").value, pwd: $("scfPwd").checked, ex: $("scfEx").checked
    };
  }
  function writeForm(f) {
    if (!f) return;
    var r = form.querySelector('input[name="stage"][value="' + f.stage + '"]'); if (r) r.checked = true;
    var set = function (id, v) { if (v != null) $(id).value = v; };
    set("scfSector", f.sector); set("scfState", f.state); set("scfArea", f.area); set("scfEntity", f.entity);
    set("scfProj", f.proj); set("scfTurn", f.turn); set("scfExport", f.exp); set("scfAge", f.age); set("scfGender", f.gender); set("scfSocial", f.social);
    ["Artisan:artisan", "Udyam:udyam", "Gst:gst", "Iec:iec", "Dpiit:dpiit", "Fssai:fssai", "Pwd:pwd", "Ex:ex"].forEach(function (x) {
      var k = x.split(":"); $("scf" + k[0]).checked = !!f[k[1]];
    });
  }
  function validate(f) {
    errEl.textContent = "";
    var miss = !f.stage ? "Tell us where you are right now (step 1)." :
      !f.sector ? "Choose the kind of business." :
      !f.state ? "Select your state." :
      f.age == null ? "Enter the owner's age (step 3)." :
      (f.age < 14 || f.age > 99) ? "Enter an age between 14 and 99." : "";
    if (miss) { errEl.textContent = miss; return false; }
    return true;
  }

  function isSpecial(f) {   // PMEGP / CMEGP special category
    return f.gender === "f" || f.gender === "o" || f.social !== "gen" || f.pwd || f.ex ||
      C.ner.indexOf(f.state) >= 0 || C.hill.indexOf(f.state) >= 0;
  }
  function msmeClass(f) {
    if (f.turn == null) return null;
    for (var i = 0; i < C.classification.length; i++) if (f.turn <= C.classification[i][2]) return C.classification[i][0];
    return "Large";
  }

  // ── Rules ───────────────────────────────────────────────────────────────────
  // Returns { ok, reasons[], fail, notes[] }. Every rule key present must match.
  function evaluate(s, f) {
    var r = s.rule || {}, reasons = [], notes = [];
    function no(msg) { return { ok: false, fail: msg }; }
    if (r.states) {
      if (r.states.indexOf(f.state) < 0) return no(r.states.length === 1 ? "Only for " + r.states[0] : "Only for the North Eastern states");
      reasons.push(r.states.length === 1 ? "You're in " + f.state : "Your unit is in the North East");
    }
    if (r.artisan) {
      if (!f.artisan) return no("Only for traditional artisans in the listed trades");
      reasons.push("You work as a traditional artisan");
    }
    if (r.sector) {
      if (r.sector.indexOf(f.sector) < 0) return no("Not for " + C.sectors[f.sector].split(" (")[0].toLowerCase());
      reasons.push("Covers " + C.sectors[f.sector].split(" (")[0].toLowerCase());
    }
    if (r.stage) {
      if (r.stage.indexOf(f.stage) < 0) return no(r.stage.indexOf("running") < 0 ? "For new units only, not existing businesses" : "For businesses that are already running");
      reasons.push("Fits " + STAGE_SHORT[f.stage]);
    }
    if (r.social) {
      if (r.social.indexOf(f.social) < 0) return no("Only for " + r.social.map(function (x) { return SOCIAL[x]; }).join(" / ") + " entrepreneurs");
      reasons.push("For " + SOCIAL[f.social] + " entrepreneurs");
    }
    if (r.orSocial) {
      var hit = r.orSocial.indexOf(f.social) >= 0, w = r.women && f.gender === "f", d = r.pwdOr && f.pwd;
      if (!hit && !w && !d) {
        var who = r.orSocial.map(function (x) { return SOCIAL[x]; });
        if (r.women) who.unshift("women");
        if (r.pwdOr) who.push("persons with disability");
        return no("Only for " + who.join(", ") + " entrepreneurs");
      }
      reasons.push(w ? "For women entrepreneurs" : d && !hit ? "For entrepreneurs with disability" : "For " + SOCIAL[f.social] + " entrepreneurs");
    }
    if (r.ageMin != null || r.ageMax != null) {
      if (r.ageMin != null && f.age < r.ageMin) return no("Minimum age is " + r.ageMin);
      if (r.ageMax != null && f.age > r.ageMax) return no("Age limit is " + r.ageMax + (r.ageMax >= 50 ? " (for special categories; lower for others)" : ""));
      if (r.ageMax != null) reasons.push("Your age (" + f.age + ") is within " + (r.ageMin || 18) + "–" + r.ageMax);
    }
    if (r.projMin != null || r.projMax != null) {
      if (f.proj == null) notes.push("Project limits apply" + (r.projMin != null ? ": from " + lakh(r.projMin) : "") + (r.projMax != null ? (r.projMin != null ? " to " : ": up to ") + lakh(r.projMax) : "") + ".");
      else {
        if (r.projMin != null && f.proj < r.projMin) return no("Needs a project of at least " + lakh(r.projMin));
        if (r.projMax != null && f.proj > r.projMax) return no("Project limit is " + lakh(r.projMax));
        reasons.push("Your project (" + lakh(f.proj) + ") is within the limit");
      }
    }
    if (r.export) {
      if (r.export.indexOf(f.exp) < 0) return no("For exporters");
      reasons.push(f.exp === "yes" ? "You already export" : "You plan to export");
    }
    if (r.entity) {
      if (r.entity.indexOf(f.entity) < 0) return no(r.entity.length === 1 && r.entity[0] === "group" ? "Only for groups (FPO, cooperative, SHG, cluster)" : "Needs a company, LLP or registered partnership");
      reasons.push(f.entity === "group" ? "You're a group" : "Your business type qualifies");
    }
    // Soft notes from the profile
    if (s.id === "pmegp" || s.id === "mh-cmegp") {
      if (f.proj != null && f.proj > 20 && ["service", "trade"].indexOf(f.sector) >= 0) notes.push("Service and business units are capped at ₹20 lakh project cost.");
      notes.push(isSpecial(f) ? "You fall in the special category (higher subsidy, 5% own contribution)." : "General category: 10% own contribution.");
    }
    if (s.id === "mudra" && f.proj != null && f.proj > 20) notes.push("Mudra tops out at ₹20 lakh; borrow the rest under CGTMSE.");
    if (s.id === "cgtmse") { var mc = msmeClass(f); if (mc === "Medium" || mc === "Large") return no("For micro and small enterprises only"); }
    if (s.id === "startup" && f.dpiit) reasons.push("You already have DPIIT recognition");
    if (s.id === "acabc") notes.push("Only if you have a degree or diploma in agriculture or an allied subject.");
    if (s.id === "pmfme" && f.sector === "food" && f.stage !== "idea") notes.push("Existing units can use it to upgrade or expand.");
    if (!reasons.length) reasons.push("Open to most businesses like yours");
    return { ok: true, reasons: reasons, notes: notes };
  }

  // Rough capital subsidy (₹ lakh) or null.
  function estimate(s, f) {
    var c = s.calc; if (!c) return null;
    if (c.fixed != null) return { v: c.fixed, how: "maximum, if selected" };
    if (f.proj == null) return null;
    var pct, base = f.proj, cap = c.cap;
    if (c.pmegp) {
      var sp = isSpecial(f), rural = f.area === "rural";
      pct = sp ? (rural ? 35 : 25) : (rural ? 25 : 15);
      var lim = ["service", "trade"].indexOf(f.sector) >= 0 ? 20 : 50;
      base = Math.min(base, lim);
      return { v: base * pct / 100, how: pct + "% of " + lakh(base) + (f.area ? "" : " (assumed urban; rural gets more)") };
    }
    pct = c.pct;
    var wss = f.gender === "f" || f.social === "sc" || f.social === "st";
    if (c.pctWomenScSt && wss) pct = c.pctWomenScSt;
    if (c.pctWomen && f.gender === "f") pct = c.pctWomen;
    if (c.pctRural && f.area === "rural") pct = c.pctRural;
    if (c.pctSpecial && isSpecial(f)) pct = c.pctSpecial;
    var v = base * pct / 100;
    var capped = cap != null && v > cap;
    if (capped) v = cap;
    return { v: v, how: pct + "% of " + lakh(base) + (capped ? ", capped at " + lakh(cap) : "") };
  }

  function groupOf(s) {
    if (s.status === "soon") return "watch";
    if (EXPORT_IDS[s.id]) return "export";
    if (s.calc || (/^(subsid|grant|capital|cluster)/i.test(s.kind) && !/ on /i.test(s.kind))) return "money";
    if (/loan|guarantee|finance|interest|insurance/i.test(s.kind)) return "loans";
    return "support";
  }

  // ── Action plan ─────────────────────────────────────────────────────────────
  function plan(f, matches, best) {
    var steps = [];
    if (!f.udyam) steps.push(["Register on Udyam today (free, 15 minutes)", "Go to udyamregistration.gov.in with Aadhaar and PAN. Almost every scheme, the collateral-free loan rule and the 45-day payment protection need it. Never pay an agent for this."]);
    if (f.sector === "food" && !f.fssai) steps.push(["Get FSSAI registration", C.docs.fssai + ". Basic registration is ₹100 a year on foscos.fssai.gov.in."]);
    if ((f.exp === "plan" || f.exp === "yes") && !f.iec) steps.push(["Get your IEC from DGFT", "Apply on dgft.gov.in with PAN and a bank account (fee ₹500). Then join your export promotion council for an RCMC."]);
    if (f.sector === "tech" && !f.dpiit && ["pvt", "llp", "firm"].indexOf(f.entity) >= 0) steps.push(["Apply for DPIIT startup recognition", "Free on startupindia.gov.in. It unlocks the seed fund, the tax holiday and the startup credit guarantee."]);
    if (f.sector === "tech" && ["pvt", "llp", "firm"].indexOf(f.entity) < 0) steps.push(["Consider registering as a company or LLP", "Startup India benefits (seed fund, tax holiday) need a private limited company, LLP or registered partnership."]);
    if (f.stage === "idea" || (best && best.s.calc)) steps.push(["Get a project report (DPR) made", "Banks and every subsidy scheme ask for one. Get 2–3 machinery quotations first. Under PMFME, a District Resource Person makes it free; for PMEGP, the DIC or KVIC office helps."]);
    if (best) steps.push(["Apply for " + best.s.name.split(" (")[0], "This is your biggest likely subsidy (about " + lakh(best.est.v) + "). " + (best.s.apply[0] || "")]);
    var loan = matches.filter(function (m) { return m.s.id === "mudra" || m.s.id === "cgtmse"; })[0];
    if (loan) steps.push(["Line up the bank loan", "Subsidies are released through the loan. Ask the bank to cover it under CGTMSE, and remember: no collateral up to ₹20 lakh for MSE loans."]);
    steps.push(["Visit your District Industries Centre (DIC)", "The DIC in your district handles most state schemes and PMEGP, and knows which windows are open right now. Take this report with you."]);
    return steps;
  }

  // ── Report ──────────────────────────────────────────────────────────────────
  function card(m, f) {
    var s = m.s, e = m.est;
    var badge = s.level === "state" ? s.state : "Central";
    var status = s.status === "open" ? "" :
      '<p class="scf-status scf-status--' + esc(s.status) + '"><strong>' + (s.status === "soon" ? "Not open yet" : "Check before you apply") + ':</strong> ' + esc(s.statusNote || "") + '</p>';
    var docs = (s.docs || []).map(function (d) { return '<li>' + esc(C.docs[d] || d) + '</li>'; }).join("");
    return '<article class="scf-card' + (m.top ? " is-top" : "") + '">' +
      '<div class="scf-card__meta"><span class="scf-badge' + (s.level === "state" ? " is-state" : "") + '">' + esc(badge) + '</span><span class="scf-kind">' + esc(s.kind) + '</span></div>' +
      '<h3 class="scf-card__title">' + esc(s.name) + '</h3>' +
      '<p class="scf-card__benefit">' + esc(s.benefit) + '</p>' +
      (e ? '<div class="scf-est"><span>Your estimate</span><strong>~' + esc(lakh(e.v)) + '</strong><small>' + esc(e.how) + '</small></div>' : "") +
      '<ul class="scf-why">' + m.reasons.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join("") +
      m.notes.map(function (x) { return '<li class="is-note">' + esc(x) + '</li>'; }).join("") + '</ul>' +
      status +
      '<details class="scf-more"><summary>Rules, documents and how to apply</summary>' +
        s.details.map(function (d) { return '<p>' + esc(d) + '</p>'; }).join("") +
        '<h4>Who can apply</h4><p>' + esc(s.who) + '</p>' +
        (docs ? '<h4>Documents to keep ready</h4><ul>' + docs + '</ul>' : "") +
        '<h4>How to apply</h4><ol>' + s.apply.map(function (a) { return '<li>' + esc(a) + '</li>'; }).join("") + '</ol>' +
      '</details>' +
      '<a class="btn btn-ghost btn-sm scf-link" href="' + esc(s.url) + '" target="_blank" rel="noopener">Official site ↗</a>' +
      '</article>';
  }

  function render(f) {
    var matches = [], misses = [];
    C.schemes.forEach(function (s) {
      var ev = evaluate(s, f);
      if (ev.ok) matches.push({ s: s, reasons: ev.reasons, notes: ev.notes, est: estimate(s, f) });
      else if (!(s.rule.states && s.rule.states.indexOf(f.state) < 0)) misses.push({ s: s, why: ev.fail });
    });
    // Best single subsidy: largest estimate among cash schemes that are open or likely open.
    var best = null;
    matches.forEach(function (m) { if (m.est && m.s.status !== "soon" && (!best || m.est.v > best.est.v)) best = m; });
    if (best) best.top = true;
    var stateCount = matches.filter(function (m) { return m.s.level === "state"; }).length;
    var mc = msmeClass(f);
    var portal = C.portals[f.state];
    var today = new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });

    var chips = [C.sectors[f.sector].split(" (")[0], f.state + (f.area ? " (" + (f.area === "rural" ? "rural" : "urban") + ")" : ""),
      STAGE_SHORT[f.stage], "Age " + f.age, SOCIAL[f.social] + (f.gender === "f" ? ", woman" : ""),
      f.proj != null ? "Project " + lakh(f.proj) : null, mc ? mc + " enterprise" : null].filter(Boolean);

    var html = '<div class="scf-report__head">' +
      '<div class="section-label">Your scheme report · ' + esc(today) + '</div>' +
      '<h2 class="section-title">' + matches.filter(function (m) { return m.s.status !== "soon"; }).length + ' schemes you can use</h2>' +
      '<div class="scf-chips">' + chips.map(function (c) { return '<span>' + esc(c) + '</span>'; }).join("") + '</div>' +
      '<div class="scf-actions"><button class="btn btn-primary btn-sm" type="button" id="scfPrint">Download PDF</button>' +
      '<a class="btn btn-ghost btn-sm" id="scfWa" target="_blank" rel="noopener" href="https://wa.me/?text=' + encodeURIComponent("Find government schemes and subsidies your business qualifies for (free report): " + location.href.split("#")[0].split("?")[0]) + '">Share on WhatsApp</a>' +
      '<button class="btn btn-ghost btn-sm" type="button" id="scfEdit">Edit answers</button></div></div>';

    html += '<div class="ebf-tiles scf-tiles">' +
      '<div class="ebf-tile"><div class="ebf-tile__l">Schemes matched</div><div class="ebf-tile__v">' + matches.length + '</div><div class="ebf-tile__s">' + (matches.length - stateCount) + ' central, ' + stateCount + ' ' + esc(f.state) + '</div></div>' +
      '<div class="ebf-tile"><div class="ebf-tile__l">Biggest likely subsidy</div><div class="ebf-tile__v">' + (best ? "~" + esc(lakh(best.est.v)) : "–") + '</div><div class="ebf-tile__s">' + (best ? esc(best.s.name.split(" (")[0]) : (f.proj == null ? "Add a project cost to estimate" : "No cash subsidy matched")) + '</div></div>' +
      '<div class="ebf-tile"><div class="ebf-tile__l">Collateral-free credit</div><div class="ebf-tile__v">₹20 lakh</div><div class="ebf-tile__s">RBI rule for MSE loans' + (f.udyam ? "" : " (needs Udyam)") + '</div></div>' +
      '</div>';
    html += '<p class="scf-fine">Estimates are rough, for one scheme. You usually can\'t take two capital subsidies (for example PMEGP and a state scheme) for the same unit, so pick the bigger one. Banks decide on the loan.</p>';

    html += '<section class="scf-sec"><h2 class="scf-h">Your action plan</h2><ol class="scf-plan">' +
      plan(f, matches, best).map(function (st) { return '<li><strong>' + esc(st[0]) + '</strong><span>' + esc(st[1]) + '</span></li>'; }).join("") + '</ol></section>';

    GROUPS.forEach(function (g) {
      var list = matches.filter(function (m) { return groupOf(m.s) === g[0]; });
      if (!list.length) return;
      list.sort(function (a, b) { return (b.top ? 1 : 0) - (a.top ? 1 : 0) || (b.est ? b.est.v : 0) - (a.est ? a.est.v : 0) || (a.s.status === "open" ? -1 : 1) - (b.s.status === "open" ? -1 : 1); });
      html += '<section class="scf-sec"><h2 class="scf-h">' + esc(g[1]) + ' <span>' + list.length + '</span></h2><p class="scf-sub">' + esc(g[2]) + '</p>' +
        '<div class="scf-cards">' + list.map(function (m) { return card(m, f); }).join("") + '</div></section>';
    });

    html += '<section class="scf-sec"><h2 class="scf-h">Rights every micro and small business has</h2><p class="scf-sub">Not schemes you apply for. Protections and benefits that come with Udyam registration.</p><div class="scf-rights">' +
      C.rights.map(function (r) { return '<div><strong>' + esc(r[0]) + '</strong><p>' + esc(r[1]) + '</p></div>'; }).join("") + '</div></section>';

    html += '<section class="scf-sec scf-state"><h2 class="scf-h">More from ' + esc(f.state) + '</h2><p>Every state also has an industrial or MSME policy with capital subsidy, interest subsidy, stamp-duty and SGST reimbursement, and power-tariff support, at rates that depend on your district\'s zone. Ask at the District Industries Centre (DIC) in your district' +
      (portal ? ', or check the <a href="' + esc(portal) + '" target="_blank" rel="noopener">state industries portal ↗</a>' : "") + '.</p></section>';

    if (misses.length) {
      html += '<details class="scf-sec scf-miss"><summary>Schemes you don\'t match right now, and why (' + misses.length + ')</summary><ul>' +
        misses.map(function (m) { return '<li><strong>' + esc(m.s.name) + '</strong><span>' + esc(m.why) + '</span></li>'; }).join("") + '</ul></details>';
    }

    html += '<aside class="sf-help"><div><strong>Want help picking a scheme or preparing the file?</strong><p>Book a 1:1 call and we\'ll go through your report together.</p></div>' +
      '<a class="btn btn-cyan" href="' + esc(C.bookCallUrl) + '" target="_blank" rel="noopener" id="scfBook">Book a call</a></aside>';
    html += '<p class="scf-fine scf-disclaimer">Data updated ' + esc(C.reviewed) + '. This report is a guide, not an approval: schemes change, windows open and close, and the bank or agency makes the final call. Always check the official site before you apply. No government body is connected with KidharMilega.</p>';

    report.innerHTML = html;
    report.hidden = false;
    report.scrollIntoView({ behavior: "smooth", block: "start" });
    $("scfPrint").onclick = function () {
      report.querySelectorAll("details").forEach(function (d) { d.open = true; });
      track("scf_pdf", {}); window.print();
    };
    $("scfEdit").onclick = function () { form.scrollIntoView({ behavior: "smooth", block: "start" }); };
    $("scfWa").onclick = function () { track("scf_share", { app: "whatsapp" }); };
    $("scfBook").onclick = function () { track("scf_book_call", {}); };
    return matches;
  }

  // ── Leads ───────────────────────────────────────────────────────────────────
  function sendLead(event, f, matches) {
    var lead = store(LS_LEAD);
    if (!C.leadEndpoint || !lead) return;
    var qs = new URLSearchParams(location.search);
    var body = {
      event: event, email: lead.email, phone: lead.phone || "", product: C.sectors[f.sector] || f.sector,
      state: f.state, district: f.area, segment: f.stage,
      hsn_name: matches.length + " schemes",
      details: JSON.stringify({ age: f.age, g: f.gender, soc: f.social, pwd: f.pwd, ex: f.ex, proj: f.proj, turn: f.turn, exp: f.exp, ent: f.entity, udyam: f.udyam,
        m: matches.map(function (m) { return m.s.id; }) }),
      page: location.href.split("#")[0], referrer: document.referrer || "",
      utm_source: qs.get("utm_source") || "", utm_medium: qs.get("utm_medium") || "", utm_campaign: qs.get("utm_campaign") || ""
    };
    try {
      fetch(C.leadEndpoint, { method: "POST", mode: "no-cors", headers: { "Content-Type": "text/plain;charset=utf-8" }, body: JSON.stringify(body), keepalive: true });
    } catch (e) {}
  }

  function openGate() {
    gate.hidden = false; document.body.classList.add("sf-noscroll");
    var lead = store(LS_LEAD); if (lead) { $("scfEmail").value = lead.email || ""; $("scfPhone").value = lead.phone || ""; }
    setTimeout(function () { $("scfEmail").focus(); }, 30);
  }
  function closeGate() { gate.hidden = true; document.body.classList.remove("sf-noscroll"); }

  // ── Wiring ──────────────────────────────────────────────────────────────────
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var f = readForm();
    if (!validate(f)) return;
    profile = f; store(LS_FORM, f);
    var lead = store(LS_LEAD);
    if (lead && lead.email) { var m = render(f); sendLead("scheme_search", f, m); track("scf_generate", { returning: true, sector: f.sector, state: f.state }); }
    else openGate();
  });
  $("scfGateForm").addEventListener("submit", function (e) {
    e.preventDefault();
    var email = $("scfEmail").value.trim(), phone = $("scfPhone").value.replace(/[\s-]/g, ""), ge = $("scfGateError");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) { ge.textContent = "Enter a valid email."; $("scfEmail").focus(); return; }
    if (phone && !/^(\+?91)?[6-9]\d{9}$/.test(phone)) { ge.textContent = "Enter a 10-digit Indian mobile number, or leave it empty."; $("scfPhone").focus(); return; }
    ge.textContent = "";
    store(LS_LEAD, { email: email, phone: phone });
    closeGate();
    var m = render(profile); sendLead("scheme_report", profile, m);
    track("scf_lead", { sector: profile.sector, state: profile.state }); track("generate_lead", { method: "scheme_finder" });
  });
  $("scfGateClose").addEventListener("click", closeGate);
  gate.addEventListener("click", function (e) { if (e.target === gate) closeGate(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !gate.hidden) closeGate(); });

  // Prefill: saved answers, then ?state=&sector= (for links from product pages)
  writeForm(store(LS_FORM));
  var qs = new URLSearchParams(location.search);
  if (qs.get("state") && C.portals) $("scfState").value = qs.get("state");
  if (qs.get("sector") && C.sectors[qs.get("sector")]) $("scfSector").value = qs.get("sector");
})();
