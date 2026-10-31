"""Launch the Quillseek Gradio frontend."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from quillseek.config import get_settings
from quillseek.ui.app import CSS_PATH, build_app
from quillseek.ui.theme import THEME


def main() -> None:
    """Start Gradio on the configured host and port."""
    settings = get_settings()
    build_app().launch(
        server_name=settings.api_host,
        server_port=settings.ui_port,
        theme=THEME,
        css=CSS_PATH.read_text(encoding="utf-8"),
        favicon_path=str(Path(__file__).resolve().parents[1] / "assets" / "favicon.svg"),
    )


if __name__ == "__main__":
    main()
