# Learning Notes — Phase 1 & the Schema Concept

> **What this file is:** my own plain-language study notes for Baraat — written
> so I (Saimukesh) can re-read and *explain* these ideas in an interview, not
> just nod along. Not code, not a spec. A "teach it back to myself" doc.
> Updated as we go.

---

## 0. The big picture (where Phase 1 sits)

Baraat *looks* like a wedding-vendor research agent. It's really a **portfolio**
that proves 16 AI-product-management skills. The app is the vehicle; the proof
is in the tradeoffs, the deliberate failures I catch and document, and the
numbers I can show.

The build is in **5 phases**, done in order on purpose:

1. **Phase 1 — RAG Core** ← *we are here* (search + structured extraction)
2. **Phase 2 — Tools & Agent** (budget calc, comparison, guardrails)
3. **Phase 3 — Safety** (prompt-injection attack, then defense)
4. **Phase 4 — Evals, Observability, Cost, Routing**
5. **Phase 5 — CI gate + final packaging**

---

## 1. Phase 1, in detail

### 1a. The 35 documents (the "world")
- 35 synthetic vendor docs: 7 each across photographers, caterers, decorators,
  venues, makeup artists.
- Written as **prose** (listing + reviews), not neat tables — so the system has
  real reading/extraction work to do.
- All fictional (fake names, fake phones, fake format-shaped GST numbers).

### 1b. Messiness planted ON PURPOSE
A clean corpus would make the evals meaningless theatre. So we planted realistic
problems, each one designed to break the system in a *named, well-known* way:

| Trait | Count | What it tests | Example |
|---|---|---|---|
| **Stale / conflicting price** | 5 | freshness handling | Anokhi: ₹1,150 (2022) vs ₹1,450 (2023) — which is current? |
| **Buried red flag** | 5 | "lost in the middle" | a complaint hidden in a late paragraph of a positive doc |
| **Near-duplicate names + exact-match** | 7 | why we need hybrid search | "Royal Decor Studio" vs "Royal Decor & Events"; exact GST/phone |
| **Reserved for Phase 3** | 3 | (untouched now) | clean docs that become injection-attack targets later |

Plus **16 clean control docs** — these matter too: a good system must NOT
invent red flags or staleness where none exist.

**Ground-truth answer key:** `data/vendors/_corpus_manifest.md` records exactly
what we planted in each doc. It is kept OUT of the search index (files starting
with `_` are skipped) — otherwise the system could read its own answer key and
every test would pass for the wrong reason.

### 1c. The golden set (the honest exam)
- A set of **questions + expected answers** — an exam with an answer key written
  BEFORE the system takes the test.
- **I (Saimukesh) write the expected answers myself**, before seeing the
  system's output. Claude drafts candidate questions (it knows where the traps
  are), but I own the answers — that's what keeps the eval honest. An eval you
  write *after* seeing the output isn't an eval, it's a rationalization.
- ~8–10 questions in Phase 1, growing to 30–40 by Phase 4.

