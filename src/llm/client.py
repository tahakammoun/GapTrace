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


def _cache_key(
    provider: str, model: str, system: str | None, prompt: str, temperature: float
) -> str:
    raw = f"{provider}|{model}|{system or ''}|{prompt}|{temperature}"
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


def _call_gemini(system: str | None, prompt: str, temperature: float) -> str:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ProviderUnavailable("gemini: GOOGLE_API_KEY not set")

    client = genai.Client(api_key=api_key)
    contents = f"{system}\n\n{prompt}" if system else prompt

    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config={"temperature": temperature},
            )
            return response.text
        except genai_errors.ClientError as e:
            if e.code != 429:
                raise
            # 429 covers both per-minute rate limiting (transient, worth
            # retrying) and daily quota exhaustion (not). We can't tell them
            # apart from the error alone, so retry like any transient error
            # and only give up -- letting Groq take over -- once retries run out.
            if attempt == len(RETRY_DELAYS):
                raise ProviderUnavailable("gemini: quota exceeded") from e
            time.sleep(delay)
        except genai_errors.ServerError as e:
            if e.code != 503:
                raise
            if attempt == len(RETRY_DELAYS):
                raise ProviderUnavailable("gemini: unavailable after retries") from e
            time.sleep(delay)

    raise ProviderUnavailable("gemini: unavailable after retries")


def _call_groq(system: str | None, prompt: str, temperature: float) -> str:
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
            json={"model": GROQ_MODEL, "messages": messages, "temperature": temperature},
            timeout=60,
        )
        if resp.status_code in (429, 500, 502, 503, 504) and attempt < len(RETRY_DELAYS):
            time.sleep(delay)
            continue
        if resp.status_code == 429:
            raise ProviderUnavailable("groq: quota exceeded")
        if resp.status_code == 413:
            # Retrying won't shrink the prompt -- this provider simply can't
            # take a request this size, so there's no fallback for THIS call,
            # not a reason to crash the whole run.
            raise ProviderUnavailable("groq: payload too large") from None
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    raise ProviderUnavailable("groq: unavailable after retries")


_CALLERS = {"gemini": _call_gemini, "groq": _call_groq}
_MODELS = {"gemini": GEMINI_MODEL, "groq": GROQ_MODEL}


def complete(
    prompt: str, *, system: str | None = None, use_cache: bool = True, temperature: float = 0.0
) -> str:
    """Get a completion for `prompt`, trying providers in PROVIDER_ORDER.

    Cached on disk per (provider, model, system, prompt, temperature). Every
    provider's cache is checked before ANY live call: otherwise an answer Groq
    gave on a day Gemini was out of quota gets silently re-bought from Gemini
    the next day -- wasting quota and, since the two models disagree often
    enough, flipping the result depending on which provider had quota. Falls
    through to the next provider only on ProviderUnavailable (missing key or
    quota); any other error propagates immediately.

    temperature defaults to 0.0, not the provider default: every current
    caller is a classification task (status, applicability) where the same
    question should get the same answer. Without this, two near-identical
    prompts -- e.g. the same condition checked for its Art.13 and Art.14
    catalog entries -- could get different applicability verdicts purely
    from sampling noise, not from anything in the evidence.
    """
    if use_cache:
        for provider in PROVIDER_ORDER:
            key = _cache_key(provider, _MODELS[provider], system, prompt, temperature)
            cached = _cache_get(key)
            if cached is not None:
                return cached

    failures = []
    for provider in PROVIDER_ORDER:
        model = _MODELS[provider]
        key = _cache_key(provider, model, system, prompt, temperature)
        try:
            text = _CALLERS[provider](system, prompt, temperature)
        except ProviderUnavailable as e:
            failures.append(str(e))
            continue

        if use_cache:
            _cache_set(key, text, provider, model)
        return text

    raise AllProvidersExhausted("; ".join(failures))
