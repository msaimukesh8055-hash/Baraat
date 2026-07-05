# Phase 1 Results — RAG Core (with real numbers)

> The single "read this in 2 minutes" summary of everything Phase 1 proved. Written
> for a non-technical reader first. Deeper detail lives in `docs/failure-log.md`
> (the F-numbers), `docs/learning-notes/` (plain-language teaching), and the
> decision records. Every number here is measured, not estimated.

---

## 1. What Phase 1 was about

Baraat researches wedding vendors and flags problems (stale prices, hidden
complaints, look-alike firms). Phase 1 built the **two foundations** that everything
else sits on:

- **Track A — Retrieval (RAG):** given a question, *find and read* the right passage.
- **Track B — Extraction:** turn each messy vendor document into a *clean, validated
  structured record* for later math and comparison.

Both were built on a **corpus we deliberately booby-trapped** so the system could be
tested against known problems instead of a tidy, meaningless demo.

---

## 2. The test data (built to fail on purpose)

- **35 synthetic vendor docs** (7 each: photographers, caterers, decorators, venues,
  makeup artists). All fictional. 32 active + 3 reserved for Phase 3.
- **Planted traps**, each testing a known failure mode:

  | Trap | Count | Tests |
  |---|---|---|
  | Stale / conflicting price | 5 | freshness handling |
  | Buried red flag (complaint hidden late in a positive doc) | 5 | "lost in the middle" |
  | Near-duplicate names + exact-match hooks (GST/phone) | 7 | why hybrid search is needed |
  | Clean controls (no trap) | 16 | must NOT invent problems |

- **A private answer key** (`data/vendors/_corpus_manifest.md`) records exactly what
  was planted, and is **kept out of the search index** so the system can't cheat.

---

## 3. Track B — Extraction results

We ran all 32 active docs through the extraction pipeline (schema → validate →
repair → fallback), using an open model on Groq (`llama-3.3-70b-versatile`).

**Reliability (the shape / structure of the output):**

| Metric | Result |
|---|---|
| Docs processed | 32 |
| Passed validation first try | 32 (29 fresh + 3 cached) |
| Needed a repair | 0 |
| Fell back to "needs human review" | 0 |
| Total tokens | ~67,400 |

Every record was schema-valid on the first try. Because the safety nets (repair,
fallback) never fired on real data, we **proved them deliberately with a mock**
(failure-log **F3**): a valid case was accepted, an invalid one was repaired, and an
always-invalid one fell back to `needs_human_review` — all three paths work.

**Content correctness (are the facts right — checked by hand vs the manifest):**

| Check | Score |
|---|---|
| Stale prices correctly flagged | 5 / 5 |
| GST numbers copied exactly | 6 / 6 |
| Buried red flags surfaced | 5 / 5 |
| False-positive red flags (clean docs) | 1 (Pixel Pandit) |

