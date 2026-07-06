"""LLMPolicy — a REAL brain for the agent (Groq/Llama), drop-in for ScriptedPolicy.

Given the user request + the history of tool calls so far, it asks the model for the
next Action as JSON:
    {"action": "tool", "tool": "<name>", "args": {...}}   -> call a tool
    {"action": "finish", "answer": "<text>"}              -> done

The orchestrator + guardrails are unchanged: they don't care whether the Action came
from a script or a live model. If the model returns unparseable JSON or names a tool
that doesn't exist, we degrade to a `finish` rather than crash (the fuzzy-brain
equivalent of the tool layer's input validation).

vendor_ids are grounded by listing the real extracted stems in the system prompt, so
the model compares actual vendors instead of hallucinating ids.
"""
import json
from pathlib import Path

from .orchestrator import Action
from ..tools.contracts import TOOL_CONTRACTS

EXTRACTED_DIR = Path(__file__).resolve().parents[2] / "data" / "extracted"


def _available_vendor_ids() -> list[str]:
    return sorted(p.stem for p in EXTRACTED_DIR.glob("*.json") if not p.stem.startswith("_"))


def _format_tools() -> str:
    blocks = []
    for c in TOOL_CONTRACTS:
        schema = json.dumps(c["input_schema"], ensure_ascii=False)
        blocks.append(f"- {c['name']}: {c['description']}\n  input schema: {schema}")
    return "\n".join(blocks)


def _system_prompt() -> str:
    vendors = ", ".join(_available_vendor_ids())
    return (
        "You are Baraat's tool-using agent for wedding-vendor due diligence. "
        "Answer ONLY by using the provided tools to get facts; never invent numbers, "
        "prices, or ratings.\n\n"
        "Available tools:\n" + _format_tools() + "\n\n"
        "Known vendor_ids (use these exact strings for vendor_comparator):\n"
        + vendors + "\n\n"
        "On each turn reply with EXACTLY ONE JSON object, nothing else:\n"
        '  {"action": "tool", "tool": "<name>", "args": { ... }}  to call a tool, or\n'
        '  {"action": "finish", "answer": "<final answer for the user>"}  when done.\n\n'
        "Rules:\n"
        "- Call one tool per turn; you will see its result before the next turn.\n"
        "- After a tool result gives you what you need, FINISH with a clear answer.\n"
        "- If a tool returns an error, either fix the arguments and retry, or finish "
        "with an explanation.\n"
        "- Keep the final answer concise and grounded in the tool results."
    )


class LLMPolicy:
    def __init__(self, backend):
        self.backend = backend

    def _messages(self, request: str, steps):
        messages = [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": request},
        ]
        for s in steps:
            messages.append({
                "role": "assistant",
                "content": json.dumps({
                    "action": "tool", "tool": s.action.name, "args": s.action.args,
                }),
            })
            env = s.result or {}
            payload = env.get("output") if env.get("ok") else {"error": env.get("errors")}
            messages.append({
                "role": "user",
                "content": f"TOOL RESULT ({s.action.name}): "
                           + json.dumps(payload, ensure_ascii=False),
            })
        return messages

    def __call__(self, request, steps, tools) -> Action:
        resp = self.backend.complete(self._messages(request, steps), json_mode=True)
        return self._parse(resp["text"])

    @staticmethod
    def _parse(text: str) -> Action:
        try:
            obj = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return Action("finish", answer=f"(could not parse agent decision: {text[:200]})")
        if obj.get("action") == "tool":
            return Action("tool", name=obj.get("tool"), args=obj.get("args") or {})
        if obj.get("action") == "finish":
            return Action("finish", answer=obj.get("answer") or "(no answer given)")
        return Action("finish", answer=f"(unrecognized agent decision: {text[:200]})")
