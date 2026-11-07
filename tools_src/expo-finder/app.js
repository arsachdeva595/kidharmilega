/* KidharMilega Expo Finder: city + product + goal → email gate → expo report.
 * Fair, venue and city data come from window.EXF_CONFIG, written by expo_finder.py. */
(function () {
  "use strict";
  var C = window.EXF_CONFIG || {};
  var $ = function (id) { return document.getElementById(id); };
  var LS_LEAD = "sf_lead_v1", LS_FORM = "exf_form_v1";   // same lead key as the other tools: one email per browser
  var AE_SRC = "https://allevents.in/scripts/public/ae-plugin-embed-lib.js";
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var RADIUS = { city: 60, region: 600, india: Infinity };
  var RADIUS_TEXT = { city: "60 km", region: "600 km", india: "anywhere in India" };
  var KIND = { b2b: "Trade only", b2c: "Public / retail", mixed: "Trade + public days" };
  var GOAL_SHORT = { sell: "sell to visitors", trade: "find dealers and bulk buyers", "export": "meet export buyers", source: "find suppliers", learn: "study the market" };

  var form = $("exfForm"), errEl = $("exfError"), gate = $("exfGate"), report = $("exfReport");
  var profile = null;

  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function store(key, val) {
    try { if (val === undefined) return JSON.parse(localStorage.getItem(key) || "null"); localStorage.setItem(key, JSON.stringify(val)); }
    catch (e) { return null; }
  }
  function track(name, params) { try { if (window.gtag) window.gtag("event", name, params || {}); } catch (e) {} }
  function rupees(x) { return "₹" + Math.round(x).toLocaleString("en-IN"); }
  function shortSector(k) { return (C.sectors[k] || k).split(",")[0].split(" (")[0]; }

  function cityRow(name) {
    for (var i = 0; i < C.cities.length; i++) if (C.cities[i][0] === name) return C.cities[i];
    return null;
  }
  function km(a, b) {   // haversine, road distance is usually ~1.3x this
    var R = 6371, r = Math.PI / 180;
    var dLat = (b[0] - a[0]) * r, dLng = (b[1] - a[1]) * r;
    var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }

  // ── Form ────────────────────────────────────────────────────────────────────
  function radioVal(name) { var r = form.querySelector('input[name="' + name + '"]:checked'); return r ? r.value : ""; }
  function readForm() {
    return {
      city: $("exfCity").value, sector: $("exfSector").value, goal: radioVal("goal"), travel: radioVal("travel") || "region",
      udyam: $("exfUdyam").checked, women: $("exfWomen").checked, scst: $("exfScst").checked,
      artisan: $("exfArtisan").checked, shg: $("exfShg").checked, iec: $("exfIec").checked
    };
  }
  function writeForm(f) {
    if (!f) return;
    if (f.city) $("exfCity").value = f.city;
    if (f.sector) $("exfSector").value = f.sector;
    ["goal", "travel"].forEach(function (n) { var r = form.querySelector('input[name="' + n + '"][value="' + f[n] + '"]'); if (r) r.checked = true; });
    ["Udyam:udyam", "Women:women", "Scst:scst", "Artisan:artisan", "Shg:shg", "Iec:iec"].forEach(function (x) {
      var k = x.split(":"); $("exf" + k[0]).checked = !!f[k[1]];
    });
  }
  function validate(f) {
    errEl.textContent = "";
    var miss = !f.city ? "Select your city." : !f.sector ? "Choose what you make or sell." : !f.goal ? "Pick your main goal (step 2)." : "";
    if (miss) { errEl.textContent = miss; return false; }
    return true;
  }

  // ── Matching ────────────────────────────────────────────────────────────────
  function nextRun(months) {
    if (!months || !months.length) return null;
    var now = new Date(), m0 = now.getMonth() + 1, y0 = now.getFullYear(), best = null;
    months.forEach(function (m) {
      var d = (m - m0 + 12) % 12;
      if (best === null || d < best.d) best = { d: d, m: m, y: y0 + (m < m0 ? 1 : 0) };
    });
    return best;
  }
  function goalFit(fair, goal) {
    var k = fair.kind;
    if (goal === "sell") return k === "b2b" ? 0 : 2;
    if (goal === "trade") return k === "b2b" ? 2 : k === "mixed" ? 1.5 : 0;
    if (goal === "export") return fair.export ? 2 : 0;
    if (goal === "source") return k === "b2b" ? 2 : k === "mixed" ? 1 : 0;
    return k === "b2b" ? 1.5 : 1;   // learn
  }
  function evaluate(fair, f, home) {
    var exact = fair.sectors.indexOf(f.sector) >= 0, general = fair.sectors.indexOf("*") >= 0;
    if (!exact && !general) return null;
    var fit = goalFit(fair, f.goal);
    if (!fit) return null;
    var v = fair.venue ? C.venues[fair.venue] : null;
    var dist = v ? km(home, [v.lat, v.lng]) : null;
    var nx = nextRun(fair.months);
    var why = [];
    why.push(exact ? "Made for " + shortSector(f.sector).toLowerCase() : "General fair that takes most products, including yours");
    if (f.goal === "sell") why.push(fair.kind === "b2c" ? "Visitors come to shop, so you can sell on the spot" : "Public days let you sell on the spot");
    if (f.goal === "trade") why.push(fair.kind === "b2b" ? "Trade visitors: retailers, distributors and bulk buyers" : "Trade days bring dealers before the public days");
    if (f.goal === "export") why.push("Foreign buyers come to this fair");
    if (f.goal === "source") why.push("Suppliers and manufacturers exhibit here");
    if (f.goal === "learn") why.push("A good place to see what sells and meet people in your trade");
    var note = "";
    if (fair.only === "artisan" && !f.artisan) note = "Stalls go to registered artisans and weavers. Get a Pehchan card or weaver ID first.";
    if (fair.only === "shg" && !f.shg) note = "Only for self-help groups. Join or form an SHG through your block's livelihood mission.";
    var score = fit * 10 + (exact ? 8 : 0) + (note ? -12 : 0) + (fair.export && f.goal === "export" ? 3 : 0) - (nx ? nx.d * 0.4 : 3);
    return { fair: fair, venue: v, dist: dist, next: nx, why: why, note: note, exact: exact, score: score };
  }

  function match(f) {
    var row = cityRow(f.city), home = [row[2], row[3]], radius = RADIUS[f.travel];
    var near = [], trip = [], various = [];
    C.fairs.forEach(function (fair) {
      var m = evaluate(fair, f, home);
      if (!m) return;
      if (m.dist === null) various.push(m);
      else if (m.dist <= radius) near.push(m);
      else if (m.exact) trip.push(m);   // far away: only fairs made for this product are worth the trip
    });
    var byWhen = function (a, b) { return (a.next ? a.next.d : 13) - (b.next ? b.next.d : 13) || a.dist - b.dist; };
    near.sort(function (a, b) { return b.score - a.score || byWhen(a, b); });
    trip.sort(function (a, b) { return b.score - a.score || byWhen(a, b); });
    return { home: home, row: row, near: near, trip: trip.slice(0, 5), various: various };
  }

  // ── Report pieces ───────────────────────────────────────────────────────────
  function searchUrl(q) { return "https://www.google.com/search?q=" + encodeURIComponent(q); }
  function whenText(m) {
    var fair = m.fair;
    if (!fair.months.length) return "Dates vary by edition";
    if (fair.months.length === 12) return "All year, stalls rotate";
    var usual = "Usually " + fair.months.map(function (x) { return MONTHS[x - 1]; }).join("–");
    var nx = m.next;
    return usual + " · next likely " + MONTHS[nx.m - 1] + " " + nx.y + (nx.d === 0 ? " (this month)" : nx.d === 1 ? " (next month)" : " (in " + nx.d + " months)");
  }
  function card(m, f) {
    var fair = m.fair, v = m.venue;
    var place = v ? v.name + ", " + v.city + (m.dist != null && m.dist > 5 ? " · ~" + Math.round(m.dist / 10) * 10 + " km away" : m.dist != null ? " · in your city" : "") : "Held in different cities";
    var badges = '<span class="scf-badge">' + esc(KIND[fair.kind]) + '</span>' +
      (fair["export"] ? '<span class="scf-badge is-state">Export buyers</span>' : "");
    var links = (fair.url ? '<a class="btn btn-ghost btn-sm" href="' + esc(fair.url) + '" target="_blank" rel="noopener">Official site ↗</a>' : "") +
      '<a class="btn btn-ghost btn-sm" href="' + esc(searchUrl(fair.name + " " + (m.next ? m.next.y : new Date().getFullYear()) + " dates stall booking")) + '" target="_blank" rel="noopener">Find this year\'s dates ↗</a>';
    return '<article class="scf-card exf-card' + (m.top ? " is-top" : "") + '">' +
      '<div class="scf-card__meta">' + badges + '<span class="scf-kind">' + esc(fair.org) + '</span></div>' +
      '<h3 class="scf-card__title">' + esc(fair.name) + '</h3>' +
      '<p class="exf-when"><strong>' + esc(whenText(m)) + '</strong>' + (fair.next ? '<span>Next edition: ' + esc(fair.next) + '</span>' : "") + '</p>' +
      '<p class="exf-place">' + esc(place) + '</p>' +
      '<p class="scf-card__benefit">' + esc(fair.who) + '</p>' +
      '<ul class="scf-why">' + m.why.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join("") +
      '<li class="is-note">' + esc(fair.tip) + '</li></ul>' +
      (m.note ? '<p class="scf-status"><strong>Eligibility:</strong> ' + esc(m.note) + '</p>' : "") +
      '<div class="exf-links">' + links + '</div>' +
      '</article>';
  }
  function section(title, sub, list, f) {
    if (!list.length) return "";
    return '<section class="scf-sec"><h2 class="scf-h">' + esc(title) + ' <span>' + list.length + '</span></h2>' +
      (sub ? '<p class="scf-sub">' + esc(sub) + '</p>' : "") +
      '<div class="scf-cards">' + list.map(function (m) { return card(m, f); }).join("") + '</div></section>';
  }

  function venuesNear(home, radius) {
    var lim = Math.max(Math.min(radius, 400), 150), seen = {}, out = [];
    Object.keys(C.venues).forEach(function (k) {
      var v = C.venues[k];
      if (/announced each year/i.test(v.name)) return;
      var d = km(home, [v.lat, v.lng]);
      if (d <= lim && !seen[v.name]) { seen[v.name] = 1; out.push({ v: v, d: d }); }
    });
    return out.sort(function (a, b) { return a.d - b.d; }).slice(0, 6);
  }

  function supportFor(f) {
    return C.support.filter(function (s) {
      if (s.needs === "craft") return f.artisan || f.sector === "craft" || f.sector === "textile";
      if (s.needs === "scst") return f.scst;
      if (s.needs === "export") return f.iec || f.goal === "export";
      return true;
    });
  }
  function pmsRate(f) { return f.women || f.scst ? 1 : 0.8; }

  function cityPage(f) {
    var keys = [f.city, C.aeCity[f.city], f.city.split(" (")[0], f.city === "Delhi" ? "New Delhi" : null, f.city === "Bengaluru" ? "Bangalore" : null];
    for (var i = 0; i < keys.length; i++) if (keys[i] && C.cityPages[keys[i].toLowerCase()]) return C.cityPages[keys[i].toLowerCase()];
    return null;
  }

  function fillPrompt(t, f, budget) {
    var now = new Date(), later = new Date(now.getFullYear(), now.getMonth() + 6, 1);
    return t.replace(/\{city\}/g, f.city).replace(/\{radius\}/g, RADIUS_TEXT[f.travel])
      .replace(/\{sector\}/g, (C.sectors[f.sector] || "").toLowerCase()).replace(/\{goal\}/g, GOAL_SHORT[f.goal])
      .replace(/\{from\}/g, MONTHS[now.getMonth()] + " " + now.getFullYear()).replace(/\{to\}/g, MONTHS[later.getMonth()] + " " + later.getFullYear())
      .replace(/\{budget\}/g, budget);
  }

  // ── Budget calculator ───────────────────────────────────────────────────────
  var CALC = [
    ["rent", "Stall rent (total)", 40000, "Ask the organiser. Local melas often charge a flat fee; big trade fairs charge per square metre."],
    ["build", "Stall branding and fit-out", 15000, "Banner, lights, shelves, table cover. Shell-scheme stalls come with walls and basic furniture."],
    ["people", "People at the stall", 2, ""],
    ["days", "Days (including setup)", 5, ""],
    ["perday", "Stay + food per person per day", 2500, ""],
    ["tickets", "Travel tickets and goods transport", 8000, ""],
    ["print", "Printing, samples and giveaways", 7000, ""],
    ["margin", "Your profit per order", 0, "Profit on one order, not the price."]
  ];
  function calcHtml(f) {
    var margin = f.goal === "sell" ? 300 : 5000;
    return '<section class="scf-sec"><h2 class="scf-h">Will the stall pay back?</h2><p class="scf-sub">Change the numbers to match your quote. Everything updates as you type.</p>' +
      '<div class="exf-calc"><div class="exf-calc__in">' + CALC.map(function (c) {
        var val = c[0] === "margin" ? margin : c[2];
        return '<label class="exf-field"><span>' + esc(c[1]) + '</span><input class="sf-input" type="number" min="0" inputmode="numeric" data-k="' + c[0] + '" value="' + val + '">' +
          (c[3] ? '<small>' + esc(c[3]) + '</small>' : "") + '</label>';
      }).join("") + '</div><div class="exf-calc__out" id="exfCalcOut"></div></div></section>';
  }
  function calcRun(f) {
    var box = $("exfCalcOut"); if (!box) return;
    var v = {};
    report.querySelectorAll(".exf-calc input").forEach(function (i) { v[i.dataset.k] = Math.max(0, parseFloat(i.value) || 0); });
    var stay = v.people * v.days * v.perday;
    var total = v.rent + v.build + stay + v.tickets + v.print;
    var sub = f.udyam ? Math.min(v.rent * pmsRate(f), 30000) : 0;
    var net = total - sub;
    var orders = v.margin > 0 ? Math.ceil(net / v.margin) : null;
    var conv = f.goal === "sell" ? 0.25 : 0.1;
    box.innerHTML =
      '<div class="exf-row"><span>Total cost</span><strong>' + rupees(total) + '</strong></div>' +
      '<div class="exf-row"><span>Stay and food</span><span>' + rupees(stay) + '</span></div>' +
      '<div class="exf-row"><span>MSME stall-rent reimbursement' + (f.udyam ? " (if the fair is approved)" : "") + '</span><span>' + (f.udyam ? "– " + rupees(sub) : "Needs Udyam") + '</span></div>' +
      '<div class="exf-row is-total"><span>Your real cost</span><strong>' + rupees(net) + '</strong></div>' +
      (orders != null ? '<div class="exf-be"><strong>' + orders.toLocaleString("en-IN") + ' orders</strong> to break even' +
        '<small>That means talking seriously to about ' + Math.ceil(orders / conv).toLocaleString("en-IN") + ' visitors' + (f.goal === "sell" ? " (if 1 in 4 buys)" : " (if 1 in 10 leads becomes an order)") + '. Count repeat orders from fair leads too: B2B buyers often order over the next 3–6 months.</small></div>'
        : '<div class="exf-be"><small>Add your profit per order to see how many orders you need.</small></div>');
    return net;
  }

  // ── Report ──────────────────────────────────────────────────────────────────
  function render(f) {
    var r = match(f);
    var all = r.near.concat(r.trip);
    var soonest = all.filter(function (m) { return m.next && m.fair.months.length < 12; }).sort(function (a, b) { return a.next.d - b.next.d || b.score - a.score; })[0];
    if (r.near[0]) r.near[0].top = true; else if (r.trip[0]) r.trip[0].top = true;
    var page = cityPage(f);
    var aeCity = C.aeCity[f.city] || f.city;
    var aeCat = f.goal === "sell" ? "Exhibitions" : "Business";
    var today = new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });
    var total = all.length + r.various.length;
    var chips = [f.city + " (" + r.row[1] + ")", shortSector(f.sector), "Goal: " + GOAL_SHORT[f.goal], "Travel: " + RADIUS_TEXT[f.travel],
      f.udyam ? "Udyam" : null, f.women ? "Woman-owned" : null, f.scst ? "SC/ST" : null, f.artisan ? "Artisan card" : null, f.shg ? "SHG" : null, f.iec ? "Exporter" : null].filter(Boolean);

    var html = '<div class="scf-report__head">' +
      '<div class="section-label">Your expo report · ' + esc(today) + '</div>' +
      '<h2 class="section-title">' + total + ' fairs worth your time</h2>' +
      '<div class="scf-chips">' + chips.map(function (c) { return '<span>' + esc(c) + '</span>'; }).join("") + '</div>' +
      '<div class="scf-actions"><button class="btn btn-primary btn-sm" type="button" id="exfPrint">Download PDF</button>' +
      '<a class="btn btn-ghost btn-sm" id="exfWa" target="_blank" rel="noopener" href="https://wa.me/?text=' + encodeURIComponent("Find trade fairs and expos worth a stall for your business (free report): " + location.href.split("#")[0].split("?")[0]) + '">Share on WhatsApp</a>' +
      '<button class="btn btn-ghost btn-sm" type="button" id="exfEdit">Edit answers</button></div></div>';

    html += '<div class="ebf-tiles scf-tiles">' +
      '<div class="ebf-tile"><div class="ebf-tile__l">Fairs that fit</div><div class="ebf-tile__v">' + total + '</div><div class="ebf-tile__s">' + r.near.length + ' within ' + esc(RADIUS_TEXT[f.travel]) + (r.trip.length ? ", " + r.trip.length + " worth the trip" : "") + '</div></div>' +
      '<div class="ebf-tile"><div class="ebf-tile__l">Next one up</div><div class="ebf-tile__v">' + (soonest ? MONTHS[soonest.next.m - 1] + " " + soonest.next.y : "–") + '</div><div class="ebf-tile__s">' + (soonest ? esc(soonest.fair.name.split(" (")[0]) : "Check live events below") + '</div></div>' +
      '<div class="ebf-tile"><div class="ebf-tile__l">Stall subsidy</div><div class="ebf-tile__v">' + (pmsRate(f) === 1 ? "100%" : "80%") + '</div><div class="ebf-tile__s">of stall rent, up to ₹30,000' + (f.udyam ? " at approved fairs" : " (needs Udyam)") + '</div></div>' +
      '</div>';
    html += '<p class="scf-fine">Fair months are the usual ones; organisers move dates. Always confirm dates and stall rates on the official site before you book travel or pay.</p>';

    // Live events in the city
    html += '<section class="scf-sec"><h2 class="scf-h">What\'s on in ' + esc(f.city) + ' right now</h2>' +
      '<p class="scf-sub">Live listings of upcoming exhibitions and business events from AllEvents. Smaller local expos and melas show up here before anywhere else.' +
      (page ? ' See also our <a href="' + esc(page) + '">' + esc(f.city.split(" (")[0]) + ' events page</a>.' : "") + '</p>' +
      '<div class="exf-ae"><div class="ae-embed-plugin" data-type="city" data-cityname="' + esc(aeCity) + '" data-category="' + aeCat + '" data-height="460" data-width="100%" data-header="1" data-border="0" data-transparency=""></div></div></section>';

    html += section("Fairs near you", "Within " + RADIUS_TEXT[f.travel] + " of " + f.city + ", best fit first.", r.near, f);
    if (!r.near.length) html += '<section class="scf-sec"><h2 class="scf-h">Fairs near you</h2><p class="scf-sub">None of the big recurring fairs we track fit you within ' + esc(RADIUS_TEXT[f.travel]) + '. Use the live listings above and the first AI prompt below to find local expos' + (f.travel !== "india" ? ", or look at the fairs worth the trip." : ".") + '</p></section>';
    html += section("Worth the trip", "Further away, but made for your product. One good fair a year can be worth more than five local ones.", r.trip, f);
    html += section("Held in many cities", "Government-run bazaars that travel. Watch for the next one near you.", r.various, f);

    var vn = venuesNear(r.home, RADIUS[f.travel]);
    if (vn.length) {
      html += '<section class="scf-sec"><h2 class="scf-h">Exhibition venues near you</h2><p class="scf-sub">Most fairs in your area happen at these grounds. Their event calendars show what\'s coming before organisers advertise.</p><ul class="exf-venues">' +
        vn.map(function (x) {
          return '<li><strong>' + esc(x.v.name) + '</strong><span>' + esc(x.v.city) + (x.d > 5 ? " · ~" + Math.round(x.d / 10) * 10 + " km" : "") + '</span>' +
            '<a href="' + esc(x.v.url || searchUrl(x.v.name + " " + x.v.city + " upcoming events")) + '" target="_blank" rel="noopener">' + (x.v.url ? "Website ↗" : "Upcoming events ↗") + '</a></li>';
        }).join("") + '</ul></section>';
    }

    html += '<section class="scf-sec"><h2 class="scf-h">Get a cheaper stall</h2><p class="scf-sub">Most small businesses pay full price because nobody told them about these.</p><div class="scf-cards">' +
      supportFor(f).map(function (s) {
        var warn = s.needs === "udyam" && !f.udyam ? '<p class="scf-status"><strong>First step:</strong> register on Udyam (free, udyamregistration.gov.in). This reimbursement needs it.</p>' : "";
        return '<article class="scf-card"><h3 class="scf-card__title">' + esc(s.name) + '</h3><p class="scf-card__benefit">' + esc(s.benefit) + '</p>' +
          '<ul class="scf-why"><li>' + esc("For: " + s.who) + '</li><li class="is-note">' + esc(s.how) + '</li></ul>' + warn +
          (s.url ? '<a class="btn btn-ghost btn-sm scf-link" href="' + esc(s.url) + '" target="_blank" rel="noopener">Official site ↗</a>' : "") + '</article>';
      }).join("") + '</div><p class="scf-fine" style="margin-top:12px">Figures as commonly published for the scheme; confirm the current rules and approved fair list with your MSME-DFO. Want every scheme you qualify for? <a href="' + esc(C.schemeFinder) + '">Try the Scheme Finder</a>.</p></section>';

    html += calcHtml(f);

    html += '<section class="scf-sec"><h2 class="scf-h">AI prompts to go further</h2><p class="scf-sub">Copy into ChatGPT, Claude, Gemini or Perplexity (one with web search works best). Filled in for you.</p><div class="exf-prompts">' +
      Object.keys(C.prompts).map(function (k, i) {
        var p = C.prompts[k];
        return '<details class="exf-prompt"' + (i === 0 ? " open" : "") + '><summary>' + esc(p[0]) + '</summary><pre id="exfP' + k + '">' + esc(fillPrompt(p[1], f, "60,000–1,00,000")) + '</pre>' +
          '<button class="btn btn-ghost btn-sm exf-copy" type="button" data-p="exfP' + k + '">Copy prompt</button></details>';
      }).join("") + '</div></section>';

    html += '<section class="scf-sec"><h2 class="scf-h">Your expo checklist</h2><div class="exf-check">' +
      C.checklist.map(function (g) {
        return '<div><h3>' + esc(g[0]) + '</h3><ul>' + g[1].map(function (x) { return '<li><label><input type="checkbox"><span>' + esc(x) + '</span></label></li>'; }).join("") + '</ul></div>';
      }).join("") + '</div></section>';
    html += '<section class="scf-sec exf-flags"><h2 class="scf-h">Red flags of a fake or weak expo</h2><ul>' +
      C.redFlags.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join("") + '</ul></section>';

    html += '<aside class="sf-help"><div><strong>Not sure which fair to pick, or how to set up the stall?</strong><p>Book a 1:1 call and we\'ll go through your report together.</p></div>' +
      '<a class="btn btn-cyan" href="' + esc(C.bookCallUrl) + '" target="_blank" rel="noopener" id="exfBook">Book a call</a></aside>';
    html += '<p class="scf-fine scf-disclaimer">Fair data reviewed ' + esc(C.reviewed) + '. Distances are straight-line. KidharMilega is not connected with any organiser or government body listed here and takes no fee from them. Confirm everything with the organiser before you pay.</p>';

    report.innerHTML = html;
    report.hidden = false;
    report.scrollIntoView({ behavior: "smooth", block: "start" });

    // AllEvents scans the page when its script loads, so load it again for each new report.
    var old = $("exfAeScript"); if (old) old.parentNode.removeChild(old);
    var s = document.createElement("script"); s.id = "exfAeScript"; s.src = AE_SRC + "?t=" + Date.now(); s.async = true; document.body.appendChild(s);

    calcRun(f);
    report.querySelectorAll(".exf-calc input").forEach(function (i) { i.addEventListener("input", function () { calcRun(f); }); });
    report.querySelectorAll(".exf-copy").forEach(function (b) {
      b.addEventListener("click", function () {
        var text = $(b.dataset.p).textContent;
        var done = function () { b.textContent = "Copied ✓"; setTimeout(function () { b.textContent = "Copy prompt"; }, 1800); };
        track("exf_copy_prompt", { id: b.dataset.p });
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text); done(); });
        else { fallbackCopy(text); done(); }
      });
    });
    $("exfPrint").onclick = function () {
      report.querySelectorAll("details").forEach(function (d) { d.open = true; });
      track("exf_pdf", {}); window.print();
    };
    $("exfEdit").onclick = function () { form.scrollIntoView({ behavior: "smooth", block: "start" }); };
    $("exfWa").onclick = function () { track("exf_share", { app: "whatsapp" }); };
    $("exfBook").onclick = function () { track("exf_book_call", {}); };
    return all.concat(r.various);
  }
  function fallbackCopy(text) {
    var t = document.createElement("textarea"); t.value = text; t.style.position = "fixed"; t.style.opacity = "0";
    document.body.appendChild(t); t.select(); try { document.execCommand("copy"); } catch (e) {} document.body.removeChild(t);
  }

  // ── Leads ───────────────────────────────────────────────────────────────────
  function sendLead(event, f, matches) {
    var lead = store(LS_LEAD);
    if (!C.leadEndpoint || !lead) return;
    var qs = new URLSearchParams(location.search), row = cityRow(f.city);
    var body = {
      event: event, email: lead.email, phone: lead.phone || "", product: C.sectors[f.sector] || f.sector,
      state: row ? row[1] : "", district: f.city, segment: f.goal,
      hsn_name: matches.length + " fairs",
      details: JSON.stringify({ travel: f.travel, udyam: f.udyam, w: f.women, scst: f.scst, art: f.artisan, shg: f.shg, iec: f.iec,
        m: matches.map(function (m) { return m.fair.id; }) }),
      page: location.href.split("#")[0], referrer: document.referrer || "",
      utm_source: qs.get("utm_source") || "", utm_medium: qs.get("utm_medium") || "", utm_campaign: qs.get("utm_campaign") || ""
    };
    try {
      fetch(C.leadEndpoint, { method: "POST", mode: "no-cors", headers: { "Content-Type": "text/plain;charset=utf-8" }, body: JSON.stringify(body), keepalive: true });
    } catch (e) {}
  }

  function openGate() {
    gate.hidden = false; document.body.classList.add("sf-noscroll");
    var lead = store(LS_LEAD); if (lead) { $("exfEmail").value = lead.email || ""; $("exfPhone").value = lead.phone || ""; }
    setTimeout(function () { $("exfEmail").focus(); }, 30);
  }
  function closeGate() { gate.hidden = true; document.body.classList.remove("sf-noscroll"); }

  // ── Wiring ──────────────────────────────────────────────────────────────────
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var f = readForm();
    if (!validate(f)) return;
    profile = f; store(LS_FORM, f);
    var lead = store(LS_LEAD);
    if (lead && lead.email) { var m = render(f); sendLead("expo_search", f, m); track("exf_generate", { returning: true, sector: f.sector, city: f.city, goal: f.goal }); }
    else openGate();
  });
  $("exfGateForm").addEventListener("submit", function (e) {
    e.preventDefault();
    var email = $("exfEmail").value.trim(), phone = $("exfPhone").value.replace(/[\s-]/g, ""), ge = $("exfGateError");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) { ge.textContent = "Enter a valid email."; $("exfEmail").focus(); return; }
    if (phone && !/^(\+?91)?[6-9]\d{9}$/.test(phone)) { ge.textContent = "Enter a 10-digit Indian mobile number, or leave it empty."; $("exfPhone").focus(); return; }
    ge.textContent = "";
    store(LS_LEAD, { email: email, phone: phone });
    closeGate();
    var m = render(profile); sendLead("expo_report", profile, m);
    track("exf_lead", { sector: profile.sector, city: profile.city }); track("generate_lead", { method: "expo_finder" });
  });
  $("exfGateClose").addEventListener("click", closeGate);
  gate.addEventListener("click", function (e) { if (e.target === gate) closeGate(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !gate.hidden) closeGate(); });

  // Prefill: saved answers, then ?city=&sector=&goal= (for links from city event pages)
  writeForm(store(LS_FORM));
  var qs = new URLSearchParams(location.search);
  var qc = qs.get("city");
  if (qc) {
    var lc = qc.toLowerCase(), hit = null;
    C.cities.forEach(function (c) { if (!hit && (c[0].toLowerCase() === lc || c[0].toLowerCase().split(" (")[0] === lc || (C.aeCity[c[0]] || "").toLowerCase() === lc)) hit = c[0]; });
    if (!hit && lc === "new delhi") hit = "Delhi";
    if (!hit && lc === "bangalore") hit = "Bengaluru";
    if (hit) $("exfCity").value = hit;
  }
  if (qs.get("sector") && C.sectors[qs.get("sector")]) $("exfSector").value = qs.get("sector");
  if (qs.get("goal")) { var g = form.querySelector('input[name="goal"][value="' + qs.get("goal") + '"]'); if (g) g.checked = true; }
})();
