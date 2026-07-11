"""Answer-quality eval: generate an answer for each golden question, judge it, report.

  python -m src.evals.answer_eval

For each golden question:
  1. generate an answer (retrieve -> compose)   [answer stage]
  2. judge it vs the expected answer            [LLM-as-judge]
Then aggregate: mean score + verdict counts. Saves a JSON to evals/results/.

Crash-resilient (Groq free-tier hits rate limits on long runs): each question is
retried with backoff, partial results are written after every question, and a
per-question failure is recorded as an 'error' row rather than killing the run.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from ..answer.generator import AnswerGenerator
from .llm_judge import judge_answer
from ..extraction.config import GROQ_API_KEY, GROQ_BASE_URL
from ..extraction.model_backend import GroqBackend, ModelError

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "data" / "golden_set" / "golden_set.json"
RESULTS = REPO / "evals" / "results"
PARTIAL = RESULTS / "answer_eval_partial.json"   # overwritten as we go (crash-safe)
MODEL = "llama-3.3-70b-versatile"
PACE_S = 5.0            # gap between questions to ease the TPM limit
MAX_Q_RETRIES = 3       # per-question retries on rate-limit


def _aggregate(rows):
    scored = [r for r in rows if r["verdict"] != "error"]
    mean = round(sum(r["score"] for r in scored) / len(scored), 3) if scored else 0.0
    counts = {v: sum(1 for r in rows if r["verdict"] == v)
              for v in ("correct", "partial", "incorrect", "error")}
    return mean, counts


def _write(path, rows):
    mean, counts = _aggregate(rows)
    path.write_text(json.dumps(
        {"model": MODEL, "mean_score": mean, "verdict_counts": counts, "rows": rows},
        indent=2, ensure_ascii=False))
    return mean, counts


def _answer_and_judge(gen, backend, q):
    """One question with backoff retries on rate-limit; raises if all fail."""
    for attempt in range(MAX_Q_RETRIES):
        try:
            answer, used = gen.answer(q["question"])
            verdict = judge_answer(q["question"], q["expected_answer"], answer, backend)
            return answer, used, verdict
        except ModelError as e:
            if attempt == MAX_Q_RETRIES - 1:
                raise
            wait = 30 * (attempt + 1)
            print(f"     rate-limited ({e}); waiting {wait}s then retrying...")
            time.sleep(wait)


def main():
    if not GROQ_API_KEY:
        raise SystemExit("No GROQ_API_KEY found. Set it in .env or the environment.")
    questions = json.loads(GOLDEN.read_text())
    backend = GroqBackend(GROQ_API_KEY, GROQ_BASE_URL, MODEL)
    gen = AnswerGenerator(backend)
    RESULTS.mkdir(parents=True, exist_ok=True)

    rows = []
    for q in questions:
        try:
            answer, used, verdict = _answer_and_judge(gen, backend, q)
        except ModelError as e:
            answer, used = "(error)", []
            verdict = {"verdict": "error", "score": 0.0, "reasoning": f"rate limit: {e}"}
        rows.append({
            "id": q["id"], "behavior": q["behavior"], "question": q["question"],
            "expected": q["expected_answer"], "answer": answer.strip(),
            "used_vendors": used, "verdict": verdict["verdict"],
            "score": verdict["score"], "reasoning": verdict["reasoning"],
        })
        _write(PARTIAL, rows)   # crash-safe incremental save
        print(f"{q['id']}  {verdict['verdict']:<9} ({verdict['score']}) — {q['question'][:55]}")
        print(f"     judge: {verdict['reasoning']}")
        time.sleep(PACE_S)

    mean, counts = _aggregate(rows)
    print(f"\n=== ANSWER-QUALITY EVAL ===")
    print(f"mean score = {mean}  ({counts['correct']} correct, {counts['partial']} partial, "
          f"{counts['incorrect']} incorrect, {counts['error']} error of {len(rows)})")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = RESULTS / f"answer_eval_{ts}.json"
    _write(out, rows)
    print(f"saved -> {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
