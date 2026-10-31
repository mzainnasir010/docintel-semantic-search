"""Smoke test that the Gradio frontend shell builds without backend access."""

import gradio as gr
import httpx

from quillseek_frontend.api_client import APIClient
from quillseek_frontend.app import build_app


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


def test_launcher_applies_the_custom_theme_and_stylesheet() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    launcher = (root / "frontend" / "scripts" / "run_frontend.py").read_text(encoding="utf-8")

    assert "theme=THEME" in launcher
    assert "css=CSS_PATH.read_text" in launcher
