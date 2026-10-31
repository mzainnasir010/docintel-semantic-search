"""DOCX extraction with heading-aware logical page records."""

from __future__ import annotations

import logging
from pathlib import Path

from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph

from docintel.models import PageContent

logger = logging.getLogger(__name__)


def _iter_body_blocks(document: DocumentObject):
    """Yield body paragraphs and tables in their original document order."""
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def _format_table(table: Table) -> str:
    """Flatten table cells into pipe-separated rows."""
    return "\n".join(
        " | ".join(cell.text.strip() for cell in row.cells)
        for row in table.rows
        if any(cell.text.strip() for cell in row.cells)
    )


def load_docx(
    path: str | Path,
    *,
    doc_id: str | None = None,
    doc_name: str | None = None,
) -> list[PageContent]:
    """Extract paragraphs, headings, and tables as section-based logical pages.

    DOCX files do not store stable physical page boundaries. Each heading section
    is therefore emitted as a logical unit with page number 1.
    """
    source_path = Path(path)
    resolved_doc_id = doc_id or source_path.stem
    resolved_doc_name = doc_name or source_path.name
    sections: list[tuple[str | None, list[str]]] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    try:
        document = Document(source_path)
        for block in _iter_body_blocks(document):
            if isinstance(block, Paragraph):
                text = block.text.strip()
                if not text:
                    continue
                style_name = block.style.name if block.style is not None else ""
                if style_name.lower().startswith("heading"):
                    if current_lines:
                        sections.append((current_heading, current_lines))
                    current_heading = text
                    current_lines = [text]
                else:
                    current_lines.append(text)
            else:
                table_text = _format_table(block)
                if table_text:
                    current_lines.append(table_text)
        if current_lines:
            sections.append((current_heading, current_lines))
    except Exception as error:
        logger.warning("Could not load DOCX %s: %s", source_path, error)
        return []

    if not sections:
        return [
            PageContent(
                doc_id=resolved_doc_id,
                doc_name=resolved_doc_name,
                page_number=1,
                text="",
                source_path=str(source_path),
            )
        ]
    return [
        PageContent(
            doc_id=resolved_doc_id,
            doc_name=resolved_doc_name,
            page_number=1,
            section=heading,
            text="\n\n".join(lines),
            source_path=str(source_path),
        )
        for heading, lines in sections
    ]

