"""Unit tests for Gemini setup request construction."""

from pydantic import SecretStr

from quillseek.config import Settings
from scripts.check_gemini import build_gemini_request, check_gemini


def test_build_gemini_request_uses_configured_model_and_prompt() -> None:
    endpoint, payload = build_gemini_request(
        "https://example.invalid/v1beta/", "gemini-test", "Say READY", 0.1
    )
    assert endpoint == (
        "https://example.invalid/v1beta/models/gemini-test:generateContent"
    )
    assert payload["contents"][0]["parts"][0]["text"] == "Say READY"
    assert payload["generationConfig"]["temperature"] == 0.1


def test_gemini_request_does_not_put_api_key_in_endpoint_or_payload() -> None:
    endpoint, payload = build_gemini_request(
        "https://example.invalid/v1beta", "gemini-test", "Say READY", 0.1
    )
    assert "key" not in endpoint.lower()
    assert "key" not in str(payload).lower()


def test_check_gemini_sends_key_in_header_and_returns_reply(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "candidates": [
                    {"content": {"parts": [{"text": " READY\n"}]}}
                ]
            }

    def fake_post(url, *, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr("scripts.check_gemini.httpx.post", fake_post)
    settings = Settings(
        _env_file=None,
        gemini_api_key=SecretStr("unit-test-key"),
        gemini_model="gemini-test",
    )

    reply, latency = check_gemini(settings)

    assert reply == "READY"
    assert latency >= 0
    assert captured["headers"] == {"x-goog-api-key": "unit-test-key"}
    assert "key" not in captured["url"].lower()


def test_env_example_has_placeholder_but_no_runtime_values() -> None:
    from pathlib import Path

    env_lines = Path(".env.example").read_text(encoding="utf-8").splitlines()
    assignments = dict(line.split("=", 1) for line in env_lines if "=" in line)

    assert assignments["GEMINI_API_KEY"] == "your-api-key-here"
    assert all(value == "" for name, value in assignments.items() if name != "GEMINI_API_KEY")
