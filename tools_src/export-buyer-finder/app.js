/* KidharMilega Export Buyer Finder (teaser): HSN → US import snapshot (UN Comtrade) → buyer-list waitlist.
 * Config from window.EBF_CONFIG (export_buyer_finder.py). HSN search from /tools/shared/hsn-search.js. */
(function () {
  "use strict";
  var C = window.EBF_CONFIG || {}, H = window.KMHSN, esc = H.esc;
  var $ = function (id) { return document.getElementById(id); };
  var LS_LEAD = "ebf_lead_v1", INDIA = 699;
  var META = C.meta || {}, MUS = META.us || {}, MIN = META["in"] || {}, NAMES = META.partners || {};
  var YEARS = MUS.years || [], IYEARS = MIN.years || [], US = 842, MCA = META.ca || null;
  var els = {
    form: $("ebfForm"), hsn: $("ebfHsn"), list: $("ebfHsnList"), status: $("ebfHsnStatus"), picked: $("ebfPicked"),
    error: $("ebfError"), results: $("ebfResults"), title: $("ebfTitle"), sub: $("ebfSub"), market: $("ebfMarket"),
    waitCode: $("ebfWaitCode"), waitForm: $("ebfWaitForm"), email: $("ebfEmail"), phone: $("ebfPhone"), seg: $("ebfSeg"),
    waitError: $("ebfWaitError"), done: $("ebfDone"), doneEmail: $("ebfDoneEmail"), sfLink: $("ebfSfLink")
  };
  var selected = null, combo, chapters = { us: {}, "in": {}, ca: {} }, caRows = [], caShowAll = false;

  function store(key, val) {
    try { if (val === undefined) return JSON.parse(localStorage.getItem(key) || "null"); localStorage.setItem(key, JSON.stringify(val)); }
    catch (e) { return null; }
  }
  function track(name, params) { try { if (window.gtag) window.gtag("event", name, params || {}); } catch (e) {} }

  function usd(v) {
    if (v == null) return "–";
    var a = Math.abs(v);
    if (a >= 1e9) return "$" + (v / 1e9).toFixed(a >= 1e10 ? 0 : 1) + "B";
    if (a >= 1e6) return "$" + (v / 1e6).toFixed(a >= 1e8 ? 0 : 1) + "M";
    if (a >= 1e3) return "$" + Math.round(v / 1e3) + "K";
    return "$" + Math.round(v);
  }
  function pct(x) { return x == null ? "–" : (x >= 0.1 ? (x * 100).toFixed(0) : (x * 100).toFixed(1)) + "%"; }
  function country(code) { return NAMES[String(code)] || ("Country " + code); }

  // ── Picking ────────────────────────────────────────────────────────────────
  function pick(l) {
    selected = l;
    els.picked.innerHTML =
      '<div class="sf-picked__code">HSN ' + esc(H.fmtCode(l.code)) + ' <span class="sf-opt">→ US data for HS ' + esc(l.code.slice(0, 6)) + '</span></div>' +
      '<div class="sf-picked__title">' + esc(l.title || l.heading) + '</div>' +
      (l.detail ? '<div class="sf-picked__detail">Tariff line: ' + esc(l.detail) + '</div>' : "") +
      '<button type="button" class="sf-link" id="ebfChange">Change</button>';
    els.picked.hidden = false;
    $("ebfChange").onclick = function () { unpick(); combo.clear(); };
    track("ebf_pick_hsn", { hsn: l.code });
  }
  function unpick() { selected = null; els.picked.hidden = true; }

  // ── Data ───────────────────────────────────────────────────────────────────
  function loadChapter(key, ch) {
    var m = META[key], cache = chapters[key];
    if (cache[ch]) return Promise.resolve(cache[ch]);
    if (!m || (m.chapters && m.chapters.indexOf(ch) < 0)) return Promise.resolve({});
    return fetch(C.dataBase + key + "/" + ch + ".json").then(function (r) { return r.ok ? r.json() : {}; })
      .catch(function () { return {}; }).then(function (d) { cache[ch] = d; return d; });
  }

  // Exact HS6 row, else the 4-digit heading summed (no supplier ranking then).
  function rowFor(code, data, years) {
    var h6 = code.slice(0, 6);
    if (data[h6]) return { level: "hs6", code: h6, row: data[h6] };
    // Whole heading: add up its HS6 codes. The country ranking adds up each code's top list, so very small
    // partners can be missing, but the leaders are right.
    var h4 = code.slice(0, 4), w = years.map(function () { return null; }), i = w.slice(), any = false, sum = {};
    Object.keys(data).forEach(function (k) {
      if (k.indexOf(h4) !== 0) return;
      any = true;
      data[k].w.forEach(function (v, j) { if (v != null) w[j] = (w[j] || 0) + v; });
      (data[k].i || []).forEach(function (v, j) { if (v != null) i[j] = (i[j] || 0) + v; });
      (data[k].top || []).forEach(function (t) { sum[t[0]] = (sum[t[0]] || 0) + t[1]; });
    });
    if (!any) return null;
    var top = Object.keys(sum).map(function (p) { return [+p, sum[p]]; }).sort(function (a, b) { return b[1] - a[1]; });
    var r = null;
    top.forEach(function (t, j) { if (t[0] === INDIA && r === null) r = j + 1; });
    return { level: "hs4", code: h4, row: { w: w, i: i, top: top.slice(0, 10), n: null, r: r } };
  }

  function latestIdx(arr) { for (var k = arr.length - 1; k >= 0; k--) if (arr[k] != null) return k; return -1; }

  // ── Render ─────────────────────────────────────────────────────────────────
  function render() {
    var l = selected, name = H.shortName(l), ch = l.code.slice(0, 2);
    els.title.textContent = "Export market for " + name;
    els.sub.textContent = "HSN " + H.fmtCode(l.code) + " · " + (l.title || l.heading);
    els.waitCode.textContent = "HSN " + H.fmtCode(l.code);
    els.sfLink.href = C.supplierFinder + "?hsn=" + encodeURIComponent(l.code);
    els.market.innerHTML = '<p class="sf-hint">Loading trade data…</p>';
    show();
    Promise.all([loadChapter("in", ch), loadChapter("us", ch), loadChapter("ca", ch)]).then(function (res) {
      if (selected !== l) return;
      var hin = IYEARS.length ? rowFor(l.code, res[0], IYEARS) : null, hus = YEARS.length ? rowFor(l.code, res[1], YEARS) : null;
      var html = "";
      if (hin) html += indiaHtml(hin);
      else if (IYEARS.length) html += '<p class="ebf-note">No India export records for this code in ' + IYEARS[0] + "–" + IYEARS[IYEARS.length - 1] + '. India may report it under a nearby code. Try a related product.</p>';
      html += '<div id="ebfCa">' + canadaHtml(l.code, res[2]) + '</div>';
      if (hus) html += '<h2 class="ebf-h2" id="ebfUs">The US market in detail</h2>' + marketHtml(hus);
      else if (YEARS.length) html += '<p class="ebf-note">No US import records for this code in ' + YEARS[0] + "–" + YEARS[YEARS.length - 1] + '. The US may classify it under a nearby code.</p>';
      els.market.innerHTML = html || '<p class="ebf-note">Trade data is being updated. Join the waitlist below and check back soon.</p>';
    });
  }

  // ── Canadian importers from India (named) ────────────────────────────────
  function caFor(code, data) {
    var h6 = code.slice(0, 6);
    if (data[h6]) return { level: "hs6", code: h6, rows: data[h6] };
    var h4 = code.slice(0, 4), seen = {}, rows = [];
    Object.keys(data).sort().forEach(function (k) {
      if (k.indexOf(h4) !== 0) return;
      data[k].forEach(function (r) { if (!seen[r[0]]) { seen[r[0]] = 1; rows.push(r); } });
    });
    var RANK = { specialist: 3, other: 2, chain: 1, luxury: 0 };
    rows.sort(function (a, b) { return (RANK[b[3]] - RANK[a[3]]) || (a[4] - b[4]) || (Math.min(b[5], 10) - Math.min(a[5], 10)) || (a[0] < b[0] ? -1 : 1); });
    return rows.length ? { level: "hs4", code: h4, rows: rows } : null;
  }
  function nice(name) {
    return name.toLowerCase().replace(/(^|[\s\/(&.-])([a-z\u00e0-\u00ff])/g, function (m, a, b) { return a + b.toUpperCase(); })
      .replace(/(\s)(And|Of|The|For|Du|De|Des|Et)(?=\s)/g, function (m, sp, w) { return sp + w.toLowerCase(); })
      .replace(/\b(Llc|Ulc|Lp|Llp|Plc|Uk|Usa|Bc)\b/g, function (m) { return m.toUpperCase(); });
  }
  function canadaHtml(code, data) {
    if (!MCA) return "";
    var hit = caFor(code, data);
    var head = '<h2 class="ebf-h2">Canadian companies importing this from India</h2>';
    if (!hit) return head + '<p class="ebf-note">No Canadian importer of this code from India is listed for ' + MCA.year + '.</p>';
    caRows = hit.rows;
    var n = caRows.length, unlocked = !!store(LS_LEAD), show = unlocked && caShowAll ? n : Math.min(10, n);
    var html = head + '<p class="section-sub" style="margin-bottom:var(--space-md)"><strong>' + n + '</strong> ' + (n === 1 ? "company" : "companies") +
      ' imported HS ' + esc(hit.code) + ' from India in ' + MCA.year + ', named in Canadian government data.' +
      (hit.level === "hs4" ? ' No exact list for HS ' + esc(code.slice(0, 6)) + ', so this covers the whole heading.' : "") + '</p>';
    html += '<ol class="ebf-buyers">' + caRows.slice(0, show).map(function (r) {
      var tags = '<span class="ebf-tag is-proof">Imports this from India</span>';
      if (r[3] === "chain") tags += '<span class="ebf-tag">Big retail chain</span>';
      if (r[3] === "luxury") tags += '<span class="ebf-tag">Luxury brand, sources in-house</span>';
      if (r[4]) tags += '<span class="ebf-tag">Based outside Canada</span>';
      return '<li><div class="ebf-buyers__n">' + esc(nice(r[0])) + '</div><div class="ebf-buyers__m">' + esc(r[1]) + ', ' + esc(r[2]) +
        (r[5] ? ' · also imports ' + r[5] + ' related product' + (r[5] === 1 ? "" : "s") + ' from India' : "") + '</div><div class="ebf-tags">' + tags + '</div></li>';
    }).join("") + '</ol>';
    if (n > show) {
      html += unlocked ? '<button type="button" class="btn btn-ghost btn-sm" id="ebfCaAll">Show all ' + n + ' companies</button>'
        : '<p class="ebf-more"><strong>+' + (n - show) + ' more companies.</strong> <a href="#ebfWait">Join the free waitlist</a> to see the full list.</p>';
    }
    html += '<p class="ebf-source">' + esc(MCA.licence) + ' Source: ' + esc(MCA.source) + ', ' + MCA.year + '. The list shows who imported, not how much. Contacts are not included.</p>';
    return html;
  }
  function refreshCanada() {
    var box = $("ebfCa"); if (!box || !selected) return;
    loadChapter("ca", selected.code.slice(0, 2)).then(function (d) { box.innerHTML = canadaHtml(selected.code, d); });
  }

  // India → every destination (single series for the trend; destinations ranked, US marked).
  function indiaHtml(hit) {
    var r = hit.row, k = latestIdx(r.w), yr = IYEARS[k], W = r.w[k], top = r.top || [];
    var html = hit.level === "hs4" ? '<p class="ebf-note">No exact India data for HS ' + esc(selected.code.slice(0, 6)) + ', so this shows the whole heading ' + esc(hit.code) + '.</p>' : "";
    var lead = top[0];
    html += '<div class="ebf-tiles">' +
      tile("India's exports to the world, " + yr, usd(W), "") +
      tile("Top buyer country", lead ? country(lead[0]) : "–", lead && W ? pct(lead[1] / W) + " of India's exports" : "") +
      tile("Countries buying it", r.n ? String(r.n) : "–", "from India in " + yr) +

      '</div>';
    html += columns("India → world, " + IYEARS[0] + "–" + IYEARS[IYEARS.length - 1], r.w, IYEARS, null);
    if (top.length) {
      html += '<div class="ebf-card"><h3>Top ' + top.length + ' countries buying this from India, ' + yr + '</h3><ol class="ebf-bars">' +
        top.map(function (t, j) { return barRow(j + 1, t[0], t[1], top[0][1], W, US); }).join("") + '</ol>' +
        (top.some(function (t) { return t[0] === US; }) ? '<p class="ebf-trend"><a href="#ebfUs">See the US market in detail ↓</a></p>' : "") + '</div>';
      var share3 = W ? top.slice(0, 3).reduce(function (a, t) { return a + t[1]; }, 0) / W : null, tips = [];
      if (share3 != null) tips.push("The top 3 countries take <strong>" + pct(share3) + "</strong> of India's exports of this product." + (share3 > 0.7 ? " Buyers are concentrated, so start with these markets." : " Demand is spread out, so smaller markets are worth a look too."));
      var a = firstIdx(r.w);
      if (a >= 0 && k > a && r.w[a]) {
        var g = W / r.w[a] - 1;
        tips.push("India's exports of this " + (Math.abs(g) < 0.02 ? "<strong>stayed flat</strong>" : g > 0 ? "grew <strong>" + pct(g) + "</strong>" : "fell <strong>" + pct(-g) + "</strong>") + " between " + IYEARS[a] + " and " + IYEARS[k] + ".");
      }
      html += '<div class="ebf-card ebf-insights"><h3>What this means for you</h3><ul>' + tips.map(function (t) { return "<li>" + t + "</li>"; }).join("") + '</ul></div>';
    }
    html += '<p class="ebf-source">Source: ' + esc(MIN.source || "UN Comtrade") + '. India-reported export values (FOB), HS ' + esc(hit.code) +
      '. Rankings computed by KidharMilega. Data pulled ' + esc(MIN.fetched || "") + '.</p>';
    return html;
  }

  function show() {
    els.results.hidden = false;
    els.results.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function marketHtml(hit) {
    var r = hit.row, k = latestIdx(r.w), yr = YEARS[k], W = r.w[k], I = r.i[k] || 0, share = W ? I / W : null;
    var html = "";
    if (hit.level === "hs4") html += '<p class="ebf-note">No exact US data for HS ' + esc(selected.code.slice(0, 6)) + ', so this shows the whole heading ' + esc(hit.code) + '.</p>';

    html += '<div class="ebf-tiles">' +
      tile("US imports from the world, " + yr, usd(W), "") +
      tile("From India, " + yr, usd(I), !I ? "None recorded" : share != null ? pct(share) + " of the US market" : "") +
      tile("India's rank", r.r ? "#" + r.r : (I ? "–" : "Not shipping"), r.n ? "of " + r.n + " supplier countries" : (hit.level === "hs4" && r.r ? "across the heading" : "")) +
      '</div>';

    // India's sales to the US by year (single series → no legend).
    html += columns("India → US, " + YEARS[0] + "–" + YEARS[YEARS.length - 1], r.i, YEARS, r.w, trendLine(r));

    // Top supplier countries, India highlighted.
    if (r.top && r.top.length) {
      var topMax = r.top[0][1], rows = r.top.slice(), indiaIn = rows.some(function (t) { return t[0] === INDIA; });
      html += '<div class="ebf-card"><h3>Who the US buys from, ' + yr + '</h3><ol class="ebf-bars">' +
        rows.map(function (t, j) { return barRow(j + 1, t[0], t[1], topMax, W); }).join("") +
        (!indiaIn && I ? '<li class="ebf-gap" aria-hidden="true">…</li>' + barRow(r.r, INDIA, I, topMax, W) : "") +
        '</ol></div>';
    }

    html += '<div class="ebf-card ebf-insights"><h3>What this means for you</h3><ul>' + insights(r, k).map(function (s) { return "<li>" + s + "</li>"; }).join("") + '</ul></div>';
    html += '<p class="ebf-source">Source: ' + esc(MUS.source || "UN Comtrade") + '. US-reported import values (CIF), HS ' + esc(hit.code) +
      '. Rankings computed by KidharMilega. Data pulled ' + esc(MUS.fetched || "") + '. Values for the latest year may still be revised.</p>';
    return html;
  }

  // Year columns for one series. shareOf (optional) adds "x% of …" to each tooltip.
  function columns(title, vals, years, shareOf, foot) {
    var fi = firstIdx(vals), li = latestIdx(vals);
    if (fi < 0 || li <= fi) return "";
    var max = Math.max.apply(null, vals.map(function (v) { return v || 0; })) || 1;
    return '<div class="ebf-card"><h3>' + esc(title) + '</h3><div class="ebf-cols" role="img" aria-label="' + esc(title) + '">' +
      years.map(function (y, j) {
        var v = vals[j], h = v ? Math.max(2, Math.round(v / max * 100)) : 0, sh = shareOf && shareOf[j] ? (v || 0) / shareOf[j] : null;
        return '<div class="ebf-col" title="' + y + ": " + usd(v) + (sh != null ? " (" + pct(sh) + " of US imports)" : "") + '">' +
          '<span class="ebf-col__v">' + ((j === fi || j === li) && v ? usd(v) : "") + '</span>' +
          '<span class="ebf-col__bar"><span style="height:' + h + '%"></span></span><span class="ebf-col__y">' + y + '</span></div>';
      }).join("") + '</div>' + (foot || "") + '</div>';
  }

  function tile(label, value, sub) {
    if (value === "–") return "";
    return '<div class="ebf-tile"><div class="ebf-tile__l">' + esc(label) + '</div><div class="ebf-tile__v">' + esc(value) + '</div>' +
      (sub ? '<div class="ebf-tile__s">' + esc(sub) + '</div>' : "") + '</div>';
  }
  function barRow(rank, code, v, max, W, mark) {
    var isIn = code === (mark || INDIA);
    return '<li class="' + (isIn ? "is-india" : "") + '" title="' + esc(country(code)) + ": " + usd(v) + (W ? " (" + pct(v / W) + ")" : "") + '">' +
      '<span class="ebf-bars__n">' + (rank || "") + '</span><span class="ebf-bars__c">' + esc(country(code)) + '</span>' +
      '<span class="ebf-bars__t"><span style="width:' + Math.max(1, v / max * 100) + '%"></span></span>' +
      '<span class="ebf-bars__v">' + usd(v) + (W ? ' <small>' + pct(v / W) + '</small>' : "") + '</span></li>';
  }

  function firstIdx(arr) { for (var k = 0; k < arr.length; k++) if (arr[k]) return k; return -1; }
  function trendLine(r) {
    var a = firstIdx(r.i), b = latestIdx(r.i);
    if (a < 0 || b <= a) return "";
    var ch = r.i[b] / r.i[a] - 1, sa = r.w[a] ? r.i[a] / r.w[a] : null, sb = r.w[b] ? r.i[b] / r.w[b] : null;
    return '<p class="ebf-trend">' + (Math.abs(ch) < 0.02 ? "Flat" : (ch > 0 ? "Up " : "Down ") + pct(Math.abs(ch))) + " since " + YEARS[a] +
      (sa != null && sb != null ? (pct(sa) === pct(sb) ? ". India's share of US imports held at about " + pct(sb) + "." : ". India's share of US imports went from " + pct(sa) + " to " + pct(sb) + ".") : ".") + '</p>';
  }

  function insights(r, k) {
    var out = [], W = r.w[k], I = r.i[k] || 0, top = r.top || [];
    if (!I || (W && I / W < 0.005)) {
      out.push("The US imported <strong>" + usd(W) + "</strong> of this, but very little came from India. That's an open lane, or a sign of a barrier such as duties, standards or certification. Check that before you invest.");
    } else if (r.r === 1) {
      out.push("India is already the <strong>#1 supplier</strong>. US buyers know Indian makers here, so you compete on product, price and reliability against other Indian exporters.");
    } else if (top.length && top[0][0] !== INDIA) {
      var x = top[0][1] / I;
      out.push("<strong>" + esc(country(top[0][0])) + "</strong> ships " + (x >= 10 ? Math.round(x) : x.toFixed(1)) + "× more than India. Buyers sourcing from there are worth pitching on diversification, design and smaller order sizes.");
    }
    var a = firstIdx(r.i);
    if (a >= 0 && k > a && r.i[a] && I) {
      var g = I / r.i[a] - 1;
      out.push("India's sales to the US " + (Math.abs(g) < 0.02 ? "<strong>stayed flat</strong>" : g > 0 ? "grew <strong>" + pct(g) + "</strong>" : "fell <strong>" + pct(-g) + "</strong>") + " between " + YEARS[a] + " and " + YEARS[k] + ".");
    }
    if (W) {
      var slice = W > 1e9 ? 0.001 : 0.01;
      out.push("Winning just <strong>" + (slice * 100) + "%</strong> of this US market would be about <strong>" + usd(W * slice) + " a year</strong> in sales.");
    }
    out.push("These numbers show the market. The buyer list (coming soon) shows the actual US companies importing this from India.");
    return out;
  }

  // ── Waitlist ───────────────────────────────────────────────────────────────
  function sendLead(event) {
    var lead = store(LS_LEAD);
    if (!C.leadEndpoint || !lead || !selected) return;
    var qs = new URLSearchParams(location.search);
    var body = {
      event: event, email: lead.email, phone: lead.phone || "", hsn: selected.code, hsn_name: selected.title || selected.heading,
      product: H.shortName(selected), state: "", district: "", segment: lead.seg || "",
      page: location.href.split("#")[0], referrer: document.referrer || "",
      utm_source: qs.get("utm_source") || "", utm_medium: qs.get("utm_medium") || "", utm_campaign: qs.get("utm_campaign") || ""
    };
    try { fetch(C.leadEndpoint, { method: "POST", mode: "no-cors", headers: { "Content-Type": "text/plain;charset=utf-8" }, body: JSON.stringify(body), keepalive: true }); } catch (e) {}
  }
  function showDone(lead) {
    els.waitForm.hidden = true; els.done.hidden = false; els.doneEmail.textContent = lead.email;
  }

  els.form.addEventListener("submit", function (e) {
    e.preventDefault();
    els.error.textContent = "";
    if (!selected) { els.error.textContent = "Pick your HSN code from the list first."; els.hsn.focus(); return; }
    render();
    track("ebf_view_market", { hsn: selected.code });
    if (store(LS_LEAD)) sendLead("export_search");
  });
  els.waitForm.addEventListener("submit", function (e) {
    e.preventDefault();
    var email = els.email.value.trim(), phone = els.phone.value.replace(/[\s-]/g, ""), seg = els.seg.value;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) { els.waitError.textContent = "Enter a valid email."; els.email.focus(); return; }
    if (phone && !/^(\+?91)?[6-9]\d{9}$/.test(phone)) { els.waitError.textContent = "Enter a 10-digit Indian mobile number, or leave it empty."; els.phone.focus(); return; }
    if (!seg) { els.waitError.textContent = "Choose where you are in exporting."; els.seg.focus(); return; }
    els.waitError.textContent = "";
    var lead = { email: email, phone: phone, seg: seg };
    store(LS_LEAD, lead);
    sendLead("export_waitlist");
    showDone(lead);
    refreshCanada();
    track("ebf_waitlist", { hsn: selected && selected.code, segment: seg }); track("generate_lead", { method: "export_buyer_finder" });
  });

  els.market.addEventListener("click", function (e) {
    if (e.target.id === "ebfCaAll") { caShowAll = true; refreshCanada(); track("ebf_ca_all", { hsn: selected && selected.code }); }
  });

  combo = H.combo({ input: els.hsn, list: els.list, status: els.status, idPrefix: "ebfOpt", onPick: pick, onClear: unpick });
  var known = store(LS_LEAD); if (known) showDone(known);
  H.load(C.hsnUrl).then(function () {
    els.status.textContent = "Type at least 2 characters. Search by code (e.g. 4820) or by product (e.g. leather journal).";
    var code = (new URLSearchParams(location.search).get("hsn") || "").replace(/\D/g, "");
    if (code) { combo.prefill(code); if (selected) render(); }
  }).catch(function () { els.status.textContent = "Couldn't load the HSN list. Check your connection and refresh the page."; });
})();
