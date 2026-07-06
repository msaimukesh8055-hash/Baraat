"""Deterministic demo of the agent + all four guardrails.

Run: python -m src.agent.demo_agent

Four scenarios:
  A. Good path        -> stop condition (finish) reached cleanly
  B. Runaway loop     -> repeat-detection guardrail (no_progress)
  C. Tool budget hit  -> degraded fallback (partial answer, not a crash)
  D. Loop budget hit  -> degraded fallback (partial answer, not a crash)
"""
from .orchestrator import Action, Agent
from .policies import ScriptedPolicy
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


def _print(title, result):
    print(f"\n================ {title} ================")
    print(f"ok={result.ok}  stop_reason={result.stop_reason}  tool_calls={result.tool_calls}")
    print("answer:")
    print(result.answer)


def scenario_good():
    policy = ScriptedPolicy([
        Action("tool", "budget_allocator", {
            "total_budget_inr": 1500000,
            "weights": {"venue": 0.4, "caterer": 0.3, "photographer": 0.3}}),
        Action("tool", "contract_risk_checker", {
            "contract_text": "Client pays 80% advance on booking. Delivery approximately after the event."}),
        Action("finish", answer="Budget split done; the contract is HIGH risk (80% upfront, vague delivery)."),
    ])
    return Agent(TOOLS, policy).run("Split my 15L budget and check this contract.")


def scenario_runaway_loop():
    # The agent calls the SAME tool with the SAME args twice -> no progress.
    repeated = Action("tool", "vendor_comparator", {
        "vendor_ids": ["caterer_grandthali_caterers", "caterer_grandthali_events"]})
    policy = ScriptedPolicy([repeated, repeated])
    return Agent(TOOLS, policy).run("Compare these two caterers.")


def _six_distinct_calls():
    return [
        Action("tool", "budget_allocator",
               {"total_budget_inr": n, "weights": {"venue": 1}})
        for n in (100000, 200000, 300000, 400000, 500000, 600000)
    ]


def scenario_tool_budget():
    # Six distinct valid calls, never finishing -> tool budget (5) bites first.
    policy = ScriptedPolicy(_six_distinct_calls())
    return Agent(TOOLS, policy).run("(agent that keeps calling tools)")


def scenario_loop_budget():
    # Raise tool budget so the LOOP budget (4) is the one that bites.
    policy = ScriptedPolicy(_six_distinct_calls())
    return Agent(TOOLS, policy, loop_budget=4, tool_budget=10).run("(agent that never finishes)")


def main():
    _print("A. GOOD PATH (stop condition)", scenario_good())
    _print("B. RUNAWAY LOOP (repeat detection)", scenario_runaway_loop())
    _print("C. TOOL BUDGET (degraded fallback)", scenario_tool_budget())
    _print("D. LOOP BUDGET (degraded fallback)", scenario_loop_budget())


if __name__ == "__main__":
    main()
