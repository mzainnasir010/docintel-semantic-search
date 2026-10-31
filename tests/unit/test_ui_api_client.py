"""Unit tests for frontend API requests and friendly backend errors."""

from pathlib import Path

import httpx
import pytest

from quillseek_frontend.api_client import (
    APIClient,
    BackendAPIError,
    BackendUnavailableError,
)


def test_api_client_calls_health_and_uploads_multiple_files(tmp_path) -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/documents/upload":
            return httpx.Response(200, json={"uploaded": ["one.txt", "two.txt"], "count": 2})
        return httpx.Response(404, json={"detail": "missing"})

    one = tmp_path / "one.txt"
    two = tmp_path / "two.txt"
    one.write_text("first", encoding="utf-8")
    two.write_text("second", encoding="utf-8")
    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = APIClient("http://backend.test", client=http)

    assert client.health() == {"status": "ok"}
    assert client.upload_files([one, two])["count"] == 2
    assert requests[0].url.path == "/health"
    assert requests[1].url.path == "/documents/upload"
    assert "one.txt" in requests[1].content.decode()
    assert "two.txt" in requests[1].content.decode()
    assert "first" in requests[1].content.decode()
    http.close()


def test_api_client_surfaces_backend_error_payload() -> None:
    http = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                413,
                json={"error": "request_error", "detail": "Upload exceeds limit"},
            )
        )
    )
    client = APIClient("http://backend.test", client=http)

    with pytest.raises(BackendAPIError, match="Upload exceeds limit") as error:
        client.documents()

    assert error.value.status_code == 413
    http.close()


@pytest.mark.parametrize("error", [httpx.ConnectError("offline"), httpx.ReadTimeout("slow")])
def test_api_client_maps_network_failures_to_friendly_error(error) -> None:
    http = httpx.Client(
        transport=httpx.MockTransport(lambda request: (_ for _ in ()).throw(error))
    )
    client = APIClient("http://backend.test", client=http)

    with pytest.raises(BackendUnavailableError, match="backend"):
        client.health()
    http.close()


def test_api_client_refuses_empty_upload_list() -> None:
    client = APIClient("http://backend.test", client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200))))
    with pytest.raises(ValueError, match="at least one file"):
        client.upload_files([])
    client._client.close()
