// Scoring + matching. Pure functions, no DOM — shared by the browser and tests.

export const DIMS = ["R", "I", "A", "S", "E", "C"];
export const TRAITS = ["openness", "conscientiousness", "extraversion", "agreeableness", "stability"];

// Plain-language names — the UI never shows "RIASEC" or "Big Five".
export const DIM_LABELS = {
  R: "Maker", I: "Thinker", A: "Creator", S: "Helper", E: "Persuader", C: "Organiser",
};
export const DIM_PHRASES = {
  R: "you like working with your hands and real, physical things",
  I: "you like figuring out how and why things work",
  A: "you like creating things in your own style",
  S: "you like helping, teaching and looking after people",
  E: "you like selling, persuading and taking charge",
  C: "you like order, numbers and systems that run smoothly",
};
const ARCHETYPES = {
  RI: "The Builder-Engineer", RA: "The Maker", RS: "The Hands-on Helper", RE: "The Hustling Doer",
  RC: "The Reliable Operator", IA: "The Inventor", IS: "The Expert Guide", IE: "The Strategist",
  IC: "The Analyst", AS: "The Creative Mentor", AE: "The Brand Builder", AC: "The Detail Designer",
  SE: "The Community Builder", SC: "The Service Pro", EC: "The Trader",
};

const WEIGHT_INTEREST = 0.72;
const WEIGHT_TRAITS = 0.28;
const OVERSHOOT_PENALTY = 0.25; // having more of a trait than an idea needs costs little
const LOCAL_BONUS = 0.05; // the user's district ODOP: raw material, artisans and buyers are nearby
const EXACT_LOCAL_BONUS = 0.03; // extra when the idea is that exact district product, not just the same model
const TRAIT_FIT_KEYS = ["openness", "conscientiousness", "extraversion", "agreeableness"];

// ── Data ─────────────────────────────────────────────────────────────────────

/**
 * ideas.json has two layers: business models (profile + evidence) and the
 * ideas users see. Each idea inherits its model's profile; `slug` is the
 * model's slug so ODOP and other model-level links keep working.
 */
export function hydrate(data) {
  const models = Object.fromEntries(data.models.map((m) => [m.slug, m]));
  return data.ideas.map((i) => {
    const m = models[i.model];
    return {
      ...i, slug: m.slug, riasec: m.riasec, traits: m.traits, code: m.code,
      sub: m.sub, category: m.category, modelName: m.name, modelData: m,
    };
  });
}

function hash(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) h = Math.imul(h ^ str.charCodeAt(i), 16777619);
  return h >>> 0;
}

// ── Profile ──────────────────────────────────────────────────────────────────

/** answers: { [questionId]: number 1–5 | choice value } */
export function computeProfile(questions, answers) {
  const sums = {}, counts = {};
  for (const q of questions) {
    const a = answers[q.id];
    if (a == null || (q.kind !== "interest" && q.kind !== "trait")) continue;
    const key = q.kind === "interest" ? q.dim : q.trait;
    const v = q.reverse ? 6 - a : a;
    sums[key] = (sums[key] ?? 0) + (v - 1) / 4;
    counts[key] = (counts[key] ?? 0) + 1;
  }
  const norm = (k) => (counts[k] ? sums[k] / counts[k] : 0.5);
  // Ideas on the same model score the same; the seed breaks those ties per
  // answer set, so different people see different ideas from one model.
  const seed = hash(questions.filter((q) => q.kind === "interest" || q.kind === "trait")
    .map((q) => answers[q.id] ?? "-").join(""));
  return {
    seed,
    riasec: Object.fromEntries(DIMS.map((d) => [d, norm(d)])),
    traits: Object.fromEntries(TRAITS.map((t) => [t, norm(t)])),
    constraints: {
      budget: answers.budget ?? 4,
      location: answers.location ?? "open",
      team: answers.team ?? "small",
      time: answers.time ?? "full",
      // The ODOP product of the user's district, if they picked one and it maps to an idea.
      localIdea: answers.district?.idea || null,
      localKey: answers.district ? `${answers.district.district}|${answers.district.state}` : null,
    },
  };
}

export function topDims(riasec, n = 2) {
  return [...DIMS].sort((a, b) => riasec[b] - riasec[a] || DIMS.indexOf(a) - DIMS.indexOf(b)).slice(0, n);
}

