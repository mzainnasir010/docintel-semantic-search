"""Mockable LLM interface and Gemini Developer API implementation."""

from __future__ import annotations

import json
import random
import time
from collections.abc import Iterator
from typing import Any, Protocol

import httpx

from quillseek.config import Settings, get_settings


class LLMError(RuntimeError):
    """Base class for errors raised by an LLM provider."""


class InvalidAPIKeyError(LLMError):
    """The provider rejected the configured API key or its permissions."""


class ModelUnavailableError(LLMError):
    """The configured model does not exist or is unavailable to this key."""


class RateLimitError(LLMError):
    """The provider rejected the request because of quota or rate limits."""


class ServiceUnavailableError(LLMError):
    """The hosted provider is temporarily unavailable."""


class LLMTimeoutError(LLMError):
    """The provider did not answer before the configured timeout."""


class NetworkError(LLMError):
    """A transport-level failure prevented communication with the provider."""


class APIError(LLMError):
    """A provider response was unsuccessful or could not be interpreted."""


class LLMClient(Protocol):
    """Provider-neutral interface consumed by retrieval augmented services."""

    def generate(self, prompt: str) -> str:
        """Generate a complete text response for a prompt."""

    def stream(self, prompt: str) -> Iterator[str]:
        """Yield response text as provider chunks arrive."""


class GeminiClient:
    """Thin synchronous client for Gemini's generate and SSE stream endpoints."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if retry_base_delay < 0:
            raise ValueError("retry_base_delay must be non-negative")
        self.settings = settings or get_settings()
        self._client = client or httpx.Client()
        self._owns_client = client is None
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

    def close(self) -> None:
        """Close the internally created HTTP client, if any."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> GeminiClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def generate(self, prompt: str) -> str:
        """Return the generated text, mapping provider failures to typed errors."""
        response = self._request(
            f"{self._base_endpoint}:generateContent", self._payload(prompt)
        )
        try:
            data = response.json()
            return self._extract_text(data)
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise APIError("Gemini returned an invalid generation response.") from exc

    def stream(self, prompt: str) -> Iterator[str]:
        """Yield text from Gemini's server-sent event stream."""
        endpoint = f"{self._base_endpoint}:streamGenerateContent"
        try:
            with self._client.stream(
                "POST",
                endpoint,
                params={"alt": "sse"},
                headers=self._headers,
                json=self._payload(prompt),
                timeout=self.timeout,
            ) as response:
                self._raise_for_status(response)
                for line in response.iter_lines():
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    if line == "[DONE]":
                        break
                    try:
                        data = json.loads(line)
                        text = self._extract_text(data)
                    except (ValueError, KeyError, IndexError, TypeError) as exc:
                        raise APIError("Gemini returned an invalid streaming response.") from exc
                    if text:
                        yield text
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Gemini request timed out.") from exc
        except httpx.RequestError as exc:
            raise NetworkError("Could not communicate with the Gemini API.") from exc

    @property
    def _base_endpoint(self) -> str:
        return (
            f"{self.settings.gemini_base_url.rstrip('/')}/models/"
            f"{self.settings.gemini_model}"
        )

    @property
    def _headers(self) -> dict[str, str]:
        key = self.settings.gemini_api_key.get_secret_value()
        if not key:
            raise InvalidAPIKeyError("Set GEMINI_API_KEY in the project .env file.")
        return {"x-goog-api-key": key, "Content-Type": "application/json"}

    def _payload(self, prompt: str) -> dict[str, Any]:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        return {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.settings.llm_temperature,
                "maxOutputTokens": self.settings.llm_max_output_tokens,
                "thinkingConfig": {
                    "thinkingLevel": self.settings.llm_thinking_level
                },
            },
        }

    def _request(self, endpoint: str, payload: dict[str, Any]) -> httpx.Response:
        last_transport_error: httpx.RequestError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.post(
                    endpoint,
                    headers=self._headers,
                    json=payload,
                    timeout=self.timeout,
                )
            except httpx.RequestError as exc:
                last_transport_error = exc
                if attempt == self.max_retries:
                    if isinstance(exc, httpx.TimeoutException):
                        raise LLMTimeoutError("Gemini request timed out.") from exc
                    raise NetworkError("Could not communicate with the Gemini API.") from exc
                self._wait_before_retry(attempt)
                continue

            if response.status_code in {408, 429, 500, 502, 503, 504}:
                if attempt < self.max_retries:
                    delay = self._retry_delay(attempt, response)
                    time.sleep(delay)
                    continue
            self._raise_for_status(response)
            return response

        # The loop either returns or raises; this keeps the type checker satisfied.
        if isinstance(last_transport_error, httpx.TimeoutException):
            raise LLMTimeoutError("Gemini request timed out.") from last_transport_error
        raise NetworkError("Could not communicate with the Gemini API.") from last_transport_error

    def _wait_before_retry(self, attempt: int) -> None:
        time.sleep(self._backoff(attempt))

    def _retry_delay(self, attempt: int, response: httpx.Response) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        return self._backoff(attempt)

    def _backoff(self, attempt: int) -> float:
        return self.retry_base_delay * (2**attempt) * random.uniform(0.8, 1.2)

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        candidates = data.get("candidates")
        if not candidates:
            raise APIError("Gemini returned no response candidates.")
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(part.get("text", "") for part in parts)

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        status = response.status_code
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if status in (401, 403):
                raise InvalidAPIKeyError("Gemini rejected the API key or permissions.") from exc
            if status == 404:
                raise ModelUnavailableError("The configured Gemini model was not found.") from exc
            if status == 429:
                raise RateLimitError("Gemini quota or rate limit was exceeded.") from exc
            if status in (500, 502, 503, 504):
                raise ServiceUnavailableError("The Gemini API is temporarily unavailable.") from exc
            raise APIError(f"Gemini API returned HTTP {status}.") from exc
