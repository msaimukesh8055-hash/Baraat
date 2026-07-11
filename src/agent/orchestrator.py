"""The agent orchestrator — an explicit loop WE own, with the four guardrails.

Competency #8. We deliberately wrote the loop ourselves (rather than using a
provider's hidden function-calling loop) so the guardrails are visible, testable
code:

  1. LOOP BUDGET        - max iterations of think->act (stops infinite loops)
  2. TOOL BUDGET        - max total tool calls (stops over-calling)
  3. STOP CONDITION     - the policy must emit a `finish` action to end
  4. DEGRADED FALLBACK  - on budget exhaustion / repeated failure, return a partial
                          honest answer instead of crashing or hanging
  (+ REPEAT DETECTION   - same tool + same args twice in a row = no progress -> stop)

The agent's "brain" is a pluggable **policy**: a callable
    policy(request, history, tools) -> Action
so the guardrails can be proven deterministically with a scripted policy, and a real
LLM policy can be dropped in unchanged.
"""
from dataclasses import dataclass, field
import json

from ..tools.base import execute_tool
from ..observability.tracer import NullTracer

LOOP_BUDGET = 6   # max think->act iterations
TOOL_BUDGET = 5   # max tool invocations per request


@dataclass
class Action:
    """What the policy decides to do next."""
    type: str                       # "tool" or "finish"
    name: str | None = None         # tool name (for type == "tool")
    args: dict = field(default_factory=dict)
    answer: str | None = None       # final text (for type == "finish")


@dataclass
class Step:
    action: Action
    result: dict | None = None      # the tool envelope from execute_tool


@dataclass
class AgentResult:
    ok: bool                        # did we reach a clean finish?
    answer: str
    stop_reason: str                # "finished" | "loop_budget" | "tool_budget" |
                                    # "no_progress"
    steps: list = field(default_factory=list)
    tool_calls: int = 0


class Agent:
    def __init__(self, tools: dict, policy, loop_budget=LOOP_BUDGET,
                 tool_budget=TOOL_BUDGET, tracer=None):
        self.tools = tools                    # name -> tool module
        self.policy = policy
        self.loop_budget = loop_budget
        self.tool_budget = tool_budget
        self.tracer = tracer or NullTracer()  # no-op unless a real tracer is passed

    def run(self, request: str) -> AgentResult:
        steps: list[Step] = []
        tool_calls = 0
        last_signature = None

        for _ in range(self.loop_budget):
            # The LLM decision. The wrapped backend records the llm.* span inside.
            with self.tracer.span("decide", kind="decide"):
                action = self.policy(request, steps, self.tools)

            # STOP CONDITION: the policy says it's done.
            if action.type == "finish":
                return AgentResult(True, action.answer or self._summarize(steps),
                                   "finished", steps, tool_calls)

            # From here it's a tool action.
            signature = (action.name, json.dumps(action.args, sort_keys=True))

            # REPEAT DETECTION: identical call twice in a row = no progress.
            if signature == last_signature:
                return self._degrade(steps, tool_calls, "no_progress",
                                     f"stopped: agent repeated the same call to "
                                     f"'{action.name}' with no progress")

            # TOOL BUDGET: refuse to exceed the cap.
            if tool_calls >= self.tool_budget:
                return self._degrade(steps, tool_calls, "tool_budget",
                                     f"stopped: tool budget of {self.tool_budget} calls reached")

            # Execute (the tool contract validates in/out; a bad call is a caught
            # error envelope, never a crash). Recorded as a tool span.
            tool = self.tools.get(action.name)
            with self.tracer.span(f"tool.{action.name}", kind="tool") as sp:
                if tool is None:
                    env = {"tool": action.name, "ok": False, "stage": "unknown_tool",
                           "output": None, "errors": [f"no such tool: {action.name!r}"]}
                else:
                    env = execute_tool(tool, action.args)
                sp.set(ok=env["ok"], stage=env["stage"])

            tool_calls += 1
            steps.append(Step(action, env))
            last_signature = signature

        # LOOP BUDGET exhausted without a finish.
        return self._degrade(steps, tool_calls, "loop_budget",
                             f"stopped: loop budget of {self.loop_budget} steps reached "
                             f"without the agent finishing")

    # --- degraded fallback: never crash/hang; return what we DID accomplish ---
    def _degrade(self, steps, tool_calls, reason, note) -> AgentResult:
        partial = self._summarize(steps)
        answer = (f"{note}. Partial results:\n{partial}" if partial
                  else f"{note}. No usable results were produced.")
        return AgentResult(False, answer, reason, steps, tool_calls)

    @staticmethod
    def _summarize(steps) -> str:
        lines = []
        for s in steps:
            env = s.result or {}
            if env.get("ok"):
                lines.append(f"- {s.action.name}: {json.dumps(env['output'], ensure_ascii=False)}")
            else:
                lines.append(f"- {s.action.name}: (failed @ {env.get('stage')}: {env.get('errors')})")
        return "\n".join(lines)
