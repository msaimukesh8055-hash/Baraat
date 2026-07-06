"""payment_schedule_validator — check a payment plan against red-flag heuristics.

The schema already guarantees each instalment percent is in [0, 100] (so a "120%"
instalment is rejected at the door as a bad argument). This tool adds the
cross-field / domain checks a schema can't express:
  - do the percentages actually sum to 100?
  - is too much money demanded upfront?
  - is it full prepayment?
"""
from .contracts import PAYMENT_SCHEDULE_VALIDATOR as CONTRACT  # noqa: F401

TOLERANCE = 0.01
_MILESTONE_KEYWORDS = ("event", "delivery", "completion", "final", "handover", "album")


def validate_args(args: dict) -> list[str]:
    # Schema covers per-field ranges + minItems; no extra cross-field precondition
    # is needed here (an empty schedule is already rejected by minItems: 1).
    return []


def run(args: dict) -> dict:
    installments = args["installments"]
    total = round(sum(i["percent"] for i in installments), 4)
    valid = abs(total - 100) <= TOLERANCE

    flags = []
    if not valid:
        flags.append(f"Instalment percentages sum to {total:g}%, not 100%.")

    first = installments[0]["percent"]
    if first > 50:
        flags.append(f"High upfront payment: first instalment is {first:g}% (>50%).")

    if len(installments) == 1 and abs(installments[0]["percent"] - 100) <= TOLERANCE:
        flags.append("Full prepayment: 100% due in a single instalment.")

    # How much is due BEFORE any milestone-tagged instalment (event/delivery/etc.)?
    # If a large majority is due before the vendor delivers, that's leverage risk.
    before_milestone = 0.0
    saw_milestone = False
    for inst in installments:
        due = (inst.get("due") or "").lower()
        if any(k in due for k in _MILESTONE_KEYWORDS):
            saw_milestone = True
            break
        before_milestone += inst["percent"]
    if saw_milestone and before_milestone > 75:
        flags.append(
            f"{before_milestone:g}% is due before the event/delivery milestone (>75%)."
        )

    return {"valid": valid, "total_percent": total, "risk_flags": flags}
