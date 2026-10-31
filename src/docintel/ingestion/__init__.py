"""Document loaders and ingestion helpers."""

from docintel.ingestion.docx_loader import load_docx
from docintel.ingestion.pdf_loader import (
    get_pdf_creation_date,
    iter_pdf_pages,
    load_pdf,
    parse_pdf_creation_date,
)
from docintel.ingestion.txt_loader import decode_text, load_txt
from docintel.ingestion.service import detect_file_type, ingest_files, stable_document_id

__all__ = [
    "decode_text",
    "detect_file_type",
    "get_pdf_creation_date",
    "load_docx",
    "load_pdf",
    "load_txt",
    "ingest_files",
    "iter_pdf_pages",
    "parse_pdf_creation_date",
    "stable_document_id",
]
