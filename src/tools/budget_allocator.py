"""budget_allocator — split a total budget across categories by weights.

A calculator with constraints. The interesting engineering detail: to guarantee the
allocations sum EXACTLY to the total (no rounding drift), the last category absorbs
the remainder instead of being rounded independently. That's why we also have an
output-validation rule checking the sum — belt and suspenders.
"""
from .contracts import BUDGET_ALLOCATOR as CONTRACT, CATEGORIES  # noqa: F401 (re-exported)


def validate_args(args: dict) -> list[str]:
    errors = []
    weights = args["weights"]
    for k in weights:
        if k not in CATEGORIES:
            errors.append(f"unknown category in weights: {k!r} (allowed: {CATEGORIES})")
    if sum(weights.values()) <= 0:
        errors.append("weights must include at least one positive value (cannot normalize all-zero)")
    return errors


def run(args: dict) -> dict:
    total = args["total_budget_inr"]
    weights = args["weights"]
    wsum = sum(weights.values())

    allocations = {}
    running = 0.0
    items = list(weights.items())
    for i, (cat, w) in enumerate(items):
        if i == len(items) - 1:
            amt = round(total - running, 2)      # last absorbs the remainder
        else:
            amt = round(total * w / wsum, 2)
            running += amt
        allocations[cat] = amt

    return {
        "allocations": allocations,
        "total_allocated_inr": round(sum(allocations.values()), 2),
        "notes": (
            f"Allocated Rs {total:,.0f} across {len(allocations)} categories by "
            f"normalized weights (weights summed to {wsum:g})."
        ),
    }


def validate_output(args: dict, output: dict) -> list[str]:
    errors = []
    total = args["total_budget_inr"]
    if abs(output["total_allocated_inr"] - total) > 1.0:
        errors.append(
            f"allocations sum to {output['total_allocated_inr']} but budget is {total}"
        )
    for cat, amt in output["allocations"].items():
        if amt < 0:
            errors.append(f"negative allocation for {cat}: {amt}")
    return errors
