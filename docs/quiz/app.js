import { QUESTIONS, INTEREST_SCALE, AGREE_SCALE } from "./questions.js";
import {
  hydrate, computeProfile, match, scoreIdea, whyCopy, typeCode, archetype, topDims, fitCheck,
  DIMS, DIM_LABELS, BUDGET_LABELS, RELAX_LABELS, FIT_BANDS, GAP_LABELS, formatLakh, formatRupees,
} from "./scoring.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

const PROMPTS = {
  interest: "How would you feel spending a good part of your day…",
  trait: "How much do you agree?",
  choice: "",
  district: "",
};

let ideas = [];
let districts = []; // ODOP index: one entry per district
let answers = {};
let idx = 0;

// Fit-check mode: guide pages link here as ?idea=<key>, and the result opens with that idea's fit.
const checkKey = new URLSearchParams(location.search).get("idea");
let checkIdea = null;

const ideasReady = fetch("data/ideas.json").then((r) => r.json()).then((d) => {
  ideas = hydrate(d);
  checkIdea = checkKey ? ideas.find((i) => i.key === checkKey) || null : null;
  if (checkIdea) {
    $("intro-eyebrow").textContent = "KidharMilega · Fit check";
    $("intro-title").innerHTML = `Does <em>${esc(checkIdea.name)}</em> fit you?`;
    $("intro-lede").textContent = `33 quick taps, about 3 minutes. We'll score how well ${checkIdea.name} matches your interests, personality, budget and location, and show the ideas that fit you even better.`;
  }
});
const districtsReady = fetch("data/odop.json").then((r) => r.json()).then((d) => { districts = d; });
// Keys of ideas with a published guide on kidharmilega.in/ideas/. The site export writes this file;
// standalone builds don't have it, so result cards simply skip the guide link.
let guides = new Set();
const guidesReady = fetch("data/guides.json").then((r) => (r.ok ? r.json() : [])).then((k) => { guides = new Set(k); }).catch(() => {});
const GUIDES_URL = "../ideas/";

function show(id) {
  for (const s of document.querySelectorAll(".screen")) s.hidden = s.id !== id;
  window.scrollTo(0, 0);
}

function render() {
  const q = QUESTIONS[idx];
  $("bar").style.width = `${(idx / QUESTIONS.length) * 100}%`;
  $("counter").textContent = `Question ${idx + 1} of ${QUESTIONS.length}`;
  $("prompt").textContent = q.hint || PROMPTS[q.kind];
  $("qtext").textContent = q.text;
  $("back").hidden = idx === 0;

  if (q.kind === "district") {
    renderDistrictPicker(q);
    return;
  }

  const opts = q.kind === "choice"
    ? q.options
    : (q.kind === "interest" ? INTEREST_SCALE : AGREE_SCALE).map((label, i) => ({ value: i + 1, label }));

  $("options").innerHTML = "";
  for (const o of opts) {
    const b = document.createElement("button");
    b.className = "opt" + (answers[q.id] === o.value ? " selected" : "");
    b.textContent = o.label;
    b.onclick = () => choose(q.id, o.value);
    $("options").appendChild(b);
  }
}

