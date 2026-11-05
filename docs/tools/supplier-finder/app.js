/* KidharMilega Supplier Finder: HSN search → district → email gate → prompts + audit checklist.
 * Config (prompts, checklist, endpoints) comes from window.SF_CONFIG, written by supplier_finder.py. */
(function () {
  "use strict";
  var C = window.SF_CONFIG || {};
  var $ = function (id) { return document.getElementById(id); };
  var LS_LEAD = "sf_lead_v1", LS_CHECKS = "sf_checks_v1";

  var els = {
    form: $("sfForm"), hsn: $("sfHsn"), list: $("sfHsnList"), status: $("sfHsnStatus"), picked: $("sfPicked"),
    productWrap: $("sfProductWrap"), product: $("sfProduct"), state: $("sfState"), district: $("sfDistrict"),
    dlist: $("sfDistrictList"), suggest: $("sfSuggest"), chips: $("sfChips"), error: $("sfError"),
    gate: $("sfGate"), gateForm: $("sfGateForm"), gateClose: $("sfGateClose"), email: $("sfEmail"), phone: $("sfPhone"),
    gateError: $("sfGateError"), results: $("sfResults"), rTitle: $("sfResultsTitle"), rSub: $("sfResultsSub"),
    prompts: $("sfPrompts"), checklist: $("sfChecklist"), print: $("sfPrint"), book: $("sfBook")
  };

  var HSN = null, LINES = [], DISTRICTS = [], selected = null, activeIdx = -1, shown = [];

  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function store(key, val) {
    try { if (val === undefined) return JSON.parse(localStorage.getItem(key) || "null"); localStorage.setItem(key, JSON.stringify(val)); }
    catch (e) { return null; }
  }
  function track(name, params) { try { if (window.gtag) window.gtag("event", name, params || {}); } catch (e) {} }
  function fmtCode(c) { return c.length === 8 ? c.slice(0, 4) + " " + c.slice(4, 6) + " " + c.slice(6) : c.length === 6 ? c.slice(0, 4) + " " + c.slice(4) : c; }

  // ── Data ────────────────────────────────────────────────────────────────────
  function loadData() {
    var a = fetch(C.hsnUrl).then(function (r) { if (!r.ok) throw new Error("hsn"); return r.json(); });
    var b = fetch(C.districtsUrl).then(function (r) { if (!r.ok) throw new Error("districts"); return r.json(); });
    return Promise.all([a, b]).then(function (res) {
      HSN = res[0]; DISTRICTS = res[1];
      LINES = HSN.t.map(function (row) {
        var code = row[0], h4 = code.slice(0, 4);
        var title = (code.length >= 6 && HSN.x[code.slice(0, 6)]) || HSN.h[h4] || "";
        var heading = HSN.h[h4] || "";
        var ch = HSN.c[code.slice(0, 2)] || ["", ""];
        return { code: code, title: title, detail: row[1] || "", heading: heading, chapter: ch[0],
                 hay: norm(title + " " + heading + " " + (row[1] || "")) };
      });
      els.status.textContent = "Type at least 2 characters. Search by code (e.g. 6302) or by product (e.g. brass diya).";
      fillStates();
    }).catch(function () {
      els.status.textContent = "Couldn't load the HSN list. Check your connection and refresh the page.";
    });
  }

  function fillStates() {
    var states = [];
    DISTRICTS.forEach(function (d) { if (states.indexOf(d.s) < 0) states.push(d.s); });
    states.sort();
    els.state.innerHTML = '<option value="">Select state</option>' + states.map(function (s) {
      return '<option>' + esc(s) + '</option>';
    }).join("");
  }

  function fillDistricts() {
    var st = els.state.value, seen = {};
    els.dlist.innerHTML = DISTRICTS.filter(function (d) { return !st || d.s === st; }).map(function (d) {
      var name = d.d.replace(/\s*\(.*\)\s*/g, "").trim();
      if (seen[name]) return ""; seen[name] = 1;
      return '<option value="' + esc(name) + '">';
    }).join("");
  }

  // ── HSN search ──────────────────────────────────────────────────────────────
  // Words Indian buyers use → words the HSN text uses. Matching is on word starts, so "lamp" also finds "lamps".
  var SYN = {
    bedsheet: ["bed linen", "bedsheet"], chadar: ["bed linen", "bedspread"], razai: ["quilt"], rajai: ["quilt"],
    kurta: ["kurta", "shirt"], kurti: ["kurta", "blouse"], dupatta: ["shawl", "scarves", "stole"], stole: ["shawl", "stole"],
    chunni: ["shawl", "scarves"], lehenga: ["skirt", "ensemble", "dress"], salwar: ["trouser", "ensemble"],
    jeans: ["denim", "trouser"], tshirt: ["t shirt", "singlet"], pashmina: ["cashmere", "kashmir", "fine animal hair"],
    khadi: ["khadi", "handloom"], kalamkari: ["printed"], dari: ["dari", "carpet", "floor covering"], durrie: ["carpet", "floor covering"],
    diya: ["lamp", "clay articles", "lighting"], dhoop: ["agarbatti", "odoriferous"], agarbatti: ["agarbatti", "odoriferous"], incense: ["agarbatti", "odoriferous"],
    attar: ["essential oil", "perfume"], ittar: ["essential oil", "perfume"], mehndi: ["henna", "lawsonia"], henna: ["henna", "lawsonia"],
    kumkum: ["kumkum", "make up", "bindi"], sindoor: ["kumkum", "make up"], ayurvedic: ["ayurvedic", "medicament"],
    achar: ["preserved by vinegar", "pickle"], pickle: ["preserved by vinegar", "pickle"], namkeen: ["namkeen", "bhujia", "food preparation"], bhujia: ["bhujia", "namkeen"],
    mithai: ["sweetmeat", "sugar confectionery"], sweets: ["sweetmeat", "sugar confectionery"], gur: ["jaggery"],
    makhana: ["fox nut", "makhana", "nuts"], atta: ["wheat or meslin flour", "atta"], besan: ["gram flour", "flour"],
    suji: ["semolina"], sooji: ["semolina"], poha: ["flaked", "rice"], dal: ["leguminous", "pulse", "dal"], daal: ["leguminous", "pulse"],
    rajma: ["kidney bean"], chana: ["chickpea", "gram"], haldi: ["turmeric"], jeera: ["cumin"], elaichi: ["cardamom"],
    dalchini: ["cinnamon"], mirchi: ["capsicum", "chilli"], chilli: ["capsicum", "chilli"], chili: ["capsicum", "chilli"],
    masala: ["spice", "masala"], ghee: ["ghee", "butter"], pottery: ["clay articles", "ceramic"], terracotta: ["clay articles", "terracotta", "ceramic statuettes", "ceramic"],
    clay: ["clay articles", "clay", "ceramic"], matka: ["clay articles", "ceramic"], murti: ["statuette", "idol"], idol: ["statuette", "idol"],
    handicraft: ["statuette", "ornament", "handicraft"], chappal: ["footwear", "chappal", "slipper"], slipper: ["footwear", "slipper"],
    chudi: ["bangle"], jhumka: ["jewellery", "imitation jewellery"], earring: ["jewellery", "imitation jewellery"],
    tiffin: ["container", "kitchen"], kadai: ["kitchen", "table"], tawa: ["kitchen", "table"], jhadu: ["broom"], broom: ["broom"],
    rassi: ["twine", "cordage", "rope"], wooden: ["wood"], banarasi: ["silk", "saree"], saree: ["saree", "sari"], sari: ["saree", "sari"],
    lamp: ["lamp", "lighting"], brass: ["articles of brass", "brass", "copper"], rakhi: ["rakhi", "made up"], notebook: ["exercise book", "notebook"], copy: ["exercise book"]
  };
  function norm(t) { return " " + String(t).toLowerCase().replace(/[^a-z0-9%]+/g, " ") + " "; }
  // 1 if the first (best) alternative is present, less for later ones, 0 if none.
  function count(hay, alts) { for (var i = 0; i < alts.length; i++) if (hay.indexOf(" " + alts[i]) >= 0) return 1 / (1 + i * 0.5); return 0; }

  function search(q) {
    q = q.trim().toLowerCase();
    if (q.length < 2 || !LINES.length) return [];
    var digits = q.replace(/[\s.]/g, "");
    if (/^\d+$/.test(digits)) {
      return LINES.filter(function (l) { return l.code.indexOf(digits) === 0; }).slice(0, 40);
    }
    var toks = q.split(/[^a-z0-9%]+/).filter(function (t) { return t.length > 1; });
    if (!toks.length) return [];
    var alts = toks.map(function (t) {
      var stem = t.length > 4 ? t.replace(/(es|s)$/, "") : t;
      return SYN[t] || SYN[stem] || [stem];
    });
    // Lines matching every word come first. If none do (e.g. "banarasi saree"), show lines matching the most words.
    var out = [], partial = [];
    for (var i = 0; i < LINES.length; i++) {
      var l = LINES[i], score = 0, hits = 0;
      if (!l.nt) { l.nt = norm(l.title); l.nh = norm(l.heading); l.nd = norm(l.detail); }
      for (var j = 0; j < alts.length; j++) {
        if (!count(l.hay, alts[j])) continue;
        hits++;
        score += 4 * count(l.hay, alts[j]) + 1.5 * count(l.nt, alts[j]) + count(l.nh, alts[j]) + 0.5 * count(l.nd, alts[j]);
      }
      if (hits === alts.length) out.push([score, l]);
      else if (hits && !out.length) partial.push([hits * 10 + score, l]);
    }
    if (!out.length) { out = partial; out.partial = true; }
    out.sort(function (a, b) { return b[0] - a[0] || (a[1].code < b[1].code ? -1 : 1); });
    var res = out.slice(0, 40).map(function (x) { return x[1]; });
    res.partial = !!out.partial;
    return res;
  }

  function renderList(items) {
    shown = items; activeIdx = -1;
    if (!items.length) {
      els.list.innerHTML = ""; els.list.hidden = true; els.hsn.setAttribute("aria-expanded", "false");
      if (els.hsn.value.trim().length >= 2 && LINES.length) els.status.textContent = "No match. Try a simpler word (e.g. \"bedsheet\" → \"bed linen\") or the first 4 digits of the code.";
      return;
    }
    els.status.textContent = items.partial ? "No exact match for every word. Showing the closest codes. Try one simple word, like \"lamp\" or \"saree\"." : items.length >= 40 ? "Showing the first 40 matches. Type more to narrow it down." : items.length + " matches";
    els.list.innerHTML = items.map(function (l, i) {
      return '<li role="option" id="sfOpt' + i + '" data-i="' + i + '"><span class="sf-code">' + esc(fmtCode(l.code)) + '</span>' +
        '<span class="sf-otitle">' + esc(l.title || l.heading) + '</span>' +
        (l.detail ? '<span class="sf-odetail">' + esc(l.detail) + '</span>' : "") + '</li>';
    }).join("");
    els.list.hidden = false; els.hsn.setAttribute("aria-expanded", "true");
  }

  function setActive(i) {
    var opts = els.list.querySelectorAll("li");
    if (!opts.length) return;
    activeIdx = (i + opts.length) % opts.length;
    opts.forEach(function (o, k) { o.classList.toggle("is-active", k === activeIdx); o.setAttribute("aria-selected", k === activeIdx); });
    els.hsn.setAttribute("aria-activedescendant", "sfOpt" + activeIdx);
    opts[activeIdx].scrollIntoView({ block: "nearest" });
  }

  function shortName(l) {
    var t = (l.title || l.heading).split(/;|\(/)[0].trim();
    var rest = (l.title || "").split(";")[1];
    if (rest && t.length < 40) t += "," + rest.split(/,|\(/)[0];
    return t.replace(/\s+/g, " ").trim().slice(0, 90);
  }

  function pick(l) {
    selected = l;
    els.list.hidden = true; els.hsn.setAttribute("aria-expanded", "false");
    els.hsn.value = l.code;
    els.status.textContent = "";
    els.picked.innerHTML =
      '<div class="sf-picked__code">HSN ' + esc(fmtCode(l.code)) + (l.code.length < 8 ? ' <span class="sf-opt">(6-digit, check your invoice for the full code)</span>' : "") + '</div>' +
      '<div class="sf-picked__title">' + esc(l.title || l.heading) + '</div>' +
      (l.detail ? '<div class="sf-picked__detail">Tariff line: ' + esc(l.detail) + '</div>' : "") +
      '<div class="sf-picked__ch">Chapter ' + esc(l.code.slice(0, 2)) + ' · ' + esc(l.chapter) + '</div>' +
      '<button type="button" class="sf-link" id="sfChange">Change</button>';
    els.picked.hidden = false;
    $("sfChange").onclick = function () { els.picked.hidden = true; els.hsn.value = ""; selected = null; els.suggest.hidden = true; els.hsn.focus(); };
    els.productWrap.hidden = false;
    if (!els.product.dataset.touched) els.product.value = shortName(l);
    renderSuggestions();
    track("sf_pick_hsn", { hsn: l.code });
  }

  // ── ODOP district suggestions ───────────────────────────────────────────────
  function renderSuggestions() {
    if (!selected) return;
    var h4 = selected.code.slice(0, 4), ch = selected.code.slice(0, 2);
    var exact = [], near = [];
    DISTRICTS.forEach(function (d) {
      if (d.h.indexOf(h4) >= 0) exact.push(d);
      else if (d.h.indexOf(ch) >= 0 || d.h.some(function (x) { return x.length === 4 && x.slice(0, 2) === ch; })) near.push(d);
    });
    // Districts whose product maps to this heading first, earliest rule match (= main product) first.
    exact.sort(function (a, b) { return a.h.indexOf(h4) - b.h.indexOf(h4) || a.h.length - b.h.length; });
    var list = exact.concat(near).slice(0, 14);
    if (!list.length) { els.suggest.hidden = true; return; }
    els.chips.innerHTML = list.map(function (d, i) {
      return '<button type="button" class="sf-chip' + (i < exact.length ? "" : " is-near") + '" data-s="' + esc(d.s) + '" data-d="' + esc(d.d.replace(/\s*\(.*\)\s*/g, "").trim()) + '">' +
        '<strong>' + esc(d.d) + '</strong>, ' + esc(d.s) + '<span>' + esc(d.p) + '</span></button>';
    }).join("");
    els.suggest.hidden = false;
  }

  // ── Results ─────────────────────────────────────────────────────────────────
  function vars() {
    var district = els.district.value.trim(), state = els.state.value;
    return {
      product: els.product.value.trim() || shortName(selected),
      hsn: selected.code,
      hsnName: (selected.title || selected.heading).replace(/\s+/g, " "),
      district: district, state: state,
      place: district + (state ? ", " + state : "")
    };
  }
  function fill(t, v) { return t.replace(/\{(\w+)\}/g, function (m, k) { return v[k] != null ? v[k] : m; }); }

  function categoriesFor(code) {
    var cats = C.checklist.categories, out = [];
    cats.forEach(function (c) { if ((c.heads || []).some(function (h) { return code.indexOf(h) === 0; })) out.push(c); });
    cats.forEach(function (c) { if (out.indexOf(c) < 0 && (c.ch || []).indexOf(code.slice(0, 2)) >= 0) out.push(c); });
    return out;
  }

  function renderResults() {
    var v = vars();
    els.rTitle.textContent = "Suppliers of " + v.product + " in " + v.place;
    els.rSub.textContent = "HSN " + fmtCode(v.hsn) + " · " + v.hsnName;

    els.prompts.innerHTML = C.prompts.map(function (p, i) {
      var text = fill(p.text, v);
      var open = i === 0 ?
        '<a class="btn btn-ghost btn-sm" target="_blank" rel="noopener" href="https://claude.ai/new?q=' + encodeURIComponent(text) + '" data-open="claude">Open in Claude ↗</a>' +
        '<a class="btn btn-ghost btn-sm" target="_blank" rel="noopener" href="https://chatgpt.com/?q=' + encodeURIComponent(text) + '" data-open="chatgpt">Open in ChatGPT ↗</a>' : "";
      return '<article class="sf-prompt' + (p.id === "gmb" ? " is-hack" : "") + '">' +
        '<div class="sf-prompt__step">' + esc(p.step) + '</div>' +
        '<h3 class="sf-prompt__title">' + esc(p.title) + '</h3>' +
        '<p class="sf-prompt__why">' + esc(p.why) + '</p>' +
        '<pre class="sf-prompt__text" id="sfP' + i + '">' + esc(text) + '</pre>' +
        '<div class="sf-prompt__actions"><button type="button" class="btn btn-primary btn-sm" data-copy="' + i + '">Copy prompt</button>' + open + '</div>' +
        '</article>';
    }).join("");

    var checks = store(LS_CHECKS) || {};
    var groups = [];
    categoriesFor(v.hsn).forEach(function (c) { groups.push({ id: "c-" + c.id, group: "For " + c.label, items: c.items, cat: true }); });
    C.checklist.general.forEach(function (g, gi) { groups.push({ id: "g" + gi, group: g.group, items: g.items }); });

    var total = 0;
    var html = groups.map(function (g) {
      return '<section class="sf-group' + (g.cat ? " is-cat" : "") + '"><h3>' + esc(g.group) + '</h3><ul>' +
        g.items.map(function (it, k) {
          var key = g.id + "-" + k; total++;
          return '<li><label><input type="checkbox" data-key="' + esc(key) + '"' + (checks[key] ? " checked" : "") + '>' +
            '<span><strong>' + esc(it[0]) + '</strong><span>' + esc(it[1]) + '</span></span></label></li>';
        }).join("") + '</ul></section>';
    }).join("");
    html += '<section class="sf-group is-red"><h3>Red flags: walk away if you see these</h3><ul class="sf-flags">' +
      C.checklist.redFlags.map(function (f) { return '<li>' + esc(f) + '</li>'; }).join("") + '</ul></section>';
    els.checklist.innerHTML = '<div class="sf-progress" id="sfProgress"></div>' + html;
    updateProgress(total);

    els.results.hidden = false;
    els.results.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function updateProgress(total) {
    var boxes = els.checklist.querySelectorAll("input[type=checkbox]");
    total = total || boxes.length;
    var done = 0; boxes.forEach(function (b) { if (b.checked) done++; });
    var p = $("sfProgress");
    if (p) p.innerHTML = '<span>' + done + ' of ' + total + ' checks done</span><span class="sf-bar"><span style="width:' + Math.round(done / total * 100) + '%"></span></span>';
  }

  function copy(text, btn) {
    function done() { var o = btn.textContent; btn.textContent = "Copied ✓"; setTimeout(function () { btn.textContent = o; }, 1800); }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done, function () { fallback(); });
    } else fallback();
    function fallback() {
      var ta = document.createElement("textarea"); ta.value = text; ta.setAttribute("readonly", "");
      ta.style.position = "fixed"; ta.style.opacity = "0"; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); done(); } catch (e) {} document.body.removeChild(ta);
    }
  }

  // ── Leads ───────────────────────────────────────────────────────────────────
  function sendLead(event) {
    var lead = store(LS_LEAD);
    if (!C.leadEndpoint || !lead || !selected) return;
    var v = vars(), qs = new URLSearchParams(location.search);
    var body = {
      event: event, email: lead.email, phone: lead.phone || "", hsn: v.hsn, hsn_name: v.hsnName, product: v.product,
      state: v.state, district: v.district, page: location.href.split("#")[0], referrer: document.referrer || "",
      utm_source: qs.get("utm_source") || "", utm_medium: qs.get("utm_medium") || "", utm_campaign: qs.get("utm_campaign") || ""
    };
    try {
      fetch(C.leadEndpoint, { method: "POST", mode: "no-cors", headers: { "Content-Type": "text/plain;charset=utf-8" }, body: JSON.stringify(body), keepalive: true });
    } catch (e) {}
  }

  function validate() {
    els.error.textContent = "";
    if (!selected) { els.error.textContent = "Pick your HSN code from the list first."; els.hsn.focus(); return false; }
    if (!els.state.value) { els.error.textContent = "Select a state."; els.state.focus(); return false; }
    if (!els.district.value.trim()) { els.error.textContent = "Type the district or city where you want suppliers."; els.district.focus(); return false; }
    return true;
  }

  function openGate() {
    els.gate.hidden = false; document.body.classList.add("sf-noscroll");
    var lead = store(LS_LEAD); if (lead) { els.email.value = lead.email || ""; els.phone.value = lead.phone || ""; }
    setTimeout(function () { els.email.focus(); }, 30);
  }
  function closeGate() { els.gate.hidden = true; document.body.classList.remove("sf-noscroll"); }

  // ── Wiring ──────────────────────────────────────────────────────────────────
  var t;
  els.hsn.addEventListener("input", function () {
    clearTimeout(t);
    if (selected && els.hsn.value !== selected.code) { selected = null; els.picked.hidden = true; els.suggest.hidden = true; }
    t = setTimeout(function () { renderList(search(els.hsn.value)); }, 120);
  });
  els.hsn.addEventListener("keydown", function (e) {
    if (els.list.hidden) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActive(activeIdx + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive(activeIdx - 1); }
    else if (e.key === "Enter") { if (activeIdx >= 0 || shown.length === 1) { e.preventDefault(); pick(shown[Math.max(activeIdx, 0)]); } }
    else if (e.key === "Escape") { els.list.hidden = true; }
  });
  els.list.addEventListener("mousedown", function (e) {
    var li = e.target.closest("li"); if (!li) return; e.preventDefault(); pick(shown[+li.dataset.i]);
  });
  document.addEventListener("click", function (e) { if (!e.target.closest(".sf-combo")) els.list.hidden = true; });
  els.product.addEventListener("input", function () { els.product.dataset.touched = "1"; });
  els.state.addEventListener("change", fillDistricts);
  els.chips.addEventListener("click", function (e) {
    var b = e.target.closest(".sf-chip"); if (!b) return;
    els.state.value = b.dataset.s; fillDistricts(); els.district.value = b.dataset.d;
    els.chips.querySelectorAll(".sf-chip").forEach(function (c) { c.classList.toggle("is-on", c === b); });
    track("sf_pick_odop", { district: b.dataset.d });
  });

  els.form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (!validate()) return;
    var lead = store(LS_LEAD);
    if (lead && lead.email) { renderResults(); sendLead("search"); track("sf_generate", { hsn: selected.code, returning: true }); }
    else openGate();
  });
  els.gateForm.addEventListener("submit", function (e) {
    e.preventDefault();
    var email = els.email.value.trim(), phone = els.phone.value.replace(/[\s-]/g, "");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) { els.gateError.textContent = "Enter a valid email."; els.email.focus(); return; }
    if (phone && !/^(\+?91)?[6-9]\d{9}$/.test(phone)) { els.gateError.textContent = "Enter a 10-digit Indian mobile number, or leave it empty."; els.phone.focus(); return; }
    els.gateError.textContent = "";
    store(LS_LEAD, { email: email, phone: phone });
    closeGate(); renderResults(); sendLead("lead");
    track("sf_lead", { hsn: selected.code }); track("generate_lead", { method: "supplier_finder" });
  });
  els.gateClose.addEventListener("click", closeGate);
  els.gate.addEventListener("click", function (e) { if (e.target === els.gate) closeGate(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !els.gate.hidden) closeGate(); });

  els.prompts.addEventListener("click", function (e) {
    var b = e.target.closest("[data-copy]");
    if (b) { var i = +b.dataset.copy; copy($("sfP" + i).textContent, b); track("sf_copy_prompt", { prompt: C.prompts[i].id, hsn: selected && selected.code }); return; }
    var o = e.target.closest("[data-open]"); if (o) track("sf_open_ai", { app: o.dataset.open });
  });
  els.checklist.addEventListener("change", function (e) {
    var cb = e.target; if (!cb.dataset || !cb.dataset.key) return;
    var s = store(LS_CHECKS) || {}; if (cb.checked) s[cb.dataset.key] = 1; else delete s[cb.dataset.key];
    store(LS_CHECKS, s); updateProgress();
  });
  els.print.addEventListener("click", function () { window.print(); });
  els.book.addEventListener("click", function () { track("sf_book_call", {}); });

  // Prefill from ?hsn=&state=&district= (used by links from HSN pages)
  loadData().then(function () {
    var qs = new URLSearchParams(location.search), code = (qs.get("hsn") || "").replace(/\D/g, "");
    if (qs.get("state")) { els.state.value = qs.get("state"); fillDistricts(); }
    if (qs.get("district")) els.district.value = qs.get("district");
    if (code) {
      var hit = LINES.filter(function (l) { return l.code === code; })[0];
      if (hit) pick(hit); else { els.hsn.value = code; renderList(search(code)); }
    }
  });
})();
