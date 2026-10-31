"""Start the Quillseek FastAPI backend with Uvicorn."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_SRC = PROJECT_ROOT / "backend" / "src"
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

import uvicorn

from quillseek.config import get_settings


def main() -> None:
    """Run the API using host and port from project configuration."""
    settings = get_settings()
    uvicorn.run("quillseek.api.app:app", host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    main()
