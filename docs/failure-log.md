# Failure Log

> The running record of "what broke, how we caught it, and how we fixed it"
> (CLAUDE.md §3.1). Failures are deliberately created or honestly captured here
> *before* fixing — the before/after pair is the portfolio artifact, not the fix
> alone. Newest phase at the bottom.

---

## Phase 1 — RAG Core

### F1 (build bug) — Groq behind Cloudflare: HTTP 403 "error 1010" from Python
- **What broke:** the extractor's first real call returned `HTTP 403: error code 1010`. Cloudflare blocks requests based on client signature; Python's default `User-Agent` (`Python-urllib/3.11`) is on the block list.
- **How caught:** a `curl` POST to the same endpoint succeeded while the Python call failed — isolating it to the client, not the key or network.
- **Fix:** send a normal `User-Agent` header (`baraat-extractor/1.0`) from the backend.
- **Lesson:** "the key works in curl" ≠ "the key works from my code." Client fingerprinting is a real, invisible failure mode when calling provider APIs.

### F2 (build bug) — Free-tier rate limit: HTTP 429 (tokens-per-minute)
- **What broke:** the full 35-doc run died after ~4 docs with `HTTP 429 ... TPM Limit 12000`. Each call resends the schema-heavy prompt (~2.4k tokens), so ~5 docs/min is the ceiling on Groq's free tier.
- **How caught:** the run crashed mid-corpus; the 429 body included `try again in 2.145s`.
- **Fix:** (1) backend parses the suggested retry time and backs off on 429; (2) runner paces calls (~11s apart); (3) runner is **resumable** — skips already-extracted docs so a crash never re-spends tokens.
- **Lesson:** provider rate limits are a guardrail problem (preview of competency #8). Backoff + pacing + resumability turn a hard failure into a slow-but-reliable run.

### F3 (deliberate failure — reliability demo) — repair + fallback loop
- **Why we had to force it:** on the real Groq run, the model did its job *well* —
  it extracted the right data and every record passed **both** Python validations
  (SHAPE/format and RULES) on the first try. That's a good outcome, but it means
  the **repair** and **fallback** safety nets *never fired* — so we had no proof
  they actually work. You can't claim a safety net works if it was never tested.
- **What we did on purpose:** we swapped in a `MockBackend` (no API key,
  deterministic — it returns scripted "model" answers instead of calling Groq) and
  **deliberately infused wrong values** into the records, specifically to see if
  the validators catch them and the recovery logic behaves. Three scripted cases:
  - **Case 1 — clean:** valid JSON → **accepted on the first try** (proves the
    happy path doesn't false-alarm).
  - **Case 2 — invalid, then repaired:** we injected two rule-breaking values —
    `rating: 7.5` (the rule caps rating at **5.0**, so 7.5 is out of range) and
    `price_unit: per_day` for a **caterer** (the rule says a caterer must be
    `per_plate`). The Python validator caught both, the loop **sent the exact
    errors back to the (mock) model asking for a fix**, the corrected record came
    back valid, and it was **accepted**. (This is the "went back and asked for the
    right answer" path.)
  - **Case 3 — invalid every time, then fallback:** we scripted a record that
    **stays wrong no matter how many times we ask**. After the capped retries (2)
    it still failed validation, so instead of guessing it **fell back** to
    `needs_human_review: true` with a note. (This is the "even after twice it's
    still wrong → flag a human" path.)
- **Result:** all three paths behaved exactly as designed
  (`src/extraction/demo_mock.py`).
- **Why it matters:** this is the competency #7 (structured-output reliability)
  artifact. The point isn't that the model failed — it's that **when a model
  fails, our system catches it, tries a bounded repair, and degrades honestly
  instead of shipping garbage.** Forcing the failure with a mock is *more*
  convincing than hoping the live model misbehaves — it's repeatable, free, and
  deterministic.

### F4 (content-correctness finding — Layer 3 vs the manifest) — over-eager red flags
- **Not a validator bug — a different layer doing its job.** The automated Python
  validator only checks SHAPE (format) and RULES (self-consistency); it
  *structurally cannot* see whether a fact is true. Content correctness is a
  separate, deliberate **Layer 3** (manual vs the manifest now; LLM-as-judge in
  Phase 4). F4 is that Layer-3 check finding something layers 1–2 can't — which is
  precisely why it's worth logging, not removing.
- **Context:** on the real Groq run (32 non-reserved docs, model `llama-3.3-70b-versatile`, 0 repairs, 0 fallbacks, ~67k tokens), records were schema-valid. Checking content against `data/vendors/_corpus_manifest.md` surfaced nuances validation can't:
  - **False positive:** `photographer_pixelpandit` → `red_flags: ["Communication was a little slow during peak season."]`, but the manifest planted **no** red flag there. The model treats mild review criticism as a due-diligence red flag.
  - **Where that phrase came from (NOT a hallucination):** the sentence is a real
    review line in the source doc (`photographer_pixelpandit.md`, in the "What
    couples say" section — one mildly negative quote among two glowing ones). Groq
    copied it verbatim; the error is **misclassification, not fabrication** — it
    promoted a minor review nitpick to a serious `red_flag`. The doc's *actual*
    planted issue is **stale pricing** (₹95,000 in 2021 vs ₹1,40,000 in 2024), not
    a red flag. So the model both invented a red flag AND that flag is a trivial
    gripe, not a genuine warning sign (billing dispute, lost footage, late
    delivery). This subtler failure — "can't tell a nitpick from a warning" — is a
    more realistic and instructive bug than pure fabrication.
  - **Defensible judgment calls:** open-ended "from ₹X and up" pricing (royal_decor pair, lakeview, petals_and_props) → `price_confidence: low`. Consistent with our rules, but worth noting the boundary.
- **Score (extraction vs manifest, Phase 1 baseline):** stale detection 5/5; GST exact-match 6/6; all 5 buried-red-flag docs surfaced their flags; **1 false-positive red flag** out of the clean-control set.
- **How this was caught (honest provenance — don't overclaim):** the finding came
  from an **assistant-run spot-check** during the session — reading the 32
  extracted records against `_corpus_manifest.md` by eye — **not** from Saimukesh
  personally doing the manual review, and **not** from a formal scored eval. The
  plan says "Layer 3 = human (Saimukesh) checks vs manifest"; in reality this F4
  was an informal assistant pass. **Still pending:** (1) Saimukesh personally
  re-doing/owning the manual comparison (same discipline as owning the golden-set
  answers), and (2) the systematic, scored Layer-3 eval (LLM-as-judge in Phase 4).
- **Status:** logged, **not yet fixed** (per §3.1). Candidate fixes for later: a red-flag severity threshold, or prompt guidance distinguishing "serious issue" from "mild review gripe." This is the textbook demonstration that **schema-valid ≠ content-correct** — only grading against ground truth catches it.

---

### F5 (retrieval eval — baseline) — recall@5 passes but exact-match quality fails

- **Stage:** baseline semantic-only retrieval, 10 golden questions, k=5.
- **The metric trap:** the first headline number was recall@5 = **1.0 (10/10)** —
  gold doc in top 5 for every question. This looked like a pass but is
  **saturated**: baseline is already at the ceiling, so recall@5 literally *cannot*
  show whether hybrid search helps. A metric that can't move is the wrong metric.
- **Fix to the eval itself:** added two stricter, rank-sensitive metrics so the
  hybrid improvement will be measurable:

  | Metric | Baseline | What it measures | Headroom? |
  |---|---|---|---|
  | recall@5 | **1.0**  | gold doc anywhere in top 5 | none (saturated) |
  | recall@1 | **0.80** | gold doc at **rank 1** | yes — Q08, Q09 fail |
  | MRR      | **0.875**| avg of 1/rank (rank-sensitive) | yes |

  The honest baseline to report and improve against is **recall@1 = 0.80,
  MRR = 0.875**, not recall@5 = 1.0.
- **Why this is misleading — the real failures are in ranking and disambiguation:**

  **Q08 — GST exact-match (gold rank: 4):**
  - Question: *"Which vendor has GST number 36AAEGP2210R1Z3?"*
  - Top-5 returned: `caterer_swadsagar, caterer_grandthali_events, decorator_royal_decor_events, venue_grand_pavilion, caterer_grandthali_caterers`
  - The correct vendor (`venue_grand_pavilion`) is rank 4, behind 3 irrelevant vendors.
  - **Root cause:** a GST string is a random alphanumeric code — it has no semantic
    "meaning" for an embedding model to latch onto. Semantic search finds it
    eventually (it's in the chunk text) but ranks it low because the question's
    words don't semantically cluster near a venue's passage.
  - **Fix:** hybrid/keyword search will exact-match the GST string and rank it 1st.

  **Q09 — near-duplicate name (gold rank: 2, impostor also in top 5):**
  - Question: *"Two decorators share Royal Decor — which is in Udaipur and what's its GST?"*
  - Top-5: `royal_decor_events, royal_decor_studio, royal_decor_studio, royal_decor_studio, royal_decor_events`
  - Both the correct vendor (Studio, Udaipur) **and** the wrong near-duplicate
    (Events, Jaipur) fill the entire top 5. A downstream LLM sees both GST numbers
    and may answer with the wrong one.

  **Q10 — near-duplicate phone (gold rank: 1, impostor also in top 5):**
  - Question: *"Two caterers share Grand Thali — what's the Delhi one's phone?"*
  - Top-5: `grandthali_caterers, grandthali_events, grandthali_caterers, grandthali_events, grandthali_caterers`
  - Same problem — both near-duplicates interleaved across all 5 slots.

- **The key insight:** `recall@5 = 1.0` does not mean the retrieval is correct for
  exact-match questions. The right document is technically *present*, but:
  1. Ranked too low (Q08) — keyword search fixes ranking.
  2. The impostor is *also* present (Q09, Q10) — disambiguation requires exact
     string matching (GST/phone/city), not meaning-based similarity.
  A downstream LLM working from these 5 chunks could easily answer with the wrong
  vendor's GST or phone number. **recall@k alone is insufficient for near-duplicate
  cases — precision and rank matter too.**

- **Q06 — a THIRD near-duplicate the top-5 view had hidden (found only via the
  stricter "other vendors in top-k" check):**
  - Question: *"What is the current per-plate price at Anokhi Rasoi?"*
  - Top-5: `anokhi_rasoi, annapurna_rasoi, anokhi_rasoi, anokhi_rasoi, anokhi_rasoi`
  - Gold is rank 1 (good), but `caterer_annapurna_rasoi` also appears — "**Anokhi**
    Rasoi" vs "**Annapurna** Rasoi" both contain "Rasoi" and sound alike. recall@5
    and recall@1 both looked fine here; only inspecting *which other vendors* share
    the top-k surfaced this latent confusability. Not a failure yet (gold is #1),
    but a fragility worth tracking.

- **Also noted:** multiple chunks from the same document appear in the top 5
  (Q09/Q10 show the same vendor_id 3× in 5 slots). Future improvement: deduplicate
  by vendor_id before returning top-k, so the 5 slots represent 5 distinct vendors.

- **Motivates:** hybrid search (Stage 2) — keyword matching will exact-match GST/
  phone strings and give city-based disambiguation weight. Expected deltas to
  report: **recall@1 0.80 → ~1.0** (Q08 rank 4→1, Q09 rank 2→1) and a matching MRR
  rise; recall@5 stays 1.0 (already saturated) and is kept only as a floor check.

---

### F6 (retrieval eval — hybrid, Stage 2) — keyword fixes GST, but a shared word defeats near-dup disambiguation

- **What we built:** hybrid retrieval = the existing semantic (dense) search + a
  from-scratch BM25 keyword search, fused with **Reciprocal Rank Fusion (RRF)**
  (`src/retrieval/keyword_search.py`, `src/retrieval/hybrid.py`). RRF over raw score
  addition because cosine (0–1) and BM25 (unbounded) live on different scales;
  fusing by *rank* is scale-free.
- **Measured delta (same 10 golden questions):**

  | Metric | Baseline | Hybrid | Δ |
  |---|---|---|---|
  | recall@5 | 1.0 | 1.0 | — (saturated floor) |
  | **recall@1** | **0.80** | **0.90** | **+0.10** |
  | **MRR** | **0.875** | **0.95** | **+0.075** |

- **Win — Q08 (GST lookup): rank 4 → rank 1.** The tokenizer keeps
  `36AAEGP2210R1Z3` as one token; BM25 exact-matches it and RRF lifts it to #1.
  This is the case pure semantic search *structurally* could not do (a random code
  has no meaning to embed). Clean demonstration of *why* hybrid exists.
- **Partial win — Q10 (Grand Thali near-dup):** the wrong Lucknow twin dropped from
  interleaved (slots 2 & 4 at baseline) to a single slot at rank 4; gold now fills
  4 of the top 5. Less impostor contamination, though not zero.
- **Survived failure — Q09 (Royal Decor near-dup): still rank 2.** This is the
  interesting one. The query asks for "the one **based in** Udaipur." But the word
  "Udaipur" appears in **both** docs:
  - `decorator_royal_decor_studio.md` — its real location (4 mentions).
  - `decorator_royal_decor_events.md` — inside its disambiguation note: *"often
    mistaken for Royal Decor Studio in **Udaipur**."*
  So keyword matching on "Udaipur" **can't separate them** — both legitimately
  contain the token. BM25 sees words, not roles; it cannot distinguish "located in
  Udaipur" from "cross-references the Udaipur firm." The Jaipur impostor stays at
  rank 1.
- **The lesson (and what it motivates):** hybrid fixes *exact-string* retrieval
  (Q08) but not *relational/semantic disambiguation* (Q09). When the discriminating
  word is shared across both candidates, neither meaning-similarity nor keyword
  overlap can rank them correctly. This is the textbook motivation for **Stage 3 —
  reranking**: a cross-encoder scores the query and each chunk *together* and can
  learn that "based in Udaipur" is a location claim, not a mention. Expected next
  delta: Q09 rank 2 → 1, recall@1 0.90 → 1.0.
- **Also observed:** duplicate chunks from the same vendor still fill multiple top-5
  slots (Q10 shows gold 4×). Vendor-level dedup before returning top-k remains a
  pending improvement (would also free slots to reveal/relegate impostors).

---

### F7 (retrieval eval — reranking, Stage 3) — the expensive tool that DIDN'T help

**This is the most instructive result of the retrieval arc, precisely because it
went against the expectation.** We predicted reranking would flip Q09 (rank 2 → 1)
and lift recall@1 to 1.0. We measured. It did not.

- **What we built:** a cross-encoder reranker (`src/retrieval/reranker.py`,
  `Xenova/ms-marco-MiniLM-L-6-v2`, local, ~80MB). It takes hybrid's top-N=20
  candidates and re-scores each (query, chunk) pair *together*. Includes the
  graceful-degradation guardrail (Knob 3): on any cross-encoder failure it falls
  back to the hybrid ranking instead of crashing.
- **Measured result (same 10 golden questions):**

  | Stage | recall@1 | MRR | latency/query (CPU) |
  |---|---|---|---|
  | baseline (semantic) | 0.80 | 0.875 | 5.7 ms |
  | hybrid (+ keyword) | 0.90 | 0.95 | 6.5 ms |
  | **rerank (+ cross-encoder)** | **0.90** | **0.95** | **223.7 ms** |

  Reranking = **no recall@1 or MRR improvement**, at **~34× the latency** of hybrid.
- **Why Q09 survived even the cross-encoder — the key insight:** the reranker ranked
  the *wrong* vendor (Royal Decor & Events, Jaipur) #1. That impostor doc contains a
  disambiguation note: *"often mistaken for Royal Decor Studio **in Udaipur**."* The
  query asks for "the one based **in Udaipur**." The note **literally contains the
  query phrase**, so the cross-encoder — which is *supposed* to be the deep reader —
  scored the impostor highest. The corpus's own realistic cross-reference is an
  **adversarial lexical trap** that defeats semantic AND keyword AND cross-encoder
  ranking. No ranker can win here, because the discriminating text points the *wrong*
  way.
- **The PM conclusion (competency #15 — when a technique is the WRONG tool):** on
  this corpus, **reranking is not worth shipping** — 34× the latency for zero measured
  accuracy gain. The honest recommendation is to **stop the retrieval arc at hybrid**
  and solve the residual near-duplicate case a different way:
  - **Metadata filtering** — filter candidates by the structured `location` field
    ("Udaipur") from the **extracted records** (Track B). *This is where extraction
    and retrieval finally connect:* the JSON we built for tool-math also disambiguates
    near-duplicates that no text ranker can. A `city == "Udaipur"` filter removes the
    Jaipur impostor entirely — something reranking cannot do.
- **Was building it wasted?** No — the *negative result is the artifact*. "I built the
  fancy stage, measured it, found +0% for +34× cost, diagnosed why, and chose not to
  ship it" is a stronger portfolio story than a reranker that happened to help. It
  demonstrates measure-don't-assume, cost/latency judgment, and root-cause diagnosis.
- **Kept in the repo** as a working, swappable stage (`--retriever rerank`) so the
  negative result is reproducible, not just asserted.

---

## Phase 2 — Tools & Agent Orchestration

### F8 (deliberate failures — agent guardrails) — runaway loop & budget exhaustion caught

The agent is an explicit loop we own (`src/agent/orchestrator.py`), driven by a
pluggable policy. As in Phase 1 (MockBackend proving the repair/fallback loop), we
used a **ScriptedPolicy** to make the agent misbehave on purpose and showed each
guardrail catching it (`python -m src.agent.demo_agent`). Budgets: loop=6, tool=5.

| Scenario | What the agent did | Guardrail | Outcome |
|---|---|---|---|
| A. Good path | budget → contract → finish | stop condition | `finished`, 2 calls, clean |
| B. Runaway loop | called `vendor_comparator` with identical args twice | repeat detection | `no_progress`, stopped at call 1 |
| C. Over-calling | 6 distinct tool calls, never finishing | tool budget (5) | `tool_budget`, degraded partial answer |
| D. Never finishing | never emits finish (tool budget raised) | loop budget (4) | `loop_budget`, degraded partial answer |

- **The artifact:** in B, C, and D the agent would, unguarded, loop forever or
  over-spend. Instead each returns a **degraded but honest partial answer** ("stopped:
  … Partial results: …") — never a crash, never a hang, never silence.
- **Why the pluggable policy matters:** forcing the failure with a scripted policy is
  repeatable and free (same reasoning as Phase 1's mock). A real LLM policy drops into
  the same orchestrator unchanged — the guardrails don't care where the Action came
  from.
- **Also demonstrated:** scenario B shows `vendor_comparator` correctly pulling
  **extracted records** (Track B) — price/rating/red-flag count — and recommending the
  better caterer. This is the first place Phase 1 extraction is *used*, not just built.
- **Two layers of guarding now exist:** tool contracts guard each single call
  (validate in/out); guardrails guard the whole sequence (budgets, stop, degrade).

### F9 (real agent — self-correcting bad tool arguments) — the repair loop, live

Wired a real LLM policy (`src/agent/llm_policy.py`, Groq/Llama-3.3-70b) into the same
orchestrator + guardrails, so the agent can be asked natural-language questions
(`python -m src.agent.ask "..."`). The scripted brain was swapped for a live one; the
guardrails did not change.

- **The artifact (asked: "split my 15L, ~40% venue, 30% catering, rest evenly"):**
  1. The model first called `budget_allocator` with **wrong category names**
     (`catering`, `makeup`) — a real, unprompted LLM mistake.
  2. The **tool contract caught it** at input validation: *"unknown category
     'catering' (allowed: … caterer …)"*.
  3. The error was fed back; the model **corrected the names** (`caterer`,
     `makeup_artist`) and retried → success → finished with a clean answer.
- **Why it matters:** this is the tool-layer repair loop (competency #7) happening
  for real, not mocked. The value of a *strict* tool contract is exactly this: a fuzzy
  model's mistake becomes a caught, self-correctable error instead of silent garbage
  (e.g. a budget silently dropped on the floor for an unknown category).
- **Other live checks:** "compare Grand Thali Caterers vs Events" → agent mapped both
  names to the correct `vendor_id` stems and pulled real extracted data (recommended
  the 4.7-rated one). "Is 80% upfront + 20% on event day risky?" → agent built the
  instalments and the validator flagged high-upfront + majority-before-milestone.
- **Design point:** the LLMPolicy is a drop-in for ScriptedPolicy — the orchestrator,
  guardrails, and tools are identical. The scripted policy proves guardrails
  deterministically (F8); the LLM policy shows the real agent working (F9).
