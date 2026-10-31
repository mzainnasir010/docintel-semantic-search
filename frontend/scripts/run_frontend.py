"""Launch the Quillseek Gradio frontend."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
PROJECT_SRC = FRONTEND_ROOT / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from quillseek_frontend.app import CSS_PATH, build_app
from quillseek_frontend.config import get_frontend_settings
from quillseek_frontend.theme import THEME


def main() -> None:
    """Start Gradio on the configured host and port."""
    settings = get_frontend_settings()
    build_app().launch(
        server_name=settings.api_host,
        server_port=settings.ui_port,
        theme=THEME,
        css=CSS_PATH.read_text(encoding="utf-8"),
        favicon_path=str(FRONTEND_ROOT / "assets" / "favicon.svg"),
    )


if __name__ == "__main__":
    main()
