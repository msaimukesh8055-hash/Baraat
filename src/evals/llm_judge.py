"""LLM-as-judge — grades a free-text answer against a reference answer, by MEANING.

Metric #8 (answer correctness), the real SLA. Why an LLM and not string-match: a
correct answer can be phrased many ways ("₹2,10,000" vs "2.1 lakh"), so exact-match is
useless. The judge reads QUESTION + REFERENCE + ANSWER and returns a verdict + score +
one-line reasoning — like a teacher grading an essay against an answer key.

Kept honest by design (Phase 4 will calibrate it against human scoring): the judge is
itself an LLM and can be wrong, so we check its agreement with a human sample.
"""
import json

JUDGE_SYSTEM = (
    "You are a strict, fair grader for a wedding-vendor assistant. You are given a "
    "QUESTION, a REFERENCE ANSWER (ground truth), and an ASSISTANT ANSWER. Decide how "
    "well the assistant answer matches the reference, judging by MEANING, not wording.\n"
    "Grading:\n"
    "- 'correct' (score 1.0): captures the key facts of the reference; extra correct "
    "detail is fine.\n"
    "- 'partial' (score 0.5): partially right but missing a key fact or adds a minor "
    "wrong detail.\n"
    "- 'incorrect' (score 0.0): misses or contradicts the key facts, or says it doesn't "
    "know when the reference has an answer.\n"
    "Note: if the reference says a price is conflicting/stale and the assistant flags "
    "that too, that is 'correct'. Reply with ONLY a JSON object: "
    '{"verdict": "correct|partial|incorrect", "score": 1.0, "reasoning": "one sentence"}'
)


def judge_answer(question: str, reference: str, answer: str, backend) -> dict:
    user = (f"QUESTION:\n{question}\n\nREFERENCE ANSWER:\n{reference}\n\n"
            f"ASSISTANT ANSWER:\n{answer}\n\nGrade the assistant answer.")
    out = backend.complete(
        [{"role": "system", "content": JUDGE_SYSTEM},
         {"role": "user", "content": user}],
        json_mode=True,
    )
    try:
        obj = json.loads(out["text"])
        verdict = obj.get("verdict", "incorrect")
        score = float(obj.get("score", 0.0))
        reasoning = obj.get("reasoning", "")
    except (json.JSONDecodeError, TypeError, ValueError):
        verdict, score, reasoning = "incorrect", 0.0, f"judge parse error: {out['text'][:120]}"
    # keep verdict/score consistent
    score = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}.get(verdict, score)
    return {"verdict": verdict, "score": score, "reasoning": reasoning}
