"""Answer-quality eval: generate an answer for each golden question, judge it, report.

  python -m src.evals.answer_eval

For each golden question:
  1. generate an answer (retrieve -> compose)   [answer stage]
  2. judge it vs the expected answer            [LLM-as-judge]
Then aggregate: mean score + verdict counts. Saves a JSON to evals/results/.

This is metric #8 (answer correctness) end to end — the real SLA — distinct from the
recall@k retrieval metric we already had.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from ..answer.generator import AnswerGenerator
from .llm_judge import judge_answer
from ..extraction.config import GROQ_API_KEY, GROQ_BASE_URL
from ..extraction.model_backend import GroqBackend

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "data" / "golden_set" / "golden_set.json"
RESULTS = REPO / "evals" / "results"
MODEL = "llama-3.3-70b-versatile"


def main():
    if not GROQ_API_KEY:
        raise SystemExit("No GROQ_API_KEY found. Set it in .env or the environment.")
    questions = json.loads(GOLDEN.read_text())
    backend = GroqBackend(GROQ_API_KEY, GROQ_BASE_URL, MODEL)
    gen = AnswerGenerator(backend)

    rows = []
    for q in questions:
        answer, used = gen.answer(q["question"])
        verdict = judge_answer(q["question"], q["expected_answer"], answer, backend)
        rows.append({
            "id": q["id"], "behavior": q["behavior"], "question": q["question"],
            "expected": q["expected_answer"], "answer": answer.strip(),
            "used_vendors": used, "verdict": verdict["verdict"],
            "score": verdict["score"], "reasoning": verdict["reasoning"],
        })
        print(f"{q['id']}  {verdict['verdict']:<9} ({verdict['score']}) — {q['question'][:55]}")
        print(f"     judge: {verdict['reasoning']}")
        time.sleep(1.0)  # gentle pacing for the free-tier rate limit

    mean = round(sum(r["score"] for r in rows) / len(rows), 3)
    counts = {v: sum(1 for r in rows if r["verdict"] == v)
              for v in ("correct", "partial", "incorrect")}
    print(f"\n=== ANSWER-QUALITY EVAL ===")
    print(f"mean score = {mean}  ({counts['correct']} correct, "
          f"{counts['partial']} partial, {counts['incorrect']} incorrect of {len(rows)})")

    RESULTS.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = RESULTS / f"answer_eval_{ts}.json"
    out.write_text(json.dumps(
        {"model": MODEL, "mean_score": mean, "verdict_counts": counts, "rows": rows},
        indent=2, ensure_ascii=False))
    print(f"saved -> {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
