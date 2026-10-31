"""Frontend-only settings; the Gradio process talks to the backend over HTTP."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class FrontendSettings(BaseSettings):
    """Runtime settings needed to launch the Gradio process and reach the API."""

    backend_url: str = "http://127.0.0.1:8000"
    api_host: str = "127.0.0.1"
    ui_port: int = 7860

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
    )


@lru_cache(maxsize=1)
def get_frontend_settings() -> FrontendSettings:
    """Return cached frontend settings."""
    return FrontendSettings()
