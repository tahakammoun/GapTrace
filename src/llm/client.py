"""Single entry point for all model calls: disk-cached, provider-routed,
with backoff on transient errors. Gemini is primary, Groq is the fallback
for when Gemini's free-tier daily quota is exhausted.

Nothing outside this module should import google.genai or call an LLM
provider's SDK/API directly.
"""

import hashlib
import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = ROOT / ".cache" / "llm"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

PROVIDER_ORDER = ["gemini", "groq"]
RETRY_DELAYS = [2, 4, 8, 16, 32]


class ProviderUnavailable(Exception):
    """This provider can't be used right now (missing key, quota exhausted)."""


class AllProvidersExhausted(Exception):
    """Every configured provider failed for this call."""


def _cache_key(provider: str, model: str, system: str | None, prompt: str) -> str:
    raw = f"{provider}|{model}|{system or ''}|{prompt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> str | None:
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))["text"]


def _cache_set(key: str, text: str, provider: str, model: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{key}.json"
    payload = {"provider": provider, "model": model, "text": text}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _call_gemini(system: str | None, prompt: str) -> str:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ProviderUnavailable("gemini: GOOGLE_API_KEY not set")

    client = genai.Client(api_key=api_key)
    contents = f"{system}\n\n{prompt}" if system else prompt

    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        try:
            response = client.models.generate_content(model=GEMINI_MODEL, contents=contents)
            return response.text
        except genai_errors.ClientError as e:
            if e.code == 429:
                raise ProviderUnavailable("gemini: quota exceeded") from e
            raise
        except genai_errors.ServerError as e:
            if e.code != 503 or attempt == len(RETRY_DELAYS):
                raise
            time.sleep(delay)

    raise ProviderUnavailable("gemini: unavailable after retries")


def _call_groq(system: str | None, prompt: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ProviderUnavailable("groq: GROQ_API_KEY not set")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        resp = httpx.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": GROQ_MODEL, "messages": messages},
            timeout=60,
        )
        if resp.status_code == 429:
            raise ProviderUnavailable("groq: quota exceeded")
        if resp.status_code >= 500 and attempt < len(RETRY_DELAYS):
            time.sleep(delay)
            continue
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    raise ProviderUnavailable("groq: unavailable after retries")


_CALLERS = {"gemini": _call_gemini, "groq": _call_groq}
_MODELS = {"gemini": GEMINI_MODEL, "groq": GROQ_MODEL}


def complete(prompt: str, *, system: str | None = None, use_cache: bool = True) -> str:
    """Get a completion for `prompt`, trying providers in PROVIDER_ORDER.

    Cached on disk per (provider, model, system, prompt) — a cache hit on
    the first provider short-circuits before any network call, so a
    quota-exhausted primary provider never blocks re-reading work already
    paid for. Falls through to the next provider only on ProviderUnavailable
    (missing key or quota); any other error propagates immediately.
    """
    failures = []
    for provider in PROVIDER_ORDER:
        model = _MODELS[provider]
        key = _cache_key(provider, model, system, prompt)

        if use_cache:
            cached = _cache_get(key)
            if cached is not None:
                return cached

        try:
            text = _CALLERS[provider](system, prompt)
        except ProviderUnavailable as e:
            failures.append(str(e))
            continue

        if use_cache:
            _cache_set(key, text, provider, model)
        return text

    raise AllProvidersExhausted("; ".join(failures))