async function renderDistrictPicker(q) {
  $("options").innerHTML = `<p class="fine">Loading districts…</p>`;
  await districtsReady;
  if (QUESTIONS[idx] !== q) return; // user moved on while loading

  const current = answers[q.id];
  const states = [...new Set(districts.map((d) => d.state))];
  $("options").innerHTML = `
    <label class="field">State
      <select id="state-select"><option value="">Choose your state</option>
        ${states.map((st) => `<option ${current?.state === st ? "selected" : ""}>${esc(st)}</option>`).join("")}
      </select>
    </label>
    <label class="field">District
      <select id="district-select" disabled><option value="">Choose your district</option></select>
    </label>
    <button id="district-next" class="btn primary" disabled>Continue</button>
    <button id="district-skip" class="btn ghost">Skip this question</button>`;

  const stateSel = $("state-select"), distSel = $("district-select"), next = $("district-next");
  const fillDistricts = () => {
    const list = districts.filter((d) => d.state === stateSel.value);
    distSel.innerHTML = `<option value="">Choose your district</option>` +
      list.map((d) => `<option ${current?.district === d.district && current?.state === d.state ? "selected" : ""}>${esc(d.district)}</option>`).join("");
    distSel.disabled = !list.length;
    next.disabled = !distSel.value;
  };
  stateSel.onchange = fillDistricts;
  distSel.onchange = () => { next.disabled = !distSel.value; };
  next.onclick = () => choose(q.id, districts.find((d) => d.state === stateSel.value && d.district === distSel.value));
  $("district-skip").onclick = () => choose(q.id, null);
  if (current) fillDistricts();
}

function choose(id, value) {
  answers[id] = value;
  if (idx < QUESTIONS.length - 1) {
    idx++;
    render();
  } else {
    finish();
  }
}

async function finish() {
  await Promise.all([ideasReady, districtsReady, guidesReady]);
  const profile = computeProfile(QUESTIONS, answers);
  const result = match(ideas, profile);
  const check = checkIdea ? fitCheck(ideas, checkIdea, profile) : null;
  renderResult(profile, result, check);
  show("result");
}

function stExample(e) {
  const deal = e.deal
    ? `got ${formatLakh(e.deal.amount_lakh)} for ${+e.deal.equity_pct.toFixed(2)}%${e.deal.sharks.length ? ` from ${e.deal.sharks.join(", ")}` : ""}`
    : `asked ${formatLakh(e.ask.amount_lakh)} for ${e.ask.equity_pct}%, no deal`;
  const rev = e.revenue_lakh ? `, ${formatLakh(e.revenue_lakh)} yearly revenue` : "";
  const space = e.space ? ` <span class="muted">[${esc(e.space)}]</span>` : "";
  return `<li><strong>${esc(e.name)}</strong>${space} <span class="muted">(S${e.season} E${e.episode}${e.city ? `, ${esc(e.city)}` : ""})</span> — ${esc(e.what)}${rev}; ${deal}.</li>`;
}

function d2cBlock(examples) {
  if (!examples?.length) return "";
  return `<div class="shark"><p class="shark-head">🛒 D2C brands on Shark Tank India</p>
    <p class="fine">Other direct-to-consumer brands that built online, even if their product is different. Their playbook for sourcing, pricing and selling online carries over.</p>
    <ul>${examples.map(stExample).join("")}</ul></div>`;
}

function sharkTank(st, isTop) {
  if (!st) return "";
  const summary = `${st.pitches} Shark Tank India pitch${st.pitches > 1 ? "es" : ""} in this space · ${st.deals} got a deal` +
    (st.median_revenue_lakh ? ` · median revenue ${formatLakh(st.median_revenue_lakh)}/yr` : "");
  const examples = (isTop ? st.examples : st.examples.slice(0, 1)).map(stExample).join("");
  const note = isTop ? `<p class="fine">These brands scaled far enough to pitch on TV — most started much smaller.</p>` : "";
  return `<div class="shark"><p class="shark-head">🦈 ${summary}</p><ul>${examples}</ul>${note}</div>`;
}

function odopLine(odop) {
  if (!odop) return "";
  const links = odop.examples.map((e) =>
    `<a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.district)}</a>`).join(", ");
  const more = odop.districts > odop.examples.length ? ", and more" : "";
  return `<p class="odop-line">📍 ODOP product of ${odop.districts} district${odop.districts > 1 ? "s" : ""}: ${links}${more}.</p>`;
}

