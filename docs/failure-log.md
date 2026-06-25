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
  - **Defensible judgment calls:** open-ended "from ₹X and up" pricing (royal_decor pair, lakeview, petals_and_props) → `price_confidence: low`. Consistent with our rules, but worth noting the boundary.
- **Score (extraction vs manifest, Phase 1 baseline):** stale detection 5/5; GST exact-match 6/6; all 5 buried-red-flag docs surfaced their flags; **1 false-positive red flag** out of the clean-control set.
- **Status:** logged, **not yet fixed** (per §3.1). Candidate fixes for later: a red-flag severity threshold, or prompt guidance distinguishing "serious issue" from "mild review gripe." This is the textbook demonstration that **schema-valid ≠ content-correct** — only grading against ground truth catches it.
