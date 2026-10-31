"""Plain-text loading with common encoding fallbacks."""

from __future__ import annotations

import logging
from pathlib import Path

from docintel.models import PageContent

logger = logging.getLogger(__name__)

_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin-1")


def decode_text(data: bytes) -> str:
    """Decode bytes using UTF encodings first, then common Western fallbacks."""
    for encoding in _ENCODINGS:
        try:
            return data.decode(encoding).removeprefix("\ufeff")
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace").removeprefix("\ufeff")


def load_txt(
    path: str | Path,
    *,
    doc_id: str | None = None,
    doc_name: str | None = None,
) -> list[PageContent]:
    """Read a text file as one logical page, returning an empty page on failure."""
    source_path = Path(path)
    resolved_doc_id = doc_id or source_path.stem
    resolved_doc_name = doc_name or source_path.name
    try:
        text = decode_text(source_path.read_bytes())
    except OSError as error:
        logger.warning("Could not read TXT %s: %s", source_path, error)
        text = ""
    if not text.strip():
        logger.warning("TXT %s is empty or contains no readable text", source_path)
    return [
        PageContent(
            doc_id=resolved_doc_id,
            doc_name=resolved_doc_name,
            page_number=1,
            text=text.strip(),
            source_path=str(source_path),
        )
    ]