/** MBTI-style shorthand derived from Big Five traits. */
export function typeCode(traits) {
  return (
    (traits.extraversion >= 0.5 ? "E" : "I") +
    (traits.openness >= 0.5 ? "N" : "S") +
    (traits.agreeableness >= 0.5 ? "F" : "T") +
    (traits.conscientiousness >= 0.5 ? "J" : "P")
  );
}

export function archetype(riasec) {
  const [a, b] = topDims(riasec, 2);
  const key = DIMS.indexOf(a) < DIMS.indexOf(b) ? a + b : b + a;
  return ARCHETYPES[key];
}

// ── Matching ─────────────────────────────────────────────────────────────────

function pearson(x, y) {
  const n = x.length;
  const mx = x.reduce((s, v) => s + v, 0) / n;
  const my = y.reduce((s, v) => s + v, 0) / n;
  let num = 0, dx = 0, dy = 0;
  for (let i = 0; i < n; i++) {
    num += (x[i] - mx) * (y[i] - my);
    dx += (x[i] - mx) ** 2;
    dy += (y[i] - my) ** 2;
  }
  if (dx < 1e-6 || dy < 1e-6) return null;
  return num / Math.sqrt(dx * dy);
}

/** 0–1. Shape match (Pearson, as O*NET's own profiler does); falls back to distance for flat profiles. */
export function interestFit(userVec, ideaVec) {
  const r = pearson(userVec, ideaVec);
  if (r !== null) return (r + 1) / 2;
  const dist = Math.sqrt(userVec.reduce((s, v, i) => s + (v - ideaVec[i]) ** 2, 0));
  return 1 - dist / Math.sqrt(userVec.length);
}

export function traitFit(userTraits, ideaTraits) {
  let penalty = 0;
  for (const k of TRAIT_FIT_KEYS) {
    const need = ideaTraits[TRAITS.indexOf(k)];
    const have = userTraits[k];
    penalty += have < need ? need - have : (have - need) * OVERSHOOT_PENALTY;
  }
  return 1 - penalty / TRAIT_FIT_KEYS.length;
}

const LOCATION_OK = {
  online: ["online", "any"],
  city: ["local", "online", "any"],
  rural: ["rural", "online", "any"],
  open: ["online", "local", "rural", "any"],
};

const FILTERS = {
  time: (idea, c) => c.time === "full" || idea.time !== "full",
  location: (idea, c) => LOCATION_OK[c.location].includes(idea.location),
  budget: (idea, c) => idea.budget <= c.budget,
};
// If filters leave too few ideas, drop them in this order.
const RELAX_ORDER = ["time", "location", "budget"];

function applyFilters(ideas, constraints, minCount) {
  let active = [...RELAX_ORDER];
  const relaxed = [];
  for (;;) {
    const pool = ideas.filter((i) => active.every((f) => FILTERS[f](i, constraints)));
    if (pool.length >= minCount || active.length === 0) return { pool, relaxed };
    relaxed.push(active.shift());
  }
}

function teamPenalty(idea, team) {
  if (team === "solo" && idea.team === "team") return 0.08;
  if (team === "solo" && idea.team === "small") return 0.02;
  if (team === "team" && idea.team === "solo") return 0.03;
  return 0;
}

function riskPenalty(idea, traits) {
  return traits.stability < 0.4 && idea.budget >= 3 ? 0.04 : 0;
}

export function scoreIdea(idea, profile) {
  const userVec = DIMS.map((d) => profile.riasec[d]);
  const interest = interestFit(userVec, idea.riasec);
  const traits = traitFit(profile.traits, idea.traits);
  const exact = !!profile.constraints.localKey && !!idea.odop_here?.keys?.includes(profile.constraints.localKey);
  const local = exact || profile.constraints.localIdea === idea.slug;
  const score =
    WEIGHT_INTEREST * interest + WEIGHT_TRAITS * traits -
    teamPenalty(idea, profile.constraints.team) - riskPenalty(idea, profile.traits) +
    (local ? LOCAL_BONUS : 0) + (exact ? EXACT_LOCAL_BONUS : 0);
  return { idea, score, interest, traits, local };
}

