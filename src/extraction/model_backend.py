"""Model backends — the SWAPPABLE part of the extractor.

The whole pipeline (validate -> repair -> fallback) is model-agnostic. Swapping
the LLM is just swapping a backend. This is good engineering AND sets up the
model-routing competency (#9) later.

- GroqBackend: real calls to Groq Cloud (OpenAI-compatible), stdlib urllib only.
- MockBackend: scripted responses, for testing the reliability logic with NO key
  and NO cost — including deliberately broken responses to prove repair/fallback.
"""
import json
import re
import time
import urllib.error
import urllib.request


class ModelError(Exception):
    pass


class GroqBackend:
    def __init__(self, api_key: str, base_url: str, model: str):
        if not api_key:
            raise ModelError("GROQ_API_KEY is empty — set it in .env or the environment.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    @staticmethod
    def _retry_after(detail, default=5.0):
        """Pull 'try again in 2.145s' out of a 429 body, else use default."""
        m = re.search(r"try again in ([0-9.]+)s", detail)
        return (float(m.group(1)) + 0.5) if m else default

    def complete(self, messages, json_mode: bool = True, _rl_tries: int = 6):
        url = f"{self.base_url}/chat/completions"
        payload = {"model": self.model, "messages": messages, "temperature": 0}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # Groq sits behind Cloudflare, which 403s the default Python urllib
            # User-Agent (error 1010). A normal UA gets through.
            "User-Agent": "baraat-extractor/1.0",
        }

        for _ in range(_rl_tries):
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")
                if json_mode and e.code == 400:
                    # Some models reject json_object mode — retry without it.
                    return self.complete(messages, json_mode=False, _rl_tries=_rl_tries)
                if e.code == 429:
                    # Free-tier tokens-per-minute limit — wait the suggested time.
                    wait = self._retry_after(detail)
                    time.sleep(wait)
                    continue
                raise ModelError(f"HTTP {e.code}: {detail[:300]}")
            except urllib.error.URLError as e:
                raise ModelError(f"network error reaching Groq: {e}")
            return {
                "text": body["choices"][0]["message"]["content"],
                "usage": body.get("usage", {}),
                "latency": time.time() - t0,
                "model": self.model,
            }
        raise ModelError("rate limit: exhausted retries")


class MockBackend:
    """Returns scripted responses in order. Each script entry is a raw string
    (what the 'model' would return). Used to test the loop deterministically."""

    def __init__(self, scripted_responses, model="mock"):
        self._responses = list(scripted_responses)
        self._i = 0
        self.model = model

    def complete(self, messages, json_mode: bool = True):
        if self._i >= len(self._responses):
            raise ModelError("MockBackend ran out of scripted responses")
        text = self._responses[self._i]
        self._i += 1
        return {"text": text, "usage": {}, "latency": 0.0, "model": self.model}
