/* Shared HSN search for KidharMilega tools (Supplier Finder, Export Buyer Finder).
 * window.KMHSN.load(url)          → Promise of lines [{code,title,detail,heading,chapter}]
 * window.KMHSN.search(q)          → matching lines (array, .partial = true when not every word matched)
 * window.KMHSN.combo(opts)        → wires an input + listbox; calls opts.onPick(line)
 * window.KMHSN.fmtCode / shortName / byCode
 * Data file: hsn.json built by tools_src/supplier-finder/hsn_compile.py. */
(function () {
  "use strict";
  var LINES = [], BY = {};

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
    lamp: ["lamp", "lighting"], brass: ["articles of brass", "brass", "copper"], rakhi: ["rakhi", "made up"], notebook: ["exercise book", "notebook"], copy: ["exercise book"],
    journal: ["exercise book", "note book", "diaries", "notebook"], diary: ["diaries", "note book", "notebook"]
  };
  function norm(t) { return " " + String(t).toLowerCase().replace(/[^a-z0-9%]+/g, " ") + " "; }
  // 1 if the first (best) alternative is present, less for later ones, 0 if none.
  function count(hay, alts) { for (var i = 0; i < alts.length; i++) if (hay.indexOf(" " + alts[i]) >= 0) return 1 / (1 + i * 0.5); return 0; }
  function esc(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }

  function fmtCode(c) { return c.length === 8 ? c.slice(0, 4) + " " + c.slice(4, 6) + " " + c.slice(6) : c.length === 6 ? c.slice(0, 4) + " " + c.slice(4) : c; }

  function load(url) {
    return fetch(url).then(function (r) { if (!r.ok) throw new Error("hsn"); return r.json(); }).then(function (H) {
      LINES = H.t.map(function (row) {
        var code = row[0], h4 = code.slice(0, 4);
        var title = (code.length >= 6 && H.x[code.slice(0, 6)]) || H.h[h4] || "";
        var heading = H.h[h4] || "";
        var ch = H.c[code.slice(0, 2)] || ["", ""];
        var l = { code: code, title: title, detail: row[1] || "", heading: heading, chapter: ch[0],
                  hay: norm(title + " " + heading + " " + (row[1] || "")) };
        BY[code] = l;
        return l;
      });
      return LINES;
    });
  }

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

  function shortName(l) {
    var t = (l.title || l.heading).split(/;|\(/)[0].trim();
    var rest = (l.title || "").split(";")[1];
    if (rest && t.length < 40) t += "," + rest.split(/,|\(/)[0];
    return t.replace(/\s+/g, " ").trim().slice(0, 90);
  }

  /* opts: {input, list, status, onPick(line), onClear(), idPrefix} — the listbox markup uses .sf-* classes. */
  function combo(o) {
    var shown = [], active = -1, t, picked = null, pfx = o.idPrefix || "hsnOpt";
    function render(items) {
      shown = items; active = -1;
      if (!items.length) {
        o.list.innerHTML = ""; o.list.hidden = true; o.input.setAttribute("aria-expanded", "false");
        if (o.input.value.trim().length >= 2 && LINES.length) o.status.textContent = "No match. Try a simpler word (e.g. \"bedsheet\" → \"bed linen\") or the first 4 digits of the code.";
        return;
      }
      o.status.textContent = items.partial ? "No exact match for every word. Showing the closest codes. Try one simple word, like \"lamp\" or \"saree\"." : items.length >= 40 ? "Showing the first 40 matches. Type more to narrow it down." : items.length + " matches";
      o.list.innerHTML = items.map(function (l, i) {
        return '<li role="option" id="' + pfx + i + '" data-i="' + i + '"><span class="sf-code">' + esc(fmtCode(l.code)) + '</span>' +
          '<span class="sf-otitle">' + esc(l.title || l.heading) + '</span>' +
          (l.detail ? '<span class="sf-odetail">' + esc(l.detail) + '</span>' : "") + '</li>';
      }).join("");
      o.list.hidden = false; o.input.setAttribute("aria-expanded", "true");
    }
    function setActive(i) {
      var opts = o.list.querySelectorAll("li");
      if (!opts.length) return;
      active = (i + opts.length) % opts.length;
      opts.forEach(function (x, k) { x.classList.toggle("is-active", k === active); x.setAttribute("aria-selected", k === active); });
      o.input.setAttribute("aria-activedescendant", pfx + active);
      opts[active].scrollIntoView({ block: "nearest" });
    }
    function pick(l) {
      picked = l;
      o.list.hidden = true; o.input.setAttribute("aria-expanded", "false");
      o.input.value = l.code; o.status.textContent = "";
      o.onPick(l);
    }
    o.input.addEventListener("input", function () {
      clearTimeout(t);
      if (picked && o.input.value !== picked.code) { picked = null; if (o.onClear) o.onClear(); }
      t = setTimeout(function () { render(search(o.input.value)); }, 120);
    });
    o.input.addEventListener("keydown", function (e) {
      if (o.list.hidden) return;
      if (e.key === "ArrowDown") { e.preventDefault(); setActive(active + 1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); setActive(active - 1); }
      else if (e.key === "Enter") { if (active >= 0 || shown.length === 1) { e.preventDefault(); pick(shown[Math.max(active, 0)]); } }
      else if (e.key === "Escape") { o.list.hidden = true; }
    });
    o.list.addEventListener("mousedown", function (e) {
      var li = e.target.closest("li"); if (!li) return; e.preventDefault(); pick(shown[+li.dataset.i]);
    });
    document.addEventListener("click", function (e) { if (!o.list.contains(e.target) && e.target !== o.input) o.list.hidden = true; });
    return {
      pick: pick,
      clear: function () { picked = null; o.input.value = ""; o.input.focus(); },
      // For ?hsn= deep links: pick an exact code, else show matches for it.
      prefill: function (code) { if (BY[code]) pick(BY[code]); else { o.input.value = code; render(search(code)); } }
    };
  }

  window.KMHSN = { load: load, search: search, combo: combo, fmtCode: fmtCode, shortName: shortName,
                   byCode: function (c) { return BY[c]; }, esc: esc };
})();
