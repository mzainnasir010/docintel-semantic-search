"""Integration check for launch-ready Gradio UI configuration."""

from quillseek.ui.app import build_app


class EmptyClient:
    def health(self):
        return {"status": "ok", "gemini_configured": True}

    def documents(self):
        return {"documents": [], "pending_uploads": []}


def test_full_app_build_has_quillseek_page_title() -> None:
    app = build_app(EmptyClient())
    config = app.get_config_file()
    assert config["title"] == "Quillseek"
