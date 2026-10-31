"""PDF text extraction using PyMuPDF."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections.abc import Iterator

import pymupdf

from quillseek.models import PageContent

logger = logging.getLogger(__name__)

_PDF_DATE_PATTERN = re.compile(
    r"^D:(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})"
    r"(?P<hour>\d{2})?(?P<minute>\d{2})?(?P<second>\d{2})?"
    r"(?P<zone>Z|[+-]\d{2}'?\d{2}'?)?$"
)


def parse_pdf_creation_date(value: str | None) -> datetime | None:
    """Parse a PDF creation date value into a datetime when it is valid."""
    if not value:
        return None
    match = _PDF_DATE_PATTERN.match(value.strip())
    if not match:
        return None
    parts = match.groupdict()
    try:
        parsed = datetime(
            int(parts["year"]), int(parts["month"]), int(parts["day"]),
            int(parts["hour"] or 0), int(parts["minute"] or 0),
            int(parts["second"] or 0),
        )
    except ValueError:
        return None
    zone = parts["zone"]
    if not zone:
        return parsed
    if zone == "Z":
        return parsed.replace(tzinfo=timezone.utc)
    if zone:
        try:
            sign = 1 if zone[0] == "+" else -1
            digits = zone[1:].replace("'", "")
            offset = timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
            return parsed.replace(tzinfo=timezone(sign * offset))
        except (ValueError, OverflowError):
            return None
    return parsed


def get_pdf_creation_date(path: str | Path) -> datetime | None:
    """Read and parse the PDF creation date without raising on damaged files."""
    source_path = Path(path)
    try:
        with pymupdf.open(source_path) as pdf:
            metadata = pdf.metadata or {}
        return parse_pdf_creation_date(metadata.get("creationDate"))
    except Exception as error:
        logger.warning("Could not read PDF metadata from %s: %s", source_path, error)
        return None


def iter_pdf_pages(
    path: str | Path,
    *,
    doc_id: str | None = None,
    doc_name: str | None = None,
) -> Iterator[PageContent]:
    """Yield extracted PDF pages one at a time, retaining empty/image-only pages."""
    source_path = Path(path)
    resolved_doc_id = doc_id or source_path.stem
    resolved_doc_name = doc_name or source_path.name
    try:
        with pymupdf.open(source_path) as pdf:
            for page_index, page in enumerate(pdf, start=1):
                try:
                    text = page.get_text("text") or ""
                except Exception as error:
                    logger.warning(
                        "Could not extract PDF page %s from %s: %s",
                        page_index,
                        source_path,
                        error,
                    )
                    text = ""
                if not text.strip():
                    logger.warning(
                        "PDF page %s in %s has no extractable text (empty or image-only)",
                        page_index,
                        source_path,
                    )
                yield PageContent(
                    doc_id=resolved_doc_id,
                    doc_name=resolved_doc_name,
                    page_number=page_index,
                    text=text.strip(),
                    source_path=str(source_path),
                )
    except Exception as error:
        logger.warning("Could not load PDF %s: %s", source_path, error)


def load_pdf(
    path: str | Path,
    *,
    doc_id: str | None = None,
    doc_name: str | None = None,
) -> list[PageContent]:
    """Compatibility helper that materializes the page-wise PDF iterator."""
    return list(iter_pdf_pages(path, doc_id=doc_id, doc_name=doc_name))

