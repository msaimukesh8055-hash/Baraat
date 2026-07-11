"""Model routing + fallback (#9) — send each request to the right-sized model.

Idea: not every request needs the big model. Simple factual lookups go to the small,
cheap, fast model (8b); requests that need real reasoning (contract risk, budgeting,
comparison) go to the strong model (70b). This trades a little accuracy on hard tasks
for big cost/latency wins on easy ones.

The classifier is a transparent keyword heuristic (auditable, zero-cost, no extra LLM
call just to route). A fallback cascade means if the chosen model errors or times out,
we automatically try the next one — degrade, don't die (same spirit as Phase 2
guardrails).
"""
import re
from dataclasses import dataclass

SMALL = "llama-3.1-8b-instant"
LARGE = "llama-3.3-70b-versatile"

# request patterns that need the STRONG model (reasoning, tools, multi-vendor)
_COMPLEX = [
    ("contract_analysis", [r"\bcontract\b", r"\brisky?\b", r"\bclause\b",
                            r"payment (schedule|plan)", r"\bupfront\b", r"\brefund\b"]),
    ("budget_planning",   [r"\bbudget\b", r"\ballocat", r"\bsplit\b.{0,20}(budget|lakh|money|across)"]),
    ("comparison",        [r"\bcompare\b", r"\bcheaper\b", r"\bbetter\b", r"\bvs\.?\b",
                           r"more expensive", r"which (one|is)"]),
]


@dataclass
class Route:
    task_type: str
    model: str
    reason: str


def classify(request: str) -> Route:
    low = request.lower()
    for task_type, patterns in _COMPLEX:
        if any(re.search(p, low) for p in patterns):
            return Route(task_type, LARGE, f"{task_type} needs reasoning -> large model")
    return Route("simple_lookup", SMALL, "factual lookup/retrieval -> small model")


class Router:
    """Routes to a model by request type, with a fallback cascade on failure."""

    def __init__(self, backends: dict):
        # backends: {model_name: backend_with_.complete()}
        self.backends = backends

    def route(self, request: str) -> Route:
        return classify(request)

    def complete(self, request: str, messages, fallback: bool = True):
        r = classify(request)
        order = [r.model]
        if fallback:
            order += [m for m in self.backends if m != r.model]

        errors = []
        for model in order:
            backend = self.backends.get(model)
            if backend is None:
                continue
            try:
                out = backend.complete(messages)
                return {
                    "task_type": r.task_type,
                    "routed_to": r.model,
                    "model_used": model,
                    "fell_back": model != r.model,
                    "output": out,
                }
            except Exception as e:  # noqa: BLE001 - fallback catches any backend failure
                errors.append(f"{model}: {e}")
        raise RuntimeError(f"all models failed: {errors}")
