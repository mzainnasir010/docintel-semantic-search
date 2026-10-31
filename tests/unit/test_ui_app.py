"""Smoke test that the Gradio frontend shell builds without backend access."""

import gradio as gr
import httpx

from quillseek.ui.api_client import APIClient
from quillseek.ui.app import build_app


def test_gradio_app_object_builds_without_calling_backend() -> None:
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503, json={"detail": "not available"})

    client = APIClient(
        "http://backend.test",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    app = build_app(client)

    assert isinstance(app, gr.Blocks)
    assert not calls
    client._client.close()
