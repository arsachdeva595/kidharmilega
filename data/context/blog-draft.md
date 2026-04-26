# I Built a Machine That Researches 787 Indian Districts So You Don't Have To

*How a DM saying "bhai kaunsa business karoon?" became a pipeline that hunts government portals, scrapes DuckDuckGo, transcribes YouTube videos, and turns all of it into a startup guide — one district at a time.*

---

## It started with a question I couldn't answer

I run a page called **Startup Wale Bhaia**.

The idea was simple: talk to people trying to build something real — not the VC-backed startup crowd in Bangalore, but the guy in Gorakhpur who has ₹3 lakh saved up and genuinely doesn't know where to begin. The guy whose family keeps saying "naukri kar le" but whose gut keeps saying otherwise.

The page grew. 15,000 followers. Then the DMs started coming in.

Over a thousand of them. Each asking roughly the same thing in a hundred different ways:

> "Bhai mere paas 2 lakh hai, kaunsa business karoon?"
> "UP mein kaunsa product export hota hai?"
> "Mera district Bhagalpur hai — koi opportunity hai kya?"
> "GI tag kya hota hai aur iske saath kya kiya ja sakta hai?"

I was answering them one by one. And every time I sat down to answer, I hit the same wall: **there was no single place where this information lived.**

Government websites existed — but broken, buried behind three layers of navigation, or completely empty. Export data was in PDFs from 2019. YouTube had the good stuff but it was scattered, in Hindi, unstructured. Nobody had assembled it for the person who actually needed it.

So I decided to build it myself.

---

## The idea: KidharMilega

India's central government runs a scheme called **ODOP — One District One Product**. The concept is elegant: every district has something it's historically been best at making. Bhagalpur makes silk. Tiruppur makes hosiery. Bikaner makes namkeen. Jaipur cuts gemstones.

The scheme exists. The products exist. The clusters exist. The artisans exist.

What doesn't exist is **a page that tells a first-generation founder, in plain language, exactly what the opportunity looks like and how to enter it** — with real setup costs, real margins, real government schemes, and an honest answer to "kya yeh flop bhi ho sakta hai?"

That's KidharMilega. Not a report. Not a PDF. A page that reads like advice from someone who's been there.

The name comes from the first question everyone asks: *kidhar milega ye cheez?*

---

## The scale problem: 787 districts, one person, one API key

India has 787 ODOP districts. Researching even 50 manually would take months.

I had Python, an Anthropic API key, and a clear picture of what someone asking "kaunsa business karoon?" actually needed to know. Three scripts. Each one feeds the next.

```
find_urls.py  →  enrich.py  →  build.py  →  GitHub Pages
```

Here's how each one actually works — including the parts that broke badly before they worked.

---

## Script 1: Hunt every source that exists

Before you can research a district, you need to know *where its data lives*.

The first script — `find_urls.py` — runs three layers of source discovery and saves everything into a single CSV: `state, district, url, status, youtube_ids, pdf_urls, google_urls`.

**Layer 1 — Verified ODOP URLs**

I manually verified 71 government ODOP URLs from official state portals and hardcoded them into the script. These are protected — no automated run can overwrite them. For the remaining 716 districts, the script probes URL patterns: `{district}.{state-code}.gov.in/one-district-one-product/`.

Result across 787 districts: **166 MATCH** (direct ODOP pages), **480 BASE** (only homepage reachable), **141 FAILED** (nothing found).

**Layer 2 — DuckDuckGo research URLs**

For every district, the script searches for high-quality business research pages that aren't on government portals — PIB press releases, IBEF sector reports, articles on trade publications, case studies from `odopup.in`.

Results are ranked: priority domains (PIB, IBEF, Ministry sites) float up, noise domains (IndiaMART, travel sites, social media) are filtered out. Up to 5 URLs per district go into the `google_urls` column.

This layer exists because a 2022 PIB press release about Moradabad brass exports regularly has better production numbers than the official district portal.

**Layer 3 — YouTube video IDs**

