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
- **What we did on purpose:** with a `MockBackend` (no API key, deterministic), scripted three model behaviours and ran them through the real validate→repair→fallback logic:
  - valid JSON → accepted first try
  - invalid (`rating: 7.5`, `price_unit: per_day` for a caterer) → **repaired** with targeted errors, then accepted
  - invalid every attempt → **fell back** to `needs_human_review: true` (never guessed)
- **Result:** all three paths behaved as designed (`src/extraction/demo_mock.py`).
- **Why it matters:** this is the competency #7 (structured-output reliability) artifact. Forcing the failure with a mock is *more* convincing than hoping the live model misbehaves — it's repeatable and free.

### F4 (content-correctness finding — Layer 3 vs the manifest) — over-eager red flags
- **Context:** on the real Groq run (32 non-reserved docs, model `llama-3.3-70b-versatile`, 0 repairs, 0 fallbacks, ~67k tokens), records were schema-valid. Checking content against `data/vendors/_corpus_manifest.md` surfaced nuances validation can't:
  - **False positive:** `photographer_pixelpandit` → `red_flags: ["Communication was a little slow during peak season."]`, but the manifest planted **no** red flag there. The model treats mild review criticism as a due-diligence red flag.
  - **Defensible judgment calls:** open-ended "from ₹X and up" pricing (royal_decor pair, lakeview, petals_and_props) → `price_confidence: low`. Consistent with our rules, but worth noting the boundary.
- **Score (extraction vs manifest, Phase 1 baseline):** stale detection 5/5; GST exact-match 6/6; all 5 buried-red-flag docs surfaced their flags; **1 false-positive red flag** out of the clean-control set.
- **Status:** logged, **not yet fixed** (per §3.1). Candidate fixes for later: a red-flag severity threshold, or prompt guidance distinguishing "serious issue" from "mild review gripe." This is the textbook demonstration that **schema-valid ≠ content-correct** — only grading against ground truth catches it.
