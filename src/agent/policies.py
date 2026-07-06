"""Agent policies — the pluggable "brain" that picks the next Action.

A policy is any callable: policy(request, steps, tools) -> Action.

ScriptedPolicy plays a fixed list of actions. Just like Phase 1 used a MockBackend
to *deterministically* exercise the repair/fallback loop, we use a scripted policy to
deterministically exercise the guardrails — including making the agent misbehave on
purpose (repeat a call, or never finish) so we can show the guardrails catching it.

A real LLM policy (format tools + request + history, ask the model for the next
action as JSON, parse it) drops in here unchanged — the orchestrator and guardrails
don't care where the Action comes from.
"""
from .orchestrator import Action


class ScriptedPolicy:
    """Emits a predetermined sequence of actions; defaults to `finish` when spent."""

    def __init__(self, actions: list[Action]):
        self.actions = list(actions)
        self.i = 0

    def __call__(self, request, steps, tools) -> Action:
        if self.i < len(self.actions):
            a = self.actions[self.i]
            self.i += 1
            return a
        return Action("finish", answer="(policy exhausted)")
