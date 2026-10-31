"""Application settings loaded from environment variables and .env."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime configuration with PLAN.md defaults."""

    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.8-flash"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    chroma_path: str = "data/chroma"
    collection_name: str = "documents"
    upload_dir: str = "data/uploads"
    chunk_size: int = 800
    chunk_overlap: int = 100
    chunk_strategy: str = "recursive"
    top_k: int = 5
    min_similarity: float = 0.25
    llm_temperature: float = 0.1
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    backend_url: str = "http://127.0.0.1:8000"
    ui_port: int = 7860
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings for the current process."""
    return Settings()

