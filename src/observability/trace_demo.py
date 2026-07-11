"""Run a real request through the traced agent, print a timeline, save the trace.

  python -m src.observability.trace_demo
  python -m src.observability.trace_demo "Compare Grand Thali Caterers and Grand Thali Events."

Shows the observability substrate working: every step (LLM decision, tool call) is a
timed span with tokens; the trace is saved to observability/traces/ so we can point at
a real request. Cost/latency reports (later steps) just read this data.
"""
import argparse
from pathlib import Path

from .tracer import Tracer
from .tracing_backend import TracingBackend
from ..agent.orchestrator import Agent
from ..agent.llm_policy import LLMPolicy
from ..agent.ask import TOOLS, AGENT_MODEL
from ..extraction.config import GROQ_API_KEY, GROQ_BASE_URL
from ..extraction.model_backend import GroqBackend

TRACES_DIR = Path(__file__).resolve().parents[2] / "observability" / "traces"

DEFAULT_Q = ("I have 12 lakh for my wedding. Split it with about 45% for the venue and "
             "30% for catering, and check if a payment plan of 80% upfront is risky.")


def print_timeline(tracer: Tracer):
    print(f"\nTRACE {tracer.trace_id}  —  \"{tracer.request}\"")
    print(f"{'start':>8} {'dur':>8}   step")
    print(f"{'-'*8} {'-'*8}   {'-'*40}")
    for s in tracer.spans:
        indent = "  " * s.depth
        extra = ""
        if s.kind == "llm":
            extra = f"  [{s.attrs.get('tokens_in',0)}+{s.attrs.get('tokens_out',0)} tok, {s.attrs.get('model','?')}]"
        elif s.kind == "tool":
            extra = f"  [{'ok' if s.attrs.get('ok') else 'FAIL:'+str(s.attrs.get('stage'))}]"
        print(f"{s.start_ms:>8.1f} {str(s.duration_ms):>8}   {indent}{s.name}{extra}")

    su = tracer.summary()
    print(f"\nSUMMARY: total {su['total_ms']} ms | {su['llm_calls']} LLM calls | "
          f"{su['tool_calls']} tool calls | {su['tokens_total']} tokens "
          f"({su['tokens_in']} in + {su['tokens_out']} out)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?", default=DEFAULT_Q)
    args = ap.parse_args()

    if not GROQ_API_KEY:
        raise SystemExit("No GROQ_API_KEY found. Set it in .env or the environment.")

    tracer = Tracer().start(args.question)
    backend = TracingBackend(GroqBackend(GROQ_API_KEY, GROQ_BASE_URL, AGENT_MODEL), tracer)
    agent = Agent(TOOLS, LLMPolicy(backend), tracer=tracer)

    with tracer.span("request", kind="request"):
        result = agent.run(args.question)

    print_timeline(tracer)
    print(f"\nANSWER: {result.answer}\n")
    path = tracer.save(TRACES_DIR)
    print(f"trace saved -> {path.relative_to(Path(__file__).resolve().parents[2])}")


if __name__ == "__main__":
    main()
