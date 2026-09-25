// Question bank. All items are original wording.
// kind "interest": how much you'd enjoy an activity → RIASEC dimension
// kind "trait":    how much you agree with a statement → Big Five trait (reverse = negatively keyed)
// kind "choice":   practical constraints used as filters before matching
// kind "district": optional home district (state → district picker); its ODOP product gets a local-advantage boost

export const INTEREST_SCALE = ["Hate it", "Dislike", "Neutral", "Like", "Love it"];
export const AGREE_SCALE = ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"];

export const QUESTIONS = [
  // Constraints first — quick, concrete, gets people started.
  { id: "budget", kind: "choice", text: "How much could you invest to get started?",
    options: [
      { value: 1, label: "Under ₹50,000" },
      { value: 2, label: "₹50,000 – ₹2 lakh" },
      { value: 3, label: "₹2 – 10 lakh" },
      { value: 4, label: "More than ₹10 lakh" },
    ] },
  { id: "location", kind: "choice", text: "Where do you want to run it?",
    options: [
      { value: "online", label: "Online, from anywhere" },
      { value: "city", label: "In my city or town" },
      { value: "rural", label: "In a village or rural area" },
      { value: "open", label: "I'm open to anything" },
    ] },
  { id: "district", kind: "district", optional: true,
    text: "Which district are you from?",
    hint: "Optional. Every district has an ODOP (One District One Product). If yours suits you, we'll show it." },
  { id: "team", kind: "choice", text: "Who's building it with you?",
    options: [
      { value: "solo", label: "Just me" },
      { value: "small", label: "1–2 partners or family" },
      { value: "team", label: "I want to build a team" },
    ] },
  { id: "time", kind: "choice", text: "How much time can you give it?",
    options: [
      { value: "side", label: "A few hours a day, alongside a job or studies" },
      { value: "full", label: "Full-time" },
    ] },

  // Interests — "How would you feel spending a good part of your day…"
  { id: "r1", kind: "interest", dim: "R", text: "Repairing a bike, machine or appliance until it works again" },
  { id: "i1", kind: "interest", dim: "I", text: "Digging into numbers to work out why sales went down" },
  { id: "a1", kind: "interest", dim: "A", text: "Designing a logo, a product or the look of a shop" },
  { id: "s1", kind: "interest", dim: "S", text: "Teaching someone a skill until they finally get it" },
  { id: "e1", kind: "interest", dim: "E", text: "Convincing a shopkeeper to stock your product" },
  { id: "c1", kind: "interest", dim: "C", text: "Keeping accounts, bills and GST records neat and up to date" },

  { id: "r2", kind: "interest", dim: "R", text: "Making things with your hands — cooking, building, stitching or growing" },
  { id: "i2", kind: "interest", dim: "I", text: "Researching a product in depth before you buy or sell it" },
  { id: "a2", kind: "interest", dim: "A", text: "Coming up with new recipes, styles or content ideas" },
  { id: "s2", kind: "interest", dim: "S", text: "Patiently helping a customer sort out their problem" },
  { id: "e2", kind: "interest", dim: "E", text: "Negotiating a better price with a supplier" },
  { id: "c2", kind: "interest", dim: "C", text: "Following a checklist so every order goes out exactly right" },

  { id: "r3", kind: "interest", dim: "R", text: "Being on your feet — on a shop floor, a farm or a site — not at a desk" },
  { id: "i3", kind: "interest", dim: "I", text: "Solving a tricky technical or logical puzzle" },
  { id: "a3", kind: "interest", dim: "A", text: "Creating something that shows off your own taste and style" },
  { id: "s3", kind: "interest", dim: "S", text: "Looking after people — kids, elders, patients or guests" },
  { id: "e3", kind: "interest", dim: "E", text: "Leading a small team and pushing them to hit targets" },
  { id: "c3", kind: "interest", dim: "C", text: "Managing stock so nothing runs out and nothing goes to waste" },

  // Traits
  { id: "o1", kind: "trait", trait: "openness", text: "I get bored doing the same thing the same way" },
  { id: "c4", kind: "trait", trait: "conscientiousness", text: "I finish what I start, even when it gets boring" },
  { id: "x1", kind: "trait", trait: "extraversion", text: "Talking to strangers gives me energy" },
  { id: "g1", kind: "trait", trait: "agreeableness", text: "I'd rather keep a customer happy than win an argument" },
  { id: "n1", kind: "trait", trait: "stability", text: "I stay calm when money is tight or plans fall apart" },
  { id: "o2", kind: "trait", trait: "openness", reverse: true, text: "I prefer proven methods over trying new ideas" },
  { id: "c5", kind: "trait", trait: "conscientiousness", reverse: true, text: "My plans often slip because I leave things to the last minute" },
  { id: "x2", kind: "trait", trait: "extraversion", reverse: true, text: "After a day of meeting people, I need quiet time alone" },
  { id: "g2", kind: "trait", trait: "agreeableness", reverse: true, text: "I don't mind being blunt if it gets the deal done" },
  { id: "n2", kind: "trait", trait: "stability", reverse: true, text: "Not knowing how much I'll earn next month would keep me up at night" },
];
