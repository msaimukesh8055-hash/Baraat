"""Tool execution wrapper — the reliability envelope for every tool call.

Competency #7 at the tool layer: a tool call is not "call the function." It is a
gated pipeline that validates on the way IN and on the way OUT, so a fuzzy agent
can never (a) run a tool on bad arguments or (b) hand a malformed result
downstream without it being caught.

    args ──► [1] input schema ──► [2] cross-field arg rules ──► [3] run ──►
             [4] output schema ──► [5] cross-field output rules ──► result

Any stage failing short-circuits with a structured error envelope (never an
exception bubbling up, never a silent bad value). The agent/repair layer reads
`ok` and `errors` to decide what to do next.

A "tool" here is any object exposing:
    CONTRACT           - the dict from contracts.py (has input/output schema)
    run(args) -> dict  - the actual logic (assumes args already validated)
    validate_args(args)   -> list[str]   (optional cross-field input checks)
    validate_output(args, output) -> list[str]  (optional cross-field output checks)
"""
from .validation import validate_against_schema


def _envelope(name, ok, output, stage, errors):
    return {"tool": name, "ok": ok, "stage": stage, "output": output, "errors": errors}


def execute_tool(tool, args: dict, max_output_repairs: int = 2) -> dict:
    contract = tool.CONTRACT
    name = contract["name"]

    # [1] input schema
    errs = validate_against_schema(args, contract["input_schema"])
    if errs:
        return _envelope(name, False, None, "input_validation", errs)

    # [2] cross-field argument rules (things a schema can't express)
    validate_args = getattr(tool, "validate_args", None)
    if validate_args:
        errs = validate_args(args)
        if errs:
            return _envelope(name, False, None, "input_validation", errs)

    # [3] run — an exception is a caught failure, not a crash
    try:
        output = tool.run(args)
    except Exception as e:  # pragma: no cover - defensive
        return _envelope(name, False, None, "run_error", [f"tool raised: {e!r}"])

    # [4]+[5] output schema + cross-field output rules, with a BOUNDED repair loop.
    # If a tool exposes repair_output(args, prev_output, errors) and its output is
    # malformed, we let it try to fix itself up to max_output_repairs times — the
    # tool-layer analog of the Phase 1 extraction repair loop. If it still can't
    # produce valid output, we return a caught failure (never pass garbage on).
    validate_output = getattr(tool, "validate_output", None)
    repair_output = getattr(tool, "repair_output", None)

    def _output_errors(out):
        e = validate_against_schema(out, contract["output_schema"])
        if validate_output:
            e = e + validate_output(args, out)
        return e

    errs = _output_errors(output)
    repairs = 0
    while errs and repair_output and repairs < max_output_repairs:
        output = repair_output(args, output, errs)
        repairs += 1
        errs = _output_errors(output)

    if errs:
        env = _envelope(name, False, output, "output_validation", errs)
        env["repairs"] = repairs
        return env

    env = _envelope(name, True, output, "ok", [])
    env["repairs"] = repairs
    return env
