/* KidharMilega Export Buyer Finder: HSN → India's export markets, market details (UN Comtrade) → masked buyer
 * companies (Canada, UK) behind "Show more" → "unlock full details" waitlist.
 * Config from window.EBF_CONFIG (export_buyer_finder.py). HSN search from /tools/shared/hsn-search.js. */
(function () {
  "use strict";
  var C = window.EBF_CONFIG || {}, H = window.KMHSN, esc = H.esc;
  var $ = function (id) { return document.getElementById(id); };
  var LS_LEAD = "ebf_lead_v1", INDIA = 699;
  var META = C.meta || {}, MUS = META.us || {}, MIN = META["in"] || {}, NAMES = META.partners || {};
  var YEARS = MUS.years || [], IYEARS = MIN.years || [], US = 842, hasBuyers = false;
  var els = {
    form: $("ebfForm"), hsn: $("ebfHsn"), list: $("ebfHsnList"), status: $("ebfHsnStatus"), picked: $("ebfPicked"),
    error: $("ebfError"), results: $("ebfResults"), title: $("ebfTitle"), sub: $("ebfSub"), market: $("ebfMarket"),
    waitCode: $("ebfWaitCode"), waitForm: $("ebfWaitForm"), email: $("ebfEmail"), phone: $("ebfPhone"), seg: $("ebfSeg"),
    waitError: $("ebfWaitError"), done: $("ebfDone"), doneEmail: $("ebfDoneEmail"), sfLink: $("ebfSfLink"),
    sample: $("ebfSample")
  };
  var selected = null, combo, chapters = { us: {}, "in": {}, ca: {}, uk: {} };

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
      '<div class="sf-picked__code">HSN ' + esc(H.fmtCode(l.code)) + ' <span class="sf-opt">→ trade data for HS ' + esc(l.code.slice(0, 6)) + '</span></div>' +
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
    Promise.all([loadChapter("in", ch), loadChapter("us", ch), loadChapter("ca", ch), loadChapter("uk", ch)]).then(function (res) {
      if (selected !== l) return;
      var hin = IYEARS.length ? rowFor(l.code, res[0], IYEARS) : null, hus = YEARS.length ? rowFor(l.code, res[1], YEARS) : null;
      var groups = [listFor("ca", l.code, res[2]), listFor("uk", l.code, res[3])].filter(Boolean);
      hasBuyers = groups.length > 0;
      var html = "";
      // 1–2. Where India sells it: tiles, trend, top 10 countries, takeaways.
      if (hin) html += indiaHtml(hin);
      else if (IYEARS.length) html += '<p class="ebf-note">No India export records for this code in ' + IYEARS[0] + "–" + IYEARS[IYEARS.length - 1] + '. India may report it under a nearby code. Try a related product.</p>';
      // 3. Market details: the US deep dive.
      if (hus) html += '<h2 class="ebf-h2" id="ebfUs">The US market in detail</h2>' + marketHtml(hus);
      // 4. Buyer companies, masked, behind "Show more". Countries with no list for this code are left out.
      var total = groups.reduce(function (a, g) { return a + g.total; }, 0);
      if (groups.length) {
        html += '<div class="ebf-more-wrap" id="ebfMoreWrap"><button type="button" class="btn btn-cyan btn-lg" id="ebfShowMore">Show more: ' + total.toLocaleString("en-IN") + " buyer " + plural(total, "company", "companies") +
          ' <span class="btn__arrow" aria-hidden="true">&darr;</span></button><p class="sf-hint">Importers in ' + groups.map(function (g) { return LISTS[g.key].country; }).join(" and ") + ' from official government data.</p></div>' +
          '<section class="ebf-buyer-sec" id="ebfBuyers" hidden><h2 class="ebf-h2">Companies buying this product</h2>' +
          '<p class="section-sub">Names and contacts are hidden for now. Unlocking them is coming soon: join below and we\'ll tell you first.</p>' +
          groups.map(groupHtml).join("") + '</section>';
      }
      els.sample.hidden = groups.length > 0;  // the sample lead only when there are no real (masked) rows to show
      els.market.innerHTML = html || '<p class="ebf-note">Trade data is being updated. Join the list below and check back soon.</p>';
    });
  }

  // ── Buyer companies (Canada: from India; UK: from anywhere), masked ─────────
  var RANK = { specialist: 3, other: 2, chain: 1, luxury: 0 };
  var TYPE = { specialist: "Specialist importer", other: "Importer", chain: "Big retail chain", luxury: "Luxury brand, sources in-house" };
  var LISTS = {
    ca: {
      country: "Canada",
      sort: function (a, b) { return (RANK[b[3]] - RANK[a[3]]) || (a[4] - b[4]) || (Math.min(b[5], 10) - Math.min(a[5], 10)) || (a[0] < b[0] ? -1 : 1); },
      head: function (g, m) { return "<strong>" + g.total.toLocaleString("en-IN") + "</strong> " + plural(g.total, "company", "companies") + " imported HS " + esc(g.code) + " <strong>from India</strong> in " + m.year + "."; },
      row: function (r) {
        return {
          where: esc(r[1]) + ", " + esc(r[2]) + (r[4] ? " (based outside Canada)" : ""), seg: r[3],
          proof: '<span class="ebf-tag is-proof">Imported this from India</span>',
          activity: r[5] ? "Also imports " + r[5] + " related " + plural(r[5], "product", "products") + " from India" : "Buys this product from India"
        };
      },
      foot: function (m) { return esc(m.licence) + " Source: " + esc(m.source) + ", " + m.year + "."; }
    },
    uk: {
      country: "the UK",
      sort: function (a, b) { return (RANK[b[3]] - RANK[a[3]]) || (b[4] - a[4]) || (Math.min(b[6], 15) - Math.min(a[6], 15)) || (b[5] - a[5]) || (a[0] < b[0] ? -1 : 1); },
      head: function (g, m) {
        return "<strong>" + g.total.toLocaleString("en-IN") + "</strong> " + plural(g.total, "company", "companies") + " imported HS " + esc(g.code) + " into the UK, " + ym(m.months[0]) + " to " + ym(m.months[1]) +
          ". HMRC doesn't record where they buy from, so these import the product, not necessarily from India.";
      },
      row: function (r, m) {
        var span = monthsBetween(m.months[0], m.months[1]);
        return {
          where: esc(r[1]), seg: r[3],
          proof: '<span class="ebf-tag">Imported this product</span>',
          activity: r[4] + " of " + span + " months, last " + ym(r[5]) + (r[6] ? " · " + r[6] + " related " + plural(r[6], "product", "products") : "")
        };
      },
      foot: function (m) { return esc(m.licence) + " Source: " + esc(m.source) + ". Couriers, customs agents and agent addresses removed."; }
    }
  };

  function plural(n, one, many) { return n === 1 ? one : many; }
  function ym(m) { var s = String(m); return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][+s.slice(4) - 1] + " " + s.slice(0, 4); }
  function monthsBetween(a, b) { return (Math.floor(b / 100) - Math.floor(a / 100)) * 12 + (b % 100) - (a % 100) + 1; }

  // Exact HS6 list, else every HS6 in the heading merged (one row per company). A ["+", n] row = n more cut from the file.
  function listFor(key, code, data) {
    var m = META[key];
    if (!m || (m.covered && m.covered.indexOf(code.slice(0, 2)) < 0)) return null;
    var h6 = code.slice(0, 6), more = 0;
    function clean(rows) { return rows.filter(function (r) { if (r[0] === "+") { more += r[1]; return false; } return true; }); }
    var rows, level = "hs6", at = h6;
    if (data[h6]) rows = clean(data[h6]);
    else {
      var h4 = code.slice(0, 4), seen = {};
      rows = []; level = "hs4"; at = h4;
      Object.keys(data).sort().forEach(function (k) {
        if (k.indexOf(h4) !== 0) return;
        clean(data[k]).forEach(function (r) { if (!seen[r[0]]) { seen[r[0]] = 1; rows.push(r); } });
      });
      rows.sort(LISTS[key].sort);
    }
    return rows.length ? { key: key, level: level, code: at, rows: rows, total: rows.length + more } : null;
  }

  // Same card as the sample lead: name and contacts are placeholders, never the real values.
  function groupHtml(g) {
    var L = LISTS[g.key], m = META[g.key], show = Math.min(10, g.rows.length);
    return '<div class="ebf-group"><h3 class="ebf-group__h">' + (g.key === "ca" ? "Canada" : "United Kingdom") + '</h3>' +
      '<p class="ebf-group__sub">' + L.head(g, m) + (g.level === "hs4" ? " Covers the whole heading " + esc(g.code) + "." : "") + '</p>' +
      g.rows.slice(0, show).map(function (r) {
        var x = L.row(r, m);
        return '<div class="ebf-row ebf-lead">' +
          '<div><span class="ebf-blur" aria-label="Company name hidden">Company name hidden</span><small>' + esc(TYPE[x.seg]) + ' · ' + x.where + '</small></div>' +
          '<div><b>Proof</b>' + x.proof + '</div>' +
          '<div><b>Activity</b><span>' + x.activity + '</span></div>' +
          '<div><b>Contacts</b><span class="ebf-blur" aria-label="Contacts hidden">website · email · phone</span></div>' +
          '</div>';
      }).join("") +
      (g.total > show ? '<p class="ebf-more"><strong>+' + (g.total - show).toLocaleString("en-IN") + ' more</strong> in the full list.</p>' : "") +
      '<p class="ebf-source">' + L.foot(m) + '</p></div>';
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
    if (hasBuyers) out.push("These numbers show the market. Tap <strong>Show more</strong> below to see the companies buying it.");
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
    track("ebf_waitlist", { hsn: selected && selected.code, segment: seg }); track("generate_lead", { method: "export_buyer_finder" });
  });

  els.market.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("#ebfShowMore");
    if (!b) return;
    $("ebfBuyers").hidden = false; $("ebfMoreWrap").hidden = true;
    $("ebfBuyers").scrollIntoView({ behavior: "smooth", block: "start" });
    track("ebf_show_buyers", { hsn: selected && selected.code });
  });

  combo = H.combo({ input: els.hsn, list: els.list, status: els.status, idPrefix: "ebfOpt", onPick: pick, onClear: unpick });
  var known = store(LS_LEAD); if (known) showDone(known);
  H.load(C.hsnUrl).then(function () {
    els.status.textContent = "Type at least 2 characters. Search by code (e.g. 4820) or by product (e.g. leather journal).";
    var code = (new URLSearchParams(location.search).get("hsn") || "").replace(/\D/g, "");
    if (code) { combo.prefill(code); if (selected) render(); }
  }).catch(function () { els.status.textContent = "Couldn't load the HSN list. Check your connection and refresh the page."; });
})();
