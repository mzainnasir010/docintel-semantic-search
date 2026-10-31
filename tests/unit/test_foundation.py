"""Smoke tests for foundation configuration and logging."""

import logging

from docintel.config import Settings
from docintel.logging_config import configure_logging


def test_settings_load_defaults(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    settings = Settings(_env_file=None)
    assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert settings.chunk_size == 800
    assert settings.gemini_api_key.get_secret_value() == ""
    assert settings.gemini_model == "gemini-3.8-flash"


def test_settings_accept_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("TOP_K", "7")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    settings = Settings(_env_file=None)
    assert settings.top_k == 7
    assert settings.gemini_model == "test-model"
    assert settings.gemini_api_key.get_secret_value() == "unit-test-key"


def test_logging_initializes_console_and_rotating_file(tmp_path) -> None:
    logger = configure_logging("DEBUG", tmp_path / "test.log")
    logger.debug("foundation smoke test")
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 2
    assert (tmp_path / "test.log").read_text(encoding="utf-8").find(
        "foundation smoke test"
    ) >= 0

