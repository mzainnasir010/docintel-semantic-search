"""Console and rotating file logging configuration."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(
    level: str = "INFO", log_path: str | Path = "logs/quillseek.log"
) -> logging.Logger:
    """Configure the application logger and return it."""
    logger = logging.getLogger("quillseek")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    destination = Path(log_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rotating = RotatingFileHandler(
        destination, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    rotating.setFormatter(formatter)
    logger.addHandler(rotating)
    return logger

