"""Opt-in end-to-end smoke test against the configured Gemini API."""

import pytest

from quillseek.config import get_settings
from quillseek.rag import GeminiClient
from quillseek.rag.llm import (
    LLMTimeoutError,
    NetworkError,
    RateLimitError,
    ServiceUnavailableError,
)


@pytest.mark.gemini
def test_live_gemini_generate_returns_text() -> None:
    settings = get_settings()
    if not settings.gemini_api_key.get_secret_value():
        pytest.skip("GEMINI_API_KEY is not configured")

    try:
        with GeminiClient(settings) as client:
            answer = client.generate("Reply with the single word READY.")
    except (RateLimitError, ServiceUnavailableError, LLMTimeoutError, NetworkError) as error:
        pytest.skip(f"Gemini is temporarily unavailable: {type(error).__name__}")

    assert answer.strip()
    assert "READY" in answer.upper()
