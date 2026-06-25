# Baraat — Topic-by-Topic Walkthrough (plain language)

> A clean, "explain it back in my own words" walkthrough, one topic at a time.
> This is the *narrative* version for interview prep. Deeper detail lives in
> `phase1-and-schema.md` and `retrieval-and-evals.md`; this file is the spine.
>
> Topics:
> 1. Extraction (DONE — below)
> 2. Retrieval (DONE — below)
> 3. Golden dataset & evals (DONE — below)

---

## Topic 1 — Extraction (turning 35 messy docs into clean records)

### 1. The setup
- We have **35 vendor documents** — messy, prose-style pages (listings + reviews),
  with realistic problems planted on purpose (stale prices, buried complaints,
  near-duplicate names). 32 are in scope; 3 are reserved for Phase 3.
- We use the **Groq model** (Llama 3.3 70B) to *read* each document and pull the
  facts out.
- The facts have to land in a fixed shape we designed: the **schema**.

### 2. The schema = fields + rules
The schema is two things at once:
- **Fields** — the labeled boxes every vendor must be turned into: `name`,
  `category`, `price_range_inr {min, max}`, `price_unit`, `gst_number`, `rating`,
  `red_flags`, `needs_human_review`, `extraction_notes`, etc.
- **Rules** — constraints those boxes must obey, e.g.:
  - `min` price ≤ `max` price
  - a `caterer` must be priced `per_plate` (unit must match the category)
  - if `needs_human_review` is true, `extraction_notes` must explain why
  - `rating` between 0 and 5; `gst_number` matches the 15-char format

### 3. The Python validator — TWO checks, ZERO intelligence
After Groq fills in a record, a plain **Python script** checks it. This script is
**not smart** — it is just `if`-statements looking at the values already in the
JSON. It does **no meaning-search, no looking things up in the real world.** Two
checks, in order:

- **Check A — SHAPE (format).** Are the boxes the right *type/format*? Is `rating`
  a number 0–5? Is `category` one of the 5 allowed words? Is the GST the right
  shape? (This is "structural validation.")
- **Check B — RULES.** Do this **one record's** fields agree with the rules we
  wrote? `min ≤ max`? unit matches category? review-flag has a note?
  > ⚠️ This is *within a single record* — Anokhi's record is never compared to
  > another vendor's. And calling it "meaning" is a trap: there's **no semantic
  > understanding here**, only our hardcoded rules being satisfied or not.

### 4. What happens after the check — accept / repair / fallback
```
Groq fills the record
      │
      ▼
Python validator:  SHAPE ok?  →  RULES ok?
      │
  ┌───┴────────────────────────────┐
  ▼ both pass                       ▼ something fails
ACCEPT the record           REPAIR: hand Groq the exact errors,
(write it to the table)      ask it to fix and return again
                                    │  (capped — max 2 tries)
                              ┌─────┴──────┐
                              ▼ now passes  ▼ still failing
                            ACCEPT        FALLBACK:
                                          needs_human_review = true
                                          + a note (never silently guess)
```
- **Accept** → the clean record is saved.
- **Repair** → the *same* Groq model is asked again, this time shown precisely
  what it got wrong. Capped at 2 tries so it can't loop forever.
- **Fallback** → if it still won't validate, we don't pretend. We flag the record
  `needs_human_review = true` with a note. This whole thing is still just a Python
  script — a fixed, capped retry, **not** an agent.

### 5. What actually happened on the real run
- 32 docs, Groq Llama-3.3-70B, **0 repairs, 0 fallbacks** — every record passed
  SHAPE + RULES on the first try. That's why there was **no real Failure-3**; the
  repair/fallback paths never fired on real data.
- So we proved those paths **deliberately with a mock** (F3): scripted a
  valid case, an invalid-then-repaired case, and an invalid-always case. The last
  one failed twice and **fell back** — exactly as designed. (Your summary of this
  was right.)

### 6. Layer 3 — me, by hand, vs the MANIFEST
SHAPE + RULES can only prove a record is *well-formed and self-consistent*. They
can **never** prove the *facts are true* — the validator has no access to ground
truth, only to the JSON in front of it. So the final layer is:
- **I manually compare the records to `data/vendors/_corpus_manifest.md`** (the
  ground-truth ledger of what we planted in each doc).
- This is the only layer that catches "confidently wrong but internally
  consistent" — e.g. the pixelpandit record invented a red flag the manifest never
  planted (F4). SHAPE was fine, RULES were fine; only the manifest comparison
  caught it.

> **The three layers, in one line each:**
> 1. SHAPE — is the JSON well-formed? (Python, automatic)
> 2. RULES — does this record obey our constraints? (Python, automatic)
> 3. FACTS — is it actually true? (me, by hand, vs the **manifest**)

