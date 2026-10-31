"""HTTP-only client used by the Gradio frontend to call the backend API."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, Iterable

import httpx

from quillseek_frontend.config import get_frontend_settings


class BackendError(RuntimeError):
    """Base class for expected backend communication and API errors."""


class BackendUnavailableError(BackendError):
    """The backend could not be reached or timed out."""


class BackendAPIError(BackendError):
    """The backend returned an unsuccessful status and a safe error message."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class APIClient:
    """Small injectable synchronous client for the Quillseek REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        client: Any | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = (base_url or get_frontend_settings().backend_url).rstrip("/")
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None
        self.timeout = timeout

    def close(self) -> None:
        """Close the internally created HTTP client."""
        if self._owns_client:
            self._client.close()

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def documents(self) -> dict[str, Any]:
        return self._request("GET", "/documents")

    def upload_files(self, file_paths: Iterable[str | Path]) -> dict[str, Any]:
        files = []
        for value in file_paths:
            path = Path(value)
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            files.append(("files", (path.name, path.read_bytes(), content_type)))
        if not files:
            raise ValueError("Choose at least one file to upload")
        return self._request("POST", "/documents/upload", files=files)

    def start_index(self) -> dict[str, Any]:
        return self._request("POST", "/index")

    def index_status(self, job_id: str) -> dict[str, Any]:
        return self._request("GET", f"/index/status/{job_id}")

    def delete_document(self, doc_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/documents/{doc_id}")

    def reset_collection(self) -> dict[str, Any]:
        return self._request("DELETE", "/collection")

    def search(self, query: str, k: int | None = None) -> dict[str, Any]:
        return self._request("POST", "/search", json={"query": query, "k": k})

    def ask(self, query: str, k: int | None = None) -> dict[str, Any]:
        return self._request("POST", "/ask", json={"query": query, "k": k})

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            timeout = kwargs.pop("timeout", self.timeout)
            if self._owns_client:
                kwargs["timeout"] = timeout
            response = self._client.request(method, f"{self.base_url}{path}", **kwargs)
        except httpx.TimeoutException as error:
            raise BackendUnavailableError(
                "The backend did not respond in time. Check that it is running and retry."
            ) from error
        except httpx.RequestError as error:
            raise BackendUnavailableError(
                "The backend is unavailable. Start the Quillseek backend and retry."
            ) from error
        try:
            payload = response.json()
        except ValueError as error:
            if not response.is_success:
                raise BackendAPIError(
                    response.status_code, "The backend could not complete the request."
                ) from error
            raise BackendAPIError(502, "The backend returned an invalid response.") from error
        if not response.is_success:
            detail = payload.get("detail") or payload.get("error") or "The request failed."
            if isinstance(detail, dict):
                detail = detail.get("detail") or "The request failed."
            raise BackendAPIError(response.status_code, str(detail))
        if not isinstance(payload, dict):
            raise BackendAPIError(502, "The backend returned an invalid response.")
        return payload