/** Returns { top, runnersUp, relaxed } — runners-up prefer different sub-categories. */
export function match(ideas, profile, { runnersUp = 2 } = {}) {
  const want = 1 + runnersUp;
  const tiebreak = (idea) => hash(`${profile.seed ?? 0}:${idea.id}`);
  const { pool, relaxed } = applyFilters(ideas, profile.constraints, want);
  const ranked = pool
    .map((i) => scoreIdea(i, profile))
    .sort((a, b) => b.score - a.score || tiebreak(a.idea) - tiebreak(b.idea) || a.idea.id - b.idea.id);

  const picks = [];
  for (const r of ranked) {
    if (picks.length >= want) break;
    if (!picks.some((p) => p.idea.sub === r.idea.sub)) picks.push(r);
  }
  for (const r of ranked) {
    if (picks.length >= want) break;
    if (!picks.includes(r)) picks.push(r);
  }
  return { top: picks[0], runnersUp: picks.slice(1), relaxed, poolSize: pool.length };
}

/** Where one chosen idea (the guide the user came from) ranks for this profile, and which filters it misses. */
export function fitCheck(ideas, target, profile) {
  const result = scoreIdea(target, profile);
  const rank = 1 + ideas.filter((i) => i !== target && scoreIdea(i, profile).score > result.score).length;
  const pct = rank / ideas.length;
  const band = pct <= 0.1 ? "strong" : pct <= 0.3 ? "good" : pct <= 0.6 ? "partial" : "weak";
  const gaps = RELAX_ORDER.filter((f) => !FILTERS[f](target, profile.constraints));
  return { result, rank, total: ideas.length, band, gaps };
}

export const FIT_BANDS = {
  strong: "Strong fit",
  good: "Good fit",
  partial: "Partial fit",
  weak: "Weak fit",
};
export const GAP_LABELS = {
  time: "It needs full-time attention, and you said you can only start part-time.",
  location: "It works best in a different kind of location from the one you chose.",
  budget: "It usually needs more starting money than the budget you chose.",
};

// ── Copy ─────────────────────────────────────────────────────────────────────

const TRAIT_LINES = {
  openness: "It rewards trying new things, which suits your curious side.",
  conscientiousness: "It runs on consistency and follow-through — which you've said you have.",
  extraversion: "It's people-heavy, and meeting people gives you energy.",
  agreeableness: "Happy customers drive it, and you naturally put them first.",
};

export function whyCopy(result, profile, { withIntro = true, district = null } = {}) {
  const [a, b] = topDims(profile.riasec, 2);
  const ideaTop = topDims(Object.fromEntries(DIMS.map((d, i) => [d, result.idea.riasec[i]])), 2);
  const shared = ideaTop.filter((d) => d === a || d === b);

  let line = withIntro
    ? `You lean ${DIM_LABELS[a]} + ${DIM_LABELS[b]}: ${DIM_PHRASES[a]}, and ${DIM_PHRASES[b].replace(/^you /, "")}.`
    : "";
  if (shared.length) {
    line += ` ${result.idea.name} leans on exactly that ${shared.map((d) => DIM_LABELS[d]).join(" + ")} side.`;
  } else {
    line += ` ${result.idea.name} is your closest overall match — it uses a mix of your strengths.`;
  }

  // Best-aligned demanding trait.
  let best = null;
  for (const k of TRAIT_FIT_KEYS) {
    const need = result.idea.traits[TRAITS.indexOf(k)];
    const have = profile.traits[k];
    if (need >= 0.55 && have >= need - 0.05 && (!best || need > best.need)) best = { k, need };
  }
  if (best) line += " " + TRAIT_LINES[best.k];
  if (result.local && district) {
    line += ` It's also ${district.district}'s ODOP product, so raw material, skilled workers and buyers are already nearby.`;
  }
  return line.trim();
}

export function formatRupees(rupees) {
  return rupees == null ? "" : formatLakh(rupees / 100000);
}

/** Amounts in the Shark Tank data are in ₹ lakhs. */
export function formatLakh(lakh) {
  if (lakh == null) return "";
  if (lakh >= 100) return `₹${+(lakh / 100).toFixed(1)} Cr`;
  if (lakh >= 1) return `₹${+lakh.toFixed(1)}L`;
  return `₹${Math.round(lakh * 100000).toLocaleString("en-IN")}`;
}

export const BUDGET_LABELS = { 1: "Under ₹50K", 2: "₹50K–2L", 3: "₹2–10L", 4: "₹10L+" };
export const RELAX_LABELS = {
  time: "full-time ideas",
  location: "other locations",
  budget: "higher budgets",
};
