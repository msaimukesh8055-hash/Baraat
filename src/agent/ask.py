"""Ask the real agent a natural-language question.

  python -m src.agent.ask "I have 15 lakh. Split it, ~40% venue, and check an 80%-upfront contract."
  python -m src.agent.ask "Compare Grand Thali Caterers and Grand Thali Events & Catering."

The agent (LLMPolicy on Groq/Llama) decides which tools to call; the same four
guardrails from the scripted demo wrap it. A step-by-step trace is printed so you can
SEE the agent choosing tools, then the final answer.
"""
import argparse

from .orchestrator import Agent
from .llm_policy import LLMPolicy
from ..extraction.config import GROQ_API_KEY, GROQ_BASE_URL
from ..extraction.model_backend import GroqBackend, ModelError
from ..tools import (
    budget_allocator,
    contract_risk_checker,
    payment_schedule_validator,
    vendor_comparator,
)

TOOLS = {
    "budget_allocator": budget_allocator,
    "payment_schedule_validator": payment_schedule_validator,
    "contract_risk_checker": contract_risk_checker,
    "vendor_comparator": vendor_comparator,
}

# The agent uses a stronger/instruction-following open model for tool selection.
AGENT_MODEL = "llama-3.3-70b-versatile"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--model", default=AGENT_MODEL)
    args = ap.parse_args()

    if not GROQ_API_KEY:
        raise SystemExit("No GROQ_API_KEY found. Set it in .env or the environment.")

    backend = GroqBackend(GROQ_API_KEY, GROQ_BASE_URL, args.model)
    agent = Agent(TOOLS, LLMPolicy(backend))

    print(f"\nQ: {args.question}\n")
    try:
        result = agent.run(args.question)
    except ModelError as e:
        raise SystemExit(f"Model error: {e}")

    # Step-by-step trace of what the agent decided.
    for i, step in enumerate(result.steps, 1):
        env = step.result or {}
        status = "ok" if env.get("ok") else f"FAILED @ {env.get('stage')}"
        print(f"  step {i}: called {step.action.name}({step.action.args}) -> {status}")
        if not env.get("ok"):
            print(f"           errors: {env.get('errors')}")

    print(f"\n[stop_reason={result.stop_reason}  tool_calls={result.tool_calls}]")
    print("\nANSWER:\n" + result.answer + "\n")


if __name__ == "__main__":
    main()
