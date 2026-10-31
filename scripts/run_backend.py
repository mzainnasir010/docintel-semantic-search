"""Start the DocIntel FastAPI backend with Uvicorn."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

import uvicorn

from docintel.config import get_settings


def main() -> None:
    """Run the API using host and port from project configuration."""
    settings = get_settings()
    uvicorn.run("docintel.api.app:app", host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    main()