### 7. Where the golden dataset sits (it does NOT belong here)
The **golden dataset** (≈10 questions + expected answers) was built now, but it is
a **separate thing for a separate track (retrieval)**. It is the exam for "did the
system *answer the user* correctly?" — not for extraction.
- Extraction is graded against the **MANIFEST**.
- Retrieval/answering is graded against the **GOLDEN DATASET**.
- The golden dataset is *written from* the manifest, but it never appears in the
  extraction flow above. Keep the two answer keys apart.

### 8. The real-life takeaway (interview framing)
In a real project with 35 docs, "me checking by hand" (Layer 3) is the correct,
not-lazy choice. At thousands of docs it becomes a **sampled** manual check plus an
**LLM-as-judge** doing an approximate automated version of the same
manifest-comparison — which is exactly what Phase 4 builds later. The repeatable
AI-PM skill on display: *design a schema, let the model fill it, validate
mechanically (shape + rules), and handle the model's mistakes honestly (repair,
then an explicit "needs human review" fallback) instead of trusting it blindly.*

---

## Topic 2 — Retrieval (finding the right text for a question)

### 1. What this track does (and how it differs from extraction)
Retrieval is the **"find and read"** track. Given a user's question, it fetches
the most relevant passages from the corpus. It works on the **raw prose** — it
never touches the JSON records from extraction. (Extraction = "compare and
compute" on clean fields; retrieval = "find and read" the actual words. Two
independent siblings built from the same 35 docs.)

### 2. Step 1 — Chunking (cut docs into passages)
- A whole document is too big to retrieve as one lump — a buried complaint would
  get "averaged away" inside a mostly-positive page (the **lost-in-the-middle**
  problem). So we cut each doc into smaller **chunks**.
- **Paragraph-aware**, ~160 words max per chunk (not blind fixed-size cuts), so a
  chunk is a coherent thought, not a sentence sliced in half.
