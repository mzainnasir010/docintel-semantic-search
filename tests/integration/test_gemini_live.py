"""Live Gemini API smoke test; requires user-provided local credentials."""

import httpx
import pytest
from dotenv import dotenv_values

from quillseek.config import Settings
from backend.scripts.check_gemini import check_gemini


@pytest.mark.gemini
@pytest.mark.integration
def test_live_gemini_returns_non_empty_text() -> None:
    local_env = dotenv_values(".env")
    api_key = local_env.get("GEMINI_API_KEY", "")
    if not api_key:
        pytest.skip("GEMINI_API_KEY is not configured in .env")
    settings = Settings(
        _env_file=None,
        gemini_api_key=api_key,
        gemini_model=local_env.get("GEMINI_MODEL", "gemini-3.8-flash"),
        gemini_base_url=local_env.get(
            "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
        ),
    )
    try:
        reply, _ = check_gemini(settings)
    except (httpx.ConnectError, httpx.TimeoutException) as error:
        pytest.skip(f"Gemini API is unreachable: {error.__class__.__name__}")
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 408 or error.response.status_code == 429 or error.response.status_code >= 500:
            pytest.skip(f"Gemini API is temporarily unavailable: HTTP {error.response.status_code}")
        raise
    assert reply
