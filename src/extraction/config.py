"""Configuration + .env loading (stdlib only, no external dependency).

We deliberately avoid python-dotenv so the pipeline runs anywhere with a bare
Python 3 — fewer moving parts is itself a reliability choice.
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path = REPO_ROOT / ".env") -> None:
    """Load KEY=VALUE lines from .env into the environment (without overriding
    anything already set in the real environment, which takes precedence)."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


load_dotenv()

# Model backend (Groq Cloud is OpenAI-compatible; serves open models like Llama).
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_BASE_URL = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
EXTRACTION_MODEL = os.environ.get("EXTRACTION_MODEL", "llama-3.3-70b-versatile")

# Agent guardrail (preview of competency #8): cap repair attempts so a model that
# keeps producing junk can't loop forever burning tokens. After this many repairs
# we degrade gracefully to a flagged "needs human review" record.
MAX_REPAIRS = int(os.environ.get("MAX_REPAIRS", "2"))
