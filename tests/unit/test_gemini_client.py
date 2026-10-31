"""Mocked contract and error tests for the Gemini-backed LLM client."""

import httpx
import pytest
from pydantic import SecretStr

from quillseek.config import Settings
from quillseek.rag import (
    APIError,
    GeminiClient,
    InvalidAPIKeyError,
    LLMTimeoutError,
    ModelUnavailableError,
    NetworkError,
    RateLimitError,
    ServiceUnavailableError,
)


def settings() -> Settings:
    return Settings(
        _env_file=None,
        gemini_base_url="https://example.test/v1beta/",
        gemini_api_key=SecretStr("test-key"),
        gemini_model="gemini-test",
        llm_temperature=0.35,
        llm_max_output_tokens=128,
        llm_thinking_level="low",
    )


def response(text: str = "Hello!") -> httpx.Response:
    return httpx.Response(
        200,
        json={"candidates": [{"content": {"parts": [{"text": text}]}}]},
    )


def test_generate_builds_configured_request_and_extracts_text() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return response("Generated answer")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        result = GeminiClient(settings(), client=http).generate("Say hello")

    request = captured["request"]
    assert result == "Generated answer"
    assert str(request.url) == (
        "https://example.test/v1beta/models/gemini-test:generateContent"
    )
    assert request.headers["x-goog-api-key"] == "test-key"
    assert b"test-key" not in request.content
    assert request.read().decode().find('"temperature":0.35') >= 0
    assert b'"maxOutputTokens":128' in request.content
    assert b'"thinkingLevel":"low"' in request.content


def test_generate_captures_provider_token_usage_metadata() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "candidates": [{"content": {"parts": [{"text": "Answer"}]}}],
            "usageMetadata": {"promptTokenCount": 123, "candidatesTokenCount": 17,
                              "totalTokenCount": 140},
        })

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = GeminiClient(settings(), client=http)
        assert client.generate("Question") == "Answer"
        assert client.last_usage == {"input_tokens": 123, "output_tokens": 17, "total_tokens": 140}


def test_stream_yields_sse_text_chunks() -> None:
    body = (
        'data: {"candidates":[{"content":{"parts":[{"text":"First "}]}}]}\n\n'
        'data: {"candidates":[{"content":{"parts":[{"text":"second"}]}}]}\n\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith(":streamGenerateContent")
        assert request.url.params["alt"] == "sse"
        assert request.headers["x-goog-api-key"] == "test-key"
        return httpx.Response(200, text=body)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        chunks = list(GeminiClient(settings(), client=http).stream("Stream"))
    assert chunks == ["First ", "second"]


@pytest.mark.parametrize(
    ("status", "exception"),
    [
        (401, InvalidAPIKeyError),
        (403, InvalidAPIKeyError),
        (404, ModelUnavailableError),
        (429, RateLimitError),
        (503, ServiceUnavailableError),
        (400, APIError),
    ],
)
def test_http_errors_map_to_typed_exceptions(status, exception) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"message": "redacted test"}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(exception):
            GeminiClient(settings(), client=http).generate("Test")


def test_timeout_and_network_failures_are_typed() -> None:
    def timed_out(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    with httpx.Client(transport=httpx.MockTransport(timed_out)) as http:
        with pytest.raises(LLMTimeoutError):
            GeminiClient(settings(), client=http).generate("Test")

    def disconnected(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no network")

    with httpx.Client(transport=httpx.MockTransport(disconnected)) as http:
        with pytest.raises(NetworkError):
            GeminiClient(settings(), client=http).generate("Test")


def test_retryable_503_uses_bounded_backoff_then_returns_success(monkeypatch) -> None:
    calls = 0
    waits = []

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(503, json={"error": {"status": "UNAVAILABLE"}})
        return response("Recovered")

    monkeypatch.setattr("quillseek.rag.llm.time.sleep", waits.append)
    monkeypatch.setattr("quillseek.rag.llm.random.uniform", lambda _low, _high: 1.0)
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = GeminiClient(settings(), client=http, max_retries=3, retry_base_delay=0.25)
        assert client.generate("Retry me") == "Recovered"

    assert calls == 3
    assert waits == [0.25, 0.5]


def test_retryable_status_exhaustion_raises_typed_error(monkeypatch) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"error": {"status": "UNAVAILABLE"}})

    monkeypatch.setattr("quillseek.rag.llm.time.sleep", lambda _delay: None)
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(ServiceUnavailableError):
            GeminiClient(settings(), client=http, max_retries=2).generate("Retry me")

    assert calls == 3


def test_retry_after_header_controls_wait(monkeypatch) -> None:
    calls = 0
    waits = []

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                503,
                headers={"Retry-After": "3"},
                json={"error": {"status": "UNAVAILABLE"}},
            )
        return response("Ready")

    monkeypatch.setattr("quillseek.rag.llm.time.sleep", waits.append)
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        assert GeminiClient(settings(), client=http).generate("Wait") == "Ready"

    assert waits == [3.0]


def test_missing_key_and_empty_prompt_fail_before_network() -> None:
    no_key = settings().model_copy(update={"gemini_api_key": SecretStr("")})
    client = httpx.Client(transport=httpx.MockTransport(lambda _: response()))
    with pytest.raises(InvalidAPIKeyError):
        GeminiClient(no_key, client=client).generate("Test")
    with pytest.raises(ValueError, match="prompt must not be empty"):
        GeminiClient(settings(), client=client).generate("   ")
    client.close()


def test_malformed_response_is_an_api_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(APIError, match="no response candidates"):
            GeminiClient(settings(), client=http).generate("Test")
