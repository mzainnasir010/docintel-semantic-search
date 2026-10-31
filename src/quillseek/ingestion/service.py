"""Batch document routing, identity, and per-file error handling."""

from __future__ import annotations

import hashlib
import logging
import zipfile
from pathlib import Path

from quillseek.ingestion.docx_loader import load_docx
from quillseek.ingestion.pdf_loader import get_pdf_creation_date, iter_pdf_pages
from quillseek.ingestion.txt_loader import load_txt
from quillseek.models import DocumentRecord, IngestionSummary
from quillseek.preprocessing import BoilerplateReport, iter_preprocessed_pages

logger = logging.getLogger(__name__)
_SUPPORTED = {".pdf": "pdf", ".docx": "docx", ".txt": "txt"}
_OOXML_DOCUMENT_TYPE = (
    b"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
)


def stable_document_id(path: str | Path) -> str:
    """Return a 16-hex SHA-256 identifier, hashing file content in blocks."""
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
    except OSError:
        # Keep a deterministic failed record even when the path cannot be read.
        digest.update(str(path).encode("utf-8", errors="replace"))
    return digest.hexdigest()[:16]


def detect_file_type(path: str | Path) -> str | None:
    """Detect supported documents from their signatures, then their extension."""
    source_path = Path(path)
    try:
        with source_path.open("rb") as source:
            signature = source.read(8)
        if signature.startswith(b"%PDF-"):
            return "pdf"
        if signature.startswith(b"PK") and zipfile.is_zipfile(source_path):
            try:
                with zipfile.ZipFile(source_path) as archive:
                    if "[Content_Types].xml" in archive.namelist() and _OOXML_DOCUMENT_TYPE in archive.read("[Content_Types].xml"):
                        return "docx"
            except (OSError, zipfile.BadZipFile, KeyError):
                pass
    except OSError:
        return _SUPPORTED.get(source_path.suffix.lower())
    return _SUPPORTED.get(source_path.suffix.lower())


def ingest_files(paths: list[str | Path]) -> IngestionSummary:
    """Ingest each path independently and summarize successes and failures."""
    documents: list[DocumentRecord] = []
    pages = []
    failed: list[DocumentRecord] = []
    page_counts: dict[str, int] = {}
    succeeded = 0

    for item in paths:
        path = Path(item)
        doc_id = stable_document_id(path)
        file_type = detect_file_type(path)
        try:
            if file_type is None:
                raise ValueError(f"Unsupported document type: {path.suffix or '(no extension)'}")
            name = path.name
            if file_type == "pdf":
                page_factory = lambda: iter_pdf_pages(
                    path, doc_id=doc_id, doc_name=name
                )
                created_at = get_pdf_creation_date(path)
            elif file_type == "docx":
                source_pages = load_docx(path, doc_id=doc_id, doc_name=name)
                page_factory = lambda: iter(source_pages)
                created_at = None
            else:
                source_pages = load_txt(path, doc_id=doc_id, doc_name=name)
                page_factory = lambda: iter(source_pages)
                created_at = None
            cleanup_report = BoilerplateReport()
            loaded_pages = list(
                iter_preprocessed_pages(page_factory, report=cleanup_report)
            )
            if not loaded_pages:
                raise ValueError(f"No pages could be extracted from {name}")
            record = DocumentRecord(
                doc_id=doc_id,
                doc_name=name,
                source_path=str(path),
                file_type=file_type,
                num_pages=len(loaded_pages),
                created_at=created_at,
                status="indexed",
            )
            documents.append(record)
            pages.extend(loaded_pages)
            page_counts[doc_id] = len(loaded_pages)
            succeeded += 1
        except Exception as error:
            reason = str(error) or error.__class__.__name__
            logger.warning("Failed to ingest %s: %s", path, reason)
            record = DocumentRecord(
                doc_id=doc_id,
                doc_name=path.name or str(path),
                source_path=str(path),
                file_type=file_type or "unsupported",
                num_pages=0,
                status="failed",
                error_message=reason,
            )
            documents.append(record)
            failed.append(record)
            page_counts[doc_id] = 0

    return IngestionSummary(
        succeeded=succeeded,
        failed=failed,
        documents=documents,
        pages=pages,
        page_counts=page_counts,
    )
