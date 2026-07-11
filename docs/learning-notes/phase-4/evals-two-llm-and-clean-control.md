# Phase 4 — Evals: one LLM answers, another LLM grades

> Plain-language record of the answer-quality eval: the two-LLM structure, the
> 40-question exam, the clean-control gap we caught and fixed, and why the judge
> itself needs human calibration. Companion to `phase-4-scope.md`.

---

## 1. High level — what this step is

We built the **exam for answer quality**. 40 questions, each with a *known-correct
answer* (that I own). Ask the system each question, it produces an answer, and a
**judge-LLM grades that answer** against the correct one. Output = a **quality score**
(metric #8, the real SLA).

---

## 2. The two LLM roles (the key structure)

Two different LLM jobs:
1. **The answerer** — retrieves the vendor's chunks, then writes a grounded answer.
   *(The system under test.)*
2. **The judge** — reads (question + my correct answer + the system's answer) and
   decides correct / partial / incorrect. *(The grader.)*

> In one line: **one LLM answers, another LLM checks it.**

---

## 3. Granular — one question start to finish (Q29)

> Q29: "Are there any red flags for Ever After Films?" (a clean vendor)

- **Answerer** retrieves Ever After's chunks → writes an answer.
- **Before the fix:** *"I don't have that information."* — it hedged, because a clean
  listing has no sentence saying "there are no problems," and we told it never to guess.
- **Judge** compares to expected "None; clean" → marks **incorrect**.
- **The fix:** changed the *answerer's* instructions — "if the listing shows no
  problems, confidently say 'no red flags found'; don't hedge, but still never invent
  problems."
- **After the fix:** *"No red flags were found in the listing."* → Judge marks
  **correct.** ✅

---

## 4. Results (40-question run)

**Before the fix:** mean quality = **0.70**

| Category | Score | Read |
|---|---|---|
| exact-match (GST/phone) | 1.00 | ✅ Phase-1-hard cases now answered perfectly |
| freshness / stale price | 1.00 | ✅ works end to end |
| simple lookup | 0.77 | some missing prices, some judge strictness |
| buried red flag | 0.60 | F13 "right doc, wrong chunk" |
| comparison | 0.50 | needs 2 vendors retrieved |
| **clean control** | **0.08** | 🔴 the gap — see below |

**The clean-control gap (F14):** the system couldn't say "no red flags found" — it
hedged "I don't have information." Only the **negative-test** questions caught it. A
due-diligence tool that can't state a clean bill of health is a real product gap.

**After the fix (confirmed by spot-checks; full re-run was blocked by Groq rate limits):**
- Q29 clean control: incorrect → **correct** ✅
- Q17 lookup: partial → **correct** ✅ (k=8 fetched the price chunk)

**One case the fix does NOT solve (honest + useful):** Q03 (Candid Frames buried red
flag) still fails. The complaint says "couples reported… the studio…" and never repeats
the name "Candid Frames," so the keyword search buries that chunk below 8 others. That's
a **retrieval** problem, not a prompt one — and the case where **reranking might finally
be worth it** (it wasn't for near-duplicates).

---

## 5. Who watches the watchman — judge calibration

Since the **judge is itself an LLM, it can be wrong.** So we don't just trust it — a
**human-calibration** step: I grade a 12-question sample myself, and we measure how
often the judge agrees with me (`human_calibration.py`). Part of the low score was a
*real gap* (clean-control) and part was *judge strictness* (penalizing extra correct
detail) — calibration separates the two. That check is the difference between a real
eval and a fake one.

---

## 6. Two honest process lessons
- **The saved-only-at-end runner lost 37/40 questions** when a rate-limit crash hit.
  Fixed: per-question backoff + incremental crash-safe saves + record failures as
  'error' rows instead of dying. (Reliability applies to the eval harness too.)
- **The fix helped clean-control but not buried-red-flag** — because they have
  different root causes (prompt vs retrieval). One fix does not move every category;
  the per-category breakdown is what tells you *what* actually changed.

---

## Mini-recap
- 40 questions → **answerer LLM** answers each → **judge LLM** grades vs the known
  answer → quality score (0.70 baseline).
- **Clean-control 0.08** was the gap (can't say "no red flags found"); a prompt fix
  flipped it to correct.
- **Buried-red-flag** needs a *retrieval* fix (reranking), not a prompt fix.
- The **judge is an LLM too**, so we **calibrate it against a human**.
