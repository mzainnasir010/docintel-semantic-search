"""Opt-in end-to-end smoke test against the configured Gemini API."""

import pytest

from docintel.config import get_settings
from docintel.rag import GeminiClient


@pytest.mark.gemini
def test_live_gemini_generate_returns_text() -> None:
    settings = get_settings()
    if not settings.gemini_api_key.get_secret_value():
        pytest.skip("GEMINI_API_KEY is not configured")

    with GeminiClient(settings) as client:
        answer = client.generate("Reply with the single word READY.")

    assert answer.strip()
    assert "READY" in answer.upper()
