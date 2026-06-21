"""Run extraction over the whole vendor corpus and write records + a run report.

Usage:
  python -m src.extraction.run_extraction              # real run via Groq
  python -m src.extraction.run_extraction --limit 3    # just the first 3 docs

Skips any file starting with '_' (the manifest and Phase-3 reserved docs) so the
answer key never gets extracted and the reserved docs stay untouched in Phase 1.
"""
import argparse
import json
import time
from pathlib import Path

from . import config
from .extractor import extract_one
from .model_backend import GroqBackend

VENDOR_DIR = config.REPO_ROOT / "data" / "vendors"
OUT_DIR = config.REPO_ROOT / "data" / "extracted"


def corpus_files():
    return sorted(p for p in VENDOR_DIR.glob("*.md") if not p.name.startswith("_"))


def write_report(results, path):
    lines = ["# Extraction Run Report", ""]
    lines.append(f"- Model: `{results['model']}`")
    lines.append(f"- Docs processed: {results['total']}")
    lines.append(f"- OK first try: {results['ok_first_try']}")
    lines.append(f"- OK after repair: {results['ok_after_repair']}")
    lines.append(f"- Fell back to human review: {results['fallback']}")
    lines.append(f"- Total tokens: {results['total_tokens']}")
    lines.append("")
    lines.append("| vendor_id | status | attempts | price_confidence | #red_flags | needs_review |")
    lines.append("|---|---|---|---|---|---|")
    for r in results["rows"]:
        lines.append(
            f"| {r['vendor_id']} | {r['status']} | {r['attempts']} | "
            f"{r['price_confidence']} | {r['red_flags']} | {r['needs_human_review']} |"
        )
    path.write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="process only the first N docs")
    ap.add_argument("--force", action="store_true", help="re-extract even if output exists")
    ap.add_argument("--pace", type=float, default=11.0,
                    help="seconds to wait between API calls (free-tier TPM pacing)")
    args = ap.parse_args()

    backend = GroqBackend(config.GROQ_API_KEY, config.GROQ_BASE_URL, config.EXTRACTION_MODEL)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    files = corpus_files()
    if args.limit:
        files = files[:args.limit]

    summary = {
        "model": config.EXTRACTION_MODEL, "total": 0,
        "ok_first_try": 0, "ok_after_repair": 0, "fallback": 0,
        "total_tokens": 0, "rows": [],
    }

    for i, path in enumerate(files):
        vendor_id = path.stem
        out_path = OUT_DIR / f"{vendor_id}.json"

        # Resumable: skip docs already extracted (unless --force). Load the
        # existing record so the run report still covers the whole corpus.
        if out_path.exists() and not args.force:
            rec = json.loads(out_path.read_text())
            status, attempts, tokens = "cached", 0, 0
        else:
            doc_text = path.read_text()
            rec, trace = extract_one(doc_text, vendor_id, path.name, backend, config.MAX_REPAIRS)
            out_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
            status = trace["status"]
            attempts = len(trace["attempts"])
            tokens = sum(a["usage"].get("total_tokens", 0) for a in trace["attempts"])
            # Pace to stay under the free-tier tokens-per-minute limit.
            if args.pace and i < len(files) - 1:
                time.sleep(args.pace)

        summary["total"] += 1
        summary.setdefault("cached", 0)
        summary[{"ok_first_try": "ok_first_try", "ok_after_repair": "ok_after_repair",
                 "fallback_human_review": "fallback", "cached": "cached"}[status]] += 1
        summary["total_tokens"] += tokens
        summary["rows"].append({
            "vendor_id": vendor_id, "status": status, "attempts": attempts,
            "price_confidence": rec.get("price_confidence"),
            "red_flags": len(rec.get("red_flags", [])),
            "needs_human_review": rec.get("needs_human_review"),
        })
        print(f"  {status:22s} {vendor_id}  (attempts={attempts}, "
              f"confidence={rec.get('price_confidence')}, red_flags={len(rec.get('red_flags', []))})")

    write_report(summary, OUT_DIR / "_run_report.md")
    print(f"\nDone: {summary['total']} docs -> {OUT_DIR}")
    print(f"  first-try OK: {summary['ok_first_try']}, after-repair: {summary['ok_after_repair']}, "
          f"fallback: {summary['fallback']}, tokens: {summary['total_tokens']}")


if __name__ == "__main__":
    main()
