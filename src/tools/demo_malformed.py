"""Deliberate malformed-OUTPUT demo — the tool-layer analog of Phase 1's F3.

Real tools here are deterministic and correct, so they never emit malformed output.
To prove the OUTPUT gate + the bounded repair loop actually work, we use FIXTURE
tools that emit bad output on purpose (same idea as extraction's MockBackend).

Three cases mirror F3's valid / repaired / fallback trichotomy, but for tool OUTPUT:
  1. broken, no repair method   -> caught at output_validation (garbage NOT passed on)
  2. flaky, repair fixes it      -> repaired then accepted
  3. unfixable, repair no help   -> bounded repairs give up -> caught failure (no hang)

Run: python -m src.tools.demo_malformed
"""
import json

from . import base

# A tiny shared contract: input {x: number}, output {doubled: number}.
_CONTRACT = {
    "name": "double_it",
    "description": "fixture tool: return x doubled",
    "input_schema": {
        "type": "object", "additionalProperties": False, "required": ["x"],
        "properties": {"x": {"type": "number"}},
    },
    "output_schema": {
        "type": "object", "additionalProperties": False, "required": ["doubled"],
        "properties": {"doubled": {"type": "number"}},
    },
}


class BrokenTool:
    """Returns a STRING where the schema requires a number, and has no repair."""
    CONTRACT = _CONTRACT

    def run(self, args):
        return {"doubled": str(args["x"] * 2)}   # malformed: string, not number


class FlakyTool:
    """Emits malformed output first, but can fix itself when asked."""
    CONTRACT = _CONTRACT

    def run(self, args):
        return {"doubled": str(args["x"] * 2)}   # malformed on first produce

    def repair_output(self, args, prev, errors):
        return {"doubled": float(prev["doubled"])}   # coerce back to number -> valid


class UnfixableTool:
    """Always malformed; its 'repair' never actually fixes it (bounded-loop test)."""
    CONTRACT = _CONTRACT

    def run(self, args):
        return {"doubled": "nope"}

    def repair_output(self, args, prev, errors):
        return {"doubled": "still nope"}   # never becomes a number


def _show(title, env):
    status = "OK" if env["ok"] else f"CAUGHT @ {env['stage']}"
    print(f"--- {title}: {status}  (repairs={env.get('repairs', 0)}) ---")
    for e in env["errors"]:
        print("   error:", e)
    if env["ok"]:
        print("  ", json.dumps(env["output"], ensure_ascii=False))
    print()


def main():
    _show("1. broken tool, no repair", base.execute_tool(BrokenTool(), {"x": 5}))
    _show("2. flaky tool, repair fixes it", base.execute_tool(FlakyTool(), {"x": 5}))
    _show("3. unfixable tool, bounded repairs give up", base.execute_tool(UnfixableTool(), {"x": 5}))


if __name__ == "__main__":
    main()
