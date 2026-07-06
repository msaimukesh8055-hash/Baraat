"""vendor_comparator — compare 2-3 vendors on price, rating, red flags.

The orchestration tool: unlike the other three (pure functions on their arguments),
this one PULLS DATA — price/rating/red-flags come from the extracted records
(Track B). This is the point where Phase 1's extraction finally gets *used*.

Failure modes we care about:
  - unknown vendor_id  -> bad-arg error (caught before doing work)
  - a vendor with missing/partial data -> a DEGRADED row, not a crash
It also becomes the natural stress case for the agent's loop/tool budgets, because
an agent could (wrongly) call it repeatedly.
"""
import json
from pathlib import Path

from .contracts import VENDOR_COMPARATOR as CONTRACT  # noqa: F401

EXTRACTED_DIR = Path(__file__).resolve().parents[2] / "data" / "extracted"


def _load_record(vendor_id: str):
    path = EXTRACTED_DIR / f"{vendor_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def validate_args(args: dict) -> list[str]:
    errors = []
    seen = set()
    for vid in args["vendor_ids"]:
        if vid in seen:
            errors.append(f"duplicate vendor_id: {vid!r}")
        seen.add(vid)
        if _load_record(vid) is None:
            errors.append(f"unknown vendor_id (no extracted record): {vid!r}")
    return errors


def run(args: dict) -> dict:
    rows = []
    for vid in args["vendor_ids"]:
        rec = _load_record(vid)
        # validate_args already guarantees rec exists; still guard defensively so a
        # partial record degrades to a usable row instead of raising.
        rows.append({
            "vendor_id": vid,
            "name": rec.get("name", vid),
            "price_range_inr": rec.get("price_range_inr", {"min": 0, "max": 0}),
            "rating": float(rec.get("rating", 0) or 0),
            "red_flag_count": len(rec.get("red_flags", []) or []),
            "price_confidence": rec.get("price_confidence", "unknown"),
        })

    # Simple, explainable recommendation: prefer fewer red flags, then higher rating,
    # then lower max price. (Transparent heuristic, not a black box.)
    best = min(rows, key=lambda r: (r["red_flag_count"], -r["rating"],
                                    r["price_range_inr"].get("max", 0)))
    reason = (f"{best['name']} — {best['red_flag_count']} red flag(s), "
              f"rating {best['rating']}, price up to Rs {best['price_range_inr'].get('max', 0):,.0f}.")

    return {"rows": rows, "recommendation": reason}
