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

## 4. Correcting a wrong mental model: the "gold chunk" must be pre-marked

A mistake I actually made: I described the gold chunk as "the chunk that shows up
in the top 5" — i.e. defined by what retrieval returns. That's backwards, and
it's circular: if the gold chunk is whatever retrieval returns, retrieval can
never score below 100%, because you're grading it against its own output.

```
 ✗ WRONG:  run retrieval → look at the top 5 → call that "the gold chunk"
           (circular — there is nothing left to fail)

 ✓ RIGHT:  decide the gold chunk FIRST, from the manifest, before running
           anything
                │
                ▼
           THEN run retrieval
                │
                ▼
           check: did the pre-decided gold chunk land in the top-k?
           → that check is recall@k
```

**The rule:** the gold chunk is picked from ground truth (the manifest) at the
time the golden question is *written*, independent of and prior to any
retrieval run. Once it's fixed, it never changes based on what the system
returns — otherwise the eval stops being honest (same logic as "I write the
golden set's expected answers before seeing the system's output," §1c of the
companion schema notes file).

---

## 5. The actual baseline run — and why recall@5 = 1.0 fooled me

We ran the 10 golden questions through **baseline (semantic-only) retrieval**.
First result: **recall@5 = 1.0** — every gold doc was somewhere in the top 5. Looks
perfect. It isn't. Two lessons came out of this run.

### 5a. What recall@5 vs recall@1 actually check
- We don't string-match the *expected answer text* against chunks. We check
  whether a chunk **from the correct document** (the gold doc, by `vendor_id`)
  shows up. The expected answer is *my* ground truth; the gold *doc* is what
  retrieval is graded against.
- **recall@5** = did the right doc land *anywhere* in the top 5? → 10/10 = **1.0**
- **recall@1** = did the right doc land at *rank 1* (the very first)? → 8/10 = **0.80**

### 5b. Lesson 1 — a saturated metric can't show improvement
recall@5 was already at the ceiling (1.0) on baseline. If it's maxed before I even
add hybrid search, it **literally cannot go up** — so it can't prove hybrid helped.
A metric that can't move is the wrong metric. So I added two stricter, rank-aware
metrics that *do* have headroom:

| Metric | Baseline | Measures | Room to improve? |
|---|---|---|---|
| recall@5 | **1.0**  | gold doc anywhere in top 5 | none (saturated) |
| recall@1 | **0.80** | gold doc at **rank 1** | yes |
| MRR      | **0.875**| avg of 1/rank (rank-sensitive) | yes |

> Interview line: *"My first headline metric was saturated at 1.0 — it looked like
> a pass but couldn't measure the very improvement I was about to make. I switched
> to recall@1 and MRR, which had headroom, before claiming anything."*

### 5c. Lesson 2 — "in the top 5" hides two different real failures
The gold doc being *present* is not the same as retrieval being *correct*. Three
exact-match questions show why:

| Q | Type | Gold rank | The real problem |
|---|---|---|---|
| Q08 | GST lookup (want Grand Pavilion) | **4** | right doc **buried** behind 3 irrelevant vendors |
| Q09 | Royal Decor (want **Udaipur**) | **2** | wrong twin (**Jaipur**, Royal Decor & Events) sits at rank 1 |
| Q10 | Grand Thali (want **Delhi**) | **1** | right one is #1, but wrong twin (**Lucknow**) is right behind it |

- **Q08 = a ranking problem.** A GST string (`36AAEGP2210R1Z3`) has no *meaning* for
  an embedding model to grab, so semantic search ranks it low.
- **Q09/Q10 = a disambiguation problem.** The two near-duplicate firms *sound the
  same*, so meaning-based search returns **both** — a downstream LLM would see two
  GSTs / two phone numbers and could pick the wrong one. We don't want the impostor
  in the list at all.

### 5d. The clean questions — and a hidden third near-duplicate (Q06)
The other 7 were all **rank 1**. But Q06 hid a surprise that *only* the stricter
"which other vendors are in the top 5?" view exposed:

| Q | Type | Rank | Note |
|---|---|---|---|
| Q01–Q05 | lookups + buried red flags | 1 | clean ✅ (buried complaints *were* found) |
| **Q06** | stale price (Anokhi Rasoi) | 1 | ⚠️ "**Annapurna** Rasoi" also appeared — sounds like "**Anokhi** Rasoi" |
| Q07 | stale price (Rajwada Palace) | 1 | clean ✅ |

Q06's gold is still rank 1, so it's not a failure — but it's a **third**
near-duplicate pair we never planted on purpose, and both recall metrics looked
perfect. Only inspecting the *other* vendors in the top 5 surfaced it. Logged as a
fragility, not a failure.

### 5e. The honest baseline scoreboard (what hybrid must beat)
- **recall@5 = 1.0** — saturated, kept only as a floor check.
- **recall@1 = 0.80** ← the real number to beat.
- **MRR = 0.875** ← rank-sensitive, also has room.
- The two things dragging recall@1 below 1.0 are exactly **Q08 (rank 4)** and
  **Q09 (rank 2)** — both exact-match cases. That's precisely what hybrid (keyword +
  semantic) should fix: **expected recall@1 0.80 → ~1.0**.

*(All of this is also in `docs/failure-log.md` as F5 — the failure log is the
formal record; this is the plain-language version for me.)*

---

## Mini-recap
- The system is a **pipeline**: retrieval output (chunks) and answer output (prose)
  are **two different things, graded two different ways.**
- **recall@k** scores *retrieval* (mechanically, now). Baseline/hybrid/reranking
  are mechanisms to **raise recall@k**, not to improve the written answer.
- The **golden set** is the *exam* (questions + answers) — needed even though we
  have the manifest (the *textbook*), because only it is shaped as questions.
- **Baseline result:** recall@5 = 1.0 was *saturated and misleading*; the honest
  numbers are **recall@1 = 0.80, MRR = 0.875**. Q08 (buried rank 4) and Q09 (wrong
  near-dup twin at rank 1) are what hybrid search must fix. "In the top 5" ≠
  "correct" — **rank and near-duplicate contamination matter too.**