The YouTube Data API searches for relevant videos for every district — queries like `{product} {district} business manufacturing` and `ODOP {product} {district} India`. Up to 5 video IDs per district go into `youtube_ids`. They don't get watched here. They get transcribed later — in the next script — when everything else fails.

This is not a fallback of last resort. Local entrepreneurs and MSME cluster associations post detailed Hindi videos explaining how their industry actually works — real machine costs, real buyer contacts, how government schemes pan out on the ground. The official website often has none of this.

---

## Script 2: Research every district — but trust nothing until verified

This is where the machine breaks if you're not careful.

The naive approach: scrape the govt page, feed it to AI, done. The problem is that approach fails *silently* for most districts. The page returns HTTP 200 but the content is a loading spinner. The scrape throws an exception and the AI gets an empty dict and hallucinates everything. The output looks great. The data is fabricated.

I discovered this the hard way: 785 out of 787 districts had AI-generated content in the cache — but `scraped_facts.json` only had 2 entries. Meaning 785 district pages had been generated with zero real sourcing. The AI was inventing production numbers, export figures, and success stories from nothing.

That's not useful. That's dangerous. Someone reads that page and makes a real financial decision.

The fix was a **4-layer fallback chain** plus a cache staleness detector:

```
P1 → Official govt ODOP page
      ↓ (empty or broken)
P2 → Google/DuckDuckGo research URLs (already in the CSV from Script 1)
      ↓ (still nothing)
P3 → MoFPI / PMFME PDF handbooks (searched live)
      ↓ (still nothing)
P4 → YouTube video transcripts (IDs from the CSV, captions fetched live)
```

Each layer has a hard trigger condition: if the previous layer returned empty content, or the page_quality check returned `empty` or `partial`, the next layer runs. The script prints exactly what happened per district:

```
[gov:empty] [g?] [g?] [g:partial] ✓ 12 fields updated
```

Govt page was empty. Tried 2 Google URLs — no data. Third Google URL returned partial data. Generated content using those facts.

**The source quality problem is solved like this:**

Every cache entry now stores `_scraped_quality` — what quality of facts were used to generate it. A normal run checks: *does this district have real scraped facts now, but a cache entry that was generated before those facts existed?* If yes, it regenerates. If scraping still returns nothing, the existing cache entry is kept untouched. The machine never overwrites real data with hallucinated data.

---

## What "real facts" looks like vs what hallucination looks like

Claude Haiku runs **twice** per district.

**Call 1 (extraction):** Reads the raw scraped content, returns only what's explicitly stated. Artisan count, production scale, cluster names, export markets, scheme names. Empty string for anything not mentioned. This is the grounding layer — no inference, no elaboration.

**Call 2 (generation):** Takes those facts as verified context and generates all 60+ content fields with the "Startup Wale Bhaia" lens applied.

The generation prompt has one central instruction: *write like an experienced founder sending a WhatsApp message to a friend who just asked "kaunsa business karoon" — not like a government report.*

There's an explicit banned words list in the prompt: vibrant, tapestry, testament, burgeoning, bustling, brimming, showcase, leverage, elevate, foster, beacon, nestled, thriving, rich heritage. Any of those appearing in output is flagged as a quality warning.

What the output looks like when it's working:

- **`alert_stat`** for Bikaner: *"Bikaner accounts for 45% of India's namkeen exports — ₹850 Cr annual trade volume, 2000+ registered units, 400 tonnes produced daily."* Source: govt ODOP page.
- **`alert_stat`** for Tiruppur: *"Tiruppur produces 400+ million hosiery units annually with 85% export demand — a single 500-unit/day unit can gross ₹2.5–3.5 Cr/year at export prices."* Source: scraped from trade publication via DuckDuckGo.
- **`step_1_learn`** for Lucknow Chikankari: visit the Chowk area in Old Lucknow, talk to artisans directly, register on Udyam (free). No money required in Step 1 — this is enforced in the prompt.
- **`faq_6`**: *"Agar flop hua toh?"* — an honest answer about what your exit options look like, not reassurance.

