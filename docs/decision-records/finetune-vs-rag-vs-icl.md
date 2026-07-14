# Decision Record — Fine-tuning vs In-context learning vs RAG vs Distillation

**Status:** judgment record (Phase 5) — a reasoning artifact, deliberately NOT built
**Date:** 2026-07-11

> Competency #15: knowing when each approach is the WRONG tool is the skill. This
> records, for Baraat specifically, which technique fits where — and why we did not
> reach for the others.

## The four techniques, one line each
- **RAG** — fetch relevant text at query time, answer grounded in it.
- **In-context learning (ICL)** — put instructions/examples in the prompt; the model
  adapts per-call, weights unchanged.
- **Fine-tuning** — train the model's weights on labeled examples to bake in a behavior.
- **Distillation** — train a smaller model to imitate a bigger one (cheaper inference).

## What Baraat actually uses, and why

**RAG — the core. Correct choice.**
Baraat's job is due diligence over vendor facts that (a) change (prices go stale — ADR
0002), (b) must be **attributable** ("per this listing…"), and (c) live in a small,
editable corpus. RAG fits all three: add/edit a vendor doc and the system is instantly
up to date, and every answer can cite its source. **Fine-tuning would be the wrong tool
here** — it bakes facts into weights, so a price change means retraining, and there's no
attribution. Retrieval evals (recall@k) also let us *measure* the fact layer directly.

**ICL — for the small, stable behaviors. Correct choice.**
Extraction (fill the schema), tool argument selection, the LLM-judge rubric, and the
answer style are all steered by **instructions + a couple of examples in the prompt**.
These behaviors are small and stable, and ICL needs zero training data and zero training
infra. When we found the clean-control gap, the fix was a one-line prompt change (ICL) —
minutes, not a training run.

## What we deliberately did NOT do, and when it WOULD be right

**Fine-tuning — wrong for Baraat now.** Reasons: the corpus is ~35 docs (nowhere near
the thousands of labeled examples fine-tuning wants); facts change (weights would go
stale); we need attribution (weights give none). It would become the *right* tool only
if we had a **narrow, stable, high-volume behavior with lots of labels** — e.g. a
dedicated "red-flag severity" classifier trained on thousands of human-labeled reviews
(cf. the F4 over-eager-red-flag problem). Even then, only the classifier — never the
vendor facts.

**Distillation — wrong for Baraat now, but adjacent to routing.** Distillation makes
sense once you have (a) real traffic and (b) a strong model's outputs to imitate. Today
we have neither. It becomes interesting as the *next step after routing* (ADR 0003): if
the 8b model turns out to under-perform on some category, we could distill the 70b's
behavior on that category into a small fast model — getting 70b-ish quality at 8b cost.
That needs a labeled/curated set (which our golden set + judge could help generate) and
enough volume to justify the effort. Deferred, with a clear trigger.

## The one-paragraph judgment
For a small, changing, attribution-required fact base, **RAG + ICL is right and
fine-tuning is wrong** — you'd be training away the very properties (freshness,
citability, editability) the product needs. Fine-tuning/distillation earn their place
only for a *narrow, stable, high-volume behavior with labels* — a red-flag classifier or
a distilled router — never for the facts themselves. Reaching for fine-tuning first here
would be the classic wrong-tool mistake.