- Each chunk is tagged with a **vendor prefix** ("Vendor: {name} ({category}).
  …") so the passage is self-describing even out of context.
- Result on our corpus: **32 docs → 204 chunks** (avg ~6.4 per doc). Files
  starting with `_` (manifest + Phase-3 reserved docs) are skipped.

### 3. Step 2 — Embedding (turn text into meaning-numbers)
- Each chunk is run through an **embedding model** that converts text into a list
  of numbers (a **vector**) capturing its *meaning*. Similar meanings → vectors
  that sit close together on a "map of meaning."
- We use a **local** model (`BAAI/bge-small-en-v1.5`, 384 numbers per chunk).
  Local because Groq has no embeddings endpoint, and local is free, offline, and
  deterministic — no per-query API cost or network dependency for something this
  small.

### 4. Step 3 — Vector store (the searchable database of vectors)
- All 204 chunk-vectors are stored in a simple **NumPy array** and saved to
  `data/index/`.
- Deliberately **not** FAISS/Chroma/Pinecone — at ~200 chunks, exact cosine
  similarity over a NumPy array is simpler, dependency-light, and just as fast.
  Those heavier tools are a documented *upgrade path* for when scale/persistence/
  concurrency actually demand it. (Resisting over-engineering is itself the point.)

### 5. Step 4 — Search (baseline = semantic only)
```
user question
     │
     ▼
embed the question with the SAME model used to build the index
     │
     ▼
query vector (384 numbers)
     │
     ▼
cosine similarity vs all 204 chunk vectors  →  rank by closeness
     │
     ▼
top-k chunks (k=5)   ← this is the retrieval OUTPUT
```
This is **baseline retrieval: semantic only** — search purely by *meaning*. No
keyword matching, no reranking yet. It's Stage 1 of a planned 3-stage arc.

### 6. The 3-stage improvement arc (and what each fixes)
Each stage is measured on the **same golden questions** so the **recall@5 delta**
is provable (this is where Topic 3's golden set plugs in):
```
Stage 1  BASELINE (semantic only)   — good at fuzzy meaning; BAD at exact
                                       strings (GST/phone) and buries red flags
Stage 2  + HYBRID (semantic+keyword) — adds exact word/char matching; fixes
                                       exact-match & near-duplicate-name questions
Stage 3  + RERANKING                 — smarter second pass re-orders top
                                       candidates so the buried red flag rises
```

### 7. What breaks on baseline (the failures we expect to log)
Semantic search is meaning-based, so two planted traps should fail at baseline —
and we log the real failure *before* fixing it:
- **Exact-match (GST / phone / near-duplicate names)** — semantic search is bad at
  exact strings; "08ABACR4567Q1Z9" has no "meaning" to sit near. → fixed by
  **hybrid** (Stage 2).
- **Buried red flag** — a complaint hidden in a late paragraph of an otherwise
  positive doc ranks low. → improved by **reranking** (Stage 3).

### 8. How recall@5 plugs in here
For each golden question, the **pre-marked gold chunk** is the passage that
*should* be retrieved. Run the question through search; if the gold chunk is in
the top 5 → hit. recall@5 = hits ÷ total questions. We compute it at baseline,
then hybrid, then reranked — and the rising number is the evidence that each
change actually helped (no "this should help," show the delta).

> **Interview one-liner:** *"Retrieval is the find-and-read track over raw prose.
> I chunk paragraph-aware to beat lost-in-the-middle, embed locally, search by
> cosine similarity, and improve it in three measured stages — baseline → hybrid
> → reranked — each proven with a recall@5 delta on a fixed golden set."*

---

## Topic 3 — Golden dataset & evals (the honest exam)

### 1. What it is, in one line
A small, fixed set of **~10 questions, each with the correct answer pre-written**,
that we use to **grade the system** — like an exam with an answer key written
*before* the student sits it.

### 2. What it's made FROM (and who owns the answers)
- Built **from the manifest** (`_corpus_manifest.md`) — the ground-truth ledger of
  what we planted in each doc. The manifest is the *textbook*; the golden set is
  the *exam written from that textbook*.
- **I (the human) own the answers**, written *before* seeing the system's output.
  Claude can draft candidate questions (it knows where the traps are), but if I
  wrote the answers *after* seeing the output, it wouldn't be an eval — it'd be a
  rationalization.
- It's a **curated sample**, not every possible question: deliberately targets the
  known failure modes (simple lookup, exact-match GST/name, stale price, buried
  red flag).

### 3. Each entry has THREE parts (because there are two graders)
This is the key detail. One question carries two different "correct" references:

```
GOLDEN ENTRY
├── question          "Does Anokhi have any complaints?"
├── expected answer   (prose) "Yes — a billing dispute / late setup is noted."
└── gold chunk        the SPECIFIC correct passage, pre-marked from the manifest
                       (Anokhi's complaint paragraph)
```
- The **expected answer** is for grading the final written reply.
- The **gold chunk** is for grading retrieval — and it must be **decided up
  front**, not read off whatever retrieval returns (otherwise the eval is
  circular and can never fail).

### 4. The two uses (two stages, two graders)
```
                          GOLDEN SET
                              │
            ┌─────────────────┴──────────────────┐
            ▼                                     ▼
  USE 1: grade RETRIEVAL                USE 2: grade the ANSWER
  "did the gold chunk land             "is the written reply correct
   in the top 5?"                       & grounded?"
            │                                     │
            ▼                                     ▼
       recall@5                            LLM-AS-JUDGE
   mechanical, no LLM,                  an LLM scores the prose
   objective, runs NOW                  reply vs the expected answer
   (Track A is built)                   (Phase 4 — not built yet)
```
- **Use 1 — recall@5 (now).** For each question, did the **pre-marked gold chunk**
  appear in the top-5 retrieved chunks? Count the hits ÷ total = recall@5. Pure
  mechanical check — no LLM, same score every time.
- **Use 2 — LLM-as-judge (Phase 4).** Once the system *writes* answers, an LLM
  grades each written answer against the expected answer. Needed because prose
  can't be checked with `if`-statements — you need judgment.

### 5. How it's used in the build (the eval engine)
The golden set is the fixed yardstick for the whole **baseline → hybrid →
reranking** arc. We run the **same** questions at every stage and report the
**recall@5 delta**, so each improvement is *proven*, not asserted:
```
same golden questions ─► baseline   recall@5 = ?.??
                      ─► + hybrid    recall@5 = ?.??   (delta logged)
                      ─► + reranking recall@5 = ?.??   (delta logged)
```
Later (Phase 5) this same set powers the **CI eval gate**: if a code change drops
the score below a threshold, the build fails — that's the regression-prevention
mechanism, not just a one-time demo.

### 6. Don't confuse it with the manifest (the two answer keys, again)
- **Manifest** = facts about each doc, organized *by document*. Grades
  **extraction**. Has no questions.
- **Golden set** = questions + answers + gold chunks, organized *by question*.
  Grades **retrieval/answering**. Written *from* the manifest, but a separate
  artifact used in a separate track.

> **Interview one-liner:** *"The golden set is my exam, authored from the manifest
> before any run. Each question carries a pre-marked gold chunk for mechanical
> recall@k and an expected answer for the LLM-judge — same set drives the
> retrieval-improvement deltas and, later, the CI regression gate."*