> **Golden set ≠ corpus manifest — don't confuse them (I did, once):**
> - **Corpus manifest** = answer key of *what's in each document* (true price,
>   planted red flag, GST, per doc). Used to grade **extraction** ("did the JSON
>   record match the doc?").
> - **Golden set** = *user questions + expected answers*. Used to grade
>   **retrieval / answering** ("did the system answer the user's question?").
> - Two answer keys, two different evals. The golden set's answers are often
>   *authored from* the manifest, but they are distinct artifacts. For checking
>   **extraction content-correctness, the reference is the manifest**, not the
>   golden set.

### 1d. The 3-stage retrieval improvement loop
We run the **same** golden questions at every stage, so the only thing changing
is the search method — that's what makes the before/after numbers trustworthy.

1. **Baseline = semantic search ONLY** (meaning-based). Run questions, measure,
   and **log the real failures** (esp. exact-match GST and buried red flags) to
   `docs/failure-log.md` *before* fixing anything. The failure is the artifact.
2. **+ Hybrid (semantic + keyword).** Re-run same questions, report the delta.
   Expect exact-match / near-duplicate questions to jump.
3. **+ Reranking** (a smarter second pass that re-scores top candidates).
   Re-run, report the delta. Expect buried red flags / precision to improve.

> ⚠️ Common mix-up I had: **baseline is semantic-only; keyword is ADDED in the
> hybrid stage.** Not the other way around.

**Two scoring words:**
- **Recall@5** = of the chunks that SHOULD have been found, how many showed up
  in the top 5? ("did we find the right info?")
- **Precision** = of what we returned, how much was actually relevant? ("did we
  return junk alongside it?")

---

## 2. The schema concept (the part I wanted notes on)

### 2a. What it is, in one line
A **schema** is a set of rules — written as a JSON shape — that defines the
**standardized form** every messy vendor doc must be turned into. "Structured
output" = the act of reading a messy doc and filling in that form.

**Analogy:** the 35 docs are like 35 handwritten letters. The schema is a form
with labeled boxes (Name, City, Price min/max, Phone, Red flags, Rating).
Filling the form from the letter = structured extraction. Result: every vendor
ends up as the *same neat shape*, like a spreadsheet row.

### 2b. Who fills it in?
- **I (the PM/builder)** write the schema + the extraction instructions.
- **Claude (the LLM)** does the actual reading-and-filling, one doc at a time.
- **My code** then VALIDATES Claude's filled form against the rules.
- If Claude got it wrong → ask again (**repair**); if it keeps failing →
  flag **`needs_human_review`** instead of silently guessing.

Example: Claude reads Anokhi, sees two conflicting prices, and (because we told
it how) marks `price_confidence: "stale"` rather than confidently picking the
wrong number.

### 2c. WHY we build it — and the key correction
**The schema is NOT for RAG / chunking.** This was my main mix-up. Extraction
and retrieval are **two independent siblings**, not a pipeline where one feeds
the other.

> **RAG/retrieval reads the RAW prose — it never needs the JSON.**
> **The JSON exists for a different job: math and comparison by the tools.**

**Résumé analogy:**
- RAG = a **search engine** over the full résumé text ("who knows Python?").
  Works on the words directly. Doesn't need any spreadsheet.
- Schema = typing each résumé into an **HR spreadsheet** so you can sort,
  filter, compute ("average salary expected", "who's under budget?").
- Both built from the same résumés, but the spreadsheet is for *calculations*,
  not to help the search engine.

**Which track answers which question (Baraat):**

| Question | Track | Why |
|---|---|---|
| "Does Anokhi have complaints?" | **RAG / retrieval** | find & read the buried text |
| "Is Anokhi within my ₹1,200/plate budget?" | **Schema / JSON** | compare numbers (math) |
| "Compare these 3 caterers on price & rating" | **Schema / JSON** | line up clean fields |
| "Summarize Anokhi's reviews" | **RAG / retrieval** | needs the actual review text |

Rule of thumb: **retrieval = "find and read"; schema = "compare and compute."**
You can't run `if price <= budget` on a paragraph of prose — you need the number
in a labeled box.

*(Footnote / advanced: structured fields CAN later also help retrieval via
"metadata filtering" — e.g. "only search caterers in Jaipur". Nice-to-have, not
the reason we build the schema, and not where we start.)*

### 2d. The three reasons we want a schema (interview-ready)
1. **A program can't act on prose — only on fields.** Tools need to do math &
   comparison; you can compare two `price_range_inr.max` numbers, not two
   paragraphs. → makes data machine-usable.
2. **It forces the model to commit to specifics — and lets us catch it when
   wrong.** A filled field can be validated (rating 0–5? GST 15 chars?). Prose
   has nothing to validate. → competency #7 structured-output reliability.
3. **Defining the form before building the machine is the discipline.** Spec
   the output with examples & edge cases first → "done" is unambiguous.
   → competency #3 spec-by-example.

### 2e. Why this matters for a PM (the transferable lesson)
This isn't just a Baraat trick — it's a core AI-PM skill:

- **PMs constantly receive piles of unstructured data** — support tickets, user
  interviews, reviews, sales call notes, survey free-text, contracts.
- The valuable move is to **design a schema** (decide what fields actually
  matter for the decision) and then **use an LLM like Claude to extract** every
  messy item into that clean shape — at scale, in minutes instead of weeks.
- Then you can **count, compare, sort, and decide** on real structure instead
  of vibes ("37% of churned users mention 'pricing' as a red flag").
- The PM skill is twofold: (1) **knowing what to put in the schema** (which
  fields drive the decision; what to ignore), and (2) **handling unreliability**
  — validation, repair, and an honest "needs human review" fallback instead of
  trusting the model blindly.

> **One-liner:** "Turning messy text into a validated, decision-ready structure
> — and handling the model's mistakes gracefully — is one of the most repeatable
> ways an AI PM creates leverage."

### 2f. What happens when extraction goes wrong (the safety net)
```
Claude extracts JSON
   → validate against schema rules
       → valid?  accept
       → invalid (e.g. rating 7.5, bad category, text in a number box)
            → REPAIR: show the model its error, ask again (up to N tries)
                 → still invalid?
                     → FALLBACK: needs_human_review = true + note why
```
Principle (CLAUDE.md §3.3): a malformed extraction is a **logged failure event,
not a silent retry.** We'll deliberately trigger one later and log before/after.

---

## 2g. WHEN do we test what — "detect & record now → use & answer later"

A confusion I had: *"Why check stale-price / GST detection now? Doesn't that
belong at the user-query level, after RAG is built?"* Answer: the same behaviour
gets checked at **two different levels, for two different reasons** — and the
check I did after extraction was NOT the user-query test.

**The clean reframe:**
- **Extraction's job (now):** *detect* that a price is stale and *record* it in
  the field `price_confidence: "stale"`; *copy* the GST exactly into
  `gst_number`. So "detection" actually happens at **extraction time**.
- **The query layer's job (later):** when the user asks "is the price current?",
  *use* that recorded field to *answer* them.

So: **detect & record now → use & answer later.**

**Two test levels, not redundant:**

| | Component check (now) | End-to-end check (later) |
|---|---|---|
| Question | "Did extraction *record* the fact right?" | "Does the system *answer* the user right?" |
| Tests | extraction (Track B) | retrieval + answer (whole system) |
| Graded vs | corpus manifest | golden set |
| When | right after building extraction | after RAG is built |

**Why check the component now instead of waiting:**
1. **Garbage in → garbage out.** Records feed everything downstream. If a price
   was wrongly recorded `high`, no amount of good retrieval saves the answer.
   Verify the input layer before building on it.
2. **Fault isolation.** If a user-level answer is wrong later, was it extraction,
   retrieval, or generation? Having checked extraction independently lets me
   *rule it out* and localize the bug.

**Analogy:** building a car. Extraction check = engine on a **test bench** (does
it make power?). Query-level eval = **road test with a driver** (golden set).
You don't skip the bench test because the road test is the "real" one — and if
the road test fails, the bench result tells you whether to blame the engine.

> Caveat: what I ran post-extraction was a quick **sanity spot-check** vs the
> manifest, not the formal scored eval. The systematic Layer-3 evals come with
> the golden set later.

---

## 2h. How the extraction actually ran (script vs agent + reading the report)

**It was a plain Python script, NOT an agent.** I ran one command
(`python3 -m src.extraction.run_extraction`), which executed a fixed pipeline:
for each doc → read → call the model (Groq) once → parse → validate → repair if
needed → save. The model did ONE narrow job ("fill this JSON"); it did not decide
the steps — the code did.

**Script vs agent — the distinction (classic interview question):**

| | Script / pipeline (this) | Agent (Phase 2) |
|---|---|---|
| Who decides the steps? | the programmer hardcodes them | the LLM decides, in a loop |
| Control flow | fixed, predictable | dynamic (picks tools, decides when to stop) |
| Guardrails (loop/tool budgets)? | minimal (a capped retry) | essential — the whole point |
| Example | "read → extract → validate → save" | "should I call the budget tool? then compare? am I done?" |

That's why `src/agent/` is empty right now — agents are Phase 2. The repair loop
is NOT an agent: it's a fixed, capped retry, not the LLM choosing its own actions.

**Reading the run report (two gotchas I hit):**
- **`needs_human_review: False` is GOOD.** False = extraction succeeded, no human
  needed. True = it failed and is flagged for a human. All-False = all 32 records
  clean. The only place True appears is the deliberate mock-failure demo.
- **`cached` rows are still real Groq output** — they were extracted in an earlier
  run and reused (the resumable runner skips already-saved docs to avoid
  re-spending tokens). Coverage was 32/32 via Groq; nothing skipped due to limits.

**Rate-limit terms (Groq free tier = 12k tokens/min):**
- **backoff** = on a 429, wait the time the API suggests, then retry.
- **pacing** = wait ~11s between docs to stay under the per-minute limit.
- **resumable runner** = save each record as it finishes; re-running continues
  from where it stopped. (Slower, but never loses or re-pays for work.)

---

## 3. The proposed schema (status: awaiting my sign-off)

Base from PRD §4, plus 4 proposed additions (each justified, not decoration):

| Field | Meaning | Note |
|---|---|---|
| vendor_id | unique id (filename slug) | |
| name | business name | |
| category | one of the 5 types | enum — must match exactly |
| location | city | |
| price_range_inr {min,max} | price as numbers | min ≤ max |
| **price_unit** | per_plate / per_day / per_event / package | **ADD #1** — caterers are per-plate, venues per-day; comparing without a unit is meaningless |
| price_last_verified | date or null | |
| price_confidence | high / low / stale | |
| contact {phone,email} | contact | |
| gst_number | 15-char or null | disambiguates near-duplicates |
| rating | 0.0–5.0 | |
| review_count | integer ≥ 0 | |
| red_flags | array of strings | empty [] if none, never missing |
| **source_file** | which doc it came from | **ADD #2** — attribution (competency #2) |
| **needs_human_review** | true/false | **ADD #3** — the fallback flag (PRD asks for this state) |
| **extraction_notes** | string or null | **ADD #4** — human-readable "why flagged" |

**Open sign-off questions (to decide before writing the spec file):**
1. Keep all 4 additions? (rec: yes)
2. price_confidence = `high|low|stale` or simplify to `high|stale`? (rec: keep 3)
3. Anything to add/cut?

---

## 4. Mini-glossary
- **RAG** (Retrieval-Augmented Generation): answer using retrieved text, not the
  model's memory.
- **Chunking**: cutting long docs into smaller passages for precise retrieval.
- **Embedding**: turning text into a list of numbers (a "vector") that captures
  meaning; similar meanings sit close together on a "map of meaning."
- **Vector store**: the database of those vectors you can search by closeness.
- **Semantic search**: search by meaning (the map). Bad at exact strings/numbers.
- **Keyword search**: exact word/character matching. Good at GST numbers, names.
- **Hybrid search**: semantic + keyword combined.
- **Reranking**: a smarter second pass that re-scores the top candidates.
- **Schema**: the rules/shape (JSON) for the structured output.
- **Structured extraction**: filling the schema from messy prose (Claude does it).
- **Validation**: checking the filled form against the schema rules.
- **Repair loop**: showing the model its error and asking it to fix the output.
- **Recall / Precision**: did we find the right info / was what we returned
  actually relevant.
