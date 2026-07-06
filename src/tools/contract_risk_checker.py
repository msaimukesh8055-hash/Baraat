"""contract_risk_checker — scan contract text for risky clauses.

Heuristic (regex/keyword) pattern matching. Deliberately NOT an LLM: a transparent,
auditable rule set is a better first artifact, and its **false negatives** (a real
risk phrased unusually and therefore missed) are exactly the failure mode we want to
expose and measure. Each fired flag quotes the evidence span (attribution).

overall_risk = the highest severity among the fired flags (low if none fired).
"""
import re

from .contracts import CONTRACT_RISK_CHECKER as CONTRACT  # noqa: F401

_SEV_RANK = {"low": 0, "medium": 1, "high": 2}


def _window(text: str, start: int, end: int, pad: int = 40) -> str:
    a = max(0, start - pad)
    b = min(len(text), end + pad)
    return text[a:b].strip().replace("\n", " ")


def validate_args(args: dict) -> list[str]:
    if not args["contract_text"].strip():
        return ["contract_text is empty / whitespace only"]
    return []


def run(args: dict) -> dict:
    text = args["contract_text"]
    low = text.lower()
    flags = []

    # 1. Large upfront / advance payment (>50% or full advance)
    m = re.search(r"(\d{1,3})\s*%\s*(?:advance|upfront|in advance|on booking|on signing)", low)
    if m and int(m.group(1)) > 50:
        flags.append({"pattern": "large_upfront_payment", "severity": "high",
                      "evidence": _window(text, m.start(), m.end())})
    elif re.search(r"(?:full|100%|entire)\s+(?:payment|amount)?\s*(?:in advance|upfront|advance)", low):
        m2 = re.search(r"(?:full|100%|entire)[^.]{0,40}(?:advance|upfront)", low)
        flags.append({"pattern": "full_advance_payment", "severity": "high",
                      "evidence": _window(text, m2.start(), m2.end()) if m2 else "full advance payment"})

    # 2. No cancellation clause (absence -> can't quote a span)
    if "cancel" not in low:
        flags.append({"pattern": "no_cancellation_clause", "severity": "medium",
                      "evidence": "(no mention of 'cancellation' found in the contract text)"})

    # 3. No refund policy (absence)
    if "refund" not in low:
        flags.append({"pattern": "no_refund_policy", "severity": "medium",
                      "evidence": "(no mention of 'refund' found in the contract text)"})

    # 4. Vague delivery timeline
    vague = re.search(r"\b(approximately|around|roughly|tentativ\w*|as soon as possible|asap|to be decided|tbd)\b", low)
    if vague:
        flags.append({"pattern": "vague_delivery_timeline", "severity": "medium",
                      "evidence": _window(text, vague.start(), vague.end())})

    # 5. Verbal-only amendments
    verbal = re.search(r"\b(verbal\w*|orally|over the phone)\b", low)
    if verbal:
        flags.append({"pattern": "verbal_amendments", "severity": "low",
                      "evidence": _window(text, verbal.start(), verbal.end())})

    overall = "low"
    if flags:
        overall = max(flags, key=lambda f: _SEV_RANK[f["severity"]])["severity"]

    return {"overall_risk": overall, "risk_flags": flags}