---

## What broke, and how

**1. JSON truncation.** Claude was returning valid JSON for 40 fields then stopping mid-string on field 41. `max_tokens=4096` was too low for 60+ field output. The session looked clean. The data was silently truncated. Fix: 8192 tokens + a JSON extractor that finds the outermost `{` and `}` rather than trusting the full response string.

**2. Fallback chain not triggering.** The P2 chain was supposed to kick in when the page returned empty. But when `scrape_facts()` threw a network exception, the facts dict came back as `{}` — an empty Python dict. `{}.get("page_quality")` returns `None`, not `"empty"`. The condition `if page_quality == "empty"` missed it entirely. Fix: `not facts or facts.get("page_quality") in ("empty", "", None)`.

**3. Good URLs being overwritten by bad ones.** The CSV had some districts mapped to `.nic.in` homepages — old NIC-hosted government sites with no ODOP data. When the script loaded the CSV first, then the hardcoded verified URLs, the CSV was winning. Fix: load CSV first, then `urls.update(GOVT_ODOP_URLS)` — hardcoded entries always overwrite.

**4. DuckDuckGo search returning zero results.** `googlesearch-python` — the library originally powering Layer 2 — had stopped working. Google was blocking its requests silently. Every search returned an empty list with no error. Replaced entirely with `ddgs` (DuckDuckGo search library). Works without API key, handles rate limiting internally.

**5. District names with parentheticals breaking URL slugs.** "Anantapuram (Anantapur)" was being slugified to `anantapuramanantapur`, which matches no real URL. Fix: `clean_for_domain()` strips everything in parentheses before slug generation — `"Anantapuram (Anantapur)"` → `"Anantapuram"` → `anantapuram`. Matched immediately.

**6. Silent hallucination at scale.** The biggest one. 785 districts enriched without any real data. Discovered by auditing `scraped_facts.json` — only 2 entries. Fix: added `_scraped_quality` to every cache entry, added `key not in scraped_facts` to the `to_process` trigger, and a `_stale_cache()` detector that catches entries generated without real facts even after scraping is done.

---

## What I actually learned

**Government data is published, not accessible.** Every state has the ODOP data — the scheme mandated it. But "published" means a PDF buried on `mofpi.gov.in`, or an HTML page that renders only in Internet Explorer on a specific intranet. The 4-layer fallback chain exists entirely because of this.

**India's best business information is on YouTube.** Seriously. A local entrepreneur in Moradabad makes a 20-minute video explaining the brass export business — real machine costs, real buyer types, which government schemes actually deliver and which are just paperwork. He has 3,000 subscribers. None of it is indexed. The YouTube transcript layer was added specifically for this.

**AI is only as good as what you feed it.** This sounds obvious. It isn't, because the failure mode is invisible — the output looks confident and well-structured whether the input was a real government report or nothing at all. The two-call architecture (extract first, then generate) exists to force a separation between "what we know" and "what we're saying."

**The hard part was never the code.** The code took weeks. Knowing which six FAQs a founder from Bhagalpur actually needs answered took a year of DMs. The pipeline is technically interesting. The question set is what makes it useful.

**Static is the right architecture for India's connectivity.** 787 HTML files on GitHub Pages. No server. No database. No JS framework. Loads in under a second on 2G in Gorakhpur. An SSR framework would have been faster to build and would add 300ms to every load. Wrong trade.

---

## Where it stands

787 districts. 3 Python scripts. ~2,400 lines of code. One CSV that is the single source of truth for where data lives.

The 166 MATCH districts — verified ODOP pages, real scraped data — are getting enriched first. Then the 480 BASE districts via Layer 2 Google research. Then the 141 FAILED districts via PDFs and YouTube transcripts.

After that, the next DM question: *"kahan milega raw material?"* and *"kaun kharidega mera product?"* Supply chain maps, vendor directories, buyer listings. The discovery problem doesn't end at the product page.

---

*If you've been sitting on "kaunsa business karoon?" — find your district. That's what this is for.*
