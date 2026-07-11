# Phase 4 — Scope (Evals, Observability, Cost, Routing)

> Plain-language map of the biggest phase, written before building. Phases 1–3
> BUILT the system; Phase 4 MEASURES it and uses the numbers to make smart choices.
> Competencies: #1 evals, #9 routing/fallback, #10 caching, #11 latency, #12
> observability, #13 cost.

---

## 0. The big picture

> Put the car on a dyno: gauges for everything, then tune. We measure Baraat on
> three axes — **quality** (is the answer right?), **speed** (how fast?), **money**
> (what does it cost?) — then use those numbers to make **smart choices** (which
> model to use).

---

## 1. Four workstreams

### Workstream 1 — Evals (QUALITY)
**Evals do NOT create the answer.** The system already creates answers (the agent in
Phase 2, the briefing in Phase 3). **Evals = the exam that GRADES those answers.**

How it works:
1. 40 questions **with expected answers** (golden set, expanded from 10).
2. **Ask the system** those 40 questions → it produces 40 answers.
3. **Grade** each answer against the expected answer.

Two important nuances:
- **Grading is by MEANING, not exact text.** A free-text answer can be right in many
  wordings, so we don't string-match. An **LLM-as-judge** reads the answer + the
  expected answer and decides "is this correct and grounded?" — like grading an essay,
  not a fill-in-the-blank.
- **This grades a NEW thing.** recall@1 (Phase 1, 0.90) graded **retrieval** (did we
  fetch the right chunk?). Evals grade the **answer** (did the system SAY the right
  thing?). Two different stages:

  | | Grades | Grader | Status |
  |---|---|---|---|
  | recall@1 (Phase 1) | did we fetch the right chunk? | mechanical | done (0.90) |
  | **evals (Phase 4)** | did the system say the right thing? | **LLM-judge** | new |

- **Human check:** I manually grade a small sample to confirm the LLM-judge agrees
  with me — "an exam to check the examiner."

### Workstream 2 — Observability (WATCH the process)
**Record what happened inside each request**, like a flight recorder:
- tokens used (input + output)
- number of tool calls / steps
- latency (how long each step took)
- errors

For one request we get a **trace**: "retrieval 6ms, tool call 200ms, LLM answer 800ms,
420 tokens." Just faithfully recording the numbers. **This is the substrate everything
else reads from.**

### Workstream 3 — Cost & Latency (READ those numbers)
Not new measuring — **calculated from the observability data**:
- **Cost** = tokens × model price. Then total per question type / per tool / per
  workflow. ("This request: 420 tokens → ₹0.03.")
- **Latency** = analyze the recorded timing, especially **first-token latency** (time
  until the answer starts appearing) and prefill-vs-decode.

Workstream 2 *collects* raw numbers; Workstream 3 *turns them into* money and speed.

### Workstream 4 — Routing & Caching (USE the numbers to save money)
- **Routing:** two models — a **small/cheap/fast** one and a **big/smart/expensive**
  one. Send each question to the right one:
  - "What's Ever After's price?" → easy → **small model** (cheap)
  - "Is this contract risky?" → hard → **big model** (worth it)
  A **cost vs accuracy tradeoff**, proven with real numbers.
- **Fallback:** if the chosen model fails/times out, automatically try another — degrade,
  don't die (same spirit as Phase 2 guardrails).
- **Caching:** a *different* money-saver — **don't pay twice for the same work.** If two
  users ask the same thing, reuse the answer. Mostly a **documented tradeoff** (where it
  helps Baraat, where it doesn't).

---

## 2. One request, through all four (concrete)

User asks: *"What's the price for Ever After Films?"*
1. **Routing** → simple lookup → send to the **small model**.
2. **Observability** → records: 1 tool call, 350 tokens, 400ms.
3. **Cost** → 350 tokens × rate = ₹0.02.
4. **Evals** (later) → LLM-judge checks the answer "₹2,10,000" matches the golden
   answer → correct ✅.

---

## 3. Why the build order is what it is

**Tracing (observability) is the foundation** — once every request records tokens +
latency + spans, cost and latency reports are just *reading that data*. Evals give the
accuracy axis. Routing then combines cost + accuracy to decide.

```
1. Observability (tracing)   → the substrate (tokens, latency, spans per request)
2. Evals (golden set 40 + LLM-judge + human calibration)  → the accuracy axis
3. Cost attribution          → reads trace data
4. Latency reporting         → reads trace data
5. Routing + fallback        → uses cost + accuracy to route
6. Caching tradeoff (ADR)    → reasoning writeup
```

---

## 4. Two decisions (with recommendations)
1. **Two models for routing:** Groq offers `llama-3.1-8b-instant` (small/cheap/fast)
   and `llama-3.3-70b-versatile` (big/strong). Route simple → 8b, hard → 70b. *Rec:
   use these two* — a real, measurable setup.
2. **Judge model:** ideally a strong model; we only have Groq, so judge = Groq 70b
   (same caveat as the extraction ADR — Claude would be the production choice). Cost
   uses Groq's **published per-token rates** (real rates, honest attribution, even on
   the free tier).

---

## 5. The deliverable
A **cost/latency/accuracy report with real numbers**, a **working model router** with
documented tradeoffs, and an **observability trace** you can point to.

---

## Mini-recap
- Phase 4 = **measure** quality (evals), the process (observability), money+speed
  (cost/latency), then **choose** the right model (routing).
- **Evals GRADE answers** (by meaning, via LLM-judge) — different from recall@1 which
  graded retrieval.
- **Observability collects** the raw numbers; **cost & latency are calculated** from
  them.
- **Routing** = right-sized model per question (cost vs accuracy); **caching** =
  don't pay twice; **fallback** = degrade, don't die.
- Build order: **observability first** (the substrate), then evals, cost, latency,
  routing, caching.
