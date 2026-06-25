# Learning Notes — Retrieval & Evaluation (Track A)

> My plain-language notes on how retrieval works and how we measure it. Companion
> to `phase1-and-schema.md` (which covered the corpus, schema, and extraction).
> Written so I can explain this in an interview, not just nod along.

---

## 1. The system is a PIPELINE with two outputs (retrieval vs answer)

The biggest unlock: the system isn't one black box with a single output. It has
**stages**, and **each stage produces its own output you can evaluate separately.**

```
   user question
        │
        ▼
 ┌──────────────┐   OUTPUT 1 = retrieved chunks
 │ 1. RETRIEVAL │ ───────────────────────────►  (BUILT — we are here)
 └──────────────┘
        │
        ▼
 ┌──────────────┐   OUTPUT 2 = a written answer
 │ 2. ANSWER    │ ───────────────────────────►  (NOT built yet — Phase 4)
 │    (LLM)     │
 └──────────────┘
        │
        ▼
   answer to user
```

**What each output means:**
- **Retrieval output = the chunks the search fetched.** "Given the question, here
  are the top-k passages I think are relevant." No writing, no LLM — just search
  returning pieces of the corpus. *This is all we've built so far.*
- **Answer output = the written reply an LLM composes** using those chunks. "Based
  on the retrieved passages, here's the answer in prose." *This stage doesn't
  exist yet; it comes in a later phase.*

**Two outputs → two different graders:**

| Stage | Its output | How we grade it | Grader | When |
|---|---|---|---|---|
| 1. Retrieval | the fetched chunks | "is the right chunk in the top-k?" → recall@k | **mechanical** (no LLM) | now |
| 2. Answer | the written answer | "is it accurate & grounded?" | **LLM-as-judge** | Phase 4 |

> Interview line: *"I evaluate each pipeline stage separately. Retrieval is graded
> mechanically with recall@k; the final written answer is graded by an LLM-judge.
> Matching the grader to the output type is the point."*

---

## 2. recall@k — what it is and why we use it NOW

**What it measures:** of all the questions, for how many did the *correct chunk*
show up in the **top k** retrieved results (we use k=5).

```
recall@5 = (questions whose gold chunk was in the top 5) ÷ (total questions)
```

Example: ask "does Anokhi have complaints?" — the *gold chunk* is Anokhi's
complaint paragraph. If that paragraph is in the top 5 results → hit. If not →
miss. Do this for all 10 golden questions; the fraction of hits is recall@5.

**Why it's the right measuring stick right now:** we just built the *retrieval*
stage, and the whole next arc is about *improving retrieval*. recall@k is how you
put a number on "did retrieval fetch the right stuff?" It's:
- **mechanical** — just check if the gold chunk is in the list (no LLM, no opinion)
- **objective & reproducible** — same inputs, same score every time
- **cheap & instant**

**CRUCIAL point — what baseline / hybrid / reranking actually improve:**
These three are **mechanisms to improve recall@k (retrieval quality)** — they are
**NOT** about improving the written answer. They change *which chunks get fetched*:
- **Baseline (semantic only)** — search by meaning. Good at fuzzy lookups; bad at
  exact strings (GST) and tends to bury red flags.
- **Hybrid (semantic + keyword)** — adds exact keyword matching. Fixes exact-match
  (GST, phone, near-duplicate names).
- **Reranking** — a smarter second pass that re-orders the top candidates so the
  truly relevant chunk (e.g. the buried complaint) rises into the top-k.

We measure recall@5 at each stage on the *same* golden questions, so the
improvement (the delta) is provable: e.g. baseline 0.5 → hybrid 0.7 → reranked 0.8.
Better retrieval ⇒ the answer stage later has better material to work with, but the
answer stage is a *separate* thing graded *separately*.

> Interview line: *"Baseline → hybrid → reranking are retrieval improvements; I
> prove each one with a recall@k delta on a fixed question set. They feed the
> answer stage but aren't graded as answers."*

---

## 3. Why a golden set when we already have the corpus / manifest / schema?

Sharp question I asked: *"We have the schema and the extracted records and the
manifest — why build ANOTHER truth dataset?"*

Because those are organized **by document** — they're *facts about each vendor*.
But to **test a system you need QUESTIONS**, and none of those artifacts contain
questions.

| Artifact | What it holds | Organized by | Has questions? |
|---|---|---|---|
| Corpus (`data/vendors`) | the 35 messy source docs | document | no |
| Manifest | what we planted in each doc (facts) | document/vendor | no |
| Schema | the *shape/rules* for records (empty template) | — | no (no facts either) |
| Extracted records | structured JSON per vendor | vendor | no |
| **Golden set** | **questions + expected answers** | **question** | **YES** |

- The **schema** is just an empty template (field names + rules) — no facts, no
  answers, so it can't be the truth a grader checks against.
- The **manifest/records** have facts, but as a pile organized by vendor — **not
  questions.** You can't grade a system without asking it something.

**Textbook vs exam analogy (the keeper):**
- Manifest / records = the **textbook** (all the facts written down).
- Golden set = the **exam questions written from that textbook**, plus the answer
  key.
- A teacher *has* the textbook but still has to *write an exam* — you can't grade a
  student by handing them the textbook. And the exam doesn't ask *every possible*
  question; it asks a **representative sample** that tests the important behaviours
  and the known failure modes.

**So the golden set:**
- is **written using** the manifest as the source of truth (honest answers),
- but is a **distinct artifact** because it's the only one shaped as
  "question → expected answer,"
- and is a **curated sample** (8–10 now, 30–40 later) targeting specific
  behaviours: simple lookup, exact-match, freshness/stale, buried red flag — not
  an exhaustive list of every question.

> Interview line: *"The manifest is my textbook of ground-truth facts; the golden
> set is the exam I wrote from it — a curated sample of question/answer pairs that
> probes specific failure modes. The facts can't grade a system; questions can."*

---

## Mini-recap
- The system is a **pipeline**: retrieval output (chunks) and answer output (prose)
  are **two different things, graded two different ways.**
- **recall@k** scores *retrieval* (mechanically, now). Baseline/hybrid/reranking
  are mechanisms to **raise recall@k**, not to improve the written answer.
- The **golden set** is the *exam* (questions + answers) — needed even though we
  have the manifest (the *textbook*), because only it is shaped as questions.