function districtCard(district, profile) {
  if (!district) return "";
  const idea = ideas.find((i) => i.slug === district.idea);
  const fit = idea ? scoreIdea(idea, profile) : null;
  const cost = district.cost[0] ? `Setup ${formatRupees(district.cost[0])}–${formatRupees(district.cost[1])}` : "";
  const facts = [cost, district.margin && `D2C margins ${esc(district.margin)}`, district.breakeven && `break-even ${esc(district.breakeven)}`]
    .filter(Boolean).join(" · ");
  return `
    <article class="card odop">
      <p class="eyebrow">Your district · ${esc(district.district)}, ${esc(district.state)}${fit ? ` · ${Math.round(fit.score * 100)}% fit for you` : ""}</p>
      <h3>ODOP: ${esc(district.product)}</h3>
      <p>${esc(district.why)}</p>
      ${facts ? `<p class="fine">${facts}</p>` : ""}
      ${idea ? `<p class="fine">Closest business model: ${esc(idea.modelName)}.</p>` : ""}
      <a class="btn primary" href="${esc(district.url)}" target="_blank" rel="noopener">See the ${esc(district.product)} playbook on KidharMilega →</a>
    </article>`;
}

function similarIdeas(i) {
  const sibs = ideas.filter((x) => x.model === i.model && x.id !== i.id).slice(0, 4);
  return sibs.length ? `<p class="fine">Similar ideas: ${sibs.map((x) => esc(x.name)).join(" · ")}</p>` : "";
}

function guideLink(i, isTop) {
  if (!guides.size) return "";
  if (guides.has(i.key)) {
    return `<div class="card-actions"><a class="btn ${isTop ? "primary" : ""}" href="${GUIDES_URL}${encodeURIComponent(i.key)}/">Read Full Guide <span aria-hidden="true">→</span></a></div>`;
  }
  // No guide yet: point to the closest published guide on the same business model, if any.
  const near = ideas.find((x) => x.model === i.model && guides.has(x.key));
  if (near) {
    return `<div class="card-actions"><a class="btn ${isTop ? "primary" : ""}" href="${GUIDES_URL}${encodeURIComponent(near.key)}/">Read Full Guide <span aria-hidden="true">→</span></a></div>
      <p class="fine">This idea's own guide is coming soon; the guide above covers ${esc(near.name)}, which runs on the same business model.</p>`;
  }
  return `<p class="fine">The full guide for this idea is coming soon. <a href="${GUIDES_URL}">Browse the business ideas with guides</a>.</p>`;
}

function ideaCard(r, profile, isTop) {
  const i = r.idea;
  const m = i.modelData;
  return `
    <article class="card ${isTop ? "top" : ""}">
      <p class="eyebrow">${isTop ? "Your best match" : "Also a strong fit"} · ${Math.round(r.score * 100)}% fit</p>
      <h3>${esc(i.name)}</h3>
      <p>${esc(i.pitch)}</p>
      <div class="meta">
        <span class="chip">${esc(i.category)}</span>
        ${i.market ? `<span class="chip">For: ${esc(i.market)}</span>` : ""}
        <span class="chip">Start: ${BUDGET_LABELS[i.budget]}</span>
        <span class="chip">${i.team === "solo" ? "Solo-friendly" : i.team === "small" ? "Small team" : "Needs a team"}</span>
        <span class="chip">${i.time === "full" ? "Full-time" : "Can start part-time"}</span>
      </div>
      <p class="why">${esc(whyCopy(r, profile, { withIntro: isTop, district: answers.district }))}</p>
      ${i.name !== i.modelName ? `<p class="fine">Business model: ${esc(i.modelName)}</p>` : ""}
      ${guideLink(i, isTop)}
      ${isTop ? similarIdeas(i) : ""}
      ${i.inspired_by ? `<div class="shark"><p class="shark-head">🦈 The Shark Tank India pitch behind this idea</p><ul>${stExample(i.inspired_by)}</ul></div>` : ""}
      ${odopLine(i.odop_here || m.odop)}
      ${i.inspired_by && !isTop ? "" : sharkTank(m.sharktank, isTop)}
      ${i.d2c && (isTop || !m.sharktank) ? d2cBlock(isTop ? m.sharktank_d2c : m.sharktank_d2c?.slice(0, 1)) : ""}
    </article>`;
}