The one miss (**F4**): the model turned a mild review gripe ("communication was a
little slow") into a due-diligence red flag the manifest never planted. The record
was perfectly *well-formed* — only comparing against ground truth caught it. This is
the textbook lesson: **schema-valid ≠ content-correct.**

---

## 4. Track A — Retrieval results (the headline)

We wrote a **golden set of 10 questions** (2 controls, 3 buried red flags, 2 stale,
3 exact-match) with answers fixed in advance, and measured retrieval at three stages.

**Important eval lesson first:** our initial metric, **recall@5** (was the right doc
anywhere in the top 5?), read **1.0 at baseline** — a perfect score that was actually
**useless**, because it was already maxed out and couldn't show any improvement. We
switched to stricter, rank-sensitive metrics: **recall@1** (is the right doc *first*?)
and **MRR**. (failure-log **F5**.)

**The three-stage arc:**

| Stage | recall@1 | MRR | Latency / query | Decision |
|---|---|---|---|---|
| **Baseline** (semantic only) | 0.80 | 0.875 | 5.7 ms | starting point |
| **Hybrid** (semantic + keyword) | **0.90** | **0.95** | 6.5 ms | **SHIP** — big gain, ~free |
| **Rerank** (+ cross-encoder) | 0.90 | 0.95 | **223.7 ms** | **DON'T ship** — 0 gain, 34× cost |

*(recall@5 stayed 1.0 throughout — kept only as a floor check.)*

**What each stage taught:**

- **Baseline → Hybrid (F6):** semantic search is blind to exact strings. It buried
  the GST-lookup answer at rank 4 (a code has no "meaning" to match). Adding keyword
  (BM25) search fixed it — GST question jumped to **rank 1**. Cost: +0.8 ms. This is
  a clear, cheap win, so we ship it.

- **Hybrid → Rerank (F7) — the most instructive result:** we *expected* the
  expensive cross-encoder to fix the last hard case (Q09, two "Royal Decor" firms).
  We measured. **It made no difference** — and cost **34× more latency.** The reason
  is sharp: the wrong firm's document literally says *"often mistaken for Royal Decor
  Studio **in Udaipur**"* — it contains the exact phrase the question asks about, so
  it fools semantic, keyword, *and* cross-encoder ranking alike. **No text ranker can
  win here.** We chose **not to ship reranking**, and identified the real fix:
  **metadata filtering** on the extracted `location` field (Track B) — filter to
  `city = Udaipur` and the impostor disappears. This is where the two tracks connect.

---

## 5. Failures caught and logged (the portfolio's backbone)

Every failure was captured *before* fixing — the before/after pair is the artifact.

| # | What | Type |
|---|---|---|
| F1 | Groq blocked by Cloudflare (Python User-Agent) | build bug |
| F2 | Free-tier rate limit (429) → backoff + pacing + resumable runner | build bug |
| F3 | Repair + fallback loop proven via deliberate mock | reliability demo |
| F4 | Over-eager red flag (schema-valid ≠ content-correct) | content finding |
| F5 | recall@5 saturated at 1.0 → switched to recall@1 / MRR | eval design |
| F6 | Hybrid fixes GST ranking; a shared word defeats near-dup | retrieval |
| F7 | Reranking = 0 gain for 34× cost → not shipped | judgment (right/wrong tool) |

---

## 6. The judgments a reviewer should notice

1. **We measure, we don't assume.** Every retrieval change was proven with a number
   on a fixed question set — including the change we *rejected*.
2. **We fixed our own metric.** Caught recall@5 being saturated and switched to a
   metric with headroom before claiming success.
3. **We rejected a fancy technique on evidence.** Reranking is the "impressive"
   stage; we shipped hybrid instead because the data said reranking wasn't worth 34×
   the latency (competency #15 — knowing when a tool is the *wrong* tool).
4. **We handle model mistakes honestly.** Validation + repair + a real "needs human
   review" fallback, plus a hand-check against ground truth for content correctness.

---

## 7. Honestly not done yet (scope discipline)

- The residual near-duplicate case (Q09) is **diagnosed but not yet fixed** — the fix
  (metadata filtering via extracted `location`) is planned, not built.
- Content-correctness Layer-3 was an **assistant spot-check**, not yet a formal
  human-owned or LLM-judge scored eval (that's Phase 4).
- Vendor-level de-duplication of chunks in the top-k is a noted, unbuilt improvement.
- Freshness is flagged at extraction time but not **re-verified** over time (see
  ADR 0002).

---

## 8. One-paragraph version (for the README later)

*Phase 1 built Baraat's retrieval and extraction cores on a deliberately
booby-trapped corpus. Extraction turned 32 messy docs into schema-valid records with
zero repairs and a proven repair/fallback safety net; a hand-check against ground
truth caught one over-eager red flag (schema-valid ≠ content-correct). Retrieval was
measured across three stages on a 10-question golden set: hybrid search lifted
recall@1 from 0.80 to 0.90 almost for free, while a cross-encoder reranker added 34×
latency for zero gain and was rejected on the evidence — the residual look-alike-firm
case needs metadata filtering, not a better ranker. Every failure is logged with a
before/after pair (F1–F7).*
