# ADR 0001 — Model backend for extraction: open model via Groq

**Status:** accepted (Phase 1)
**Date:** 2026-06-21

## Context
The extractor (Track B) needs an LLM to turn vendor prose into structured JSON.
`CLAUDE.md` §4 names Claude (Anthropic API) as the project LLM. At build time the
builder had no Anthropic API key, but did have a **Groq Cloud** key (note: Groq ≠
xAI's "Grok" — Groq is a fast-inference host for open models like Llama).

## Decision
Use **Groq Cloud** with the open model **`llama-3.3-70b-versatile`** as the
extraction backend for now, behind a **provider-agnostic backend interface**
(`src/extraction/model_backend.py`).

## Why this is acceptable (and partly a strength)
- The target audience is a **Google/Meta-caliber AI PM panel**, not Anthropic —
  they care about engineering judgment, not which vendor was used.
- The reliability machinery (schema validation, repair loop, fallback) is
  **model-agnostic**. Making the model a swappable plug-in is good design and
  pre-stages competency #9 (model routing/fallback).
- An open model that follows JSON instructions slightly less perfectly than a
  frontier model actually **exercises the repair/fallback loop more** — a plus
  for demonstrating competency #7.

## Tradeoffs / costs
- **Free-tier limits** (12k tokens/min) forced backoff + pacing + a resumable
  runner (see failure-log F2). Slower, but robust.
- Possible small quality gap vs Claude on subtle extraction (see failure-log F4:
  one false-positive red flag). Acceptable for a baseline; logged, not hidden.
- `CLAUDE.md` §4 still names Claude as the **LLM-judge** for evals. That choice
  is deferred to Phase 4 and can stay Claude (or move) independently.

## Revisit when
- An Anthropic key becomes available (flip the backend; optionally A/B Claude vs
  Llama on the same docs for a real quality/cost delta — a strong artifact).
- We design the Phase 4 eval judge.

## Security note
The Groq key was pasted into chat during setup and is therefore considered
exposed; it must be **rotated** at console.groq.com. Going forward, keys live only
in `.env` (gitignored) or the environment — never committed, never in chat.
