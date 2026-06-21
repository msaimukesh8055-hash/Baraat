"""Deterministic proof of the validate -> repair -> fallback loop, with NO API key.

This is the "break it on purpose" artifact for competency #7. We script three
model behaviours and show the loop handling each:

  CASE 1: clean valid JSON           -> accepted first try
  CASE 2: invalid then corrected     -> repaired, then accepted
  CASE 3: invalid every time         -> falls back to needs_human_review

Run: python -m src.extraction.demo_mock
"""
import json

from .extractor import extract_one
from .model_backend import MockBackend

DOC = "Demo Caterer — Jaipur. Veg package ₹1,200 per plate. +91 90000 00000. Rating 4.5 (100 reviews)."

VALID = {
    "vendor_id": "caterer_demo", "name": "Demo Caterer", "category": "caterer",
    "location": "Jaipur", "price_range_inr": {"min": 1200, "max": 1200},
    "price_unit": "per_plate", "price_last_verified": None, "price_confidence": "high",
    "contact": {"phone": "+91 90000 00000", "email": None}, "gst_number": None,
    "rating": 4.5, "review_count": 100, "red_flags": [],
    "source_file": "caterer_demo.md", "needs_human_review": False, "extraction_notes": None,
}

# Same as VALID but with two planted errors: rating out of range, wrong price_unit.
BROKEN = dict(VALID, rating=7.5, price_unit="per_day")


def run_case(title, scripted):
    print(f"\n=== {title} ===")
    backend = MockBackend(scripted)
    rec, trace = extract_one(DOC, "caterer_demo", "caterer_demo.md", backend, max_repairs=2)
    for a in trace["attempts"]:
        print(f"  attempt {a['n']}: errors={a['errors'] if a['errors'] else 'NONE (valid)'}")
    print(f"  FINAL STATUS: {trace['status']}")
    print(f"  needs_human_review={rec['needs_human_review']}")
    return trace["status"]


def main():
    s1 = run_case("CASE 1: valid first try", [json.dumps(VALID)])
    s2 = run_case("CASE 2: broken -> repaired", [json.dumps(BROKEN), json.dumps(VALID)])
    s3 = run_case("CASE 3: broken every time -> fallback",
                  [json.dumps(BROKEN), json.dumps(BROKEN), json.dumps(BROKEN)])

    assert s1 == "ok_first_try", s1
    assert s2 == "ok_after_repair", s2
    assert s3 == "fallback_human_review", s3
    print("\nAll three reliability paths behaved as expected. ✅")


if __name__ == "__main__":
    main()