function fitCard(check, profile) {
  const i = check.result.idea;
  const gaps = check.gaps.map((g) => `<li>${esc(GAP_LABELS[g])}</li>`).join("");
  return `
    <article class="card top fit-check">
      <p class="eyebrow">Your fit check · ${FIT_BANDS[check.band]}</p>
      <h3>${esc(i.name)}: ${Math.round(check.result.score * 100)}% fit</h3>
      <p>It ranks <strong>#${check.rank.toLocaleString("en-IN")} of ${check.total.toLocaleString("en-IN")}</strong> ideas for you.</p>
      <p class="why">${esc(whyCopy(check.result, profile, { withIntro: false, district: answers.district }))}</p>
      ${gaps ? `<p class="fine">Watch out:</p><ul class="fine">${gaps}</ul>` : ""}
      <a class="btn" href="../ideas/${encodeURIComponent(i.key)}/">Back to the ${esc(i.name)} guide</a>
    </article>`;
}

function renderResult(profile, { top, runnersUp, relaxed }, check = null) {
  const code = typeCode(profile.traits);
  const arch = archetype(profile.riasec);
  const [a, b] = topDims(profile.riasec, 2);
  const bars = [...DIMS]
    .sort((x, y) => profile.riasec[y] - profile.riasec[x])
    .map((d) => `
      <div class="bar-row"><span>${DIM_LABELS[d]}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${Math.round(profile.riasec[d] * 100)}%"></div></div>
      </div>`).join("");

  const relaxNote = relaxed.length
    ? `<p class="notice">Very few ideas matched all your filters, so we also included ${relaxed.map((r) => RELAX_LABELS[r]).join(" and ")}.</p>`
    : "";

  $("result").innerHTML = `
    <p class="eyebrow">Your founder type</p>
    <h1><span class="type-badge">${code}</span> ${arch}</h1>
    <p class="lede">You're strongest as a ${DIM_LABELS[a]} and ${DIM_LABELS[b]}.</p>
    <div class="bars">${bars}</div>
    ${relaxNote}
    ${check ? fitCard(check, profile) : ""}
    ${check ? `<h2 class="section-head">${check.rank === 1 ? "Your other strong matches" : "Ideas that fit you even better"}</h2>` : ""}
    ${[top, ...runnersUp].filter((r) => !check || r.idea !== check.result.idea)
      .map((r, n) => ideaCard(r, profile, !check && n === 0)).join("")}
    ${districtCard(answers.district, profile)}
    <div class="actions">
      <button id="share" class="btn primary">Share my result</button>
      <button id="retake" class="btn">Retake quiz</button>
    </div>
    <p class="fine">The four-letter type is a Myers-Briggs-style shorthand worked out from your personality answers.</p>`;

  $("retake").onclick = () => { answers = {}; idx = 0; show("intro"); };
  const shareName = check ? check.result.idea.name : top.idea.name;
  $("share").onclick = async () => {
    const text = check
      ? `I'm ${code} · ${arch} — ${shareName} is a ${FIT_BANDS[check.band].toLowerCase()} for me. Check yours:`
      : `I'm ${code} · ${arch} — my best-fit business is ${shareName}. Find yours:`;
    const url = location.href.split("#")[0];
    try {
      if (navigator.share) await navigator.share({ text, url });
      else { await navigator.clipboard.writeText(`${text} ${url}`); $("share").textContent = "Copied!"; }
    } catch { /* share sheet dismissed */ }
  };
}

$("start").onclick = () => { show("quiz"); render(); };
$("back").onclick = () => { if (idx > 0) { idx--; render(); } };
