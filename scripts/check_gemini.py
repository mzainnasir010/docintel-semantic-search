"""Send a minimal prompt to the configured Gemini Developer API."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import httpx

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from docintel.config import Settings, get_settings


def build_gemini_request(
    base_url: str, model: str, prompt: str, temperature: float
) -> tuple[str, dict[str, Any]]:
    """Build the endpoint and JSON body without including credentials."""
    endpoint = f"{base_url.rstrip('/')}/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 128},
    }
    return endpoint, payload


def check_gemini(settings: Settings | None = None) -> tuple[str, float]:
    """Return Gemini's text response and elapsed seconds, without logging the key."""
    active_settings = settings or get_settings()
    api_key = active_settings.gemini_api_key.get_secret_value()
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY in the project-root .env file first.")

    endpoint, payload = build_gemini_request(
        active_settings.gemini_base_url,
        active_settings.gemini_model,
        "Reply with the single word READY.",
        active_settings.llm_temperature,
    )
    started_at = time.perf_counter()
    response = httpx.post(
        endpoint,
        headers={"x-goog-api-key": api_key},
        json=payload,
        timeout=30.0,
    )
    response.raise_for_status()
    elapsed_seconds = time.perf_counter() - started_at
    response_data = response.json()
    reply = response_data["candidates"][0]["content"]["parts"][0]["text"]
    return reply.strip(), elapsed_seconds


def main() -> None:
    """Run the API check and print only the model reply and latency."""
    try:
        reply, latency = check_gemini()
    except httpx.ConnectError:
        raise SystemExit("Could not reach the Gemini API; check your internet connection.") from None
    except httpx.TimeoutException:
        raise SystemExit("The Gemini API request timed out; try again later.") from None
    except httpx.HTTPStatusError as error:
        raise SystemExit(
            f"Gemini API returned HTTP {error.response.status_code}; check the model, key, and API availability."
        ) from None
    print(f"Gemini reply: {reply}")
    print(f"Latency: {latency:.2f} seconds")


if __name__ == "__main__":
    main()
