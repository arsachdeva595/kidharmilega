/* KidharMilega HSN Code Finder: plain-words search → HSN line → code breakdown, India exports, ODOP districts,
 * next steps. Search comes from /tools/shared/hsn-search.js (window.KMHSN); settings from window.HF_CONFIG. */
(function () {
  "use strict";
  var C = window.HF_CONFIG || {}, H = window.KMHSN, IN = C.india;
  var $ = function (id) { return document.getElementById(id); };
  var esc = H.esc, fmt = H.fmtCode;
  var input = $("hfInput"), status = $("hfStatus"), result = $("hfResult");
  var districts = null, chCache = {};

  function track(name, params) { try { if (window.gtag) window.gtag("event", name, params || {}); } catch (e) {} }
  function getJson(url) { return fetch(url).then(function (r) { if (!r.ok) throw new Error(url); return r.json(); }); }
  function usd(v) {
    var a = Math.abs(v);
    if (a >= 1e9) return "$" + (v / 1e9).toFixed(a >= 1e10 ? 0 : 1) + " billion";
    if (a >= 1e6) return "$" + (v / 1e6).toFixed(a >= 1e8 ? 0 : 1) + " million";
    if (a >= 1e3) return "$" + Math.round(v / 1e3) + "K";
    return "$" + Math.round(v);
  }
  function inr(v) {   // rough ₹ for a reader who thinks in crore; ₹88/$ is close enough for a headline
    var r = v * 88;
    if (r >= 1e7) return "≈ ₹" + Math.round(r / 1e7).toLocaleString("en-IN") + " crore";
    if (r >= 1e5) return "≈ ₹" + Math.round(r / 1e5).toLocaleString("en-IN") + " lakh";
    return "";
  }
  function pct(x) { return (x * 100).toFixed(x < 0.1 ? 1 : 0) + "%"; }
  function country(c) { return (IN && IN.partners[String(c)]) || "Country " + c; }
  function last(arr) { for (var i = arr.length - 1; i >= 0; i--) if (arr[i] != null) return i; return -1; }
  function first(arr) { for (var i = 0; i < arr.length; i++) if (arr[i]) return i; return -1; }

  // India's exports of a 6-digit code, or of its 4-digit heading when the exact code has no data.
  function indiaRow(code) {
    if (!IN) return Promise.resolve(null);
    var ch = code.slice(0, 2), h6 = code.slice(0, 6), h4 = code.slice(0, 4);
    if (IN.chapters.indexOf(ch) < 0) return Promise.resolve(null);
    var p = chCache[ch] || (chCache[ch] = getJson(C.inBase + ch + ".json"));
    return p.then(function (rows) {
      if (rows[h6]) return { level: "hs6", code: h6, row: rows[h6] };
      var w = null, tops = {};
      Object.keys(rows).forEach(function (k) {
        if (k.slice(0, 4) !== h4) return;
        var r = rows[k];
        w = w ? w.map(function (v, i) { return (v || 0) + (r.w[i] || 0); }) : r.w.slice();
        (r.top || []).forEach(function (t) { tops[t[0]] = (tops[t[0]] || 0) + t[1]; });
      });
      if (!w) return null;
      var top = Object.keys(tops).map(function (k) { return [k, tops[k]]; }).sort(function (a, b) { return b[1] - a[1]; });
      return { level: "hs4", code: h4, row: { w: w, top: top.slice(0, 5) } };
    }).catch(function () { return null; });
  }

  function exportsHtml(hit) {
    if (!hit) return '<p class="hf-muted">No India export data recorded for this code. It may be sold mostly within India, or recorded under a nearby code.</p>';
    var r = hit.row, k = last(r.w), a = first(r.w), W = r.w[k], yr = IN.years[k], top = (r.top || []).slice(0, 3);
    var html = hit.level === "hs4" ? '<p class="hf-muted">No data for the exact 6-digit code, so this is the whole heading ' + esc(hit.code) + '.</p>' : "";
    html += '<div class="hf-big"><b>' + usd(W) + '</b> <span>' + esc(inr(W)) + ' exported by India in ' + yr + '</span></div>';
    if (a >= 0 && a < k && r.w[a]) {
      var g = W / r.w[a] - 1;
      html += '<p>' + (Math.abs(g) < 0.02 ? "Flat" : g > 0 ? "Up <strong>" + pct(g) + "</strong>" : "Down <strong>" + pct(-g) + "</strong>") + ' since ' + IN.years[a] + '.</p>';
    }
    if (top.length && W) html += '<p>Top buyers: ' + top.map(function (t) { return '<strong>' + esc(country(t[0])) + '</strong> (' + pct(t[1] / W) + ')'; }).join(", ") + '.</p>';
    html += '<p class="hf-src">UN Comtrade, India-reported exports. Pulled ' + esc(IN.fetched) + '.</p>';
    return html;
  }

  function districtsHtml(code, l) {
    var h4 = code.slice(0, 4), text = " " + ((l.title || "") + " " + (l.detail || "")).toLowerCase() + " ";
    // Districts whose product is named in this line come first (turmeric before ginger under 0910).
    function rel(d) {
      return d.p.toLowerCase().split(/[^a-z]+/).filter(function (w) { return w.length > 3 && text.indexOf(w) >= 0; }).length;
    }
    var hits = (districts || []).filter(function (d) { return d.h && d.h.indexOf(h4) >= 0; })
      .map(function (d, i) { return { d: d, r: rel(d), i: i }; })
      .sort(function (a, b) { return b.r - a.r || a.i - b.i; })
      .map(function (x) { return x.d; });
    if (!hits.length) return '<p class="hf-muted">No ODOP district is mapped to heading ' + esc(h4) + ' yet.</p>';
    var show = hits.slice(0, 12);
    return '<p>' + hits.length + ' district' + (hits.length > 1 ? "s have" : " has") + ' an ODOP product under heading ' + esc(h4) + ':</p><div class="hf-dists">' +
      show.map(function (d) { return '<a href="' + esc(C.paths.base + d.u) + '"><strong>' + esc(d.d) + '</strong><span>' + esc(d.p) + ' · ' + esc(d.s) + '</span></a>'; }).join("") +
      '</div>' + (hits.length > show.length ? '<p class="hf-muted">+' + (hits.length - show.length) + ' more in the Supplier Finder.</p>' : "");
  }

  function render(l) {
    var code = l.code, h6 = code.slice(0, 6), h4 = code.slice(0, 4);
    var shareUrl = location.origin + location.pathname + "?hsn=" + code;
    try { history.replaceState(null, "", "?hsn=" + code); } catch (e) {}
    result.innerHTML =
      '<div class="hf-card hf-main">' +
        '<div class="section-label">HSN code</div>' +
        '<div class="hf-code"><span id="hfCode">' + esc(fmt(code)) + '</span><button type="button" class="btn btn-primary btn-sm" id="hfCopy">Copy</button></div>' +
        '<h2 class="hf-title">' + esc(l.title || l.heading) + '</h2>' +
        (l.detail ? '<p class="hf-detail">Tariff line: ' + esc(l.detail) + '</p>' : "") +
        '<dl class="hf-levels">' +
          '<div><dt>8 digits · India</dt><dd>' + esc(code) + '</dd><p>Shipping bill, export documents, large-business invoices.</p></div>' +
          '<div><dt>6 digits · worldwide</dt><dd>' + esc(h6) + '</dd><p>Same in every country. Use it to search foreign trade data.</p></div>' +
          '<div><dt>4 digits · heading</dt><dd>' + esc(h4) + '</dd><p>' + esc(l.heading) + '</p></div>' +
          '<div><dt>Chapter ' + esc(code.slice(0, 2)) + '</dt><dd class="hf-ch">' + esc(l.chapter) + '</dd></div>' +
        '</dl>' +
        '<div class="hf-gst"><strong>On your GST invoice:</strong> turnover up to ₹5 crore → at least <b>' + esc(h4) + '</b> on B2B invoices. Above ₹5 crore → at least <b>' + esc(h6) + '</b> on every invoice. ' +
          '<a href="' + esc(C.gstUrl) + '" target="_blank" rel="noopener" data-t="gst">Check the current GST rate on CBIC &rarr;</a></div>' +
        '<div class="hf-actions"><a class="btn btn-ghost btn-sm" id="hfWa" target="_blank" rel="noopener" href="https://wa.me/?text=' +
          encodeURIComponent("HSN code for " + (l.title || l.heading).split(";")[0] + ": " + code + "\nFind any product's HSN code free: " + shareUrl) + '">Share on WhatsApp</a></div>' +
      '</div>' +
      '<div class="hf-grid">' +
        '<div class="hf-card"><h3>Where India sells this</h3><div id="hfIn"><p class="hf-muted">Loading…</p></div>' +
          '<a class="btn btn-ghost btn-sm" href="' + esc(C.paths["export"] + "?hsn=" + code) + '" data-t="export">Find foreign buyers &rarr;</a></div>' +
        '<div class="hf-card"><h3>Districts that make it</h3><div id="hfDist"><p class="hf-muted">Loading…</p></div>' +
          '<a class="btn btn-ghost btn-sm" href="' + esc(C.paths.supplier + "?hsn=" + code) + '" data-t="supplier">Find suppliers &rarr;</a></div>' +
      '</div>' +
      '<div class="hf-card hf-next"><h3>What to do with this code</h3><ol>' +
        '<li><strong>Sourcing?</strong> <a href="' + esc(C.paths.supplier + "?hsn=" + code) + '" data-t="supplier">Supplier Finder</a> gives AI prompts to find real manufacturers for this code in any district.</li>' +
        '<li><strong>Exporting?</strong> <a href="' + esc(C.paths["export"] + "?hsn=" + code) + '" data-t="export">Export Buyer Finder</a> shows which countries buy it from India and named importers in Canada and the UK.</li>' +
        '<li><strong>Selling to the UK?</strong> Search <b>' + esc(h6) + '</b> on <a href="https://www.uktradeinfo.com/" target="_blank" rel="noopener" data-t="uktradeinfo">uktradeinfo.com</a>, the UK government\'s free trade data site.</li>' +
        '<li><strong>Not started yet?</strong> <a href="' + esc(C.paths.budget) + '" data-t="budget">Budget Matcher</a> shows which district businesses fit your money.</li>' +
      '</ol></div>';
    result.hidden = false;
    result.scrollIntoView({ behavior: "smooth", block: "start" });

    $("hfCopy").onclick = function () {
      var b = this;
      (navigator.clipboard ? navigator.clipboard.writeText(code) : Promise.reject()).then(function () {
        b.textContent = "Copied"; setTimeout(function () { b.textContent = "Copy"; }, 1500);
      }).catch(function () { b.textContent = code; });
      track("hf_copy", { hsn: code });
    };
    indiaRow(code).then(function (hit) { var el = $("hfIn"); if (el) el.innerHTML = exportsHtml(hit); });
    (districts ? Promise.resolve() : getJson(C.districtsUrl).then(function (d) { districts = d; }))
      .catch(function () { districts = []; })
      .then(function () { var el = $("hfDist"); if (el) el.innerHTML = districtsHtml(code, l); });
    track("hf_pick", { hsn: code });
  }

  result.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a[data-t]");
    if (a) track("hf_click", { to: a.getAttribute("data-t") });
  });

  var combo = H.combo({ input: input, list: $("hfList"), status: status, idPrefix: "hfOpt", onPick: render,
    onClear: function () { result.hidden = true; } });

  function runQuery(q) {
    input.value = q; input.focus();
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }
  document.querySelectorAll(".hf-ex").forEach(function (b) {
    b.addEventListener("click", function () { runQuery(b.getAttribute("data-q")); track("hf_example", { q: b.getAttribute("data-q") }); });
  });

  H.load(C.hsnUrl).then(function (lines) {
    status.textContent = lines.length.toLocaleString("en-IN") + " Indian HSN codes loaded. Start typing.";
    var qs = new URLSearchParams(location.search), code = (qs.get("hsn") || "").replace(/\D/g, "");
    if (code) { combo.prefill(code); if (H.byCode(code)) return; input.scrollIntoView({ block: "center" }); }
    else if (qs.get("q")) runQuery(qs.get("q"));
  }).catch(function () { status.textContent = "Couldn't load the HSN list. Check your connection and reload."; });
})();
