"""Reproducible demo of the three self-contained tools + their validation gates.

Run: python -m src.tools.demo

Shows, for each tool, a happy path AND deliberately-bad inputs being blocked at the
right stage (input schema, cross-field rule, or output rule). This is the visible
proof that the tool contracts (Phase 2 step 1) are enforced (step 2).
"""
import json

from . import base, budget_allocator, payment_schedule_validator
from . import contract_risk_checker as crc


def _show(title, env):
    status = "OK" if env["ok"] else f"BLOCKED @ {env['stage']}"
    print(f"--- {title}: {status} ---")
    for e in env["errors"]:
        print("   error:", e)
    if env["ok"] and env["output"] is not None:
        print("  ", json.dumps(env["output"], ensure_ascii=False))
    print()


def main():
    # budget_allocator
    _show("budget: happy path", base.execute_tool(budget_allocator, {
        "total_budget_inr": 1500000,
        "weights": {"venue": 0.4, "caterer": 0.3, "photographer": 0.15,
                    "decorator": 0.1, "makeup_artist": 0.05}}))
    _show("budget: negative budget", base.execute_tool(budget_allocator, {
        "total_budget_inr": -500, "weights": {"venue": 1}}))
    _show("budget: unknown category", base.execute_tool(budget_allocator, {
        "total_budget_inr": 100000, "weights": {"flowers": 1}}))
    _show("budget: all-zero weights", base.execute_tool(budget_allocator, {
        "total_budget_inr": 100000, "weights": {"venue": 0, "caterer": 0}}))

    # payment_schedule_validator
    _show("payment: clean 30/40/30", base.execute_tool(payment_schedule_validator, {
        "installments": [{"percent": 30, "due": "on booking"},
                         {"percent": 40, "due": "1 month before"},
                         {"percent": 30, "due": "event day"}]}))
    _show("payment: high upfront 70/30", base.execute_tool(payment_schedule_validator, {
        "installments": [{"percent": 70, "due": "on booking"},
                         {"percent": 30, "due": "event day"}]}))
    _show("payment: doesn't sum to 100", base.execute_tool(payment_schedule_validator, {
        "installments": [{"percent": 50, "due": "on booking"},
                         {"percent": 40, "due": "event day"}]}))
    _show("payment: 120% instalment", base.execute_tool(payment_schedule_validator, {
        "installments": [{"percent": 120, "due": "on booking"}]}))

    # contract_risk_checker
    risky = ("Client shall pay 80% advance on booking. Delivery of the wedding album "
             "will happen approximately after the event. Any changes to this agreement "
             "may be made verbally.")
    safe = ("A 25% booking amount is due on signing, 50% one month prior, and the "
            "remaining 25% on the event day. Cancellations up to 60 days before the "
            "event receive a full refund. Final album delivered within 45 days.")
    _show("contract: risky text", base.execute_tool(crc, {"contract_text": risky}))
    _show("contract: safe text", base.execute_tool(crc, {"contract_text": safe}))
    _show("contract: empty", base.execute_tool(crc, {"contract_text": "   "}))


if __name__ == "__main__":
    main()
