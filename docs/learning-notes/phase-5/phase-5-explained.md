# Phase 5 — Explained (CI gate + final packaging)

> Plain-language walkthrough of the wrap-up phase. Phases 1–4 BUILT and MEASURED the
> system; Phase 5 PROTECTS the quality (so it can't silently break) and PRESENTS the
> whole thing (so a reviewer gets it in minutes). Competencies: #16 (production failure
> modes, consolidated), #15 (fine-tuning-vs-RAG judgment), full project narrative.

---

## 1. The CI eval gate — "quality can't silently break"

**What "CI" is:** Continuous Integration — the automated checker that runs every time
you push code. The robot that says "this change is OK" or "blocked."

**What the gate does:** runs the 40-question eval and **fails the build if the quality
score drops below a threshold** (0.65). Every future change must keep the AI at least as
good — or CI rejects it.

**Why it's the capstone:** a demo that works *once* is worthless if the next tweak
quietly makes it dumber. Most AI demos have no safety net. The gate makes a regression
**impossible to miss** — automatically.

**The proof (demo):**
- baseline scores 0.70 → above 0.65 → **PASS** ✅
- deliberately break it (zero the exact-match answers) → 0.50 → below 0.65 → **FAIL** ❌
  (exits non-zero, which is how CI blocks a merge).

**Analogy:** a spell-checker that refuses to publish if you just added typos. The gate
refuses to ship a change that made the AI worse. (Competency #16 — silent eval
regressions.)

---

## 2. Fine-tuning vs RAG vs ICL — the judgment record (#15)

**What it is:** a *written argument* (no code) on when each technique is the right/wrong
tool for Baraat. The four:
- **RAG** — fetch facts at query time (we use this)
- **ICL** (in-context learning) — put instructions/examples in the prompt (we use this)
- **Fine-tuning** — retrain the model's weights to bake in behavior
- **Distillation** — train a small model to copy a big one

**The judgment:** Baraat's facts **change** (prices) and must be **attributable** (cite
the source). **RAG + ICL fit perfectly.** **Fine-tuning is the WRONG tool** — it bakes
facts into weights (a price change means retraining), gives no attribution, and needs
thousands of examples we don't have. Distillation deferred (needs traffic + labels).

**Why it matters:** competency #15 is literally "knowing when each approach is the WRONG
tool." The skill is the *judgment to not reach for fine-tuning when it's wrong* — argued
clearly. That restraint is the artifact.

---

## 3. Failure log consolidated — the reasoning arc at a glance

**What:** an **index table at the top** of the failure log listing all failures (F1–F14),
each with a one-line summary + type.

**Why:** the failure log is arguably the most valuable file — what broke, how it was
caught, how it was fixed. The index turns a long log into a **scannable story**: build
bugs (F1–2), deliberate reliability demos (F3, F8, F10), honest findings (F4, F13, F14),
an eval-metric fix (F5), a technique rejected on evidence (F7), and the safety
attack→defense pair (F11→F12).

---

## 4. Architecture diagram — the shape of the system

**What:** a doc with a diagram of how it all connects — the **two tracks** (retrieval +
extraction) from one corpus, feeding the **agent** (tools + guardrails), wrapped by the
**safety** layer, on the **observability + eval** spine — plus one request's flow.

**Why:** a reviewer needs the structure fast. A diagram shows in seconds what prose takes
paragraphs to say.

---

## 5. README — the front door

**What:** the public-facing story for a non-technical reader first: what Baraat does, the
competency map, headline numbers (recall 0.80→0.90, safety 3/3 blocked, routing 87%
cheaper), copy-paste run commands, and **honest limitations**.

**Why:** it's the first thing anyone opens. In under 2 minutes it must say "this is a
portfolio of real AI-PM judgment" and point to the deeper docs.

---

## The one-sentence summary

> Phases 1–4 **built and measured**; Phase 5 **locks in the quality** (CI gate stops
> silent regressions) and **packages the story** (decision record, failure-log index,
> architecture, README) so the work is both *defensible* and *presentable*.

**The portfolio-grade subtlety:** the README and failure log **don't hide the open gaps**
(buried-red-flag retrieval, 8b accuracy blocked by the daily cap, one classifier
misroute). Showing what's *not* done, honestly, is the signal of a real engineer/PM — and
it gives genuine "here's what I'd do next" answers in an interview.

---

## Mini-recap
- **CI gate:** auto-fails a build if quality drops below 0.65 (proved: 0.70 PASS → 0.50
  FAIL). The regression-prevention mechanism.
- **#15 decision record:** RAG+ICL are right (changing, attributable facts);
  fine-tuning/distillation are the wrong tool now, deferred with triggers.
- **Failure-log index, architecture diagram, README:** package the story so it's
  scannable and honest.
- **Phase 5 = protect (gate) + present (docs).**
